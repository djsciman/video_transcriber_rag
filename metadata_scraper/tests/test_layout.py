from pathlib import Path

import pytest

from bjj_organizer.errors import MatchError, UsageError
from bjj_organizer.layout import detect_layout, looks_like_library_root


def _touch(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"")


def test_leaf_folder(tmp_path: Path):
    for i in range(1, 5):
        _touch(tmp_path / f"Vol{i}.mp4")
    kind, seasons = detect_layout(tmp_path)
    assert kind == "leaf"
    assert seasons == []


def test_nested_seasons(tmp_path: Path):
    for name in ("Closed Guard", "Open Guard"):
        for i in range(1, 3):
            _touch(tmp_path / name / f"{i}.mp4")
    kind, seasons = detect_layout(tmp_path)
    assert kind == "nested"
    assert [s.name for s in seasons] == ["Closed Guard", "Open Guard"]


def test_mixed_root_videos_and_seasons_errors(tmp_path: Path):
    _touch(tmp_path / "root.mp4")
    _touch(tmp_path / "Closed Guard" / "1.mp4")
    with pytest.raises(MatchError, match="both videos and season"):
        detect_layout(tmp_path)


def test_library_root_heuristic(tmp_path: Path):
    for i in range(12):
        show = tmp_path / f"Show {i}"
        _touch(show / "Season A" / "1.mp4")
        _touch(show / "Season B" / "1.mp4")
    assert looks_like_library_root(tmp_path)
    with pytest.raises(UsageError, match="library root"):
        detect_layout(tmp_path)
