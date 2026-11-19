# Pare BJJ Instructional Chapter

## 1. Objective

Process one BJJ instructional video chapter and extract its instructional content into a clean, structured representation.

Produce three distinct representations:

1. **`transcript_cleaned`** — A faithful, readable version of the instructor's speech, with verbal clutter and redundant repetition removed.
2. **`technique_steps`** — An executable mechanical sequence for each independently taught technique.
3. **`main_ideas`** — Two or three pithy, imperative statements of the ideas that bear the most weight. This is not a re-summarization of the steps.

Also classify each extracted technique using the seed vocabularies. Put that classification on the technique object. Extract `suggested_tags` as keywords from `main_ideas`.

The seed is primarily a terminology source for cleaning the transcript. Tag fields may be filled more freely: a strong seed match is written as-is; an educated guess or a value with no seed match is written with a trailing `*`.

The chapter transcript is the authoritative source.

Do not supplement the instruction with outside BJJ knowledge. Do not invent techniques, steps, corrections, explanations, or outcomes.

Accuracy and source fidelity take precedence over formatting preferences and output completeness.

When information is ambiguous or insufficiently supported, preserve the uncertainty rather than guessing.

## 2. Input

You will receive the complete chapter and its contextual metadata:

```text
instructor: …
instructional: …
volume: …
chapter: …
previous_chapter: …   (empty if none)
next_chapter: …       (empty if none)

Chapter speech:

…
```

### Metadata usage

Use metadata to identify instructors, instructional titles, chapter identity, and terminology.

Previous and next chapter information may help resolve ambiguous references, identify terminology, and understand continuity.

However:
- The current chapter is the authoritative source for extracted instruction.
- Do not import mechanical steps or technical explanations from adjacent chapters.
- Do not complete unfinished instruction using information from another chapter.
- Do not invent titles, names, or contextual information that was not supplied.

Keep chapter titles and names already used in the instructional material, including instructor names.

## 3. Source fidelity and terminology

Treat the chapter transcript as the authoritative source.

Preserve all meaningful instructional content, technical distinctions, corrections, and variations.

Distinguish between:

- **Source facts:** Information the instructor actually said or demonstrated.
- **Normalization:** Changes to wording that preserve the original meaning.
- **Interpretation:** Conclusions reasonably supported by the instruction and context.
- **Unsupported inference:** Information not established by the source.

Use source facts, appropriate normalization, and sufficiently supported interpretation. Never introduce unsupported inference.

### Terminology correction

The seed (named-move names, position labels, submission names, judo/wrestling repair hints) is the primary tool for repairing the transcript.

Correct mistranscribed grappling terminology using:
- The instructional and chapter titles.
- Terminology already established in the volume.
- The seed named-move, position, and submission vocabularies.
- The repair hints below.
- Judo and wrestling names for equivalent movements.

Repair hints are terminology references, not required tag values.

Correct a mistranscribed term only when phonetic similarity and instructional context strongly support the intended term.

Do not rewrite the instructor's speech merely because a seed term exists.

When the intended term cannot be identified confidently, retain the closest defensible transcription rather than guessing.

### Inside and outside terminology

Add `(inside …)` or `(outside …)` when the directional meaning is clear from context and is important to the instruction.

- Inside = toward the relevant primary body connection.
- Outside = away from the relevant primary body connection.

Determine the reference point from the immediate positional context.

Do not replace an inside/outside term the instructor already spoke.

When multiple interpretations are possible, preserve the original wording without adding a directional label.

## 4. Processing workflow

Process the chapter in the following order:

1. Read the complete transcript and supplied metadata.
2. Identify the instructional subject and distinguish actual teaching from introductions, commentary, and incidental speech.
3. Clean the transcript while preserving meaningful instruction.
4. Identify distinct, independently taught techniques.
5. Reconcile demonstrations, repetitions, variations, and corrections.
6. Reconstruct each technique's mechanical sequence.
7. Extract the most valuable lessons the athlete should remember.
8. Classify each technique: strong seed matches unmarked, guesses and unmatched values with `*`.
9. Validate the relationships between steps, concepts, and hop classifications.
10. Produce the final JSON.

