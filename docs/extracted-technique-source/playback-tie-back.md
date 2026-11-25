# Playback tie-back from volume files and time ranges

Research for [Research: Video playback tie-back from volume files and time ranges](https://github.com/djsciman/video_transcriber_rag/issues/104). Re-performed 2026-11-25 against `v2` (`479d2c1`) and the live corpus.

This document records how playback resolution works today and which keys an **extracted technique** must carry so the coach can open the original volume at the showing. It does not pick a player. It does not implement a store.

## Answer

Playback is resolved at open time. The citation stores the video **file name** (basename with extension) and a **speech-start timestamp** per showing. The coach-set **video root** and the transcript's **mirrored folder** are supplied when the coach opens the showing. Do not store an absolute path.

`playback_handle` is `{video_file}@{timestamp}`. `resolve_video_playback` joins `video_root / transcript_folder / video_file`, accepts suffixes `.mp4 .mkv .mov .avi .webm .m4v`, and returns the path, the timestamp, and `available`. A missing or non-video file still admits the citation.

An extracted-technique row reuses that join. On live corpus JSON the video file name is top-level `video_file` (copied onto each chapter as `volume`). The mirrored folder is the JSON file's parent relative to the corpus root, including `Season 01` when present. There is **no** `video_file_path` on any of 558 live volumes.

`source_time_ranges` is the specified showing list, but on the live corpus it is almost always empty (5315 of 5378 techniques). Until a processing ticket fills starts from `transcript_raw` stamps or `chapter.start`, ingest should still keep the three join keys and treat an empty range list as "no showing," not as a rejected row.

## How playback works today

### Handle format

[`coach_app/citations.py`](../../coach_app/citations.py) `playback_handle(video_file, timestamp)` returns `{video_file}@{timestamp}`. Timestamp uses Python's default float `str` (`12.5` stays `12.5`).

[`CuratedStore.accept`](../../coach_app/store.py) writes one `Showing` per proposal detail: `timestamp = float(detail["speech_start"])`, `playback_link = playback_handle(video_file, …)`. The citation `volume` field is that same basename. The `Volume` record is keyed by `(instructional, video_file_name)` and stores no folder.

Open-time resolution does **not** parse the handle string. `CuratedStore.resolve_playback` passes `citation.volume` and `showing.timestamp` into `resolve_video_playback`.

### Path resolution

```python
named = Path(video_root) / transcript_folder / video_file
available = named.is_file() and named.suffix.casefold() in _VIDEO_SUFFIXES
return named, float(speech_start), available
```

- `video_root` is the coach-set video library root, passed at open time.
- `transcript_folder` is the relative folder that mirrors the volume under that root. Tests use a show folder such as `"Half Guard Passing and Dynamic Pins"` ([`tests/test_citations.py`](../../tests/test_citations.py)). Live corpus JSON sits under that same relative tree, often `Show folder\Season 01\`.
- `video_file` is the basename including extension. Transcribe writes `video.name` ([`bjj_pipeline/batch_panoscribe.py`](../../bjj_pipeline/batch_panoscribe.py)). Prepare copies it onto every chapter as `volume`. On the 50 filled samples, `chapter.volume == payload.video_file` for all 496 chapters.

`output_path_for` maps `video.relative_to(library)` to `corpus / rel.with_suffix(".json")`. The JSON parent relative to the corpus root **is** `transcript_folder`.

There is no glob, no extension fallback, and no walk. Same-stem `.nfo` / `.json` files are ignored.

Closed [What a playback link opens](https://github.com/djsciman/video_transcriber_rag/issues/13): store the file name, not an absolute path; resolve at open time; no player is named.

### Suffix rules

Playback availability (`_VIDEO_SUFFIXES`): `.mp4 .mkv .mov .avi .webm .m4v` (casefold). Transcribe walks those plus `.flv` and `.wmv`. An `.flv` that exists is `available=False`.

### Missing-file behavior

[`test_missing_video_still_admits_the_citation`](../../tests/test_citations.py) and glossary **Playback link**: accept still writes the citation; resolve still returns a `Playback` with `path.name == video_file` and the showing's `speech_start`; `available` is `False`. The coach uses the timestamp and the volume name to look the file up.

`resolve_playback` names no player. The resolve test asserts `ffmpeg`, `whisper`, `vlc`, and `browser` do not appear in its source.

## Live corpus video keys (2026-11-25)

| Field | Live corpus | Marcelo sample |
|---|---|---|
| `video_file` | present on all 558 volumes | absent |
| `video_file_path` | present on **0** volumes | `Show\Season 01\file.mp4` |
| chapter `volume` | equals `video_file` | absent (credits on volume root) |
| chapter `title` | identity | sample uses `chapter_title` |

Example live join for Danaher GFF Half Guard S01E05:

- `transcript_folder` = `Danaher - GFF Half Guard\Season 01`
- `video_file` = `Half Guard - Go Further Faster by John Danaher - S01E05 - The Single Most Important Section of this Video.mp4`
- Join: `video_root / transcript_folder / video_file`

Storing only the basename is not enough once instructionals have season folders. Persist the relative folder (or a relative `video_file_path` derived at ingest from the JSON path). Do not persist an absolute path. `Volume` in the curated store still does not keep the folder.

## `source_time_ranges` as showings

Glossary **Extracted technique** carries "the times in that volume where it is shown." Prompt §15 and the extract spec put those times on `source_time_ranges`.

Mapping:

- Each non-empty range string → one showing.
- Speech start → the **start** of the range.
- Range end is not an argument to `resolve_video_playback`.
- Empty list → no showing. The row stays findable. Same spirit as a missing file: do not reject the row.
- Several ranges → several showings on the same volume.

Parse `{start}-{end}` in the format the string actually uses, then convert the start to float seconds.

### What the live corpus actually has

| Kind | Count (whole corpus) |
|---|---|
| Technique objects | 5378 |
| `source_time_ranges: []` | 5315 |
| Seconds-dash strings (`1234.00-1560.00`) | 63 |
| Clock strings (`04:32-06:18`) | 0 |

In 50 filled samples, only two non-empty ranges: `"0.00-0.00"` (Danaher GFF Strangles Turtle, "Sprawling Juji Jime") and `"1680.00-2040.00"` (Wardzinski Butterfly Guard Re-Discovered S01E01). Treat `0.00-0.00` as empty.

Why they are empty: default prepare is staged. Cleanup strips `<sec>` stamps (`docs/prepare-llm-cleanup.md`). Extract is told to use only timestamps in its input and to return `[]` if cleaned speech has none (`docs/prepare-llm-extract.md`). Combined prompt §15 still shows clock examples; extract spec forbids them. Live filled ranges are nest seconds.

`transcript_raw` still has usable stamps, including overlap-copied spans that start **before** `chapter.start` (422 of 496 chapters in the 50 samples). Those stamps are the high-trust showing clock if a later processing ticket backfills ranges. `chapter.start` is a coarser fallback (opens at the chapter, not the showing).

The Marcelo sample still shows the intended filled shape (`1036.24-1603.98` on Butterfly sweep). Do not assume the live corpus matches that yet.

## Minimum fields for tie-back

On the row, or copied from the parent volume JSON at ingest:

1. **`video_file`** — basename including extension.
2. **`transcript_folder`** — relative mirrored folder under the video root (JSON parent relative to the corpus root, including season folders).
3. **`speech_start` per showing** — float seconds from each `source_time_ranges` start when present.

Open-time only: **video root**.

Handle `{video_file}@{speech_start}` can be derived.

Not required for the join, useful when `available` is false: instructor, instructional, chapter `title`, range end.

Empty `source_time_ranges` does not block ingest. A later [Grilling: Processing before ingest](https://github.com/djsciman/video_transcriber_rag/issues/111) can decide whether to fill starts from `transcript_raw` or `chapter.start`.

## Out of scope

- Naming a player.
- Implementing the data-source store or changing production `coach_app`.
- Locking a storage engine.
- Choosing clock versus seconds as the only stored format. Live filled ranges are seconds-dash; the combined prompt still shows clock examples. Convert the start to seconds at open time.

## Sources

- [`coach_app/citations.py`](../../coach_app/citations.py) — `playback_handle`, `resolve_video_playback`, `_VIDEO_SUFFIXES`
- [`coach_app/store.py`](../../coach_app/store.py) — `Showing`, `Playback`, `accept`, `resolve_playback`
- [`tests/test_citations.py`](../../tests/test_citations.py)
- [`GLOSSARY.md`](../../GLOSSARY.md) — **Playback link**, **Extracted technique**
- [Issue 13 resolution](https://github.com/djsciman/video_transcriber_rag/issues/13#issuecomment-6486639520)
- [`bjj_pipeline/batch_panoscribe.py`](../../bjj_pipeline/batch_panoscribe.py) — `video_file` basename; `output_path_for`
- [`bjj_pipeline/prepare.py`](../../bjj_pipeline/prepare.py) — chapter `volume` from `video_file`; staged extract
- [`docs/prepare-llm-prompt.md`](../prepare-llm-prompt.md) §15
- [`docs/prepare-llm-extract.md`](../prepare-llm-extract.md) — nest-style ranges; empty when cleaned speech has no stamps
- [`docs/prepare-llm-cleanup.md`](../prepare-llm-cleanup.md) — strips `<sec>` timestamps
- Live corpus walk 2026-11-25 (558 volumes, 5378 technique objects)
- [`docs/samples/butterfly-marcelo-s01e01-pare.json`](../samples/butterfly-marcelo-s01e01-pare.json)
