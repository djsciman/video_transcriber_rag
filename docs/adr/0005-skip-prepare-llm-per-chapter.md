---
status: accepted
---

# Skip prepare `--llm` per chapter

`--llm` calls a paid chat model per chapter. A volume-grain skip would re-send finished chapters after a mid-volume fail. Default `--llm` is **staged**: two Completer calls on the **same** `--provider` / `--model` (cleanup at low reasoning, extract at medium) with the short specs. `--method one-call` keeps one Completer call per chapter with [`docs/prepare-llm-prompt.md`](../prepare-llm-prompt.md) and `reasoning_effort` low when the adapter posts that field. There is no volume-wide cleanup call. Default flipped to staged after the Anthropic Haiku 5.5 method bake-off (#117).

## One-call skip

Skip a chapter when `transcript_cleaned` is already a string and `concepts` and `suggested_tags` are already lists. Skip a chapter with empty `transcript_raw`. The volume is finished for one-call `--llm` when no remaining chapter still needs a call. `--force` / `--force-stage prepare` re-sends chapters that already have cleaned speech.

## Staged skip (default)

Cleanup is done when `transcript_cleaned` is a string. Extract is done when `concepts` is a list. `suggested_tags` is not a staged skip key; on that path they are derived in prepare from `concepts` and `main_ideas`. Empty `transcript_raw` skips both stages. Failed cleanup leaves LLM keys off and does not extract. Failed extract keeps cleaned speech. `--force` re-sends both staged stages. The volume is finished for staged `--llm` when nest is done and no remaining chapter still needs cleanup or extract.

## Considered options

- Volume-grain skip on every chapter having `transcript_cleaned`. Rejected because one failed chapter would retry the whole volume.
- Treating empty-raw chapters as unfinished. Rejected because they would never complete and would block skip.
- Volume-wide cleanup. Rejected: duplicate chapter titles and output-length risk make it unfit for a one-shot corpus.

## Consequences

A later prompt change needs `--force` to rewrite cleaned chapters. Nest skip stays volume-grain on `transcript_raw` (ADR-0002). Chapter speech stays on the volume JSON (ADR-0004). `--provider` and `--model` (and `BJJ_LLM_PROVIDER` / `BJJ_LLM_MODEL`) select one lightweight SKU for the whole run; one-call, cleanup, and extract all use that pair. Prepaid key for the selected provider.
