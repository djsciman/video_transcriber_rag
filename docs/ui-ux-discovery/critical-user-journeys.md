# Critical journeys

The actor is the **coach**. Primary / secondary / exceptional as used here:

- **Primary** — the coach cannot teach a topic through to performance under resistance without this path.
- **Secondary** — specified, repeated, but not on the first-teach critical path.
- **Exceptional** — specified recovery, refuse, or edge.

Each journey is **Required** unless marked **Inferred** or **Proposed enhancement**.

---

## J1. First runtime: persist store, import seed, set paths

- **Kind:** Primary
- **Objective:** Have a live catalog and playback paths so later sessions load without re-accepting.
- **Start:** No persisted store, or empty location.
- **Context:** Consensus seed at `docs/enrichment-seed/seed.json`. Corpus JSON and videos live outside the repo.
- **Actions:** Open the application (`py -3 -m coach_app`). First `CuratedStore.open` imports the seed. Coach sets video root and transcript folder on Home and saves.
- **Decisions:** Where the video root and transcript folder are.
- **Application responses:** Live catalog present. Settings persist. Home may show "No topics yet."
- **Outcomes:** Later runtime loads catalog edits, settings, and records without a second seed import.
- **Alts:** Later runtime with seed already imported skips import (**Required** FR-14).
- **Failures:** Missing seed file would fail first open (**Inferred** from `_import_committed_seed`). Wrong folders: playback later shows missing file but citations still admit.
- **Completion:** Seed imported flag set; video root and transcript folder stored.

Evidence: issues 70.4-10, #71, #72; `tests/test_persist_store.py`.

---

## J2. Curate a completed volume into accepted citations

- **Kind:** Primary
- **Objective:** Admit catalog teaching the advisor may use.
- **Start:** Completed volume JSON exists. Store may already have other citations.
- **Context:** Citation bar. Clean-up does not write the store.
- **Actions:** Pick JSON on Curate. See nested parts (or untitled part called out). Review proposed cleaned statements. Correct move name and bullets. Accept or dismiss each. Optionally playback a showing. Optionally mark an other-ruleset aside on a showing. After accept, correct or remove.
- **Decisions:** Are these the words I will teach from? Dismiss vs accept. Other-ruleset aside or not.
- **Application responses:** Proposals appear before writes. Accept writes instructional, volume, citation. Dismiss writes nothing. Edit after accept replaces in place. Missing video still shows timestamp and volume name.
- **Outcomes:** New corpus citations in the store, still uncategorized until placement.
- **Alts:** Untitled part: no citeable proposals until movements are marked (**Required**). Chapter < 1 min / intro / outro / named roll: no proposal.
- **Failures:** Bad JSON path: no parts (**Inferred**). Playback file missing: citation still admitted.
- **Completion:** Each wanted movement has an accepted citation; rejected drafts stored nothing.

Evidence: issues 52.3-30, 70.20-32, #73; `tests/test_curate.py`.

---

## J3. Review and correct placement onto named moves

- **Kind:** Primary (new citations cannot appear on lessons or Design until linked)
- **Objective:** Link citations to named moves, or leave them uncategorized on purpose.
- **Start:** One or more citations with empty `named_move_id`. Live catalog present.
- **Context:** Finder is where catalog organize lives. Placement is a review pass, not tree editing.
- **Actions:** Open Place. Scroll proposals. Accept proposed named-move, correct to another named move, or skip. Optionally write a coach-authored citation on a named move. Repeat later on remaining uncategorized.
- **Decisions:** Accept / correct / skip per citation. Whether to author own knowledge.
- **Application responses:** One scrollable pass. Skip leaves uncategorized. Uncategorized stay off lessons and Design marks. Uncategorized remain visible in the finder bucket.
- **Outcomes:** Linked citations offered on Design marks and lessons.
- **Alts:** Leave uncategorized indefinitely (**Required** optional pass).
- **Failures:** Accept with no named-move id leaves uncategorized (`placement.py` accept-without-id). Unknown action errors.
- **Completion:** Coach has reviewed the pass; remaining uncategorized are a deliberate bucket, not a lost pile.

Evidence: issues 52.84-88, 70.44-47, #76; `tests/test_ui_placement.py`.

---

## J4. Open, resume, and remove a topic

