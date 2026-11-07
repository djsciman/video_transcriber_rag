---
status: accepted
---

# Skip a pipeline stage when its artifact exists

The corpus-prep command walks a library of instructionals. Re-searching Fanatics, concatenating volumes, or re-running Whisper on a finished show is waste. A second run should fill gaps only.

Each selected stage prints SKIP when its artifact already exists, RUN when it would work, and FAIL when it cannot. Omitting `--apply` is a dry run that prints those labels without writing files, decoding a volume, or starting speech. `--force` re-runs every selected stage; `--force-stage` re-runs one. Visual embed of sidecar chapter files is `--embed` and is not implied by `--apply`.

Skip artifacts today: match skips a folder that already has a product URL in the match CSV; organize skips when `tvshow.nfo` and at least one `Season ##` folder are on disk; detect skips a volume that already has container chapters or a sidecar (uncombined chapter-file seasons warn and skip unless `--force-stage detect`); transcribe skips when the mirrored JSON already has a `segments` list, including an empty list. Title-card detect is in the default stages. Visual embed stays `--embed`.

## Considered options

- Always re-run every stage. Rejected because Whisper and concat dominate the wait.
- Using organize repair letters as the skip oracle. Rejected because a letter can be true when the product page has no timestamps.
- Treating `--apply` as embed. Rejected so OCR titles can be reviewed in sidecars before they go into the volume.

## Consequences

A corpus built from pre-concat chapter files is not skip-stable after organize concatenates those clips into volumes. Force on transcribe re-runs speech only; chapter and `video_file` stamps still happen in the same write. Force organize re-plans; repair stays a separate operator path.
