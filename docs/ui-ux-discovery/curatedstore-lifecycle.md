# Curated store lifecycle

What the store holds, how it changes, and what a redesigned UI must not invent. Records list from issue 52 implementation decisions and `coach_app/store.py`.

Do **not** treat this as a database schema spec. The UI spec forbids naming the engine or file layout. Persistence exists; pickle-on-disk is **Inferred** implementation.

## Records the store holds (**Required**)

| Record | Identity / key facts | Notes |
| --- | --- | --- |
| Instructional | instructor, name, gi or no-gi | Written on accept |
| Volume | instructional, video file name | Written on accept |
| Accepted citation | volume, chapter, movement, cleaned statement, showings (speech start, playback handle), optional other-ruleset caveat on a showing, optional named-move link | Coach-authored: movement + bullets + optional named-move; no playback |
| Topic | kept name, gi or no-gi, system words empty until chosen | |
| Other-ruleset yes/no | topic + instructional; caveat on a yes | Replace in place |
| Set-aside | this topic + earlier topic | Several per topic |
| Enrichment nodes | position, type of move, submission, named move, catalog system | Live copy after seed |
| Unit | topic pair, paragraph | One current unit per topic |
| Class | purpose, unit | |
| Lesson | kind, target, citations, partner job / scenario / condition | Exactly one named move or catalog system |
| Custom lesson | snapshot of a lesson | Not a topic belonging |
| Unit history | snapshot of unit + packed classes | Past entry immutable on copy |

**Also persisted in the product store (Required by 70.103, Inferred as fields):** video root, transcript folder, seed-imported flag, design sessions, sheets, current topic.

## Records the store must **not** hold (**Required**)

- Clean-up part list (raw-volume step)
- Disagreement (citations read together)
- Citation list on the topic
- Read-mode checkboxes
- Success-watch clipboard
- Earlier versions of a cleaned statement
- Frozen copy of an earlier system's words on a set-aside

## Lifecycle workflows

### Ingestion — **Required**

```
completed volume JSON
  -> cleanup_volume (raw parts; not stored)
  -> propose_statements (drafts; not stored)
  -> coach correct
  -> accept -> instructional + volume + citation
     or dismiss -> nothing
```

Citation bar applied at propose time (`statements.py`): titled part, duration >= 60s, not intro/outro/named roll; multi-idea titles split.

### Validation — **Required** (coach) / **not** a stored status

The coach validates wording before and after accept. There is no "validated" flag. Post-accept save **is** the validation. **Proposed enhancement:** a needs-validation badge on newly admitted citations.

### Classification — **Required**

Advisor proposes named-move ids. Coach accept/correct/skip. Uncategorized is a valid long-lived state. Linked citations only are offered on lessons and Design marks.

### Enrichment catalog edits — **Required**

Seed import once. Coach add/rename/move/delete. Rename/move keep citation links (stable node id). Delete drops the node (and dependent named moves if a path node is deleted) and clears `named_move_id` on those citations.

### Relationship discovery — **Required** where specified

| Relationship | How it is made | History |
| --- | --- | --- |
| Citation -> named move | Placement pass or later link | Current id only |
| Showing -> other-ruleset caveat | Mark on showing | Current showing tuple |
| Topic -> instructional welcome | Yes/no | Replace in place |
| Topic -> system words | Coach entry | Replace in place |
| Topic -> earlier topic set-aside | Set aside / end | Pair exists or not |
| Lesson -> named move or catalog system | Target id | Current |
| Lesson -> citations used | Coach / packing | Current tuple |
| Catalog system -> member named moves | Finder/catalog write | Current members |

### Provenance — **Required**

Corpus citation keeps instructor, instructional, volume, chapter, playback handles. Word edits must not change those fields. Coach-authored citations have none of those.

Playback resolves at **open time** from video root + transcript folder + `video_file` + speech start. Missing file still admits.

### Versioning — **Required** (replace in place)

| Artifact | Versioning |
| --- | --- |
| Cleaned statement | None. Save replaces. |
| System words | None. Later choice replaces. |
| Other-ruleset yes/no | None. Later choice replaces. |
| Unit packing | Current unit replaced by later `put_unit` / Propose / Convert / history copy |
| Unit history | Explicit snapshots. Copy does not change the snapshot. |
| Enrichment seed | Not re-applied. Live tree only. |

**Proposed enhancement:** citation undo / statement history. Not in the specs. Do not implement as if locked.

### Deduplication — **not specified**

A second accept of the same chapter can create another citation. **Proposed enhancement** if the coach wants merge. Label it so.

### Conflict resolution — **Required** as briefing, not as stored conflict rows

- Same-ruleset disagreement: advisor flags sides; each side carries a citation; coach determines the system. Other side may become partner-job text.
- System conflict: earlier same-ruleset system shown beside an incompatible side; coach set-aside.
- Cross-ruleset: never pick a winner; caveat lists only.

### Review and approval — **Required**

| Gate | Approver |
| --- | --- |
| Statement -> store | Coach accept |
| Placement link | Coach accept/correct (skip = no link) |
| Other-ruleset on topic | Coach yes/no |
| System | Coach words |
| Draft packing | Advisor proposes; coach reads Draft then Edit |
| Catalog node delete | Coach |

### Change history — **Required** split

- Unit history exists.
- Citation edit does not keep prior text.
- Remove topic clears belongings listed below.

### Information lifecycle

| Object | Birth | Death |
| --- | --- | --- |
| Raw volume | Transcribed (corpus) | Never in store |
| Cleaned proposal | propose_statements | Vanish on dismiss; or become citation |
| Citation | accept or coach-authored write | `remove` |
| Topic | open | remove (pair reusable) |
| Unit | open topic / pack | drop on topic remove or replaced by later unit of same pair |
| Custom | place or create | delete_custom |
| History entry | save_history | dropped if that topic is removed (`store.remove_topic`) |
| Seed | first runtime | flag prevents re-import |

### Remove topic — what clears (**Required** intent; implementation evidence)

Clears: topic, other-ruleset choices for the pair, set-asides where this pair is this or earlier topic, units/classes/lessons of the pair, unit histories of the pair.

Does not clear: instructionals, volumes, citations, enrichment, Custom.

**Gap:** `remove_topic` does not pop `design_sessions` or `sheets` for that pair. Spec says "clears what belonged." Treat leftover map/sheet as a defect or as **Inferred** leak; redesign should clear them with the topic.

### Newly admitted vs changed

- **Newly admitted:** accept writes a new citation id; typically uncategorized until placement.
- **Changed:** `correct` same id; `put_other_ruleset_choice` same key; `choose_system` same topic key; `put_citation` with new `named_move_id`.

The current shell does not badge these. **Required** records; **Proposed enhancement** to surface them.

## External artifacts (not store)

- Video files
- Transcript JSON
- Enrichment seed file (copied in, not linked)
- Browser print output
- Briefing memo object (computed)

## Pipeline ADRs

[ADR 0001](../adr/0001-sample-a-volume-once-for-chapter-starts.md) and [ADR 0002](../adr/0002-skip-pipeline-stage-when-artifact-exists.md) affect chapter quality and when JSON exists. They do not add store records.
