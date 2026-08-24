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

try:
    import yaml
except ModuleNotFoundError as exc:
    raise SystemExit(
        "PyYAML is required to read mojiemoji catalogs. Install it with "
        "`python3 -m pip install --user 'pyyaml>=6.0'`, or run from the "
        "repository with `uv run ...`."
    ) from exc

from lib.cache_path import default_cache_file
from lib.flavor import Flavor
from lib.yaml_helpers import emit_term_key


SCRIPTS_DIR = Path(__file__).resolve().parent
CACHE_STATS_SCRIPT = SCRIPTS_DIR / "cache_stats.py"
# Relative to the checkout root: the catalog as a committed source, which
# is what a bump has to rewrite — never an installed copy of the core.
CORE_PYPROJECT_RELPATH = Path("packages") / "mojiemoji-core" / "pyproject.toml"
CATALOG_RELPATH = (
    Path("packages") / "mojiemoji-core" / "src" / "mojiemoji"
    / "data" / "prestamp-catalog.yml"
)


def canonical_repo_root(start: Path = SCRIPTS_DIR) -> Path | None:
    """Return the source checkout root, not an installed package mirror."""
    for candidate in (start, *start.parents):
        if (
            (candidate / ".claude-plugin" / "plugin.json").is_file()
            and (candidate / CATALOG_RELPATH).is_file()
        ):
            return candidate
    return None


def required_source_path(path: Path | None, label: str) -> Path:
    if path is not None:
        return path

    raise SystemExit(
        f"bump-catalog: canonical {label} not found. Run from the source "
        f"checkout or pass --{label.replace('_', '-')} explicitly; refusing "
        "to mutate an installed Codex package cache."
    )


