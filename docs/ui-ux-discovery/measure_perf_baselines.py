"""Throwaway timings for hop walk, keyword search, and sentence find.

Does not change the index engine. Uses a 384-d hashed CPU stub so cosine
loop cost matches MiniLM blob width. Chat is stubbed. MiniLM is timed
separately when FastEmbed is installed.
"""

from __future__ import annotations

import hashlib
import json
import statistics
import sys
import tempfile
import time
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bjj_pipeline.prepare import ingest_prepared_corpus
from coach_app.extracted_index import ExtractedIndex, MiniLMEmbedder, MINILM_MODEL_ID

CORPUS = Path(r"C:\Users\dumbo\Documents\GitHub\bjj_transcripts\library")
SAMPLE = ROOT / "docs" / "samples" / "butterfly-marcelo-s01e01-pare.json"
HOP_FIELDS = (
    "named_move",
    "ruleset",
    "move_type",
    "start_occupancy",
    "start_position",
    "end_occupancy",
    "end_position",
)
RUNS = 5


def hashed_embedder(text: str) -> list[float]:
    block = hashlib.sha256((text or "").encode("utf-8")).digest()
    out: list[float] = []
    while len(out) < 384:
        block = hashlib.sha256(block).digest()
        for i in range(0, 32, 4):
            v = int.from_bytes(block[i : i + 4], "little") / 2**32
            out.append(v * 2.0 - 1.0)
    return out[:384]


def timed(fn, *, warmup=1, runs=RUNS):
    for _ in range(warmup):
        fn()
    samples = []
    result = None
    for _ in range(runs):
        start = time.perf_counter()
        result = fn()
        samples.append(time.perf_counter() - start)
    samples.sort()
    n = None
    if result is not None and hasattr(result, "__len__") and not isinstance(result, (str, bytes)):
        n = len(result)
    return {
        "n_hits": n,
        "runs": runs,
        "warmup": warmup,
        "min_s": samples[0],
        "median_s": statistics.median(samples),
        "max_s": samples[-1],
        "samples_s": samples,
    }


