# video_transcriber_rag

Tools and domain work for turning BJJ instructional videos into a searchable speech corpus, then into a coach-only advising application.

This repository currently focuses on the **pipeline that prepares that corpus**: organizing local instructionals against [BJJ Fanatics](https://bjjfanatics.com/) product pages (`metadata_scraper/`), detecting and embedding chapter markers on volumes, batch-transcribing speech with [panoscribe](https://pypi.org/project/panoscribe/), and keeping glossary and architecture decisions for the coaching advisor that will read the curated store.

The coach is the only user of the eventual application. Domain language lives in [`GLOSSARY.md`](GLOSSARY.md). Specs and open questions live as [GitHub issues](https://github.com/djsciman/video_transcriber_rag/issues) (map issue [#1](https://github.com/djsciman/video_transcriber_rag/issues/1)).

## What this repo does

| Script | Purpose |
|--------|---------|
| `metadata_scraper/organize_instructional.py` | Scrape a BJJ Fanatics product page and reorganize a local folder as a Jellyfin/TMM TV show (NFO, artwork, volumes, named chapters) |
| `metadata_scraper/match_bjjfanatics.py` | Match local folder names to BJJ Fanatics product URLs and write `bjjfanatics_matches.csv` |
| `generate_chapters.py` | Detect title-card chapter starts, OCR titles, write sidecar CSVs, optionally embed chapters into the video |
| `find_color_frames.py` | Lower-level HSV color-frame scanner used by chapter detection (also usable alone) |
| `batch_panoscribe.py` | Walk a video tree and complete each transcript: speech only when missing, container chapters, and `video_file` |
| `completeness_scan.py` | Report library completeness (combined volumes, named chapters, NFO, playback, transcripts) and write a markdown drill-down |

Supporting material:

- `GLOSSARY.md` — coaching and instructional vocabulary
- `docs/adr/` — architecture decision records
- `docs/volumes-awaiting-parse.md` — raw corpus volumes not yet curated
- `docs/agents/` — how agents use the issue tracker, labels, and domain docs
- `tests/` — unit tests for chapter-start detection and batch completion (no ffmpeg, GPU, or real panoscribe)
- `metadata_scraper/tests/` — pytest suite for scrape, match, NFO, layout, and organize pipelines

Video files and transcript JSON typically live **outside** this repo.

## Prerequisites

### System tools

- **Python 3.12+** (on Windows use the launcher: `py -3`)
- **ffmpeg** and **ffprobe** on `PATH` (required for chapter detection, embedding, reading container chapters, and `metadata_scraper` concat/remux)
- **panoscribe** installed for the same Python interpreter (required only for batch transcription)

### Python packages

Install the corpus pipeline from [`requirements.txt`](requirements.txt):

```powershell
py -3 -m pip install -r requirements.txt
```

That pulls in `numpy`, `opencv-python-headless`, `rapidocr`, and `panoscribe`. `panoscribe` also pulls in faster-whisper (and typically needs a CUDA-capable GPU for comfortable speed; CPU works but is slow). Chapter title OCR uses RapidOCR; speech OCR in panoscribe is off by default in the batch script.

Install the library organizer from [`metadata_scraper/requirements.txt`](metadata_scraper/requirements.txt):

```powershell
py -3 -m pip install -r metadata_scraper\requirements.txt
```

That pulls in `beautifulsoup4`, `lxml`, and `pytest`. The scraper talks to BJJ Fanatics over HTTPS; ffmpeg is used when concatenating chapter files into volumes or remuxing chapter markers.

## Getting started

1. Clone the repository and open a shell in the repo root.
2. Confirm Python and ffmpeg:

   ```powershell
   py -3 --version
   ffmpeg -version
   ffprobe -version
   ```

3. Install the Python packages (corpus pipeline, then organizer):

   ```powershell
   py -3 -m pip install -r requirements.txt
   py -3 -m pip install -r metadata_scraper\requirements.txt
   ```
4. Confirm panoscribe (for transcription):

   ```powershell
   panoscribe --help
   ```

5. Run the unit tests:

   ```powershell
   py -3 -m unittest discover -s tests -v
   py -3 -m pytest metadata_scraper -c metadata_scraper\pytest.ini -v
   ```

## Typical workflow

### Organize a local instructional library

1. **Match** folder names to BJJ Fanatics URLs with `match_bjjfanatics.py` (optional; writes `bjjfanatics_matches.csv` that `organize_instructional.py` can use as a hint).
2. **Dry-run** `organize_instructional.py --folder ...` (prints the plan; no writes).
3. **Apply** with `--apply` (NFO, artwork, season folders, volume files, named chapters).
4. **Repair** later with `--repair` if a show is only partly organized.

Leftover multi-instructional bundle folders are out of this pipeline; flatten them by hand and organize each instructional folder on its own.

### Detect chapters and transcribe

For volumes that still lack chapter markers:

1. **Detect chapters** (writes `<stem>_chapters.csv` and `<stem>_chapternames.csv` next to the video).
2. **Review** the CSVs (edit titles if OCR missed).
3. **Embed** with `--apply` (stream-copy remux; close the file in VLC or other players first on Windows).
4. **Transcribe** a directory tree with `batch_panoscribe.py` into a mirrored JSON corpus.

For volumes that already have chapters in the container, skip to step 4.

## Usage

All commands below are run from the repository root. On Windows prefer `py -3`; bare `python` may be the Windows Store stub.

### Organize instructionals (`metadata_scraper`)

`organize_instructional.py` scrapes a BJJ Fanatics product page and reorganizes a local show folder for Jellyfin / TinyMediaManager: `tvshow.nfo`, posters, `Season ##` folders, episode NFO, and (when timestamps exist) named chapter markers. Default is a dry-run.

Dry-run one show (searches Fanatics and asks you to confirm the URL in a terminal):

```powershell
py -3 metadata_scraper\organize_instructional.py --folder "path\to\Show Title by Instructor"
```

Pass the product URL when you already know it:

```powershell
py -3 metadata_scraper\organize_instructional.py --folder "path\to\Show Title by Instructor" --url "https://bjjfanatics.com/products/the-handle"
```

Write files:

```powershell
py -3 metadata_scraper\organize_instructional.py --folder "path\to\Show Title by Instructor" --url "https://bjjfanatics.com/products/the-handle" --apply
```

One product URL per instructional folder. Chapter downloads are always concatenated into volumes with Fanatics chapter titles when names exist (starts from each source file's duration). Leftover bundle folders with several instructionals inside are not organized as one show.

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
py -3 metadata_scraper\organize_instructional.py --folder "path\to\Show Title by Instructor" --repair
py -3 metadata_scraper\organize_instructional.py --folder "path\to\Show Title by Instructor" --repair --repair-steps all
```

Repair letters: **B** show NFO and artwork, **C** season folders, **D** combine chapter clips, **E** write chapter markers, **F** rename episodes and write episode NFO, **G** move leftovers into `extras/`.

### Match folders to Fanatics URLs

`match_bjjfanatics.py` searches BJJ Fanatics for each top-level folder under a library root and writes `folder_path,product_url` CSV. Edit `ROOT` and `OUT_CSV` at the top of the script (they default to a local library path). `organize_instructional.py` will use a matching row in `bjjfanatics_matches.csv` as a URL hint when `--url` is omitted.

```powershell
py -3 metadata_scraper\match_bjjfanatics.py
py -3 metadata_scraper\match_bjjfanatics.py --subfolders
```

`--subfolders` also matches one level of child folders (search name is `parent child` so names like `Season 1` still match the series). Matching prefers the specific instructional product over a store listing titled as a bundle.

### Detect and embed chapters

Scan a video for title cards and write sidecar CSVs (no remux yet):

```powershell
py -3 generate_chapters.py "path\to\Volume 1.webm" 000000
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
py -3 generate_chapters.py --apply "path\to\Volume 1.webm"
```

Detect and embed in one step when the chapter CSV is missing:

```powershell
py -3 generate_chapters.py "path\to\Volume 1.webm" 000000 --apply
```

Outputs next to the video:

- `<stem>_chapters.csv` — `Chapter,StartTimestamp,EndTimestamp`
- `<stem>_chapternames.csv` — volume stem and OCR titles

Embedding copies streams (no re-encode) and replaces the original only after ffprobe confirms the new chapters.

### Probe title-card color frames

Standalone corner-pixel HSV scan (debugging / picking a hex):

```powershell
py -3 find_color_frames.py "path\to\Volume 1.webm" 000000
```

### Batch-transcribe a video tree

```powershell
py -3 batch_panoscribe.py "path\to\videos" "path\to\transcript-corpus"
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
py -3 completeness_scan.py "path\to\video-library" "path\to\transcript-corpus"
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
├── batch_panoscribe.py       # Batch speech + chapter stamp
├── completeness_scan.py      # Library completeness report
├── find_color_frames.py      # HSV frame matching
├── generate_chapters.py      # Chapter CSV + embed CLI
├── metadata_scraper/
│   ├── organize_instructional.py
│   ├── match_bjjfanatics.py
│   ├── requirements.txt
│   ├── bjj_organizer/        # Scrape, match, NFO, concat
│   └── tests/
├── docs/
│   ├── adr/                  # Accepted decisions
│   ├── agents/               # Issue tracker, triage labels, domain docs
│   └── volumes-awaiting-parse.md
└── tests/
    ├── test_chapter_starts.py
    ├── test_batch_panoscribe.py
    └── test_completeness_scan.py
```

## Tests

Chapter-start, batch, and completeness-scan logic is tested with temporary trees and stand-in probes (no ffmpeg, GPU, or real panoscribe):

```powershell
py -3 -m unittest discover -s tests -v
```

Organizer tests use HTML/JSON fixtures (no live Fanatics, ffmpeg, or library paths):

```powershell
py -3 -m pytest metadata_scraper -c metadata_scraper\pytest.ini -v
```

## Domain and design docs

- **[`GLOSSARY.md`](GLOSSARY.md)** — use these terms (instructor, volume, chapter, citation, curated store, topic, system, …) in issues and code talk.
- **[`docs/adr/`](docs/adr/)** — for example [ADR 0001](docs/adr/0001-sample-a-volume-once-for-chapter-starts.md): sample each volume once when detecting chapter starts.
- **[`docs/agents/`](docs/agents/)** — GitHub issues via `gh`, triage labels (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`), and how agents should read the glossary before exploring.

The advising application (curated store, citations, topics) is specified on the issue map; this repo’s scripts feed the raw corpus that curation later admits.

## Notes and limits

- Close the target video in players before `generate_chapters.py --apply` or `organize_instructional.py --apply`, or Windows may refuse to replace the file.
- `match_bjjfanatics.py` uses a hardcoded `ROOT` / `OUT_CSV`; change those constants before running it.
- `organize_instructional.py` without `--url` needs a terminal so it can confirm a Fanatics lookup (or a matching row in `bjjfanatics_matches.csv`).
- Automatic title-card detection can miss plates held for less than about one second.
- A hex plate that fails coverage can fall back to a dark-saturated pixel test (high saturation, low value).
- `batch_panoscribe.py` treats two videos that differ only by extension and would share one JSON path as a failure (nothing written for that pair).
- Corpus JSON and video roots are machine-local; they are not committed here.

## License

No license file is present in this repository yet. Clarify ownership and reuse terms before redistributing.
