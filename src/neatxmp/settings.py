"""Persist user settings across invocations."""

from __future__ import annotations

import json
from pathlib import Path

_SETTINGS_PATH = Path.home() / ".config" / "neatxmp" / "settings.json"


def load() -> dict:
    try:
        return json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save(data: dict) -> None:
    _SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _SETTINGS_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")
