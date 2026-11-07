"""Read and Edit modes of the class-card sheet. Draft stays the no-edit proposal."""

from __future__ import annotations

from dataclasses import dataclass, replace

from coach_app.build import DRAFT_COLUMNS, PackedClass
from coach_app.store import Class, Lesson


@dataclass(frozen=True)
class Sheet:
    unit: object
    classes: tuple[PackedClass, ...]
    mode: str
    layout: str = "B"
    columns: tuple[str, ...] = DRAFT_COLUMNS
    editable: bool = False


@dataclass(frozen=True)
class LessonCard:
    lesson: Lesson
    kind: str
    target: str
    what_to_run: tuple[str, ...]
    glued: bool = False


def open_sheet(store, draft, mode="read") -> Sheet:
    key = _mode(mode)
    return Sheet(
        unit=draft.unit,
        classes=draft.classes,
        mode=key,
        layout=getattr(draft, "layout", "B"),
        columns=tuple(getattr(draft, "columns", DRAFT_COLUMNS)),
        editable=key == "edit",
    )


def set_mode(sheet: Sheet, mode: str) -> Sheet:
    key = _mode(mode)
    return replace(sheet, mode=key, editable=key == "edit")


def class_cards(store, sheet: Sheet) -> tuple[tuple[LessonCard, ...], ...]:
    rows = []
    for packed in sheet.classes:
        cards = []
        lessons = packed.lessons
        for index, lesson in enumerate(lessons):
            start, end = _block(lessons, index)
            cards.append(
                LessonCard(
                    lesson=lesson,
                    kind=lesson.kind,
                    target=_target_name(store, lesson.target),
                    what_to_run=_what_to_run(store, lesson),
                    glued=start != end,
                )
            )
        rows.append(tuple(cards))
    return tuple(rows)


def add_lesson(store, sheet: Sheet, lesson: Lesson, *, class_index=None, index=None) -> Sheet:
    _require_edit(sheet)
    stored = [store.put_lesson(lesson)]
    if lesson.kind == "technique":
        stored.append(
            store.put_lesson(
                Lesson(
                    kind="drill",
                    target=lesson.target,
                    citations=lesson.citations,
                )
            )
        )
    if class_index is None or class_index == len(sheet.classes):
        packed = PackedClass(
            class_record=store.put_class(Class()),
            lessons=tuple(stored),
        )
        return replace(sheet, classes=sheet.classes + (packed,))
    if class_index < 0 or class_index >= len(sheet.classes):
        raise ValueError("Class is not on the sheet.")
    current = sheet.classes[class_index]
    lessons = list(current.lessons)
    at = len(lessons) if index is None else index
    at = max(0, min(at, len(lessons)))
    if at < len(lessons):
        start, end = _block(lessons, at)
        if start < at <= end:
            at = end + 1
    lessons[at:at] = stored
    classes = list(sheet.classes)
    classes[class_index] = PackedClass(
        class_record=current.class_record,
        lessons=tuple(lessons),
    )
    return replace(sheet, classes=tuple(classes))


def remove_lesson(store, sheet: Sheet, lesson_id: str) -> Sheet:
    _require_edit(sheet)
    located = _locate(sheet, lesson_id)
    if located is None:
        raise ValueError("Lesson is not on the sheet.")
    class_index, lesson_index = located
    bags, records = _bags(sheet)
    start, end = _block(bags[class_index], lesson_index)
    del bags[class_index][start : end + 1]
    if not bags[class_index]:
        if len(bags) == 1:
            raise ValueError("A class always has at least one lesson.")
        del bags[class_index]
        del records[class_index]
    return _sheet_from_bags(sheet, records, bags)


