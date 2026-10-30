# video_transcriber_rag

Tools and domain work for turning BJJ instructional videos into a searchable speech corpus, then into a coach-only advising application.

This repository currently focuses on the **pipeline that prepares that corpus**: detecting and embedding chapter markers on volumes, batch-transcribing speech with [panoscribe](https://pypi.org/project/panoscribe/), and keeping glossary and architecture decisions for the coaching advisor that will read the curated store.

The coach is the only user of the eventual application. Domain language lives in [`GLOSSARY.md`](GLOSSARY.md). Specs and open questions live as [GitHub issues](https://github.com/djsciman/video_transcriber_rag/issues) (map issue [#1](https://github.com/djsciman/video_transcriber_rag/issues/1)).

## What this repo does

| Script | Purpose |
|--------|---------|
| `generate_chapters.py` | Detect title-card chapter starts, OCR titles, write sidecar CSVs, optionally embed chapters into the video |
| `find_color_frames.py` | Lower-level HSV color-frame scanner used by chapter detection (also usable alone) |
| `batch_panoscribe.py` | Walk a video tree, transcribe with panoscribe, mirror JSON under an output root, stamp container chapters and `video_file` |

Supporting material:

- `GLOSSARY.md` — coaching and instructional vocabulary
- `docs/adr/` — architecture decision records
- `docs/volumes-awaiting-parse.md` — raw corpus volumes not yet curated
- `docs/agents/` — how agents use the issue tracker, labels, and domain docs
- `tests/` — unit tests for chapter-start detection (no ffmpeg, GPU, or panoscribe)

Video files and transcript JSON typically live **outside** this repo.

## Prerequisites

### System tools

- **Python 3.12+** (on Windows use the launcher: `py -3`)
- **ffmpeg** and **ffprobe** on `PATH` (required for chapter detection, embedding, and reading container chapters)
- **panoscribe** installed for the same Python interpreter (required only for batch transcription)

### Python packages

There is no `requirements.txt` yet. Install what the scripts import:

```text
numpy
opencv-python
rapidocr
panoscribe
```

Example:

```powershell
py -3 -m pip install numpy opencv-python rapidocr panoscribe
```

`panoscribe` pulls in faster-whisper (and typically needs a CUDA-capable GPU for comfortable speed; CPU works but is slow). Chapter title OCR uses RapidOCR; speech OCR in panoscribe is off by default in the batch script.

## Getting started

1. Clone the repository and open a shell in the repo root.
2. Confirm Python and ffmpeg:

   ```powershell
   py -3 --version
   ffmpeg -version
   ffprobe -version
   ```

3. Install the Python packages listed above.
4. Confirm panoscribe (for transcription):

   ```powershell
   panoscribe --help
   ```

5. Run the chapter-start unit tests:

   ```powershell
   py -3 -m unittest discover -s tests -v
   ```

## Typical workflow

For volumes that still lack chapter markers:

1. **Detect chapters** (writes `<stem>_chapters.csv` and `<stem>_chapternames.csv` next to the video).
2. **Review** the CSVs (edit titles if OCR missed).
3. **Embed** with `--apply` (stream-copy remux; close the file in VLC or other players first on Windows).
4. **Transcribe** a directory tree with `batch_panoscribe.py` into a mirrored JSON library.

For volumes that already have chapters in the container, skip to step 4.

## Usage

All commands below are run from the repository root. On Windows prefer `py -3`; bare `python` may be the Windows Store stub.

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
| (omit hex and `--samples`) | — | Auto: histogram of color concentration and dark saturation |

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
py -3 batch_panoscribe.py "path\to\videos" "path\to\transcript-library"
```

Behavior:

- Recursively finds `.mp4`, `.mkv`, `.avi`, `.mov`, `.webm`, `.m4v`, `.flv`, `.wmv`
- Mirrors the folder tree under `output_dir` as `.json`
- Calls `panoscribe transcribe` (OCR off by default)
- Writes container chapters from ffprobe and sets `video_file` to the video’s basename (including extension)
- Asks before overwriting existing transcripts unless you pass `--force`
- Leaves already-present transcripts alone when you decline overwrite

Options:

| Flag | Meaning |
|------|---------|
| `--force` | Overwrite existing transcripts without prompting |
| `--stamp-video-file` | Only write `video_file` into existing transcripts; do not transcribe |
| `--ocr` / `--no-ocr` | Pass OCR on/off to panoscribe (default: off) |
| `--transcribe` / `--no-transcribe` | Enable/disable speech (default: on; `--no-transcribe` skips the file) |

Example stamp-only pass:

```powershell
py -3 batch_panoscribe.py "path\to\videos" "path\to\transcript-library" --stamp-video-file
```

On Windows, paths of 260+ characters are opened with the `\\?\` extended-length prefix so long mirrored library paths still work when Long Paths are disabled.

## Project layout

```text
.
├── AGENTS.md                 # Pointers for coding agents
├── GLOSSARY.md               # Domain vocabulary
├── README.md
├── batch_panoscribe.py       # Batch speech + chapter stamp
├── find_color_frames.py      # HSV frame matching
├── generate_chapters.py      # Chapter CSV + embed CLI
├── docs/
│   ├── adr/                  # Accepted decisions
│   ├── agents/               # Issue tracker, triage labels, domain docs
│   └── volumes-awaiting-parse.md
└── tests/
    └── test_chapter_starts.py
```

## Tests

Chapter-start logic is tested with pure sample rows (no video decode):

```powershell
py -3 -m unittest discover -s tests -v
```

## Domain and design docs

- **[`GLOSSARY.md`](GLOSSARY.md)** — use these terms (instructor, volume, chapter, citation, curated store, topic, system, …) in issues and code talk.
- **[`docs/adr/`](docs/adr/)** — for example [ADR 0001](docs/adr/0001-sample-a-volume-once-for-chapter-starts.md): sample each volume once when detecting chapter starts.
- **[`docs/agents/`](docs/agents/)** — GitHub issues via `gh`, triage labels (`needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`), and how agents should read the glossary before exploring.

The advising application (curated store, citations, topics) is specified on the issue map; this repo’s scripts feed the raw corpus that curation later admits.

## Notes and limits

- Close the target video in players before `generate_chapters.py --apply`, or Windows may refuse to replace the file.
- Automatic title-card detection can miss plates held for less than about one second.
- A hex plate that fails coverage can fall back to a dark-saturated pixel test (high saturation, low value).
- `batch_panoscribe.py` treats two videos that differ only by extension and would share one JSON path as a failure (nothing written for that pair).
- Corpus JSON and video roots are machine-local; they are not committed here.

## License

No license file is present in this repository yet. Clarify ownership and reuse terms before redistributing.
