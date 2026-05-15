"""Tests for cache-record.rb, cache-stats.rb, and bump-catalog.rb."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "skills" / "mojiemoji-github" / "scripts"
CACHE_RECORD = SCRIPTS / "cache-record.rb"
CACHE_STATS = SCRIPTS / "cache-stats.rb"
BUMP_CATALOG = SCRIPTS / "bump-catalog.rb"


def run_ruby(script: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    return subprocess.run(
        ["ruby", str(script), *args],
        capture_output=True,
        text=True,
        timeout=10,
        env=full_env,
    )


# ---------- cache-record.rb ----------


def test_cache_record_appends_jsonl_entry(tmp_path: Path) -> None:
    cache = tmp_path / "nested" / "usage.jsonl"
    proc = run_ruby(
        CACHE_RECORD,
        "--term", "完成",
        "--font", "maru-bold",
        "--color", "22c55e",
        "--animation", "poyoon",
        "--outline", "9934d3",
        "--file", str(cache),
    )
    assert proc.returncode == 0, proc.stderr
    assert cache.exists()
    line = cache.read_text().strip()
    entry = json.loads(line)
    assert entry["term"] == "完成"
    assert entry["flavor"] == {
        "font": "maru-bold",
        "color": "22c55e",
        "animation": "poyoon",
        "outline": "9934d3",
        "outline_width": "2",
    }
    assert entry["source"] == "selector"
    assert "ts" in entry


def test_cache_record_appends_multiple_entries(tmp_path: Path) -> None:
    cache = tmp_path / "usage.jsonl"
    for color in ("22c55e", "60a5fa", "ec4899"):
        proc = run_ruby(
            CACHE_RECORD,
            "--term", "歓迎",
            "--font", "hachimaru",
            "--color", color,
            "--animation", "bane",
            "--outline", "darker",
            "--file", str(cache),
        )
        assert proc.returncode == 0, proc.stderr
    lines = cache.read_text().strip().splitlines()
    assert len(lines) == 3
    colors = [json.loads(line)["flavor"]["color"] for line in lines]
    assert colors == ["22c55e", "60a5fa", "ec4899"]


def test_cache_record_honors_speed_flag(tmp_path: Path) -> None:
    cache = tmp_path / "usage.jsonl"
    proc = run_ruby(
        CACHE_RECORD,
        "--term", "回転",
        "--font", "noto",
        "--color", "3b82f6",
        "--animation", "kaiten",
        "--outline", "darker",
        "--speed", "slow",
        "--file", str(cache),
    )
    assert proc.returncode == 0, proc.stderr
    entry = json.loads(cache.read_text().strip())
    assert entry["flavor"]["speed"] == "slow"


def test_cache_record_fails_on_missing_required(tmp_path: Path) -> None:
    cache = tmp_path / "usage.jsonl"
    proc = run_ruby(
        CACHE_RECORD,
        "--term", "完成",
        "--file", str(cache),
    )
    assert proc.returncode == 1
    assert "missing required flag" in proc.stderr
    assert not cache.exists()


def test_cache_record_uses_env_override(tmp_path: Path) -> None:
    cache = tmp_path / "envpath.jsonl"
    proc = run_ruby(
        CACHE_RECORD,
        "--term", "確認",
        "--font", "gothic-bold",
        "--color", "f59e0b",
        "--animation", "tate_scroll",
        "--outline", "darker",
        env={"MOJIEMOJI_CACHE_FILE": str(cache)},
    )
    assert proc.returncode == 0, proc.stderr
    assert cache.exists()


def test_cache_record_uses_xdg_data_home(tmp_path: Path) -> None:
    proc = run_ruby(
        CACHE_RECORD,
        "--term", "確認",
        "--font", "gothic-bold",
        "--color", "f59e0b",
        "--animation", "tate_scroll",
        "--outline", "darker",
        env={"XDG_DATA_HOME": str(tmp_path), "MOJIEMOJI_CACHE_FILE": ""},
    )
    assert proc.returncode == 0, proc.stderr
    expected = tmp_path / "mojiemoji-plugin" / "usage.jsonl"
    assert expected.exists()
    assert proc.stdout.strip() == str(expected)


# ---------- cache-stats.rb ----------


def _seed_cache(path: Path, entries: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for e in entries:
            f.write(json.dumps(e) + "\n")


def _entry(term: str, color: str, *, font: str = "gothic-bold", animation: str = "bane") -> dict:
    return {
        "term": term,
        "flavor": {
            "font": font,
            "color": color,
            "animation": animation,
            "outline": "darker",
            "outline_width": "2",
        },
        "ts": "2026-05-15T12:00:00Z",
        "source": "selector",
    }


def test_cache_stats_promotes_term_meeting_threshold(tmp_path: Path) -> None:
    cache = tmp_path / "usage.jsonl"
    _seed_cache(cache, [_entry("祝福", "ec4899"), _entry("祝福", "ec4899")])
    proc = run_ruby(CACHE_STATS, "--file", str(cache), "--threshold", "2")
    assert proc.returncode == 0, proc.stderr
    assert "祝福:" in proc.stdout
    assert "ec4899" in proc.stdout


def test_cache_stats_skips_below_threshold(tmp_path: Path) -> None:
    cache = tmp_path / "usage.jsonl"
    _seed_cache(cache, [_entry("祝福", "ec4899")])
    proc = run_ruby(CACHE_STATS, "--file", str(cache), "--threshold", "2")
    assert proc.returncode == 0, proc.stderr
    assert "祝福" not in proc.stdout


def test_cache_stats_deduplicates_identical_flavors(tmp_path: Path) -> None:
    cache = tmp_path / "usage.jsonl"
    _seed_cache(
        cache,
        [
            _entry("祝福", "ec4899"),
            _entry("祝福", "ec4899"),
            _entry("祝福", "ec4899"),
        ],
    )
    proc = run_ruby(CACHE_STATS, "--file", str(cache), "--threshold", "2")
    assert proc.returncode == 0, proc.stderr
    # Only one variant should be emitted even with 3 identical entries.
    assert proc.stdout.count("- font:") == 1


def test_cache_stats_emits_multiple_variants_per_term(tmp_path: Path) -> None:
    cache = tmp_path / "usage.jsonl"
    _seed_cache(
        cache,
        [
            _entry("祝福", "ec4899", animation="bane"),
            _entry("祝福", "ec4899", animation="bane"),
            _entry("祝福", "22c55e", animation="poyoon"),
            _entry("祝福", "22c55e", animation="poyoon"),
        ],
    )
    proc = run_ruby(CACHE_STATS, "--file", str(cache), "--threshold", "2")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.count("- font:") == 2


def test_cache_stats_handles_missing_file(tmp_path: Path) -> None:
    cache = tmp_path / "nonexistent.jsonl"
    proc = run_ruby(CACHE_STATS, "--file", str(cache), "--threshold", "2")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == ""


def test_cache_stats_skips_malformed_lines(tmp_path: Path) -> None:
    cache = tmp_path / "usage.jsonl"
    cache.write_text(
        "not json\n"
        + json.dumps(_entry("祝福", "ec4899")) + "\n"
        + json.dumps(_entry("祝福", "ec4899")) + "\n",
    )
    proc = run_ruby(CACHE_STATS, "--file", str(cache), "--threshold", "2")
    assert proc.returncode == 0, proc.stderr
    assert "祝福" in proc.stdout
    assert "malformed" in proc.stderr.lower() or "skipped" in proc.stderr.lower()


# ---------- bump-catalog.rb (dry-run) ----------


def test_bump_catalog_dry_run_reports_new_term(tmp_path: Path) -> None:
    cache = tmp_path / "usage.jsonl"
    _seed_cache(cache, [_entry("祝福", "ec4899"), _entry("祝福", "ec4899")])
    catalog = tmp_path / "prestamp-catalog.yml"
    catalog.write_text("defaults:\n  background: transparent\n  outline_width: \"2\"\n\nterms:\n")
    proc = run_ruby(
        BUMP_CATALOG,
        "--cache", str(cache),
        "--catalog", str(catalog),
        "--threshold", "2",
        "--dry-run",
    )
    assert proc.returncode == 0, proc.stderr
    assert "祝福" in proc.stdout
    # Source catalog must not be modified during dry-run.
    assert "祝福" not in catalog.read_text()


def test_bump_catalog_dry_run_skips_existing_exact_variant(tmp_path: Path) -> None:
    cache = tmp_path / "usage.jsonl"
    _seed_cache(cache, [_entry("祝福", "ec4899"), _entry("祝福", "ec4899")])
    catalog = tmp_path / "prestamp-catalog.yml"
    catalog.write_text(
        "defaults:\n  background: transparent\n  outline_width: \"2\"\n\n"
        "terms:\n"
        "  祝福:\n"
        "    - font: gothic-bold\n"
        "      color: \"ec4899\"\n"
        "      outline: \"darker\"\n"
        "      animation: bane\n"
    )
    proc = run_ruby(
        BUMP_CATALOG,
        "--cache", str(cache),
        "--catalog", str(catalog),
        "--threshold", "2",
        "--dry-run",
    )
    assert proc.returncode == 0, proc.stderr
    assert "no new variants" in proc.stdout.lower()


def test_bump_catalog_dry_run_reports_when_no_candidates(tmp_path: Path) -> None:
    cache = tmp_path / "usage.jsonl"
    _seed_cache(cache, [_entry("祝福", "ec4899")])  # below threshold
    catalog = tmp_path / "prestamp-catalog.yml"
    catalog.write_text("defaults:\n  background: transparent\n\nterms:\n")
    proc = run_ruby(
        BUMP_CATALOG,
        "--cache", str(cache),
        "--catalog", str(catalog),
        "--threshold", "2",
        "--dry-run",
    )
    assert proc.returncode == 0, proc.stderr
    assert "no new variants" in proc.stdout.lower() or "no candidates" in proc.stdout.lower()


def test_bump_catalog_apply_merges_new_variants(tmp_path: Path) -> None:
    cache = tmp_path / "usage.jsonl"
    _seed_cache(cache, [_entry("祝福", "ec4899"), _entry("祝福", "ec4899")])
    catalog = tmp_path / "prestamp-catalog.yml"
    catalog.write_text("defaults:\n  background: transparent\n  outline_width: \"2\"\n\nterms:\n")
    proc = run_ruby(
        BUMP_CATALOG,
        "--cache", str(cache),
        "--catalog", str(catalog),
        "--threshold", "2",
        "--apply",
    )
    assert proc.returncode == 0, proc.stderr
    text = catalog.read_text()
    assert "祝福:" in text
    assert "ec4899" in text


def test_bump_catalog_apply_preserves_existing_variants(tmp_path: Path) -> None:
    cache = tmp_path / "usage.jsonl"
    _seed_cache(
        cache,
        [_entry("祝福", "60a5fa", animation="poyoon"), _entry("祝福", "60a5fa", animation="poyoon")],
    )
    catalog = tmp_path / "prestamp-catalog.yml"
    catalog.write_text(
        "defaults:\n  background: transparent\n  outline_width: \"2\"\n\n"
        "terms:\n"
        "  祝福:\n"
        "    - font: gothic-bold\n"
        "      color: \"ec4899\"\n"
        "      outline: \"darker\"\n"
        "      animation: bane\n"
    )
    proc = run_ruby(
        BUMP_CATALOG,
        "--cache", str(cache),
        "--catalog", str(catalog),
        "--threshold", "2",
        "--apply",
    )
    assert proc.returncode == 0, proc.stderr
    text = catalog.read_text()
    # Both the old and new variant should coexist under 祝福.
    assert "ec4899" in text
    assert "60a5fa" in text
    assert text.count("animation: bane") >= 1
    assert text.count("animation: poyoon") >= 1