def count_corpus(root: Path) -> dict:
    volumes = 0
    chapters = 0
    techniques = 0
    concepts = 0
    filled = 0
    empty = 0
    missing = 0
    parse_errors = 0
    instructional_dirs = set()
    for path in sorted(root.rglob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            parse_errors += 1
            continue
        if not isinstance(payload, dict) or "chapters" not in payload:
            continue
        volumes += 1
        instructional_dirs.add(path.parts[len(root.parts)] if len(path.parts) > len(root.parts) else path.name)
        chs = payload.get("chapters")
        if not isinstance(chs, list):
            continue
        chapters += len(chs)
        for chapter in chs:
            if not isinstance(chapter, dict):
                continue
            techs = chapter.get("techniques")
            if techs is None:
                missing += 1
            elif isinstance(techs, list):
                if techs:
                    filled += 1
                else:
                    empty += 1
                techniques += sum(1 for item in techs if isinstance(item, dict))
            cons = chapter.get("concepts")
            if isinstance(cons, list):
                concepts += sum(1 for item in cons if isinstance(item, str) and item)
    return {
        "path": str(root),
        "present": root.is_dir(),
        "json_volumes": volumes,
        "instructional_folders": len(instructional_dirs),
        "chapters": chapters,
        "technique_objects": techniques,
        "concept_strings": concepts,
        "chapters_filled_techniques": filled,
        "chapters_empty_techniques": empty,
        "chapters_missing_techniques": missing,
        "parse_errors": parse_errors,
    }


def count_index(index: ExtractedIndex) -> dict:
    rows = index.rows()
    kinds = Counter(row.kind for row in rows)
    instructors = Counter(row.instructor for row in rows if row.instructor)
    start_pos = Counter(row.start_position.rstrip("*") for row in rows if row.kind == "technique" and row.start_position)
    return {
        "rows": len(rows),
        "techniques": kinds.get("technique", 0),
        "concepts": kinds.get("concept", 0),
        "instructors": len(instructors),
        "top_instructors": instructors.most_common(5),
        "top_start_positions": start_pos.most_common(8),
    }


def stub_chat_full(_sentence: str) -> dict:
    return {
        "start_occupancy": "bottom",
        "start_position": "butterfly-guard",
        "move_type": "sweep",
        "keywords": ["reshoot"],
        "find_string": "reshoot butterfly sweep from bottom",
    }


def stub_chat_find_only(_sentence: str) -> dict:
    return {
        "keywords": [],
        "find_string": "reshoot butterfly sweep from bottom",
    }


def stub_chat_hops_only(_sentence: str) -> dict:
    return {
        "start_occupancy": "bottom",
        "start_position": "butterfly-guard",
        "move_type": "sweep",
        "keywords": [],
        "find_string": "reshoot butterfly sweep from bottom",
    }


def try_minilm_query() -> dict | None:
    try:
        embedder = MiniLMEmbedder()
    except Exception as exc:
        return {"available": False, "error": f"{type(exc).__name__}: {exc}"}
    texts = [
        "reshoot butterfly sweep from bottom",
        "how do I reshoot the butterfly sweep when he puts his weight on me",
    ]
    embedder(texts[0])
    times = {}
    for text in texts:
        samples = []
        for _ in range(3):
            start = time.perf_counter()
            vec = embedder(text)
            samples.append(time.perf_counter() - start)
        times[text] = {
            "dim": len(vec),
            "min_s": min(samples),
            "median_s": statistics.median(samples),
            "max_s": max(samples),
        }
    return {"available": True, "model": MINILM_MODEL_ID, "providers": ["CPUExecutionProvider"], "queries": times}


def ingest_sample_file(index: ExtractedIndex, path: Path) -> int:
    payload = json.loads(path.read_text(encoding="utf-8"))
    volume = {
        "video_file": payload.get("video_file") or payload.get("volume") or "",
        "instructor": payload.get("instructor") or "",
        "instructional": payload.get("instructional") or "",
    }
    n = 0
    for chapter in payload.get("chapters") or []:
        if not isinstance(chapter, dict):
            continue
        adapted = dict(chapter)
        if "title" not in adapted and "chapter_title" in adapted:
            adapted["title"] = adapted["chapter_title"]
        index.ingest_chapter(volume, adapted, corpus_json_path=str(path))
        n += 1
    return n


def main() -> None:
    report: dict = {
        "hardware": {
            "python": sys.version,
            "platform": __import__("platform").platform(),
            "processor": __import__("platform").processor(),
            "sqlite": __import__("sqlite3").sqlite_version,
            "note": "Windows 10 Home 10.0.26300; Intel i9-9980HK 8c/16t; ~32 GB RAM; GTX 1650 4 GB unused",
        },
        "live_index": {
            "settings_path": str(Path.home() / ".coach_app" / "settings.json"),
            "present": (Path.home() / ".coach_app" / "settings.json").is_file(),
            "extracted_index_file": None,
        },
        "corpus_count": count_corpus(CORPUS) if CORPUS.is_dir() else {"present": False, "path": str(CORPUS)},
        "sample": {"path": str(SAMPLE), "present": SAMPLE.is_file()},
    }

    sample_index = ExtractedIndex(embedder=hashed_embedder, chat=stub_chat_full)
    if SAMPLE.is_file():
        t0 = time.perf_counter()
        chapters = ingest_sample_file(sample_index, SAMPLE)
        report["sample"]["ingest_s"] = time.perf_counter() - t0
        report["sample"]["chapters_ingested"] = chapters
        report["sample"]["index"] = count_index(sample_index)
        report["sample"]["timings"] = {
            "hop_walk_empty": timed(lambda: sample_index.hop_walk()),
            "hop_walk_butterfly": timed(
                lambda: sample_index.hop_walk(
                    start_occupancy="bottom",
                    start_position="butterfly-guard",
                    move_type="sweep",
                )
            ),
            "keyword_reshoot": timed(lambda: sample_index.keyword_search("reshoot")),
            "sentence_find_stub": timed(
                lambda: sample_index.sentence_find(
                    "how do I reshoot the butterfly sweep when he puts his weight on me"
                )
            ),
        }

    report["minilm_query"] = try_minilm_query()

    if CORPUS.is_dir():
        tmp = Path(tempfile.mkdtemp(prefix="extracted-index-perf-")) / "extracted.sqlite"
        t0 = time.perf_counter()
        live = ExtractedIndex.open(tmp, embedder=hashed_embedder, chat=stub_chat_full)
        ingest_prepared_corpus(CORPUS, live)
        report["live_ingest"] = {
            "sqlite": str(tmp),
            "seconds": time.perf_counter() - t0,
            "sqlite_bytes": tmp.stat().st_size if tmp.is_file() else 0,
            "index": count_index(live),
            "embedder": "384-d sha256 stub (same width as MiniLM-L6; not the model)",
        }

        live_find_only = ExtractedIndex.open(tmp, embedder=hashed_embedder, chat=stub_chat_find_only)
        live_hops_only = ExtractedIndex.open(tmp, embedder=hashed_embedder, chat=stub_chat_hops_only)

        report["live_timings"] = {
            "rows()": timed(lambda: live.rows()),
            "hop_walk_empty": timed(lambda: live.hop_walk()),
            "hop_walk_butterfly": timed(
                lambda: live.hop_walk(
                    start_occupancy="bottom",
                    start_position="butterfly-guard",
                    move_type="sweep",
                )
            ),
            "hop_walk_start_position_or": timed(
                lambda: live.hop_walk(start_position=["butterfly-guard", "closed-guard"])
            ),
            "hop_walk_instructor_danaher": timed(
                lambda: live.hop_walk(instructor="John Danaher")
            ),
            "keyword_reshoot_both": timed(lambda: live.keyword_search("reshoot")),
            "keyword_butterfly_both": timed(lambda: live.keyword_search("butterfly")),
            "keyword_underhook_both": timed(lambda: live.keyword_search("underhook")),
            "keyword_butterfly_techniques": timed(
                lambda: live.keyword_search("butterfly", kind="techniques")
            ),
            "keyword_butterfly_concepts": timed(
                lambda: live.keyword_search("butterfly", kind="concepts")
            ),
            "sentence_find_hops_and_keyword": timed(
                lambda: live.sentence_find(
                    "how do I reshoot the butterfly sweep when he puts his weight on me"
                )
            ),
            "sentence_find_find_string_only": timed(
                lambda: live_find_only.sentence_find(
                    "how do I reshoot the butterfly sweep when he puts his weight on me"
                )
            ),
            "sentence_find_hops_only": timed(
                lambda: live_hops_only.sentence_find(
                    "how do I reshoot the butterfly sweep when he puts his weight on me"
                )
            ),
        }
        live.close()
        live_find_only.close()
        live_hops_only.close()

    out = ROOT / "docs" / "ui-ux-discovery" / "perf-baselines-raw.json"
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    print("wrote", out)


if __name__ == "__main__":
    main()