Do not expose intermediate reasoning or analysis. Return only the completed output.

## 5. Transcript cleaning

`transcript_cleaned` is the chapter's speech, pared down for readability.

Apply these rules:

- Remove filler words, false starts, empty turns of phrase, and unnecessary verbal clutter.
- Remove jokes and incidental conversation that do not contribute to the instruction.
- Collapse redundant restatements of the same idea into one clear expression.
- Preserve additional details when a repetition clarifies, expands, or corrects an earlier statement.
- Preserve meaningful technical terminology, examples, explanations, and distinctions.
- Preserve the instructor's intended meaning and instructional voice.
- Repair confidently identifiable transcription errors.
- Do not summarize the chapter or reorganize it into technique steps.
- Do not invent explanations or combine unrelated statements into new teaching.
- Remove source timestamps such as `<12.34>`.

The result must be continuous, readable prose without timestamps.

Do not remove meaningful teaching simply because it is repeated during a demonstration.

## 6. Technique identification

Extract each distinct technique intentionally taught in the chapter.

A technique is a distinct, teachable grappling movement or sequence with a sufficiently identifiable starting context, mechanical execution, and intended result.

### What qualifies as a technique

Examples include:
- A sweep.
- A guard pass.
- A submission.
- An escape.
- A takedown.
- A back take.
- A positional transition.
- Another distinct movement that can be represented using the approved classification vocabulary.

Do not create separate techniques for:
- Individual mechanical actions within a larger technique.
- Incidental movements.
- Setup details.
- Techniques merely mentioned in passing.
- Repeated demonstrations of the same sequence.
- Commentary describing why a position is useful.

### Multiple techniques in one chapter

Extract each independently taught technique separately.

A chapter may contain several techniques, and all sufficiently complete techniques must be represented.

Do not combine independent techniques into one long sequence.

When a chain contains multiple independently taught movements with identifiable starting and ending states, extract them as separate technique entries.

When a sequence is taught only as an inseparable connected technique, retain it as one entry and classify its overall movement and intended outcome.

### Repetitions and variations

Treat demonstrations as repetitions when they teach the same underlying mechanical sequence.

Treat demonstrations as variations when they introduce a materially different grip, control, movement, or response.

Preserve variations separately when they are independently teachable and mechanically distinct.

When a variation only changes an incidental detail or provides an alternative adjustment without changing the fundamental sequence, incorporate that detail into the original technique's teaching.

Do not create duplicate techniques merely because the instructor demonstrates the same technique against different resistance.

### Incomplete instruction

Do not extract a technique unless its required sequence and intended result are sufficiently established in the current chapter.

If an instructor introduces a technique but does not complete the instruction, do not complete it using outside knowledge or another chapter.

Conceptual chapters, introductory chapters, posture discussions, grip discussions, and explanations of why a position is useful are not automatically techniques.

If the chapter does not teach any sufficiently complete technique, return an empty `techniques` array.

## 7. Technique sequence extraction

**`technique_steps`** represents the mechanical sequence a student could use to drill the technique.

It is not a transcript summary or a collection of everything the instructor said.

### Demonstration reconciliation

Use the clearest and most complete demonstration as the primary sequence.

Incorporate meaningful mechanical details from other demonstrations when they supplement the primary sequence.

Follow these rules:

- Later explicit corrections supersede earlier instructions.
- Earlier demonstrations may contain important details missing from later demonstrations.
- A later demonstration is not automatically more authoritative or complete.
- Do not merge contradictory demonstrations into one sequence.
- When an instructor explicitly corrects an action, use the corrected action.
- When materially different sequences are demonstrated, preserve them as variations or separate techniques as appropriate.
- Never invent an action to bridge an unexplained gap.

### Step construction

Create one numbered line for each distinct mechanical action or meaningful control adjustment.

Requirements:

