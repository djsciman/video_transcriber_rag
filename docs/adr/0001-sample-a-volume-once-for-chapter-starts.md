---
status: accepted
---

# Sample a volume once for chapter starts

Chapter detection was decoding a volume once to score it and again at full frame rate to place chapter starts. A hex plate that missed could decode the volume a third time. The chapter list then merges anything shorter than ten seconds, so those frame-accurate starts were finer than the chapters use.

We sample each volume once. Hex and dark scans keep four frames a second, scaled to 320 pixels wide, and decide the starts in memory. A hex miss uses the dark scores from that same pass. An automatic scan keeps one scaled frame a second, holds those frames until the plate ranges are known, runs the plate test on them, and then releases them. An automatic chapter opens on two adjacent matches, about a one-second hold, rather than on half a second of consecutive full-rate frames.

## Considered options

- A second full-resolution decode after the score pass. Rejected because it dominates the wait, and the chapter merge throws away the extra precision.
- Treating a sample's dominant-color share as the plate test. Rejected because the plate test counts pixels inside the plate tolerance, and that tolerance is known only after the whole volume has been scored.
- Writing the scaled samples out to a temporary file for the plate test. Rejected in favor of holding them in memory, about 600MB per hour of the volume, and releasing them before the title text is read.

## Consequences

A chapter start can sit up to one sample interval after the true frame. A flash shorter than the interval can be missed. An automatic plate that is up for less than a second can be missed. A start within a quarter-second of the one-second lead-in can gain or lose that lead-in chapter. Title text is still read from full-resolution frames, so a scaled start can fail that re-test and the chapter can be named continued. The corner-pixel scan is unchanged.
