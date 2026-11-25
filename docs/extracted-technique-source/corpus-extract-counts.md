# Extracted-technique counts in the prepared corpus

Count for [Task: Count extracted techniques in the prepared corpus](https://github.com/djsciman/video_transcriber_rag/issues/105). Re-scanned 2026-11-25 with `py -3`. No ingest.

Prior close (2026-11-19) found 529 volumes and **0** extracted-technique objects. The live library now has filled `transcript_cleaned` and `techniques` arrays on most prepared volumes.

## Path scanned

| Path | Present |
|---|---|
| `C:\Users\dumbo\Documents\GitHub\bjj_transcripts\library` | yes (this scan) |
| `C:\Users\dumbo\Documents\GitHub\djsciman_data_projects\video-transcriber\library` | no |

Repo sample `docs/samples/butterfly-marcelo-s01e01-pare.json` is not in the corpus library and was not counted.

## Headline

| Measure | 2026-11-19 | 2026-11-25 |
|---|---:|---:|
| JSON volumes | 529 | **558** |
| Instructional folders | 78 | **86** |
| Chapters | 4516 | **4669** |
| Extracted-technique objects | 0 | **5378** |
| Chapters with a non-empty `techniques` array | 0 | **3552** |
| Chapters with an empty `techniques` array | 0 | **927** |
| Chapters missing the `techniques` key | 4516 | **190** |
| Starred hop-field values | 0 | **5259** |
| Parse errors | 0 | **0** |

One findable row is one object in a chapter `techniques` array. Empty arrays are real (theory / posture chapters). Missing keys are unprepared or nest-only chapters.

## Chapter speech

| Measure | Count |
|---|---:|
| Volumes with at least one non-empty `transcript_raw` | 476 |
| Volumes with at least one non-empty `transcript_cleaned` | 472 |
| Volumes with at least one extracted-technique object | 450 |
| Volumes with both cleaned speech and at least one filled `techniques` array | 450 |
| Chapters with `transcript_cleaned` as a string | 4479 |
| of which non-empty | 4477 |
| Chapters with `concepts` as a list | 4479 |
| Chapters with `suggested_tags` as a list | 4479 |
| Volumes that still hold a top-level `segments` list | 5 |

## Volume prepare buckets

| Bucket | Volumes |
|---|---:|
| LLM complete, at least one technique object | 450 |
| LLM complete, every `techniques` array empty | 22 |
| Nested raw, no LLM keys | 6 |
| Title / start / end only | 19 |
| Empty `chapters` list | 61 |
| **Total** | **558** |

`450 + 22 + 6 + 19 + 61 = 558`.

Five volumes still have `segments`: four Couch Finishing Leg Locks files (empty `chapters`) and Tonon Break Legs and Hearts S01E01 (nine chapters, no cleaned speech).

Every volume JSON has top-level keys `video_file`, `chapters`, `language`. `language` is `en` on all 558. No volume uses `video_file_path`. Chapter titles live on `title`, not `chapter_title`.

## Hop starring

Hop fields on each technique object: `named_move`, `ruleset`, `move_type`, `start_occupancy`, `start_position`, `end_occupancy`, `end_position`. A starred value is a string that ends in `*` with no space.

| Field | Starred |
|---|---:|
| `ruleset` | 1839 |
| `end_position` | 1359 |
| `start_position` | 1096 |
| `move_type` | 623 |
| `start_occupancy` | 169 |
| `end_occupancy` | 109 |
| `named_move` | 64 |
| **total** | **5259** |

## Tags and time ranges

`suggested_tags` is an array of **keyword strings** on both the chapter (from `concepts`) and the technique (from `main_ideas`). Zero hop-object tags remain.

| Shape | Count |
|---|---:|
| Chapter tags: strings | 4001 |
| Chapter tags: empty list | 478 |
| Technique tags: strings | 4810 |
| Technique tags: empty list | 568 |
| `source_time_ranges: []` | 5315 |
| Seconds-dash range strings | 63 |
| Clock-style range strings | 0 |

## Fifty filled samples

The walk shuffled JSON paths with `random.Random(20261125)` and kept the first 50 volumes that have both non-empty `transcript_cleaned` and a non-empty `techniques` array. All 50 share the same chapter key set (`title`, `start`, `end`, credits, `transcript_raw`, `transcript_cleaned`, `concepts`, `suggested_tags`, `techniques`) and the same eleven technique fields. Paths are listed in [Prepared chapter JSON for extracted techniques](prepared-chapter-json.md).

In those 50 volumes: 496 chapters, 86 empty `techniques` arrays, 422 chapters whose `transcript_raw` starts before `chapter.start` (ADR 0003 overlap copy), 0 cleaned chapters that still contain `<sec>` stamps.

## Method

`pathlib.rglob("*.json")` over the named library. `json.loads` UTF-8. No Ollama. No ingest. Windows long paths were not required for this walk (558 files found; prior 2026-11-19 long-path walk found 529).
