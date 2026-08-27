"""Persistent config for prestamp CLI (`~/.config/mojiemoji/config.json`).

See #125 — intensity default resolution: CLI > config > aggressive.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional

VALID_INTENSITIES = ("aggressive", "normal", "minimal")


def get_config_path() -> Path:
    """XDG-compliant config path. Honors XDG_CONFIG_HOME if set."""
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "mojiemoji" / "config.json"


def load_config() -> dict:
    """Read config. Returns {} on any failure (missing file silent, broken JSON / permission warn to stderr)."""
    path = get_config_path()
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            print(f"warning: {path} is not a JSON object; ignoring", file=sys.stderr)
            return {}
        return data
    except (json.JSONDecodeError, OSError) as e:
        print(f"warning: failed to read {path}: {e}; ignoring", file=sys.stderr)
        return {}


def save_config(cfg: dict) -> None:
    """Write config, creating parent dirs as needed."""
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
        f.write("\n")


def get_intensity() -> Optional[str]:
    """Return configured intensity, or None if unset / invalid."""
    cfg = load_config()
    prestamp = cfg.get("prestamp")
    if not isinstance(prestamp, dict):
        return None
    intensity = prestamp.get("intensity")
    if intensity is None:
        return None
    if intensity not in VALID_INTENSITIES:
        print(
            f"warning: config intensity {intensity!r} is not one of {VALID_INTENSITIES}; ignoring",
            file=sys.stderr,
        )
        return None
    return intensity


def set_intensity(intensity: str) -> None:
    """Persist intensity. Raises ValueError on invalid value."""
    if intensity not in VALID_INTENSITIES:
        raise ValueError(f"intensity must be one of {VALID_INTENSITIES}, got {intensity!r}")
    cfg = load_config()
    cfg.setdefault("prestamp", {})["intensity"] = intensity
    save_config(cfg)


def unset_intensity() -> None:
    """Remove intensity from config, preserving other keys/sections."""
    cfg = load_config()
    prestamp = cfg.get("prestamp")
    if isinstance(prestamp, dict) and "intensity" in prestamp:
        del prestamp["intensity"]
        if not prestamp:
            del cfg["prestamp"]
        save_config(cfg)
