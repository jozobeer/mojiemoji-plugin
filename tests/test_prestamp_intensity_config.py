"""CLI tests: --intensity vs ~/.config/mojiemoji/config.json (#125)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
PRESTAMP_PATH = REPO_ROOT / "skills" / "mojiemoji-github" / "scripts" / "prestamp.py"

SAMPLE_JA = "今日は実装と確認と修正をしました。\n"


def _run_prestamp(
    tmp_path: Path,
    text: str,
    *args: str,
) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "XDG_CONFIG_HOME": str(tmp_path)}
    return subprocess.run(
        [sys.executable, str(PRESTAMP_PATH), *args],
        input=text,
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )


def _write_intensity_config(tmp_path: Path, intensity: str) -> None:
    cfg_dir = tmp_path / "mojiemoji"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    (cfg_dir / "config.json").write_text(
        json.dumps({"prestamp": {"intensity": intensity}}),
        encoding="utf-8",
    )


def test_cli_arg_overrides_config(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    _write_intensity_config(tmp_path, "normal")
    proc = _run_prestamp(tmp_path, SAMPLE_JA, "--intensity", "minimal")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.endswith("<!-- mojiemoji-intensity:minimal -->\n")


def test_config_used_when_no_cli_arg(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    _write_intensity_config(tmp_path, "normal")
    proc = _run_prestamp(tmp_path, SAMPLE_JA)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.endswith("<!-- mojiemoji-intensity:normal -->\n")


def test_default_aggressive_when_no_config_no_cli(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    proc = _run_prestamp(tmp_path, SAMPLE_JA)
    assert proc.returncode == 0, proc.stderr
    assert "mojiemoji-intensity:" not in proc.stdout


def test_explicit_aggressive_cli_overrides_normal_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    _write_intensity_config(tmp_path, "normal")
    proc = _run_prestamp(tmp_path, SAMPLE_JA, "--intensity", "aggressive")
    assert proc.returncode == 0, proc.stderr
    assert "mojiemoji-intensity:" not in proc.stdout
