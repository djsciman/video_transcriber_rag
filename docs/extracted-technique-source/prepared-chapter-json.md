# Prepared chapter JSON for extracted techniques

Research for [issue #102](https://github.com/djsciman/video_transcriber_rag/issues/102). Question: what fields, grain, and gaps does prepared chapter JSON actually have for extracted techniques, including starred hops, empty chapters, time ranges, and video keys.

This note records the schema a later ingest can trust. It does not recommend a storage engine and does not implement ingest.

## Sources

- Glossary term **Extracted technique**, `GLOSSARY.md` (commit `f3cf7ac`)
- Prepare prompt, `docs/prepare-llm-prompt.md` (untracked on `initial` at research time)
- Marcelo sample, `docs/samples/butterfly-marcelo-s01e01-pare.json` (untracked on `initial` at research time)
- Live writer, `bjj_pipeline/prepare.py` (`HEAD` at `f3cf7ac`, plus the working-tree rewrite that nests without keeping Whisper `segments`)
- Tests, `tests/test_prepare.py` (and untracked `tests/test_prepare_cli.py`)
- `docs/adr/0004-store-chapter-speech-on-volume-json.md`
- `docs/adr/0003-copy-straddling-spans-into-both-chapters.md`
- Transcript inspector, `bjj_pipeline/batch_panoscribe.py` (`inspect_transcript`)
- Transcribe identity, `bjj_pipeline/batch_panoscribe.py` (`video_file` basename)

## Grain

One findable row is one **extracted technique**: one independently taught movement taken from a chapter. It is not a Technique lesson and not an accepted citation. (`GLOSSARY.md`, **Extracted technique**; map issue #101)

The prompt makes that row an object in the chapter `techniques` array. A chapter may hold several independently taught movements, or none. (`docs/prepare-llm-prompt.md` §§6, 16)

The Marcelo sample matches that grain: 9 chapters, 4 with `techniques: []`, 5 with exactly one technique object. No chapter in the sample has two techniques. The same seed name `Butterfly sweep` appears in two chapters (process vs shoot-and-reshoot). There is no technique-level id.

Identity a later ingest can form from what exists: volume key + chapter identity (`title`/`chapter_title` + `start` + `end`) + index in that chapter's `techniques` array. Named-move text is not unique.

## Two shapes, not one

Prepared JSON is not a single schema today. Ingest must not treat the live writer and the prompt/sample as the same record.

| Layer | What it actually writes / shows |
|---|---|
| Transcribe | Volume JSON with `video_file` (basename), `chapters[]` keyed by `title`/`start`/`end`, Whisper `segments`. (`bjj_pipeline/batch_panoscribe.py`) |
| Prepare nest (no `--llm`) | Same volume path. Each real chapter gets `instructor`, `instructional`, `volume`, `previous_chapter`, `next_chapter`, `transcript_raw`. Chapter identity stays `title`, `start`, `end`. (`bjj_pipeline/prepare.py`; ADR 0004; `tests/test_prepare.py`) |
| Prepare `--llm` (live writer) | Adds `transcript_cleaned` (string) and `suggested_tags` as an **array of hop objects** with field `end`, not `end_position`. Drops hops that fail a strict seed allow-list. Does not write `techniques`, `technique_steps`, `main_ideas`, `source_time_ranges`, or `*`. (`bjj_pipeline/prepare.py` `_build_prompt`, `_clean_hop`; `tests/test_prepare.py` `VALID_HOP`) |
| Prompt + Marcelo sample | LLM object is `{transcript_cleaned, techniques}`. Each technique has hop fields on the object, `technique_steps`, `main_ideas`, `source_time_ranges`, and `suggested_tags` as **keyword strings**. Sample nests that onto a volume JSON that uses `chapter_title` and `video_file_path`. |

`HEAD` prepare keeps Whisper `segments` on the volume (ADR 0004: "Whisper `segments` are left as transcribed"). The working-tree writer and its tests pop `segments` after nest (`payload.pop("segments", None)`; `tests/test_prepare.py` asserts `"segments" not in data`). The Marcelo sample also has no `segments`.

The inline prompt inside `prepare.py` `_build_prompt` still says: return JSON with `transcript_cleaned` and `suggested_tags` as hop objects (`start_position`, `start_occupancy`, `move_type`, `end`, `end_occupancy`, `named_move`, `ruleset`). That is the schema the writer will persist if `--llm` runs today. It is not the prompt in `docs/prepare-llm-prompt.md`.

## Schema a later ingest can trust (prompt + sample)

This is the extracted-technique shape the glossary, the prepare prompt, and the Marcelo sample agree on. It is **not** what `prepare.py --llm` currently persists.

### Volume object (sample)

Root keys on `docs/samples/butterfly-marcelo-s01e01-pare.json`:

- `instructional` — show folder name, e.g. `Butterfly by Marcelo Garcia`
- `volume` — video basename including extension
- `video_file_path` — relative path with Windows backslashes, e.g. `Butterfly by Marcelo Garcia\Season 01\Butterfly by Marcelo Garcia - S01E01 - Volume 1.mp4`
- `instructor` — `Marcelo Garcia`
- `chapters` — array

The sample has **no** `video_file` key.

### Chapter object (sample)

Each chapter has, in this order in the sample:

- `chapter_title` — not `title`
- `previous_chapter` / `next_chapter` — neighbor titles; `""` on first previous and last next
- `start` / `end` — floats, seconds on the volume
- `transcript_raw` — overlapping Whisper spans as `"<ss.ss> text"` joined by spaces
- `transcript_cleaned` — prose, no timestamps
- `techniques` — array of extracted-technique objects, possibly `[]`

Credits in the sample live on the **volume**, not on the chapter. The live writer puts `instructor`, `instructional`, and `volume` on **each chapter** and leaves `title` (not `chapter_title`). (`tests/test_prepare.py` `test_credits_from_show_folder_and_video_file`)

### Extracted-technique object (prompt §16 + sample)

Required fields, this order, no extras (`docs/prepare-llm-prompt.md` §16):

| Field | Type | Role |
|---|---|---|
| `named_move` | string | Seed name, suggested name with trailing `*`, or `""` only when no reasonable suggestion exists |
| `ruleset` | string | `gi`, `no-gi`, `both`, optionally with `*` |
| `move_type` | string | Seed type (`takedown`, `sweep`, `pass`, `escape`, `submission`, `transition`, `reversal`, `back-take`) or another type with `*` |
| `start_occupancy` | string | `top`, `bottom`, `neutral`, optionally with `*` |
| `start_position` | string | Seed position ID or a short label with `*` |
| `end_occupancy` | string | `top` / `bottom` / `neutral`, `""` when `end_position` is a submission ID, optionally with `*` |
| `end_position` | string | Seed position or submission ID, or a label with `*` |
| `technique_steps` | string | Numbered mechanical sequence, one line per action; not an array |
| `main_ideas` | string | Two or three pithy imperative sentences; not a step recap |
| `source_time_ranges` | array of strings | Traceability into the volume; `[]` if no reliable range |
| `suggested_tags` | array of strings | Keywords pulled from `main_ideas` only; `[]` if `main_ideas` is empty |

Hop fields are strings. There is no `system` field, no family field, no nested hop object inside `suggested_tags`. (`docs/prepare-llm-prompt.md` §§9, 16)

The live writer's hop object uses `end` instead of `end_position` and stores that hop **in** `suggested_tags`. (`HOP_FIELDS` in `bjj_pipeline/prepare.py`; `VALID_HOP` in `tests/test_prepare.py`)

## Starred hops (`*`)

Prompt rule (`docs/prepare-llm-prompt.md` §9): a trailing `*` (no space) marks a suggestion for remap. Star each field independently. A strong seed match that the chapter supports stays unmarked. Do not star a value that is both a seed match and supported. Prefer a starred value over leaving the field empty. `""` is only for no reasonable suggestion, and for `end_occupancy` on submissions.

The prompt's own starring examples are `mount*` and `Kick spin backtake*`.

Marcelo sample, five techniques:

| Chapter | `named_move` | `end_position` | Other hop fields |
|---|---|---|---|
| BUTTERFLY SWEEP PROCESS | `Butterfly sweep` | `half-guard` | all unmarked; `ruleset` `no-gi` |
| SHOOT & RESHOOT | `Butterfly sweep` | `mount*` | only end starred |
| FAR SIDE SWEEP TO COUNTER UNDERHOOK PASS | `Butterfly sweep*` | `mount*` | named move and end starred |
| 2-ON-1 SWEEP | `2-on-1 sweep*` | `mount*` | named move and end starred |
| KICK SPIN BACKTAKE | `Kick spin backtake*` | `back-control` | named move starred; `move_type` `back-take` unmarked |

`Butterfly sweep` is a seed named-move name (`docs/enrichment-seed/seed.json`). `2-on-1 sweep` and `Kick spin backtake` are not seed names; the latter is the prompt's starring example. `mount*` is used where the speech says get on top / hold top rather than naming mount.

No sample hop uses `""`. No sample stars `ruleset`, occupancy, `move_type`, or `start_position`. Speech in the sweep chapter says the underhook is not a gi grip; `ruleset` is still unmarked `no-gi`. The prompt would allow starring when volume implication is the only evidence (`docs/prepare-llm-prompt.md` §9, `ruleset`).

The live writer **cannot persist stars**. `_clean_hop` requires exact membership in seed ids / named-move names / `gi|no-gi|both`. A value `mount*` fails `end`/`end_position` membership and the hop is dropped. (`bjj_pipeline/prepare.py` `_clean_hop`; `tests/test_prepare.py` keeps only `VALID_HOP` and drops `named_move: "not-a-real-move"`)

## Empty `techniques` arrays

Prompt: if the chapter does not teach a sufficiently complete technique, return `techniques: []`. Conceptual, intro, posture, and grip chapters are not automatically techniques. Do not manufacture a row to fill the array. (`docs/prepare-llm-prompt.md` §§6, 16)

Sample empty chapters (all still have cleaned speech):

- INTRODUCTION
- HAND & FOOT POSITION
- MAINTAINING BUTTERFLY POSTURE
- ELBOW POSITIONING

Those four are the opening conceptual / posture / grip block. Empty `techniques` does not mean an empty chapter object. Ingest that skips empty arrays still needs the chapter for speech and neighbor context.

A different emptiness is **prepare skip**: volumes with no chapters, missing `chapters`, one chapter covering the whole recording, one partial chapter, or an untitled extra chapter are left unchanged. (`tests/test_prepare.py`; ADR 0004) Those volumes never receive `transcript_raw` or techniques.

## Time ranges

Prompt `source_time_ranges` (`docs/prepare-llm-prompt.md` §15):

- Array of strings
- Use only timestamps supplied in the input
- Preserve the input's timestamp format
- Separate ranges when instruction is noncontiguous
- Do not invent or extrapolate boundaries
- `[]` when a reliable range cannot be established
- Example in the prompt is clock time `"04:32-06:18"`

Chapter speech in this pipeline is not clock time. Prepare joins overlapping Whisper spans as `"<start> text"` with `start` formatted to two decimals (`bjj_pipeline/prepare.py` `_join_raw`). The sample's ranges follow that span format, not the prompt's `mm:ss` example:

- `"1036.24-1603.98"`
- `"1637.22-1869.25"`
- `"1908.40-2242.40"`
- `"2242.40-2565.04"`
- `"2596.78-2825.60"`

Each sample technique has **one** range. No empty range array appears on a populated technique. The range start is a span marker from `transcript_raw`, not necessarily `chapter.start`:

- BUTTERFLY SWEEP PROCESS chapter is `1055.0–1627.0`; range starts at `1036.24` (the overlap-copied previous span).
- 2-ON-1 SWEEP chapter is `2248.0–2580.0`; range starts at `2242.40` (again the overlap span).
- Range end is the last supporting span **start**, not `chapter.end` and not a span `end` (prepare's raw markers only store span starts).

`transcript_cleaned` has no timestamps (prompt §5; sample). Playback cannot be read from cleaned speech.

## Video keys

Three different keys exist. They are not interchangeable.

| Key | Where | Value |
|---|---|---|
| `video_file` | Transcribe / prepare volume JSON | Basename including extension. Written when missing, empty, or different from the library file. (`bjj_pipeline/batch_panoscribe.py`; README transcribe row) |
| `volume` (chapter field) | Prepare nest | Copy of that `video_file` string onto each chapter. Empty string if `video_file` is missing. (`prepare.py` `payload.get("video_file")`) |
| `volume` (sample root) | Marcelo sample | Same basename as the chapter `volume` the writer would store |
| `video_file_path` | Marcelo sample root only | Relative path from the instructional folder, Windows separators. **Not** written by transcribe or prepare |

`inspect_transcript` only knows `video_file`. It treats missing or `""` as `video_file_present: False`. It does not read `video_file_path`. (`bjj_pipeline/batch_panoscribe.py`)

Coach-app playback (out of ingest scope, cited only as a consumer of the basename) resolves `video_root / transcript_folder / video_file`. (`coach_app/citations.py` `resolve_video_playback`) The sample path is already the instructional-relative file; the pipeline key is basename only.

## Instructor / instructional / chapter keys

Live writer (`prepare.py`, `tests/test_prepare.py`):

- `instructional` — first path part under the corpus root (show folder)
- `instructor` — `tvshow.nfo` `<director>`, else first `<actor><name>`, else the suffix after ` by ` in the show folder, else `""`
- `volume` — `video_file` basename
- Chapter title field is `title`
- Neighbors are `previous_chapter` / `next_chapter` from adjacent `title`s

ADR 0004: chapter identity stays title, start, and end. Extra keys survive a later transcribe write only while those three still match. (`docs/adr/0004-store-chapter-speech-on-volume-json.md`; `tests/test_prepare_pipeline.py`)

`inspect_transcript` **rejects** a chapter that lacks a non-empty string `title`. (`batch_panoscribe.py`) The Marcelo sample uses `chapter_title` and would be `wrong shape` to that inspector, so `prepare_eligible` would skip it.

## Overlap copy in `transcript_raw`

ADR 0003: a Whisper span is copied whole into every chapter whose `[start, end]` overlaps it. Membership is overlap, not start-only. `transcript_raw` is not a partition of `segments`. (`docs/adr/0003-copy-straddling-spans-into-both-chapters.md`)

`prepare.py` `_overlaps`: `span.start <= chapter.end and span.end >= chapter.start`. Tests copy the 290–310 span into both Guard (`end` 300) and Pass (`start` 300). (`tests/test_prepare.py` `test_prepare_overwrites_in_place_and_copies_overlapping_span`)

The Marcelo sample shows the same copy on every chapter after the first: the first `<…>` marker is the previous chapter's last span, and that marker is **before** `chapter.start`. Cleaned speech repeats that overlap prose at the top of the later chapter. `source_time_ranges` can therefore start before the chapter clock.

A span that overlaps no chapter stays only in `segments` (ADR 0003). After the working-tree prepare drop of `segments`, that untitled extra speech is gone from the volume JSON.

When prepare re-pares an already nested file, `_spans_from_raw` rebuilds spans with `end = start` (the marker only). Overlap against chapter bounds is then not the original Whisper interval.

## What the live `--llm` writer persists instead

If ingest pointed at corpus JSON produced by current `prepare.py --llm`, the chapter would have:

- `transcript_cleaned`
- `suggested_tags`: list of hops `{start_position, start_occupancy, move_type, end, end_occupancy, named_move, ruleset}`
- no `techniques` array
- no `technique_steps`, `main_ideas`, `source_time_ranges`
- no `*`
- hops deduped across windows; invalid hops dropped (`_merge_hops`, `_clean_hop`)
- long chapters windowed: 4 spans per window, overlap 1 (`WINDOW_SPAN_COUNT`, `WINDOW_OVERLAP_SPANS`); cleaned text concatenated with spaces

`prepare_done(..., llm=True)` is true when every real chapter has string `transcript_cleaned`. It does not check for techniques. (`prepare.py` `prepare_done`)

Unusable completion: nest still writes `transcript_raw` and omits cleaned keys; process exit 1. (`tests/test_prepare.py` `test_unusable_completion_omits_cleaned_keys`)

## Gaps (ingest-relevant)

1. **Writer vs prompt.** The glossary, `docs/prepare-llm-prompt.md`, and the Marcelo sample describe extracted techniques as `techniques[]` objects. `prepare.py --llm` still writes hop objects into `suggested_tags` with field `end`. A corpus produced by the live writer does not contain extracted-technique rows as defined in `GLOSSARY.md`.
2. **Title key.** Pipeline and inspector: `title`. Sample: `chapter_title`. Sample JSON is not a legal transcript to `inspect_transcript`.
3. **Video key.** Pipeline: `video_file` basename. Sample: `video_file_path` relative path, no `video_file`.
4. **Credit placement.** Writer: instructor / instructional / volume on every chapter. Sample: those three on the volume root; chapters have no instructor key.
5. **Starring.** Prompt and sample use `*`. Live `_clean_hop` drops starred values.
6. **Steps and ideas.** Prompt/sample have `technique_steps` and `main_ideas`. Live writer has neither. Glossary extracted technique "carries … the mechanical steps, and the times in that volume where it is shown" — those fields exist only in the prompt/sample shape.
7. **Time format.** Prompt example is `mm:ss`; actual chapter speech and the sample use Whisper-start floats `"1036.24-1603.98"`. Ranges can start before `chapter.start` because of overlap copy. There is no per-showing list, only ranges. Span **end** times are not in `transcript_raw`.
8. **Empty techniques vs skipped volumes.** Empty `techniques: []` is valid teaching-less speech. Volumes prepare refuses to nest never get chapter speech at all.
9. **No technique id.** Same named move can repeat across chapters. Index in the chapter array is the only local discriminator in the sample.
10. **`segments`.** ADR 0004 keeps them. Working-tree prepare and the sample delete them. Overlap reconstruction from `transcript_raw` markers is start-only.
11. **Windowing vs one chapter object.** Live `--llm` may stitch several model calls into one `transcript_cleaned`. The sample is one cleaned string and at most one technique per chapter; it does not show multi-technique chapters or window artifacts.
12. **Allow-list vs suggestion.** Live writer refuses unknown names. Prompt requires a starred suggestion rather than omitting the hop. Ingest of live `--llm` output under-counts teaching that the prompt would keep as starred rows.
13. **`suggested_tags` meaning flipped.** Prompt/sample: keyword strings from `main_ideas`. Writer: hop objects. Ingest cannot key on that name without checking element type.
14. **Chapter speech is not the curated store.** ADR 0004: chapter speech is not a cleaned statement and does not enter the curated store. Extracted techniques are pre-accept findable rows (`GLOSSARY.md`).

## Trust rule for later ingest

Trust **extracted-technique fields** from the prompt + sample shape (`techniques[]` with the eleven fields above, including `*` and empty arrays). Trust **chapter speech nesting, overlap copy, credits, and `video_file` basename** from `prepare.py` + ADRs 0003/0004 + `tests/test_prepare.py`. Do not assume a volume on disk has both until a writer actually merges the prompt output onto the nested chapter objects using `title` and `video_file`.
