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
A named series of teaching volumes credited to an instructor.
_Avoid_: DVD, course, video

**Volume**:
One recording inside an instructional. One transcript file is one volume. It is raw until curation admits it to the curated store.
_Avoid_: episode, file

**Chapter**:
A titled time range inside a volume.
_Avoid_: clip, section

**Citation**:
Names the instructor, the instructional, the volume, the chapter, and the movement. The words are the cleaned statement the coach has accepted. Each time the instructor shows a detail of that movement in the chapter has a timestamp and a playback link. The volume is the video.
_Avoid_: clip, quote

**Cleaned statement**:
One statement of a movement. It keeps every detail from each time that instructor shows the movement in the chapter, with names restored to the words the instructor said. The coach accepts it before the advisor may use the citation.
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
The part of the application that reads the curated store and advises the coach. The coach determines the system.
_Avoid_: chatbot, bot, model, language model

**Gi**:
Jiu-jitsu fought in the kimono. A gi topic stays a gi topic.
_Avoid_: "gi or no-gi", kimono jiu-jitsu

**No-gi**:
Jiu-jitsu fought without the kimono. A no-gi topic is a different topic from its gi namesake.
_Avoid_: nogi

**Topic**:
Gi or no-gi work the coach chooses to teach, at the grain the coach names. The coach names it because a student failed it under resistance or because the coach plans to teach it.
_Avoid_: situation, subject, question, debate

**System**:
The coach's own choice of how one topic is taught, one per topic and one unit, and it remains that topic's system after that unit. The instructionals seed it, the coach's own experience is part of the system itself, and an instructor's method can be the whole system when it fits that experience.
_Avoid_: line, style, house game

**System conflict**:
An earlier system of the same ruleset that cannot be taught together with one side of a disagreement.
_Avoid_: debate, contradiction, line conflict

**Disagreement**:
Incompatible instruction from two or more instructors on the same topic. A citation accompanies each side. The coach determines the system.
_Avoid_: debate, conflict

**Cross-ruleset chapter**:
A chapter taught in the other ruleset that may still inform a topic, because some mechanics transfer. It keeps its own ruleset label and carries a caveat. It enters a lesson only when the coach places it there.
_Avoid_: mixed chapter, universal technique

**Caveat**:
The note on a cross-ruleset chapter that says what may transfer and what depends on tools the topic's ruleset does not share.
_Avoid_: disclaimer, warning

**Unit**:
The classes that teach one system through to performance under resistance. A unit can take multiple classes, as when a knee cut takes more than one class to learn.
_Avoid_: course, curriculum, camp

**Class**:
One meeting of students inside a unit. It is made up of lessons, and it can be a single sparring lesson.
_Avoid_: module

**Lesson**:
One part of a class. A lesson is a technique, a drill, sparring, or a game.
_Avoid_: class, module

**Technique**:
A lesson that explains a movement in detail before the students perform it. In the same class, a drill follows, and the partner job challenges the student who performs the technique.
_Avoid_: lecture

**Drill**:
A lesson of regular core movements that students perform with little further instruction against opponents who resist in a predictable way.
_Avoid_: flow roll

**Partner job**:
The predictable resistance the coach sets inside a drill. It starts light and becomes more intense, complex, and dynamic as the drill goes on. A later drill opens harder than an earlier one.
_Avoid_: script, flow roll

**Sparring**:
A lesson of live rounds that can sit anywhere in a class, including as the only lesson. A round can be positional, for points, or until submission.
_Avoid_: rolling, free play

**Scenario**:
Where a positional sparring round starts and restarts. Both people may work what they want inside it.
_Avoid_: situation, game

**Game**:
A sparring lesson that adds a condition on the move or the goal. A positional round, a points round, or a round until submission is sparring.
_Avoid_: situational sparring

**Resistance**:
A partner trying to stop the student. In a drill the partner job sets it. In sparring and in a game the round sets it.
_Avoid_: pressure, rolling