- **Kind:** Primary
- **Objective:** Name the teaching thread; resume it; or clear it.
- **Start:** Home. Catalog and citations may already exist.
- **Context:** Topic identity = ruleset + kept name. One topic, one unit.
- **Actions:** Submit name + gi or no-gi. Home lists the topic. Open the topic page (name and ruleset fixed). Resume later by submitting the same pair or clicking the home list. Remove clears belonging records; same pair can open again empty of system/unit.
- **Decisions:** Exact spelling. Gi vs no-gi. Whether to destroy the teaching thread.
- **Application responses:** Blank submit opens nothing. Trailing spaces strip. Hyphen vs space are different topics. Gi and no-gi namesakes differ. Opening creates/reuses the unit.
- **Outcomes:** An open topic the coach can brief, welcome, design, pack.
- **Alts:** Resume restores system words, map, sheet across runtimes (**Required** 70.103).
- **Failures:** Unknown pair GET shows "That topic is not open." (**Inferred**).
- **Completion:** Desired pair is listed on Home, or removed and gone.

Evidence: issues 52.39-46, 70.11-19, #74; `tests/test_ui_topics.py`.

Remove **clears** (implementation evidence, `store.remove_topic`): topic record, other-ruleset choices for that pair, set-asides involving that pair, units/classes/lessons of that pair, unit histories of that pair. **Does not clear** citations, Custom lessons, enrichment. Design sessions and sheets for that pair are **not** explicitly dropped in `remove_topic` (**Gap** — see [open-questions.md](open-questions.md)).

---

## J5. Welcome other-ruleset instructionals

- **Kind:** Primary when the corpus has the other ruleset; otherwise idle empty state
- **Objective:** Decide whether other-ruleset instructionals inform this topic's analysis, without silently packing them.
- **Start:** Topic open. At least one citation exists from an instructional of the other ruleset.
- **Context:** Offer happens after open. Each instructional is its own yes/no.
- **Actions:** On the topic page, for each offered instructional, choose Yes or No. Later replace that choice. Optionally mark a showing as an other-ruleset aside during curation.
- **Decisions:** Yes (caveat on the yes) vs No.
- **Application responses:** Yes shows caveat. Briefing includes welcomed material with why-paths-differ. Convert/Propose fallback does not pack those citations. Coach may still place one onto a lesson in Edit.
- **Outcomes:** Current yes/no per instructional on this topic.
- **Alts:** No matching instructionals -> empty panel.
- **Failures:** Changing yes to no replaces; briefing then omits that series (`test_ui_briefing.py` unwelcomed stays off).
- **Completion:** Every offered instructional has a current choice, or the coach has deferred (**Inferred** that deferral is allowed: no forced choice in spec).

Evidence: issues 52.34-38, 70.32-35, #77; `tests/test_ui_other_ruleset.py`.

---

## J6. Read the briefing and determine a system (including set-asides)

- **Kind:** Primary
- **Objective:** See citations and disagreement, then write how this topic is taught.
- **Start:** Topic open. Same-ruleset citations exist (otherwise memo is thin).
- **Context:** Analysis before packing. No class split.
- **Actions:** Open briefing. Watch playback. Compare same-ruleset methods. Read other-ruleset caveat lists if welcomed. Read disagreement sides with citations. Enter system words. If an earlier same-ruleset system conflicts with a side, set it aside or leave it visible. Put a set-aside back later.
- **Decisions:** System wording. Which earlier systems stay off this topic.
- **Application responses:** Memo names topic. Disagreement only for same-ruleset conflict. System empty until chosen; later save replaces words. Set-aside hides the note; advisor reads live words on the earlier topic.
- **Outcomes:** Topic.system is the current wording. Set-aside pairs recorded.
- **Alts:** Instructor method as the whole system when it fits (**Required** 52.60). No disagreement if advisor finds none (stand-in default returns no sides — **Inferred** product risk).
- **Failures:** Briefing without citations still names the topic (**Inferred**).
- **Completion:** Coach has current system words, or has deliberately left them empty (empty is a valid store state **Required**).

Evidence: issues 52.49-70, 70.49-58, #78, #79; `tests/test_ui_briefing.py`.

---

## J7. Design a unit on the mental map

