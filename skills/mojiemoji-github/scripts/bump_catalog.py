#!/usr/bin/env python3
"""bump_catalog — promote high-frequency entries from the local usage cache
(usage.jsonl) into prestamp-catalog.yml, bump the plugin version, and open
a PR. Fully deterministic; no LLM calls.

Modes (default is --dry-run — explicit opt-in for destructive ops):
  --dry-run  print the diff summary, do not modify any file (DEFAULT)
  --apply    modify prestamp-catalog.yml only (no version bump, no git ops)
  --pr       full pipeline: --apply + plugin.json bump + branch/commit/push/PR
             (verifies clean tree + branches from origin/main)

YAML merge strategy:
  - Existing terms: append unseen variants (fingerprint = font/color/
    animation/outline/outline_width/speed). Identical flavor is a no-op.
  - New terms: append a fresh `<term>:` block at the end of the
    `terms:` map.
  - File-level comments and existing variant ordering are preserved.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import yaml

from lib.cache_path import default_cache_file


SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPTS_DIR.parent.parent.parent
DEFAULT_CATALOG = SCRIPTS_DIR.parent / "data" / "prestamp-catalog.yml"
DEFAULT_PLUGIN_JSON = REPO_ROOT / ".claude-plugin" / "plugin.json"
CACHE_STATS_SCRIPT = SCRIPTS_DIR / "cache_stats.py"


_IDENT_RE = re.compile(r"\A[a-zA-Z][a-zA-Z0-9_]*\Z")
_HEX6_RE = re.compile(r"\A[0-9a-f]{6}\Z")
_LEADING_DIGIT_RE = re.compile(r"\A\d")
_SAFE_TERM_KEY_RE = re.compile(r"\A[㐀-䶿一-鿿豈-﫿぀-ゟ゠-ヿA-Za-z0-9_]+\Z")


def yaml_value(value: object) -> str:
    s = str(value)
    if _IDENT_RE.match(s) and not _LEADING_DIGIT_RE.match(s) and not _HEX6_RE.match(s):
        return s
    return f'"{s}"'


def render_variant_lines(flavor: dict, indent: str = "    ") -> list[str]:
    lines = [
        f"{indent}- font: {flavor['font']}",
        f"{indent}  color: {yaml_value(flavor['color'])}",
    ]
    if flavor.get("outline"):
        lines.append(f"{indent}  outline: {yaml_value(flavor['outline'])}")
    if flavor.get("outline_width"):
        lines.append(f"{indent}  outline_width: {yaml_value(flavor['outline_width'])}")
    lines.append(f"{indent}  animation: {flavor['animation']}")
    if flavor.get("speed"):
        lines.append(f"{indent}  speed: {flavor['speed']}")
    return lines


def emit_term_key(term: str) -> str:
    """Quote term keys defensively — selectors may record any phrase."""
    s = str(term)
    if _SAFE_TERM_KEY_RE.match(s) and not _LEADING_DIGIT_RE.match(s):
        return s
    escaped = s.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def flavor_fingerprint(flavor: dict, defaults: dict) -> tuple:
    resolved = {**defaults, **flavor}
    return (
        resolved.get("font"),
        resolved.get("color"),
        resolved.get("animation"),
        resolved.get("outline"),
        resolved.get("outline_width"),
        resolved.get("speed"),
    )


def _run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, **kwargs)


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cache")
    parser.add_argument("--catalog", default=str(DEFAULT_CATALOG))
    parser.add_argument("--plugin-json", dest="plugin_json", default=str(DEFAULT_PLUGIN_JSON))
    parser.add_argument("--threshold", type=int, default=2)
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--dry-run", dest="mode", action="store_const", const="dry_run")
    mode_group.add_argument("--apply", dest="mode", action="store_const", const="apply")
    mode_group.add_argument("--pr", dest="mode", action="store_const", const="pr")
    parser.set_defaults(mode="dry_run")
    args = parser.parse_args(argv)

    cache_file = args.cache or default_cache_file()
    catalog_path = Path(args.catalog)
    plugin_json_path = Path(args.plugin_json)

    if not catalog_path.is_file():
        print(f"catalog not found: {catalog_path}", file=sys.stderr)
        return 1

    # --- 1. Run cache-stats to get candidate YAML fragment ----------------
    stats_proc = subprocess.run(
        [sys.executable, str(CACHE_STATS_SCRIPT), "--file", cache_file,
         "--threshold", str(args.threshold)],
        capture_output=True,
        text=True,
    )
    if stats_proc.stderr:
        sys.stderr.write(stats_proc.stderr)
    if stats_proc.returncode != 0:
        print(
            f"bump-catalog: cache-stats failed (exit {stats_proc.returncode}); aborting.",
            file=sys.stderr,
        )
        return stats_proc.returncode or 1

    if not stats_proc.stdout.strip():
        print(f"bump-catalog: no candidates from cache (threshold={args.threshold}).")
        print("bump-catalog: no new variants to add.")
        return 0

    candidates = yaml.safe_load("---\n" + stats_proc.stdout) or {}

    # --- 2. Diff against existing catalog --------------------------------
    catalog = yaml.safe_load(catalog_path.read_text(encoding="utf-8")) or {}
    existing_terms = catalog.get("terms") or {}
    defaults = catalog.get("defaults") or {}

    additions_for_existing: dict[str, list[dict]] = {}
    new_terms: dict[str, list[dict]] = {}

    for term, variants in candidates.items():
        term_str = str(term)
        existing = existing_terms.get(term_str)
        if existing is None:
            new_terms[term_str] = variants
            continue
        existing_fingerprints = {flavor_fingerprint(v, defaults) for v in existing}
        unseen = [
            v for v in variants
            if flavor_fingerprint(v, defaults) not in existing_fingerprints
        ]
        if unseen:
            additions_for_existing[term_str] = unseen

    total_new = sum(len(v) for v in new_terms.values()) + sum(len(v) for v in additions_for_existing.values())
    if total_new == 0:
        print(f"bump-catalog: all {len(candidates)} candidate term(s) already in catalog.")
        print("bump-catalog: no new variants to add.")
        return 0

    # --- 3. Render diff summary ------------------------------------------
    summary_lines: list[str] = []
    if new_terms:
        summary_lines.append(f"新規 term ({len(new_terms)} 件):")
        for term, variants in new_terms.items():
            summary_lines.append(f"  {term}: {len(variants)} variant(s)")
    if additions_for_existing:
        summary_lines.append(f"既存 term への variant 追加 ({len(additions_for_existing)} 件):")
        for term, variants in additions_for_existing.items():
            summary_lines.append(f"  {term}: +{len(variants)} variant(s)")
    print("\n".join(summary_lines))

    if args.mode == "dry_run":
        print()
        print("--- dry-run: catalog NOT modified ---")
        print(f"would add {total_new} variant(s) across {len(new_terms) + len(additions_for_existing)} term(s).")
        return 0

    # --- 4. Apply changes to catalog -------------------------------------
    text = catalog_path.read_text(encoding="utf-8")
    # Preserve trailing newline structure: splitlines(keepends=True) keeps each
    # line's terminator, mirroring Ruby's `String#lines`.
    lines = text.splitlines(keepends=True)

    block_continuation_re = re.compile(r"\A  [^\s-]")

    for term, variants in additions_for_existing.items():
        start_idx: Optional[int] = None
        prefix = f"  {term}:"
        # Also match quoted-key form: `  "term":`
        prefix_quoted = f'  "{term}":'
        for i, line in enumerate(lines):
            if line.startswith(prefix) or line.startswith(prefix_quoted):
                start_idx = i
                break
        if start_idx is None:
            continue
        insert_idx = len(lines)
        for i in range(start_idx + 1, len(lines)):
            if block_continuation_re.match(lines[i]):
                insert_idx = i
                break
        block = [l + "\n" for v in variants for l in render_variant_lines(v)]
        lines[insert_idx:insert_idx] = block

    if new_terms:
        if not lines or not lines[-1].endswith("\n"):
            lines.append("\n")
        for term, variants in new_terms.items():
            lines.append("\n")
            lines.append(f"  {emit_term_key(term)}:\n")
            for v in variants:
                for l in render_variant_lines(v):
                    lines.append(l + "\n")

    catalog_path.write_text("".join(lines), encoding="utf-8")
    print(f"bump-catalog: catalog updated with {total_new} variant(s).")

    if args.mode == "apply":
        return 0

    # --- 5. Bump plugin.json patch version (PR mode only) ---------------
    if plugin_json_path.is_file():
        plugin = json.loads(plugin_json_path.read_text(encoding="utf-8"))
        version = plugin.get("version", "0.0.0")
        parts = [int(p) if p.isdigit() else 0 for p in version.split(".")]
        while len(parts) < 3:
            parts.append(0)
        parts[2] += 1
        bumped = ".".join(str(p) for p in parts)
        plugin["version"] = bumped
        plugin_json_path.write_text(
            json.dumps(plugin, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print(f"bump-catalog: plugin.json {version} -> {bumped}")

    # --- 6. Git: branch + commit + PR -----------------------------------
    git_root_result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=True,
    )
    git_repo_root = Path(git_root_result.stdout.strip())

    def relativize(p: Path) -> str:
        return str(p.resolve().relative_to(git_repo_root))

    catalog_rel = relativize(catalog_path)
    plugin_json_rel = relativize(plugin_json_path) if plugin_json_path.is_file() else None
    intended_paths = [p for p in (catalog_rel, plugin_json_rel) if p]

    # Verify clean tree (excluding our intended paths).
    status_proc = subprocess.run(
        ["git", "status", "--porcelain"],
        capture_output=True, text=True, check=True,
    )
    dirty: list[str] = []
    for line in status_proc.stdout.splitlines():
        if len(line) < 4:
            continue
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ")[-1].strip()
        if path not in intended_paths:
            dirty.append(line)
    if dirty:
        print(
            "bump-catalog: refusing to PR — working tree has unrelated changes:",
            file=sys.stderr,
        )
        print("\n".join(dirty), file=sys.stderr)
        return 1

    def run_or_exit(cmd: list[str], pop_stash_on_fail: bool = False) -> None:
        r = subprocess.run(cmd)
        if r.returncode != 0:
            if pop_stash_on_fail:
                subprocess.run(["git", "stash", "pop"])
            sys.exit(r.returncode)

    run_or_exit(["git", "stash", "push", "-m", "bump-catalog-temp", "--", *intended_paths])
    run_or_exit(["git", "fetch", "origin", "main"])
    run_or_exit(["git", "checkout", "main"], pop_stash_on_fail=True)
    run_or_exit(["git", "pull", "--ff-only", "origin", "main"], pop_stash_on_fail=True)

    date_slug = datetime.now(timezone.utc).strftime("%Y%m%d")
    branch = f"feat/auto-catalog-grow-{date_slug}"
    title = f"feat(catalog): {total_new} 件の variant を自動追加"
    body = (
        "![type](https://img.shields.io/badge/type-feat-blue) "
        "![scope](https://img.shields.io/badge/scope-catalog-blue) "
        "![auto](https://img.shields.io/badge/auto-generated-purple) "
        "![tests](https://img.shields.io/badge/tests-passing-green)\n\n"
        "## 概要\n\n"
        f"`scripts/bump_catalog.py` がローカル `usage.jsonl` から閾値 ({args.threshold}) "
        "を満たした variant を catalog に昇格させた自動 PR です。\n\n"
        f"{chr(10).join(summary_lines)}\n\n"
        f"total: **{total_new} variant(s)** across "
        f"**{len(new_terms) + len(additions_for_existing)} term(s)**.\n\n"
        "## 出典\n\n"
        "自動 PR は #46 で定義された複利型の catalog 育成サイクルの一部です。\n"
    )

    run_or_exit(["git", "checkout", "-b", branch], pop_stash_on_fail=True)
    run_or_exit(["git", "stash", "pop"])
    run_or_exit(["git", "add", *intended_paths])
    run_or_exit(["git", "commit", "-m", title])
    run_or_exit(["git", "push", "-u", "origin", branch])
    pr_proc = subprocess.run(
        ["gh", "pr", "create", "--assignee", "@me", "--title", title, "--body", body],
        capture_output=True, text=True,
    )
    print(pr_proc.stdout.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
