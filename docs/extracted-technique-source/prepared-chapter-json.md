# Prepared chapter JSON for extracted techniques

Research for [Research: Prepared chapter JSON and extracted-technique fields](https://github.com/djsciman/video_transcriber_rag/issues/102). Re-performed 2026-11-25 against the live corpus at `C:\Users\dumbo\Documents\GitHub\bjj_transcripts\library` and `v2` at `479d2c1`.

This note records the schema a later ingest can trust. It does not recommend a storage engine.

## Sources

- Glossary **Extracted technique**, `GLOSSARY.md` (`f3cf7ac`)
- Combined spec `docs/prepare-llm-prompt.md`
- Staged cleanup spec `docs/prepare-llm-cleanup.md`
- Staged extract spec `docs/prepare-llm-extract.md`
- Marcelo sample `docs/samples/butterfly-marcelo-s01e01-pare.json`
- Live writer `bjj_pipeline/prepare.py` (`TECHNIQUE_STRINGS`, `TECHNIQUE_LISTS`, `_normalize_technique`, `_enrich_staged`, `_derive_tags`)
- ADR 0003 (overlap copy), ADR 0004 (chapter speech on volume JSON), ADR 0005 (staged skip)
- Live walk of 558 volume JSON files; 50 shuffled volumes that have both non-empty `transcript_cleaned` and at least one non-empty `techniques` array (listed at the end)

## Grain

One findable row is one object in a chapter `techniques` array. It is not a Technique lesson and not an accepted citation (`GLOSSARY.md`).

A chapter may hold several independently taught movements, or none. Empty `techniques: []` is valid on conceptual / posture / theory chapters. There is no technique-level id. Ingest identity is volume key + chapter `title` + `start` + `end` + index in that chapter's `techniques` array. Named-move text is not unique: the same seed name can appear in several chapters.

On the 50 filled samples, 86 of 496 chapters have `techniques: []` while still holding cleaned speech, `concepts`, and keyword `suggested_tags`. Example: Danaher GFF Half Guard S01E05 chapter "The 90 Degree Rule" is cleaned theory with three `concepts` and `techniques: []`. The next chapter, "The Knee Lift", has one technique object.

## What ingest can trust on live corpus JSON (2026-11-25)

The November 19 finding that `prepare.py --llm` wrote seed-only hops into `suggested_tags` and had no `techniques` array is **stale**. On `v2`, staged `--llm` persists the prompt/sample technique object.

### Volume object (live)

Every one of 558 files has:

| Key | Type | Notes |
|---|---|---|
| `video_file` | string | Basename with extension, e.g. `Half Guard - Go Further Faster by John Danaher - S01E05 - The Single Most Important Section of this Video.mp4` |
| `chapters` | array | May be empty |
| `language` | string | Always `"en"` in this walk |

No live volume has `video_file_path`. Five volumes still have a top-level `segments` list (four Couch Finishing Leg Locks with empty `chapters`; one Tonon volume with nine titled chapters and no cleaned speech). Prepare pops `segments` after a successful nest (`payload.pop("segments", None)`).

### Chapter object (live)

Chapter identity is `title` / `start` / `end`. Live files never use `chapter_title`. Credits live on **each chapter**, not on the volume root.

| Key | Type | Role |
|---|---|---|
| `title` | string | Chapter identity |
| `start` / `end` | float seconds | Chapter clock on the volume |
| `instructor` | string | From NFO / folder ` by `, e.g. `John Danaher` |
| `instructional` | string | Show name from the corpus path, e.g. `Half Guard - Go Further Faster by John Danaher` (not the short Jellyfin folder `Danaher - GFF Half Guard`) |
| `volume` | string | Same as payload `video_file` (confirmed on all 496 chapters in the 50 samples) |
| `previous_chapter` / `next_chapter` | string | Neighbor `title`; `""` on first previous and last next |
| `transcript_raw` | string | Overlap-copied Whisper spans as `"<ss.ss> text"` |
| `transcript_cleaned` | string | Prose; timestamps stripped |
| `concepts` | array of strings | Coach/advisor points for the chapter |
| `suggested_tags` | array of strings | Keywords derived from `concepts` (staged path) |
| `techniques` | array of objects | Extracted techniques; may be `[]` |

No extra chapter keys appeared in the 558-file walk.

`transcript_raw` follows ADR 0003: a span that starts in the previous chapter is copied whole into the next. In the 50 samples, 422 of 496 chapters have at least one `<sec>` stamp **before** `chapter.start`. Zero chapters had a stamp after `chapter.end`. Example: "The Knee Lift" starts at `247.0` but `transcript_raw` opens with `<235.28>`. `transcript_cleaned` never keeps those angle-bracket stamps (0 of 496).

### Extracted-technique object (live writer + 50 samples)

`_normalize_technique` keeps only these fields. Extra keys from the model are dropped. Missing values become `""` or `[]`.

| Field | Type | Role |
|---|---|---|
| `named_move` | string | Chapter-derived or seed name; trailing `*` is a remap guess |
| `ruleset` | string | `gi`, `no-gi`, `both`, optionally with `*` |
| `move_type` | string | Seed type, or that type with `*` |
| `start_occupancy` | string | `top`, `bottom`, `neutral`, optionally with `*` |
| `start_position` | string | Seed position ID, or a short label with `*` |
| `end_occupancy` | string | `top` / `bottom` / `neutral` / `""` for submissions, optionally with `*` |
| `end_position` | string | Seed position or submission ID, or a label with `*` |
| `technique_steps` | string | Numbered mechanical sequence |
| `main_ideas` | string | Two or three imperative sentences |
| `source_time_ranges` | array of strings | Showing ranges; usually `[]` on the live corpus (see below) |
| `suggested_tags` | array of strings | Keywords derived from `main_ideas` (staged path) |

Hops sit **on the technique object**. They are not nested inside `suggested_tags`. Chapter `suggested_tags` and technique `suggested_tags` are keyword strings, not hop objects. Across the whole corpus: 4001 chapters have string tags, 478 have `[]`; 4810 techniques have string tags, 568 have `[]`. Zero dict-shaped tags.

Star is a trailing `*` with no space. Corpus-wide starred hop counts:

| Field | Starred values |
|---|---|
| `ruleset` | 1839 |
| `end_position` | 1359 |
| `start_position` | 1096 |
| `move_type` | 623 |
| `start_occupancy` | 169 |
| `end_occupancy` | 109 |
| `named_move` | 64 |
| **total** | **5259** |

Live values that leave the seed lists still appear: `move_type` `pin` (unstarred) and `drill*` in the 50 samples; `ruleset` `"*"` eight times. Ingest should treat `*` as a remap flag on whatever string precedes it, including a bare `"*"`.

Concrete row (Danaher GFF Half Guard S01E05, "The Knee Lift"):

```json
{
  "named_move": "Knee Lift",
  "ruleset": "both",
  "move_type": "transition",
  "start_occupancy": "bottom",
  "start_position": "half-guard",
  "end_occupancy": "bottom",
  "end_position": "half-guard",
  "technique_steps": "1. From half guard bottom …",
  "main_ideas": "Bend his leg 90 degrees and shift to the ankle.\nPoint your hips at the ceiling to lift his knee off the mat.\nOnce his knee is up, slide your leg underneath.",
  "source_time_ranges": [],
  "suggested_tags": ["Once his knee is up", "slide your leg underneath"]
}
```

A starred sibling in the same volume ("The Hip Shift"): `named_move` `Tight Waist Roll-Through Sweep`, `ruleset` `both*`, `end_position` `half-guard*`.

## Sample vs live (remaining deltas)

The Marcelo sample is still a useful **technique-object** example. It is not a live volume.

| Topic | Marcelo sample | Live corpus / `prepare.py` |
|---|---|---|
| Video identity | `video_file_path` + volume-root `volume` / `instructional` / `instructor` | Top-level `video_file` only; credits on every chapter; no `video_file_path` |
| Chapter title key | `chapter_title` | `title` |
| `concepts` | not on the sample chapter | chapter array of strings |
| Chapter `suggested_tags` | omitted on sample chapters | keyword strings from `concepts` |
| Technique hops / steps / ideas | same eleven fields | same eleven fields |
| `source_time_ranges` | nest seconds, one filled range per extracted move | almost always `[]` |
| `segments` | absent | popped after nest; 5 unprepared volumes still have them |

Trust extracted-technique **fields** from the live writer + filled volumes. Trust overlap / `video_file` / chapter `title` from prepare + ADRs 0003/0004. Do not require `video_file_path` or `chapter_title` at ingest.

## `source_time_ranges` gap

Specs disagree, and the staged default empties the field.

- Combined prompt §15 examples are clock strings (`04:32-06:18`) and say "preserve the timestamp format supplied by the input."
- Extract spec requires nest-style seconds (`["1234.00-1560.00"]`) and forbids clock strings.
- Cleanup strips `<sec>` timestamps before extract. Extract then sees cleaned speech with no stamps, so it must return `[]`.

Corpus walk: **5315** techniques have `source_time_ranges: []`; **63** have a single seconds-dash string. No clock strings. In the 50 samples only two ranges exist: `"0.00-0.00"` (unusable) and `"1680.00-2040.00"`.

Ingest can store the array as written. Playback cannot treat it as a reliable showing list until a later processing ticket fills starts from `transcript_raw` stamps or `chapter.start`. Sibling [Research: Video playback tie-back from volume files and time ranges](https://github.com/djsciman/video_transcriber_rag/issues/104) records the join keys.

## Prompt / writer notes that affect ingest

- Staged skip (ADR 0005): cleanup is done when `transcript_cleaned` is a string; extract is done when `concepts` is a list. `suggested_tags` is derived in process from `concepts` / `main_ideas`, not kept from the model.
- One-call skip still wants `transcript_cleaned` + `concepts` + `suggested_tags` as lists (`_chapter_has_llm`).
- `_normalize_technique` does not validate seed allow-lists. Starred and unlisted values persist.
- Volumes with no real chapters are left unchanged (empty `chapters` or untitled). One named chapter, including a whole-recording chapter, is nested.

## Fifty filled samples

Shuffled walk (`random.Random(20261125)`), first 50 volumes with at least one non-empty `transcript_cleaned` and at least one non-empty `techniques` array. Schema union across these 50 matches the live writer table above.

- `Danaher - GFF Half Guard\Season 01\Half Guard - Go Further Faster by John Danaher - S01E05 - The Single Most Important Section of this Video.json`
- `Danaher - GFF Guard Retention\Season 01\Guard Retention - Go Further Faster by John Danaher - S01E06 - Double-Under and Over-Under Pass.json`
- `Danaher - GFF HG Pass Pins\Season 01\Half Guard Passing and Dynamic Pins - Go Further Faster by John Danaher - S01E04 - Passing Half Guard.json`
- `Danaher - FTF 2\Season 01\Feet To Floor Volume 2 by John Danaher - S01E07 - Sasae Tsuri Komi Ashi.json`
- `Danaher - NW Side Attacks\Season 01\New Wave Jiu Jitsu Side Attacks - Building a Devastating Side Control System by John Danaher - S01E08 - Volume 8.json`
- `Danaher - ETS Back Attacks\Season 01\Back Attacks Enter The System by John Danaher - S01E03 - Back Attacks.json`
- `Wardzinski - NG Bfly Rediscovered\Season 01\The No Gi Butterfly Guard Rediscovered by Adam Wardzinski - S01E03 - Volume 3.json`
- `Danaher - NW OG Foundations\Season 01\New Wave Jiu Jitsu Open Guard The two Foundations Of Guard Play by John Danaher - S01E04 - Volume 4.json`
- `Danaher - GFF Open Guard\Season 01\Open Guard - Go Further Faster by John Danaher - S01E02 - Balancing Guard Retention with Guard Offense.json`
- `Wardzinski - PP Mount\Season 01\Polish Power Full Mount by Adam Wardzinski - S01E02 - Volume 2.json`
- `Rodriguez - Jay Rods Judo\Season 01\Jay Rods Judo by Jay Rodriguez - S01E02 - Volume 2.json`
- `Stevens - Scientific Gripping\Season 01\Scientific Gripping Systems For Jiu Jitsu by Travis Stevens - S01E03 - Volume 3.json`
- `Danaher - ETS Front Headlock\Season 01\The Front Headlock System by John Danaher - S01E02 - Front Headlock.json`
- `Danaher - FTF 1\Season 01\Feet To Floor Volume 1 Fundamental Standing Skills by John Danaher - S01E04 - Collar Drag (Uki Waza).json`
- `Danaher - FTF 3\Season 01\Feet To Floor Volume 3 by John Danaher - S01E08 - Special Topics.json`
- `Danaher - NW 4x4 Mount\Season 01\New Wave Jiu Jitsu Mounted Pin Attacks - The 4x4 Mount System by John Danaher - S01E06 - Volume 6.json`
- `Wardzinski - Bfly Rediscovered 2\Season 01\Butterfly Guard Re-Discovered 2 by Adam Wardzinski - S01E01 - Volume 1-pt1.json`
- `Faria - Side Control\Season 01\Side Control Setups & Submissions by Bernardo Faria - S01E02 - Volume 2.json`
- `Stevens - Magic Guard Passing\Season 01\Magic Guard Passing by Travis Stevens - S01E01 - Volume 1.json`
- `Danaher - S2G Upper Body\Season 01\Standing2Ground Upper Body Takedowns by John Danaher - S01E08 - Volume 8.json`
- `Danaher - S2G Upper Body\Season 01\Standing2Ground Upper Body Takedowns by John Danaher - S01E07 - Volume 7.json`
- `Mica Galvao - Back Attacks\Season 01\Galvao Style Back Attacks by Mica Galvao - S01E01 - Volume 1.json`
- `DeBlass - Submission Escapes\Season 01\Submission Escapes by Tom DeBlass - S01E03 - Volume 3.json`
- `Danaher - Fastest Sub Pct\Season 01\The Fastest Way by John Danaher - S01E03 - Volume 3.json`
- `Cornelius - Worm Guard\Season 01\Worm Guard Legacy by Keenan Cornelius - S01E04 - Bonus 2.json`
- `Ryan - SysAtk The Guard\Season 01\Systematically Attacking The Guard by Gordon Ryan - S01E02 - Volume 2.json`
- `Danaher - GFF Closed Guard\Season 01\Closed Guard - Go Further Faster by John Danaher - S01E05 - Hip Sweep.json`
- `Danaher - GFF Open Guard\Season 01\Open Guard - Go Further Faster by John Danaher - S01E08 - Kouchi Gari.json`
- `Ryan - HiPerc Gi Passes\Season 01\High Percentage Gi Passes by Gordon Ryan - S01E02 - Volume 2.json`
- `Wardzinski - Foot Sweeps\Season 01\Foot Sweeps, Ankle Picks and Tripods Engineering by Adam Wardzinski - S01E04 - Volume 4.json`
- `Ryan - SysAtk Seated OG\Season 01\Systematically Attacking From Open Guard Seated Position by Gordon Ryan - S01E05 - Volume 5.json`
- `Giles - Chokes NG\Season 01\Chokes No Gi by Lachlan Giles - S01E02 - Volume 2.json`
- `Ryan - SysAtk Seated OG\Season 01\Systematically Attacking From Open Guard Seated Position by Gordon Ryan - S01E06 - Volume 6.json`
- `Wardzinski - PP Mount\Season 01\Polish Power Full Mount by Adam Wardzinski - S01E01 - Volume 1.json`
- `Danaher - GFF Open Guard\Season 01\Open Guard - Go Further Faster by John Danaher - S01E06 - Cross Collar and Bicep Guard.json`
- `Arm Bars Enter The System by John Danaher\Season 01\Arm Bars Enter The System by John Danaher - S01E04 - Arm Bar.json`
- `Faria - BT Pressure Passing\Season 01\Battle Tested Pressure Passing by Bernardo Faria - S01E01 - Volume 1.json`
- `Jones - Triangle Machine\Season 01\The Triangle Machine by Craig Jones - S01E01 - Volume 1.json`
- `Andre Galvao - Passing Modern Guard\Season 01\Passing Modern Guard by Andre Galvao - S01E02 - Volume 2.json`
- `Higashi - NG Judo Throws\Season 01\No-Gi Judo Throws by Shintaro Higashi - S01E01 - Volume 1.json`
- `Danaher - GFF HG Pass Pins\Season 01\S01E06 - Dynamic Pins Part One.json`
- `Danaher - GFF Guard Retention\Season 01\Guard Retention - Go Further Faster by John Danaher - S01E04 - The 2nd Skill of Guard Retention.json`
- `Andre Galvao - Passing Modern Guard\Season 01\Passing Modern Guard by Andre Galvao - S01E01 - Volume 1.json`
- `Danaher - GFF Strangles Turtle\Season 01\Strangles & Turtle Breakdowns - Go Further Faster by John Danaher - S01E04 - Kata Juji Jime Open Guard and Spinning Juji Jime.json`
- `Giles - NG OG 1 K Guard\Season 01\No Gi Open Guard Volume 1 K Guard by Lachlan Giles - S01E01 - Volume 1.json`
- `Jones - Make Z Guard\Season 01\Make Z Guard Great Again by Craig Jones - S01E04 - Volume 4.json`
- `Wardzinski - Bfly Rediscovered\Season 01\Butterfly Guard Re-Discovered by Adam Wardzinski - S01E01 - Volume 1.json`
- `Danaher - ETS Kimura\Season 01\Kimura Enter The System by John Danaher - S01E05 - Kimuras.json`
- `Cornelius - Worm Guard\Season 01\Worm Guard Legacy by Keenan Cornelius - S01E03 - Bonus 1.json`
- `Danaher - NW 4x4 Mount\Season 01\New Wave Jiu Jitsu Mounted Pin Attacks - The 4x4 Mount System by John Danaher - S01E03 - Volume 3.json`
