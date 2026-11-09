"""Nest raw chapter speech and fill LLM-pared keys on a transcribed volume JSON.

Long chapters are split on Whisper span boundaries into windows of
``WINDOW_SPAN_COUNT`` spans that overlap by ``WINDOW_OVERLAP_SPANS`` span.
"""

from __future__ import annotations

import json
import os
import re
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Callable

from .batch_panoscribe import _atomic_write_json

SEASON_FOLDER = re.compile(r"^Season\s*(\d+)$", re.IGNORECASE)
_BY = re.compile(r"\s+by\s+", re.IGNORECASE)
_TOKEN = re.compile(r"[a-z0-9]+")
_STOP = frozenset(
    {"the", "a", "an", "of", "and", "to", "in", "on", "for", "with", "from", "vs"}
)

Completer = Callable[[str], str]

WINDOW_SPAN_COUNT = 4
WINDOW_OVERLAP_SPANS = 1
DEFAULT_LLM_BASE_URL = "http://localhost:11434/v1"
# Official Ollama 4B tag. Operators set BJJ_LLM_MODEL=qwen3:4b-instruct if missing.
DEFAULT_LLM_MODEL = "qwen3.5:4b"
SEED_PATH = Path(__file__).resolve().parents[1] / "docs" / "enrichment-seed" / "seed.json"

OCCUPANCY = ("top", "bottom", "neutral")
RULESETS = ("gi", "no-gi", "both")
HOP_FIELDS = (
    "start_position",
    "start_occupancy",
    "move_type",
    "end",
    "end_occupancy",
    "named_move",
    "ruleset",
)


def prepare_volume(
    json_path: Path,
    corpus_root: Path,
    video_library_root: Path | None = None,
    completer: Completer | None = None,
) -> int:
    """Rewrite ``json_path`` with nested raw speech and, when possible, pared keys.

    Returns 0 on nest success (and model success when ``completer`` is set).
    Returns 1 when nesting ran but the model half failed.
    """
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return 0
    chapters = payload.get("chapters")
    segments = payload.get("segments")
    if not isinstance(segments, list):
        segments = []
    if not _eligible_chapters(chapters, segments):
        return 0

    instructional = _instructional_name(json_path, corpus_root)
    instructor = _instructor(instructional, video_library_root)
    volume = payload.get("video_file")
    if not isinstance(volume, str):
        volume = ""

    vocab = _seed_vocab() if completer is not None else None
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
        overlapping = _overlapping_spans(chapter, segments)
        updated["transcript_raw"] = _join_raw(overlapping)
        if completer is not None and vocab is not None:
            try:
                cleaned, tags = _pare_chapter(updated, overlapping, completer, vocab)
            except Exception:
                model_ok = False
            else:
                updated["transcript_cleaned"] = cleaned
                updated["suggested_tags"] = tags
        nested.append(updated)
    payload["chapters"] = nested
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
    url = f"{base}/chat/completions"
    body = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "reasoning_effort": "none",
            "response_format": {"type": "json_object"},
            "options": {"num_ctx": 2048},
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
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


def _transcript_raw(chapter: dict, segments: list) -> str:
    return _join_raw(_overlapping_spans(chapter, segments))


