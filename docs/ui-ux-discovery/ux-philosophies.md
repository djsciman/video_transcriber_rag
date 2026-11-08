# Human-centered UX philosophies for the coach-only advising application

Research for [Research: Human-Centered UX Design Philosophies and Intuitive Interaction Patterns](https://github.com/djsciman/video_transcriber_rag/issues/88), a child of the [UI/UX Redesign map](https://github.com/djsciman/video_transcriber_rag/issues/85).

This document is discovery, not a lock. It does not pick a winner. Live screens stay the spec-70 stdlib HTTP shell until the review child records direction.

Throwaway prototypes:

- `prototypes/ui-ux-redesign/ux-index.html`
- `prototypes/ui-ux-redesign/ux-guided.html` (task-oriented guided next-action / progressive disclosure)
- `prototypes/ui-ux-redesign/ux-inbox.html` (attention inbox + workspace)
- `prototypes/ui-ux-redesign/ux-studio.html` (topic studio with Design map as spatial center)

Filenames are kept as specified. Research names that map onto them are in section 9.

## 1. Executive summary

The spec-70 shell is a flat nav of equally weighted screens: Home, Curate, Place, Finder, Design, Sheet, Custom, History, plus topic, briefing, print, and settings routes that are not always labeled in that nav (`coach_app/app.py`, `coach_app/ui_*.py`). That layout matches a catalog of capabilities. It does not match how a coach actually works: admit a volume to the curated store, place citations on named moves, open a topic, read a briefing, determine a system, Design a unit, pack a Draft, Edit the sheet, print a packet.

Established findings (not this ticket's recommendations):

- Discoverability comes from perceived affordances, signifiers, constraints, mapping, and feedback, not from a complete list of destinations ([Norman, *The Design of Everyday Things*](https://www.si.edu/object/siris_sil_1091646); [Norman, "Affordances and Design"](https://jnd.org/affordances-and-design/)).
- People keep a conceptual model of how a system works. That model is built from the system image (screens, labels, behavior), not from the designer's intent ([Norman, "Affordances and Design"](https://jnd.org/affordances-and-design/); [IxDF, Mental models](https://ixdf.org/literature/book/the-glossary-of-human-computer-interaction/mental-models)).
- Visibility of system status, match to the coach's language, recognition over recall, and error prevention are the Nielsen heuristics that most obviously fail in a flat screen list ([Nielsen, 10 usability heuristics](https://www.nngroup.com/articles/ten-usability-heuristics/)).
- Progressive disclosure and staged disclosure are the proven ways to keep power without dumping every command on the first screen ([Nielsen, Progressive disclosure](https://www.nngroup.com/articles/progressive-disclosure/)).
- Hick–Hyman and Fitts constrain how many choices to show at once and how large and close primary actions should be ([NNG, Hick's Law](https://www.nngroup.com/videos/hicks-law-long-menus/); [NNG, Fitts's Law](https://www.nngroup.com/articles/fitts-law/)).
- WCAG 2.2 still organizes accessibility as Perceivable, Operable, Understandable, Robust ([W3C WAI, WCAG 2 Overview](https://www.w3.org/WAI/standards-guidelines/wcag/); [Understanding WCAG 2.2](https://www.w3.org/WAI/WCAG22/Understanding/intro)).

This application is a **complex application** in NN/g's sense: broad goals, nonlinear workflows, high information volume ([NNG, Application complexity](https://www.nngroup.com/articles/complex-application-design-framework/)). The coach is the only person who uses it. Students never do. The advisor proposes; the coach accepts, corrects, removes, places, chooses, and converts. That distinction is a conceptual-model problem, not a visual-skin problem.

Three candidate interaction paradigms, not three skins:

| Filename | Research name | Organizing idea |
| --- | --- | --- |
| `ux-guided.html` | Guided work | Time and next action. One current job. Staged disclosure. |
| `ux-inbox.html` | Attention inbox | Attention and state. Queues of outstanding work plus a workspace. |
| `ux-studio.html` | Topic studio | Place and object. The open topic and Design map sit at the center. |

No winner is selected. The review child ([issue 89](https://github.com/djsciman/video_transcriber_rag/issues/89)) is the place to grill these candidates against the workflow discovery ticket.

## 2. Research methodology and sources

### Method

1. Read `GLOSSARY.md` and locked teaching language. The person who uses the application is the **coach**. Students never use it.
2. Inspect the live spec-70 shell: `coach_app/app.py`, `coach_app/shell.css`, and `coach_app/ui_*.py` (Home, settings, Curate, Place, Finder, topics, briefing/system, Design, Sheet Draft/Read/Edit, Custom, History, print).
3. Read primary and first-party sources: Norman (*The Design of Everyday Things* and jnd.org essays), Nielsen Norman Group, W3C WAI / WCAG 2.2, Interaction Design Foundation topic articles, Fitts and Hick–Hyman as summarized by NNG with original citations, Shneiderman's eight golden rules, Jobs to Be Done (Christensen / Ulwick), journey mapping (NNG).
4. Distinguish **established findings** (cited) from **application of those findings to this application** (this ticket's analysis) and from **candidate principles** (section 6, not a lock).
5. Make three throwaway HTML prototypes that differ in information architecture and interaction, not color.

Out of scope: replacing live screens, locking a visual stack (sibling issue 87), rewriting production `coach_app/`, naming an advisor vendor or store engine.

### Primary sources

**Norman**

- *The Design of Everyday Things*, revised edition. Contents and claims summarized by the Smithsonian catalog: psychopathology of everyday things; psychology of everyday actions; knowledge in the head vs in the world; constraints, discoverability, feedback; human error vs design ([Smithsonian record](https://www.si.edu/object/siris_sil_1091646)). Chapter 1 PDF used for affordance / signifier / mapping wording ([Norman, DOET ch. 1](https://www.arjun-chandrasekhar-teaching.com/courses/Pitt/CMPINF0010/course-readings/design/Norman-The-Design-of-Everyday-Things-Chapter-1.pdf)).
- ["Affordances and Design"](https://jnd.org/affordances-and-design/)
- ["The Four Fundamental Principles of Human-Centered Design"](https://jnd.org/the-four-fundamental-principles-ofhuman-centered-design-and-application/)
- ["Humanity-Centered versus Human-Centered Design"](https://jnd.org/humanity-centered-versus-human-centered-design/)
- ["People-Centered (Not Tech-Driven) Design"](https://jnd.org/people-centered-not-tech-driven-design/)
- ["Emotional Design: People and Things"](https://jnd.org/emotional-design-people-and-things/)

**Nielsen Norman Group**

- [10 usability heuristics](https://www.nngroup.com/articles/ten-usability-heuristics/)
- [Progressive disclosure](https://www.nngroup.com/articles/progressive-disclosure/)
- [Fitts's Law](https://www.nngroup.com/articles/fitts-law/)
- [Hick's Law](https://www.nngroup.com/videos/hicks-law-long-menus/)
- [Minimize cognitive load](https://www.nngroup.com/articles/minimize-cognitive-load/)
- [Recognition rather than recall (heuristic 6)](https://www.nngroup.com/articles/ten-usability-heuristics/)
- [Journey mapping 101](https://www.nngroup.com/articles/journey-mapping-101/)
- [Information scent](https://www.nngroup.com/articles/information-scent/)
- [Information foraging](https://www.nngroup.com/articles/information-foraging/)
- [Usability heuristics applied to complex applications](https://www.nngroup.com/articles/usability-heuristics-complex-applications/)
- [Application complexity: 5-layer framework](https://www.nngroup.com/articles/complex-application-design-framework/)
- [User expertise stagnates](https://www.nngroup.com/articles/stagnating-expertise/)
- [Gestalt principles for visual UI design](https://www.uxtigers.com/post/gestalt-principles) (Nielsen, UX Tigers)

**W3C WAI**

- [WCAG 2 Overview](https://www.w3.org/WAI/standards-guidelines/wcag/)
- [Understanding WCAG 2.2: four principles](https://www.w3.org/WAI/WCAG22/Understanding/intro)
- [What's new in WCAG 2.2](https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/)
- [Designing for web accessibility](https://www.w3.org/WAI/tips/designing/)

**Interaction Design Foundation**

- [Affordances](https://www.interaction-design.org/literature/topics/affordances)
- [Mental models](https://ixdf.org/literature/book/the-glossary-of-human-computer-interaction/mental-models)
- [Shneiderman's eight golden rules](https://www.interaction-design.org/literature/article/shneiderman-s-eight-golden-rules-will-help-you-design-better-interfaces%c2%a0)

**Original / cited laws**

- Fitts, P. M. (1954). The information capacity of the human motor system in controlling the amplitude of movement. Summarized with the Shannon formulation in [NNG Fitts's Law](https://www.nngroup.com/articles/fitts-law/).
- Hick, W. E. (1952). On the rate of gain of information. Hyman, R. (1953). Stimulus information as a determinant of reaction time. Summarized as Hick–Hyman in [NNG Hick's Law](https://www.nngroup.com/videos/hicks-law-long-menus/).
- Sweller, J. (1988). Cognitive load during problem solving. Applied to UX as intrinsic / extraneous / germane load in [NNG Minimize cognitive load](https://www.nngroup.com/articles/minimize-cognitive-load/).
- Gibson, J. J. (1979). *The Ecological Approach to Visual Perception*. Source of affordance, cited by [Norman](https://jnd.org/affordances-and-design/).
- Card, Pirolli, et al. (Xerox PARC). Information foraging. [NNG](https://www.nngroup.com/articles/information-foraging/).

**Other established work used below**

- Shneiderman, B. Eight golden rules; direct manipulation.
- Saffer, D. *Microinteractions* (triggers, rules, feedback, loops). Norman wrote the foreword.
- Fogg, B. J. (2009). A behavior model for persuasive design (motivation, ability, trigger).
- Christensen / Moesta (jobs-as-progress) and Ulwick (job map: define, locate, prepare, confirm, execute, monitor, modify, conclude).
- Rosenfeld, Morville, Arango. Information architecture (organization, labeling, navigation, search) as applied through NNG IA / scent articles.

## 3. Summary of relevant UX philosophies and principles

Each subsection states the **established finding**, then a short **this-application note**. Notes are analysis, not locks.

### 3.1 Norman: affordances, signifiers, discoverability, feedback, mapping, constraints, conceptual models

**Affordances** are action possibilities in the relation between a person and an object, not a visual style. Gibson coined the term; Norman brought it into design and later stressed *perceived* affordance ([Norman, Affordances and Design](https://jnd.org/affordances-and-design/); [IxDF, Affordances](https://www.interaction-design.org/literature/topics/affordances)). A button affords pressing only if the coach can perceive that it can be pressed and that pressing it will do the intended work.

**Signifiers** are perceivable cues that communicate where and how to act. Norman introduced the term because designers were calling labels and shadows "affordances." Affordances are what is possible; signifiers announce it ([DOET ch. 1](https://www.arjun-chandrasekhar-teaching.com/courses/Pitt/CMPINF0010/course-readings/design/Norman-The-Design-of-Everyday-Things-Chapter-1.pdf)).

**Discoverability** is whether the coach can determine what actions are possible and the current state of the device from looking ([DOET](https://www.si.edu/object/siris_sil_1091646)). A complete nav of screen names is not the same as discoverability of *what to do next*.

**Feedback** communicates that an action was received and what state resulted. Immediate, specific feedback builds a conceptual model; silence forces guesswork ([Nielsen heuristic 1](https://www.nngroup.com/articles/ten-usability-heuristics/); Norman DOET).

**Mapping** is the relationship between controls and effects. Natural mapping uses spatial or semantic correspondence ([NNG, natural mapping via heuristic 2](https://www.nngroup.com/articles/ten-usability-heuristics/)). In this application, mapping includes: advisor proposal -> coach Accept/Correct/Skip; Design canvas -> Draft classes; cleaned statement -> citation in the curated store.

**Constraints** (physical, cultural, semantic, logical) limit possible actions so the right action is the easy one ([DOET](https://www.si.edu/object/siris_sil_1091646)). Spec-70 already uses some: technique and following drill are glued; gi and no-gi stay separate topics. Constraints that are not visible do not help.

**Conceptual models.** Norman: the most important part of a successful design is a coherent conceptual model. The coach's model is assembled from the **system image**. A misunderstanding is worse than a lack of understanding, because the coach will not know they are wrong ([Norman, HCD principles, opaque automation](https://jnd.org/the-four-fundamental-principles-ofhuman-centered-design-and-application/)). Conceptual models need only be good enough to guide action; different aspects of a system can have different models.

**This-application note.** The live shell's conceptual model is "a list of screens." The coach's work model is "admit teaching into the store, then teach one topic through to a packet." Those two models do not match. Signifiers such as `Curate` and `Place` have weak information scent for a first-time coach. `Sheet` does not say Draft / Read / Edit. Briefing and print are not in the labeled nav.

### 3.2 Gulfs of execution and evaluation

Norman: the gulf of execution is the gap between the coach's intention and the actions the system affords; the gulf of evaluation is the gap between the system's state and the coach's ability to interpret it ([IxDF course outline citing Norman](https://www.interaction-design.org/courses/psychology-of-interaction-design-the-ultimate-guide)).

**This-application note.** Execution gulf: "I want to teach Hip bump sweep (gi)" does not map onto Open topic -> Briefing -> Choose system -> Design -> Convert. Evaluation gulf: after Accept on a cleaned statement, the Home screen does not show that the curated store grew, that the citation is uncategorized, or that Place is the next review.

### 3.3 Error prevention and recovery

Norman treats most "human error" as design failure: slips (inattention) vs mistakes (wrong model) ([NNG heuristic 5](https://www.nngroup.com/articles/ten-usability-heuristics/)). Best designs prevent; then they offer undo, plain-language diagnosis, and a path out ([heuristics 3, 5, 9](https://www.nngroup.com/articles/ten-usability-heuristics/)).

**This-application note.** High-cost actions already exist: Remove topic, remove accepted citation, convert Design to Draft. Spec-70 often POSTs and redirects with little confirmation of what changed. Convert with an empty map shows `_EMPTY_CONVERT` on Design (`coach_app/ui_design.py`). Missing video files still admit citations (glossary: playback link may be absent). Those states need to be visible as outstanding work, not silent.

### 3.4 Human-centered design (HCD) and humanity-centered design

Norman's four HCD principles ([jnd.org, 2019](https://jnd.org/the-four-fundamental-principles-ofhuman-centered-design-and-application/)):

1. Solve the root issue, not the presented symptom.
2. Focus on people.
3. Take a systems point of view (activities and interdependencies, not isolated screens).
4. Iterate with rapid prototypes and tests with the people who will use it.

He later expands to humanity-centered design: ecosystem, long-term impact, design *with* the community ([jnd.org, 2022](https://jnd.org/humanity-centered-versus-human-centered-design/)). For this local coach-only application, HCD is the operative frame. Humanity-centered concerns (students, gym culture, gi/no-gi as separate practices) sit in domain rules already locked on issues 52 and 70, not in this UI ticket.

People-centered, not tech-driven: start from the coach's needs and capabilities; technology fills what the coach cannot do alone ([Norman, 2019](https://jnd.org/people-centered-not-tech-driven-design/)). The advisor is a partner that proposes; it does not determine the system.

**This-application note.** A root issue is not "the nav needs more labels." The root issue is that the coach cannot see the activity: fill the curated store, then teach one topic. Screen-by-screen optimization can make each page clearer while the global activity stays opaque (Norman's local vs global optimization warning).

### 3.5 Interaction design (IxD)

IxD is the design of the dialogue between person and system over time: what the person can do, how the system answers, how the conversation closes ([Shneiderman: dialogs yield closure](https://www.interaction-design.org/literature/article/shneiderman-s-eight-golden-rules-will-help-you-design-better-interfaces%c2%a0)). Direct manipulation (Shneiderman) keeps objects visible, actions rapid and reversible, and effects immediately visible. Spec-70 Design already uses a force-graph as a direct-manipulation object. Curation and briefing do not.

### 3.6 Cognitive load

Cognitive load is mental effort required to operate the system. UX work targets **extraneous** load: clutter, novel jargon, memory of other screens ([NNG, Minimize cognitive load](https://www.nngroup.com/articles/minimize-cognitive-load/)). Three NNG tactics: avoid visual clutter, build on existing mental models, offload tasks (show, don't make the coach remember). Interaction cost = physical + mental effort; cutting clicks that raise mental effort is a net loss ([NNG, efficiency vs expectations](https://www.nngroup.com/articles/efficiency-vs-expectations/)).

**This-application note.** Intrinsic load is high and legitimate: disagreements, other-ruleset caveats, enrichment hierarchy, packing rules. Extraneous load is the coach reconstructing "where am I in teaching this topic?" from a nav of eight destinations. Offload: keep topic, ruleset, system-chosen?, map-ready?, sheet-mode on screen.

### 3.7 Gestalt

People perceive organized wholes: proximity, similarity, continuity, closure, figure-ground, common region ([Nielsen on Gestalt](https://www.uxtigers.com/post/gestalt-principles); Wertheimer, 1920s). Grouping is the first read, before labels.

**This-application note.** Spec-70 already groups some things well: class-card color by lesson type; caveat boxes; disagreement sides. The shell nav treats Home, Curate, Place, Finder, Design, Sheet, Custom, History as one Gestalt group of equal weight. They are not equal. Curation work and topic work are different activities.

### 3.8 Information architecture

IA is organization, labeling, navigation, and search so people can find and complete work. Labels need **information scent**: an estimate of value on the other side of a click, from the words and their context ([NNG, Information scent](https://www.nngroup.com/articles/information-scent/); [Information foraging](https://www.nngroup.com/articles/information-foraging/); Card / Pirolli, PARC). Vague verbs (`Explore`, `Learn`) fail as nav ([NNG, IA mistakes](https://www.nngroup.com/articles/3-ia-mistakes/)).

**This-application note.** `Sheet` has poor scent for Draft/Read/Edit. `Place` has poor scent for "review uncategorized citations." `Finder` has better scent for enrichment browse. Home mixes topic open with playback folders. Briefing is a child of topic but lives on an unlabeled route.

### 3.9 Progressive disclosure and staged disclosure

Progressive disclosure: show a few important options first; reveal specialized options on request. Improves learnability, efficiency, and error rate. Get the split right; make the path to secondary features obvious ([Nielsen, 2006](https://www.nngroup.com/articles/progressive-disclosure/)).

Staged disclosure (wizards): linear steps for a task whose parts are not interdependent. Harmful when steps must be compared together (Nielsen's hotel-reservation example).

**This-application note.** Curation (load volume -> review proposals -> accept) is a candidate for staged disclosure. Design (add walk + spatial map + convert) is interdependent and should stay on one surface. Briefing + system choice are one activity (the memo is "before the coach determines the system" in `ui_briefing.py`). Do not split them across a wizard that hides disagreement while the coach types system words.

### 3.10 Recognition versus recall

Minimize memory load; keep actions and options visible. Recognition is cheaper than recall ([Nielsen heuristic 6](https://www.nngroup.com/articles/ten-usability-heuristics/)). Norman's "knowledge in the world vs knowledge in the head" is the same tradeoff ([DOET](https://www.si.edu/object/siris_sil_1091646)).

**This-application note.** The coach should not have to remember that uncategorized citations wait on Place, or that an empty system blocks a coherent Design, or that Convert lives on Design not Sheet. Put those facts in the world.

### 3.11 Hick–Hyman Law

Decision time grows with the number and uncertainty of choices ([Hick 1952, Hyman 1953](https://www.nngroup.com/videos/hicks-law-long-menus/)). Grouping and progressive disclosure keep the choice set small without removing power.

**This-application note.** Eight equal nav items plus unlabeled routes is a Hick problem for a first-time coach. A returning coach who already knows the map is less harmed (Nielsen heuristic 7: accelerators for experts).

### 3.12 Fitts's Law

Movement time grows with distance and shrinks with target size. Bigger, closer, edge-placed (mouse) targets are faster; crowded small targets cause slips ([Fitts 1954; NNG 2022](https://www.nngroup.com/articles/fitts-law/)). WCAG 2.2 adds target-size minimums ([What's new in 2.2](https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/)).

**This-application note.** Primary coach actions (Accept citation, Choose system, Convert, Print) should be large and adjacent to the object they act on, not a small button at the far end of a form. Spec-70 already places Accept next to the proposal (`ui_curate.py`). Convert is easier to miss on a wide Design canvas.

### 3.13 Mental models, consistency, Jakob's Law

A mental model is a simplified internal theory that lets someone predict a system ([Nielsen, mental models](https://www.uxtigers.com/post/user-expectations); Craik 1943; Johnson-Laird 1983). Jakob's Law: people spend most of their time in other products; they expect this one to work like those ([heuristic 4](https://www.nngroup.com/articles/ten-usability-heuristics/)). Internal consistency still matters more for a specialist tool than copying a commercial product. This ticket must not imitate a commercial product as a copy.

**This-application note.** The coach already has mental models: a volume is a recording; a topic is something to teach; a system is a dilemma; a class is a meeting. The application should speak that language (heuristic 2; `GLOSSARY.md`). It should not import inbox/kanban/studio metaphors so strongly that they overwrite those words. Candidate 2 uses "inbox" as an *attention* structure, not as mail.

### 3.14 Emotional design and microinteractions

Norman: visceral (appearance), behavioral (use), reflective (meaning, self-image) ([jnd.org, Emotional Design](https://jnd.org/emotional-design-people-and-things/)). For a coach-only advising application, behavioral trust matters more than decoration: the advisor must look like a proposal, not like a verdict.

Saffer: a microinteraction is trigger, rules, feedback, loops/modes. Details turn tolerated tools into ones people will re-enter ([Saffer, *Microinteractions*](https://dl.acm.org/doi/10.5555/2531374)). NNG ties microinteractions to continuous status communication ([heuristic 1](https://www.nngroup.com/articles/ten-usability-heuristics/)).

**This-application note.** Accepting a cleaned statement, choosing a system, converting Design to Draft, and printing are closure moments (Shneiderman rule 4). They should feel finished: count of citations now in the store, system words saved on the topic, Draft mode on the sheet, packet pages ready.

### 3.15 Behavioral design (Fogg)

Behavior = motivation x ability x trigger, at the same moment ([Fogg, 2009](https://www.bjfogg.com)). Use here is **not** to persuade the coach to do work they did not intend. Use it to make intended work able and triggerable: when motivation is already "teach this topic," ability is reduced extraneous load, and the trigger is a visible next action. Dark patterns are out of scope and out of ethics for a coach-owned local application.

### 3.16 Accessibility and inclusive design

WCAG 2.2: 13 guidelines under POUR — Perceivable, Operable, Understandable, Robust ([W3C](https://www.w3.org/WAI/WCAG22/Understanding/intro)). Success criteria at A / AA / AAA. W3C encourages the latest version; 2.2 is backwards compatible with 2.1 and 2.0 ([WCAG 2 Overview](https://www.w3.org/WAI/standards-guidelines/wcag/)). Practical WAI tips: contrast, not color alone, identifiable interactive elements, headings and whitespace, target size, consistent help ([Designing for web accessibility](https://www.w3.org/WAI/tips/designing/)). Spec-70 already sets `lang="en"`, `aria-current="page"` on nav. Color-coded class cards must not be the only lesson-type cue (they also use labels/pills).

Shneiderman: seek universal usability (novice/expert, age, disability). A single-coach local app still needs keyboard operation, visible focus (WCAG 2.4.11 Focus Not Obscured), and understandable errors.

### 3.17 Nielsen's 10 heuristics (applied as a set)

1. Visibility of system status
2. Match between system and the real world
3. User control and freedom
4. Consistency and standards
5. Error prevention
6. Recognition rather than recall
7. Flexibility and efficiency of use
8. Aesthetic and minimalist design
9. Help users recognize, diagnose, and recover from errors
10. Help and documentation

For complex apps, NN/g stresses recognition cues in dense data, staged disclosure of rare controls, and status that spans long-running work ([complex applications](https://www.nngroup.com/articles/usability-heuristics-complex-applications/)).

### 3.18 Jobs to Be Done

Two families: Christensen/Moesta (progress the person is trying to make) and Ulwick (functional job map: define, locate, prepare, confirm, execute, monitor, modify, conclude) ([Ulwick, mapping the job](https://jobs-to-be-done.com/mapping-the-job-to-be-done-45336427b3bc)). A job map is not a journey map: it describes what the person is trying to get done, not the current UI steps.

**This-application note.** Candidate jobs (analysis, not a lock):

- When a raw volume is on disk, admit its teaching into the curated store so advising can use it.
- When citations sit uncategorized, place them on named moves so they can enter a lesson.
- When a student failed a movement under resistance, open that topic and determine the system.
- When the system is chosen, Design the unit and pack a Draft the coach can Edit and print.

The UI should be organized around those jobs, or around the objects those jobs act on (store, topic), not around Python modules.

### 3.19 Journey mapping and task-oriented UI

A journey map visualizes the process a person goes through to accomplish a goal: actor, scenario, phases, actions/thoughts/emotions, opportunities ([NNG, Journey mapping 101](https://www.nngroup.com/articles/journey-mapping-101/)). User flows are the finer in-product steps ([NNG, journeys vs flows](https://www.nngroup.com/articles/user-journeys-vs-user-flows)).

Task-oriented UI (and Shneiderman's closure): group the interface by the job in progress, show beginning/middle/end, and put the next action next to the object. Contrasts with object-oriented UI (objects first, actions on the object) and with application-oriented UI (features in a menu).

**This-application note.** Spec-70 is application-oriented (screens as features). Candidate 1 is task-oriented. Candidate 3 is object-oriented (topic as object). Candidate 2 is state-oriented (work items as objects in queues).

### 3.20 Additional theories that earn a place

**Tesler's law.** Complexity is conserved; the application can absorb it so the coach does not ([NNG, Tesler's Law](https://www.nngroup.com/videos/teslers-law/)). Placement proposals, first packing, and briefing memos are Tesler in product form: the advisor takes complexity; the coach decides.

**Knowledge in the world.** Norman: put structure in the environment so the coach need not memorize sequences.

**Activity-centered systems approach.** Norman HCD principle 3: design the whole activity. Curation without Place leaves citations unusable on a lesson. Design without a system leaves the map unanchored. Print without a sheet prints nothing useful.

**Direct manipulation.** The Design force-graph is already this. Studio candidate extends it: the topic *is* a place you work inside.

**Flexibility and efficiency (heuristic 7).** First-time coaches need guidance; returning coaches re-teach from History, curate another volume, and jump to Edit. Any candidate that only serves one of those two will fail.

## 4. Comparative analysis of the most applicable approaches

Approaches below are established ways to *organize* an application. They are not visual themes.

| Approach | Organizes by | Strength here | Weakness here |
| --- | --- | --- | --- |
| Application / feature nav (status quo) | Screens | Honest about capabilities; cheap to implement in stdlib HTTP | Weak discoverability of next action; Hick load; poor scent; no activity model |
| Task-oriented / staged disclosure | Current job and step | Shrinks gulf of execution; first-time friendly; closure | Can hide interdependent work; returning coach may feel infantalized |
| Attention / queue (GTD-like) | Outstanding work state | Status visibility; returning coach sees what is stuck | Queue metaphors can overwrite domain language; risk of "email" feel |
| Object / spatial (topic as place) | Open topic + Design map | Matches "one topic" teaching; Design already spatial | Curation is store-wide, not topic-local; empty studio is a cold start |
| Document / memo | Briefing as the artifact | Briefing is already a memo; print is already a packet | Does not cover Curate/Place/Finder well |
| Command palette / search-first | Recall of named actions | Fast for experts | Violates recognition-over-recall for first-time use |

Most applicable combination (analysis, not a lock): **activity-centered HCD** as the philosophy, **Nielsen heuristics + WCAG** as the quality bar, and **one of** task / queue / spatial as the interaction paradigm. Visual design and technology stack belong to issue 87.

Comparison on the ticket's own questions:

| Question | Feature nav now | Guided | Inbox | Studio |
| --- | --- | --- | --- | --- |
| Discover functionality | Scan eight labels | See current job + later steps collapsed | See counts per state | See docks around the map |
| Possible actions | Whatever the screen posts | One primary action | Actions on the open card | Actions on the object in the studio |
| What next | Unstated | Explicit next-action | Highest-severity queue | Suggested from topic gaps |
| Workflow nav | Lateral screens | Linear stage rail | Queue -> workspace | Spatial docks |
| Advisor vs coach | Same buttons, mixed copy | Labeled proposal vs decision | "Needs decision" queue | Proposal layer on the map |
| Curated store | Invisible except Finder/Place | Store health as a stage | Store items in queues | Store as a side room |
| Progress / errors | Empty copy on some panels | Checklist of blockers | Queue membership | Gap marks on the map |

## 5. Application-specific implications

Grounded in spec-70 as inspected.

### 5.1 Discoverability

`nav_items()` in `coach_app/app.py` labels: Home, Curate, Place, Finder, Design, Sheet, Custom, History. Unlabeled: settings POST, `/topics`, `/briefing`, `/print`. Home holds topic open *and* playback folders. A first-time coach cannot discover that briefing exists without opening a topic. Print is reached from the sheet/design flow, not the shell nav.

Implication: either promote briefing/print into a visible activity, or stop treating the shell nav as the map of the product.

### 5.2 Communicating possible actions

Curate already pairs each proposal with Accept / Dismiss and later Correct / Remove (`ui_curate.py`). Place uses Accept / Correct / Skip plus author (`ui_placement.py`). Briefing uses Choose on system words and Set aside on conflicts (`ui_briefing.py`). Design uses an add walk, map clicks, and Convert (`ui_design.py`). Sheet uses Draft / Read / Edit modes (`ui_sheet.py`).

The pattern is good locally and invisible globally. Signifiers should distinguish:

- **Information** (citation text, playback link, caveat, memo)
- **Advisor recommendation** (proposed cleaned statement, proposed named-move link, briefing disagreement sides, first packing)
- **Coach decision** (accept, correct, skip, choose system, set-aside, welcome other-ruleset)
- **Coach action** (open topic, convert, print, remove)

Color alone is not enough (WCAG). Use labels, regions, and wording: "Advisor proposes" vs "Coach chooses."

### 5.3 What to do next

Nothing in the shell computes a next action. Empty states say "No uncategorized citations" or "Empty until chosen" but do not point to the complementary screen.

Candidate next-action rules (for prototypes, not production):

1. No video root / transcript folder -> settings
2. Raw volume not curated -> Curate
3. Uncategorized citations -> Place
4. No topic open -> Open topic
5. Topic with empty system -> Briefing
6. System chosen, empty Design map -> Design
7. Map with named moves, no sheet -> Convert to Draft
8. Draft exists -> Read / Edit / Print
9. Returning: History copy, or another volume

### 5.4 Workflow representation

Two interleaved activities:

**Store activity:** settings -> Curate -> Place -> Finder (organize enrichment, coach-authored citations).

**Topic activity:** Open topic (welcome other-ruleset) -> Briefing (disagreement, set-aside, choose system) -> Design -> Convert (Draft) -> Edit sheet (Custom pull, History) -> Print.

They meet: citations must be in the store and on a named move before Design and lessons can use them. Spec-70 never draws that join.

### 5.5 Distinguishing information, recommendations, decisions, actions

Norman on opaque automation: recommendations without a conceptual model reduce trust; over-trust is more dangerous than under-trust ([HCD essay](https://jnd.org/the-four-fundamental-principles-ofhuman-centered-design-and-application/)). The glossary already says the advisor advises and the coach determines the system. The UI should make that legally and visually true: proposals are reversible, labeled, and never the same control as a coach commit.

### 5.6 Relationship to the curated store

The store is the coach's records on this machine. Home does not report: volumes awaiting, citations accepted, uncategorized count, enrichment nodes, topics, units. Finder and Place are the only windows into store health. A coach can believe "I curated" while citations remain uncategorized and unusable on a lesson.

### 5.7 Progress, completion, errors, outstanding work

Outstanding work that should be first-class:

- Raw volumes in the transcript folder not yet accepted
- Uncategorized citations
- Empty system words on an open topic
- Unpackable Design canvas (no named moves or systems; `_EMPTY_CONVERT`)
- Missing video files (citation still valid; playback link absent)
- Other-ruleset instructionals not yet welcomed yes/no
- Draft vs Edit: dashed vs solid class cards already signify mode (`ui_sheet.py`)

Errors: failed JSON load on Curate currently yields empty proposals without a plain-language diagnosis (`ui_curate.py` `_load` except path). Heuristic 9 wants: what went wrong, in coach language, and what to do.

### 5.8 Making curation and Design-to-Draft approachable

Curation is intrinsically a review queue. Approachable means: one volume at a time, one proposal at a time if needed (Hick), playback link next to the statement (Fitts: action next to object), accept is the large target, dismiss is available but not equal-weight if the default is admit.

Design-to-Draft is intrinsically spatial then linear. Approachable means: empty map explains how to add a named move (add walk already exists); Convert is disabled with a reason until the map can pack; Draft is clearly a proposal (dashed cards already); Edit is the coach's sheet.

### 5.9 First-time vs returning coach

Nielsen heuristic 7 and stagnating expertise: people do not keep learning features; they reuse a few ([NNG, stagnating expertise](https://www.nngroup.com/articles/stagnating-expertise/)). First-time: staged disclosure, visible next action, just-in-time help (heuristic 10). Returning: jump to Place, jump to a topic studio, copy from History, accelerators. Forgiveness (undo, Remove that is hard to hit accidentally) makes exploration possible.

The coach is the only person. There is no student-facing mode, no multi-seat onboarding. Expertise will grow, then stagnate. Discoverability of old features (Custom, History, Finder organize) remains a problem after year one.

## 6. Recommended design principles (candidates, not a lock)

These are candidates for the review child to accept, rewrite, or reject.

1. **Coach language is the system language.** Topic, citation, curated store, briefing, Design, Draft, Custom, enrichment, system, set-aside, cleaned statement, playback link. No "user," no vendor, no engine.
2. **The advisor proposes; the coach determines.** Proposals are labeled, reversible, and visually distinct from commits.
3. **Put knowledge in the world.** Topic, ruleset, store counts, system-chosen, map-ready, sheet mode, missing video, uncategorized count stay visible.
4. **One activity at a time, whole activity visible.** Do not optimize Curate in isolation from Place, or Design in isolation from system choice.
5. **Next action is a first-class object.** If nothing is next, say the work is clear.
6. **Constraints that already exist in domain rules should be visible.** Glued technique+drill, gi/no-gi split, uncategorized not offered on a lesson, Convert needs named moves or systems.
7. **Closure after meaningful work.** Accept, Choose, Convert, Print each produce a status the coach can evaluate (gulf of evaluation).
8. **Recognition over recall; accelerators for return visits.** Guidance can collapse.
9. **POUR as a floor.** Contrast, not color alone, keyboard, visible focus, target size, understandable errors.
10. **Forgiving high-cost actions.** Remove topic / remove citation need control and freedom (heuristic 3), not hidden POST buttons of equal weight to Open.
11. **Tesler: the application holds packing and placement complexity; the coach holds decisions.**
12. **Do not copy a commercial product.** Metaphors (inbox, studio, guide) are structural, not brand imitation.

## 7. Potential interaction paradigms

1. **Guided work (staged + progressive disclosure).** A job rail. One primary action. Secondary tools behind an explicit control. Prototype: `ux-guided.html`.
2. **Attention inbox + workspace.** Work items in Awaiting / In progress / Needs decision / Done. Opening an item opens a workspace. Prototype: `ux-inbox.html`.
3. **Topic studio (object + spatial).** The open topic is a place. Design map is the center. Briefing, store, sheet, print are docks. Prototype: `ux-studio.html`.
4. **Document-centric (not prototyped).** Briefing memo and print packet as the two documents; everything else is how you assemble them. Strong for print week, weak for curation.
5. **Command-first (not prototyped).** Search "Hip bump" and land on topic + citations. Strong for returning experts, weak for first-time conceptual model.
6. **Hybrid (not prototyped, likely in review).** Studio for topic work + inbox counts for store health + a single next-action when the coach is stuck. Hybrids are how many complex apps end; they are not a fourth candidate here because this ticket asked for three distinct approaches.

## 8. Risks, trade-offs, unresolved questions

**Risks**

- Wizard fatigue if guided work is mandatory after the coach already knows the path.
- Inbox metaphor colliding with mail, or with "the advisor is messaging you."
- Studio leaving curation as a second-class room, starving the store.
- Over-trust in advisor proposals if they sit in the same visual layer as coach decisions (Norman).
- Color-coded queues or class cards failing WCAG if they are the only cue.
- Local-optimization: a beautiful Design canvas that still does not tell the coach to choose a system.
- Issue 87 (visual/tech) picking a stack that cannot express the chosen paradigm (force-graph + queues + print CSS).

**Trade-offs**

- Guidance vs speed (heuristics 6 vs 7).
- One screen of interdependent controls vs staged simplicity (Nielsen hotel example).
- Knowledge in the world (always-on status) vs aesthetic minimalism (heuristic 8).
- Domain-faithful labels vs familiar external patterns (Jakob's Law vs glossary lock).

**Unresolved questions (for issue 86 / 89, not answered here)**

- What does the coach actually do in the first ten minutes of a new machine? (Needs journey evidence from 86.)
- Is curation daily and topic work weekly, or the reverse? Frequency should drive which activity owns Home.
- Should uncategorized citations block Design, warn, or stay silent?
- Is "next action" allowed to be wrong, or must it be derived only from store facts?
- How much of Finder belongs in the main activity vs a maintenance dock?
- Print: inside the topic studio, or a separate output bench?
- First-time empty store: guided setup of video root + first volume, or Home with two empty lists as now?

## 9. Three candidate approaches

No winner. Each subsection is meant to be readable next to its prototype.

### 9.1 Candidate A — Guided work

**Prototype:** [`prototypes/ui-ux-redesign/ux-guided.html`](../../prototypes/ui-ux-redesign/ux-guided.html)

**Philosophy.** Human-centered, activity-centered, staged disclosure. Shrink the gulf of execution. Tesler: the application sequences the job; the coach decides at each step.

**Paradigm.** Task-oriented UI. One current job. Progressive disclosure of later stages. Shneiderman closure at each stage.

**IA.** A stage rail, not a screen nav:

1. Folders (playback)
2. Curate a volume
3. Place citations
4. Open a topic
5. Briefing and system
6. Design
7. Draft / Edit sheet
8. Print

Secondary: Finder, Custom, History behind "More tools."

**Journeys (in the prototype)**

- Curate/place: load sample volume -> accept a cleaned statement (store count rises) -> place onto Hip bump sweep.
- Topic -> briefing -> system: open Hip bump sweep (gi) -> read same-ruleset citations and a disagreement -> choose system words.
- Design -> Draft -> Edit -> print: add/see named moves on a simplified map -> convert (Draft dashed cards) -> Edit purpose line -> print packet preview.

**Patterns.** Next-action card (Fitts: large target). Disabled Convert with reason. Proposal vs decision labels. Status line after every commit.

**Pros.** Best first-time discoverability; lowest Hick load; clear next action; easy POUR structure (one h1, one primary button).

**Cons.** Returning coach overhead; interdependent Design/briefing can feel split; risk of "cannot skip."

**Usability.** High learnability, medium efficiency unless Skip/jump exists (prototype includes Jump to stage). Error rate should drop because illegal actions are constrained.

**Accessibility.** Linear DOM order matches the job; one main landmark; primary button is a real `<button>`; stage rail uses `aria-current`. Risk: rail as the only status if not also text.

### 9.2 Candidate B — Attention inbox + workspace

**Prototype:** [`prototypes/ui-ux-redesign/ux-inbox.html`](../../prototypes/ui-ux-redesign/ux-inbox.html)

**Philosophy.** Visibility of system status as the home. Recognition over recall: outstanding work is listed, not remembered. Heuristic 1 as the product.

**Paradigm.** Queue + workspace. Items have state: Awaiting, In progress, Needs decision, Done. Opening an item opens the workspace for that job. Not a copy of a commercial board: four attention states, coach language on the cards.

**IA.** Home is the four queues. Workspace is a panel (curate, place, topic/briefing, design/sheet/print). Finder/Custom/History are "tools" that create or consume items.

**Journeys**

- Curate/place: card "Volume 1 awaiting curation" -> workspace accept -> card moves; new card "2 citations uncategorized" -> place.
- Topic -> briefing -> system: card "Hip bump sweep (gi) needs a system" -> briefing workspace -> Choose -> card moves to In progress (Design).
- Design -> Draft -> Edit -> print: Design card -> convert -> Edit -> Print; cards land in Done.

**Patterns.** Counts as signifiers. "Needs decision" is only advisor proposals and coach forks (welcome other-ruleset, disagreement set-aside, accept/skip). Workspace shows proposal chrome vs decision chrome.

**Pros.** Best returning-coach scan; store health is unavoidable; scales to many volumes/topics.

**Cons.** Weak spatial model for Design; can feel like chores; first-time coach may not know why a card exists (needs scent on the card title).

**Usability.** High status visibility; efficiency for mixed workdays; learnability depends on card wording.

**Accessibility.** Lists and headings per queue; do not use color of the column as the only state. Keyboard: move from list to workspace without a pointer.

### 9.3 Candidate C — Topic studio

**Prototype:** [`prototypes/ui-ux-redesign/ux-studio.html`](../../prototypes/ui-ux-redesign/ux-studio.html)

**Philosophy.** Object-oriented, direct manipulation, conceptual model "a topic is a place you teach from." Mapping: map marks -> lessons -> class cards -> print pages.

**Paradigm.** Spatial studio. The open topic and Design map occupy the center. Docks: Store (curate/place/finder), Briefing, Sheet, Print. You enter a topic; you do not "go to the Design screen."

**IA.** Two layers: (1) store room when no topic is open; (2) topic studio when one is. Switching topics switches studios. History/Custom hang off the sheet dock.

**Journeys**

- Curate/place: Store dock -> curate volume -> place onto a named move that also appears as a map mark once the topic is open.
- Topic -> briefing -> system: entering the studio opens briefing dock if system is empty (constraint); Choose pins system words under the topic title.
- Design -> Draft -> Edit -> print: map is already center; Convert in the map toolbar; sheet dock shows Draft then Edit; print dock shows the packet.

**Patterns.** Persistent topic title + ruleset + system one-liner. Gap marks (empty system, unpackable map) as figure against the map ground (Gestalt). Advisor proposals as dashed marks; coach-accepted as solid.

**Pros.** Best match to Design-already-spatial; strongest conceptual model for teaching; returning coach re-enters a place.

**Cons.** Cold start with no topic; curation is easy to hide; Fitts: docks far from map center; force-graph accessibility needs a non-pointer equivalent (list of marks).

**Usability.** High efficiency inside a topic; weaker for store-only days. Learnability depends on dock signifiers.

**Accessibility.** Map cannot be the only UI: include a mark list (spec-70 already has `mark-list`). Docks as `aria-expanded` regions. Print CSS remains a separate concern.

### 9.4 How to evaluate (for issue 89)

Walk the same three journeys on all three files, plus a first-time empty path and a returning History path. Score with Nielsen's 10, POUR, and the candidate principles in section 6. Do not score visual polish (issue 87). Do not pick a winner in this ticket.

---

*End of research document. No approach is selected.*
