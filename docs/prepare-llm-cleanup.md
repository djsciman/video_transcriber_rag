# Pare chapter speech

## Objective

Rewrite one chapter's raw speech as readable `transcript_cleaned`. Repair grappling terms. Strip `<sec>` timestamps. Do not summarize. Do not turn speech into steps. Do not extract movements, concepts, tags, or hops.

Return JSON only:

```json
{ "transcript_cleaned": "string" }
```

Do not add other keys.

## Input

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

Chapter speech is `transcript_raw` and may include nest timestamps such as `<1234.00>`.

Use titles and neighbors only to repair terminology. Do not import teaching from another chapter.

## Cleaning

- Remove filler, false starts, empty turns of phrase, jokes, and incidental talk that is not instruction.
- Collapse redundant restatements; keep a repetition that clarifies, expands, or corrects.
- Preserve meaningful terminology, examples, explanations, distinctions, and the instructor's voice.
- Repair a mistranscribed grappling term only when titles, neighbors, or the repair hints below strongly support it. If unsure, keep the closest defensible wording.
- Remove source timestamps such as `<12.34>`. The result is continuous prose without timestamps.
- Do not summarize the chapter. Do not reorganize speech into numbered technique steps.
- Do not invent explanations. Do not combine unrelated statements into new teaching.
- Do not extract techniques or concepts.

## Repair hints (terminology only)

These are names that ASR often mangles. They are not hop IDs and they do not require a tag.

Neutral; Tie-up / clinch; Kumikata / clinch; Front headlock; Yoko-shiho-gatame; Kesa-gatame; Kami-shiho-gatame; Tate-shiho-gatame; Referee's position (bottom); All fours / turtle; Hadaka-jime; Sankaku-jime; Ude-hishigi-juji-gatame; Ude-garami; Sode-guruma-jime; Nami-juji-jime; Gyaku-juji-jime; Kata-juji-jime; Stand-up escape family; Okuri-eri-jime; Duck under; Body lock; Bear hug; Inside trip; O-uchi-gari; Ko-uchi-gari; Outside trip; O-soto-gari; Ko-soto-gari; Lateral drop; Suplex; Ura-nage; Bridge; Arm drag; Sprawl; Snapdown; Double leg; Morote-gari; Sukui-nage; Single leg; Kuchiki-taoshi; Ankle pick; Kibisu-gaeshi; High crotch; Seoi-nage; Ippon-seoi-nage; Uchi-mata; O-goshi; Fireman's carry; Kata-guruma; Knee tap; Tai-otoshi; Harai-goshi; De-ashi-harai; Foot sweep; Granby / hip heist family; Sit-out; Stand-up; Switch; Tight waist, far ankle

Inside = toward the relevant primary body connection. Outside = away from it. Add `(inside …)` or `(outside …)` only when that meaning is clear and important. Do not replace an inside/outside term the instructor already spoke.

## Output

One JSON object with `transcript_cleaned` as a string. No `concepts`. No `techniques`. No `suggested_tags`.
