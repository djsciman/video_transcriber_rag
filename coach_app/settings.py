"""Coach-facing application settings."""

from __future__ import annotations

import json
import os
from pathlib import Path

SETTINGS_PATH_ENV = "COACH_APP_SETTINGS_PATH"
EXTRACTED_INDEX_KEY = "extracted_index"


def settings_path() -> Path:
    env = os.environ.get(SETTINGS_PATH_ENV)
    if isinstance(env, str) and env.strip():
        return Path(env)
    return Path.home() / ".coach_app" / "settings.json"


def extracted_index_path() -> Path | None:
    raw = _load().get(EXTRACTED_INDEX_KEY)
    if not isinstance(raw, str) or not raw.strip():
        return None
    return Path(raw)


def set_extracted_index_path(location) -> None:
    data = _load()
    if location is None or location == "":
        data.pop(EXTRACTED_INDEX_KEY, None)
    else:
        data[EXTRACTED_INDEX_KEY] = str(Path(location))
    _save(data)


def _load() -> dict:
    path = settings_path()
    if not path.is_file():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _save(data: dict) -> None:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
