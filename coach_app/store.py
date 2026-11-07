"""Coach-only curated store. The only source of truth for advising records."""

from __future__ import annotations

from dataclasses import dataclass, replace

from coach_app.enrichment import (
    aliases_of,
    family_of,
    names_from_cross_refs,
    occupancy_for,
    unify_seed,
)


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
    named_move_id: str = ""
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
    family: str = ""
    ruleset: str = ""
    start_id: str = ""
    type_of_move: str = ""
    end_id: str = ""
    start_occupancy: str = ""
    end_occupancy: str = ""
    aliases: tuple[str, ...] = ()
    cross_refs: tuple[str, ...] = ()


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
        self._seed_imported = False

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
        return self._put_identified(self._enrichment_nodes, self._with_occupancy(node))

    def enrichment_node(self, node_id: str) -> EnrichmentNode | None:
        return self._enrichment_nodes.get(node_id)

    def enrichment_nodes(self) -> tuple[EnrichmentNode, ...]:
        return tuple(self._enrichment_nodes.values())

    def import_enrichment_seed(self, seed: dict) -> None:
        if self._seed_imported:
            return
        catalog = unify_seed(seed)
        positions = {item["id"]: item for item in catalog["positions"]}
        submissions = {item["id"]: item for item in catalog["submissions"]}
        for item in catalog["positions"]:
            self.put_enrichment_node(
                EnrichmentNode(
                    kind="position",
                    name=item["label"],
                    id=item["id"],
                    family=item.get("family") or "other",
                    aliases=aliases_of(item),
                    cross_refs=names_from_cross_refs(item),
                )
            )
        for item in catalog["submissions"]:
            self.put_enrichment_node(
                EnrichmentNode(
                    kind="submission",
                    name=item["label"],
                    id=item["id"],
                    aliases=aliases_of(item),
                    cross_refs=names_from_cross_refs(item),
                )
            )
        for item in catalog["move_types"]:
            self.put_enrichment_node(
                EnrichmentNode(
                    kind="type of move",
                    name=item["label"],
                    id=item["id"],
                )
            )
        for path in catalog["paths"]:
            start_family = family_of(positions, path["start"])
            end_id = path["end"]
            end_kind = "submission" if end_id in submissions else "position"
            end_family = family_of(positions, end_id)
            start_side, end_side = occupancy_for(
                path["move_type"], start_family, end_kind, end_family
            )
            for leaf in path.get("leaves") or ():
                self.put_enrichment_node(
                    EnrichmentNode(
                        kind="named move",
                        name=leaf["name"],
                        id=self._named_move_id(
                            path["start"], path["move_type"], end_id, leaf["name"]
                        ),
                        ruleset=leaf.get("ruleset") or "both",
                        start_id=path["start"],
                        type_of_move=path["move_type"],
                        end_id=end_id,
                        start_occupancy=start_side,
                        end_occupancy=end_side,
                        aliases=aliases_of(leaf),
                        cross_refs=names_from_cross_refs(leaf),
                    )
                )
        self._seed_imported = True

    def search_enrichment(self, query: str) -> tuple[EnrichmentNode, ...]:
        needle = query.strip().casefold()
        if not needle:
            return ()
        hits = []
        for node in self._enrichment_nodes.values():
            haystack = " ".join((node.name, *node.aliases, *node.cross_refs)).casefold()
            if needle in haystack:
                hits.append(node)
        return tuple(hits)

    def browse_hierarchy(
        self,
        start: str | None = None,
        type_of_move: str | None = None,
    ) -> tuple[EnrichmentNode, ...]:
        if start is None:
            return tuple(
                node for node in self._enrichment_nodes.values() if node.kind == "position"
            )
        start_id = self._resolve_catalog_id(start, "position")
        named = [
            node
            for node in self._enrichment_nodes.values()
            if node.kind == "named move" and node.start_id == start_id
        ]
        if type_of_move is None:
            type_ids = {node.type_of_move for node in named}
            return tuple(
                node
                for node in self._enrichment_nodes.values()
                if node.kind == "type of move" and node.id in type_ids
            )
        type_id = self._resolve_catalog_id(type_of_move, "type of move")
        end_ids = {
            node.end_id
            for node in named
            if node.type_of_move == type_id
        }
        return tuple(
            node
            for node in self._enrichment_nodes.values()
            if node.id in end_ids and node.kind in {"position", "submission"}
        )

    def rename_enrichment_node(self, node_id: str, name: str) -> EnrichmentNode:
        node = self._enrichment_nodes[node_id]
        renamed = replace(node, name=name)
        self._enrichment_nodes[node_id] = renamed
        return renamed

    def move_enrichment_node(
        self,
        node_id: str,
        start_id: str,
        type_of_move: str,
        end_id: str,
    ) -> EnrichmentNode:
        node = self._enrichment_nodes[node_id]
        type_id = self._resolve_catalog_id(type_of_move, "type of move")
        moved = replace(
            node,
            start_id=self._resolve_catalog_id(start_id, "position"),
            type_of_move=type_id,
            end_id=end_id,
            start_occupancy="",
            end_occupancy="",
        )
        moved = self._with_occupancy(moved)
        self._enrichment_nodes[node_id] = moved
        return moved

    def delete_enrichment_node(self, node_id: str) -> None:
        node = self._enrichment_nodes.pop(node_id, None)
        if node is None:
            return
        dropped = {node_id}
        if node.kind != "named move":
            for other in list(self._enrichment_nodes.values()):
                if other.kind != "named move":
                    continue
                depends = (
                    (node.kind == "position" and node_id in {other.start_id, other.end_id})
                    or (node.kind == "type of move" and other.type_of_move == node_id)
                    or (node.kind == "submission" and other.end_id == node_id)
                )
                if depends:
                    dropped.add(other.id)
                    self._enrichment_nodes.pop(other.id, None)
        for citation in list(self._citations.values()):
            if citation.named_move_id in dropped:
                self._citations[citation.id] = replace(citation, named_move_id="")

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

    def _named_move_id(self, start_id: str, type_of_move: str, end_id: str, name: str) -> str:
        slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in name).strip("-")
        return f"{start_id}/{type_of_move}/{end_id}/{slug}"

    def _resolve_catalog_id(self, value: str, kind: str) -> str:
        node = self._enrichment_nodes.get(value)
        if node and node.kind == kind:
            return node.id
        for node in self._enrichment_nodes.values():
            if node.kind == kind and node.name.casefold() == value.casefold():
                return node.id
        return value

    def _with_occupancy(self, node: EnrichmentNode) -> EnrichmentNode:
        if node.kind != "named move":
            return node
        end_kind = self._end_kind(node.end_id)
        if node.start_occupancy and (node.end_occupancy or end_kind == "submission"):
            return node
        start = self._enrichment_nodes.get(node.start_id)
        start_family = start.family if start else "other"
        end = self._enrichment_nodes.get(node.end_id)
        end_family = end.family if end and end_kind == "position" else "other"
        start_side, end_side = occupancy_for(
            node.type_of_move, start_family, end_kind, end_family
        )
        return replace(
            node,
            start_occupancy=node.start_occupancy or start_side,
            end_occupancy=node.end_occupancy or end_side,
        )

    def _end_kind(self, end_id: str) -> str:
        end = self._enrichment_nodes.get(end_id)
        if end:
            return end.kind
        return "position"
