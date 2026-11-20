"""Reference-free scores for compare-llm chapter pares."""

from __future__ import annotations

import json
import re
from pathlib import Path
from statistics import mean, median
from typing import Sequence

TOKEN = re.compile(r"[a-z0-9']+")
TIMESTAMP = re.compile(r"<\d+\.\d+>")
RANGE = re.compile(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)")
OVERVIEW_TITLE = re.compile(
    r"\b(overview|principle|principles|concept|concepts|introduction|summary|problem|problems)\b",
    re.IGNORECASE,
)


def tokens(text: str) -> list[str]:
    stripped = TIMESTAMP.sub(" ", text or "")
    return TOKEN.findall(stripped.lower())


def token_f1(left: str, right: str) -> float:
    a = set(tokens(left))
    b = set(tokens(right))
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    overlap = len(a & b)
    precision = overlap / len(b)
    recall = overlap / len(a)
    if precision + recall == 0:
        return 0.0
    return 2 * precision * recall / (precision + recall)


def _is_move_title(title: str) -> bool:
    text = (title or "").strip()
    if not text:
        return False
    return OVERVIEW_TITLE.search(text) is None


def _parse_ranges(raw: object) -> list[tuple[float, float]]:
    found: list[tuple[float, float]] = []
    values = raw if isinstance(raw, list) else []
    for item in values:
        if not isinstance(item, str):
            continue
        match = RANGE.fullmatch(item.strip())
        if not match:
            continue
        found.append((float(match.group(1)), float(match.group(2))))
    return found


def score_chapter(chapter: dict) -> dict:
    raw = chapter.get("transcript_raw") if isinstance(chapter.get("transcript_raw"), str) else ""
    cleaned = chapter.get("transcript_cleaned")
    has_cleaned = isinstance(cleaned, str)
    cleaned_text = cleaned if has_cleaned else ""
    raw_tokens = set(tokens(raw))
    cleaned_tokens = set(tokens(cleaned_text))
    cover = (len(raw_tokens & cleaned_tokens) / len(raw_tokens)) if raw_tokens and has_cleaned else 0.0
    novel = (len(cleaned_tokens - raw_tokens) / len(cleaned_tokens)) if cleaned_tokens else 0.0
    techniques = chapter.get("techniques") if isinstance(chapter.get("techniques"), list) else []
    named: list[str] = []
    starred = 0
    bad_ranges = 0
    start = chapter.get("start")
    end = chapter.get("end")
    lo = start if isinstance(start, (int, float)) else None
    hi = end if isinstance(end, (int, float)) else None
    for item in techniques:
        if not isinstance(item, dict):
            continue
        name = item.get("named_move")
        if isinstance(name, str) and name.strip():
            named.append(name)
        for value in item.values():
            if isinstance(value, str) and value.endswith("*"):
                starred += 1
            elif isinstance(value, list):
                starred += sum(1 for part in value if isinstance(part, str) and part.endswith("*"))
        for low, high in _parse_ranges(item.get("source_time_ranges")):
            if lo is None or hi is None or low < lo - 0.05 or high > hi + 0.05 or high < low:
                bad_ranges += 1
    title = chapter.get("title") if isinstance(chapter.get("title"), str) else ""
    empty_extract = bool(
        has_cleaned and _is_move_title(title) and not named
    )
    ratio = (len(cleaned_text) / len(raw)) if has_cleaned and raw else 0.0
    return {
        "has_cleaned": has_cleaned,
        "raw_cover": cover,
        "novel_frac": novel,
        "cleaned_raw_ratio": ratio,
        "leftover_timestamps": len(TIMESTAMP.findall(cleaned_text)),
        "technique_count": len(techniques),
        "duplicate_named_moves": len(named) - len(set(named)),
        "starred_fields": starred,
        "out_of_bounds_ranges": bad_ranges,
        "empty_extract_on_move_title": empty_extract,
    }


def summarize_provider(scores: Sequence[dict]) -> dict:
    cleaned = [row for row in scores if row.get("has_cleaned")]
    if not cleaned:
        return {
            "cleaned_chapters": 0,
            "median_raw_cover": 0.0,
            "median_novel_frac": 0.0,
            "median_cleaned_raw_ratio": 0.0,
            "leftover_timestamps": 0,
            "out_of_bounds_ranges": 0,
            "duplicate_named_moves": 0,
            "starred_fields": 0,
            "empty_extract_on_move_title": 0,
            "technique_count_mean": 0.0,
            "zero_technique_chapters": 0,
        }
    return {
        "cleaned_chapters": len(cleaned),
        "median_raw_cover": median(row["raw_cover"] for row in cleaned),
        "median_novel_frac": median(row["novel_frac"] for row in cleaned),
        "median_cleaned_raw_ratio": median(row["cleaned_raw_ratio"] for row in cleaned),
        "leftover_timestamps": sum(row["leftover_timestamps"] for row in cleaned),
        "out_of_bounds_ranges": sum(row["out_of_bounds_ranges"] for row in cleaned),
        "duplicate_named_moves": sum(row["duplicate_named_moves"] for row in cleaned),
        "starred_fields": sum(row["starred_fields"] for row in cleaned),
        "empty_extract_on_move_title": sum(
            1 for row in cleaned if row["empty_extract_on_move_title"]
        ),
        "technique_count_mean": mean(row["technique_count"] for row in cleaned),
        "zero_technique_chapters": sum(1 for row in cleaned if row["technique_count"] == 0),
    }


