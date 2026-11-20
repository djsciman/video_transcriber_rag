from __future__ import annotations

import re
from pathlib import Path

from .errors import MatchError, UsageError
from .naming import VIDEO_EXTS, season_folder_number

IGNORE_DIR_NAMES = {
    "extras",
    "featurettes",
    "trailers",
    "behind the scenes",
    "interviews",
    "samples",
    "scripts",
    "theme-music",
    "backdrops",
}


def is_video(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in VIDEO_EXTS


def list_videos(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    videos = [p for p in folder.iterdir() if is_video(p) and not p.name.startswith(".")]
    return sorted(videos, key=lambda p: p.name.lower())


def dir_has_videos(folder: Path) -> bool:
    return bool(list_videos(folder))


def child_dirs(folder: Path) -> list[Path]:
    return sorted(
        (
            p
            for p in folder.iterdir()
            if p.is_dir() and p.name.lower() not in IGNORE_DIR_NAMES and not p.name.startswith(".")
        ),
        key=lambda p: p.name.lower(),
    )


def looks_like_library_root(folder: Path) -> bool:
    children = child_dirs(folder)
    if len(children) < 12:
        return False
    nested_shows = 0
    for child in children:
        if any(dir_has_videos(sub) for sub in child_dirs(child)):
            nested_shows += 1
    return nested_shows >= 2


def detect_layout(folder: Path) -> tuple[str, list[Path]]:
    """Return ('leaf', []) or ('nested', [season_dirs])."""
    if not folder.is_dir():
        raise UsageError(f"Folder does not exist: {folder}")
    if looks_like_library_root(folder):
        raise UsageError(
            f"{folder} looks like the library root, not a single show. "
            "Point --folder at one instructional or series folder."
        )
    seasons = [d for d in child_dirs(folder) if dir_has_videos(d)]
    root_videos = list_videos(folder)
    if seasons and root_videos:
        raise MatchError(
            "Show folder has both videos and season subfolders. "
            "Jellyfin cannot mix those; move root videos into a season folder first."
        )
    if seasons:
        deeper = []
        for season in seasons:
            if any(dir_has_videos(sub) for sub in child_dirs(season)):
                deeper.append(season.name)
        if deeper:
            raise MatchError(
                "Nested more than two levels (show/season/files). "
                f"Flatten these first: {', '.join(deeper)}"
            )
        return "nested", seasons
    if root_videos:
        return "leaf", []
    raise UsageError(f"No video files found in {folder}")


def season_source_name(folder: Path) -> str:
    nfo = folder / "season.nfo"
    if nfo.is_file():
        text = nfo.read_text(encoding="utf-8", errors="replace")
        match = re_search_title(text)
        if match:
            return match
    name = folder.name
    if season_folder_number(name) is not None:
        return name
    return name


def re_search_title(nfo_text: str) -> str | None:
    match = re.search(r"<title>(.*?)</title>", nfo_text, re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    title = re.sub(r"\s+", " ", match.group(1)).strip()
    return title or None
