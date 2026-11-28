# Performance baselines: hop walk, keyword search, sentence find, Design map

Research for [Performance baselines for find, hop walk, and Design](https://github.com/djsciman/video_transcriber_rag/issues/139). Child of [Three-job coach UI implementation spec](https://github.com/djsciman/video_transcriber_rag/issues/134).

These are **measured numbers on this coach machine**, not product budgets. A later grilling child locks targets. The index engine was not changed. No GPU embeddings.

## Hardware

Measured 2026-11-28 on the coach laptop:

| Item | Value | Source |
|---|---|---|
| OS | Windows 11 (`Windows-11-10.0.26300-SP0`; `Get-ComputerInfo` also reports Windows 10 Home build 26300) | `platform.platform()`; `Get-ComputerInfo` |
| CPU | Intel Core i9-9980HK @ 2.40 GHz, 8 cores / 16 threads | `Win32_Processor` |
| RAM | 32 GB (34 073 567 232 bytes) | `Win32_ComputerSystem.TotalPhysicalMemory` |
| GPU | NVIDIA GeForce GTX 1650, 4 GB (unused for this work) | `Win32_VideoController` |
| Python | 3.12.10, 64-bit | `sys.version` (`py -3`) |
| SQLite | 3.49.1 with FTS5 | `sqlite3.sqlite_version`; `sqlite_compileoption_used('ENABLE_FTS5')` |
| ONNX Runtime | 1.31.0 (CPU provider used) | `py -3 -m pip show onnxruntime` |
| FastEmbed | 0.9.1, installed only to time MiniLM query; not used for the temp ingest | `pip show fastembed` |

## Live extracted-index file

**Missing.** `C:\Users\dumbo\.coach_app\settings.json` does not exist, so `coach_app.settings.extracted_index_path()` is unset. No production `extracted.sqlite` was found next to the corpus or the repo.

Baselines below use a **temp on-disk SQLite** filled by `bjj_pipeline.prepare.ingest_prepared_corpus` against the live library, plus the documented Marcelo sample.

## N: corpus JSON (re-count)

Path: `C:\Users\dumbo\Documents\GitHub\bjj_transcripts\library`. Walked with `json.loads` on every `*.json` that has a `chapters` key. No ingest in this table.

| Measure | 2026-11-25 ([#105](https://github.com/djsciman/video_transcriber_rag/issues/105)) | This scan (2026-11-28) |
|---|---:|---:|
| JSON volumes | 558 | **558** |
| Chapters | 4669 | **4669** |
| Technique objects (`techniques[]` dicts) | 5378 | **5378** |
| Chapters with a non-empty `techniques` array | 3552 | **3552** |
| Chapters with an empty `techniques` array | 927 | **927** |
| Chapters missing `techniques` | 190 | **190** |
| Concept strings | (not in the #105 headline) | **16846** |
| Parse errors | 0 | **0** |
| Instructional top-level folders | 86 | **84** |

Technique / chapter / volume counts are unchanged from 2026-11-25. Folder count differs because this scan counts unique first path segments among those 558 volume JSON files.

Duplicate JSON (same `video_file` + chapter `title` + `start` + array index) exists on disk: **46** duplicate technique objects, so **5332** unique technique keys and **16717** unique concept keys.

Repo sample `docs/samples/butterfly-marcelo-s01e01-pare.json` is not in the library. After mapping `chapter_title` → `title` for ingest, it yields **5 technique rows and 0 concept rows** (those sample chapters use empty `techniques` and no `concepts` lists).

## N: temp extracted index

Ingest: `ExtractedIndex.open(temp.sqlite)` + `ingest_prepared_corpus(library)` from `bjj_pipeline/prepare.py`. Embedder for ingest was a **384-d SHA-256 stub** (same blob width as MiniLM-L6; not the model). Chat unused at ingest.

| Measure | Value |
|---|---:|
| Ingest wall time | **130.2 s** |
| SQLite file size | **98.7 MiB** (103 481 344 bytes) |
| Rows | **21322** |
| Technique rows | **5207** |
| Concept rows | **16115** |
| Distinct `instructor` values | 22 |

Technique rows (5207) are below unique JSON keys (5332) because `ingest_prepared_corpus` walks every copy and last-write-wins on `(video_file, chapter_title, chapter_start, kind, array_index)` (`ExtractedIndex.ingest_chapter` / `_clear_unreviewed_for_chapter` in `coach_app/extracted_index.py`). Worm Guard and similar duplicate trees are the usual extra copies.

Prior MiniLM ingest of 5378 live rows was **160 s / 8.3 MB of vectors** on this machine ([#123](https://github.com/djsciman/video_transcriber_rag/issues/123); ADR-0006). This temp file is larger because it stores copied extract JSON, FTS, and hop columns, not vectors alone.

## Method

Script: `docs/ui-ux-discovery/measure_perf_baselines.py`.

- `time.perf_counter`, 1 warmup + 5 timed runs; report min / median / max.
- Disk-backed stdlib `sqlite3` through `ExtractedIndex` (`hop_walk`, `keyword_search`, `sentence_find`). Engine unchanged.
- Sentence find **chat stubbed**: the callable returns hops / keywords / `find_string` with no network. Production chat is `production_sentence_find_chat` in `coach_app/extracted_index.py` (not timed).
- Cosine uses 384-d float32 blobs, matching MiniLM-L6 width (`MiniLMEmbedder`, `CPUExecutionProvider`). Stub vectors stand in for stored blobs so the Python loop is the same width as production.
- MiniLM query embedding timed separately after installing FastEmbed 0.9.1 (CPU only).

`sentence_find` always hydrates **every** row (`self.rows()`), runs hop walk and keyword search when the stub fills those fields, then `_cosine` plus a per-row `embedding()` SELECT (`coach_app/extracted_index.py`). It **ranks** the whole index; hit count is therefore all 21322 rows.

## Sample (5 technique rows)

Marcelo sample, in-memory index, hashed 384-d stub, chat stubbed.

| Call | Hits | Median | Min | Max |
|---|---:|---:|---:|---:|
| `hop_walk()` | 5 | 0.14 ms | 0.14 ms | 0.15 ms |
| `hop_walk(bottom, butterfly-guard, sweep)` | 4 | 0.12 ms | 0.12 ms | 0.13 ms |
| `keyword_search("reshoot")` | 1 | 0.061 ms | 0.058 ms | 0.078 ms |
| `sentence_find(...)` (stub chat) | 5 | 0.84 ms | 0.84 ms | 0.92 ms |

## Live-scale timings (temp index, 21322 rows)

Medians unless noted. Seconds, then milliseconds.

### Hop walk

`hop_walk` is technique-only (`kind = 'technique'` plus stripped hop IN clauses). It materializes full `ExtractedRow` objects, including parsed `extract_json`.

| Call | Hits | Median | Min | Max |
|---|---:|---:|---:|---:|
| `rows()` (all kinds) | 21322 | **543 ms** | 522 ms | 552 ms |
| `hop_walk()` (all techniques) | 5207 | **162 ms** | 154 ms | 176 ms |
| `hop_walk(instructor="John Danaher")` | 2555 | **139 ms** | 136 ms | 146 ms |
| `hop_walk(start_position=["butterfly-guard","closed-guard"])` | 630 | **20 ms** | 19 ms | 20 ms |
| `hop_walk(bottom, butterfly-guard, sweep)` | 120 | **3.0 ms** | 2.9 ms | 3.3 ms |

Narrow hops are a few milliseconds. Listing every technique is dominated by row hydration, not the SQL filter.

### Keyword search

FTS5 `MATCH` on `extract_fts` (`named_move`, `instructor`, `instructional`, `chapter_title`, `technique_steps`, `main_ideas`, `suggested_tags`, `concept`).

| Call | Hits | Median | Min | Max |
|---|---:|---:|---:|---:|
| `keyword_search("reshoot")` | 8 | **0.33 ms** | 0.32 ms | 0.36 ms |
| `keyword_search("butterfly", kind="techniques")` | 604 | **25 ms** | 24 ms | 26 ms |
| `keyword_search("butterfly", kind="concepts")` | 1355 | **34 ms** | 33 ms | 35 ms |
| `keyword_search("underhook")` | 1660 | **54 ms** | 53 ms | 58 ms |
| `keyword_search("butterfly")` (both) | 1959 | **59 ms** | 56 ms | 66 ms |

Rare tokens are sub-millisecond. Broad tokens that hit thousands of rows pay the same row-hydration cost as hop walk.

### Sentence find (chat stubbed)

Typed sentence: `how do I reshoot the butterfly sweep when he puts his weight on me`.

Stubs:

- hops + keyword: `start_occupancy=bottom`, `start_position=butterfly-guard`, `move_type=sweep`, `keywords=["reshoot"]`, `find_string="reshoot butterfly sweep from bottom"`
- hops only: same hops, empty keywords
- find-string only: no hops, no keywords

| Call | Ranked rows | Median | Min | Max |
|---|---:|---:|---:|---:|
| hops + keyword | 21322 | **3.90 s** | 3.78 s | 4.12 s |
| hops only | 21322 | **3.86 s** | 3.77 s | 3.95 s |
| find-string only | 21322 | **3.79 s** | 3.73 s | 3.89 s |

Hop/keyword prefilters do not shrink the ranked list; they only set the full-match band. Cost is `rows()` (~0.54 s) plus a cosine and a per-row embedding SELECT over 21322 rows.

CPU MiniLM-L6 query embed (FastEmbed, `CPUExecutionProvider`, after 2.61 s model load):

| Text | Dim | Median |
|---|---:|---:|
| `reshoot butterfly sweep from bottom` | 384 | **2.9 ms** |
| typed sentence (not used by find; production embeds `find_string`) | 384 | **3.8 ms** |

One MiniLM query is negligible next to the 3.8 s rank loop. Production would add this ~3 ms (and a cold-load of ~2.6 s once per process) on top of the stubbed-chat numbers. Cloud chat latency is **not** in these baselines.

## Design map render (spec-70 JS)

Source: `coach_app/ui_design.py` `_map_script` on `implement/spec-70` at `1654281` (`layoutLabels` 28 iterations, overlap pass, SVG `paintGraph`). Copied into `docs/ui-ux-discovery/measure_design_map.html`. Timed with Edge headless (`msedge.exe --headless=new --virtual-time-budget=15000`) via `performance.now()`, 8 runs after one warmup paint.

`sample_tight_waist` in `coach_app/design.py` places the two home named moves, three trilemma named moves, and the system when the catalog has them: **6 marks** is the Tight-waist-scale case.

| Marks | What | Median | Min | Max |
|---:|---|---:|---:|---:|
| 0 | empty map | 0.0 ms | 0.0 ms | 0.2 ms |
| 6 | Tight-waist scale | **0.40 ms** | 0.20 ms | 2.2 ms |
| 20 | denser unit | **1.35 ms** | 1.10 ms | 1.7 ms |
| 50 | stress (far above a unit map) | **4.35 ms** | 3.30 ms | 6.4 ms |

First 6-mark samples included 1.7–2.2 ms; later paints sit around 0.2–0.4 ms. At unit scale the spec-70 SVG paint is a fraction of a millisecond to a couple of milliseconds. This is **client JS paint**, not Python `CuratedStore` seed import.

## Reproduction

```
py -3 docs/ui-ux-discovery/measure_perf_baselines.py
```

Design: open `docs/ui-ux-discovery/measure_design_map.html` in Edge, or dump-dom headless as in this run. Raw JSON from this run: `docs/ui-ux-discovery/perf-baselines-raw.json`.

## Not locked

Do not treat these as budgets. Grilling child [#145](https://github.com/djsciman/video_transcriber_rag/issues/145) locks numbers. This note does not choose a host, a filter library, or an index change.

## Sources

- `coach_app/extracted_index.py` — `hop_walk`, `keyword_search`, `sentence_find`, `MiniLMEmbedder`, per-row `embedding()`
- `bjj_pipeline/prepare.py` — `ingest_prepared_corpus`
- `coach_app/settings.py` — extracted-index path
- `coach_app/design.py` — `sample_tight_waist`
- `implement/spec-70` `coach_app/ui_design.py` `_map_script` / `paintGraph` (`1654281`)
- `docs/adr/0006-sqlite-fts5-extracted-index.md`
- [Task: Count extracted techniques](https://github.com/djsciman/video_transcriber_rag/issues/105) (558 / 5378 on 2026-11-25)
- [Research: Local CPU embedding models](https://github.com/djsciman/video_transcriber_rag/issues/123) (MiniLM ingest 160 s)
- Live library `C:\Users\dumbo\Documents\GitHub\bjj_transcripts\library`
- `docs/samples/butterfly-marcelo-s01e01-pare.json`
