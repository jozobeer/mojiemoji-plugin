"""coverage.py --intensity and 2D SURFACE_THRESHOLDS behavior."""

from __future__ import annotations

import importlib.util

import pytest

from conftest import COVERAGE, run_py

def _load_coverage_mod():
    spec = importlib.util.spec_from_file_location("coverage_intensity", COVERAGE)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    assert spec is not None and spec.loader is not None
    # noqa: S403 — test-only dynamic import of the repo script
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def test_aggressive_cli_parity_with_default() -> None:
    body = "# 概要\n\n本テキストは説明です。修正と対応を行いました。\n"
    a = run_py(COVERAGE, body, "--surface", "issue-body", "--mode", "warn")
    b = run_py(COVERAGE, body, "--surface", "issue-body", "--mode", "warn", "--intensity", "aggressive")
    assert a.returncode == b.returncode
    assert a.stdout == b.stdout


def test_minimal_passes_low_density_issue_body_fails_aggressive() -> None:
    # Low stamp-to-prose ratio: satisfies minimal density (0.4) but not aggressive (2.0).
    stamp = (
        '<img src="https://mojiemoji.jozo.beer/emoji/%E3%83%86%E3%82%B9%E3%83%88?'
        'font=gothic&color=3b82f6&animation=bane&background=transparent&outline_width=0" '
        'alt="テスト" height="24" align="absmiddle">'
    )
    prose = "あ" * 200
    body = f"{stamp}\n\n{prose}\n"
    agg = run_py(COVERAGE, body, "--surface", "issue-body", "--mode", "block", "--intensity", "aggressive")
    mini = run_py(COVERAGE, body, "--surface", "issue-body", "--mode", "block", "--intensity", "minimal")
    assert agg.returncode == 2
    assert mini.returncode == 0


@pytest.mark.parametrize(
    "surface,intensity,metric_key,delta",
    [
        ("issue-body", "aggressive", "min_density", 0.01),
        ("issue-body", "normal", "min_sentence_hit", 0.01),
        ("issue-body", "minimal", "min_paragraph_hit", 0.01),
        ("pr-body", "aggressive", "min_density", 0.01),
        ("pr-body", "normal", "min_sentence_hit", 0.01),
        ("pr-body", "minimal", "max_consecutive_unstamped_paragraphs", -1),
        ("review-body", "aggressive", "min_density", 0.01),
        ("review-body", "normal", "min_paragraph_hit", 0.01),
        ("review-body", "minimal", "min_density", 0.01),
        ("comment-body", "aggressive", "min_density", 0.01),
        ("comment-body", "normal", "min_paragraph_hit", 0.01),
        ("comment-body", "minimal", "min_sentence_hit", 0.01),
        ("release-note", "aggressive", "min_density", 0.01),
        ("release-note", "normal", "min_density", 0.01),
        ("release-note", "minimal", "max_consecutive_unstamped_paragraphs", -1),
    ],
)
def test_threshold_boundary_triggers_block(surface: str, intensity: str, metric_key: str, delta: float) -> None:
    mod = _load_coverage_mod()
    th = mod.SURFACE_THRESHOLDS[(surface, intensity)]
    metrics = {
        "stamp_count": 100,
        "japanese_char_count": 100,
        "density": float(th["min_density"]),
        "sentence_hits": 100,
        "sentence_total": 100,
        "sentence_hit_rate": float(th["min_sentence_hit"]),
        "paragraph_hits": 100,
        "paragraph_total": 100,
        "paragraph_hit_rate": float(th["min_paragraph_hit"]),
        "max_consecutive_unstamped": int(th["max_consecutive_unstamped_paragraphs"]),
        "heading_warnings": [],
        "paragraph_warnings": [],
    }
    failures_ok = mod.check_failures(metrics, th)
    assert failures_ok == [], failures_ok

    breach = dict(metrics)
    if metric_key == "min_density":
        breach["density"] = float(th["min_density"]) - 0.01
    elif metric_key == "min_sentence_hit":
        breach["sentence_hit_rate"] = float(th["min_sentence_hit"]) - 0.01
    elif metric_key == "min_paragraph_hit":
        breach["paragraph_hit_rate"] = float(th["min_paragraph_hit"]) - 0.01
    elif metric_key == "max_consecutive_unstamped_paragraphs":
        breach["max_consecutive_unstamped"] = int(th["max_consecutive_unstamped_paragraphs"]) + 1
    failures_bad = mod.check_failures(breach, th)
    assert failures_bad != [], (metric_key, th, failures_bad)


def test_surface_thresholds_string_key_maps_to_aggressive() -> None:
    mod = _load_coverage_mod()
    a = mod.SURFACE_THRESHOLDS["issue-body"]
    b = mod.SURFACE_THRESHOLDS[("issue-body", "aggressive")]
    assert a == b
