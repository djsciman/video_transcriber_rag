# Requirements inventory

Extracted from issues 52, 70, children 71-84, issue 1 Decisions so far, `GLOSSARY.md`, and `coach_app/` as behavioral evidence. Labels: **Required** / **Inferred** / **Proposed enhancement**.

Ids are stable for [requirements-traceability.md](requirements-traceability.md).

## Functional requirements

### Local coach-only application

| Id | Requirement | Status |
| --- | --- | --- |
| FR-01 | Only the coach uses the screens. Students never query. | Required — 52.1, 70.1, glossary Coach/Student |
| FR-02 | UI, curated store, corpus, and advisor reading stay on the coach's machine. | Required — 52.2, 70.2, issue 5 |
| FR-03 | Open in a browser on that machine. | Required — 70.3 |
| FR-04 | Bind is local (product: `127.0.0.1`). | Inferred — issue 70 close comment; `coach_app/app.py` |
| FR-05 | Every write goes through one `CuratedStore` facade. No second source of truth. | Required — 52/70 implementation decisions |
| FR-06 | Do not name a frontend framework, database engine, or advisor vendor in product specs. | Required — 52/70 out of scope |

### Persistence and first runtime

| Id | Requirement | Status |
| --- | --- | --- |
| FR-10 | Curated store survives closing the application. | Required — 70.4, #71 |
| FR-11 | Video root and transcript folder survive restart. | Required — 70.5, #71, #72 |
| FR-12 | Later runtime loads the same store with no import step. | Required — 70.6 |
| FR-13 | First runtime imports the consensus enrichment seed into the live catalog. | Required — 70.7, 52.72, #71 |
| FR-14 | Later runtime keeps catalog edits; does not re-import the seed over them. | Required — 70.8, 52.74, #71 |
| FR-15 | Coach sets video root and transcript folder from the UI. | Required — 70.9-10, #72 |
| FR-16 | Restart mid-topic restores that topic, system words, map, and sheet. | Required — 70.103 |
| FR-17 | Default persisted location is a folder on disk (`CuratedStore.open`). | Inferred — `store.py`, README; spec forbids naming engine/layout |

### Topics

| Id | Requirement | Status |
| --- | --- | --- |
| FR-20 | Home lists open topics with kept name and gi or no-gi. Empty list is valid. | Required — 70.11, #72, #74 |
| FR-21 | Open a topic by submitting name as typed plus gi or no-gi. | Required — 52.39, 70.12, #74 |
| FR-22 | Blank name opens nothing. | Required — 70.13, #74 |
| FR-23 | Trailing spaces strip. Leading spaces are kept. | Required (trailing) — 52.40, 70.14; Inferred (leading kept) — `tests/test_topics.py` |
| FR-24 | Same ruleset + same kept name reopens that topic. | Required — 52.41, 70.15, #16 |
| FR-25 | Any other characters, including spelling, open a new topic. | Required — 52.42, 70.16 |
| FR-26 | Name and ruleset stay fixed on an open topic. | Required — 52.43, 70.17, #17 |
| FR-27 | Remove a topic at any time; belonging records clear; the pair can open again. | Required — 52.44, 70.18, glossary Topic |
| FR-28 | One topic produces one unit. Weekly mix of unrelated topics is out of scope. | Required — 52.45, 70.19 |
| FR-29 | Gi and no-gi namesakes are different topics. | Required — 52.46, glossary Gi/No-gi/Topic |

### Curation

