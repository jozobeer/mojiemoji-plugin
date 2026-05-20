"""Tests for lib.config — XDG config and prestamp intensity persistence (#125)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "skills" / "mojiemoji-github" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from lib import config  # noqa: E402


def test_get_config_path_default_no_xdg(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("XDG_CONFIG_HOME", raising=False)
    assert config.get_config_path() == Path.home() / ".config" / "mojiemoji" / "config.json"


def test_get_config_path_honors_xdg(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", "/tmp/xdg-foo")
    assert config.get_config_path() == Path("/tmp/xdg-foo/mojiemoji/config.json")


def test_load_config_missing_returns_empty(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert config.load_config() == {}


def test_load_config_invalid_json_warns_and_returns_empty(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    cfg_path = tmp_path / "mojiemoji" / "config.json"
    cfg_path.parent.mkdir(parents=True)
    cfg_path.write_text("{not json", encoding="utf-8")
    assert config.load_config() == {}
    err = capsys.readouterr().err
    assert "warning" in err


def test_load_config_non_object_returns_empty(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    cfg_path = tmp_path / "mojiemoji" / "config.json"
    cfg_path.parent.mkdir(parents=True)
    cfg_path.write_text("[1,2,3]", encoding="utf-8")
    assert config.load_config() == {}
    assert "warning" in capsys.readouterr().err


def test_get_intensity_unset_returns_none(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert config.get_intensity() is None


def test_get_intensity_normal(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    p = tmp_path / "mojiemoji" / "config.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps({"prestamp": {"intensity": "normal"}}), encoding="utf-8")
    assert config.get_intensity() == "normal"


def test_get_intensity_minimal(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    p = tmp_path / "mojiemoji" / "config.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps({"prestamp": {"intensity": "minimal"}}), encoding="utf-8")
    assert config.get_intensity() == "minimal"


def test_get_intensity_aggressive(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    p = tmp_path / "mojiemoji" / "config.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps({"prestamp": {"intensity": "aggressive"}}), encoding="utf-8")
    assert config.get_intensity() == "aggressive"


def test_get_intensity_invalid_warns_returns_none(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    p = tmp_path / "mojiemoji" / "config.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps({"prestamp": {"intensity": "loud"}}), encoding="utf-8")
    assert config.get_intensity() is None
    assert "warning" in capsys.readouterr().err


def test_set_intensity_creates_file_and_parents(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    config.set_intensity("minimal")
    cfg_path = tmp_path / "mojiemoji" / "config.json"
    assert cfg_path.is_file()
    data = json.loads(cfg_path.read_text(encoding="utf-8"))
    assert data == {"prestamp": {"intensity": "minimal"}}


def test_set_intensity_invalid_raises_value_error(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    with pytest.raises(ValueError, match="intensity must be one of"):
        config.set_intensity("loud")


def test_set_intensity_overwrites_existing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    p = tmp_path / "mojiemoji" / "config.json"
    p.parent.mkdir(parents=True)
    p.write_text(json.dumps({"prestamp": {"intensity": "minimal"}}), encoding="utf-8")
    config.set_intensity("aggressive")
    assert json.loads(p.read_text(encoding="utf-8")) == {"prestamp": {"intensity": "aggressive"}}


def test_unset_intensity_removes_key_preserves_other_sections(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    p = tmp_path / "mojiemoji" / "config.json"
    p.parent.mkdir(parents=True)
    p.write_text(
        json.dumps({"prestamp": {"intensity": "normal"}, "other": {"foo": 1}}),
        encoding="utf-8",
    )
    config.unset_intensity()
    assert json.loads(p.read_text(encoding="utf-8")) == {"other": {"foo": 1}}


def test_unset_intensity_when_not_set_is_noop(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    config.unset_intensity()
    cfg_path = tmp_path / "mojiemoji" / "config.json"
    assert not cfg_path.exists()
