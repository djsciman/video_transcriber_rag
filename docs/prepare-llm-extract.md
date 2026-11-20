# Extract concepts and techniques

## Objective

From one chapter's **cleaned** speech (not raw), write `concepts` and `techniques`. Do not re-pare speech. Do not return `transcript_cleaned` or `suggested_tags`.

## Input

Envelope fields (`instructor`, `instructional`, `volume`, `chapter`, `previous_chapter`, `next_chapter`) plus cleaned chapter speech. Timestamps have already been stripped. Do not import teaching from another chapter.

## Drill test

Extract a technique only if a **student** could drill the start, the mechanics, and a named finish from this chapter without inventing the finish. Overviews, posture talks, grip talks, and theory stay in `concepts` with `"techniques": []`.

Do not extract a movement that is only named in passing. Do not complete an unfinished movement from outside knowledge or from a neighbor chapter.

## Concepts

`concepts` is an array of independent coaching points from this chapter's cleaned speech. Cap five. A focused chapter is often one entry. Paraphrases of one thesis stay one entry. Do not split a ramble. Do not invent. Do not import the next chapter.

## Hop vs concepts

Hop fields may be starred guesses (`mount*`) when the chapter does not name the value. **Never infer** applies to `concepts` only, not to hop fields. `concepts` must not invent; hops may propose a starred remap.

## Techniques

Each independently taught, drillable movement is one object. Repeated demos of the same sequence are one technique. A material variation that is itself drillable is a separate entry. Chains with identifiable starts and finishes may split; an inseparable sequence stays one entry.

`technique_steps`: numbered mechanical actions a student could drill. Step 1 names start position and occupancy. The last step names the demonstrated finish. Do not invent a bridging action. Later explicit corrections win.

`main_ideas`: two or three pithy imperative sentences (never more). Not a restatement of the steps.

## Hop fields (all strings)

Fill every field. Strong seed match: unmarked. Educated guess or no seed match: trailing `*`.

| Field | Value |
|---|---|
| `named_move` | Short name from this chapter, or that name with `*` |
| `ruleset` | `gi`, `no-gi`, `both`, or those with `*` |
| `move_type` | Seed type, or that type with `*` |
| `start_occupancy` | `top`, `bottom`, `neutral`, or those with `*` |
| `start_position` | Seed position ID, or a short label with `*` |
| `end_occupancy` | `top`, `bottom`, `neutral`, `""` for submissions, or those with `*` |
| `end_position` | Seed position or submission ID, or a short label with `*` |

No `system` field. No family field.

`move_type` prefer: `takedown`, `sweep`, `pass`, `escape`, `submission`, `transition`, `reversal`, `back-take`. Another type takes `*`.

Occupancy is the athlete performing the movement.

- Escape: starts bottom in a pin or control; end is the position achieved.
- Pass: starts top; finishes still top past the guard.
- Sweep: starts bottom; finishes top.
- Takedown: starts neutral; end occupancy is the result.
- Transition: same occupancy role throughout.
- Reversal: disadvantaged to advantaged when sweep/escape do not fit. Do not use it as a generic dump.
- Back-take: intended to establish `back-control`.
- Submission: `end_position` is a submission ID; `end_occupancy` is `""`.

`ruleset`: `gi` / `no-gi` / `both`. Star when the volume only implies it. Do not leave it empty when the volume already established gi vs no-gi.

Name `named_move` from this chapter's speech or title. Do not pull a catalog name the chapter did not teach.

## Position IDs

`standing`, `clinch`, `front-headlock`, `closed-guard`, `open-guard`, `half-guard`, `deep-half-guard`, `z-guard`, `butterfly-guard`, `de-la-riva`, `reverse-de-la-riva`, `spider-guard`, `lasso-guard`, `collar-sleeve`, `x-guard`, `single-leg-x`, `k-guard`, `rubber-guard`, `worm-guard`, `shin-to-shin`, `fifty-fifty`, `saddle`, `outside-ashi`, `headquarters`, `leg-drag-position`, `side-control`, `kesa-gatame`, `north-south`, `knee-on-belly`, `mount`, `s-mount`, `technical-mount`, `turtle`, `truck`, `back-control`, `crucifix`.

Star a guess. If none fits, a short label with `*`.

## Submission IDs (`end_position`; `end_occupancy` is `""`)

`rear-naked-choke`, `guillotine`, `darce`, `anaconda`, `arm-triangle`, `triangle`, `armbar`, `kimura`, `americana`, `omoplata`, `ezekiel`, `north-south-choke`, `cross-collar-choke`, `bow-and-arrow`, `loop-choke`, `clock-choke`, `baseball-bat-choke`, `paper-cutter`, `gogoplata`, `straight-ankle-lock`, `heel-hook`, `toe-hold`, `kneebar`, `calf-slicer`, `twister`, `wrist-lock`.

## Source time ranges

`source_time_ranges` is an array of nest-style second ranges, not clock times.

Example: `["1234.00-1560.00"]`.

Use only timestamps present in the input. If the cleaned speech has none, return `[]`. Do not invent boundaries. Do not write `04:32-06:18`.

## Output

```json
{
  "concepts": ["string"],
  "techniques": [
    {
      "named_move": "string",
      "ruleset": "string",
      "move_type": "string",
      "start_occupancy": "string",
      "start_position": "string",
      "end_occupancy": "string",
      "end_position": "string",
      "technique_steps": "string",
      "main_ideas": "string",
      "source_time_ranges": ["1234.00-1560.00"]
    }
  ]
}
```

No `suggested_tags`. Extra keys are dropped. Theory chapter: `"techniques": []`.
