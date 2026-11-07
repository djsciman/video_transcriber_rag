"""Read and Edit modes of the class-card sheet. Draft stays the no-edit proposal."""

from __future__ import annotations

import inspect
from dataclasses import fields

from coach_app.build import BuildAdvisor, convert, propose
from coach_app.design import open_design, sample_tight_waist
from coach_app.edit import (
    add_lesson,
    class_cards,
    drag_lesson,
    open_sheet,
    remove_lesson,
    set_mode,
    set_purpose,
)
from coach_app.store import Citation, Class, Lesson, Unit
from tests.test_build import TIGHT_WAIST_PARAGRAPH
from tests.test_design import _named, _tight_waist_catalog


def _draft(store):
    result = convert(store, sample_tight_waist(store), BuildAdvisor())
    assert result.draft is not None
    return result.draft


def _link(store, named_move, **fields) -> Citation:
    return store.put_citation(Citation(named_move_id=named_move.id, **fields))


def _kinds(packed):
    return [lesson.kind for lesson in packed.lessons]


def _glue_pairs(lessons):
    pairs = []
    for index, lesson in enumerate(lessons):
        if lesson.kind != "technique":
            continue
        pairs.append((index, lesson, lessons[index + 1]))
    return pairs


def test_read_and_edit_share_the_class_card_sheet_and_draft_stays_no_edit():
    store = _tight_waist_catalog()
    draft = _draft(store)
    read = open_sheet(store, draft, "read")
    edit = open_sheet(store, draft, "edit")
    switched = set_mode(read, "edit")
    source = inspect.getsource(inspect.getmodule(open_sheet))

    assert draft.editable is False
    assert not hasattr(draft, "add_lesson")
    assert not hasattr(draft, "remove_lesson")
    assert read.unit == draft.unit == edit.unit
    assert read.classes == draft.classes == edit.classes
    assert read.columns == draft.columns == edit.columns == (
        "Lesson",
        "Type",
        "Target",
        "What to run",
    )
    assert read.layout == draft.layout == edit.layout == "B"
    assert read.mode == "read"
    assert edit.mode == "edit"
    assert read.editable is False
    assert edit.editable is True
    assert switched.mode == "edit"
    assert switched.editable is True
    assert switched.classes == read.classes
    assert type(read) is type(edit)
    try:
        add_lesson(
            store,
            read,
            Lesson(kind="sparring", scenario="Half guard bottom."),
        )
    except ValueError as error:
        assert "edit" in str(error).casefold()
    else:
        raise AssertionError("expected Read mode to refuse packing")
    assert "playback" not in source.casefold()
    assert "prototypes" not in source.casefold()
    assert "<html" not in source.casefold()
    assert "max_classes" not in source.casefold()


def test_technique_cards_show_step_bullets_and_glued_drills_show_partner_job_only():
    store = _tight_waist_catalog()
    knee = _named(store, "Knee lever")
    cite = _link(
        store,
        knee,
        movement="Knee lever from half guard",
        step_bullets=(
            "inside foot place next to their inside knee",
            "cut the knee through to mount",
        ),
    )
    draft = _draft(store)
    sheet = open_sheet(store, draft, "read")
    cards = class_cards(store, sheet)
    technique = cards[0][0]
    drill = cards[0][1]

    assert technique.lesson.kind == "technique"
    assert technique.lesson.citations == (cite.id,)
    assert technique.what_to_run == cite.step_bullets
    assert drill.lesson.kind == "drill"
    assert drill.lesson.target == technique.lesson.target
    assert drill.what_to_run == (drill.lesson.partner_job,)
    assert drill.lesson.partner_job
    assert cite.step_bullets[0] not in drill.what_to_run
    assert technique.glued is True
    assert drill.glued is True
    assert sheet.columns[-1] == "What to run"


def test_glue_holds_on_drag_add_and_remove():
    store = _tight_waist_catalog()
    draft = _draft(store)
    sheet = open_sheet(store, draft, "edit")
    first = sheet.classes[0].lessons[0]
    following = sheet.classes[0].lessons[1]
    extra = _named(store, "Old school sweep")

    moved = drag_lesson(store, sheet, first.id, class_index=1, index=0)
    added = add_lesson(
        store,
        moved,
        Lesson(kind="technique", target=extra.id, citations=()),
        class_index=0,
        index=0,
    )
    inserted = added.classes[0].lessons[0]
    inserted_drill = added.classes[0].lessons[1]
    removed = remove_lesson(store, added, inserted.id)

    assert moved.classes[1].lessons[0].id == first.id
    assert moved.classes[1].lessons[1].id == following.id
    assert moved.classes[1].lessons[0].kind == "technique"
    assert moved.classes[1].lessons[1].kind == "drill"
    assert moved.classes[1].lessons[0].target == moved.classes[1].lessons[1].target
    assert first.id not in {lesson.id for lesson in moved.classes[0].lessons}
    assert following.id not in {lesson.id for lesson in moved.classes[0].lessons}
    assert inserted.kind == "technique"
    assert inserted_drill.kind == "drill"
    assert inserted.target == extra.id == inserted_drill.target
    assert store.lesson(inserted.id) == inserted
    assert store.lesson(inserted_drill.id) == inserted_drill
    assert inserted.id not in {lesson.id for lesson in removed.classes[0].lessons}
    assert inserted_drill.id not in {
        lesson.id for lesson in removed.classes[0].lessons
    }
    for packed in (moved.classes + added.classes + removed.classes):
        for index, technique, drill in _glue_pairs(packed.lessons):
            assert drill.kind == "drill"
            assert drill.target == technique.target
            assert packed.lessons[index + 1] is drill