- Step 1 names the starting position and occupancy.
- The final step identifies the demonstrated finish or positional outcome.
- Each line describes one principal mechanical action.
- Include the body part, direction, and purpose when established by the instruction.
- Use clear anatomical and positional terminology.
- Preserve meaningful grip, frame, underhook, overhook, hook, knee, hip, head, and limb-control details.
- Include important directional movements and positional adjustments.
- Express the sequence in the correct mechanical order.
- Make the sequence sufficiently specific that a student could drill the demonstrated technique.

Do not:
- Include jokes or commentary.
- Include repeated demonstrations as duplicate actions.
- Add explanations that belong in `main_ideas`.
- Invent unstated movements.
- Split or combine actions simply to reach a preferred step count.

There is no mandatory minimum or maximum number of steps. Mechanical completeness and accuracy take precedence over brevity.

When hop classification is present, the sequence must accurately represent the movement from `start_position` and `start_occupancy` to `end_position` and `end_occupancy`.

## 8. Main ideas: highest-weight teaching

**`main_ideas` is two or three pithy, imperative statements of the ideas that bear the most weight.**

This is not a re-summarization of `technique_steps`.

Write as commands an athlete can carry onto the mat. Prefer the principles, timing, and priorities that decide whether the technique works.

Maximum: three sentences. Prefer two when two ideas carry the chapter.

### What belongs here

Keep only the heaviest ideas the instructor actually taught:

- The positional battle or relationship that must be won first.
- The cue, control, or timing that makes or breaks the move.
- The answer to the resistance the instructor actually showed.

Drop anything that is already obvious from reading the numbered steps.

### Writing rules

- Imperative voice: "Push the elbow in and go." not "He explains that you should push the elbow in."
- Pithy: short, load-bearing sentences.
- Do not walk the sequence again in prose.
- Do not reproduce the cleaned transcript.
- Do not fill the section with generic BJJ advice.
- Include only insights supported by the chapter.
- Two or three sentences. Never more.

### Suggested tags

`suggested_tags` is an array of keyword strings extracted from `main_ideas`.

Pull the load-bearing terms and short phrases from those sentences. Do not invent tags from `technique_steps` or from outside knowledge. Do not put hop objects in this array.

If `main_ideas` is empty, return `[]`.

## 9. Technique classification

Place hop classification on the technique object itself.

A hop represents the complete, independently taught movement, not an individual action within the movement.

If a chapter teaches multiple independently classifiable movements, create separate technique entries.

Fill every hop field. Prefer a value over leaving the field empty.

### Seed match vs suggestion

The lists below are the seed. Use them first.

- **Strong seed match:** The transcript, chapter title, or demonstrated mechanics map clearly to one seed value. Write that seed value with no mark.
- **Suggestion:** There is no seed match, or the value is an educated guess not explicitly present in the transcript. Write the proposed value with a trailing `*` (no space), for example `mount*` or `Kick spin backtake*`.

Star each field independently. A strong `start_position` may sit next to a suggested `end_position`.

The `*` means a reviewer can remap that field. Do not star a value that is both a seed match and supported by the chapter.

Do not refuse a tag because the finish, name, or ruleset is imperfectly stated. Propose the best value and star it when it is a guess.

### Hop fields on each technique

All hop fields are strings.

| Field | Value |
|---|---|
| `named_move` | Seed named-move name, a suggested name with `*`, or `""` |
| `ruleset` | `gi`, `no-gi`, `both`, or those values with `*` |
| `move_type` | Seed move type, or that type with `*` |
| `start_occupancy` | `top`, `bottom`, `neutral`, or those values with `*` |
| `start_position` | Seed position ID, or an ID/label with `*` |
| `end_occupancy` | `top`, `bottom`, `neutral`, `""` for submissions, or those values with `*` |
| `end_position` | Seed position or submission ID, or an ID/label with `*` |

Do not include a `system` field.

Do not store a family field.

Do not nest these fields inside `suggested_tags`.

### Occupancy definitions

Occupancy describes the relative positional role of the athlete performing the technique.