| Id | Requirement | Status |
| --- | --- | --- |
| FR-30 | Raw volume stays raw until the coach accepts a citation. | Required — 52.3, glossary Volume/Corpus |
| FR-31 | Pick completed volume JSON from disk. | Required — 70.20, #73 |
| FR-32 | Clean-up nests speech under real chapters; drops empty recognizer fields; copies `video_file`; strips only uh/um/er fillers. | Required — 52.4-6, #19 |
| FR-33 | Two or more titled chapter ranges are real chapters; none or one whole-recording chapter is an untitled part (unciteable until movements are marked). | Required — 52.7-8, 70.21-22 |
| FR-34 | Propose cleaned statements before any store write. One movement, one instructor, one chapter. | Required — 52.13, 70.23 |
| FR-35 | Statement keeps every spoken detail from each showing; unspoken shown detail stays off. | Required — 52.14-15, glossary Cleaned statement |
| FR-36 | Each showing that added a detail has its own playback link. | Required — 52.16, glossary Playback link |
| FR-37 | Citation bar: >= 1 minute; skip intro/outro/named roll; multi-idea titles split per movement. | Required — 52.17-19 |
| FR-38 | Coach corrects move name and step bullets, then accepts or dismisses. Accept writes instructional, volume, citation. Dismiss writes nothing. | Required — 52.20-21, 52.26, 70.24-26, #73 |
| FR-39 | After accept, correct+save replaces the statement with no earlier version. Provenance fields stay. Movement name follows a move-name edit. | Required — 52.22-24, 70.27-28, #23, glossary Cleaned statement |
| FR-40 | Coach may remove an accepted citation. | Required — 52.25, 70.29, glossary Citation |
| FR-41 | Playback opens video root + transcript folder + `video_file` at showing speech start. Missing file still admits/shows the citation with timestamp and volume name. | Required — 52.27-28, 70.30-31, #13 |
| FR-42 | Spoken house terms survive; unnamed motion is not given to the advisor. | Required — 52.29-30, #14 |
| FR-43 | Clean-up does not enter the store. | Required — 52.71 |

### Ruleset and other-ruleset

| Id | Requirement | Status |
| --- | --- | --- |
| FR-50 | An instructional is gi or no-gi as a whole. | Required — 52.31, glossary Instructional |
| FR-51 | Locked unlabeled four are no-gi; two mixed series are gi. | Required — 52.32-33, #11 |
| FR-52 | Mark other-ruleset aside on a showing; caveat sits on that showing. | Required — 52.34, 70.32, glossary Other-ruleset variant/Caveat |
| FR-53 | After a topic is open, offer each matching instructional of the other ruleset that already has at least one accepted citation. Coach welcomes each on its own. | Required — 52.35, 70.33, #15 |
| FR-54 | Later yes or no replaces the current choice. Yes carries one caveat used by each citation from that instructional on that topic. | Required — 52.38, 70.34, glossary Caveat |
| FR-55 | Welcomed other-ruleset material informs analysis; those citations enter a lesson only when the coach places them. | Required — 52.36-37, 70.35 |
| FR-56 | Same-ruleset accepted citations are selectable with no extra choice. | Required — 52.47 |

### Enrichment finder and placement

| Id | Requirement | Status |
| --- | --- | --- |
| FR-60 | Finder browses the live catalog: positions, types of move, submissions, named moves, catalog systems. | Required — 70.36, #75, glossary Enrichment |
| FR-61 | Dimensional search (position, sweep, submission, instructor, ruleset, and like). | Required — 70.37, 52.128 |
| FR-62 | Hierarchy browse: start position -> type of move -> end position or submission. | Required — 70.38, #24 |
| FR-63 | One position identity for start and end; submissions end-only. | Required — 52.75-76, 70.39-40 |
| FR-64 | Coach add, rename, move, delete on the live copy. Rename/move keep citation links. Delete uncategorizes. | Required — 52.73, 52.86-87, 70.41-43 |
| FR-65 | Uncategorized citations live in their own browse bucket; not offered on a lesson or Design mark until linked. | Required — 70.44, glossary Uncategorized |
| FR-66 | One scrollable placement-review pass when new citations enter; optional and repeatable. | Required — 52.84-85, 70.45-46, #76 |
| FR-67 | Coach-authored citation: movement name + step bullets on a named move; no instructional, volume, chapter, or playback. | Required — 52.88, 70.47, glossary Citation |
| FR-68 | Judo/wrestling cross-refs searchable as alternate names. | Required — 52.89, 70.48 |
| FR-69 | Named-move leaves tagged gi, no-gi, or both; higher path levels shared. Occupancy inferred (pass top, sweep bottom, takedown neutral, escape bottom on pin/control, transition same side and family). | Required — 52.77-80 |
| FR-70 | Catalog system = two or more named moves that create a dilemma. | Required — 52.81, glossary System |
| FR-71 | Lesson connects to exactly one named move or exactly one catalog system. | Required — 52.82 |
| FR-72 | Catalog organize stays on the finder, not Design. | Required — 52.96, 70.71 |

