"""Keep coach settings off the developer's home directory during tests."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def isolate_coach_settings(tmp_path, monkeypatch):
    monkeypatch.setenv("COACH_APP_SETTINGS_PATH", str(tmp_path / "coach-settings.json"))
