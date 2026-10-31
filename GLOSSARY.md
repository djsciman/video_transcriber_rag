# Coaching from instructionals

Language for the coach who uses transcribed BJJ instructionals to teach one topic through to performance under resistance.

## Language

**Coach**:
The person who decides what a student trains and how. The only person who uses this application.
_Avoid_: user, instructor

**Instructor**:
The person who teaches on an instructional.
_Avoid_: coach

**Student**:
A person the coach trains. A student does not use this application.
_Avoid_: user, athlete

**Instructional**:
A named series of teaching volumes credited to an instructor. The series is gi or no-gi as a whole.
_Avoid_: DVD, course, video, mixed series

**Volume**:
One recording inside an instructional. One transcript file is one volume. It is raw until curation admits it to the curated store.
_Avoid_: episode, file

**Chapter**:
A titled time range inside a volume.
_Avoid_: clip, section

**Citation**:
Names the instructor, the instructional, the volume, the chapter, and the movement. The words are the cleaned statement the coach has accepted. Each time the instructor shows a detail of that movement in the chapter has a timestamp and a playback link. The volume is the video. When the coach changes the move name in the cleaned statement, the movement name on the citation updates with that edit. The coach may remove an accepted citation from the curated store.
_Avoid_: clip, quote

**Cleaned statement**:
One statement of a movement, written from the speech, keeping every spoken detail from each showing in the chapter, with names restored to the words the instructor said. A detail the instructor shows and does not say stays out, and the coach accepts the statement before the advisor may use the citation. The coach may correct those words before accept and after accept; after accept the curated store replaces the statement and keeps no earlier version.
_Avoid_: transcript, quote

**Playback link**:
A link on a citation that opens that volume's video file at the second when that showing's own speech begins. When that file is not available, the citation still enters the curated store. The timestamp and the volume, including that volume's video file name, let the coach find the video.
_Avoid_: url, deep link

**Corpus**:
The instructionals transcribed for the coach. A volume is in the corpus as soon as it is transcribed, including while it is still raw, and it reaches the curated store only after curation.
_Avoid_: library, dataset, knowledge base

**Application**:
The coach-only program this spec defines. It curates raw volumes and advises the coach on a topic.
_Avoid_: tool, chatbot, product

**Curated store**:
The records the advisor is allowed to read. A raw volume is not among them until it passes curation.
_Avoid_: database, knowledge graph, vector store

**Advisor**:
The part of the application that reads the curated store and advises the coach. It is given that store only, the coach uses the playback link to watch the video, and the coach determines the system.
_Avoid_: chatbot, bot, model, language model

**Gi**:
Jiu-jitsu fought in the kimono. A gi topic stays a gi topic.
_Avoid_: "gi or no-gi", kimono jiu-jitsu

**No-gi**:
Jiu-jitsu fought without the kimono. A no-gi topic is a different topic from its gi namesake.
_Avoid_: nogi

**Topic**:
Gi or no-gi work the coach chooses to teach, at the grain the coach names, because a student failed it under resistance or because the coach plans to teach it. The same ruleset and the same name, with trailing spaces removed, are one topic, and any other characters are another topic. Once open, the name and the ruleset stay fixed. The coach can remove a topic at any time; remove clears what belonged to that topic; the same ruleset and the same name can open again.
_Avoid_: situation, subject, question, debate

**System**:
The coach's own choice of how one topic is taught, one per topic and one unit, and it remains that topic's system after that unit. The instructionals seed it, the coach's own experience is part of the system itself, and an instructor's method can be the whole system when it fits that experience.
_Avoid_: line, style, house game

**System conflict**:
An earlier system of the same ruleset that a student cannot follow together with one side of a disagreement.
_Avoid_: debate, contradiction, line conflict

**Set-aside**:
The coach's choice that one earlier system stays off one topic until the coach shows that system on that topic again.
_Avoid_: dismissal

**Disagreement**:
Incompatible instruction from two or more instructors on the same topic. A citation accompanies each side. The coach determines the system.
_Avoid_: debate, conflict

**Other-ruleset variant**:
A showing of a movement, inside an instructional of one ruleset, where the instructor briefly shows that movement for the other ruleset. The coach marks it on the citation, it carries a caveat, and it enters a lesson only when the coach places it there.
_Avoid_: cross-ruleset chapter, mixed chapter, universal technique

**Caveat**:
The note that says what may transfer and what depends on tools the topic's ruleset does not share. On an other-ruleset variant, the note sits on that showing. When the coach chooses yes for an instructional of the other ruleset, the note sits on that yes, and each citation from that instructional uses it for the topic.
_Avoid_: disclaimer, warning

**Unit**:
The classes that teach one system through to performance under resistance. It carries a paragraph in the coach's words used as an advisor build prompt or as a descriptor while the coach builds by hand. It keeps a history of saved states; the coach can copy a past state into a new editable unit. There is no maximum number of classes.
_Avoid_: course, curriculum, camp

**Class**:
One meeting of students inside a unit. It has a short purpose line, which may be empty, and an ordered list of lessons. It always has at least one lesson and may have no technique lesson. The coach packs lessons into classes; any lesson type may open a class.
_Avoid_: module

**Lesson**:
One part of a class. A lesson is a technique, a drill, sparring, or a game.
_Avoid_: class, module

**Technique**:
A lesson that explains a movement in detail before the students perform it. It carries the citations the coach placed for that movement. In the same class, its drill follows with nothing between them, and the partner job challenges the student who performs the technique.
_Avoid_: lecture

**Drill**:
A lesson of regular core movements that students perform with little further instruction against opponents who resist in a predictable way. It carries the partner job as text. A drill may sit in a class with no technique ahead of it.
_Avoid_: flow roll

**Partner job**:
The predictable resistance the coach sets inside a drill. It starts light and becomes more intense, complex, and dynamic as the drill goes on. A later drill opens harder than an earlier one.
_Avoid_: script, flow roll

**Sparring**:
A lesson of live rounds that can sit anywhere in a class, including as the only lesson. It carries the scenario in the coach's words. A round can be positional, for points, or until submission.
_Avoid_: rolling, free play

**Scenario**:
Where a positional sparring round starts and restarts. Both people may work what they want inside it.
_Avoid_: situation, game

**Game**:
A sparring lesson that adds a condition on the move or the goal. It carries that condition in the coach's words. A positional round, a points round, or a round until submission is sparring.
_Avoid_: situational sparring

**Custom lesson**:
A lesson saved from a unit, or created in the Custom library, that the coach can pull into a unit through search or hierarchy browse under Custom.
_Avoid_: template, favorite, snippet

**Enrichment**:
Material from outside the corpus that fills hierarchy and search nodes the transcripts never name.
_Avoid_: scrape, ontology import

**Resistance**:
A partner trying to stop the student. In a drill the partner job sets it. In sparring and in a game the round sets it.
_Avoid_: pressure, rolling
