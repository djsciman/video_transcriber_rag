"""Custom library and unit history. Save on place; copies go through the store."""

from __future__ import annotations

from dataclasses import dataclass, replace

from coach_app.store import CustomLesson, Lesson, PackedClass, UnitHistory, system_members


@dataclass(frozen=True)
class AddLessonSources:
    custom: tuple[CustomLesson, ...]
    search: tuple[object, ...]
    hierarchy: tuple[object, ...]
    map_moves: tuple[str, ...]


def place_lesson(
    store,
    sheet,
    lesson: Lesson,
    *,
    class_index=None,
    index=None,
    glued: Lesson | None = None,
):
    from coach_app.edit import add_lesson

    placed = add_lesson(
        store, sheet, lesson, class_index=class_index, index=index, glued=glued
    )
    return _apply_glued(store, sheet, placed, lesson, glued)


def pull_custom(store, custom_id: str) -> tuple[Lesson, ...]:
    custom = store.custom_lesson(custom_id)
    source = replace(custom.lesson, id="")
    if source.kind != "technique":
        return (source,)
    drill = Lesson(
        kind="drill",
        target=source.target,
        citations=source.citations,
        partner_job=source.partner_job,
    )
    return (replace(source, partner_job=""), drill)


def create_custom(store, lesson: Lesson, glued: Lesson | None = None) -> CustomLesson:
    return store.put_custom_lesson(CustomLesson(lesson=_snapshot(lesson, glued)))


def edit_custom(
    store,
    custom_id: str,
    lesson: Lesson,
    glued: Lesson | None = None,
) -> CustomLesson:
    return store.put_custom_lesson(
        CustomLesson(id=custom_id, lesson=_snapshot(lesson, glued))
    )


def delete_custom(store, custom_id: str) -> None:
    store.delete_custom_lesson(custom_id)


def search_library(
    store,
    *,
    position: str = "",
    sweep: str = "",
    submission: str = "",
    instructor: str = "",
    ruleset: str = "",
    query: str = "",
) -> tuple[object, ...]:
    hits: list[object] = []
    for node in store.enrichment_nodes():
        if node.kind != "named move":
            continue
        if _matches_dimensions(
            store,
            node,
            position=position,
            sweep=sweep,
            submission=submission,
            instructor=instructor,
            ruleset=ruleset,
            query=query,
        ):
            hits.append(node)
    for custom in store.custom_lessons():
        target = store.enrichment_node(custom.lesson.target) if custom.lesson.target else None
        if target is None or target.kind != "named move":
            continue
        if _matches_dimensions(
            store,
            target,
            position=position,
            sweep=sweep,
            submission=submission,
            instructor=instructor,
            ruleset=ruleset,
            query=query,
        ):
            hits.append(custom)
    return tuple(hits)


def browse_library(
    store,
    start: str | None = None,
    type_of_move: str | None = None,
    end: str | None = None,
) -> tuple[object, ...]:
    if end is None:
        return store.browse_hierarchy(start, type_of_move)
    start_id = _catalog_id(store, start, "position")
    type_id = _catalog_id(store, type_of_move, "type of move")
    end_id = _catalog_id(store, end)
    named = [
        node
        for node in store.enrichment_nodes()
        if node.kind == "named move"
        and node.start_id == start_id
        and node.type_of_move == type_id
        and node.end_id == end_id
    ]
    named_ids = {node.id for node in named}
    systems = [
        node
        for node in store.enrichment_nodes()
        if node.kind == "system" and named_ids.intersection(system_members(node))
    ]
    targets = named_ids | {node.id for node in systems}
    customs = [
        custom
        for custom in store.custom_lessons()
        if custom.lesson.target in targets
    ]
    return tuple(named) + tuple(systems) + tuple(customs)


def named_moves_on_map(session) -> tuple[str, ...]:
    if session is None:
        return ()
    return tuple(
        mark.target
        for mark in session.marks
        if mark.kind in {"named move", "system"}
    )


def add_lesson_sources(store, session=None, **filters) -> AddLessonSources:
    browse = {
        key: filters[key]
        for key in ("start", "type_of_move", "end")
        if key in filters and filters[key] is not None
    }
    search = {
        key: value
        for key, value in filters.items()
        if key not in {"start", "type_of_move", "end"}
    }
    return AddLessonSources(
        custom=tuple(store.custom_lessons()),
        search=search_library(store, **search),
        hierarchy=browse_library(store, **browse),
        map_moves=named_moves_on_map(session),
    )


