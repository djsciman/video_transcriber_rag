"""Nest speech under real chapters on a raw volume. Does not enter the curated store."""

from __future__ import annotations

import re

_FILLERS = frozenset({"uh", "um", "er"})
_SPAN_PREFIX = re.compile(r"<(\d+(?:\.\d+)?)>")


def _strip_fillers(text: str) -> str:
    tokens = [
        token
        for token in text.split()
        if token.casefold() not in _FILLERS
    ]
    return " ".join(tokens)


def cleanup_volume(volume: dict) -> dict:
    """Turn completed volume JSON into a raw part-list record."""
    speech = [
        {
            "start": span["start"],
            "end": span["end"],
            "text": _strip_fillers(span["text"]),
        }
        for span in volume.get("segments") or []
    ]
    speech.sort(key=lambda span: span["start"])
    chapters = [
        chapter
        for chapter in volume.get("chapters") or []
        if str(chapter.get("title") or "").strip()
    ]
    if len(chapters) >= 2:
        if any(_joined_chapter_speech(chapter) is not None for chapter in chapters):
            parts = _parts_from_chapter_speech(chapters)
        else:
            parts = _nest_under_chapters(chapters, speech)
        recording_title = ""
    else:
        parts = [_untitled_part(speech)]
        recording_title = ""
        if len(chapters) == 1 and _covers_whole_recording(chapters[0], speech):
            recording_title = chapters[0]["title"]
    return {
        "video_file": volume.get("video_file"),
        "recording_title": recording_title,
        "parts": parts,
    }


def _joined_chapter_speech(chapter: dict) -> str | None:
    cleaned = chapter.get("transcript_cleaned")
    if isinstance(cleaned, str):
        return cleaned
    raw = chapter.get("transcript_raw")
    if isinstance(raw, str):
        return raw
    return None


def _parts_from_chapter_speech(chapters: list[dict]) -> list[dict]:
    ordered = sorted(chapters, key=lambda chapter: chapter["start"])
    return [
        {
            "title": chapter["title"],
            "start": chapter["start"],
            "end": chapter["end"],
            "speech": _speech_from_joined(chapter, _joined_chapter_speech(chapter) or ""),
        }
        for chapter in ordered
    ]


def _speech_from_joined(chapter: dict, joined: str) -> list[dict]:
    text = joined.strip()
    if not text:
        return []
    matches = list(_SPAN_PREFIX.finditer(text))
    if not matches:
        return [
            {
                "start": chapter["start"],
                "end": chapter["end"],
                "text": text,
            }
        ]
    spans = []
    for index, match in enumerate(matches):
        start = float(match.group(1))
        chunk_end = (
            matches[index + 1].start() if index + 1 < len(matches) else len(text)
        )
        chunk = text[match.end() : chunk_end].strip()
        if not chunk:
            continue
        if index + 1 < len(matches):
            end = float(matches[index + 1].group(1))
        else:
            end = chapter["end"]
        if end < start:
            end = start
        spans.append({"start": start, "end": end, "text": chunk})
    return spans


def _untitled_part(speech: list[dict]) -> dict:
    if speech:
        start = speech[0]["start"]
        end = speech[-1]["end"]
    else:
        start = 0.0
        end = 0.0
    return {"title": "", "start": start, "end": end, "speech": speech}


def _nest_under_chapters(chapters: list[dict], speech: list[dict]) -> list[dict]:
    ordered = sorted(chapters, key=lambda chapter: chapter["start"])
    chapter_parts = [
        {
            "title": chapter["title"],
            "start": chapter["start"],
            "end": chapter["end"],
            "speech": [],
        }
        for chapter in ordered
    ]
    untitled_runs: list[list[dict]] = []
    current_run: list[dict] = []
    for span in speech:
        chapter = _chapter_containing(span["start"], ordered)
        if chapter is None:
            current_run.append(span)
            continue
        if current_run:
            untitled_runs.append(current_run)
            current_run = []
        index = ordered.index(chapter)
        chapter_parts[index]["speech"].append(span)
    if current_run:
        untitled_runs.append(current_run)
    untitled_parts = [
        {
            "title": "",
            "start": run[0]["start"],
            "end": run[-1]["end"],
            "speech": run,
        }
        for run in untitled_runs
    ]
    return sorted(
        chapter_parts + untitled_parts,
        key=lambda part: (part["start"], part["title"] != ""),
    )


def _chapter_containing(span_start: float, chapters: list[dict]) -> dict | None:
    containing = [
        chapter
        for chapter in chapters
        if chapter["start"] <= span_start <= chapter["end"]
    ]
    if not containing:
        return None
    return max(containing, key=lambda chapter: chapter["start"])


def _covers_whole_recording(chapter: dict, speech: list[dict]) -> bool:
    if not speech:
        return chapter["start"] <= 0.0
    return chapter["start"] <= speech[0]["start"] and chapter["end"] >= speech[-1]["end"]
