# Enrichment seed

One-time consensus seed for hierarchy browse and dimensional search.

Product rules: [How hierarchy enrichment is sourced and kept](https://github.com/djsciman/video_transcriber_rag/issues/24).  
Assembled for: [Assemble the consensus enrichment seed from open sources](https://github.com/djsciman/video_transcriber_rag/issues/25).  
Organize next: [Visualize and organize enrichment categories from the seed](https://github.com/djsciman/video_transcriber_rag/issues/26).

## Load this

- **`seed.json`** — the artifact to import (version 2). Shared path levels are `starting_position` → `move_type` → `ending_position_or_submission`. Named-move leaves under each path carry `ruleset`: `gi`, `no-gi`, or `both`. Many leaves and some positions also carry `cross_refs` to judo and wrestling names. The top-level `crosswalk` array flattens those mappings for search.
- **`SOURCES.md`** — sources and license notes, including judo and wrestling pages.
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
    "leaves": [{
      "name": "Hip bump sweep",
      "ruleset": "both",
      "cross_refs": [{ "art": "judo", "name": "…", "source": "kodokan-wikipedia" }]
    }]
  }],
  "crosswalk": [{
    "seed_leaf": "Double leg takedown",
    "art": "judo",
    "name": "Morote-gari",
    "source": "kodokan-wikipedia"
  }]
}
```

Ids on the vocab lists are stable handles for the prototype. Path `start` / `move_type` / `end` values match those ids.

## Judo and wrestling cross-refs

Open Kodokan judo lists and wrestling takedown / folkstyle sources supply alternate names on the same BJJ finder nodes. Example: BJJ leaf `Double leg takedown` cross-refs wrestling `Double leg` and judo `Morote-gari`. Cross-refs do not change the three shared path levels or ruleset leaf tags.

## Not in this seed

- Lesson fields, citations, or Custom lessons
- An `uncategorized` node (that bucket is a product browse state for unlinked citations)
- A final coach-accepted category layout (that is the prototype ticket)