- **Kind:** Primary
- **Objective:** Place an unordered map of occupancies, named moves, and systems for this topic.
- **Start:** Topic open. Live catalog. Linked citations available for marks.
- **Context:** Design does not pack. Catalog organize is on Finder.
- **Actions:** Open Design (layout B prompt above). Write or skip unit paragraph. Add walk family -> position -> occupancy -> type -> end -> named move. Double-click to continue a hop. Left-click to choose already-linked citations and notes. Right-click to delete. Pan/zoom/recenter/reset-marks. Optionally add a catalog system mark.
- **Decisions:** Which hops belong on this unit. Which linked citations this unit uses. Occupancy is inferred, not a second position.
- **Application responses:** Family filters occupancy/type (no escape from closed-guard bottom). Named move replaces type mark. Uncategorized citations absent from the mark. Empty-canvas add does not wipe existing marks.
- **Outcomes:** Persisted design session for the topic pair.
- **Alts:** Propose later fills the canvas from the paragraph (J8).
- **Failures:** Add walk with no matching named move cannot finish that hop (**Inferred** from walk options).
- **Completion:** Map has named-move and/or system marks the coach intends to pack, or the coach is still exploring.

Evidence: issues 52.90-97, 70.59-72, #80; `tests/test_ui_design.py`.

---

## J8. Pack the first Draft (Propose or Convert)

- **Kind:** Primary
- **Objective:** Turn the map into glued technique+drill classes the coach can read, then edit.
- **Start:** Design screen. Packable map and/or unit paragraph.
- **Context:** Draft is no-edit dashed cards. Layout B.
- **Actions:**
  - **Propose:** paragraph -> advisor fills canvas and Draft together.
  - **Convert:** pack the hand-built canvas.
- **Decisions:** Propose vs Convert. Whether the paragraph is enough.
- **Application responses:** First Draft glued technique+drill, class cuts, partner-job stubs, no Playback column. Pinned system is one glued block unless a member is isolated. Empty Convert shows a visible reason and writes no classes.
- **Outcomes:** Unit, classes, lessons in the store; sheet available; lessons also saved under Custom on later Edit place (first pack writes lessons; Custom save-on-place is Edit **Required**).
- **Alts:** Convert without paragraph. Propose may use a stand-in that only fills the Tight waist sample (**Inferred** fixture in `BuildAdvisor`).
- **Failures:** Empty map Convert refused. Other-ruleset citations not packed by fallback.
- **Completion:** Draft cards visible; coach can switch to Edit/Read.

Evidence: issues 52.98-104, 70.73-78, #81; `tests/test_build.py`, `tests/test_ui_design.py`.

---

## J9. Edit the sheet; pull Custom / finder / map lessons

