"""Custom library and unit history screens. Drive HTTP, then the store.

Headed browser is unavailable in this environment; urllib is the stand-in.
"""

from __future__ import annotations

import inspect

from coach_app.app import CoachApp
from coach_app.edit import add_lesson
from coach_app.library import (
    browse_library,
    copy_history,
    create_custom,
    delete_custom,
    edit_custom,
    save_history,
    search_library,
)
from coach_app.store import CuratedStore, CustomLesson, Lesson, Unit
from coach_app.ui_sheet import current_sheet
from tests.test_ui_design import _named
from tests.test_ui_sheet import _Page, _form, _get, _pack, _post, _sheet


def _custom(app: CoachApp) -> str:
    return app.url.rstrip("/") + "/custom"


def _history(app: CoachApp) -> str:
    return app.url.rstrip("/") + "/history"


def test_custom_and_history_are_on_the_nav_without_prototype_chrome(tmp_path):
    with CoachApp(tmp_path) as app:
        home = _Page(_get(app.url))
        custom = _Page(_get(_custom(app)))
        history = _Page(_get(_history(app)))

    assert any(href == "/custom" and label == "Custom" for href, label in home.links)
    assert any(href == "/history" and label == "History" for href, label in home.links)
    assert "Custom" in custom.text
    assert "History" in history.text
    for page in (home, custom, history):
        assert "PROTOTYPE" not in page.markup
        assert "Load sample" not in page.markup
        assert "variant" not in page.markup.lower()
        assert "Guided walkthroughs" not in page.markup


def test_create_edit_delete_custom_without_an_open_unit(tmp_path):
    with CoachApp(tmp_path) as app:
        assert app.store.units() == ()
        url = _custom(app)
        page = _Page(_get(url))
        old = _named(app.store, "Old school sweep")
        created = _Page(
            _post(
                url,
                {
                    **_form(page, "create-custom")["inputs"],
                    "kind": "drill",
                    "target": old.id,
                    "partner_job": "Hold the underhook.",
                },
            )
        )
        assert app.store.units() == ()
        saved = app.store.custom_lessons()
        assert len(saved) == 1
        custom_id = saved[0].id
        edited = _Page(
            _post(
                url,
                {
                    **_form(created, f"edit-{custom_id}")["inputs"],
                    "kind": "drill",
                    "target": old.id,
                    "partner_job": "Open harder.",
                },
            )
        )
        _Page(_post(url, _form(edited, f"delete-{custom_id}")["inputs"]))

    store = CuratedStore.open(tmp_path)
    assert store.units() == ()
    assert store.topics() == ()
    assert "Hold the underhook." in created.markup
    assert "Open harder." in edited.markup
    assert "class-card" in created.markup
    assert store.custom_lesson(custom_id) is None
    assert store.custom_lessons() == ()
    assert isinstance(saved[0], CustomLesson)


def test_search_and_hierarchy_under_custom_find_those_lessons(tmp_path):
    with CoachApp(tmp_path) as app:
        url = _custom(app)
        page = _Page(_get(url))
        old = _named(app.store, "Old school sweep")
        created = _Page(
            _post(
                url,
                {
                    **_form(page, "create-custom")["inputs"],
                    "kind": "sparring",
                    "target": old.id,
                    "scenario": "Half guard, both may work.",
                },
            )
        )
        custom_id = app.store.custom_lessons()[0].id
        searched = _Page(
            _post(
                url,
                {
                    **_form(created, "search-library")["inputs"],
                    "position": "Half guard",
                    "sweep": "sweep",
                    "ruleset": "gi",
                },
            )
        )
        browse_start = _Page(
            _post(url, _form(searched, "browse-start-half-guard")["inputs"])
        )
        browse_type = _Page(
            _post(url, _form(browse_start, "browse-type-sweep")["inputs"])
        )
        browse_end = _Page(
            _post(url, _form(browse_type, "browse-end-side-control")["inputs"])
        )
        hits = search_library(
            app.store,
            position="Half guard",
            sweep="sweep",
            ruleset="gi",
        )
        leaves = browse_library(
            app.store,
            start="half-guard",
            type_of_move="sweep",
            end="side-control",
        )

    assert "Half guard, both may work." in searched.sections.get(
        "search-results", searched.text
    )
    assert any(isinstance(hit, CustomLesson) and hit.id == custom_id for hit in hits)
    assert "Type of move" in browse_start.text or "sweep" in browse_start.markup.casefold()
    assert "Side control" in browse_type.text or "side-control" in browse_type.markup
    assert "Old school sweep" in browse_end.markup
    assert "Half guard, both may work." in browse_end.markup
    assert any(isinstance(item, CustomLesson) and item.id == custom_id for item in leaves)
    store = CuratedStore.open(tmp_path)
    assert any(item.id == custom_id for item in store.custom_lessons())


