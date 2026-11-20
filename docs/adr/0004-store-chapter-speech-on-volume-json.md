---
status: accepted
---

# Store chapter speech on the volume JSON

Transcribed volumes already keep Whisper `segments` and chapter markers on one corpus JSON. A second tree of chapter-speech files would drift from that record and from the video-library path.

Prepare writes chapter speech onto the existing chapter objects: instructor, instructional, volume, previous and next chapter titles, and `transcript_raw`. Chapter identity stays title, start, and end. Whisper `segments` are left as transcribed. The rewrite is an atomic replace of the same path.

## Considered options

- A sidecar tree next to the corpus JSON. Rejected because citations and playback already key off the volume file, and a second tree would need its own skip story.
- Replacing `segments` with nested chapter speech. Rejected so the original speech remains inspectable and transcribe skip still sees a `segments` list.

## Consequences

Extra keys on a chapter survive a later transcribe write only while title, start, and end still match. Volumes with no real chapters, or one chapter covering the whole recording, are left unchanged. Chapter speech is not a cleaned statement and does not enter the curated store.
