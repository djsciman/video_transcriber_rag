# Open questions, conflicts, gaps

Items for [Review: UI/UX Research Findings, Prototype Evaluation, and Design Decisions](https://github.com/djsciman/video_transcriber_rag/issues/89). Domain rules stay closed unless the coach reopens them.

## Conflicts

### C1. Issue 1 inventory vs issue 52 locked rulesets

Issue 1 Decisions still narrate "4 not decidable, 2 mixed; the coach still labels." Issues 11 and 52 locked those six series (four no-gi, two gi). **Resolution for this tree:** follow #52. Treat #1 as historical map prose.

### C2. "System" overloaded

Glossary System is both (a) how one topic is taught (coach words on the topic) and (b) two or more named moves that create a dilemma (catalog node). Issue 52 implementation decisions already split them. UI copy must not collapse the two.

### C3. Remove-topic belongings vs persisted map/sheet

Spec: remove clears what belonged to the topic. Implementation `CuratedStore.remove_topic` drops topic, other-ruleset choices, set-asides, units/classes/lessons, unit histories. It does not pop `design_sessions` or `sheets` for that pair. **Gap / possible defect.** Redesign should clear map and sheet with the topic unless review says otherwise.

### C4. Hand-build empty vs Convert refuse

Issue 9: coach may start empty. Issue 30/70: empty map refuses Convert. Compatible if "start empty" means Edit after some packing path, or Design with no marks yet. **Ambiguity:** can the coach create classes with no Propose/Convert? UI Edit add-lesson exists once a sheet exists; creating a sheet without Draft is underspecified.

## Ambiguities

### A1. Must the coach choose a system before Design?

Briefing is "before I determine the system." Design does not require system words in code. Empty system is a valid store state. **Guidance vs gate** is unspecified.

### A2. Must every offered other-ruleset instructional be answered?

Offer is Required. Forced yes/no before briefing is not stated. Unanswered means not welcomed, so those citations stay off the briefing.

### A3. When is unit history saved?

UI exposes save. Specs do not auto-snapshot on every Edit. Later Propose/Convert / `put_unit` replaces the current unit. Coach can lose packing if they skip save. **Inferred** risk.

### A4. Leading spaces in topic names

Trailing strip is Required. Tests keep a leading space as a distinct name. Confirm this is intended.

### A5. Ruleset for instructionals not in the locked map

`instructional_ruleset` uses the locked six, else the `ruleset` argument, else `""`. How the Curate UI supplies ruleset for a new series is an implementation detail to keep visible.

### A6. Disagreement in the product stand-in

`BriefingAdvisor.disagreeing_sides` returns `()`. Tests inject advisors that flag sides. Product briefing may show no disagreement unless the stand-in is replaced. Spec requires disagreement **when** two methods conflict; detecting conflict is advisor work, vendor unspecified.

### A7. Propose packing stand-in

`BuildAdvisor.design_from_paragraph` only fills the Tight waist sample when the paragraph mentions that phrase. Real Propose for other topics is unspecified beyond "stand in the vendor."

### A8. Movement marks on untitled parts

Issue 18: all videos will have chapter markers. `propose_statements` still accepts `marks` to slice untitled parts. Curate UI may or may not expose mark entry. **Gap** if awaiting-parse volumes remain.

### A9. Current topic pointer

`set_current_topic` is called from Design, Sheet, history copy — not from topic open on Home (`ui_topics.py`). Resume-after-restart of "the" topic may depend on which screen last wrote it.

### A10. Citation list on a Design mark when many citations belong to one named move

Explicit fog on issues 1 and 52/70 out of scope.

## Gaps (specs silent)

| Gap | Notes |
| --- | --- |
| G1 | Unified inbox of awaiting work |
| G2 | Watching the transcript folder for new JSON |
| G3 | Deduplicating re-curated chapters |
| G4 | Statement undo / citation version history (explicitly **not** a spec; only a proposed enhancement) |
| G5 | How the coach's experience is written into the system beyond coach-authored citations (52 out of scope) |
| G6 | Whether units shorten time to performance (52 out of scope) |
| G7 | Cloud backup / file sync / advisor text leaving the machine (52/70 out of scope) |
| G8 | Multi-coach, multi-machine |
| G9 | Accessibility and performance numeric targets (85 not yet specified) |
| G10 | Desktop vs tablet vs print visual system beyond local browser (85) |
| G11 | How much spec-70 screen inventory is re-chunked (85) |
| G12 | Copy history when id missing; delete confirmation for topic/citation/Custom |
| G13 | Stale playback when the coach moves files after accept |
| G14 | Clearing design session/sheet on topic remove (see C3) |
| G15 | Whether Custom lessons of a removed topic's named moves should be listed as orphaned |

## Under-specified interaction

- Destructive removes (topic, citation, catalog node, Custom) have no spec'd confirm step.
- No spec'd undo except history copy for units and in-place replace for words.
- No spec'd progress on a multi-proposal curate session if the browser closes mid-list (proposals are not stored; accepted ones are).
- Dimensional search "and like dimensions" is open-ended.
- Success watch has no on-screen instrument beyond Read; qualitative lists are in the spec.

## Assumptions this tree used

- Product behavior on `implement/spec-70` at `1654281` is evidence for journeys, not a visual lock for the redesign.
- Pipeline ADRs do not add coach screens.
- Sibling files `ux-philosophies.md` and `tech-visual.md` are out of this branch.

## Proposed enhancements (not locked)

1. Home/shell inbox: uncategorized, unanswered welcomes, empty system, unpackable map, missing videos.
2. After-accept deep-link into placement.
3. Batch accept on placement (conflicts with per-item review if done silently).
4. Citation text history / undo.
5. Dedup on re-curate.
6. Auto history snapshot before Propose/Convert replaces the unit.
7. Confirm on remove topic.
8. Folder watcher for new volume JSON.

Label these on the review child. Do not ship them as if issue 52/70 required them.