### Briefing and system

| Id | Requirement | Status |
| --- | --- | --- |
| FR-80 | Briefing before the coach determines the system. Names the open topic. No class split. | Required — 52.49-50, 52.59, 70.49-50, 70.54, #78 |
| FR-81 | Advisor selects by reading movement and cleaned statement. | Required — 52.48 |
| FR-82 | Same-ruleset citations: instructor, instructional, volume, chapter, instructor move name, step bullets, playback. | Required — 52.51, 70.51 |
| FR-83 | Step bullets name body part, action, and opponent body part when there is one. Inside = toward primary connection; outside = opposite. | Required — 52.52-54 |
| FR-84 | Other-ruleset block asks why paths differ; may-transfer and depends-on lists; does not pick a winner. | Required — 52.55-56, 70.52 |
| FR-85 | Same-ruleset disagreement only when two methods of one ruleset conflict; each side with its citation. | Required — 52.57-58, 70.53 |
| FR-86 | Store holds neither a disagreement record nor a citation list on the topic. | Required — 52.70 |
| FR-87 | Topic holds system words, empty until chosen, replaced in place, no history. Remains after the unit. | Required — 52.62-64, 70.55-56, #22, glossary System |
| FR-88 | Earlier same-ruleset system shown beside a side a student cannot follow together with it. | Required — 52.65, 70.57, glossary System conflict |
| FR-89 | Set-aside records this topic + earlier topic; several can sit on one topic; ending removes the pair; advisor reads live words, no frozen copy. | Required — 52.66-69, 70.58 |
| FR-90 | Other side of a disagreement is available as partner-job text. | Required — 52.61 |
| FR-91 | Topic-level system (how this topic is taught) is a different record from a catalog system (dilemma of named moves). | Required — 52 implementation decisions, glossary System |

### Design, Draft, Edit, Read, print

