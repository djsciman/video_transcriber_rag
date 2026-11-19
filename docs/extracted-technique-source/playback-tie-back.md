# Playback tie-back from volume files and time ranges

Research for [Research: Video playback tie-back from volume files and time ranges](https://github.com/djsciman/video_transcriber_rag/issues/104), a child of [Extracted-technique data source for the curated store](https://github.com/djsciman/video_transcriber_rag/issues/101).

This document records how playback resolution works today and which keys an **extracted technique** must carry so the coach can open the original volume at the showing. It does not pick a player. It does not implement a store.

## Answer

Playback is resolved at open time. The curated citation stores the video **file name** (basename with extension) and a **speech-start timestamp** per showing. The coach-set **video root** and the transcript's **mirrored folder** are supplied when the coach opens the showing, not stored as an absolute path.

`playback_handle` formats that pair as `{video_file}@{timestamp}`. `resolve_video_playback` joins `video_root / transcript_folder / video_file`, checks that the named path is a file whose suffix is in a small video set, and returns the path, the timestamp, and an `available` flag. A missing or non-video file still admits the citation.

An extracted-technique row can reuse that same open-time join. It must carry (or inherit at ingest) three keys: the video file name, the relative mirrored folder under the video root, and one speech-start per showing. `source_time_ranges` on the prepared technique is the showing list: each range is one showing, opened at the start of that range.

## How playback works today

### Handle format

[`coach_app/citations.py`](../../coach_app/citations.py) `playback_handle(video_file, timestamp)` returns:

```text
{video_file}@{timestamp}
```

`timestamp` is interpolated with Python's default `str` for a float (`12.5` stays `12.5`). Tests assert the stored link ends with `@5.26` and `@12.5` ([`tests/test_briefing.py`](../../tests/test_briefing.py), [`tests/test_citations.py`](../../tests/test_citations.py)).

[`CuratedStore.accept`](../../coach_app/store.py) writes one `Showing` per proposal detail:

- `timestamp` = `float(detail["speech_start"])`
- `playback_link` = `playback_handle(video_file, detail["speech_start"])`

The citation's `volume` field is that same `video_file` basename. The `Volume` record is keyed by `(instructional, video_file_name)` and stores no folder.

Open-time resolution does **not** parse the handle string. `CuratedStore.resolve_playback` passes `citation.volume` and `showing.timestamp` into `resolve_video_playback`. The handle is identity and display on the showing, not the lookup key.

### Path resolution

```python
named = Path(video_root) / transcript_folder / video_file
available = named.is_file() and named.suffix.casefold() in _VIDEO_SUFFIXES
return named, float(speech_start), available
```

Source: [`resolve_video_playback`](../../coach_app/citations.py).

- `video_root` is the coach-set video library root, passed at open time.
- `transcript_folder` is the relative folder that mirrors the volume under that root. Tests use the show folder name, e.g. `"Half Guard Passing and Dynamic Pins"`, not an absolute transcript-corpus path ([`tests/test_citations.py`](../../tests/test_citations.py)).
- `video_file` is the basename including extension, from transcript JSON `video_file` ([`bjj_pipeline/batch_panoscribe.py`](../../bjj_pipeline/batch_panoscribe.py) writes `video.name`).

The transcriber mirrors the video tree into JSON: `output_path_for` maps `video.relative_to(input_dir)` to `output_dir / rel.with_suffix(".json")`. The JSON path's parent relative to the corpus root is the same relative folder as the video under the video root. That is the `transcript_folder` argument.

There is no glob, no extension fallback, and no walk. The named path is the only candidate. Same-stem `.nfo` and `.json` files in that folder are ignored ([`test_playback_resolves_video_path_and_speech_start`](../../tests/test_citations.py)).

The README example passes `transcript_folder=r"path\to\transcript-corpus\that-show"`. That string is the mirrored relative folder under `video_root`, not a second root. An absolute transcript-corpus path would replace `video_root` under `pathlib` join rules and would not match the tests.

Closed [What a playback link opens](https://github.com/djsciman/video_transcriber_rag/issues/13): store the file name, not an absolute path; resolve at open time against the coach-set video root and the transcript's mirrored folder. The spec names no player.

### Suffix rules

Playback availability uses this set in [`coach_app/citations.py`](../../coach_app/citations.py):

```text
.mp4  .mkv  .mov  .avi  .webm  .m4v
```

Comparison is `suffix.casefold()`, so `.MP4` counts. The named path must also `is_file()`.

Transcribe walks a larger set ([`bjj_pipeline/batch_panoscribe.py`](../../bjj_pipeline/batch_panoscribe.py) `VIDEO_EXTS`): the six above plus `.flv` and `.wmv`. Organizer naming uses a smaller set (`.mp4`, `.mkv`, `.webm`, `.m4v`). If `video_file` is `Vol1.flv` and that file exists, `available` is false because `.flv` is not a playback suffix.

An empty `.mp4` still counts as available (`write_bytes(b"")` in the resolve test). Completeness scan's "playback" column is a separate decode check and is not used by `resolve_video_playback`.

### Missing-file behavior

[`test_missing_video_still_admits_the_citation`](../../tests/test_citations.py) and glossary **Playback link**:

- `store.accept` still writes the citation.
- `resolve_playback` still returns a `Playback` with `path.name == video_file` and the showing's `speech_start`.
- `available` is `False`.
- The coach uses the timestamp and the volume, including the video file name, to look the video up.

A same-stem `.nfo` with no video file is treated as missing, not as a video.

`resolve_playback` names no player. The resolve test asserts `ffmpeg`, `whisper`, `vlc`, and `browser` do not appear in its source.

### What a curated showing stores versus what open time needs

| Piece | Stored on the citation / volume | Supplied at open time |
| --- | --- | --- |
| Video file name | `citation.volume`, `Volume.video_file_name`, handle prefix | — |
| Speech start | `Showing.timestamp`, handle suffix | — |
| Video root | not stored | `video_root` |
| Mirrored folder | not stored | `transcript_folder` |
| Absolute path | not stored | computed |
| Player | not stored | out of scope |

Coach-authored citations have no instructional, volume, chapter, or playback link ([`GLOSSARY.md`](../../GLOSSARY.md) **Citation**). This tie-back is for corpus rows only.

## Prepared extracted-technique keys

Glossary **Extracted technique**: one independently taught movement taken from a chapter; it carries the times in that volume where it is shown. It is one findable row before accept, not a Technique lesson and not an accepted citation.

### Volume-level video keys on the sample

Prepared sample [`docs/samples/butterfly-marcelo-s01e01-pare.json`](../samples/butterfly-marcelo-s01e01-pare.json) (may be untracked on `initial`):

| Field | Sample value | Role |
| --- | --- | --- |
| `instructional` | `Butterfly by Marcelo Garcia` | show name |
| `volume` | `Butterfly by Marcelo Garcia - S01E01 - Volume 1.mp4` | basename with extension; same grain as transcript `video_file` |
| `video_file_path` | `Butterfly by Marcelo Garcia\Season 01\Butterfly by Marcelo Garcia - S01E01 - Volume 1.mp4` | relative path under the video root, Windows separators |
| `instructor` | `Marcelo Garcia` | not required for path join |

`video_file_path` is volume-level, not on each technique object. `coach_app` does not read it. Committed [`bjj_pipeline/prepare.py`](../../bjj_pipeline/prepare.py) stamps each chapter with `volume` from payload `video_file` and does not write `video_file_path`. The sample still shows how a relative path splits into the two arguments `resolve_video_playback` needs:

- `transcript_folder` = parent of `video_file_path` → `Butterfly by Marcelo Garcia\Season 01`
- `video_file` = name of `video_file_path` → `Butterfly by Marcelo Garcia - S01E01 - Volume 1.mp4`

Join: `video_root / transcript_folder / video_file`.

Storing only the basename is not enough once instructionals have season folders. The relative folder (or the full relative `video_file_path`) must travel with the row, because `Volume` in the curated store does not keep it.

### `source_time_ranges`

The pare prompt ([`docs/prepare-llm-prompt.md`](../prepare-llm-prompt.md) §15) defines `source_time_ranges` as an array of timestamp strings on each technique:

- Use only timestamps supplied in the input.
- Preserve the input format.
- Use separate ranges when the teaching is noncontiguous.
- Empty array when a reliable range cannot be established.
- Prompt examples use clock strings: `"04:32-06:18"`, `"08:12-09:45"`.

The Marcelo sample uses Whisper span seconds from `transcript_raw` (`<1036.24> …`), one range per technique, all contiguous:

| Chapter | `named_move` | `source_time_ranges` |
| --- | --- | --- |
| BUTTERFLY SWEEP PROCESS | Butterfly sweep | `1036.24-1603.98` |
| SHOOT & RESHOOT | Butterfly sweep | `1637.22-1869.25` |
| FAR SIDE SWEEP TO COUNTER UNDERHOOK PASS | Butterfly sweep* | `1908.40-2242.40` |
| 2-ON-1 SWEEP | 2-on-1 sweep* | `2242.40-2565.04` |
| KICK SPIN BACKTAKE | Kick spin backtake* | `2596.78-2825.60` |

No sample technique has two ranges. The prompt still requires an array and separate strings for noncontiguous teaching. There is no parser for these strings in `coach_app` or `bjj_pipeline` today.

### Mapping ranges to showings

Curated citations and extracted techniques use different showing grain.

**Citation path today.** `StatementDrafter` emits one detail per cleaned speech span (`speech_start` = span `start`). `accept` writes one `Showing` per detail. Playback opens at that span's start, matching glossary **Playback link**: "at the second when that showing's own speech begins."

**Extracted-technique path.** One row is one object in a chapter `techniques` array. Its `source_time_ranges` cover the demonstrations that support that movement. Map:

- Each non-empty range string → one showing.
- That showing's timestamp → the **start** of the range (the second that showing's speech begins).
- The range end is not an argument to `resolve_video_playback`. Keep it on the row if a later player wants a stop time; it is not required to open the volume.
- Empty `source_time_ranges` → no showing. The row can still be findable. Playback is unavailable until a range exists, same spirit as a missing file: the record is not rejected for lack of a playable file.
- Several ranges → several showings on the same row, same video file and folder, different speech starts. Do not collapse them into one handle.

Parse the start token of `{start}-{end}` in the format the string actually uses (seconds as in the sample, or `MM:SS` as in the prompt example). Do not invent boundaries. Convert the start to a float of seconds before `playback_handle` / `resolve_video_playback`.

### Minimum fields an extracted-technique row needs for tie-back

These are the keys that let the existing resolver open the volume. Other technique fields (`named_move`, hops, steps, tags) are not playback keys.

Must be on the row, or copied onto it from the parent volume JSON at ingest:

1. **`video_file`** — basename including extension. Same value as transcript `video_file` and sample `volume`. Feeds `playback_handle` and `resolve_video_playback(..., video_file=...)`.
2. **`transcript_folder`** — relative mirrored folder under the coach-set video root (parent of sample `video_file_path`, including season folders). Not an absolute path.
3. **`speech_start` per showing** — float seconds, one per `source_time_ranges` entry, taken from that range's start.

Equivalent packaging: persist **`video_file_path`** (relative) plus the range starts, and split path into folder + basename at open time. Do not persist an absolute path.

Not required for the join, but already on a corpus citation and useful for the coach when `available` is false: instructional name, instructor, chapter title, range end.

Open-time only, not a row key: **video root**.

Handle string `{video_file}@{speech_start}` can be derived; it does not have to be stored if the three keys above are present.

## Out of scope (this ticket)

- Naming a player (VLC, browser, ffplay, or otherwise). Closed issue 13 and the resolve test leave the player unnamed.
- Implementing a data-source store or changing production `coach_app`.
- Locking a storage engine (sibling research and grilling tickets on map 101).
- Choosing clock-string versus seconds as the only `source_time_ranges` format. Both appear in primary sources; ingest must accept the string as written and convert the start to seconds.

## Sources

- [`coach_app/citations.py`](../../coach_app/citations.py) — `playback_handle`, `resolve_video_playback`, `_VIDEO_SUFFIXES`
- [`coach_app/store.py`](../../coach_app/store.py) — `Showing`, `Playback`, `accept`, `resolve_playback`
- [`tests/test_citations.py`](../../tests/test_citations.py) — resolve at open time; ignore `.nfo`/`.json`; missing file still admits
- [`GLOSSARY.md`](../../GLOSSARY.md) — **Playback link**, **Citation**, **Volume**, **Extracted technique**
- [Issue 13 resolution](https://github.com/djsciman/video_transcriber_rag/issues/13#issuecomment-6486639520) — file name, not absolute path; no player; missing file still admits
- [`bjj_pipeline/batch_panoscribe.py`](../../bjj_pipeline/batch_panoscribe.py) — `video_file` basename; `output_path_for` mirror
- [`docs/prepare-llm-prompt.md`](../prepare-llm-prompt.md) §15 — `source_time_ranges` rules and clock examples
- [`docs/samples/butterfly-marcelo-s01e01-pare.json`](../samples/butterfly-marcelo-s01e01-pare.json) — `volume`, `video_file_path`, second-based ranges
- [`README.md`](../../README.md) — `resolve_playback` call shape
