---
status: accepted
---

# Copy straddling spans into both chapters

Closed #19 assigned a Whisper span to one chapter by start only. Teaching words that begin in one chapter and finish after the next chapter starts were dropped from the later chapter.

Prepare copies a span into every chapter whose `[start, end]` overlaps that span. A span 290–310 with chapter B starting at 300 is copied whole into both `transcript_raw` strings. A span that overlaps no chapter stays only in `segments`. Membership is overlap, not start-only.

## Considered options

- Keep start-only assignment from #19. Rejected because a sentence that crosses a chapter start is teaching for both chapters.
- Split a straddling span at the chapter boundary. Rejected because the Whisper span is the spoken unit, and a cut would drop words from one side.

## Consequences

The same span can appear in two chapters' chapter speech. `transcript_raw` is not a partition of `segments`. Untitled extra speech is not invented as a chapter.
