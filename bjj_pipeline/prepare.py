"""Nest raw chapter speech onto a transcribed volume JSON."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from .batch_panoscribe import _atomic_write_json

SEASON_FOLDER = re.compile(r"^Season\s*(\d+)$", re.IGNORECASE)
_BY = re.compile(r"\s+by\s+", re.IGNORECASE)


def prepare_volume(
    json_path: Path,
    corpus_root: Path,
    video_library_root: Path | None = None,
) -> None:
    """Rewrite ``json_path`` in place with raw chapter speech. No model call."""
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return
    chapters = payload.get("chapters")
    if not isinstance(chapters, list) or not chapters:
        return
    segments = payload.get("segments")
    if not isinstance(segments, list):
        segments = []
    if _covers_whole_recording(chapters, segments):
        return

    instructional = _instructional_name(json_path, corpus_root)
    instructor = _instructor(instructional, video_library_root)
    volume = payload.get("video_file")
    if not isinstance(volume, str):
        volume = ""

    nested: list = []
    for index, chapter in enumerate(chapters):
        if not isinstance(chapter, dict):
            nested.append(chapter)
            continue
        previous = chapters[index - 1].get("title", "") if index > 0 else ""
        nxt = chapters[index + 1].get("title", "") if index + 1 < len(chapters) else ""
        if not isinstance(previous, str):
            previous = ""
        if not isinstance(nxt, str):
            nxt = ""
        updated = dict(chapter)
        updated["instructor"] = instructor
        updated["instructional"] = instructional
        updated["volume"] = volume
        updated["previous_chapter"] = previous
        updated["next_chapter"] = nxt
        updated["transcript_raw"] = _transcript_raw(chapter, segments)
        nested.append(updated)
    payload["chapters"] = nested
    _atomic_write_json(json_path, payload)


def _covers_whole_recording(chapters: list, segments: list) -> bool:
    if len(chapters) != 1 or not isinstance(chapters[0], dict):
        return False
    chapter = chapters[0]
    starts = [
        span["start"]
        for span in segments
        if isinstance(span, dict) and "start" in span
    ]
    ends = [
        span["end"]
        for span in segments
        if isinstance(span, dict) and "end" in span
    ]
    if not starts or not ends:
        return True
    return chapter["start"] <= min(starts) and chapter["end"] >= max(ends)


def _instructional_name(json_path: Path, corpus_root: Path) -> str:
    parent = json_path.resolve().parent
    root = corpus_root.resolve()
    try:
        relative = parent.relative_to(root)
    except ValueError:
        relative = None
    if relative is not None and relative.parts:
        return relative.parts[0]
    if SEASON_FOLDER.match(parent.name):
        return parent.parent.name
    return parent.name


def _instructor(show_folder: str, video_library_root: Path | None) -> str:
    if video_library_root is not None:
        from_nfo = _instructor_from_nfo(video_library_root / show_folder)
        if from_nfo:
            return from_nfo
    parts = _BY.split(show_folder, maxsplit=1)
    if len(parts) == 2:
        return parts[1].strip()
    return ""


def _instructor_from_nfo(show_folder: Path) -> str:
    nfo = show_folder / "tvshow.nfo"
    if not nfo.is_file():
        return ""
    try:
        root = ET.parse(nfo).getroot()
    except ET.ParseError:
        return ""
    director = (root.findtext("director") or "").strip()
    if director:
        return director
    for actor in root.findall("actor"):
        name = (actor.findtext("name") or "").strip()
        if name:
            return name
    return ""


def _overlaps(span: dict, chapter: dict) -> bool:
    return span["start"] <= chapter["end"] and span["end"] >= chapter["start"]


def _transcript_raw(chapter: dict, segments: list) -> str:
    overlapping = [
        span
        for span in segments
        if isinstance(span, dict) and "start" in span and "end" in span and _overlaps(span, chapter)
    ]
    overlapping.sort(key=lambda span: span["start"])
    parts = [
        f"<{span['start']:.2f}> {str(span.get('text') or '').strip()}"
        for span in overlapping
    ]
    return " ".join(parts)
