# Requirements traceability

Requirement ids from [requirements-inventory.md](requirements-inventory.md) and journey/workflow ids from this tree. Sources are GitHub issues, `GLOSSARY.md` entries, ADRs, or test modules as behavioral evidence.

Issue 52 user stories are `52.<n>`. Issue 70 user stories are `70.<n>`. Children #71-#84 are UI tickets. Issue 1 is the wayfinder map (prefer #52 on conflict).

## Functional requirements

| Id | Originating source |
| --- | --- |
| FR-01 | [52](https://github.com/djsciman/video_transcriber_rag/issues/52) story 1; [70](https://github.com/djsciman/video_transcriber_rag/issues/70) story 1; glossary **Coach**, **Student** |
| FR-02 | 52.2; 70.2; [5](https://github.com/djsciman/video_transcriber_rag/issues/5) |
| FR-03 | 70.3 |
| FR-04 | 70 close comment; `coach_app/app.py` (Inferred) |
| FR-05 | 52/70 implementation decisions; `tests/test_curated_store.py` |
| FR-06 | 52/70 out of scope |
| FR-10 | 70.4; [71](https://github.com/djsciman/video_transcriber_rag/issues/71); `tests/test_persist_store.py` |
| FR-11 | 70.5; #71; [72](https://github.com/djsciman/video_transcriber_rag/issues/72) |
| FR-12 | 70.6 |
| FR-13 | 70.7; 52.72; glossary **Enrichment**; `docs/enrichment-seed/seed.json` |
| FR-14 | 70.8; 52.74 |
| FR-15 | 70.9-10; #72 |
| FR-16 | 70.103; `tests/test_ui_design.py` restart restores map/sheet |
| FR-17 | `CuratedStore.open`; README (Inferred layout) |
| FR-20 | 70.11; #72; [74](https://github.com/djsciman/video_transcriber_rag/issues/74) |
| FR-21 | 52.39; 70.12; [2](https://github.com/djsciman/video_transcriber_rag/issues/2) |
| FR-22 | 70.13 |
| FR-23 | 52.40; 70.14; glossary **Topic**; leading-space keep: `tests/test_topics.py` (Inferred) |
| FR-24 | 52.41; 70.15; [16](https://github.com/djsciman/video_transcriber_rag/issues/16) |
| FR-25 | 52.42; 70.16 |
| FR-26 | 52.43; 70.17; [17](https://github.com/djsciman/video_transcriber_rag/issues/17) |
| FR-27 | 52.44; 70.18; glossary **Topic** |
| FR-28 | 52.45; 70.19; [1](https://github.com/djsciman/video_transcriber_rag/issues/1) standing answers |
| FR-29 | 52.46; glossary **Gi**, **No-gi**, **Topic** |
| FR-30 | 52.3; glossary **Volume**, **Corpus**, **Curated store** |
| FR-31 | 70.20; [73](https://github.com/djsciman/video_transcriber_rag/issues/73) |
| FR-32 | 52.4-6; [19](https://github.com/djsciman/video_transcriber_rag/issues/19); `coach_app/cleanup.py` |
| FR-33 | 52.7-8; 70.21-22 |
| FR-34 | 52.13; 70.23; glossary **Cleaned statement** |
| FR-35 | 52.14-15; glossary **Cleaned statement** |
| FR-36 | 52.16; glossary **Playback link**, **Citation** |
| FR-37 | 52.17-19; [12](https://github.com/djsciman/video_transcriber_rag/issues/12); `coach_app/statements.py` |
| FR-38 | 52.20-21, 52.26; 70.24-26; [23](https://github.com/djsciman/video_transcriber_rag/issues/23) |
| FR-39 | 52.22-24; 70.27-28; #23; glossary **Cleaned statement** |
| FR-40 | 52.25; 70.29; glossary **Citation** |
| FR-41 | 52.27-28; 70.30-31; [13](https://github.com/djsciman/video_transcriber_rag/issues/13) |
| FR-42 | 52.29-30; [14](https://github.com/djsciman/video_transcriber_rag/issues/14) |
| FR-43 | 52.71 |
| FR-50 | 52.31; glossary **Instructional** |
| FR-51 | 52.32-33; [11](https://github.com/djsciman/video_transcriber_rag/issues/11); `LOCKED_INSTRUCTIONAL_RULESETS` |
| FR-52 | 52.34; 70.32; glossary **Other-ruleset variant**, **Caveat** |
| FR-53 | 52.35; 70.33; [15](https://github.com/djsciman/video_transcriber_rag/issues/15) |
| FR-54 | 52.38; 70.34; glossary **Caveat** |
| FR-55 | 52.36-37; 70.35 |
| FR-56 | 52.47 |
| FR-60 | 70.36; [75](https://github.com/djsciman/video_transcriber_rag/issues/75); glossary **Enrichment** |
| FR-61 | 70.37; 52.128 |
| FR-62 | 70.38; [24](https://github.com/djsciman/video_transcriber_rag/issues/24) |
| FR-63 | 52.75-76; 70.39-40; glossary **Position**, **Submission** |
| FR-64 | 52.73, 52.86-87; 70.41-43 |
| FR-65 | 70.44; glossary **Uncategorized** |
| FR-66 | 52.84-85; 70.45-46; [76](https://github.com/djsciman/video_transcriber_rag/issues/76) |
| FR-67 | 52.88; 70.47; glossary **Citation** |
| FR-68 | 52.89; 70.48 |
| FR-69 | 52.77-80; [29](https://github.com/djsciman/video_transcriber_rag/issues/29); glossary **Named move**, **Type of move** |
| FR-70 | 52.81; glossary **System** (catalog) |
| FR-71 | 52.82; glossary **Lesson** |
| FR-72 | 52.96; 70.71 |
| FR-80 | 52.49-50, 52.59; 70.49-50, 70.54; [78](https://github.com/djsciman/video_transcriber_rag/issues/78); [8](https://github.com/djsciman/video_transcriber_rag/issues/8) |
| FR-81 | 52.48 |
| FR-82 | 52.51; 70.51 |
| FR-83 | 52.52-54; glossary briefing language on issue 8 |
| FR-84 | 52.55-56; 70.52 |
| FR-85 | 52.57-58; 70.53; glossary **Disagreement** |
| FR-86 | 52.70; [15](https://github.com/djsciman/video_transcriber_rag/issues/15) |
| FR-87 | 52.62-64; 70.55-56; [22](https://github.com/djsciman/video_transcriber_rag/issues/22); glossary **System** (topic) |
| FR-88 | 52.65; 70.57; [3](https://github.com/djsciman/video_transcriber_rag/issues/3); glossary **System conflict** |
| FR-89 | 52.66-69; 70.58; glossary **Set-aside** |
| FR-90 | 52.61 |
| FR-91 | 52 implementation decisions; glossary **System** |
| FR-100 | 52.90, 52.97; 70.59, 70.72; [28](https://github.com/djsciman/video_transcriber_rag/issues/28) |
| FR-101 | 52.91; 70.60-61 |
| FR-102 | 70.62-64 |
| FR-103 | 70.65-68 |
| FR-104 | 52.93-95; 70.69-70; #29 |
| FR-105 | 52.98, 52.130; 70.73, 70.77; [30](https://github.com/djsciman/video_transcriber_rag/issues/30) |
| FR-106 | 52.99; 70.74; [81](https://github.com/djsciman/video_transcriber_rag/issues/81) |
| FR-107 | 52.100-101; 70.75-76 |
| FR-108 | 52.102-104; 70.78, 70.82; [10](https://github.com/djsciman/video_transcriber_rag/issues/10) |
| FR-109 | 52.103 |
| FR-110 | 52 packing notes; `tests/test_build.py` (other-ruleset fallback Inferred as test-locked) |
| FR-111 | 52.105; 70.79; [82](https://github.com/djsciman/video_transcriber_rag/issues/82) |
| FR-112 | 52.106-107; 70.80-81 |
| FR-113 | 52.108-113; 70.84-89; glossary **Class**, **Technique**, **Drill** |
| FR-114 | 52.114-116; 70.90; glossary **Class** |
| FR-115 | 52.122-123; 70.91-92; glossary **Sparring**, **Game** |
| FR-116 | 52.124-125; 70.93-94; glossary **Custom lesson** |
| FR-117 | 52.126; 70.95; [83](https://github.com/djsciman/video_transcriber_rag/issues/83) |
| FR-118 | 52.127; 70.96; glossary **Unit** |
| FR-119 | 52.133; 70.83 |
| FR-120 | 52.120-121; 70.101; [4](https://github.com/djsciman/video_transcriber_rag/issues/4) |
| FR-121 | 52.131; 70.97-100; [84](https://github.com/djsciman/video_transcriber_rag/issues/84) |
| FR-122 | 70.102 |
| FR-123 | 70.104-105 |

## Journeys

| Id | Originating source |
| --- | --- |
| J1 | 70.4-10; #71; #72 |
| J2 | 52.3-30; 70.20-32; #73 |
| J3 | 52.84-88; 70.44-47; #76 |
| J4 | 52.39-46; 70.11-19; #74 |
| J5 | 52.34-38; 70.32-35; #77 |
| J6 | 52.49-70; 70.49-58; #78; #79 |
| J7 | 52.90-97; 70.59-72; #80 |
| J8 | 52.98-104; 70.73-78; #81 |
| J9 | 52.108-125; 70.84-94; #82 |
| J10 | 52.120-133; 70.79-83, 70.97-101; #84 |
| J11 | 52.126-127; 70.95-96; #83 |
| J12 | #75; 52.72-89 |
| J13 | #23 |
| J14 | 52.25 |
| J15 | #13; 70.30-31 |
| J16 | 70.103 |
| J17 | 70 Design-to-Edit; `put_unit` uniqueness (Inferred replace) |
| J18 | 70.76 |
| J19 | 52.8, 52.134; `docs/volumes-awaiting-parse.md` |
| J20 | 52.28 |
| J21 | 70.88 |
| J22 | 52.37; `tests/test_build.py` |
| J23 | 52.42 |
| J24 | 52.66-68 |
| I1-I4 | Inferred; validate on #89 |
| Proposed journeys | [open-questions.md](open-questions.md) |

## Operational categories

| Category | Originating source |
| --- | --- |
| A Maintenance | [86](https://github.com/djsciman/video_transcriber_rag/issues/86) prompt; acts from 52/70 |
| B Repeated build | #86 prompt; 70.11-96 |
| C Research/discovery | #86 prompt; finder/briefing/playback |
| D Design/planning | #86 prompt; Design/Build/Edit |
| E Teaching | Added from 52.120-133; 70.79-101; #4; #84 |

## Store lifecycle

| Topic | Originating source |
| --- | --- |
| Record list | 52 implementation decisions; glossary; `coach_app/store.py`; `tests/test_curated_store.py` |
| No cleanup/disagreement/topic citation list | 52.70-71; #15 |
| In-place statement replace | glossary **Cleaned statement**; #23 |
| Unit history vs no citation history | glossary **Unit**; 52.127 |
| Remove topic clears belongings | glossary **Topic**; #17; `store.remove_topic` |
| Seed once | 52.72-74; #71 |
| Pipeline ADRs | [ADR 0001](../adr/0001-sample-a-volume-once-for-chapter-starts.md), [ADR 0002](../adr/0002-skip-pipeline-stage-when-artifact-exists.md) — corpus only |

## Glossary entries used as requirements

Coach, Instructor, Student, Instructional, Volume, Chapter, Citation, Cleaned statement, Playback link, Corpus, Application, Curated store, Advisor, Gi, No-gi, Topic, System, System conflict, Set-aside, Disagreement, Other-ruleset variant, Caveat, Unit, Class, Lesson, Technique, Drill, Partner job, Sparring, Scenario, Game, Custom lesson, Enrichment, Position, Type of move, Named move, Submission, Uncategorized, Resistance.

Do not duplicate definitions; edit `GLOSSARY.md` only through domain-modeling.

## Behavioral evidence (tests)

| Area | Tests |
| --- | --- |
| Facade records | `tests/test_curated_store.py` |
| Persist / seed-once | `tests/test_persist_store.py` |
| Curate UI | `tests/test_curate.py` |
| Topics UI | `tests/test_ui_topics.py`; `tests/test_topics.py` |
| Other-ruleset UI | `tests/test_ui_other_ruleset.py` |
| Placement UI | `tests/test_ui_placement.py`; `tests/test_placement.py` |
| Briefing/system UI | `tests/test_ui_briefing.py` |
| Design/Propose/Convert UI | `tests/test_ui_design.py`; `tests/test_build.py` |
| Sheet UI | `tests/test_ui_sheet.py`; `tests/test_edit.py` |
| Custom/history UI | `tests/test_ui_library.py`; `tests/test_library.py` |
| Print UI | `tests/test_ui_print.py`; `tests/test_print_packet.py` |

## Parent map

This discovery does **not** patch [issue 85](https://github.com/djsciman/video_transcriber_rag/issues/85). Gist on the parent is the parent agent's job after children close.
