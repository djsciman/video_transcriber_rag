"""Coach-only curated store. The only source of truth for advising records."""

from __future__ import annotations

from dataclasses import dataclass, replace


@dataclass(frozen=True)
class Instructional:
    instructor: str
    name: str
    ruleset: str


@dataclass(frozen=True)
class Volume:
    instructional: str
    video_file_name: str


@dataclass(frozen=True)
class Showing:
    timestamp: float
    playback_link: str | None = None


@dataclass(frozen=True)
class Citation:
    movement: str
    instructor: str | None = None
    instructional: str | None = None
    volume: str | None = None
    chapter: str | None = None
    cleaned_statement: str | None = None
    step_bullets: tuple[str, ...] = ()
    showings: tuple[Showing, ...] = ()
    id: str = ""


@dataclass(frozen=True)
class Topic:
    name: str
    ruleset: str
    system: str = ""


@dataclass(frozen=True)
class OtherRulesetChoice:
    topic_name: str
    topic_ruleset: str
    instructional: str
    yes: bool


@dataclass(frozen=True)
class SetAside:
    topic_name: str
    topic_ruleset: str
    earlier_topic_name: str
    earlier_topic_ruleset: str


@dataclass(frozen=True)
class EnrichmentNode:
    kind: str
    name: str
    id: str = ""


@dataclass(frozen=True)
class Unit:
    topic_name: str
    topic_ruleset: str
    paragraph: str = ""
    id: str = ""


@dataclass(frozen=True)
class Class:
    purpose: str = ""
    id: str = ""


@dataclass(frozen=True)
class Lesson:
    kind: str
    target: str = ""
    citations: tuple[str, ...] = ()
    partner_job: str = ""
    scenario: str = ""
    condition: str = ""
    id: str = ""


@dataclass(frozen=True)
class CustomLesson:
    lesson: Lesson
    id: str = ""


@dataclass(frozen=True)
class UnitHistory:
    unit: Unit
    id: str = ""


class CuratedStore:
    """Local records the coach writes and the advisor later reads."""

    def __init__(self) -> None:
        self._instructionals: dict[str, Instructional] = {}
        self._volumes: dict[tuple[str, str], Volume] = {}
        self._citations: dict[str, Citation] = {}
        self._topics: dict[tuple[str, str], Topic] = {}
        self._other_ruleset: dict[tuple[str, str, str], OtherRulesetChoice] = {}
        self._set_asides: dict[tuple[str, str, str, str], SetAside] = {}
        self._enrichment_nodes: dict[str, EnrichmentNode] = {}
        self._units: dict[str, Unit] = {}
        self._classes: dict[str, Class] = {}
        self._lessons: dict[str, Lesson] = {}
        self._custom_lessons: dict[str, CustomLesson] = {}
        self._unit_histories: dict[str, UnitHistory] = {}
        self._next_id = 1

    def put_instructional(self, instructional: Instructional) -> Instructional:
        self._instructionals[instructional.name] = instructional
        return instructional

    def instructional(self, name: str) -> Instructional | None:
        return self._instructionals.get(name)

    def instructionals(self) -> tuple[Instructional, ...]:
        return tuple(self._instructionals.values())

    def put_volume(self, volume: Volume) -> Volume:
        self._volumes[(volume.instructional, volume.video_file_name)] = volume
        return volume

    def volume(self, instructional: str, video_file_name: str) -> Volume | None:
        return self._volumes.get((instructional, video_file_name))

    def volumes(self) -> tuple[Volume, ...]:
        return tuple(self._volumes.values())

    def put_citation(self, citation: Citation) -> Citation:
        return self._put_identified(self._citations, citation)

    def citation(self, citation_id: str) -> Citation | None:
        return self._citations.get(citation_id)

    def citations(self) -> tuple[Citation, ...]:
        return tuple(self._citations.values())

    def put_topic(self, topic: Topic) -> Topic:
        self._topics[(topic.name, topic.ruleset)] = topic
        return topic

    def topic(self, name: str, ruleset: str) -> Topic | None:
        return self._topics.get((name, ruleset))

    def topics(self) -> tuple[Topic, ...]:
        return tuple(self._topics.values())

    def put_other_ruleset_choice(
        self, choice: OtherRulesetChoice
    ) -> OtherRulesetChoice:
        key = (choice.topic_name, choice.topic_ruleset, choice.instructional)
        self._other_ruleset[key] = choice
        return choice

    def other_ruleset_choice(
        self, topic_name: str, topic_ruleset: str, instructional: str
    ) -> OtherRulesetChoice | None:
        return self._other_ruleset.get((topic_name, topic_ruleset, instructional))

    def put_set_aside(self, set_aside: SetAside) -> SetAside:
        key = (
            set_aside.topic_name,
            set_aside.topic_ruleset,
            set_aside.earlier_topic_name,
            set_aside.earlier_topic_ruleset,
        )
        self._set_asides[key] = set_aside
        return set_aside

    def set_asides(self, topic_name: str, topic_ruleset: str) -> tuple[SetAside, ...]:
        return tuple(
            record
            for (name, ruleset, *_rest), record in self._set_asides.items()
            if name == topic_name and ruleset == topic_ruleset
        )

    def put_enrichment_node(self, node: EnrichmentNode) -> EnrichmentNode:
        return self._put_identified(self._enrichment_nodes, node)

    def enrichment_node(self, node_id: str) -> EnrichmentNode | None:
        return self._enrichment_nodes.get(node_id)

    def enrichment_nodes(self) -> tuple[EnrichmentNode, ...]:
        return tuple(self._enrichment_nodes.values())

    def put_unit(self, unit: Unit) -> Unit:
        return self._put_identified(self._units, unit)

    def unit(self, unit_id: str) -> Unit | None:
        return self._units.get(unit_id)

    def units(self) -> tuple[Unit, ...]:
        return tuple(self._units.values())

    def put_class(self, class_record: Class) -> Class:
        return self._put_identified(self._classes, class_record)

    def class_record(self, class_id: str) -> Class | None:
        return self._classes.get(class_id)

    def classes(self) -> tuple[Class, ...]:
        return tuple(self._classes.values())

    def put_lesson(self, lesson: Lesson) -> Lesson:
        return self._put_identified(self._lessons, lesson)

    def lesson(self, lesson_id: str) -> Lesson | None:
        return self._lessons.get(lesson_id)

    def lessons(self) -> tuple[Lesson, ...]:
        return tuple(self._lessons.values())

    def put_custom_lesson(self, custom_lesson: CustomLesson) -> CustomLesson:
        return self._put_identified(self._custom_lessons, custom_lesson)

    def custom_lesson(self, custom_id: str) -> CustomLesson | None:
        return self._custom_lessons.get(custom_id)

    def custom_lessons(self) -> tuple[CustomLesson, ...]:
        return tuple(self._custom_lessons.values())

    def put_unit_history(self, history: UnitHistory) -> UnitHistory:
        return self._put_identified(self._unit_histories, history)

    def unit_history(self, history_id: str) -> UnitHistory | None:
        return self._unit_histories.get(history_id)

    def unit_histories(self) -> tuple[UnitHistory, ...]:
        return tuple(self._unit_histories.values())

    def _put_identified(self, bag: dict[str, object], record):
        stored = record if record.id else replace(record, id=self._allocate_id())
        bag[stored.id] = stored
        return stored

    def _allocate_id(self) -> str:
        allocated = str(self._next_id)
        self._next_id += 1
        return allocated
