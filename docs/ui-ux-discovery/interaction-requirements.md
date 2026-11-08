# Interaction requirements

Per workflow: what to see, which actions, preserved context, decisions, feedback, states, proactive surfacing, automated vs coach-controlled.

Work-state labels (awaiting / in progress / needs decision / done / needs validation / newly admitted / changed) are **Required** as underlying conditions. Surfacing them as chrome is **Proposed enhancement** unless a spec already requires visible copy (example: empty Convert reason is **Required**).

## Shared shell

| | |
| --- | --- |
| See | Coach-only application. Current destination. Open topic identity when one is in play. |
| Actions | Move among destinations without losing writes. |
| Context | `CuratedStore` is the only source of truth. |
| Feedback | Local, immediate after POST. |
| Automated | Persistence on write. |
| Coach-controlled | Every accept, wording, packing edit. |
| Status | Required 70.1-3, 70.102 |

**Inferred:** spec-70 is a flat link nav. Redesign should make the next advising step obvious (issue 85) without hiding destinations.

## First runtime and settings (J1 / W1)

| | |
| --- | --- |
| See | Empty topic list is valid. Video root and transcript folder fields. |
| Actions | Save paths. Open the app again. |
| Decisions | Folder locations. |
| Feedback | Values survive restart. Catalog populated after first seed import without a coach import button. |
| States | First runtime vs later runtime (seed already imported). |
| Proactive | **Proposed:** warn if paths empty before playback/curate. |
| Automated | Seed import once. |
| Coach-controlled | Paths. |

## Curate (J2 / W2)

| | |
| --- | --- |
| See | Nested parts; untitled part called out; proposals (move name, bullets) **before** store write; accepted citations for this volume; playback control or timestamp + volume name. |
| Actions | Pick JSON; correct proposal; accept; dismiss; correct after accept; remove; playback; mark other-ruleset aside. |
| Context | video_file, instructor, chapters. |
| Decisions | Accept vs dismiss; wording; aside mark. |
| Feedback | Dismiss: still nothing in store. Accept: citation appears. Save after accept: old words gone. Missing file: still show lookup fields. |
| States | Awaiting (uncurated JSON — **Proposed** inbox); needs decision (proposal); newly admitted (accepted); needs validation (coach may still correct); done (accepted and coach has moved on). |
| Automated | Cleanup, propose statements. |
| Coach-controlled | Accept, wording, remove. |

## Placement (J3 / W3)

| | |
| --- | --- |
| See | One scrollable list of uncategorized citations with proposed named-move; provenance; bullets; named-move picker; coach-author form. Empty: "No uncategorized citations." |
| Actions | Accept, correct, skip; author a citation. Repeat later. |
| Context | Live named moves including aliases/cross-refs. |
| Decisions | Link or leave uncategorized. |
| Feedback | Skip remains in the pass next time. Accept removes from uncategorized. |
| States | Awaiting / needs decision (proposal); done (linked); newly admitted still uncategorized. |
| Proactive | **Proposed:** badge on Home when uncategorized > 0. Pass itself is Required. |
| Automated | Proposed named-move id. |
| Coach-controlled | Accept/correct/skip. |

## Finder (J12 / W4)

| | |
| --- | --- |
| See | Hierarchy, search, uncategorized bucket, node kinds, occupancy on named moves, submissions as ends only. |
| Actions | Browse, search, add, rename, move, delete. |
| Context | Live catalog, not the seed file. |
| Decisions | Catalog identity. |
| Feedback | Rename keeps links. Delete uncategorizes. Later runtime keeps edits. |
| States | Done catalog vs uncategorized awaiting classification. |
| Automated | Occupancy inference. |
| Coach-controlled | All tree edits. Design must not do this. |

## Topic open/remove (J4 / W5)

| | |
| --- | --- |
| See | Home list (name + ruleset). Open topic shows name and ruleset **fixed** (no rename field). Remove control. |
| Actions | Submit name + gi/no-gi; resume; remove. |
| Decisions | Spelling; ruleset; destroy thread. |
| Feedback | Blank submit no-op. Trailing spaces strip. Same pair reopens. Remove then reopen has empty system. |
| States | No topics; open; removed. |
| Coach-controlled | All. |

## Other-ruleset welcome (J5 / W6)

| | |
| --- | --- |
| See | Each matching other-ruleset instructional after open. Current yes/no. Caveat on yes. Empty copy when none. |
| Actions | Yes; No; later replace. Showing-level mark lives on Curate. |
| Decisions | Welcome or not. |
| Feedback | Choice replaces. Briefing updates. Lessons do not auto-gain those citations. |
| States | Needs decision (offered); done (yes or no). Unanswered = awaiting **Inferred**. |
| Automated | Offer list from cited other-ruleset instructionals. |
| Coach-controlled | Yes/no; placing a citation onto a lesson. |

