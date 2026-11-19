---
status: accepted
---

# Skip prepare `--llm` per chapter

`--llm` calls a paid chat model once per chapter. A volume-grain skip would re-send finished chapters after a mid-volume fail.

Skip a chapter when `transcript_cleaned` is already a string. Skip a chapter with empty `transcript_raw`. The volume is finished for `--llm` when no remaining chapter still needs a call. `--force` / `--force-stage prepare` re-sends chapters that already have cleaned speech.

## Considered options

- Volume-grain skip on every chapter having `transcript_cleaned`. Rejected because one failed chapter would retry the whole volume.
- Treating empty-raw chapters as unfinished. Rejected because they would never complete and would block skip.

## Consequences

A later prompt change needs `--force` to rewrite cleaned chapters. Nest skip stays volume-grain on `transcript_raw` (ADR-0002). Chapter speech stays on the volume JSON (ADR-0004).
