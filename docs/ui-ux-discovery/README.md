# UI/UX discovery (coach workflows)

Index for implementation agents who redesign the coach-only advising screens. This tree extracts **what the coach must accomplish**, **how journeys run**, **how the curated store evolves**, and **what that implies for a redesigned interface**.

It does **not** reopen domain rules. Domain stays on [Coach-only advising application](https://github.com/djsciman/video_transcriber_rag/issues/52) and [`GLOSSARY.md`](../../GLOSSARY.md). Screen inventory and persistence stay on [Coach-only advising application UI](https://github.com/djsciman/video_transcriber_rag/issues/70). This tree is the child of [UI/UX Redesign: Research, Discovery, Prototyping, and Specification](https://github.com/djsciman/video_transcriber_rag/issues/85), written from [Discovery: Coach Workflows, User Journeys, Operational Tasks, and CuratedStore Evolution](https://github.com/djsciman/video_transcriber_rag/issues/86).

Live product UI remains the spec-70 stdlib HTTP shell (`py -3 -m coach_app`, bind `127.0.0.1`) until the review child records direction. One `CuratedStore` facade is the seam.

## How to read this tree

Every claim is labeled:

- **Required** — explicit in a closed or open spec, glossary entry, or locked wayfinder decision.
- **Inferred** — visible in `coach_app/` or tests, or implied by purpose, but not stated as a requirement. Validate on [Review: UI/UX Research Findings, Prototype Evaluation, and Design Decisions](https://github.com/djsciman/video_transcriber_rag/issues/89).
- **Proposed enhancement** — not supported by existing specs. Do not implement as if it were locked.

Do not invent citation version history. The specs replace cleaned statements in place. Unit history is the only saved-state list.

Prefer glossary terms. The person who uses the application is the **coach**. "User journey" in filenames is the ticket phrase; the actor is the coach. Students never use the application.

## Reports in this tree

| File | What an implementation agent takes from it |
| --- | --- |
| [requirements-inventory.md](requirements-inventory.md) | Functional requirements, inputs/outputs, data deps, business rules, automation, errors, external deps, assumptions |
| [user-roles-and-responsibilities.md](user-roles-and-responsibilities.md) | Coach-only role; advisor, instructor, student; what the coach decides vs what the advisor proposes |
| [critical-user-journeys.md](critical-user-journeys.md) | Primary / secondary / exceptional journeys with start, actions, decisions, outcomes, failures |
| [workflow-catalog.md](workflow-catalog.md) | Named workflows, state transitions, decision points |
| [coach-operational-tasks.md](coach-operational-tasks.md) | Categories A-E: maintenance, repeated build, research, design/planning, teaching |
| [curatedstore-lifecycle.md](curatedstore-lifecycle.md) | How records are admitted, classified, replaced, and cleared |
| [information-architecture-requirements.md](information-architecture-requirements.md) | What must be findable, grouped, and preserved across screens |
| [interaction-requirements.md](interaction-requirements.md) | What to see, act on, decide, and feedback; work states for a redesigned UI |
| [open-questions.md](open-questions.md) | Conflicts, gaps, ambiguities; items for the review child |
| [requirements-traceability.md](requirements-traceability.md) | Requirement id -> originating issue or glossary entry |

## Sibling reports (other branches)

Do not expect these files in this branch. They land from sibling research tickets:

- `ux-philosophies.md` — [Research: Human-Centered UX Design Philosophies and Intuitive Interaction Patterns](https://github.com/djsciman/video_transcriber_rag/issues/88)
- `tech-visual.md` — [Research: UI Technology Stack and Visual Design Approaches for a Delightful User Experience](https://github.com/djsciman/video_transcriber_rag/issues/87)

## Spec and code sources

| Source | Role |
| --- | --- |
| [`GLOSSARY.md`](../../GLOSSARY.md) | Locked language. Do not duplicate it; point at it. |
| [Issue 52](https://github.com/djsciman/video_transcriber_rag/issues/52) | Domain spec (closed). |
| [Issue 70](https://github.com/djsciman/video_transcriber_rag/issues/70) | UI + persistence spec (open until merge to `initial`). Children #71-#84 closed. |
| [Issue 1](https://github.com/djsciman/video_transcriber_rag/issues/1) | Wayfinder map; Decisions so far. Prefer #52 when #1 is historical. |
| [`docs/adr/`](../adr/) | Pipeline ADRs. They do not define coach screens. They constrain the completed volume JSON the coach curates. |
| [`coach_app/`](../../coach_app/) | Public flow: `store.py`, `app.py`, `ui_*.py`, briefing / placement / design / build / edit / library / print_packet. |
| [`tests/test_ui_*.py`](../../tests/), [`tests/test_curated_store.py`](../../tests/test_curated_store.py), [`tests/test_persist_store.py`](../../tests/test_persist_store.py) | Behavioral evidence. |

## Current shell destinations (spec-70)

Nav labels that exist today: Home, Curate, Finder, Place, Design, Sheet, Custom, History. Topic, briefing, other-ruleset welcome, settings, and print are reachable without always having a nav label. The parent map ([issue 85](https://github.com/djsciman/video_transcriber_rag/issues/85)) records that this flat nav is a deficiency, not a locked IA.

## Out of scope here

- Redesigning domain rules (citation bar, briefing shape, occupancy, glue, packing origins).
- Implementing UI or adding production dependencies.
- Prototypes (sibling agents).
- Corpus-prep pipeline (issue 42). The advising application consumes completed volume JSON the pipeline already wrote.
- Naming an advisor vendor, database engine, or frontend framework.
