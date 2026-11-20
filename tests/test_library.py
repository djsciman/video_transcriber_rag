"""Custom library and unit history through the curated-store facade."""

from __future__ import annotations

import inspect
from dataclasses import replace

from coach_app.design import sample_tight_waist
from coach_app.edit import add_lesson, open_sheet
from coach_app.library import (
    add_lesson_sources,
    browse_library,
    copy_history,
    create_custom,
    delete_custom,
    edit_custom,
    named_moves_on_map,
    place_lesson,
    pull_custom,
    save_history,
    search_library,
)
from coach_app.store import (
    Citation,
    CuratedStore,
    CustomLesson,
    Instructional,
    Lesson,
    Unit,
)
from tests.test_design import _named, _tight_waist_catalog
from tests.test_edit import _draft


def test_place_on_a_unit_writes_custom_with_no_extra_save():
    store = _tight_waist_catalog()
    sheet = open_sheet(store, _draft(store), "edit")
    knee = _named(store, "Knee lever")
    lesson = Lesson(
        kind="sparring",
        target=knee.id,
        scenario="Half guard bottom.",
    )

    placed = place_lesson(store, sheet, lesson, class_index=0)
    saved = store.custom_lessons()

    assert len(saved) == 1
    assert saved[0].lesson.kind == "sparring"
    assert saved[0].lesson.scenario == "Half guard bottom."
    assert saved[0].lesson.target == knee.id
    assert saved[0].id
    assert store.custom_lesson(saved[0].id) == saved[0]
    assert any(
        item.kind == "sparring" and item.scenario == "Half guard bottom."
        for item in placed.classes[0].lessons
    )
    assert inspect.getsource(place_lesson).count("add_lesson") >= 1
    via_edit = add_lesson(
        store,
        placed,
        Lesson(kind="game", target=knee.id, condition="Sweep only."),
        class_index=0,
    )
    assert any(
        item.lesson.kind == "game" and item.lesson.condition == "Sweep only."
        for item in store.custom_lessons()
    )
    assert via_edit.classes[0].lessons[-1].kind == "game"


def test_pull_copies_fields_technique_brings_glued_drill_edit_leaves_saved():
    store = _tight_waist_catalog()
    sheet = open_sheet(store, _draft(store), "edit")
    old = _named(store, "Old school sweep")
    custom = create_custom(
        store,
        Lesson(
            kind="technique",
            target=old.id,
            citations=("cite-old",),
            partner_job="Start light; add frames.",
        ),
    )

    copies = pull_custom(store, custom.id)
    technique, drill = copies
    placed = place_lesson(
        store,
        sheet,
        technique,
        class_index=0,
        glued=drill,
    )
    unit_technique = next(
        item
        for item in placed.classes[0].lessons
        if item.kind == "technique" and item.target == old.id
    )
    unit_drill = next(
        item
        for item in placed.classes[0].lessons
        if item.kind == "drill" and item.target == old.id
    )
    store.put_lesson(replace(unit_technique, citations=("mutated",)))
    store.put_lesson(replace(unit_drill, partner_job="Open harder."))

    saved = store.custom_lesson(custom.id)
    assert technique.kind == "technique"
    assert technique.target == old.id
    assert technique.citations == ("cite-old",)
    assert technique.id == ""
    assert drill.kind == "drill"
    assert drill.target == old.id
    assert drill.citations == ("cite-old",)
    assert drill.partner_job == "Start light; add frames."
    assert drill.id == ""
    assert unit_drill.partner_job == "Start light; add frames."
    assert saved.lesson.citations == ("cite-old",)
    assert saved.lesson.partner_job == "Start light; add frames."
    assert saved.lesson.target == old.id
    assert store.lesson(unit_technique.id).citations == ("mutated",)


def test_custom_create_edit_delete_with_no_open_unit():
    store = _tight_waist_catalog()
    move = _named(store, "Knee lever")

    created = create_custom(
        store,
        Lesson(kind="drill", target=move.id, partner_job="Hold the underhook."),
    )
    edited = edit_custom(
        store,
        created.id,
        Lesson(kind="drill", target=move.id, partner_job="Open harder."),
    )
    delete_custom(store, created.id)

    assert store.units() == ()
    assert created.id
    assert created.lesson.partner_job == "Hold the underhook."
    assert edited.id == created.id
    assert store.custom_lesson(created.id) is None
    assert all(item.id != created.id for item in store.custom_lessons())
    assert isinstance(created, CustomLesson)
    assert isinstance(edited, CustomLesson)