def rank_disagreements(
    chapters: Sequence[dict],
    *,
    limit: int = 10,
) -> list[dict]:
    ranked: list[dict] = []
    for item in chapters:
        by_provider = item.get("by_provider") or {}
        names = sorted(
            name
            for name, text in by_provider.items()
            if isinstance(text, str) and text.strip()
        )
        pair_f1: dict[str, float] = {}
        scores: list[float] = []
        for i, left in enumerate(names):
            for right in names[i + 1 :]:
                score = token_f1(by_provider[left], by_provider[right])
                pair_f1[f"{left}/{right}"] = score
                scores.append(score)
        if not scores:
            continue
        ranked.append(
            {
                "path": item.get("path", ""),
                "title": item.get("title", ""),
                "mean_pairwise_f1": mean(scores),
                "pair_f1": pair_f1,
                "providers": names,
            }
        )
    ranked.sort(key=lambda row: (row["mean_pairwise_f1"], row["title"]))
    return ranked[:limit]


def discover_volume_rels(out: Path, providers: Sequence[str]) -> list[str]:
    rels: list[str] = []
    seen: set[str] = set()
    for provider in providers:
        root = Path(out) / provider
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.json")):
            rel = path.relative_to(root).as_posix()
            if rel in seen:
                continue
            seen.add(rel)
            rels.append(rel)
    return rels


def metrics_from_dest(
    out: Path,
    volume_rels: Sequence[str],
    providers: Sequence[str],
    *,
    disagreement_limit: int = 10,
) -> dict:
    out = Path(out)
    summaries: dict[str, dict] = {}
    disagreement_chapters: list[dict] = []
    indexed: dict[tuple[str, str], dict] = {}
    for rel in volume_rels:
        for provider in providers:
            dest = out / provider / rel
            if not dest.is_file():
                continue
            payload = json.loads(dest.read_text(encoding="utf-8"))
            chapters = payload.get("chapters") if isinstance(payload.get("chapters"), list) else []
            scores: list[dict] = summaries.setdefault(provider, {}).setdefault("_scores", [])
            for index, chapter in enumerate(chapters):
                if not isinstance(chapter, dict):
                    continue
                scores.append(score_chapter(chapter))
                title = chapter.get("title") if isinstance(chapter.get("title"), str) else ""
                key = (rel, index)
                bucket = indexed.setdefault(
                    key, {"path": rel, "title": title, "by_provider": {}}
                )
                cleaned = chapter.get("transcript_cleaned")
                if isinstance(cleaned, str) and cleaned.strip():
                    bucket["by_provider"][provider] = cleaned
    for provider in providers:
        rows = summaries.get(provider, {}).pop("_scores", [])
        summaries[provider] = summarize_provider(rows)
    disagreement_chapters = list(indexed.values())
    return {
        "providers": summaries,
        "disagreements": rank_disagreements(
            disagreement_chapters, limit=disagreement_limit
        ),
    }


def render_metrics_markdown(metrics: dict) -> str:
    providers = list((metrics.get("providers") or {}).keys())
    lines = ["# LLM bake-off metrics", "", "Reference-free scores on chapters that have `transcript_cleaned`.", ""]
    headers = ["metric", *providers]
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
    fields = [
        ("cleaned_chapters", "cleaned chapters"),
        ("median_raw_cover", "median raw-token coverage"),
        ("median_novel_frac", "median novel-token rate"),
        ("median_cleaned_raw_ratio", "median cleaned/raw length"),
        ("leftover_timestamps", "leftover timestamps"),
        ("out_of_bounds_ranges", "out-of-bounds time ranges"),
        ("duplicate_named_moves", "duplicate named_move"),
        ("starred_fields", "starred guess fields"),
        ("empty_extract_on_move_title", "empty extract on move-like title"),
        ("technique_count_mean", "mean techniques"),
        ("zero_technique_chapters", "chapters with 0 techniques"),
    ]
    summaries = metrics.get("providers") or {}
    for key, label in fields:
        cells = [label]
        for provider in providers:
            value = summaries.get(provider, {}).get(key, 0)
            if isinstance(value, float):
                cells.append(f"{value:.3f}")
            else:
                cells.append(str(value))
        lines.append("| " + " | ".join(cells) + " |")
    lines.extend(["", "## Highest cleaned-text disagreement", ""])
    lines.append("| volume | chapter | mean pairwise F1 | pair F1 |")
    lines.append("| --- | --- | --- | --- |")
    for row in metrics.get("disagreements") or []:
        pairs = ", ".join(
            f"{name}={score:.3f}" for name, score in sorted(row.get("pair_f1", {}).items())
        )
        path = str(row.get("path", "")).rsplit("/", 1)[-1]
        lines.append(
            f"| {path} | {row.get('title', '')} | {row.get('mean_pairwise_f1', 0):.3f} | {pairs} |"
        )
    lines.append("")
    return "\n".join(lines)