def json_version_bumped(path: Path) -> tuple[str, str] | None:
    if not path.is_file():
        return None

    plugin = json.loads(path.read_text(encoding="utf-8"))
    version = plugin.get("version", "0.0.0")
    parts = [int(p) if p.isdigit() else 0 for p in version.split(".")]
    while len(parts) < 3:
        parts.append(0)
    parts[2] += 1
    bumped = ".".join(str(p) for p in parts)
    plugin["version"] = bumped
    path.write_text(
        json.dumps(plugin, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return version, bumped


def toml_version_bumped(path: Path) -> tuple[str, str] | None:
    """Patch-bump `[project] version` in a pyproject, preserving formatting.

    Rewritten by regex rather than a TOML round-trip: the file is
    hand-maintained, and an emitter would reflow comments and quoting that
    reviewers rely on.
    """
    if not path.is_file():
        return None

    text = path.read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"$', text, flags=re.MULTILINE)
    if match is None:
        return None

    version = match.group(1)
    parts = [int(p) if p.isdigit() else 0 for p in version.split(".")]
    while len(parts) < 3:
        parts.append(0)
    parts[2] += 1
    bumped = ".".join(str(p) for p in parts)
    path.write_text(
        text[: match.start(1)] + bumped + text[match.end(1) :],
        encoding="utf-8",
    )
    return version, bumped


def render_variant_lines(flavor: dict, indent: str = "    ") -> list[str]:
    return Flavor.from_dict(flavor).to_yaml_lines(indent=indent)


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


def package_mutation_paths(package_dir: Path | None, git_repo_root: Path) -> list[str]:
    """Return package roots that the sync step may legitimately mutate."""
    if package_dir is None or not package_dir.exists():
        return []

    return [
        str(path.resolve().relative_to(git_repo_root))
        for path in (package_dir / ".codex-plugin", package_dir / "skills")
        if path.exists()
    ]


def intended_path(path: str, intended_paths: set[str]) -> bool:
    """Return whether a git path is an intended file or lies below one."""
    return any(path == intended or path.startswith(f"{intended}/") for intended in intended_paths)


def main(argv: Optional[list[str]] = None) -> int:
    source_root = canonical_repo_root()
    default_catalog = (
        source_root / CATALOG_RELPATH if source_root else None
    )
    default_plugin_json = source_root / ".claude-plugin" / "plugin.json" if source_root else None
    core_pyproject = source_root / CORE_PYPROJECT_RELPATH if source_root else None
    package_dir = source_root / "plugins" / "mojiemoji-plugin" if source_root else None
    default_codex_plugin_json = (
        package_dir / ".codex-plugin" / "plugin.json" if package_dir else None
    )
    sync_script = source_root / "scripts" / "sync-codex-plugin-package.sh" if source_root else None
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cache")
    parser.add_argument("--catalog")
    parser.add_argument("--plugin-json", dest="plugin_json")
    parser.add_argument("--codex-plugin-json", dest="codex_plugin_json")
    parser.add_argument("--threshold", type=int, default=2)
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument("--dry-run", dest="mode", action="store_const", const="dry_run")
    mode_group.add_argument("--apply", dest="mode", action="store_const", const="apply")
    mode_group.add_argument("--pr", dest="mode", action="store_const", const="pr")
    parser.set_defaults(mode="dry_run")
    args = parser.parse_args(argv)

    cache_file = args.cache or default_cache_file()
    catalog_path = Path(args.catalog) if args.catalog else required_source_path(default_catalog, "catalog")
    plugin_json_path = Path(args.plugin_json) if args.plugin_json else default_plugin_json
    codex_plugin_json_path = (
        Path(args.codex_plugin_json) if args.codex_plugin_json else default_codex_plugin_json
    )

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

    # --- 5. Bump plugin manifest patch versions (PR mode only) ----------
    if plugin_json_path is None:
        raise SystemExit(
            "bump-catalog: canonical plugin_json not found. Run --pr from "
            "the source checkout or pass --plugin-json explicitly."
        )

    bumped = json_version_bumped(plugin_json_path)
    if bumped is not None:
        version, next_version = bumped
        print(f"bump-catalog: plugin.json {version} -> {next_version}")

    if codex_plugin_json_path is not None:
        codex_bumped = json_version_bumped(codex_plugin_json_path)
        if codex_bumped is not None:
            version, next_version = codex_bumped
            print(f"bump-catalog: codex plugin.json {version} -> {next_version}")

    # The catalog ships as core package data, so a catalog-only PR that
    # bumped just the plugin manifests would leave every `uvx mojiemoji`
    # user on the previous catalog indefinitely.
    if core_pyproject is not None:
        core_bumped = toml_version_bumped(core_pyproject)
        if core_bumped is not None:
            version, next_version = core_bumped
            print(f"bump-catalog: core pyproject.toml {version} -> {next_version}")

    if sync_script is not None and sync_script.is_file():
        sync_proc = subprocess.run([str(sync_script)])
        if sync_proc.returncode != 0:
            return sync_proc.returncode or 1

    # --- 6. Git: branch + commit + PR -----------------------------------
    git_root_result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        capture_output=True, text=True, check=True,
    )
    git_repo_root = Path(git_root_result.stdout.strip())

    def relativize(p: Path) -> str:
        return str(p.resolve().relative_to(git_repo_root))

    intended_paths = {
        relativize(catalog_path),
        *((
            relativize(plugin_json_path),
        ) if plugin_json_path.is_file() else ()),
        *((
            relativize(codex_plugin_json_path),
        ) if codex_plugin_json_path is not None and codex_plugin_json_path.is_file() else ()),
        *((
            relativize(core_pyproject),
        ) if core_pyproject is not None and core_pyproject.is_file() else ()),
    }
    intended_paths.update(package_mutation_paths(package_dir, git_repo_root))

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
        if not intended_path(path, intended_paths):
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

    run_or_exit(["git", "stash", "push", "-m", "bump-catalog-temp", "--", *sorted(intended_paths)])
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
    run_or_exit(["git", "add", *sorted(intended_paths)])
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