- `top`: The athlete occupies the dominant top position.
- `bottom`: The athlete occupies the bottom position.
- `neutral`: The athlete is standing or engaged in a neutral clinch.

Apply the following classification rules:

**Escape:** The athlete begins on the bottom in an established pin or control. The endpoint reflects the actual position achieved. An escape that results in standing may end in neutral occupancy.

**Pass:** The athlete begins on top and progresses past the opponent's guard while maintaining top positional advantage.

**Sweep:** The athlete begins on bottom and reverses positional advantage to establish top.

**Takedown:** The athlete begins in neutral standing or clinch and establishes a grounded position. End occupancy reflects the actual result.

**Transition:** The athlete changes position while maintaining the same relative positional role and positional advantage. Top remains top, bottom remains bottom, and neutral remains neutral.

**Reversal:** The athlete changes from a disadvantaged position to an advantageous position without the movement meeting the defined sweep or escape classifications. Do not use reversal as a generic substitute for an ambiguous move type.

**Back-take:** The athlete performs a movement intended to establish back control. Use `back-control` as the endpoint when that position is established.

**Submission:** The technique ends in a recognized submission. Use the submission ID as `end_position` and an empty string for `end_occupancy`.

When the movement type is imperfectly stated, still choose the best fit and star it if it is a guess.

### Field-specific rules

**`start_position`**

Use the seed position ID that best represents the actual starting position.

If the start is clear in the speech but the ID is a judgment call, use the closest seed ID with `*`.

If no seed ID fits, write a short suggested ID or label with `*`.

**`start_occupancy`**

Use the athlete's actual starting occupancy.

Do not classify based solely on whether the opponent is on top or bottom.

Star the occupancy when it is inferred rather than stated.

**`move_type`**

Use the move-type definitions above.

The classification must represent the overall technique rather than an incidental mechanical action.

Star the type when the chapter does not make the category explicit.

**`end_position`**

Use the actual final position or submission achieved when the chapter names it.

If the finish is implied (for example "get on top") and a seed leaf for this named move has an end, use that seed end with `*` unless the transcript contradicts it.

If no seed end fits, propose the closest seed ID or a short label with `*`.

For submissions, use the seed submission ID, starred when the choke or lock is implied rather than completed.

**`end_occupancy`**

Use the actual finishing occupancy.

Use `""` when `end_position` is a submission ID.

Star occupancy when it is inferred from the move type rather than stated.

**`named_move`**

If the speech, chapter title, or mechanics are a strong match to one seed named move, use that name with no mark.

If no seed name exists, or the match is an educated guess, write the best name (seed-closest or a short name from the chapter) with `*`.

**`ruleset`**

Use:
- `gi` when the instruction is clearly Gi-specific.
- `no-gi` when the instruction is clearly No-Gi-specific.
- `both` when applicability to both is established.

If the ruleset is only implied by the volume or by a remark such as "we don't have a gi," still fill it. Star it when that implication is the only evidence.

Do not leave `ruleset` empty when the volume has already established gi vs no-gi.

## 10. Approved move types

Prefer these values for `move_type`:

- `takedown`
- `sweep`
- `pass`
- `escape`
- `submission`
- `transition`
- `reversal`
- `back-take`

Prefer these values. If another type is required, write it with `*`.

## 11. Approved positions (ID)

Use these IDs for `start_position` and for `end_position` when the hop ends in a position.