def _seed_vocab() -> dict:
    seed = json.loads(SEED_PATH.read_text(encoding="utf-8"))
    move_types = [item["id"] for item in seed.get("move_types") or [] if item.get("id")]
    start_ids = [item["id"] for item in seed.get("starting_positions") or [] if item.get("id")]
    endings = seed.get("ending_positions_or_submissions") or []
    end_ids = [item["id"] for item in endings if item.get("id")]
    submission_ids = {
        item["id"]
        for item in endings
        if item.get("kind") == "submission" and item.get("id")
    }
    named: list[str] = []
    seen: set[str] = set()
    for path in seed.get("paths") or []:
        for leaf in path.get("leaves") or []:
            name = leaf.get("name")
            if isinstance(name, str) and name not in seen:
                seen.add(name)
                named.append(name)
    hints: list[str] = []
    hint_seen: set[str] = set()

    def add_hints(item: dict) -> None:
        for ref in item.get("cross_refs") or []:
            if isinstance(ref, dict):
                name = ref.get("name")
                if isinstance(name, str) and name not in hint_seen:
                    hint_seen.add(name)
                    hints.append(name)

    for item in seed.get("starting_positions") or []:
        add_hints(item)
    for item in endings:
        add_hints(item)
    for path in seed.get("paths") or []:
        for leaf in path.get("leaves") or []:
            add_hints(leaf)
    return {
        "move_types": move_types,
        "start_ids": start_ids,
        "end_ids": end_ids,
        "submission_ids": submission_ids,
        "named_moves": named,
        "hints": hints,
        "start_labels": {
            item["id"]: item.get("label") or item["id"]
            for item in seed.get("starting_positions") or []
            if item.get("id")
        },
        "end_labels": {
            item["id"]: item.get("label") or item["id"]
            for item in endings
            if item.get("id")
        },
        "move_labels": {
            item["id"]: item.get("label") or item["id"]
            for item in seed.get("move_types") or []
            if item.get("id")
        },
    }


def _title_tokens(*titles: str) -> set[str]:
    tokens: set[str] = set()
    for title in titles:
        if not isinstance(title, str):
            continue
        for tok in _TOKEN.findall(title.lower()):
            if len(tok) >= 3 and tok not in _STOP:
                tokens.add(tok)
    return tokens


def _filter_named_moves(names: list[str], tokens: set[str]) -> list[str]:
    if not tokens:
        return list(names)
    matched = [name for name in names if any(tok in name.lower() for tok in tokens)]
    if len(matched) < 5:
        return list(names)
    return matched


def _span_windows(spans: list[dict]) -> list[list[dict]]:
    if len(spans) <= WINDOW_SPAN_COUNT:
        return [spans]
    windows: list[list[dict]] = []
    start = 0
    step = WINDOW_SPAN_COUNT - WINDOW_OVERLAP_SPANS
    while start < len(spans):
        end = min(start + WINDOW_SPAN_COUNT, len(spans))
        windows.append(spans[start:end])
        if end >= len(spans):
            break
        start += step
    return windows


def _build_prompt(
    chapter: dict,
    raw: str,
    vocab: dict,
    named_moves: list[str],
    *,
    context: str = "",
) -> str:
    move_lines = [
        f"- {move_id} ({vocab['move_labels'].get(move_id, move_id)})"
        for move_id in vocab["move_types"]
    ]
    start_lines = [
        f"- {start_id} ({vocab['start_labels'].get(start_id, start_id)})"
        for start_id in vocab["start_ids"]
    ]
    end_lines = [
        f"- {end_id} ({vocab['end_labels'].get(end_id, end_id)})"
        for end_id in vocab["end_ids"]
    ]
    named_lines = [f"- {name}" for name in named_moves]
    speech_lines = (
        ["Context (do not repeat):", context, "", "Pare only this speech:", raw]
        if context
        else ["Chapter speech:", raw]
    )
    return "\n".join(
        [
            "Pare filler, false starts, idioms, and empty turns of phrase from the chapter speech.",
            "Keep chapter titles and names already used in this volume's speech, including instructor names.",
            "Repair mistranscribed grappling words using the chapter titles and the allow-list.",
            "Add (inside …) or (outside …) from context without replacing an inside/outside word already spoken.",
            "Inside is toward the primary body connection; outside is away from it.",
            "Occupancy is top, bottom, or neutral (neutral is standing or clinch).",
            "Return JSON only with keys transcript_cleaned (string) and suggested_tags (array of hop objects).",
            "Each hop object: start_position, start_occupancy, move_type, end, end_occupancy, named_move, ruleset.",
            "Use only allow-list ids and named-move names. No system field. Do not store family.",
            "end_occupancy must be an empty string when end is a submission.",
            "ruleset is gi, no-gi, or both.",
            "suggested_tags is [] when nothing fits. Do not use strings in suggested_tags.",
            "",
            f"instructor: {chapter.get('instructor', '')}",
            f"instructional: {chapter.get('instructional', '')}",
            f"volume: {chapter.get('volume', '')}",
            f"chapter: {chapter.get('title', '')}",
            f"previous_chapter: {chapter.get('previous_chapter', '')}",
            f"next_chapter: {chapter.get('next_chapter', '')}",
            "",
            "Occupancy: top, bottom, neutral",
            "Types of move:",
            *move_lines,
            "",
            "Start positions (id):",
            *start_lines,
            "",
            "Ends (id):",
            *end_lines,
            "",
            "NAMED_MOVES:",
            *named_lines,
            "END_NAMED_MOVES",
            "",
            f"Repair hints (judo/wrestling names, not hop ids): {', '.join(vocab['hints'])}",
            "",
            *speech_lines,
            "",
            "Return JSON only. suggested_tags is an array of hop objects, not strings.",
        ]
    )


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
    tags = data.get("suggested_tags", [])
    if not isinstance(tags, list):
        raise ValueError("bad tags")
    return {"transcript_cleaned": cleaned, "suggested_tags": tags}