| Id | Requirement | Status |
| --- | --- | --- |
| FR-100 | Design is a full-width force graph of occupancy, named moves, and systems. Unordered. Does not pack classes. | Required — 52.90, 52.97, 70.59, 70.72, #28 |
| FR-101 | Add walk: family -> position -> occupancy -> type -> end -> named move. Named move replaces the type mark. Occupancy/type filtered by family. | Required — 52.91, 70.60-61 |
| FR-102 | Empty-canvas click starts add with dashed draft mark. Breadcrumb rewind. Double-click nearby add with occupancy set. | Required — 70.62-64 |
| FR-103 | Left-click edits (named move, already-linked citations, coach notes). Right-click deletes. Pan, zoom, recenter, reset-marks. Labels offset with leaders, no overlap. | Required — 70.65-68 |
| FR-104 | Design reads live catalog with inferred occupancy. Marks offer only already-linked citations. | Required — 52.93-95, 70.69-70 |
| FR-105 | Unit paragraph above the canvas. Layout B: prompt, then canvas, then Draft. | Required — 52.98, 52.130, 70.73, 70.77, #30 |
| FR-106 | Propose from the paragraph fills canvas and first Draft together. | Required — 52.99, 70.74, #81 |
| FR-107 | Convert packs a hand-built canvas. Empty map refuses Convert with a visible reason. | Required — 52.100-101, 70.75-76 |
| FR-108 | First Draft: glued technique + following drill, class cuts, partner-job stubs, colored class cards, dashed, no-edit, no Playback column. | Required — 52.102-104, 70.78, 70.82 |
| FR-109 | Pinned catalog system packs as one glued block unless a member is isolated (Tight waist: roll-through may isolate). | Required — 52.103 |
| FR-110 | Citations fall back to the first linked citation, preferring specific named-move cites. Other-ruleset citations do not pack by fallback. | Required — 52 packing notes; Inferred other-ruleset fallback — `tests/test_build.py` |
| FR-111 | Read and Edit are modes of the same class-card sheet. Draft stays no-edit. | Required — 52.105, 70.79, #82 |
| FR-112 | Technique What-to-run = full step bullets. Glued drill What-to-run = partner-job text only. | Required — 52.106-107, 70.80-81 |
| FR-113 | Edit: add/remove/drag including across class cuts. Glue: drag together, add inserts drill, remove removes drill. Drag that would empty a class is refused. No class cap. Every class has at least one lesson. | Required — 52.108-113, 70.84-89 |
| FR-114 | Class may have no technique. Any lesson type may open a class. Purpose line empty until written. | Required — 52.114-116, 70.90 |
| FR-115 | After first Draft, coach adds sparring, games, drill-only. Add-lesson pulls Custom, dimensional search, hierarchy, or named moves already on the map. | Required — 52.122-123, 70.91-92 |
| FR-116 | Place on a unit saves under Custom with no separate Save. Pull from Custom copies fields; technique brings glued drill. | Required — 52.124-125, 70.93-94 |
| FR-117 | Custom library screen outside unit build: create, edit, delete. Hierarchy shows Custom through the named move or system it connects to. | Required — 52.126, 70.95, #83, glossary Custom lesson |
| FR-118 | Unit history of saved states. Copy creates a new editable unit; past entry unchanged. | Required — 52.127, 70.96, glossary Unit |
| FR-119 | Read-mode day-of checkboxes are a flourish and are not stored. | Required — 52.133, 70.83 |
| FR-120 | Success watch is qualitative (none/some/most/all attempting; none/some/most/all completing or coming close against a better partner). Not a stored clipboard. Both people free inside the scenario. | Required — 52.120-121, 70.101, #4 |
| FR-121 | Print duplex letter packet: page 1 landscape Design canvas 0.5 in margins; later pages portrait class cards 0.5 in margins; keep each class whole; hide unit paragraph and success watch on print. Browser print; no named PDF library. | Required — 52.131, 70.97-100, #84 |
| FR-122 | Move among finder, topic, briefing, Design, and sheet without losing store writes. | Required — 70.102 |
| FR-123 | Product screens omit prototype banners, variant switchers, walkthroughs, last-change lines, state dumps. Match locked green-box layouts. | Required — 70.104-105 |

## Inputs and outputs

| Direction | Artifact | Status |
| --- | --- | --- |
| In | Completed volume JSON (speech segments, chapters, `video_file`) | Required — 52 pipeline consume, 70.20 |
| In | Consensus enrichment seed `docs/enrichment-seed/seed.json` (first runtime only) | Required — 52.72, 70.7 |
| In | Video files under video root + transcript folder + `video_file` | Required — playback |
| In | Coach text: topic name, system words, unit paragraph, purpose lines, partner job, scenario, condition, statement edits, coach-authored citations, catalog names | Required |
| Out | Accepted citations, instructionals, volumes | Required |
| Out | Topics, other-ruleset choices, set-asides | Required |
| Out | Live enrichment catalog | Required |
| Out | Unit, classes, lessons, Custom lessons, unit history | Required |
| Out | Design session marks (persisted with the store) | Required — 70.103; Inferred as store fields — `store.py` `design_sessions` / `sheets` |
| Out | Briefing memo (ephemeral advisor output; not a store record) | Required — 52.70 |
| Out | Draft / sheet modes | Required |
| Out | Print packet page records | Required |
| Out | Playback path + speech start (or missing-file lookup fields) | Required |

## Data dependencies