def test_empty_classes_are_refused_with_no_class_cap_and_any_type_may_open():
    store = _tight_waist_catalog()
    sheet = open_sheet(store, _draft(store), "edit")
    roll = sheet.classes[1].lessons[2]
    trilemma = sheet.classes[1].lessons[0]
    knee = _named(store, "Knee lever")

    after_roll = remove_lesson(store, sheet, roll.id)
    after_second = remove_lesson(store, after_roll, trilemma.id)
    last_class = after_second.classes[0]
    last_block = last_class.lessons[0]
    remaining = last_class.lessons[2]

    try:
        remove_lesson(
            store,
            remove_lesson(store, after_second, last_block.id),
            remaining.id,
        )
    except ValueError as error:
        assert "lesson" in str(error).casefold()
    else:
        raise AssertionError("expected emptying the last class to be refused")

    opened = add_lesson(
        store,
        after_second,
        Lesson(kind="sparring", target=knee.id, scenario="Half guard bottom."),
    )
    game_class = add_lesson(
        store,
        opened,
        Lesson(kind="game", target=knee.id, condition="Bottom must sweep."),
    )
    drill_class = add_lesson(
        store,
        game_class,
        Lesson(kind="drill", target=knee.id, partner_job="Start light; add frames."),
    )

    assert len(after_second.classes) == 1
    assert after_second.classes[0].lessons
    assert len(drill_class.classes) == 4
    assert _kinds(opened.classes[-1]) == ["sparring"]
    assert _kinds(game_class.classes[-1]) == ["game"]
    assert _kinds(drill_class.classes[-1]) == ["drill"]
    assert all(
        lesson.kind != "technique" for lesson in drill_class.classes[-1].lessons
    )
    assert store.class_record(opened.classes[-1].class_record.id)
    assert "max_classes" not in inspect.getsource(inspect.getmodule(open_sheet))
    saved = store.custom_lessons()
    assert any(
        item.lesson.kind == "sparring" and item.lesson.scenario == "Half guard bottom."
        for item in saved
    )


def test_sparring_games_and_drill_only_store_text_after_draft():
    store = _tight_waist_catalog()
    draft = propose(
        store,
        open_design(topic_name="Tight waist", topic_ruleset="gi"),
        TIGHT_WAIST_PARAGRAPH,
        BuildAdvisor(),
    ).draft
    sheet = open_sheet(store, draft, "edit")
    knee = _named(store, "Knee lever")

    with_sparring = add_lesson(
        store,
        sheet,
        Lesson(
            kind="sparring",
            target=knee.id,
            scenario="Start and restart in half guard bottom. Both may work.",
        ),
        class_index=0,
    )
    with_game = add_lesson(
        store,
        with_sparring,
        Lesson(
            kind="game",
            target=knee.id,
            condition="Point only if the bottom player finishes the roll-through.",
        ),
        class_index=1,
    )
    with_drill = add_lesson(
        store,
        with_game,
        Lesson(
            kind="drill",
            target=knee.id,
            partner_job="Open harder than the first drill: partner hunts the switch.",
        ),
        class_index=0,
    )
    sparring = with_drill.classes[0].lessons[-2]
    drill = with_drill.classes[0].lessons[-1]
    game = with_drill.classes[1].lessons[-1]

    assert sparring.kind == "sparring"
    assert sparring.scenario == (
        "Start and restart in half guard bottom. Both may work."
    )
    assert store.lesson(sparring.id).scenario == sparring.scenario
    assert game.kind == "game"
    assert game.condition == (
        "Point only if the bottom player finishes the roll-through."
    )
    assert store.lesson(game.id).condition == game.condition
    assert drill.kind == "drill"
    assert drill.partner_job.startswith("Open harder")
    assert store.lesson(drill.id).partner_job == drill.partner_job
    assert with_drill.classes[0].lessons[0].kind == "technique"


def test_purpose_starts_empty_until_written():
    store = _tight_waist_catalog()
    draft = _draft(store)
    sheet = open_sheet(store, draft, "edit")

    assert all(packed.class_record.purpose == "" for packed in draft.classes)
    written = set_purpose(store, sheet, 0, "Win the underhook.")
    stored = store.class_record(written.classes[0].class_record.id)

    assert written.classes[0].class_record.purpose == "Win the underhook."
    assert stored == written.classes[0].class_record
    assert written.classes[1].class_record.purpose == ""
    assert isinstance(stored, Class)
    assert isinstance(written.unit, Unit)


def test_read_checkboxes_and_success_watch_are_not_stored():
    store = _tight_waist_catalog()
    sheet = open_sheet(store, _draft(store), "read")
    record_fields = {
        field.name
        for record in (Unit, Class, Lesson)
        for field in fields(record)
    }
    sheet_fields = {field.name for field in fields(type(sheet))}
    store_names = {name for name in dir(store) if not name.startswith("_")}

    assert "checkboxes" not in sheet_fields
    assert "checkbox" not in sheet_fields
    assert "success_watch" not in sheet_fields
    assert "success" not in sheet_fields
    assert "checkboxes" not in record_fields
    assert "success_watch" not in record_fields
    assert "success" not in record_fields
    assert not any("checkbox" in name.casefold() for name in store_names)
    assert not any("success" in name.casefold() for name in store_names)
    assert not hasattr(sheet, "checkboxes")
    assert not hasattr(sheet, "success_watch")
    assert store.unit(sheet.unit.id) == sheet.unit
