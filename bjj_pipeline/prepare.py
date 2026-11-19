"""Nest raw chapter speech and fill LLM-pared keys on a transcribed volume JSON.

``--llm`` sends one full chapter plus the markdown prepare spec to chat
completion. Skip a chapter that already has ``transcript_cleaned``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from functools import lru_cache
from pathlib import Path
from typing import Callable, TextIO

from .batch_panoscribe import (
    TranscriptError,
    _atomic_write_json,
    inspect_transcript,
    output_path_for,
    walk_videos,
)

SEASON_FOLDER = re.compile(r"^Season\s*(\d+)$", re.IGNORECASE)
_BY = re.compile(r"\s+by\s+", re.IGNORECASE)

Completer = Callable[[str], str]

DEFAULT_LLM_BASE_URL = "https://api.x.ai/v1"
DEFAULT_LLM_MODEL = "grok-4.3"
DEFAULT_REASONING_EFFORT = "low"
PROMPT_PATH = Path(__file__).resolve().parents[1] / "docs" / "prepare-llm-prompt.md"

TECHNIQUE_STRINGS = (
    "named_move",
    "ruleset",
    "move_type",
    "start_occupancy",
    "start_position",
    "end_occupancy",
    "end_position",
    "technique_steps",
    "main_ideas",
)
TECHNIQUE_LISTS = ("source_time_ranges", "suggested_tags")


def prepare_volume(
    json_path: Path,
    corpus_root: Path,
    video_library_root: Path | None = None,
    completer: Completer | None = None,
    *,
    force: bool = False,
) -> int:
    """Rewrite ``json_path`` with nested raw speech and, when possible, pared keys.

    Returns 0 on nest success (and model success when ``completer`` is set).
    Returns 1 when nesting ran but the model half failed.
    """
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return 0
    chapters = payload.get("chapters")
    raw_segments = payload.get("segments")
    has_segments = isinstance(raw_segments, list)
    segments = raw_segments if has_segments else []
    if has_segments:
        if not _eligible_chapters(chapters, segments):
            return 0
    elif not _eligible_nested(chapters):
        return 0

    instructional = _instructional_name(json_path, corpus_root)
    instructor = _instructor(instructional, video_library_root)
    volume = payload.get("video_file")
    if not isinstance(volume, str):
        volume = ""

    model_ok = True
    nested: list = []
    for index, chapter in enumerate(chapters):
        if not isinstance(chapter, dict):
            nested.append(chapter)
            continue
        previous = chapters[index - 1].get("title", "") if index > 0 else ""
        next_title = chapters[index + 1].get("title", "") if index + 1 < len(chapters) else ""
        if not isinstance(previous, str):
            previous = ""
        if not isinstance(next_title, str):
            next_title = ""
        updated = dict(chapter)
        updated["instructor"] = instructor
        updated["instructional"] = instructional
        updated["volume"] = volume
        updated["previous_chapter"] = previous
        updated["next_chapter"] = next_title
        if has_segments:
            overlapping = _overlapping_spans(chapter, segments)
            updated["transcript_raw"] = _join_raw(overlapping)
        else:
            existing_raw = updated.get("transcript_raw")
            if not isinstance(existing_raw, str):
                updated["transcript_raw"] = ""
        if completer is not None:
            raw = updated.get("transcript_raw")
            raw_text = raw if isinstance(raw, str) else ""
            already = isinstance(updated.get("transcript_cleaned"), str)
            if raw_text.strip() and (force or not already):
                try:
                    parsed = _enrich_chapter(updated, completer)
                except Exception:
                    model_ok = False
                else:
                    updated["transcript_cleaned"] = parsed["transcript_cleaned"]
                    updated["techniques"] = parsed["techniques"]
        nested.append(updated)
    payload["chapters"] = nested
    payload.pop("segments", None)
    _atomic_write_json(json_path, payload)
    return 0 if model_ok else 1


def complete_chat(
    prompt: str,
    *,
    urlopen=None,
    timeout: float = 600,
) -> str:
    """POST an OpenAI-compatible chat completion via stdlib urllib."""
    opener = urllib.request.urlopen if urlopen is None else urlopen
    base = os.environ.get("BJJ_LLM_BASE_URL", DEFAULT_LLM_BASE_URL).rstrip("/")
    model = os.environ.get("BJJ_LLM_MODEL", DEFAULT_LLM_MODEL)
    spec = _llm_spec()
    user = prompt
    stripped = spec.strip()
    if prompt.startswith(stripped):
        user = prompt[len(stripped) :].lstrip()
    url = f"{base}/chat/completions"
    body = json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": spec},
                {"role": "user", "content": user},
            ],
            "temperature": 0,
            "reasoning_effort": DEFAULT_REASONING_EFFORT,
            "response_format": {"type": "json_object"},
        }
    ).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    key = os.environ.get("XAI_API_KEY", "")
    if key:
        headers["Authorization"] = f"Bearer {key}"
    request = urllib.request.Request(
        url,
        data=body,
        headers=headers,
        method="POST",
    )
    with opener(request, timeout=timeout) as resp:
        raw = resp.read()
    if isinstance(raw, bytes):
        payload = json.loads(raw.decode("utf-8"))
    else:
        payload = json.loads(raw)
    content = payload["choices"][0]["message"]["content"]
    if not isinstance(content, str):
        raise ValueError("empty completion")
    return content


def _real_chapters(chapters: list) -> list:
    return [
        chapter
        for chapter in chapters
        if isinstance(chapter, dict) and str(chapter.get("title") or "").strip()
    ]


def _eligible_chapters(chapters, segments: list) -> bool:
    if not isinstance(chapters, list) or not chapters:
        return False
    if len(_real_chapters(chapters)) < 2:
        return False
    if _covers_whole_recording(chapters, segments):
        return False
    return True


def _eligible_nested(chapters) -> bool:
    if not isinstance(chapters, list):
        return False
    real = _real_chapters(chapters)
    if len(real) < 2:
        return False
    return all(isinstance(chapter.get("transcript_raw"), str) for chapter in real)


def prepare_eligible(output: Path) -> bool:
    try:
        _data, info = inspect_transcript(output)
    except TranscriptError:
        return False
    chapters = info["chapters"]
    if info["segments_present"] and isinstance(info["segments"], list):
        return _eligible_chapters(chapters, info["segments"])
    return _eligible_nested(chapters)


def _chapter_needs_llm(chapter: dict) -> bool:
    raw = chapter.get("transcript_raw")
    if not isinstance(raw, str) or not raw.strip():
        return False
    return not isinstance(chapter.get("transcript_cleaned"), str)


def prepare_done(output: Path, *, llm: bool = False) -> bool:
    try:
        _data, info = inspect_transcript(output)
    except TranscriptError:
        return False
    chapters = info["chapters"]
    if not isinstance(chapters, list) or not chapters:
        return False
    real = _real_chapters(chapters)
    if not real:
        return False
    nested = all(isinstance(chapter.get("transcript_raw"), str) for chapter in real)
    if not nested:
        return False
    if llm:
        return not any(_chapter_needs_llm(chapter) for chapter in real)
    return True


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


def _overlapping_spans(chapter: dict, segments: list) -> list[dict]:
    overlapping = [
        span
        for span in segments
        if isinstance(span, dict) and "start" in span and "end" in span and _overlaps(span, chapter)
    ]
    overlapping.sort(key=lambda span: span["start"])
    return overlapping


def _join_raw(spans: list[dict]) -> str:
    parts = [
        f"<{span['start']:.2f}> {str(span.get('text') or '').strip()}"
        for span in spans
    ]
    return " ".join(parts)


@lru_cache(maxsize=1)
def _llm_spec() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def _chapter_user_message(chapter: dict) -> str:
    title = chapter.get("title", "")
    if not isinstance(title, str):
        title = ""
    return "\n".join(
        [
            f"instructor: {chapter.get('instructor', '')}",
            f"instructional: {chapter.get('instructional', '')}",
            f"volume: {chapter.get('volume', '')}",
            f"chapter: {title}",
            f"previous_chapter: {chapter.get('previous_chapter', '')}",
            f"next_chapter: {chapter.get('next_chapter', '')}",
            "",
            "Chapter speech:",
            "",
            str(chapter.get("transcript_raw") or ""),
        ]
    )


def _llm_prompt(chapter: dict) -> str:
    return _llm_spec().rstrip() + "\n\n" + _chapter_user_message(chapter)


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _normalize_technique(raw: object) -> dict | None:
    if not isinstance(raw, dict):
        return None
    technique: dict = {}
    for field in TECHNIQUE_STRINGS:
        value = raw.get(field, "")
        technique[field] = value if isinstance(value, str) else ""
    for field in TECHNIQUE_LISTS:
        technique[field] = _string_list(raw.get(field))
    return technique


def _parse_completion(text: str) -> dict:
    if not isinstance(text, str) or not text.strip():
        raise ValueError("empty completion")
    blob = text.strip()
    if blob.startswith("```"):
        blob = blob.split("\n", 1)[-1]
        fence = blob.rfind("```")
        if fence >= 0:
            blob = blob[:fence]
        blob = blob.strip()
        if blob.lower().startswith("json"):
            blob = blob[4:].strip()
    start = blob.find("{")
    end = blob.rfind("}")
    if start < 0 or end < start:
        raise ValueError("no json")
    data = json.loads(blob[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("not object")
    cleaned = data.get("transcript_cleaned")
    if not isinstance(cleaned, str):
        raise ValueError("no cleaned")
    raw_techniques = data.get("techniques")
    if not isinstance(raw_techniques, list):
        raise ValueError("bad techniques")
    techniques = []
    for item in raw_techniques:
        technique = _normalize_technique(item)
        if technique is not None:
            techniques.append(technique)
    return {"transcript_cleaned": cleaned, "techniques": techniques}


def _enrich_chapter(chapter: dict, completer: Completer) -> dict:
    return _parse_completion(completer(_llm_prompt(chapter)))


def _print(stdout: TextIO, status: str, name: str, reason: str = "") -> None:
    line = f"{status:<4}  {'prepare':<10}  {name}"
    if reason:
        line += f"  ({reason})"
    stdout.write(line + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Walk transcribed volumes and nest chapter speech. Skip finished "
            "volumes; --force re-runs. --llm also fills transcript_cleaned."
        )
    )
    parser.add_argument("--library", type=Path, required=True, help="Root of instructional folders.")
    parser.add_argument("--corpus", type=Path, required=True, help="Root for transcript JSON.")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-run prepare even when the skip artifact already exists.",
    )
    parser.add_argument(
        "--llm",
        action="store_true",
        help="Call Grok 4.3 to fill transcript_cleaned and techniques.",
    )
    return parser


def run(
    library: Path,
    corpus: Path,
    *,
    force: bool = False,
    llm: bool = False,
    completer: Completer | None = None,
    stdout: TextIO | None = None,
) -> int:
    library = Path(library)
    corpus = Path(corpus)
    stdout = stdout if stdout is not None else sys.stdout
    if llm:
        completer_fn = complete_chat if completer is None else completer
    else:
        completer_fn = None
    failed = False
    for video in walk_videos(library):
        output = output_path_for(video, library, corpus)
        try:
            label = str(video.relative_to(library))
        except ValueError:
            label = str(video)
        if not prepare_eligible(output):
            _print(stdout, "SKIP", label)
            continue
        if prepare_done(output, llm=llm) and not force:
            _print(stdout, "SKIP", label)
            continue
        try:
            code = prepare_volume(
                output, corpus, library, completer=completer_fn, force=force
            )
        except Exception as exc:  # noqa: BLE001
            _print(stdout, "FAIL", label, str(exc))
            failed = True
        else:
            if code:
                _print(stdout, "FAIL", label, "model half")
                failed = True
            else:
                _print(stdout, "RUN", label)
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return run(args.library, args.corpus, force=args.force, llm=args.llm)


if __name__ == "__main__":
    sys.exit(main())