def _clean_hop(raw: object, vocab: dict, named: set[str]) -> dict | None:
    if not isinstance(raw, dict):
        return None
    hop = {}
    for field in HOP_FIELDS:
        value = raw.get(field, "")
        hop[field] = value if isinstance(value, str) else ""
    if hop["start_occupancy"] not in OCCUPANCY:
        return None
    if hop["move_type"] not in vocab["move_types"]:
        return None
    if hop["start_position"] not in vocab["start_ids"]:
        return None
    if hop["end"] not in vocab["end_ids"]:
        return None
    if hop["named_move"] not in named:
        return None
    if hop["ruleset"] not in RULESETS:
        return None
    if hop["end"] in vocab["submission_ids"]:
        if hop["end_occupancy"] != "":
            return None
    elif hop["end_occupancy"] not in OCCUPANCY:
        return None
    return hop


def _merge_hops(hops: list[dict]) -> list[dict]:
    seen: set[tuple] = set()
    merged: list[dict] = []
    for hop in hops:
        key = tuple(hop[field] for field in HOP_FIELDS)
        if key in seen:
            continue
        seen.add(key)
        merged.append(hop)
    return merged


def _pare_chapter(
    chapter: dict,
    spans: list[dict],
    completer: Completer,
    vocab: dict,
) -> tuple[str, list[dict]]:
    named = _filter_named_moves(
        vocab["named_moves"],
        _title_tokens(
            str(chapter.get("title") or ""),
            str(chapter.get("previous_chapter") or ""),
            str(chapter.get("next_chapter") or ""),
        ),
    )
    named_set = set(named)
    texts: list[str] = []
    hops: list[dict] = []
    for index, window in enumerate(_span_windows(spans)):
        if index == 0:
            prompt = _build_prompt(chapter, _join_raw(window), vocab, named)
        else:
            overlap = window[:WINDOW_OVERLAP_SPANS]
            rest = window[WINDOW_OVERLAP_SPANS:]
            prompt = _build_prompt(
                chapter,
                _join_raw(rest),
                vocab,
                named,
                context=_join_raw(overlap),
            )
        parsed = _parse_completion(completer(prompt))
        texts.append(parsed["transcript_cleaned"])
        for hop in parsed["suggested_tags"]:
            cleaned = _clean_hop(hop, vocab, named_set)
            if cleaned is not None:
                hops.append(cleaned)
    return " ".join(texts), _merge_hops(hops)