- **Kind:** Primary after first Draft (or after history copy)
- **Objective:** Make packing the coach's: order, cuts, non-technique work, purpose lines, resistance text.
- **Start:** A sheet exists (from Draft or history copy). Mode Edit.
- **Context:** Glue rule. No empty classes. No class cap.
- **Actions:** Drag blocks (technique+drill together) across cuts. Add technique (inserts drill). Remove technique (removes drill). Add sparring/game/drill-only. Pull from Custom, search, hierarchy, or map named moves. Write purpose, partner job, scenario, condition. Place other-ruleset citation onto a lesson only here.
- **Decisions:** Class cuts. Lesson mix. Which citations of the target to use.
- **Application responses:** Empty-class drag refused. Place saves Custom with no extra Save. Pull copies fields; editing the copy does not change the saved Custom.
- **Outcomes:** Editable unit the coach will teach.
- **Alts:** Hand-build after Convert. Start-from-empty is allowed in domain (#9) but first packing still wants named moves to Convert (**Required** empty Convert refuse). **Inferred:** starting Edit with no Draft is underspecified in the UI spec.
- **Failures:** Glue violation prevented. Lesson connection validation.
- **Completion:** Every class has >= 1 lesson; purpose/partner-job/scenario/condition are as the coach wants (purpose may stay empty).

Evidence: issues 52.108-125, 70.84-94, #82; `tests/test_ui_sheet.py`.

---

## J10. Teach from Read mode; print the duplex packet

- **Kind:** Primary on the mat; print is the takeaway
- **Objective:** Teach the class from cards; optionally carry paper.
- **Start:** Sheet exists. Mode Read. Optionally print.
- **Context:** Same class-card layout as Draft/Edit. Checkboxes not stored. Success watch qualitative, not stored. Print hides paragraph and success watch.
- **Actions:** Switch to Read. Tick day-of checkboxes (flourish). Read technique steps and drill partner jobs. Watch students in a positional round (none/some/most/all). Print: landscape canvas, then portrait class cards, 0.5 in, class cards whole.
- **Decisions:** Whether the topic is landing under resistance (not written to the store).
- **Application responses:** Checkboxes do not persist. Packet page records from `print_packet.packet`. Browser print.
- **Outcomes:** Coaching happens. Store unchanged by ticks.
- **Alts:** Teach from screen only; print optional but specified.
- **Failures:** No named PDF library. Missing Design session would omit marks on canvas page (**Inferred**).
- **Completion:** Coach has taught or has a packet in hand.

Evidence: issues 52.120-121, 52.131-133, 70.83, 70.97-101, #84; `tests/test_ui_print.py`.

---

## J11. Maintain Custom and copy from unit history

- **Kind:** Secondary (re-teach / reuse). Primary for a later cycle of the same topic.
- **Objective:** Keep reusable lessons; re-teach from a past unit without mutating the snapshot.
- **Start:** Custom library and/or saved history entries. No open unit required for Custom CRUD.
- **Context:** Hierarchy shows Custom through named move or system. Copy replaces the topic's current unit (one topic, one unit) while history stays.
- **Actions:** Create/edit/delete Custom. Search and hierarchy under Custom. Save a unit to history. Copy from history into a new editable unit.
- **Decisions:** Which snapshot to re-teach. Whether to delete a Custom lesson.
- **Application responses:** Copy leaves the past entry unchanged. Past unit fields intact.
- **Outcomes:** New editable sheet; history list unchanged.
- **Alts:** Place-on-unit already grew Custom during Edit.
- **Failures:** Copy of missing history id is unspecified (**Gap**).
- **Completion:** Desired Custom exists or is gone; re-teach sheet is in Edit.

Evidence: issues 52.126-127, 70.95-96, #83; `tests/test_ui_library.py`.

---

## Secondary journeys (specified, not first-teach)

| Id | Journey | Notes |
| --- | --- | --- |
| J12 | Organize the enrichment finder | Add/rename/move/delete nodes; dimensional search; uncategorized bucket. **Required** #75. |
| J13 | Correct a cleaned statement after accept | Provenance frozen; words replace in place. **Required** #23. |
| J14 | Remove a citation | Statement that cannot be repaired leaves the store. **Required**. |
| J15 | Playback a showing | Open at speech start; missing file still lists lookup fields. **Required**. |
| J16 | Resume after browser close | Same store, settings, current topic, map, sheet. **Required** 70.103. |
| J17 | Repeat Design-to-Draft-to-Edit on the same topic | Later Propose/Convert overwrites the topic's unit (**Inferred** from `put_unit` uniqueness). History must be saved first if the coach wants the old packing. |

## Exceptional journeys

| Id | Journey | Notes |
| --- | --- | --- |
| J18 | Convert on an empty canvas | Visible refuse; no classes written. **Required**. |
| J19 | Untitled / awaiting-parse volume | Called out; not cited until chapters/movements exist. **Required**. Empty folders stay out (52.134). |
| J20 | Missing video file | Citation admitted. **Required**. |
| J21 | Drag that empties a class | Refused. **Required**. |
| J22 | Other-ruleset citation must not silent-pack | **Required**; tested in `test_build.py`. |
| J23 | Spelling variant opens a second topic | **Required**. Coach must remove if accidental. |
| J24 | Set-aside then end | Note hides and returns; live words. **Required**. |

## Inferred journeys (validate on review)

- **I1.** Home inbox of work awaiting attention (uncategorized count, unanswered welcomes, empty system, unpackable map). Specs have the states; no screen aggregates them.
- **I2.** Watch the transcript folder for new completed JSON. Specs only support explicit pick.
- **I3.** Hand-build a unit with no Propose/Convert, starting from an empty sheet. Domain #9 allows starting empty; UI Convert refuses empty maps.
- **I4.** Re-curate the same volume. Specs do not define dedup; a second accept would add another citation (**Inferred** from `accept` always `put_citation`).

## Proposed enhancement journeys

- Unified maintenance inbox.
- Citation text history / undo beyond in-place replace.
- Multi-machine sync.
- Student-facing anything.

Do not treat proposed items as locked.