def test_add_lesson_pulls_from_custom_search_hierarchy_or_map():
    store = _tight_waist_catalog()
    sheet = open_sheet(store, _draft(store), "edit")
    session = sample_tight_waist(store)
    old = _named(store, "Old school sweep")
    knee = _named(store, "Knee lever")
    store.put_instructional(
        Instructional(instructor="Emily Kwok", name="Old School", ruleset="gi")
    )
    store.put_citation(
        Citation(
            movement="Old school sweep",
            instructor="Emily Kwok",
            instructional="Old School",
            named_move_id=old.id,
        )
    )
    custom = create_custom(
        store,
        Lesson(kind="sparring", target=old.id, scenario="Half guard, both may work."),
    )

    pulled = pull_custom(store, custom.id)
    placed = place_lesson(store, sheet, pulled[0], class_index=0)
    searched = search_library(
        store,
        position="Half guard",
        sweep="sweep",
        instructor="Emily Kwok",
        ruleset="gi",
    )
    starts = browse_library(store)
    types = browse_library(store, start="half-guard")
    ends = browse_library(store, start="half-guard", type_of_move="sweep")
    leaves = browse_library(
        store,
        start="half-guard",
        type_of_move="sweep",
        end="side-control",
    )
    mapped = named_moves_on_map(session)
    sources = add_lesson_sources(
        store,
        session,
        position="Half guard",
        sweep="sweep",
        instructor="Emily Kwok",
        ruleset="gi",
        start="half-guard",
        type_of_move="sweep",
        end="side-control",
    )

    assert pulled[0].scenario == "Half guard, both may work."
    assert any(
        item.kind == "sparring" and item.scenario == pulled[0].scenario
        for item in placed.classes[0].lessons
    )
    assert any(getattr(hit, "id", None) == old.id or getattr(hit, "name", None) == old.name for hit in searched)
    assert any(node.name == "Half guard" for node in starts)
    assert {node.kind for node in types} == {"type of move"}
    assert any(node.name == "Side control" for node in ends)
    assert any(getattr(item, "id", None) == old.id or getattr(item, "name", None) == old.name for item in leaves)
    assert any(isinstance(item, CustomLesson) and item.id == custom.id for item in leaves)
    assert knee.id in mapped
    assert _named(store, "Tight waist").id in mapped
    assert any(item.id == custom.id for item in sources.custom)
    assert sources.search
    assert sources.hierarchy
    assert knee.id in sources.map_moves


def test_history_copy_creates_new_editable_unit_and_leaves_the_past_unchanged():
    store = _tight_waist_catalog()
    sheet = open_sheet(store, _draft(store), "edit")
    original_unit = sheet.unit
    original_kinds = tuple(
        tuple(lesson.kind for lesson in packed.lessons) for packed in sheet.classes
    )

    saved = save_history(store, sheet)
    copied = copy_history(store, saved.id)
    store.put_unit(replace(copied.unit, paragraph="Retake the tight waist."))
    copied = add_lesson(
        store,
        copied,
        Lesson(kind="game", target=_named(store, "Knee lever").id, condition="Sweep only."),
    )

    past = store.unit_history(saved.id)
    assert saved.unit == original_unit
    assert past.unit == original_unit
    assert past.classes
    assert tuple(
        tuple(lesson.kind for lesson in packed.lessons) for packed in past.classes
    ) == original_kinds
    assert past.unit.paragraph == original_unit.paragraph
    assert past.unit.id == original_unit.id
    assert copied.unit.id != original_unit.id
    assert copied.unit.topic_name == original_unit.topic_name
    assert copied.unit.topic_ruleset == original_unit.topic_ruleset
    assert copied.mode == "edit"
    assert copied.editable is True
    assert store.unit(copied.unit.id) == store.unit(copied.unit.id)
    assert isinstance(copied.unit, Unit)
    assert tuple(
        tuple(lesson.kind for lesson in packed.lessons) for packed in copied.classes
    ) != original_kinds
    assert tuple(
        tuple(lesson.kind for lesson in packed.lessons) for packed in sheet.classes
    ) == original_kinds
    assert all(
        new.id != old.id
        for new_packed, old_packed in zip(copied.classes, sheet.classes)
        for new, old in zip(new_packed.lessons, old_packed.lessons)
    )


def test_custom_copy_and_history_copy_go_through_the_facade():
    source = inspect.getsource(inspect.getmodule(place_lesson))
    folded = source.casefold()

    assert "put_custom_lesson" in source
    assert "custom_lesson" in source
    assert "put_unit_history" in source
    assert "unit_history" in source
    assert "put_unit" in source
    assert "browse_hierarchy" in source
    assert "_HISTORY_CLASSES" not in source
    assert "<html" not in folded
    assert "prototypes" not in folded
    assert callable(CuratedStore.delete_custom_lesson)
