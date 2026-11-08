# Coach operational tasks

Work the coach performs, categorized. A-D come from [issue 86](https://github.com/djsciman/video_transcriber_rag/issues/86). **E. Teaching** is required by the specs (Read, print, success watch) and is added here.

Each task: **Required** unless labeled otherwise.

## A. Maintenance

Keep the curated store truthful.

| Task | Spec support | Notes |
| --- | --- | --- |
| Set and correct video root and transcript folder | 70.9-10 | Playback depends on them |
| Import seed once; never let a later runtime wipe catalog edits | 70.7-8 | First runtime only |
| Review nested parts after clean-up | 70.21-22 | Untitled parts called out |
| Correct cleaned statements after accept | 52.22, #23 | In-place replace; no earlier version |
| Remove irreparable citations | 52.25 | |
| Resolve uncategorized citations (or leave them) | 52.85, 70.46 | Optional repeatable pass |
| Organize enrichment: add/rename/move/delete | 52.73, #75 | Delete uncategorizes |
| Maintain Custom lessons (create/edit/delete) | 52.126, #83 | No open unit required |
| Review unit history; copy to re-teach | 52.127 | Copy does not mutate snapshot |
| Remove a topic and its belongings | 52.44 | Citations and Custom stay |
| Replace other-ruleset yes/no | 52.38 | |
| Replace system words | 52.63 | No history of wording |

**Inferred:** there is no dedicated "stale record finder." The coach must know to open Place, Finder uncategorized, and citation edit. A redesigned UI should still allow those acts even if it adds proactive surfacing (**Proposed enhancement** for the surfacing, not the acts).

**Not specified:** deduplicating two accepted citations of the same chapter/movement.

## B. Repeated build

Do the advising loop again for a topic.

| Task | Spec support |
| --- | --- |
| Open or resume a topic from Home | 70.11-15 |
| Repeat Design -> Propose/Convert -> Draft -> Edit | 70.73-92 |
| Save history before replacing the unit | 70.96; **Inferred** that later pack replaces the current unit (`put_unit`) |
| Copy a past unit into a new editable unit | 52.127 |
| Reuse Custom lessons on add-lesson | 70.92-94 |
| Re-welcome or change other-ruleset choices | 70.34 |
| Re-determine system words | 70.56 |

Gi vs no-gi namesakes are separate repeated builds.

## C. Research and discovery

Find teaching in the catalog and corpus.

| Task | Spec support |
| --- | --- |
| Browse hierarchy start -> type -> end | 70.38 |
| Dimensional search | 70.37, 52.128 |
| Search judo/wrestling cross-refs | 70.48 |
| Connect citations to named moves | 70.45 |
| Write coach-authored citations | 70.47 |
| Watch playback at showing speech start | 70.30 |
| Read briefing same-ruleset citations | 70.51 |
| Investigate disagreement sides | 70.53 |
| Read other-ruleset caveats (showing-level and welcome-level) | 70.32, 70.52 |
| Compare methods before choosing a system | 52.60 |

**Inferred:** research is not a separate mode; it is Finder + Place + Briefing + playback. The spec-70 shell does not guide "what to do next" (issue 85 deficiency).

## D. Design and planning

Choose how the topic is taught and pack it.

| Task | Spec support |
| --- | --- |
| Write system words | 70.55 |
| Set aside / restore earlier systems | 70.58 |
| Place marks on the mental map | 70.59-66 |
| Choose already-linked citations on a mark | 70.70 |
| Write unit paragraph | 70.73 |
| Evaluate Propose vs Convert | 70.74-76 |
| Organize class cuts | 70.84-89 |
| Write purpose lines | 70.90 |
| Write partner-job, scenario, condition | 52.117-119 |
| Add sparring, games, drill-only after Draft | 70.91 |
| Pin a catalog system so it packs as one block | 52.103 |

## E. Teaching (added; specs require it)

| Task | Spec support |
| --- | --- |
| Teach from Read-mode class cards | 70.79, 70.83 |
| Tick day-of checkboxes (not stored) | 70.83 |
| Qualitative success watch in a positional round | 52.120, #4 |
| Print duplex packet for the mats | 70.97-100 |

## Task-to-journey map

| Category | Journeys |
| --- | --- |
| A Maintenance | J1, J2 (post-accept), J3, J12-J14, J11 |
| B Repeated build | J4, J7-J9, J11, J16-J17 |
| C Research | J2 playback, J3, J5-J6, J12, J15 |
| D Design/planning | J6-J9 |
| E Teaching | J10 |

## Extra work the specs do **not** assign to the coach-in-app

- Running corpus-prep (`bjj_pipeline`) — upstream, issue 42.
- Filling empty instructional folders.
- Mixing a weekly calendar.
- Tallying students into the store.
- Naming an advisor vendor.
