"""Pack the Design map into a first Draft. Stand in the advisor vendor."""

from __future__ import annotations

from dataclasses import dataclass, replace

from coach_app.briefing import BriefingAdvisor, DisagreementSide
from coach_app.design import DesignSession, sample_tight_waist
from coach_app.placement import citations_for_design_mark, citations_for_lesson
from coach_app.store import Class, Lesson, Unit
from coach_app.topics import same_ruleset_citations


DRAFT_COLUMNS = ("Lesson", "Type", "Target", "What to run")
_DEFAULT_JOB = "Coach fills the partner job."


@dataclass(frozen=True)
class PackedClass:
    class_record: Class
    lessons: tuple[Lesson, ...]


@dataclass(frozen=True)
class Draft:
    unit: Unit
    classes: tuple[PackedClass, ...]
    layout: str = "B"
    editable: bool = False
    columns: tuple[str, ...] = DRAFT_COLUMNS


@dataclass(frozen=True)
class BuildResult:
    paragraph: str
    session: DesignSession
    draft: Draft | None = None


class BuildAdvisor(BriefingAdvisor):
    """Stand-in that fills the canvas and packs glued classes. Does not name a vendor."""

    def design_from_paragraph(self, store, session, paragraph):
        text = (paragraph or "").casefold()
        if "tight waist" not in text and "trilemma" not in text:
            return session
        designed = sample_tight_waist(store)
        return replace(
            designed,
            topic_name=session.topic_name or designed.topic_name,
            topic_ruleset=session.topic_ruleset or designed.topic_ruleset,
            chosen_citations=session.chosen_citations or designed.chosen_citations,
        )

    def isolate_member(self, store, session, member, system) -> bool:
        return (member.name or "").casefold() == "roll-through sweep"

    def partner_job(self, store, session, target, disagreement) -> str:
        return ""


def propose(store, session, paragraph, advisor) -> BuildResult:
    filled = advisor.design_from_paragraph(store, session, paragraph or "")
    draft = _write_draft(store, filled, advisor, paragraph or "")
    return BuildResult(paragraph=paragraph or "", session=filled, draft=draft)


def convert(store, session, advisor) -> BuildResult:
    if not _packable(session):
        return BuildResult(paragraph="", session=session, draft=None)
    draft = _write_draft(store, session, advisor, "")
    return BuildResult(paragraph="", session=session, draft=draft)


def _write_draft(store, session, advisor, paragraph: str) -> Draft:
    unit = store.put_unit(
        Unit(
            topic_name=session.topic_name,
            topic_ruleset=session.topic_ruleset,
            paragraph=paragraph,
        )
    )
    planned = _plan_classes(store, session, advisor)
    packed = []
    for lessons in planned:
        class_record = store.put_class(Class())
        stored = tuple(store.put_lesson(lesson) for lesson in lessons)
        packed.append(PackedClass(class_record=class_record, lessons=stored))
    return Draft(unit=unit, classes=tuple(packed))


def _packable(session) -> bool:
    return any(mark.kind in {"named move", "system"} for mark in session.marks)


def _plan_classes(store, session, advisor) -> tuple[tuple[Lesson, ...], ...]:
    member_ids = _member_ids(store, session)
    homes = _home_marks(store, session, member_ids)
    isolated = _isolated_marks(store, session, advisor, member_ids)
    systems = tuple(mark for mark in session.marks if mark.kind == "system")
    disagreement = _disagreement(store, session, advisor)
    home_lessons = _glue_marks(store, session, advisor, homes, disagreement)
    dilemma_lessons = _glue_marks(
        store, session, advisor, systems, disagreement
    ) + _glue_marks(store, session, advisor, isolated, disagreement)
    if home_lessons and dilemma_lessons:
        return (home_lessons, dilemma_lessons)
    remaining = home_lessons or dilemma_lessons
    if remaining:
        return (remaining,)
    return ()


def _member_ids(store, session) -> set[str]:
    ids: set[str] = set()
    for mark in session.marks:
        if mark.kind != "system":
            continue
        node = store.enrichment_node(mark.target)
        if node is not None:
            ids.update(node.aliases)
    return ids


def _home_marks(store, session, member_ids):
    homes = tuple(
        mark
        for mark in session.marks
        if mark.kind == "named move" and mark.target not in member_ids
    )

    def rank(mark) -> int:
        node = store.enrichment_node(mark.target)
        if node is not None and node.type_of_move == "transition":
            return 0
        return 1

    return tuple(sorted(homes, key=rank))