- Curation depends on pipeline-completed JSON, not on live Whisper/ffmpeg. **Required**.
- Playback depends on video root, transcript folder, and `video_file`. **Required**.
- Briefing depends on accepted citations + other-ruleset yes. **Required**.
- Placement depends on live named-move nodes. **Required**.
- Design depends on live catalog + already-linked citations. **Required**.
- Propose/Convert depend on a packable map (named-move or system marks). **Required**.
- Edit add-lesson depends on Custom, finder, and current Design marks. **Required**.
- Print depends on current canvas + current sheet. **Required**.
- One topic one unit: `put_unit` drops any other unit of that pair. **Inferred** from `store.py`; **Required** intent from 52.45.

## Business rules (selection)

See glossary plus:

- Citation bar and clean-up nesting rules (issue 19 / 52). **Required**.
- Glue rule. **Required**.
- Empty classes forbidden. **Required**.
- Uncategorized withheld. **Required**.
- In-place replace: cleaned statement, system words, other-ruleset yes/no. **Required**.
- Unit history is a snapshot list; citation text is not. **Required**.
- Custom is not a topic belonging; it survives topic remove. **Inferred** from `remove_topic` + glossary Custom lesson.

## Automation opportunities (specified)

| Step | Automated | Coach-controlled | Status |
| --- | --- | --- | --- |
| Clean-up | Nest parts, drop recognizer fields, strip fillers | Review nested parts | Required |
| Propose statements | Draft move name + bullets from speech | Correct, accept, dismiss | Required |
| Placement | Propose named-move id | Accept, correct, skip | Required |
| Briefing select | Read movement + statement | Determine system | Required |
| Propose packing | Fill canvas + Draft from paragraph | Edit after | Required |
| Convert packing | Order glued classes from marks | Edit after; refuse empty | Required |
| Place -> Custom | Save on place | Edit Custom copy later | Required |
| Seed import | First runtime only | Later catalog edits | Required |

**Proposed enhancement:** surface an inbox of awaiting volumes, uncategorized citations, unanswered other-ruleset offers, empty system words, unpackable maps. Specs require the underlying states, not a unified inbox.

## Error conditions (**Required** unless noted)

| Condition | Response |
| --- | --- |
| Blank topic name or ruleset not gi/no-gi | Open nothing |
| Empty map Convert | Refuse with visible reason (product copy: "The map has no named moves or systems to convert.") |
| Drag that would empty a class | Refuse |
| Lesson with neither named move nor catalog system (or both) | Validation error |
| Catalog system with fewer than two named moves | Validation error |
| Missing video file | Citation still shown; timestamp + volume name |
| Untitled part / no real chapters | Called out; unciteable until movements are marked |
| Chapter under one minute, intro/outro/named roll | Left out of proposals |
| Dismiss proposal | Store nothing |
| Second seed import | No-op |
| Topic page for a pair that is not open | Empty copy ("That topic is not open.") — Inferred from `ui_topics.py` |
| 404 unknown path | Inferred from `app.py` |

## External dependencies

| Dep | Role | Status |
| --- | --- | --- |
| Video root | Playback resolution | Required — 70.9 |
| Transcript folder | Volume JSON + `video_file` layout the pipeline wrote | Required — 70.10 |
| Completed volume JSON | Curation input | Required |
| `docs/enrichment-seed/seed.json` | First-runtime catalog | Required |
| Browser print | Duplex packet | Required — 70 |
| Corpus-prep pipeline (issue 42) | Produces JSON; not in-app | Required as upstream |
| ADR 0001 / 0002 | Chapter-start sampling and skip/force. Do not govern screens. | Required for corpus quality only |

## Assumptions and constraints

- Local single-coach machine. **Required**.
- Advisor vendor unspecified; stand-in in repo. **Required**.
- Empty Danaher folders stay out until volumes arrive. **Required** — 52.134.
- Cloud backup, file sync, whether advisor text may leave the machine: unspecified. **Required** as out of scope.
- Design/Build are coach-language phases, not glossary terms. Draft/Read/Edit are UI modes. **Required**.
- Prototype HTML is not product code. **Required**.
- `coach_app` stdlib-only at import. **Inferred** from README / issue 70 close; not a redesign lock (issue 85 leaves stack to review).