## Briefing and system (J6 / W7)

| | |
| --- | --- |
| See | Topic name + ruleset. Same-ruleset citations with bullets and playback. Other-ruleset why-differ + may-transfer / depends-on. Disagreement sides with citations. System field (empty until chosen). System conflicts with earlier topic name and **live** words. Set-aside controls. |
| Actions | Watch; enter/replace system; set aside; end set-aside. |
| Context | Open topic. No class cards. |
| Decisions | System wording; which earlier systems stay off. |
| Feedback | Replace in place. Set-aside hides the note. |
| States | Needs decision (empty system, visible conflict); done (current words). |
| Automated | Citation select; caveat lists; conflict detect (stand-in). |
| Coach-controlled | System and set-asides. |

## Design (J7 / W8)

| | |
| --- | --- |
| See | Full-width force graph. Prompt/paragraph. Walk options filtered by family. Dashed draft mark. Breadcrumb. Labels with leaders. Already-linked citations on edit. |
| Actions | Add walk; empty-canvas add; double-click hop; left-click edit; right-click delete; pan/zoom/recenter/reset-marks; choose citations on a mark; notes. |
| Context | Open topic; live catalog. |
| Decisions | Which hops; which linked citations this unit uses. |
| Feedback | Named move replaces type mark. Uncategorized absent. Add does not wipe the map. |
| States | In progress (walk); packable vs unpackable. |
| Automated | Occupancy inference; option filters. |
| Coach-controlled | Marks. Catalog organize stays on Finder. |

## Propose / Convert (J8 / W9)

| | |
| --- | --- |
| See | Layout B: prompt, canvas, Draft. Draft dashed no-edit cards. Technique full bullets; glued drill partner job only. No Playback column. Empty Convert reason. |
| Actions | Propose; Convert. |
| Decisions | Which packing path. |
| Feedback | Propose fills both surfaces. Convert on empty: visible reason, no classes. |
| States | Needs decision (empty Convert); done (Draft present). |
| Automated | Packing, partner-job stubs, glued blocks, citation fallback (same-ruleset linked only). |
| Coach-controlled | Whether to pack; all later Edit. |

## Edit / Read (J9-J10 / W10)

| | |
| --- | --- |
| See | Same colored class cards. Mode. Purpose lines. Add-lesson sources: Custom, search, hierarchy, map named moves. Glue as one block. |
| Actions | Mode switch; add/remove/drag; write purpose/partner-job/scenario/condition; pull sources; Read checkboxes. |
| Decisions | Cuts; mix; text. |
| Feedback | Empty-class drag refused. Add technique inserts drill. Remove technique removes drill. Place saves Custom. Checkboxes do not persist. |
| States | Draft done/no-edit; Edit in progress; Read teaching. |
| Automated | Glue; Custom save on place; Custom copy on pull. |
| Coach-controlled | Packing and text. Success watch is by eye, not stored. |

## Custom and history (J11 / W11)

| | |
| --- | --- |
| See | Custom list via search/hierarchy. History list of saved states. |
| Actions | Create/edit/delete Custom. Save history. Copy to new editable unit. |
| Context | Custom works with no open unit. Copy is per topic (one unit). |
| Decisions | Which snapshot to re-teach. |
| Feedback | Past history entry unchanged. Current unit replaced. |
| States | Done snapshots vs current in-progress unit. |
| Coach-controlled | Save and copy. **Inferred:** save is explicit, not automatic on every edit. |

## Print (J10 / W12)

| | |
| --- | --- |
| See | Landscape canvas page then portrait class cards; 0.5 in; class whole. No paragraph/success watch on cards. |
| Actions | Print via browser. |
| Feedback | Page records from `packet()`. |
| Automated | Page split on Class. |
| Coach-controlled | When to print. |

## Automation vs coach control (summary)

Always automated: cleanup nesting, seed-once, persist on write, occupancy inference, glue, Custom save-on-place, withholding uncategorized, same-ruleset auto-select for briefing.

Always coach: accept/dismiss, wording, remove, welcome, system, set-asides, catalog CRUD, placement skip, map marks, Edit packing, history copy.

Propose/Convert: automated packing, coach-initiated.

## Reducing repetitive work (**Inferred** opportunities; do not change domain rules)

- After accept, land in (or badge) the placement pass.
- After open topic, land on unanswered other-ruleset offers if any.
- After briefing, keep system on the same continuation (already #79).
- After Convert refuse, keep the coach on the map with the reason visible (already Required).
- Do not ask the coach to re-accept citations after restart (already Required).
- Do not re-import seed (already Required).

**Proposed enhancement:** batch accept on placement when proposals are clearly right. Specs describe per-citation accept/correct/skip, not a single "accept all."