def _isolated_marks(store, session, advisor, member_ids):
    systems = [
        store.enrichment_node(mark.target)
        for mark in session.marks
        if mark.kind == "system"
    ]
    isolated = []
    for mark in session.marks:
        if mark.kind != "named move" or mark.target not in member_ids:
            continue
        member = store.enrichment_node(mark.target)
        if member is None:
            continue
        for system in systems:
            if system is None or mark.target not in system.aliases:
                continue
            if advisor.isolate_member(store, session, member, system):
                isolated.append(mark)
                break
    return tuple(isolated)


def _glue_marks(store, session, advisor, marks, disagreement) -> tuple[Lesson, ...]:
    lessons: list[Lesson] = []
    for mark in marks:
        citations = _citations_for(store, session, mark)
        job = _drill_job(advisor, store, session, mark.target, citations, disagreement)
        lessons.append(
            Lesson(kind="technique", target=mark.target, citations=citations)
        )
        lessons.append(
            Lesson(
                kind="drill",
                target=mark.target,
                citations=citations,
                partner_job=job,
            )
        )
    return tuple(lessons)


def _citations_for(store, session, mark) -> tuple[str, ...]:
    if mark.kind == "named move":
        chosen = tuple(
            citation_id
            for named_move_id, citation_id in session.chosen_citations
            if named_move_id == mark.target
        )
        if chosen:
            return chosen
        linked = citations_for_design_mark(store, mark.target)
        node = store.enrichment_node(mark.target)
        systems = tuple(
            store.enrichment_node(item.target)
            for item in session.marks
            if item.kind == "system"
        )
        specific = tuple(
            citation
            for citation in linked
            if node is not None and _is_specific(citation, node, systems)
        )
        pool = specific or linked
        return (pool[0].id,) if pool else ()
    linked = citations_for_lesson(store, mark.target)
    system = store.enrichment_node(mark.target)
    preferred = tuple(
        citation
        for citation in linked
        if system is not None and _system_level(citation, system)
    )
    pool = preferred or linked
    return (pool[0].id,) if pool else ()


def _is_specific(citation, named_move, systems) -> bool:
    movement = _folded(citation.movement)
    move_name = _folded(named_move.name)
    if move_name and move_name in movement:
        return True
    for system in systems:
        if system is None or named_move.id not in system.aliases:
            continue
        if _system_level(citation, system):
            return False
    return True


def _system_level(citation, system) -> bool:
    movement = _folded(citation.movement)
    name = _folded(system.name)
    if not movement:
        return False
    if name and name in movement:
        return True
    tokens = name.split()
    distinctive = tokens[-1] if tokens else ""
    return bool(distinctive) and distinctive in movement


def _folded(value: str) -> str:
    return " ".join((value or "").casefold().replace("-", " ").split())


def _disagreement(store, session, advisor) -> tuple[DisagreementSide, ...]:
    fn = getattr(advisor, "disagreeing_sides", None)
    if fn is None or not session.topic_name or not session.topic_ruleset:
        return ()
    topic = store.topic(session.topic_name, session.topic_ruleset)
    if topic is None:
        return ()
    return _as_disagreement(fn(topic, same_ruleset_citations(store, topic)))


def _as_disagreement(sides) -> tuple[DisagreementSide, ...]:
    sides = tuple(sides or ())
    if not sides:
        return ()
    if isinstance(sides[0], DisagreementSide):
        return sides
    if len(sides) < 2:
        return ()
    result = []
    for index, citation in enumerate(sides):
        others = sides[:index] + sides[index + 1 :]
        partner_job = "; ".join(
            _citation_job(other) for other in others if _citation_job(other)
        )
        result.append(DisagreementSide(citation=citation, partner_job=partner_job))
    return tuple(result)


def _citation_job(citation) -> str:
    if citation.step_bullets:
        return "; ".join(citation.step_bullets)
    return citation.cleaned_statement or citation.movement or ""


def _drill_job(advisor, store, session, target_id, citations, disagreement) -> str:
    used = set(citations)
    for side in disagreement:
        if side.citation.id in used and side.partner_job:
            return side.partner_job
    fn = getattr(advisor, "partner_job", None)
    if fn is not None:
        stub = fn(store, session, store.enrichment_node(target_id), disagreement)
        if stub:
            return stub
    return _DEFAULT_JOB