- `standing` — Standing
- `clinch` — Clinch
- `front-headlock` — Front headlock
- `closed-guard` — Closed guard
- `open-guard` — Open guard
- `half-guard` — Half guard
- `deep-half-guard` — Deep half guard
- `z-guard` — Z-guard
- `butterfly-guard` — Butterfly guard
- `de-la-riva` — De La Riva
- `reverse-de-la-riva` — Reverse De La Riva
- `spider-guard` — Spider guard
- `lasso-guard` — Lasso guard
- `collar-sleeve` — Collar sleeve
- `x-guard` — X-guard
- `single-leg-x` — Single-leg X
- `k-guard` — K-guard
- `rubber-guard` — Rubber guard
- `worm-guard` — Worm guard
- `shin-to-shin` — Shin-to-shin
- `fifty-fifty` — 50/50
- `saddle` — Saddle
- `outside-ashi` — Outside ashi
- `headquarters` — Headquarters
- `leg-drag-position` — Leg drag position
- `side-control` — Side control
- `kesa-gatame` — Kesa gatame
- `north-south` — North-south
- `knee-on-belly` — Knee on belly
- `mount` — Mount
- `s-mount` — S-mount
- `technical-mount` — Technical mount
- `turtle` — Turtle
- `truck` — Truck
- `back-control` — Back control
- `crucifix` — Crucifix

Prefer these exact IDs. Star a guess (`mount*`). If no ID fits, write a short suggested label with `*`.

## 12. Approved submissions (ID)

Use these IDs for `end_position` when the hop finishes in a submission.

`end_occupancy` must be `""` for all submission endpoints.

- `rear-naked-choke` — Rear naked choke
- `guillotine` — Guillotine
- `darce` — D'Arce choke
- `anaconda` — Anaconda choke
- `arm-triangle` — Arm triangle
- `triangle` — Triangle choke
- `armbar` — Armbar
- `kimura` — Kimura
- `americana` — Americana
- `omoplata` — Omoplata
- `ezekiel` — Ezekiel choke
- `north-south-choke` — North-south choke
- `cross-collar-choke` — Cross collar choke
- `bow-and-arrow` — Bow and arrow choke
- `loop-choke` — Loop choke
- `clock-choke` — Clock choke
- `baseball-bat-choke` — Baseball bat choke
- `paper-cutter` — Paper cutter choke
- `gogoplata` — Gogoplata
- `straight-ankle-lock` — Straight ankle lock
- `heel-hook` — Heel hook
- `toe-hold` — Toe hold
- `kneebar` — Kneebar
- `calf-slicer` — Calf slicer
- `twister` — Twister
- `wrist-lock` — Wrist lock

Prefer these exact IDs. Star a guess. If no ID fits, write a short suggested label with `*`.

## 13. Approved named moves

Prefer the following names for `named_move`. A strong match is written as-is. Any other name, including a chapter-derived name with no seed leaf, is written with `*`.

Chair sit escape; Armbar from back control; Bow and arrow choke; Rear naked choke; Arm drag from butterfly; Float and smash pass; Body lock pass; Butterfly sweep; X-guard entry; Duck under; Body lock takedown; Inside trip; Outside trip; Lateral drop; Suplex; Standing guard break; Knee-in-tailbone break; Double forearm wedge break; Armbar from closed guard; Cross collar choke; Kimura from closed guard; Omoplata; Triangle choke; Hip bump sweep; Scissor sweep; Flower sweep; Lumberjack sweep; Waiter sweep; Omoplata sweep; Balloon sweep; Mission control entry; Worm guard entry; Collar-sleeve triangle; Crucifix choke; Berimbolo; Backstep vs De La Riva; Knee cut through hook; De La Riva sweep; Electric chair; Inside heel hook from 50/50; Front headlock go-behind; Front headlock escape; Anaconda choke; D'Arce choke; Guillotine choke; Peruvian necktie; Japanese necktie; Back take from half guard; Crossface and underhook pass; Knee slice pass; Backstep pass; Old school sweep; John Wayne sweep; Deep half entry; Knee shield entry; Knee cut pass; Long step pass; K-guard roll to saddle; Kesa gatame escape; Knee on belly escape; Baseball bat choke; Strip sleeve and backstep; Step over lasso smash pass; Lasso sweep; Back take from leg drag; Leg drag finish to side control; Gift wrap to back; Upa escape; Elbow-knee escape; Armbar from mount; Cross collar choke from mount; Ezekiel choke; Climb to S-mount; Follow to technical mount; North-south choke; Leg drag; Toreando pass; Over-under pass; Double under pass; X-pass; Shin pin pass; Tripod sweep; Sickle sweep; Heel grab sweep; Tomahawk sweep; Outside heel hook; Kiss of the dragon; RDLR to single-leg X; Gogoplata; S-mount armbar; Saddle escape; Inside heel hook from the saddle; Kneebar; Toe hold; Shin-to-shin to single-leg X; Elbow escape to guard; Frames and shrimp escape; Americana; Arm triangle choke; Kimura from side control; Paper cutter choke; Knee on belly transition; Knee slide to mount; Move to north-south; Straight ankle lock; Single-leg X sweep; Posture and elbow peel; C-scoop arm escape; Spider guard sweep; Standing arm drag; Sprawl; Guard pull; Snap down; Double leg takedown; Single leg takedown; Ankle pick; High crotch; Osoto gari; Seoi nage; Uchi mata; O goshi; Fireman's carry; Knee tap; Tai otoshi; Harai goshi; De ashi barai; O uchi gari; Imanari roll; Back take from technical mount; Calf slicer; Twister; Back take from turtle; Granby roll; Sit-out; Stand-up escape; Switch reversal; Clock choke; Crucifix entry; Tight waist far ankle breakdown; Truck entry; Worm guard sweep; Kick out leg; Backstep and knee twist; X-guard sweep; K-guard entry

