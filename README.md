# video_transcriber_rag

Two pieces of work for the same coach: a **corpus-prep pipeline** that organizes local BJJ instructionals and transcribes their speech, and a **coach-only advising package** (`coach_app`) that curates those transcripts into a local store and helps the coach teach one topic through to performance under resistance.

The coach is the only person who uses the application. Students never query it. Domain language lives in [`GLOSSARY.md`](GLOSSARY.md). Architecture decisions live in [`docs/adr/`](docs/adr/). The written spec is [issue #52](https://github.com/djsciman/video_transcriber_rag/issues/52).

## What this repo does

### Corpus-prep pipeline (`bjj_pipeline`)

Organizes local instructionals against [BJJ Fanatics](https://bjjfanatics.com/) product pages, detects and embeds chapter markers on volumes, and batch-transcribes speech with [panoscribe](https://pypi.org/project/panoscribe/). A volume is in the **corpus** as soon as it is transcribed. It reaches the **curated store** only after the coach accepts citations.

| Command | Purpose |
|--------|---------|
| `py -3 -m bjj_pipeline run` | One command: match, organize, detect, transcribe, prepare (skip finished work; `--apply` to write) |
| `py -3 -m bjj_pipeline organize` | Scrape a BJJ Fanatics product page and reorganize a local folder as a Jellyfin/TMM TV show (NFO, artwork, volumes, named chapters) |
| `py -3 -m bjj_pipeline match` | Match local folder names to BJJ Fanatics product URLs and write `bjjfanatics_matches.csv` |
| `py -3 -m bjj_pipeline chapters` | Detect title-card chapter starts, OCR titles, write sidecar CSVs, optionally embed chapters into the video |
| `py -3 -m bjj_pipeline transcribe` | Walk a video tree and complete each transcript: speech only when missing, container chapters, and `video_file` |
| `py -3 -m bjj_pipeline scan` | Report library completeness (combined volumes, named chapters, NFO, playback, transcripts) and write a markdown drill-down |

### Coach-only advising (`coach_app`)

Python package imported from the repository root. There is no CLI yet. One [`CuratedStore`](coach_app/store.py) is the seam: the coach writes records, the **advisor** reads them. Tests inject a stand-in advisor; they do not name a vendor.

| Module | Purpose |
|--------|---------|
| `coach_app.store` | Local curated-store facade (instructionals, volumes, citations, topics, enrichment, units) |
| `coach_app.cleanup` | Nest speech under real chapters on a raw volume. Writes nothing to the store |
| `coach_app.statements` | Propose cleaned statements from a cleaned volume. Writes nothing to the store |
| `coach_app.citations` | Instructional ruleset, statement edits, playback path |
| `coach_app.enrichment` | Unify the enrichment seed; occupancy for named-move paths |
| `coach_app.topics` | Open or remove a topic; mark and welcome other-ruleset showings |
| `coach_app.placement` | Place citations on named moves; coach-authored citations |
| `coach_app.briefing` | Briefing memo for a topic (same-ruleset citations, caveats, disagreement) |
| `coach_app.system` | Choose how the topic is taught; set-asides; live-read system conflicts |
| `coach_app.design` | Design the unit on the mental map (named moves, systems, occupancy) |
| `coach_app.build` | Pack the map into a first Draft of classes and lessons |
| `coach_app.edit` | Edit the unit sheet (add, remove, drag, purpose lines) |
| `coach_app.library` | Custom lessons and unit history (copy to re-teach) |
| `coach_app.print_packet` | Duplex packet as page records (no PDF renderer in this package) |

Supporting material:

- `GLOSSARY.md` — coaching and instructional vocabulary
- `docs/adr/` — architecture decision records
- `docs/enrichment-seed/` — consensus seed imported into the live catalog
- `docs/volumes-awaiting-parse.md` — raw corpus volumes not yet curated
- `docs/agents/` — how agents use the issue tracker, labels, and domain docs
- `tests/` — pipeline tests (no ffmpeg, GPU, or real panoscribe) and `coach_app` tests at the store facade
- `metadata_scraper/tests/` — pytest suite for scrape, match, NFO, layout, and organize

Video files and transcript JSON typically live **outside** this repo. The curated store in this package is an in-process object; persistence is not part of the public API.

## Prerequisites

### System tools

- **Python 3.12+** (on Windows use the launcher: `py -3`)
- **ffmpeg** and **ffprobe** on `PATH` (required for chapter detection, embedding, reading container chapters, and `metadata_scraper` concat/remux)
- **panoscribe** installed for the same Python interpreter (required only for batch transcription)

### Python packages

Install the pipeline package with extras. `organize` is scrape/NFO/concat; `transcribe` is speech and title-card OCR; `all` is both:

```powershell
py -3 -m pip install -e ".[all]"
```

`transcribe` pulls in `numpy`, `opencv-python-headless`, `rapidocr`, and `panoscribe`. `panoscribe` also pulls in faster-whisper (and typically needs a CUDA-capable GPU for comfortable speed; CPU works but is slow). Chapter title OCR uses RapidOCR; speech OCR in panoscribe is off by default in the batch command.

`organize` pulls in `beautifulsoup4` and `lxml`. The scraper talks to BJJ Fanatics over HTTPS; ffmpeg is used when concatenating chapter files into volumes or remuxing chapter markers.

`coach_app` needs only the standard library at import time. Tests use `pytest` (`py -3 -m pip install pytest`, also listed in `metadata_scraper/requirements.txt`).

## Getting started

1. Clone the repository and open a shell in the repo root.
2. Confirm Python and ffmpeg:

   ```powershell
   py -3 --version
   ffmpeg -version
   ffprobe -version
   ```

3. Install the Python packages:

   ```powershell
   py -3 -m pip install -e ".[all]"
   ```
4. Confirm panoscribe (for transcription):

   ```powershell
   panoscribe --help
   ```

5. Run the unit tests:

   ```powershell
   py -3 -m pytest tests -q
   py -3 -m pytest metadata_scraper -c metadata_scraper\pytest.ini -v
   ```

`coach_app` has no install extra. Import it from the repository root. Install `pytest` if it is missing: `py -3 -m pip install pytest`.

## Coach-only advising

The pipeline leaves completed volume JSON on disk. `coach_app` reads that JSON, proposes cleaned statements, and admits citations the coach accepts into `CuratedStore`. Later steps (topic, briefing, Design, Build, Edit, print) all go through that store.

### Curation from a raw volume

`cleanup_volume` turns completed corpus JSON into a part list. `propose_statements` asks the advisor to draft cleaned statements and returns them without writing the store. `store.accept` is the write.

```python
import json
from pathlib import Path

from coach_app.cleanup import cleanup_volume
from coach_app.statements import StatementDrafter, propose_statements
from coach_app.store import CuratedStore

store = CuratedStore()
seed = json.loads(
    Path("docs/enrichment-seed/seed.json").read_text(encoding="utf-8")
)
store.import_enrichment_seed(seed)

raw = json.loads(Path(r"path\to\transcript.json").read_text(encoding="utf-8"))
cleaned = cleanup_volume(raw)
proposals = propose_statements(
    cleaned, StatementDrafter(), instructor="Instructor Name"
)
if proposals:
    citation = store.accept(
        proposals[0],
        instructional="Instructional Name",
        video_file=raw["video_file"],
        ruleset="gi",
    )
    store.correct(citation, movement="Closed guard")
```

`StatementDrafter` is the in-repo stand-in that drafts from the cleaned part. Tests inject their own advisor. Replace that collaborator when you wire a real advisor; keep the `draft(...)` shape the tests use.

Correct and remove after accept:

```python
store.correct(citation, step_bullets=("Frame the far hip.", "Cut the knee."))
store.remove(citation)
```

Playback uses the volume file name on the citation plus a video root and the transcript folder:

```python
playback = store.resolve_playback(
    citation,
    citation.showings[0],
    video_root=r"path\to\video-library",
    transcript_folder=r"path\to\transcript-corpus\that-show",
)
# playback.path, playback.speech_start, playback.available
```

### Topic, placement, briefing, Design, Build

```python
from coach_app.briefing import BriefingAdvisor, brief_topic
from coach_app.build import BuildAdvisor, convert
from coach_app.design import add_named_move, open_design
from coach_app.edit import class_cards, open_sheet
from coach_app.placement import PlacementAdvisor, enter_citations
from coach_app.print_packet import packet
from coach_app.system import choose_system
from coach_app.topics import open_topic

topic = open_topic(store, "Closed guard", "gi")
stored, placement = enter_citations(
    store, store.citations(), PlacementAdvisor()
)
memo = brief_topic(store, topic.name, topic.ruleset, BriefingAdvisor())
choose_system(store, topic, "tight waist")

named = next(
    node
    for node in store.search_enrichment("hip bump")
    if node.kind == "named move"
)
session = open_design(topic_name=topic.name, topic_ruleset=topic.ruleset)
session = add_named_move(store, session, named.id)
result = convert(store, session, BuildAdvisor())
if result.draft is not None:
    sheet = open_sheet(store, result.draft, mode="edit")
    cards = class_cards(store, sheet)
    pages = packet(session, sheet, store)
```

`enter_citations`, `brief_topic`, and `convert` take an advisor collaborator. The classes above are the in-repo stand-ins the tests use. `class_cards` is the class-card layout. `packet` returns page records (canvas landscape, then one portrait class card per class); rendering a PDF is out of this package. `convert` writes a Draft when the map is packable.

Search and browse the live enrichment catalog (the seed is copied once; later coach edits stay on the store):

```python
store.search_enrichment("hip bump")
store.browse_hierarchy()  # starting positions
store.rename_enrichment_node(node_id, "Hip bump sweep")
```

Custom lessons save when placed on a unit. Unit history is a snapshot the coach can copy to re-teach (`coach_app.library`).

### Coach-app tests

Tests assert through the public facade. They use fixtures and a stand-in advisor. They do not open video, run speech, or drive a browser.

```powershell
py -3 -m pytest tests/test_curated_store.py tests/test_cleanup.py tests/test_propose_statements.py tests/test_enrichment.py tests/test_citations.py tests/test_topics.py tests/test_placement.py tests/test_briefing.py tests/test_system.py tests/test_design.py tests/test_build.py tests/test_edit.py tests/test_library.py tests/test_print_packet.py -q
```

## Typical pipeline workflow

Order is **match → organize (concat into volumes) → detect if needed → transcribe → prepare**.

One command walks top-level instructional folders. Default stages are **match, organize, detect, transcribe, prepare**. Detect skips a volume that already has container chapters or a sidecar chapter file. A season that still looks like uncombined chapter files warns and skips detect unless `--force-stage detect`. Visual embed stays opt-in (`--embed`); `--apply` writes detect sidecars only.

### One pipeline command

Dry-run a library (prints SKIP / RUN / FAIL; writes nothing; does not decode, Whisper, or call Ollama):

```powershell
py -3 -m bjj_pipeline run --library "path\to\instructionals" --corpus "path\to\transcript-corpus"
```

Apply match, organize, detect, transcribe, and prepare. `--embed` is a separate flag for visual sidecar remux; `--apply` does not embed.

```powershell
py -3 -m bjj_pipeline run --library "path\to\instructionals" --corpus "path\to\transcript-corpus" --apply
```

| Flag | Meaning |
|------|---------|
| (omit `--apply`) | Dry run: print SKIP / RUN / FAIL, no writes, no decode, no speech, no Ollama |
| `--apply` | Write match CSV, organize volumes, detect sidecars, transcripts, and chapter speech. Does **not** embed chapter sidecars |
| `--embed` | Visual remux of sidecar chapter files into volumes. Opt-in; not implied by `--apply` |
| `--force` | Re-run every selected stage even when its artifact exists |
| `--force-stage match\|organize\|detect\|transcribe\|prepare` | Re-run only that unit |
| `--matches` | Match CSV path (default: `LIBRARY/bjjfanatics_matches.csv`) |

Skip unless `--force` / `--force-stage`:

| Stage | Skip when |
|-------|-----------|
| match | That folder already has a product URL in the match CSV |
| organize | The show folder already has `tvshow.nfo` **and** at least one `Season ##` folder |
| detect | The volume already has container chapters, or a sidecar chapter file exists. Uncombined chapter-file seasons warn and skip unless `--force-stage detect` |
| transcribe | The mirrored corpus JSON already has a `segments` list (empty list counts as finished) |
| prepare | Every real chapter on the mirrored corpus JSON already has `transcript_cleaned` |

A CSV product URL is the organize URL with no yes/no prompt. One product URL per instructional folder. Missing URL outside a terminal fails that instructional's organize. Leftover multi-instructional bundle folders are out of this pipeline; flatten them by hand.

Organize concatenates per-chapter downloads into volumes (Fanatics titles; starts from each source file's duration). There is no operator path that splits a volume into chapter files or splits a bundle show.

Transcribe walks the **post-organize** tree (combined volumes under `Season ##`). Corpus JSON mirrors that tree under `--corpus`. A corpus written from pre-concat chapter files is not skip-stable after concat.

Prepare updates that existing corpus JSON in place after transcribe. Whisper `segments` stay. Skip when every real chapter already has `transcript_cleaned`. Dry-run does not call Ollama; `--force` or `--force-stage prepare` re-runs chapter speech.

| Variable | Default | Meaning |
|----------|---------|---------|
| `BJJ_LLM_BASE_URL` | `http://localhost:11434/v1` | Local Ollama base URL |
| `BJJ_LLM_MODEL` | `qwen3.5:4b` | Local model tag. Operators may set `qwen3:4b-instruct` if that tag is missing |

Repair of an already-organized show stays `py -3 -m bjj_pipeline organize --repair`; it is not a pipeline stage.

### Detect if needed

The pipeline detect stage is the default walk: one start-and-title sample per volume, sidecar only. Review the CSVs, then optionally embed. For a single volume outside the pipeline:

```powershell
py -3 -m bjj_pipeline chapters "path\to\Season 01\S01E01 - Volume 1.webm" 000000
py -3 -m bjj_pipeline chapters --apply "path\to\Season 01\S01E01 - Volume 1.webm"
```

Pipeline `--embed` is the same visual remux, still opt-in after `--apply`.

## Pipeline usage

All commands below are run from the repository root. On Windows prefer `py -3`; bare `python` may be the Windows Store stub.

### Organize instructionals

`py -3 -m bjj_pipeline organize` scrapes a BJJ Fanatics product page and reorganizes a local show folder for Jellyfin / TinyMediaManager: `tvshow.nfo`, posters, `Season ##` folders, episode NFO, and (when timestamps exist) named chapter markers. Default is a dry-run.

Dry-run one show (searches Fanatics and asks you to confirm the URL in a terminal):

```powershell
py -3 -m bjj_pipeline organize --folder "path\to\Show Title by Instructor"
```

Pass the product URL when you already know it:

```powershell
py -3 -m bjj_pipeline organize --folder "path\to\Show Title by Instructor" --url "https://bjjfanatics.com/products/the-handle"
```

Write files:

```powershell
py -3 -m bjj_pipeline organize --folder "path\to\Show Title by Instructor" --url "https://bjjfanatics.com/products/the-handle" --apply
```

One product URL per instructional folder (not keyed per-season URLs). Chapter downloads are always concatenated into volumes with Fanatics chapter titles when names exist (starts from each source file's duration). Leftover bundle folders with several instructionals inside are not organized as one show.

Useful flags:

| Flag | Default | Meaning |
|------|---------|---------|
| `--apply` | off | Write files. Without it, print the plan and exit |
| `--url` | search + confirm | Product URL for this instructional folder |
| `--container` | `keep` | Keep the original container, or remux/concat to `mkv` |
| `--extras-policy` | `extras` | Move unmatched leftover videos into `extras/`, or `skip` to leave them |
| `--skip-chapters` | off | Do not inject chapter markers. Segmented files still concatenate into volumes |
| `--season-order` | publish date | Comma-separated child folder names overriding season numbers |
| `--repair` | off | Scan the show, print a checklist, and apply only the fixes you confirm |
| `--repair-steps` | prompt | With `--repair`, apply `all` or letters such as `"B, C"` without a prompt |
| `--json` | off | Print the plan as JSON |
| `--ffmpeg` / `--ffprobe` | `PATH` | Override binaries |

Repair an already-organized show (checklist on stderr; confirm letters, or pass `--repair-steps`):

```powershell
py -3 -m bjj_pipeline organize --folder "path\to\Show Title by Instructor" --repair
py -3 -m bjj_pipeline organize --folder "path\to\Show Title by Instructor" --repair --repair-steps all
```

Repair letters: **B** show NFO and artwork, **C** season folders, **D** combine chapter clips, **E** write chapter markers, **F** rename episodes and write episode NFO, **G** move leftovers into `extras/`.

### Match folders to Fanatics URLs

`py -3 -m bjj_pipeline match` searches BJJ Fanatics for each top-level folder under `--library` and writes `folder_path,product_url` CSV to `--output`. Folders that already have a product URL in that CSV are skipped unless `--force`. The pipeline command uses the same CSV as organize's product URL (no confirm prompt). Matching prefers the specific instructional product over a store listing titled as a bundle.

```powershell
py -3 -m bjj_pipeline match --library "path\to\instructionals" --output "path\to\bjjfanatics_matches.csv"
py -3 -m bjj_pipeline match --library "path\to\instructionals" --output "path\to\bjjfanatics_matches.csv" --force
```

### Detect and embed chapters

Scan a video for title cards and write sidecar CSVs (no remux yet):

```powershell
py -3 -m bjj_pipeline chapters "path\to\Volume 1.webm" 000000
```

Useful detection options:

| Flag | Default | Meaning |
|------|---------|---------|
| `--fraction` | `0.75` | Frame matches when more than this share of pixels hit the plate color |
| `--gap` | `30` | Minimum seconds between chapter starts |
| `--min-seconds` | `10` | Merge chapters shorter than this |
| `--title-seconds` | `6` | How long after a card starts to OCR title slides |
| `--samples` | — | Known title-card timestamps; pick plate color from those frames |
| `--force` | off | Re-run the start-and-title scan even when a times sidecar exists |
| (omit hex and `--samples`) | — | Auto: histogram of color concentration and dark saturation |

An existing `<stem>_chapters.csv` skips the scan unless `--force`. Container-chapter skip is not part of this command.

Embed existing sidecars (skips rescan when the chapter CSV is present):

```powershell
py -3 -m bjj_pipeline chapters --apply "path\to\Volume 1.webm"
```

Detect and embed in one step when the chapter CSV is missing:

```powershell
py -3 -m bjj_pipeline chapters "path\to\Volume 1.webm" 000000 --apply
```

Outputs next to the video:

- `<stem>_chapters.csv` — `Chapter,StartTimestamp,EndTimestamp`
- `<stem>_chapternames.csv` — volume stem and OCR titles

Embedding copies streams (no re-encode) and replaces the original only after ffprobe confirms the new chapters.

### Probe title-card color frames

Standalone corner-pixel HSV scan (debugging / picking a hex):

```powershell
py -3 -m bjj_pipeline.find_color_frames "path\to\Volume 1.webm" 000000
```

### Batch-transcribe a video tree

```powershell
py -3 -m bjj_pipeline transcribe "path\to\videos" "path\to\transcript-corpus"
```

Behavior:

- Recursively finds `.mp4`, `.mkv`, `.avi`, `.mov`, `.webm`, `.m4v`, `.flv`, `.wmv`
- Mirrors the folder tree under `output_dir` as `.json`
- Requests speech only when the transcript has no `segments` list (an empty list counts as finished) unless `--force`
- `--force` re-runs speech only; chapters and `video_file` still stamp in the same transcript write
- Passes hard words from that volume’s container chapter titles as faster-whisper hotwords when speech runs
- Copies container chapters when the stored list is missing or differs; keeps existing chapters when the container is empty
- Writes `video_file` (basename including extension) when missing, empty, or different
- Leaves finished volumes untouched unless `--force`; delete a transcript to get new speech
- Prints created/updated/failed lines and a final Created / Updated / Unchanged / Failed summary
- Exit status 0 when every volume succeeds or is unchanged; 1 when any volume fails

Options:

| Flag | Meaning |
|------|---------|
| `--ocr` / `--no-ocr` | On-screen OCR for speech requests only (default: off) |
| `--force` | Re-run speech even when a `segments` list already exists |

On Windows, paths of 260+ characters are opened with the `\\?\` extended-length prefix so long mirrored corpus paths still work when Long Paths are disabled. Speech scratch JSON is written under the system temp directory so a long volume name cannot push that scratch path over the limit.

### Scan library completeness

Walk a video library and a mirrored transcript tree, print aggregate percents, and write a markdown drill-down of every video or instructional that does not meet the rubric:

```powershell
py -3 -m bjj_pipeline scan "path\to\video-library" "path\to\transcript-corpus"
```

Checks:

| Check | Meeting means |
| --- | --- |
| Combined into volumes | One file per volume, not a per-chapter clip (`id-vol-ch-` names, `NN.NN - title` names, volume part files, or a Jellyfin SxxEyy file whose title is not Volume/DVD and that has fewer than two container chapters) |
| Named chapters | Two or more container chapters with at least one title other than generic `Chapter N` |
| Video NFO | Sidecar `.nfo` next to the video |
| Instructional NFO | `tvshow.nfo` in that show folder under the library root |
| Play without errors | ffprobe opens the file, and an ffmpeg sample decode at the start and midpoint reports no error |
| Corresponding transcript | Mirrored `.json` exists under the transcript root |

The drill-down is written to `completeness_scan_results_<date-time>.md` in the repository root. Pass `--output` to choose another path. Pass `--skip-decode` to open each file with ffprobe only.

## Project layout

```text
.
├── AGENTS.md                 # Pointers for coding agents
├── GLOSSARY.md               # Domain vocabulary
├── README.md
├── pyproject.toml            # extras: organize, transcribe, all (installs bjj_pipeline)
├── bjj_pipeline/             # py -m bjj_pipeline match|organize|chapters|scan|transcribe|run
│   ├── organizer/            # Scrape, match, NFO, concat
│   ├── run_pipeline.py
│   ├── generate_chapters.py
│   ├── batch_panoscribe.py
│   └── completeness_scan.py
├── coach_app/                # Coach-only advising; import from repo root
│   ├── store.py              # CuratedStore facade
│   ├── cleanup.py
│   ├── statements.py
│   └── ...                   # topics, placement, briefing, design, build, edit, library, print
├── metadata_scraper/         # One-cycle shims + organizer tests
│   └── tests/
├── docs/
│   ├── adr/                  # Accepted decisions
│   ├── agents/               # Issue tracker, triage labels, domain docs
│   ├── enrichment-seed/      # seed.json imported into the live catalog
│   └── volumes-awaiting-parse.md
└── tests/                    # Pipeline tests and coach_app facade tests
```

`pyproject.toml` installs `bjj_pipeline`. `coach_app` is a sibling package used from the repository root; it is not an install extra yet.

## Tests

Pipeline tests use temporary trees and stand-in probes (no ffmpeg, GPU, or real panoscribe). Coach-app tests use fixtures and a stand-in advisor (no video, speech, or browser):

```powershell
py -3 -m pytest tests -q
py -3 -m pytest metadata_scraper -c metadata_scraper\pytest.ini -v
```

## Domain and design docs

- **[`GLOSSARY.md`](GLOSSARY.md)** — use these terms (instructor, volume, chapter, citation, curated store, topic, system, …) in issues and code talk.
- **[`docs/adr/`](docs/adr/)** — [ADR 0001](docs/adr/0001-sample-a-volume-once-for-chapter-starts.md): sample each volume once when detecting chapter starts. [ADR 0002](docs/adr/0002-skip-pipeline-stage-when-artifact-exists.md): skip a finished stage unless forced.
- **[`docs/enrichment-seed/`](docs/enrichment-seed/)** — consensus seed for hierarchy browse and dimensional search. Import once into `CuratedStore`; later edits stay on the live catalog.
- **[`docs/agents/`](docs/agents/)** — GitHub issues via `gh`, triage labels (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`), and how agents should read the glossary before exploring.

The pipeline writes the raw corpus. `coach_app` is the advising package that admits volumes into the curated store.

## Notes and limits

- `coach_app` is a library, not a CLI. `CuratedStore` is in-process; this package does not name a database engine or an application framework.
- Throwaway prototypes under `prototypes/` are not product code.
- Close the target video in players before `py -m bjj_pipeline chapters --apply`, pipeline `--embed`, or `py -m bjj_pipeline organize --apply`, or Windows may refuse to replace the file.
- Old script paths (`generate_chapters.py`, `batch_panoscribe.py`, `completeness_scan.py`, `find_color_frames.py`, `metadata_scraper/run_pipeline.py`, `organize_instructional.py`, `match_bjjfanatics.py`) still run for one cycle and print a deprecation line on stderr.
- `py -m bjj_pipeline match` takes `--library` and `--output`; it does not hardcode a disk path.
- `py -m bjj_pipeline organize` without `--url` needs a terminal so it can confirm a Fanatics lookup, unless a matching row in `bjjfanatics_matches.csv` already has a product URL (the pipeline uses that URL with no prompt).
- Automatic title-card detection can miss plates held for less than about one second.
- A hex plate that fails coverage can fall back to a dark-saturated pixel test (high saturation, low value).
- `py -m bjj_pipeline transcribe` treats two videos that differ only by extension and would share one JSON path as a failure (nothing written for that pair).
- Corpus JSON and video roots are machine-local; they are not committed here.

## License

No license file is present in this repository yet. Clarify ownership and reuse terms before redistributing.
