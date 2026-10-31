# Enrichment seed

One-time consensus seed for hierarchy browse and dimensional search.

Product rules: [How hierarchy enrichment is sourced and kept](https://github.com/djsciman/video_transcriber_rag/issues/24).  
Assembled for: [Assemble the consensus enrichment seed from open sources](https://github.com/djsciman/video_transcriber_rag/issues/25).  
Organize next: [Visualize and organize enrichment categories from the seed](https://github.com/djsciman/video_transcriber_rag/issues/26).

## Load this

- **`seed.json`** — the artifact to import. Shared path levels are `starting_position` → `move_type` → `ending_position_or_submission`. Named-move leaves under each path carry `ruleset`: `gi`, `no-gi`, or `both`.
- **`SOURCES.md`** — sources and license notes.
- **`reference/bjj-data-taxonomy-v0.1.0.json`** — CC BY 4.0 vocabulary snapshot used while assembling.

## Shape

```json
{
  "move_types": [{ "id": "sweep", "label": "Sweep" }],
  "starting_positions": [{ "id": "closed-guard", "label": "Closed guard", "family": "guard" }],
  "ending_positions_or_submissions": [{ "id": "mount", "label": "Mount", "kind": "position" }],
  "paths": [{
    "start": "closed-guard",
    "move_type": "sweep",
    "end": "mount",
    "leaves": [{ "name": "Hip bump sweep", "ruleset": "both" }]
  }]
}
```

Ids on the vocab lists are stable handles for the prototype. Path `start` / `move_type` / `end` values match those ids.

## Not in this seed

- Lesson fields, citations, or Custom lessons
- An `uncategorized` node (that bucket is a product browse state for unlinked citations)
- A final coach-accepted category layout (that is the prototype ticket)