Use the closest seed name without a mark only when it is a strong match.

Otherwise propose a name with `*`. Do not leave `named_move` empty when a reasonable suggestion exists.

## 14. Repair hints (not hop IDs)

The following are terminology references to help identify mistranscribed grappling words.

Neutral; Tie-up / clinch; Kumikata / clinch; Front headlock; Yoko-shiho-gatame; Kesa-gatame; Kami-shiho-gatame; Tate-shiho-gatame; Referee's position (bottom); All fours / turtle; Hadaka-jime; Sankaku-jime; Ude-hishigi-juji-gatame; Ude-garami; Sode-guruma-jime; Nami-juji-jime; Gyaku-juji-jime; Kata-juji-jime; Stand-up escape family; Okuri-eri-jime; Duck under; Body lock; Bear hug; Inside trip; O-uchi-gari; Ko-uchi-gari; Outside trip; O-soto-gari; Ko-soto-gari; Lateral drop; Suplex; Ura-nage; Bridge; Arm drag; Sprawl; Snapdown; Double leg; Morote-gari; Sukui-nage; Single leg; Kuchiki-taoshi; Ankle pick; Kibisu-gaeshi; High crotch; Seoi-nage; Ippon-seoi-nage; Uchi-mata; O-goshi; Fireman's carry; Kata-guruma; Knee tap; Tai-otoshi; Harai-goshi; De-ashi-harai; Foot sweep; Granby / hip heist family; Sit-out; Stand-up; Switch; Tight waist, far ankle

These hints help repair the transcript. They do not force a tag. If a hint suggests a tag that the chapter does not state, write that tag with `*`.

## 15. Source timestamp traceability

The cleaned transcript must not contain timestamps.

However, preserve source time ranges separately for each technique when the input contains timestamps that clearly identify the relevant instructional material.

`source_time_ranges` is an array of strings.

Examples:

```json
[
  "04:32-06:18",
  "08:12-09:45"
]
```

Rules:

- Use only timestamps supplied in the input.
- Associate ranges with the demonstrations and explanations that support the particular technique.
- Preserve the timestamp format supplied by the input.
- Use separate ranges when the relevant instruction occurs in noncontiguous portions of the chapter.
- Do not invent, estimate, or extrapolate timestamp boundaries.
- If a reliable source range cannot be established, return an empty array.

This field provides traceability to the original video without compromising transcript readability.

## 16. Output schema

Return exactly one JSON object with these root-level fields:

- `transcript_cleaned`
- `techniques`

Each technique object must contain these fields, in this order:

- `named_move`
- `ruleset`
- `move_type`
- `start_occupancy`
- `start_position`
- `end_occupancy`
- `end_position`
- `technique_steps`
- `main_ideas`
- `source_time_ranges`
- `suggested_tags`