def drag_lesson(store, sheet: Sheet, lesson_id: str, *, class_index, index) -> Sheet:
    _require_edit(sheet)
    located = _locate(sheet, lesson_id)
    if located is None:
        raise ValueError("Lesson is not on the sheet.")
    from_ci, from_li = located
    bags, records = _bags(sheet)
    start, end = _block(bags[from_ci], from_li)
    chunk = bags[from_ci][start : end + 1]
    opening = class_index == len(bags)
    to_ci = class_index
    if opening:
        to_li = 0
    else:
        if to_ci < 0 or to_ci >= len(bags):
            raise ValueError("Class is not on the sheet.")
        dest = bags[to_ci]
        to_li = len(dest) if index is None else index
        to_li = max(0, min(to_li, len(dest)))
        if to_li < len(dest):
            to_li, _ = _block(dest, to_li)
        if from_ci == to_ci and (to_li == start or to_li == end + 1):
            return sheet
    del bags[from_ci][start : end + 1]
    if not opening and from_ci == to_ci and to_li > start:
        to_li -= len(chunk)
    if not bags[from_ci]:
        remaining = len(bags) - 1 + (1 if opening else 0)
        if remaining == 0:
            raise ValueError("A class always has at least one lesson.")
        del bags[from_ci]
        del records[from_ci]
        if not opening and to_ci > from_ci:
            to_ci -= 1
    if opening:
        records.append(store.put_class(Class()))
        bags.append(list(chunk))
    else:
        dest = bags[to_ci]
        bags[to_ci] = dest[:to_li] + list(chunk) + dest[to_li:]
    return _sheet_from_bags(sheet, records, bags)


def set_purpose(store, sheet: Sheet, class_index: int, purpose: str) -> Sheet:
    _require_edit(sheet)
    packed = sheet.classes[class_index]
    updated = store.put_class(replace(packed.class_record, purpose=purpose))
    classes = list(sheet.classes)
    classes[class_index] = PackedClass(
        class_record=updated,
        lessons=packed.lessons,
    )
    return replace(sheet, classes=tuple(classes))


def _mode(mode: str) -> str:
    key = str(mode or "").casefold()
    if key not in {"read", "edit"}:
        raise ValueError("Read and Edit are the sheet modes.")
    return key


def _require_edit(sheet: Sheet) -> None:
    if sheet.mode != "edit":
        raise ValueError("Packing happens in Edit.")


def _locate(sheet: Sheet, lesson_id: str):
    for class_index, packed in enumerate(sheet.classes):
        for lesson_index, lesson in enumerate(packed.lessons):
            if lesson.id == lesson_id:
                return class_index, lesson_index
    return None


def _block(lessons, index: int) -> tuple[int, int]:
    lesson = lessons[index]
    nxt = lessons[index + 1] if index + 1 < len(lessons) else None
    if (
        lesson.kind == "technique"
        and nxt is not None
        and nxt.kind == "drill"
        and nxt.target == lesson.target
    ):
        return index, index + 1
    prev = lessons[index - 1] if index > 0 else None
    if (
        lesson.kind == "drill"
        and prev is not None
        and prev.kind == "technique"
        and prev.target == lesson.target
    ):
        return index - 1, index
    return index, index


def _bags(sheet: Sheet):
    return (
        [list(packed.lessons) for packed in sheet.classes],
        [packed.class_record for packed in sheet.classes],
    )


def _sheet_from_bags(sheet: Sheet, records, bags) -> Sheet:
    packed = tuple(
        PackedClass(class_record=record, lessons=tuple(lessons))
        for record, lessons in zip(records, bags)
    )
    return replace(sheet, classes=packed)


def _what_to_run(store, lesson: Lesson) -> tuple[str, ...]:
    if lesson.kind == "technique":
        bullets = []
        for citation_id in lesson.citations:
            citation = store.citation(citation_id)
            if citation is not None:
                bullets.extend(citation.step_bullets)
        return tuple(bullets)
    if lesson.kind == "drill":
        return (lesson.partner_job,) if lesson.partner_job else ()
    if lesson.kind == "sparring":
        return (lesson.scenario,) if lesson.scenario else ()
    if lesson.kind == "game":
        return (lesson.condition,) if lesson.condition else ()
    return ()


def _target_name(store, target_id: str) -> str:
    node = store.enrichment_node(target_id) if target_id else None
    return node.name if node is not None else target_id