def test_saving_a_unit_writes_a_history_entry(tmp_path):
    with CoachApp(tmp_path) as app:
        _pack(app)
        live = current_sheet(app.store, "Tight waist", "gi")
        url = _history(app)
        page = _Page(_get(url))
        saved = _Page(
            _post(
                url,
                {
                    **_form(page, "save-history")["inputs"],
                    "name": "Tight waist",
                    "ruleset": "gi",
                },
            )
        )
        histories = app.store.unit_histories()

    assert live is not None
    assert len(histories) == 1
    assert histories[0].unit == live.unit
    assert histories[0].classes
    assert "Tight waist" in saved.markup
    assert "class-card" in saved.markup
    store = CuratedStore.open(tmp_path)
    past = store.unit_history(histories[0].id)
    assert past is not None
    assert past.unit.id == live.unit.id
    assert past.unit.topic_name == "Tight waist"
    assert past.unit.topic_ruleset == "gi"


def test_copy_from_history_creates_a_new_editable_unit_and_leaves_the_past(tmp_path):
    with CoachApp(tmp_path) as app:
        _pack(app)
        original = current_sheet(app.store, "Tight waist", "gi")
        original_kinds = tuple(
            tuple(lesson.kind for lesson in packed.lessons)
            for packed in original.classes
        )
        history_url = _history(app)
        page = _Page(_get(history_url))
        page = _Page(
            _post(
                history_url,
                {
                    **_form(page, "save-history")["inputs"],
                    "name": "Tight waist",
                    "ruleset": "gi",
                },
            )
        )
        saved_id = app.store.unit_histories()[0].id
        copied_page = _Page(
            _post(history_url, _form(page, f"copy-{saved_id}")["inputs"])
        )
        copied = current_sheet(app.store, "Tight waist", "gi", "edit")
        knee = _named(app.store, "Knee lever")
        mutated = add_lesson(
            app.store,
            copied,
            Lesson(kind="game", target=knee.id, condition="Sweep only."),
            class_index=0,
        )
        past = app.store.unit_history(saved_id)
        sheet_after = _Page(_get(_sheet(app, mode="edit")))

    assert copied.unit.id != original.unit.id
    assert copied.unit.topic_name == original.unit.topic_name
    assert copied.unit.topic_ruleset == original.unit.topic_ruleset
    assert copied.mode == "edit"
    assert copied.editable is True
    assert isinstance(copied.unit, Unit)
    assert past.unit == original.unit
    assert tuple(
        tuple(lesson.kind for lesson in packed.lessons) for packed in past.classes
    ) == original_kinds
    assert mutated.unit.id == copied.unit.id
    assert any(
        lesson.kind == "game" and lesson.condition == "Sweep only."
        for packed in mutated.classes
        for lesson in packed.lessons
    )
    assert all(
        lesson.kind != "game"
        for packed in past.classes
        for lesson in packed.lessons
    )
    assert 'data-mode="edit"' in copied_page.markup
    assert "class-card" in copied_page.markup
    assert any(form["id"].startswith("remove-") for form in copied_page.forms)
    assert "class-card" in sheet_after.markup
    store = CuratedStore.open(tmp_path)
    assert store.unit_history(saved_id).unit.paragraph == original.unit.paragraph
    assert store.unit(copied.unit.id) is not None
    assert store.unit(copied.unit.id).id != original.unit.id


def test_screens_call_library_domain_and_skip_prototype_html():
    import coach_app.ui_library as ui_library

    source = inspect.getsource(ui_library)
    folded = source.casefold()
    assert "create_custom" in source
    assert "edit_custom" in source
    assert "delete_custom" in source
    assert "search_library" in source
    assert "browse_library" in source
    assert "save_history" in source
    assert "copy_history" in source
    assert "put_sheet" in source
    assert "_design_sessions" not in source
    assert "_library_walk" not in source
    assert "put_custom_lesson" not in source
    assert "put_unit_history" not in source
    assert "prototypes" not in folded
    assert "sample-unit-topic10" not in folded
    assert "enrichment-categories-topic26" not in folded
    assert "playwright" not in folded
    assert "selenium" not in folded
    assert "react" not in folded
    assert "vue" not in folded
    assert "<html" not in folded
    assert callable(create_custom)
    assert callable(edit_custom)
    assert callable(delete_custom)
    assert callable(save_history)
    assert callable(copy_history)
