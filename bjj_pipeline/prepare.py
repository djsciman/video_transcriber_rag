"""Nest raw chapter speech and fill LLM-pared keys on a transcribed volume JSON.

Default ``--llm`` is staged: two Completer calls per chapter on the same
model (cleanup then extract). ``--method one-call`` keeps the combined spec.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
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

DEFAULT_LLM_PROVIDER = "xai"
DEFAULT_LLM_BASE_URL = "https://api.x.ai/v1"
DEFAULT_LLM_MODEL = "grok-4.3"
DEFAULT_REASONING_EFFORT = "low"
DEFAULT_LLM_METHOD = "staged"
DEFAULT_ANTHROPIC_VERSION = "2023-06-01"
PROMPT_PATH = Path(__file__).resolve().parents[1] / "docs" / "prepare-llm-prompt.md"
CLEANUP_PROMPT_PATH = (
    Path(__file__).resolve().parents[1] / "docs" / "prepare-llm-cleanup.md"
)
EXTRACT_PROMPT_PATH = (
    Path(__file__).resolve().parents[1] / "docs" / "prepare-llm-extract.md"
)
LLM_METHODS = ("one-call", "staged")
CLEANUP_SPEC_MAX_CHARS = 8000
EXTRACT_SPEC_MAX_CHARS = 16000

LLM_PROVIDERS = {
    "xai": {
        "kind": "openai",
        "base_url": "https://api.x.ai/v1",
        "model": "grok-4.3",
        "key_env": "XAI_API_KEY",
        "reasoning_effort": "low",
    },
    "openai": {
        "kind": "openai",
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-5.4-mini",
        "key_env": "OPENAI_API_KEY",
        "reasoning_effort": None,
    },
    "anthropic": {
        "kind": "anthropic",
        "base_url": "https://api.anthropic.com",
        "model": "claude-haiku-5-5",
        "key_env": "ANTHROPIC_API_KEY",
        "reasoning_effort": None,
        "max_tokens": 16384,
    },
}
LLM_PROVIDER_ALIASES = {
    "grok": "xai",
    "gpt": "openai",
    "claude": "anthropic",
}

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
_TAG_SPLIT = re.compile(r"[.?!;,]")
_TAG_STOPWORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "but",
        "if",
        "then",
        "so",
        "as",
        "at",
        "by",
        "for",
        "from",
        "in",
        "into",
        "of",
        "on",
        "onto",
        "to",
        "with",
        "without",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "it",
        "its",
        "this",
        "that",
        "these",
        "those",
        "you",
        "your",
        "we",
        "our",
        "he",
        "she",
        "they",
        "them",
        "his",
        "her",
        "their",
        "not",
        "no",
        "do",
        "does",
        "did",
        "can",
        "could",
        "should",
        "must",
        "will",
        "when",
        "while",
        "after",
        "before",
        "over",
        "under",
        "up",
        "down",
        "out",
        "off",
        "about",
        "just",
        "also",
        "very",
        "more",
        "most",
        "than",
    }
)


def prepare_volume(
    json_path: Path,
    corpus_root: Path,
    video_library_root: Path | None = None,
    completer: Completer | None = None,
    *,
    cleaner: Completer | None = None,
    extractor: Completer | None = None,
    force: bool = False,
    max_llm_calls: int | None = None,
    extracted_index=None,
) -> int:
    """Rewrite ``json_path`` with nested raw speech and, when possible, pared keys.

    Returns 0 on nest success (and model success when a Completer is set).
    Returns 1 when nesting ran but the model half failed.
    """
    if completer is not None and (cleaner is not None or extractor is not None):
        raise ValueError("do not pass completer with cleaner/extractor")
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
    llm_calls = 0
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
            already = _chapter_has_llm(updated)
            if raw_text.strip() and (force or not already):
                if max_llm_calls is not None and llm_calls >= max_llm_calls:
                    nested.append(updated)
                    continue
                llm_calls += 1
                try:
                    parsed = _enrich_chapter(updated, completer)
                except Exception:
                    model_ok = False
                else:
                    updated["transcript_cleaned"] = parsed["transcript_cleaned"]
                    updated["concepts"] = parsed["concepts"]
                    updated["suggested_tags"] = parsed["suggested_tags"]
                    updated["techniques"] = parsed["techniques"]
        elif cleaner is not None or extractor is not None:
            ok, llm_calls = _enrich_staged(
                updated,
                cleaner=cleaner,
                extractor=extractor,
                force=force,
                max_llm_calls=max_llm_calls,
                llm_calls=llm_calls,
            )
            if not ok:
                model_ok = False
        nested.append(updated)
    payload["chapters"] = nested
    payload.pop("segments", None)
    _atomic_write_json(json_path, payload)
    index, owned = _resolve_extracted_index(extracted_index)
    try:
        if index is not None:
            _upsert_prepared_volume(payload, json_path, corpus_root, index)
    finally:
        if owned and index is not None:
            index.close()
    return 0 if model_ok else 1


def _corpus_relative_json(json_path: Path, corpus_root: Path) -> str:
    try:
        return json_path.resolve().relative_to(Path(corpus_root).resolve()).as_posix()
    except ValueError:
        return json_path.name


def ingest_prepared_corpus(corpus_root: Path, extracted_index) -> None:
    """Upsert techniques and concepts already on prepared volume JSON."""
    corpus_root = Path(corpus_root)
    for json_path in sorted(corpus_root.rglob("*.json")):
        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(payload, dict):
            _upsert_prepared_volume(payload, json_path, corpus_root, extracted_index)


def _chapter_credit(chapters: list, key: str) -> str:
    for chapter in chapters:
        if not isinstance(chapter, dict):
            continue
        value = chapter.get(key)
        if isinstance(value, str) and value:
            return value
    return ""


def _resolve_extracted_index(extracted_index):
    if extracted_index is not None:
        return extracted_index, False
    from coach_app.settings import extracted_index_path

    location = extracted_index_path()
    if location is None:
        return None, False
    from coach_app.extracted_index import ExtractedIndex

    return ExtractedIndex.open(location), True


def _upsert_prepared_volume(
    payload: dict, json_path: Path, corpus_root: Path, extracted_index
) -> None:
    chapters = payload.get("chapters")
    if not isinstance(chapters, list):
        return
    video_file = payload.get("video_file")
    volume = {
        "video_file": video_file if isinstance(video_file, str) else "",
        "instructor": _chapter_credit(chapters, "instructor"),
        "instructional": _chapter_credit(chapters, "instructional"),
    }
    rel = _corpus_relative_json(json_path, corpus_root)
    for chapter in chapters:
        if isinstance(chapter, dict):
            extracted_index.ingest_chapter(volume, chapter, corpus_json_path=rel)


def resolve_llm_provider(name: str | None = None) -> str:
    raw = (name or os.environ.get("BJJ_LLM_PROVIDER") or DEFAULT_LLM_PROVIDER).strip().lower()
    resolved = LLM_PROVIDER_ALIASES.get(raw, raw)
    if resolved not in LLM_PROVIDERS:
        allowed = ", ".join(sorted(LLM_PROVIDERS))
        raise ValueError(f"unknown llm provider {raw!r}; choose one of: {allowed}")
    return resolved


def _read_json(opener, request: urllib.request.Request, timeout: float) -> dict:
    try:
        with opener(request, timeout=timeout) as resp:
            raw = resp.read()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") if exc.fp or hasattr(exc, "read") else ""
        snippet = detail.strip().replace("\n", " ")[:400]
        raise RuntimeError(f"HTTP {exc.code} {snippet}".strip()) from exc
    if isinstance(raw, bytes):
        return json.loads(raw.decode("utf-8"))
    return json.loads(raw)


def make_completer(
    provider: str | None = None,
    model: str | None = None,
    *,
    spec: str | None = None,
    reasoning_effort: str | None = None,
) -> Completer:
    def completer(prompt: str) -> str:
        return complete_chat(
            prompt,
            provider=provider,
            model=model,
            spec=spec,
            reasoning_effort=reasoning_effort,
        )

    return completer


def complete_chat(
    prompt: str,
    *,
    provider: str | None = None,
    model: str | None = None,
    spec: str | None = None,
    reasoning_effort: str | None = None,
    urlopen=None,
    timeout: float = 600,
) -> str:
    """POST a chat completion to xAI, OpenAI, or Anthropic via stdlib urllib."""
    opener = urllib.request.urlopen if urlopen is None else urlopen
    name = resolve_llm_provider(provider)
    cfg = LLM_PROVIDERS[name]
    spec_text = _llm_spec() if spec is None else spec
    user = prompt
    stripped = spec_text.strip()
    if stripped and prompt.startswith(stripped):
        user = prompt[len(stripped) :].lstrip()
    chosen_model = model or os.environ.get("BJJ_LLM_MODEL") or cfg["model"]
    if cfg["kind"] == "anthropic":
        return _complete_anthropic(
            user,
            spec=spec_text,
            model=chosen_model,
            cfg=cfg,
            opener=opener,
            timeout=timeout,
        )
    return _complete_openai_compat(
        user,
        spec=spec_text,
        model=chosen_model,
        cfg=cfg,
        opener=opener,
        timeout=timeout,
        reasoning_effort=reasoning_effort,
    )


def _complete_openai_compat(
    user: str,
    *,
    spec: str,
    model: str,
    cfg: dict,
    opener,
    timeout: float,
    reasoning_effort: str | None = None,
) -> str:
    base = os.environ.get("BJJ_LLM_BASE_URL", cfg["base_url"]).rstrip("/")
    url = f"{base}/chat/completions"
    payload: dict = {
        "model": model,
        "messages": [
            {"role": "system", "content": spec},
            {"role": "user", "content": user},
        ],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    default_effort = cfg.get("reasoning_effort")
    if default_effort:
        payload["reasoning_effort"] = reasoning_effort or default_effort
    body = json.dumps(payload).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    key = os.environ.get(cfg["key_env"], "")
    if key:
        headers["Authorization"] = f"Bearer {key}"
    request = urllib.request.Request(
        url,
        data=body,
        headers=headers,
        method="POST",
    )
    data = _read_json(opener, request, timeout)
    content = data["choices"][0]["message"]["content"]
    if not isinstance(content, str):
        raise ValueError("empty completion")
    return content


def _complete_anthropic(
    user: str,
    *,
    spec: str,
    model: str,
    cfg: dict,
    opener,
    timeout: float,
) -> str:
    base = os.environ.get("BJJ_LLM_BASE_URL", cfg["base_url"]).rstrip("/")
    url = f"{base}/v1/messages"
    payload = {
        "model": model,
        "max_tokens": cfg["max_tokens"],
        "system": spec,
        "messages": [{"role": "user", "content": user}],
        "thinking": {"type": "disabled"},
    }
    body = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "anthropic-version": DEFAULT_ANTHROPIC_VERSION,
    }
    key = os.environ.get(cfg["key_env"], "")
    if key:
        headers["x-api-key"] = key
    request = urllib.request.Request(
        url,
        data=body,
        headers=headers,
        method="POST",
    )
    data = _read_json(opener, request, timeout)
    blocks = data.get("content")
    parts = [
        block.get("text")
        for block in blocks
        if isinstance(block, dict) and block.get("type") == "text" and isinstance(block.get("text"), str)
    ] if isinstance(blocks, list) else []
    text = "".join(parts)
    if not text:
        kinds = [
            block.get("type")
            for block in (blocks or [])
            if isinstance(block, dict)
        ]
        raise ValueError(
            f"empty completion (stop_reason={data.get('stop_reason')!r}, block_types={kinds})"
        )
    return text


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


def _chapter_has_llm(chapter: dict) -> bool:
    return (
        isinstance(chapter.get("transcript_cleaned"), str)
        and isinstance(chapter.get("concepts"), list)
        and isinstance(chapter.get("suggested_tags"), list)
    )


def _chapter_needs_llm(chapter: dict) -> bool:
    raw = chapter.get("transcript_raw")
    if not isinstance(raw, str) or not raw.strip():
        return False
    return not _chapter_has_llm(chapter)


def _chapter_needs_staged(chapter: dict) -> bool:
    raw = chapter.get("transcript_raw")
    if not isinstance(raw, str) or not raw.strip():
        return False
    if not isinstance(chapter.get("transcript_cleaned"), str):
        return True
    return not isinstance(chapter.get("concepts"), list)


def prepare_done(output: Path, *, llm: bool = False, method: str = DEFAULT_LLM_METHOD) -> bool:
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
        needs = _chapter_needs_staged if method == "staged" else _chapter_needs_llm
        return not any(needs(chapter) for chapter in real)
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


@lru_cache(maxsize=1)
def _cleanup_spec() -> str:
    text = CLEANUP_PROMPT_PATH.read_text(encoding="utf-8")
    if len(text) >= CLEANUP_SPEC_MAX_CHARS:
        raise ValueError(
            f"cleanup spec is {len(text)} chars; must be under {CLEANUP_SPEC_MAX_CHARS}"
        )
    return text


@lru_cache(maxsize=1)
def _extract_spec() -> str:
    text = EXTRACT_PROMPT_PATH.read_text(encoding="utf-8")
    if len(text) >= EXTRACT_SPEC_MAX_CHARS:
        raise ValueError(
            f"extract spec is {len(text)} chars; must be under {EXTRACT_SPEC_MAX_CHARS}"
        )
    return text


def _chapter_user_message(chapter: dict, speech_key: str = "transcript_raw") -> str:
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
            str(chapter.get(speech_key) or ""),
        ]
    )


def _llm_prompt(
    chapter: dict,
    spec: str | None = None,
    speech_key: str = "transcript_raw",
) -> str:
    text = _llm_spec() if spec is None else spec
    return text.rstrip() + "\n\n" + _chapter_user_message(chapter, speech_key)


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


def _json_object(text: str) -> dict:
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
    return data


def _parse_completion(text: str) -> dict:
    data = _json_object(text)
    cleaned = data.get("transcript_cleaned")
    if not isinstance(cleaned, str):
        raise ValueError("no cleaned")
    raw_concepts = data.get("concepts")
    if not isinstance(raw_concepts, list):
        raise ValueError("bad concepts")
    concepts = [item for item in raw_concepts if isinstance(item, str)]
    raw_tags = data.get("suggested_tags")
    if not isinstance(raw_tags, list):
        raise ValueError("bad suggested_tags")
    suggested_tags = [item for item in raw_tags if isinstance(item, str)]
    raw_techniques = data.get("techniques")
    if not isinstance(raw_techniques, list):
        raise ValueError("bad techniques")
    techniques = []
    for item in raw_techniques:
        technique = _normalize_technique(item)
        if technique is not None:
            techniques.append(technique)
    return {
        "transcript_cleaned": cleaned,
        "concepts": concepts,
        "suggested_tags": suggested_tags,
        "techniques": techniques,
    }


def _parse_cleanup(text: str) -> str:
    cleaned = _json_object(text).get("transcript_cleaned")
    if not isinstance(cleaned, str):
        raise ValueError("no cleaned")
    return cleaned


def _parse_extract(text: str) -> tuple[list[str], list[dict]]:
    data = _json_object(text)
    raw_concepts = data.get("concepts")
    if not isinstance(raw_concepts, list):
        raise ValueError("bad concepts")
    concepts = [item for item in raw_concepts if isinstance(item, str)]
    raw_techniques = data.get("techniques")
    if not isinstance(raw_techniques, list):
        raise ValueError("bad techniques")
    techniques = []
    for item in raw_techniques:
        technique = _normalize_technique(item)
        if technique is None:
            continue
        technique["suggested_tags"] = _derive_tags(technique.get("main_ideas") or "")
        techniques.append(technique)
    return concepts, techniques


def _derive_tags(source: str | list[str]) -> list[str]:
    if isinstance(source, list):
        texts = [item for item in source if isinstance(item, str)]
    elif isinstance(source, str):
        texts = [source]
    else:
        texts = []
    found: list[str] = []
    seen: set[str] = set()
    for text in texts:
        for part in _TAG_SPLIT.split(text):
            fragment = " ".join(part.split())
            if not fragment:
                continue
            words = fragment.split()
            if len(words) > 8:
                continue
            if all(word.lower().strip("*.,") in _TAG_STOPWORDS for word in words):
                continue
            key = fragment.lower()
            if key in seen:
                continue
            seen.add(key)
            found.append(fragment)
    return found


def _drop_llm_keys(chapter: dict, *, keep_cleaned: bool = False) -> None:
    if not keep_cleaned:
        chapter.pop("transcript_cleaned", None)
    chapter.pop("concepts", None)
    chapter.pop("techniques", None)
    chapter.pop("suggested_tags", None)


def _enrich_staged(
    chapter: dict,
    *,
    cleaner: Completer | None,
    extractor: Completer | None,
    force: bool,
    max_llm_calls: int | None,
    llm_calls: int,
) -> tuple[bool, int]:
    raw = chapter.get("transcript_raw")
    raw_text = raw if isinstance(raw, str) else ""
    if not raw_text.strip():
        return True, llm_calls
    cleaned_ok = isinstance(chapter.get("transcript_cleaned"), str)
    if cleaner is not None and (force or not cleaned_ok):
        if max_llm_calls is None or llm_calls < max_llm_calls:
            llm_calls += 1
            try:
                cleaned = _parse_cleanup(
                    cleaner(_llm_prompt(chapter, spec=_cleanup_spec()))
                )
            except Exception:
                _drop_llm_keys(chapter)
                return False, llm_calls
            chapter["transcript_cleaned"] = cleaned
            _drop_llm_keys(chapter, keep_cleaned=True)
    cleaned_ok = isinstance(chapter.get("transcript_cleaned"), str)
    if extractor is not None and cleaned_ok and (
        force or not isinstance(chapter.get("concepts"), list)
    ):
        if max_llm_calls is None or llm_calls < max_llm_calls:
            llm_calls += 1
            try:
                concepts, techniques = _parse_extract(
                    extractor(
                        _llm_prompt(
                            chapter,
                            spec=_extract_spec(),
                            speech_key="transcript_cleaned",
                        )
                    )
                )
            except Exception:
                _drop_llm_keys(chapter, keep_cleaned=True)
                return False, llm_calls
            chapter["concepts"] = concepts
            chapter["techniques"] = techniques
    if isinstance(chapter.get("concepts"), list):
        chapter["suggested_tags"] = _derive_tags(chapter["concepts"])
    return True, llm_calls


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
            "volumes; --force re-runs. --llm also fills transcript_cleaned, "
            "concepts, suggested_tags, and techniques. Default --method is "
            "staged (cleanup then extract); one-call keeps the combined spec."
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
        help=(
            "Call the chat API to fill transcript_cleaned, concepts, "
            "suggested_tags, and techniques. Default provider is xAI Grok 4.3."
        ),
    )
    parser.add_argument(
        "--method",
        choices=LLM_METHODS,
        default=DEFAULT_LLM_METHOD,
        help=(
            "How --llm calls the model: staged (default, cleanup then extract) "
            "or one-call (combined spec). --provider and --model apply to both."
        ),
    )
    parser.add_argument(
        "--provider",
        choices=sorted(LLM_PROVIDERS),
        default=DEFAULT_LLM_PROVIDER,
        help="Chat vendor for --llm (xai, openai, anthropic). Env: BJJ_LLM_PROVIDER.",
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Override the provider default model. Env: BJJ_LLM_MODEL.",
    )
    parser.add_argument(
        "--extracted-index",
        type=Path,
        default=None,
        help="SQLite extracted index to upsert after prepare writes a volume.",
    )
    return parser


def run(
    library: Path,
    corpus: Path,
    *,
    force: bool = False,
    llm: bool = False,
    method: str = DEFAULT_LLM_METHOD,
    provider: str | None = None,
    model: str | None = None,
    max_llm_calls: int | None = None,
    completer: Completer | None = None,
    cleaner: Completer | None = None,
    extractor: Completer | None = None,
    stdout: TextIO | None = None,
    extracted_index=None,
) -> int:
    library = Path(library)
    corpus = Path(corpus)
    stdout = stdout if stdout is not None else sys.stdout
    extracted_index, owned_index = _resolve_extracted_index(extracted_index)
    try:
        if extracted_index is not None:
            ingest_prepared_corpus(corpus, extracted_index)
        staged = llm and method == "staged"
        completer_fn: Completer | None = None
        cleaner_fn: Completer | None = None
        extractor_fn: Completer | None = None
        if staged:
            cleaner_fn = cleaner or make_completer(
                provider, model, spec=_cleanup_spec(), reasoning_effort="low"
            )
            extractor_fn = extractor or make_completer(
                provider, model, spec=_extract_spec(), reasoning_effort="medium"
            )
        elif llm:
            completer_fn = completer if completer is not None else make_completer(
                provider, model
            )
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
            if prepare_done(output, llm=llm, method=method) and not force:
                _print(stdout, "SKIP", label)
                continue
            try:
                code = prepare_volume(
                    output,
                    corpus,
                    library,
                    completer=completer_fn,
                    cleaner=cleaner_fn,
                    extractor=extractor_fn,
                    force=force,
                    max_llm_calls=max_llm_calls,
                    extracted_index=extracted_index,
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
    finally:
        if owned_index and extracted_index is not None:
            extracted_index.close()


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    index = None
    if args.extracted_index is not None:
        from coach_app.extracted_index import ExtractedIndex

        index = ExtractedIndex.open(args.extracted_index)
    try:
        return run(
            args.library,
            args.corpus,
            force=args.force,
            llm=args.llm,
            method=args.method,
            provider=args.provider,
            model=args.model,
            extracted_index=index,
        )
    finally:
        if index is not None:
            index.close()



if __name__ == "__main__":
    sys.exit(main())