def save_history(store, sheet) -> UnitHistory:
    return store.put_unit_history(
        UnitHistory(
            unit=sheet.unit,
            classes=tuple(
                PackedClass(class_record=item.class_record, lessons=item.lessons)
                for item in sheet.classes
            ),
        )
    )


def copy_history(store, history_id: str):
    from coach_app.edit import Sheet

    history = store.unit_history(history_id)
    unit = store.put_unit(replace(history.unit, id=""))
    packed = []
    for item in history.classes:
        class_record = store.put_class(
            replace(item.class_record, id="", unit_id=unit.id)
        )
        lessons = tuple(
            store.put_lesson(replace(lesson, id="", class_id=class_record.id))
            for lesson in item.lessons
        )
        packed.append(PackedClass(class_record=class_record, lessons=lessons))
    return Sheet(
        unit=unit,
        classes=tuple(packed),
        mode="edit",
        editable=True,
    )


def _snapshot(lesson: Lesson, glued: Lesson | None = None) -> Lesson:
    job = glued.partner_job if glued is not None else lesson.partner_job
    return replace(lesson, id="", partner_job=job)


def _apply_glued(store, before, after, lesson: Lesson, glued: Lesson | None):
    job = glued.partner_job if glued is not None else lesson.partner_job
    if lesson.kind != "technique" or not job:
        return after
    before_ids = {
        item.id for packed in before.classes for item in packed.lessons
    }
    for packed in after.classes:
        for item in packed.lessons:
            if item.id in before_ids or item.kind != "drill":
                continue
            if item.target != lesson.target:
                continue
            updated = store.put_lesson(
                replace(item, partner_job=job, citations=lesson.citations)
            )
            return _with_lesson(after, updated)
    return after


def _with_lesson(sheet, lesson: Lesson):
    classes = []
    for packed in sheet.classes:
        lessons = tuple(
            lesson if item.id == lesson.id else item for item in packed.lessons
        )
        classes.append(
            PackedClass(class_record=packed.class_record, lessons=lessons)
        )
    return replace(sheet, classes=tuple(classes))


def _matches_dimensions(
    store,
    node,
    *,
    position: str,
    sweep: str,
    submission: str,
    instructor: str,
    ruleset: str,
    query: str,
) -> bool:
    start = store.enrichment_node(node.start_id)
    end = store.enrichment_node(node.end_id)
    move_type = store.enrichment_node(node.type_of_move)
    if position:
        names = " ".join(item.name for item in (start, end) if item is not None)
        if position.casefold() not in names.casefold():
            return False
    if sweep:
        type_name = move_type.name if move_type is not None else node.type_of_move
        needle = sweep.casefold()
        if needle not in type_name.casefold() and needle != node.type_of_move.casefold():
            return False
    if submission:
        needle = submission.casefold()
        type_name = move_type.name if move_type is not None else node.type_of_move
        end_name = end.name if end is not None else ""
        is_submission = (
            (end is not None and end.kind == "submission")
            or type_name.casefold() == "submission"
            or node.type_of_move.casefold() == "submission"
        )
        if needle in {"submission", "true", "1"}:
            if not is_submission:
                return False
        elif needle not in end_name.casefold() and needle not in node.name.casefold():
            return False
    if instructor:
        cites = [
            citation
            for citation in store.citations()
            if citation.named_move_id == node.id
        ]
        if not any(
            instructor.casefold() in (citation.instructor or "").casefold()
            for citation in cites
        ):
            return False
    if ruleset and not _ruleset_matches(store, node, ruleset):
        return False
    if query:
        hay = " ".join((node.name, *node.aliases, *node.cross_refs)).casefold()
        if query.casefold() not in hay:
            return False
    return True


def _ruleset_matches(store, node, ruleset: str) -> bool:
    wanted = ruleset.casefold()
    node_ruleset = (node.ruleset or "").casefold()
    if node_ruleset in {wanted, "both", ""}:
        if node_ruleset in {wanted, "both"}:
            return True
    for citation in store.citations():
        if citation.named_move_id != node.id or not citation.instructional:
            continue
        instructional = store.instructional(citation.instructional)
        if instructional and instructional.ruleset.casefold() == wanted:
            return True
    return node_ruleset in {wanted, "both"}


def _catalog_id(store, value: str | None, kind: str | None = None) -> str:
    if not value:
        return ""
    node = store.enrichment_node(value)
    if node is not None and (kind is None or node.kind == kind):
        return node.id
    for node in store.enrichment_nodes():
        if kind is not None and node.kind != kind:
            continue
        if node.name.casefold() == value.casefold() or node.id.casefold() == value.casefold():
            return node.id
    return value
