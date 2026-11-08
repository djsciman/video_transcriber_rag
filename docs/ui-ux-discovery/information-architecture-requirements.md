# Information architecture requirements

What must remain findable, grouped, and preserved. This is not a nav mock. Issue 85 already records that the spec-70 flat nav is a deficiency.

## Locked groupings (**Required**)

The coach thinks in these objects (glossary + specs). A redesign may restack screens but must not flatten these distinctions.

1. **Corpus vs curated store** — transcribed JSON is not advice until accept.
2. **Topic** — one gi or no-gi kept name; one unit; name/ruleset fixed.
3. **Catalog (enrichment)** — positions, types of move, submissions, named moves, catalog systems; uncategorized bucket.
4. **Citation** — corpus vs coach-authored; provenance vs words.
5. **Briefing vs packing** — analysis has no class split; Design does not pack; Build packs.
6. **Map vs sheet** — unordered Design vs ordered classes.
7. **Draft vs Read vs Edit** — modes of one class-card sheet.
8. **Custom vs current unit vs history snapshot**.
9. **Topic-level system words vs catalog system (dilemma)**.
10. **Same-ruleset teaching vs other-ruleset caveat**.

## Context that must be preserved across destinations (**Required** 70.102-103)

When the coach moves among finder, topic, briefing, Design, and sheet:

- Store writes already made
- Open topic identity (kept name + ruleset)
- System words
- Design marks
- Sheet (classes/lessons/mode)
- Video root and transcript folder
- Catalog edits
- Other-ruleset choices and set-asides

Restart restores topic, system, map, sheet.

## Destinations the coach must be able to reach

Whether they remain separate screens is a review decision (issue 85 "Not yet specified"). The **capabilities** are **Required**:

| Destination (spec-70 name) | Coach job |
| --- | --- |
| Home | Topic list, open topic, settings |
| Curate | Volume pick, proposals, accept/dismiss, post-accept edit, playback, other-ruleset showing mark |
| Place | Placement pass, coach-authored citation |
| Finder | Search, hierarchy, uncategorized, catalog CRUD |
| Topic | Fixed identity, remove, other-ruleset welcome, links to briefing/Design |
| Briefing | Memo + system words + set-asides |
| Design | Paragraph, map, Propose/Convert, Draft stack |
| Sheet | Draft/Read/Edit class cards, add-lesson sources |
| Custom | CRUD without an open unit |
| History | Save, list, copy |
| Print | Packet |

**Inferred:** Settings live on Home, not a nav item. Print and briefing have empty nav labels.

## Hierarchy the coach walks (**Required**)

Finder and add-lesson:

```
start position -> type of move -> end position or submission -> named-move leaves
```

Design add walk:

```
family -> position -> occupancy -> type of move -> end -> named move
```

Occupancy is on the named move, not a second position record.

Custom hierarchy: show the lesson through the named move or system it connects to.

## Search dimensions (**Required**)

Position, sweep, submission, instructor, ruleset, and like; plus cross-refs as alternate names.

## What must stay off certain surfaces (**Required**)

| Surface | Must not show |
| --- | --- |
| Briefing | Class splits |
| Design | Catalog organize; uncategorized citations; class cuts |
| Draft | Edit controls; Playback column |
| Print class cards | Unit paragraph; success watch |
| Lesson / Design mark | Uncategorized citations |
| Product chrome | Prototype banners, variant switchers, walkthroughs, last-change, state dumps |

## Home and "what next"

**Required:** Home lists topics; empty is valid.

**Inferred / Proposed enhancement:** Home (or a shell) should distinguish awaiting / in progress / needs decision. Specs do not define that chrome. Issue 85 lists lack of next-action guidance as a current deficiency.

Candidate proactive surfaces (**Proposed enhancement**, states are Required):

- Uncategorized citation count
- Other-ruleset offers without a choice
- Topic with empty system words
- Packable map with no Draft
- Empty Convert reason
- Newly accepted citations since last placement pass
- Missing video files among accepted showings

## Sample fixtures (do not hard-code as the only topics)

- Briefing sample: gi half guard (issue 8 / 52 notes)
- Design/Build sample: gi Tight waist (home transitions + Tight waist trilemma)
- Occupancy examples: Knee slice pass from half guard is top; Old school sweep is bottom (issue 29)

## Prototype visual sources (layout lock for spec-70; redesign may replace after review)

See issue 70 prototype table. Green boxes are coach-final for the current product. Redesign review may change visual system; domain groupings above stay.
