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
A catalog teaching that belongs to a named move. A corpus citation names the instructor, the instructional, the volume, the chapter, and the movement; its words are the cleaned statement the coach has accepted; each showing in that chapter has a timestamp and a playback link; the volume is the video. A coach-authored citation is written by the coach from their own knowledge as a movement name and step bullets, with no instructional, volume, chapter, or playback link. Many citations can belong to one named move. With no named-move link it stays in the catalog under uncategorized and is not offered on a lesson. When the coach changes the move name on a corpus citation's cleaned statement, the movement name on that citation updates with that edit. The coach may remove an accepted citation from the curated store.
_Avoid_: clip, quote

**Cleaned statement**:
One statement of a movement, written from the speech, keeping every spoken detail from each showing in the chapter, with names restored to the words the instructor said. A detail the instructor shows and does not say stays out, and the coach accepts the statement before the advisor may use the citation. The coach may correct those words before accept and after accept; after accept the curated store replaces the statement and keeps no earlier version. Cleaned statements belong to corpus citations only.
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
The records kept on the coach's machine for advising and hand-build, including enrichment nodes. A raw volume is not among them until it passes curation.
_Avoid_: database, knowledge graph, vector store

**Advisor**:
The part of the application that reads the curated store and advises the coach. It selects citations from that store, proposes enrichment-node placements for new citations, uses the playback link path for the coach to watch corpus video, and leaves the system to the coach.
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
Two or more named moves used together to create a dilemma. When the partner defends one, they give another. A lesson may connect to one system. The coach also chooses a system as how one topic is taught, one per topic; that choice stays on the topic after the unit. Aliases are other names for the same system.
_Avoid_: sequence, complement, line, style, house game

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
The classes that teach one topic through to performance under resistance. Catalog enters through lessons; the unit sequences those lessons into classes. It carries a paragraph in the coach's words used as an advisor build prompt or as a descriptor while the coach builds by hand. It keeps a history of saved states; the coach can copy a past state into a new editable unit. There is no maximum number of classes.
_Avoid_: course, curriculum, camp

**Class**:
One meeting of students inside a unit. It has a short purpose line, which may be empty, and an ordered list of lessons. It always has at least one lesson and may have no technique lesson. The coach packs lessons into classes; any lesson type may open a class.
_Avoid_: module

**Lesson**:
One part of a class: a technique, a drill, sparring, or a game. It connects to exactly one named move or exactly one system. While building it, the coach chooses which citations of that target to use in the instruction.
_Avoid_: class, module

**Technique**:
A lesson that explains a movement in detail before the students perform it. In the same class, its drill follows with nothing between them, and the partner job challenges the student who performs the technique.
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
A lesson saved from a unit, or created in the Custom library, that the coach can pull into a unit through search or hierarchy browse under Custom. Hierarchy shows it through the named move or system the lesson connects to.
_Avoid_: template, favorite, snippet

**Enrichment**:
The catalog of finder records kept with the curated store: positions, types of move, submissions, named moves, and systems. The tree starts from a one-time consensus seed from open public sources; the coach then adds, renames, moves, and deletes nodes on the live copy. Enrichment does not hold lesson fields.
_Avoid_: scrape, ontology import, knowledge graph

**Position**:
One catalog record for where a named move starts or ends. Family is a field. Top, bottom, or neutral is how the student occupies it on a named move, not a second position record.
_Avoid_: starting-position list, ending-position list

**Type of move**:
What a named move accomplishes (takedown, sweep, pass, escape, submission, transition, or back take), carrying top, bottom, and/or neutral. Escape is bottom on a pin or control; pass is top; sweep is bottom; takedown is neutral; transition stays the same side and family.
_Avoid_: category, path level

**Named move**:
One catalog movement such as Hip bump sweep. It consists of a start position plus top, bottom, or neutral; a type of move; and an end (a position plus top, bottom, or neutral, or a submission). Citations belong here. A lesson may connect here.
_Avoid_: path, leaf, sequence

**Submission**:
A catalog finishing hold. A named move may end here. It is not a position.
_Avoid_: tap as a position

**Uncategorized**:
The hierarchy-browse bucket for citations that have no named-move link. Those citations are not offered on a lesson until they belong to a named move.
_Avoid_: unsorted, misc, other

**Resistance**:
A partner trying to stop the student. In a drill the partner job sets it. In sparring and in a game the round sets it.
_Avoid_: pressure, rolling
