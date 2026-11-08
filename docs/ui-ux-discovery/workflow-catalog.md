# Workflow catalog

Named workflows the redesigned interface must still support. Journeys in [critical-user-journeys.md](critical-user-journeys.md) are the coach-facing stories; this file is the state machine.

## End-to-end advising flow (**Required**)

```
corpus JSON (pipeline, out of app)
  -> clean-up (raw parts; not stored)
  -> propose statements (not stored)
  -> coach accept / dismiss
  -> accepted citations in curated store
  -> placement review (optional, repeatable)
  -> finder organize (anytime)
  -> open topic
  -> other-ruleset welcome (per instructional)
  -> briefing memo (ephemeral)
  -> choose system / set-asides
  -> Design map (unordered)
  -> Propose or Convert
  -> Draft (no-edit)
  -> Edit / Read modes of the same sheet
  -> print packet
  -> Custom grows on place; history on save; copy to re-teach
```

Design/Build are coach-language phases, not glossary terms.

## Workflows

### W1. Store runtime

| | |
| --- | --- |
| States | no-location in-memory (`CuratedStore()` tests); persisted `open(location)` |
| Transitions | first open -> import seed if not imported; later open -> restore pickle payload including settings, design sessions, sheets, current topic |
| Decisions | video root; transcript folder |
| Status | Required #71 #72 |

### W2. Ingestion (cleanup -> propose -> accept)

| | |
| --- | --- |
| States | raw JSON; cleaned parts; proposals; accepted citation; dismissed (nothing) |
| Transitions | pick file -> cleanup_volume -> propose_statements -> correct draft -> accept or dismiss -> optional post-accept correct/remove |
| Decision points | accept vs dismiss; wording; other-ruleset mark on a showing |
| Automation | cleanup, propose |
| Status | Required |

### W3. Classification (placement)

| | |
| --- | --- |
| States | uncategorized; proposed link; linked to named move |
| Transitions | enter_citations / propose_placement_pass -> accept/correct/skip -> repeat on remaining uncategorized |
| Decision points | accept / correct / skip |
| Status | Required #76 |

### W4. Catalog organize

| | |
| --- | --- |
| States | seed-imported live tree; coach-edited tree |
| Transitions | add / rename / move / delete node; delete uncategorizes citations; rename/move keep ids/links |
| Decision points | identity of a named move; whether to drop a node |
| Status | Required #75. Corpus must not auto-edit the tree. |

### W5. Topic lifecycle

| | |
| --- | --- |
| States | unopened; open (name+ruleset fixed, system maybe empty); removed |
| Transitions | submit -> open or reopen; remove -> clear belongings -> pair available again |
| Decision points | spelling; gi vs no-gi; remove |
| Status | Required #74 |

### W6. Other-ruleset welcome

| | |
| --- | --- |
| States | not offered (no other-ruleset citations); offered unanswered; yes+caveat; no |
| Transitions | open topic + cited other-ruleset instructional -> offer; yes/no replace in place |
| Decision points | yes / no / later change |
| Status | Required #77. Unanswered is **Inferred** as allowed. |

### W7. Briefing and system

| | |
| --- | --- |
| States | no briefing yet; memo shown; system empty; system current wording; system conflict visible; set-aside |
| Transitions | brief_topic -> choose_system (replace) -> set_aside / end_set_aside |
| Decision points | system words; which earlier systems stay off |
| Status | Required #78 #79. Disagreement is computed, not stored. |

### W8. Design session

| | |
| --- | --- |
| States | empty canvas; add-walk in progress (dashed draft mark); marks placed; mark editing |
| Transitions | pick walk steps; add named move/system; edit/delete mark; Propose may fill marks |
| Decision points | hops; citations on a mark; notes |
| Status | Required #80 |

### W9. Packing

| | |
| --- | --- |
| States | unpackable (no named-move/system marks); packable; Draft present |
| Transitions | Propose (paragraph+advisor); Convert (packable only); refuse Convert |
| Decision points | Propose vs Convert |
| Status | Required #81 |

### W10. Sheet modes

| | |
| --- | --- |
| States | Draft (no-edit); Read; Edit |
| Transitions | set_mode; Edit mutations persist; Read checkboxes do not |
| Decision points | packing; lesson sources; purpose/partner-job/scenario/condition |
| Status | Required #82 |

### W11. Custom and history

| | |
| --- | --- |
| States | Custom lesson exists; history snapshot exists; current unit |
| Transitions | place -> Custom save; CRUD Custom; save_history; copy_history -> new editable unit (drops other unit of same topic via `put_unit`) |
| Decision points | which snapshot; delete Custom |
| Status | Required #83 |

### W12. Print

| | |
| --- | --- |
| States | packet pages computed from current canvas + sheet |
| Transitions | GET print screen; browser print |
| Status | Required #84 |

## State vocabulary the UI should communicate

Specs do not name a single status enum. The following are **Required** underlying states, named here for IA:

| State | How it arises |
| --- | --- |
| Awaiting attention | Uncategorized citations; offered other-ruleset with no choice (**Inferred** unanswered); empty system if the coach wants one before Design (**Inferred** as guidance, not a hard gate) |
| In progress | Add-walk; open topic with empty map; Draft not yet converted |
| Needs decision | Statement proposal; placement proposal; welcome yes/no; Convert on empty canvas (decision is "place marks first") |
| Done | Accepted+linked citation; system words present; packable map packed; sheet in Read |
| Needs validation | Post-accept statement the coach may still correct; stand-in briefing/packing the coach must read |
| Newly admitted | Citation just accepted, still uncategorized |
| Changed records | In-place replace of statement, system, yes/no; unit replaced by later pack or history copy |

**Proposed enhancement:** persist those labels. Specs only persist the records.

## Decision points (coach)

1. Accept / dismiss statement
2. Wording of cleaned statement
3. Remove citation
4. Other-ruleset showing mark
5. Welcome yes/no
6. Topic name spelling and ruleset
7. Remove topic
8. Placement accept/correct/skip
9. Catalog add/rename/move/delete
10. System words
11. Set-aside / end
12. Map marks and citations on marks
13. Propose vs Convert
14. Class cuts and lesson mix
15. Purpose / partner job / scenario / condition
16. Save history / copy history
17. Print

## What is not a workflow (**Required** out of scope)

- Weekly calendar mixing topics
- Student login
- Corpus-prep match/organize/detect/transcribe inside this UI
- Re-scraping enrichment
- Citation version timeline