All hop fields must be strings. Append `*` when the value is a suggestion for the reviewer to remap. Use `""` only when no reasonable suggestion exists.

`source_time_ranges` is an array of timestamp strings.

`suggested_tags` is an array of keyword strings extracted from `main_ideas`.

`main_ideas` is a string of two or three pithy imperative sentences.

Do not add other fields.

### Output example

```json
{
  "transcript_cleaned": "From closed guard, sit up, hip bump, and finish in mount. Keep the underhook as you move forward. If the opponent posts, continue driving toward the shoulder.",
  "techniques": [
    {
      "named_move": "Hip bump sweep",
      "ruleset": "both",
      "move_type": "sweep",
      "start_occupancy": "bottom",
      "start_position": "closed-guard",
      "end_occupancy": "top",
      "end_position": "mount",
      "technique_steps": "1. Closed guard, bottom: sit up and establish the underhook.\n2. Post the appropriate hand and bring the hips toward the opponent.\n3. Drive through the shoulder while maintaining the underhook.\n4. Come up onto the knee and establish mount.",
      "main_ideas": "Win the underhook and get your hips under him before you bump. Keep traveling toward the shoulder; use his post to finish the reversal.",
      "source_time_ranges": [
        "04:32-06:18"
      ],
      "suggested_tags": [
        "win the underhook",
        "hips underneath",
        "travel toward the shoulder"
      ]
    }
  ]
}
```

The example illustrates the output structure only. Always derive the actual content from the supplied chapter.

### No-technique example

For a chapter that discusses posture, grips, positional theory, or conceptual material without teaching a sufficiently complete technique:

```json
{
  "transcript_cleaned": "The cleaned chapter speech goes here.",
  "techniques": []
}
```

Do not manufacture a technique merely to populate the array.

## 17. Final validation

Before returning the JSON, validate the entire result.

### Transcript validation

- All meaningful instructional speech is preserved.
- Filler and redundant restatements are removed.
- Corrections and meaningful clarifications are preserved.
- Terminology repairs are defensible.
- No timestamps remain in `transcript_cleaned`.
- No outside knowledge has been introduced.

### Technique validation

- Every extracted technique is independently and sufficiently taught.
- Independent techniques have not been combined.
- Repeated demonstrations have not created duplicates.
- Materially different variations have been handled appropriately.
- Later explicit corrections supersede earlier instructions.
- Incomplete techniques have not been completed through assumptions.
- Each step is mechanically meaningful and in the correct order.
- The sequence begins with the actual starting position and ends with the demonstrated result.
- No steps have been added to meet an arbitrary count.

### Main-ideas validation

- Two or three pithy imperative sentences. Never more.
- The sentences are not a re-summarization of `technique_steps`.
- They carry the ideas that bear the most weight.
- No generic BJJ advice unsupported by the chapter.

### Classification validation

- Hop fields live on the technique object, not inside `suggested_tags`.
- Each classified technique represents one independently taught movement.
- Strong seed matches are unmarked.
- Educated guesses and values with no seed match end with `*`.
- Starred values are still filled; they are suggestions for remap, not blanks.
- Start and end occupancy are consistent with the movement.
- Submission endpoints use an empty `end_occupancy`.
- The hop describes the same movement represented by `technique_steps`.

### Suggested-tags validation

- `suggested_tags` is an array of strings.
- Every tag is a keyword or short phrase taken from `main_ideas`.
- No hop objects appear in `suggested_tags`.

### Structural validation

- The root object contains exactly the two required fields.
- Every technique object contains exactly the eleven required fields.
- Hop fields are strings.
- `suggested_tags` is an array of strings.
- `source_time_ranges` is an array of strings.
- No extra fields are present.
- No Markdown fences or explanatory text surround the JSON.
- All quotation marks, braces, brackets, and escape sequences are valid.
- The output parses as valid JSON.

Correct any identified errors before returning the result.

**Return JSON only. No Markdown, commentary, explanations, or additional text.**