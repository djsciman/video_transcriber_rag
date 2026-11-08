"""Read and Edit modes of the class-card sheet. Drive HTTP, then the store.

Headed browser is unavailable in this environment; urllib is the stand-in.
"""

from __future__ import annotations

import inspect
from html.parser import HTMLParser
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from coach_app.app import CoachApp
from coach_app.edit import (
    add_lesson,
    class_cards,
    drag_lesson,
    open_sheet,
    remove_lesson,
    set_mode,
    set_purpose,
)
from coach_app.library import add_lesson_sources, place_lesson, pull_custom
from coach_app.store import Citation, CuratedStore, CustomLesson, Lesson
from coach_app.ui_design import design_session
from coach_app.ui_sheet import current_sheet
from tests.test_build import TIGHT_WAIST_PARAGRAPH
from tests.test_ui_design import (
    _design,
    _install_tight_waist,
    _named,
    _open_topic,
)


class _Page(HTMLParser):
    def __init__(self, markup: str) -> None:
        super().__init__()
        self.markup = markup
        self.title = ""
        self.text_parts: list[str] = []
        self.links: list[tuple[str, str]] = []
        self.forms: list[dict[str, object]] = []
        self.sections: dict[str, str] = {}
        self.checkboxes: list[dict[str, str]] = []
        self._in_title = False
        self._in_textarea = False
        self._textarea_name = ""
        self._textarea_parts: list[str] = []
        self._current_href = ""
        self._link_text: list[str] = []
        self._current_form: dict[str, object] | None = None
        self._select_name = ""
        self._select_selected = False
        self._section_id = ""
        self._section_parts: list[str] = []
        self.feed(markup)
        self._flush_section()

    def handle_starttag(self, tag, attrs) -> None:
        attrs = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "a":
            self._current_href = attrs.get("href", "")
            self._link_text = []
        elif tag == "section":
            self._flush_section()
            self._section_id = attrs.get("id", "")
            self._section_parts = []
        elif tag == "form":
            self._current_form = {
                "id": attrs.get("id", ""),
                "action": attrs.get("action", ""),
                "method": attrs.get("method", "get").lower(),
                "inputs": {},
            }
        elif tag == "input":
            if attrs.get("type") == "checkbox":
                self.checkboxes.append(attrs)
            name = attrs.get("name")
            if name and self._current_form is not None:
                self._current_form["inputs"][name] = attrs.get("value", "")
        elif tag == "textarea":
            self._in_textarea = True
            self._textarea_name = attrs.get("name", "")
            self._textarea_parts = []
        elif tag == "select":
            self._select_name = attrs.get("name", "")
            self._select_selected = False
            if self._select_name and self._current_form is not None:
                self._current_form["inputs"][self._select_name] = ""
        elif tag == "option":
            if self._select_name and self._current_form is not None:
                value = attrs.get("value", "")
                selected = "selected" in attrs
                current = self._current_form["inputs"].get(self._select_name, "")
                if selected or (not self._select_selected and current == ""):
                    self._current_form["inputs"][self._select_name] = value
                    if selected:
                        self._select_selected = True
        elif tag == "button":
            name = attrs.get("name")
            if name and self._current_form is not None:
                self._current_form["inputs"].setdefault(name, attrs.get("value", ""))

    def handle_endtag(self, tag) -> None:
        if tag == "title":
            self._in_title = False
        elif tag == "a":
            self.links.append((self._current_href, "".join(self._link_text).strip()))
            self._current_href = ""
            self._link_text = []
        elif tag == "textarea":
            value = "".join(self._textarea_parts)
            if self._textarea_name and self._current_form is not None:
                self._current_form["inputs"][self._textarea_name] = value
            self._in_textarea = False
            self._textarea_name = ""
        elif tag == "select":
            self._select_name = ""
            self._select_selected = False
        elif tag == "form" and self._current_form is not None:
            self.forms.append(self._current_form)
            self._current_form = None
        elif tag == "section":
            self._flush_section()

    def handle_data(self, data) -> None:
        if self._in_title:
            self.title += data
        if self._current_href:
            self._link_text.append(data)
        if self._in_textarea:
            self._textarea_parts.append(data)
        if data.strip():
            self.text_parts.append(data.strip())
            if self._section_id:
                self._section_parts.append(data.strip())

    def _flush_section(self) -> None:
        if self._section_id:
            self.sections[self._section_id] = " ".join(self._section_parts)
        self._section_id = ""
        self._section_parts = []

    @property
    def text(self) -> str:
        return " ".join(self.text_parts)


def _get(url: str) -> str:
    with urlopen(url, timeout=5) as response:
        return response.read().decode("utf-8")


def _post(url: str, fields: dict[str, str]) -> str:
    request = Request(
        url,
        data=urlencode(fields).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urlopen(request, timeout=5) as response:
        return response.read().decode("utf-8")


def _form(page: _Page, form_id: str) -> dict[str, object]:
    for form in page.forms:
        if form["id"] == form_id:
            return form
    raise AssertionError(form_id)


def _sheet(app: CoachApp, name: str = "Tight waist", ruleset: str = "gi", mode: str = "") -> str:
    query = {"name": name, "ruleset": ruleset}
    if mode:
        query["mode"] = mode
    return app.url.rstrip("/") + "/sheet?" + urlencode(query)


def _pack(app: CoachApp) -> _Page:
    _open_topic(app)
    _install_tight_waist(app.store)
    knee = _named(app.store, "Knee lever")
    app.store.put_citation(
        Citation(
            named_move_id=knee.id,
            movement="Knee lever from half guard",
            step_bullets=(
                "inside foot place next to their inside knee",
                "cut the knee through to mount",
            ),
        )
    )
    url = _design(app)
    return _Page(
        _post(
            url,
            {
                "name": "Tight waist",
                "ruleset": "gi",
                "action": "propose",
                "paragraph": TIGHT_WAIST_PARAGRAPH,
            },
        )
    )


def test_read_and_edit_are_modes_of_the_same_sheet_and_draft_stays_no_edit(tmp_path):
    with CoachApp(tmp_path) as app:
        home = _Page(_get(app.url))
        packed = _pack(app)
        draft_html = packed.sections.get("draft", packed.text)
        read = _Page(_get(_sheet(app, mode="read")))
        edit = _Page(_get(_sheet(app, mode="edit")))
        switched = _Page(_post(_sheet(app), _form(read, "mode-edit")["inputs"]))

    assert any(href == "/sheet" and label == "Sheet" for href, label in home.links)
    assert packed.sections.get("draft") or 'id="draft"' in packed.markup
    assert "Add: " not in draft_html
    assert "contenteditable" not in packed.markup.casefold()
    assert "remove-" not in {form["id"] for form in packed.forms}
    assert read.sections.get("sheet") or 'id="sheet"' in read.markup
    assert edit.sections.get("sheet") or 'id="sheet"' in edit.markup
    assert 'data-mode="read"' in read.markup
    assert 'data-mode="edit"' in edit.markup
    assert "class-card" in read.markup
    assert "class-card" in edit.markup
    assert "Knee lever" in read.markup
    assert "Knee lever" in edit.markup
    assert "Playback" not in read.markup
    assert "Playback" not in edit.markup
    assert "PROTOTYPE" not in read.markup
    assert "Load sample" not in edit.markup
    assert "variant" not in read.markup.lower()
    assert any(form["id"] == "mode-read" for form in read.forms)
    assert any(form["id"] == "mode-edit" for form in read.forms)
    assert any(form["id"].startswith("remove-") for form in edit.forms)
    assert not any(form["id"].startswith("remove-") for form in read.forms)
    assert not any(form["id"].startswith("add-") for form in read.forms)
    assert 'data-mode="edit"' in switched.markup
    assert any(form["id"].startswith("remove-") for form in switched.forms)


def test_read_checkboxes_do_not_write_the_store(tmp_path):
    with CoachApp(tmp_path) as app:
        _pack(app)
        before = list(app.store.lessons())
        before_classes = list(app.store.classes())
        read = _Page(_get(_sheet(app, mode="read")))
        named_boxes = [box for box in read.checkboxes if box.get("name")]
        _post(
            _sheet(app),
            {
                "name": "Tight waist",
                "ruleset": "gi",
                "mode": "read",
                "checkbox": "on",
                "success_watch": "They keep the underhook.",
            },
        )
        after = list(app.store.lessons())
        after_classes = list(app.store.classes())

    assert read.checkboxes
    assert named_boxes == []
    folded = read.text.casefold()
    assert "success watch" in folded
    assert "attempting" in folded
    assert "completing" in folded or "coming close" in folded
    assert "none" in folded and "some" in folded and "most" in folded and "all" in folded
    assert before == after
    assert before_classes == after_classes
    store = CuratedStore.open(tmp_path)
    assert store.lessons() == tuple(before)
    assert all(record.purpose == "" for record in store.classes())


def test_glue_holds_on_http_drag_add_and_remove(tmp_path):
    with CoachApp(tmp_path) as app:
        _pack(app)
        store = app.store
        sheet_url = _sheet(app, mode="edit")
        page = _Page(_get(sheet_url))
        live = current_sheet(store, "Tight waist", "gi")
        first = live.classes[0].lessons[0]
        following = live.classes[0].lessons[1]
        other = live.classes[1].lessons[0]
        home_drag = dict(_form(page, f"drag-{first.id}")["inputs"])
        other_drag = dict(_form(page, f"drag-{other.id}")["inputs"])
        assert home_drag["class_index"] == "0"
        assert other_drag["class_index"] == "1"
        dest = dict(home_drag)
        dest["class_index"] = other_drag["class_index"]
        dest["index"] = other_drag["index"]
        moved = _Page(_post(sheet_url, dest))
        after_drag = current_sheet(store, "Tight waist", "gi")
        extra = _named(store, "Old school sweep")
        searched = _Page(
            _post(
                sheet_url,
                {
                    **_form(moved, "search-library")["inputs"],
                    "position": "Half guard",
                    "sweep": "sweep",
                    "ruleset": "gi",
                },
            )
        )
        add_fields = dict(_form(searched, f"add-search-{extra.id}")["inputs"])
        add_fields["kind"] = "technique"
        add_fields["class_index"] = "0"
        add_fields["index"] = "0"
        added = _Page(_post(sheet_url, add_fields))
        after_add = current_sheet(store, "Tight waist", "gi")
        inserted = after_add.classes[0].lessons[0]
        inserted_drill = after_add.classes[0].lessons[1]
        removed = _Page(
            _post(sheet_url, _form(added, f"remove-{inserted.id}")["inputs"])
        )
        after_remove = current_sheet(store, "Tight waist", "gi")

    assert after_drag.classes[1].lessons[0].id == first.id
    assert after_drag.classes[1].lessons[1].id == following.id
    assert after_drag.classes[1].lessons[0].kind == "technique"
    assert after_drag.classes[1].lessons[1].kind == "drill"
    assert after_drag.classes[1].lessons[0].target == after_drag.classes[1].lessons[1].target
    assert first.id not in {lesson.id for lesson in after_drag.classes[0].lessons}
    assert following.id not in {lesson.id for lesson in after_drag.classes[0].lessons}
    assert inserted.kind == "technique"
    assert inserted_drill.kind == "drill"
    assert inserted.target == extra.id == inserted_drill.target
    assert store.lesson(inserted.id) == inserted
    assert store.lesson(inserted_drill.id) == inserted_drill
    assert inserted.id not in {
        lesson.id for packed in after_remove.classes for lesson in packed.lessons
    }
    assert inserted_drill.id not in {
        lesson.id for packed in after_remove.classes for lesson in packed.lessons
    }
    assert f"remove-{inserted.id}" not in {form["id"] for form in removed.forms}
    assert f"remove-{inserted_drill.id}" not in {form["id"] for form in removed.forms}


def test_purpose_and_sparring_game_drill_only_edit_through_the_store(tmp_path):
    with CoachApp(tmp_path) as app:
        _pack(app)
        url = _sheet(app, mode="edit")
        page = _Page(_get(url))
        written = _Page(
            _post(
                url,
                {
                    **_form(page, "purpose-0")["inputs"],
                    "purpose": "Win the underhook.",
                },
            )
        )
        knee = _named(app.store, "Knee lever")
        add_form = dict(_form(written, f"add-map-{knee.id}")["inputs"])
        assert "kind" in add_form
        assert "class_index" in add_form
        assert "scenario" in add_form
        assert "condition" in add_form
        assert "partner_job" in add_form
        for option in ("technique", "sparring", "game", "drill"):
            assert option in written.markup
        sparring_fields = dict(add_form)
        sparring_fields["kind"] = "sparring"
        sparring_fields["class_index"] = "new"
        sparring_fields["scenario"] = (
            "Start and restart in half guard bottom. Both may work."
        )
        with_sparring = _Page(_post(url, sparring_fields))
        game_fields = dict(_form(with_sparring, f"add-map-{knee.id}")["inputs"])
        game_fields["kind"] = "game"
        game_fields["class_index"] = "new"
        game_fields["condition"] = (
            "Point only if the bottom player finishes the roll-through."
        )
        with_game = _Page(_post(url, game_fields))
        drill_fields = dict(_form(with_game, f"add-map-{knee.id}")["inputs"])
        drill_fields["kind"] = "drill"
        drill_fields["class_index"] = "new"
        drill_fields["partner_job"] = (
            "Open harder than the first drill: partner hunts the switch."
        )
        with_drill = _Page(_post(url, drill_fields))
        store = app.store

    assert "Win the underhook." in written.markup
    persisted = CuratedStore.open(tmp_path)
    assert any(record.purpose == "Win the underhook." for record in persisted.classes())
    assert any(
        lesson.kind == "sparring"
        and "half guard bottom" in lesson.scenario.casefold()
        for lesson in store.lessons()
    )
    assert any(
        lesson.kind == "game" and "roll-through" in lesson.condition.casefold()
        for lesson in store.lessons()
    )
    assert any(
        lesson.kind == "drill" and lesson.partner_job.startswith("Open harder")
        for lesson in store.lessons()
    )
    assert len(store.classes()) >= 4
    assert "sparring" in with_sparring.markup.casefold()
    assert "game" in with_game.markup.casefold()
    assert "Open harder" in with_drill.markup


def test_empty_class_is_refused_and_there_is_no_class_cap(tmp_path):
    with CoachApp(tmp_path) as app:
        _pack(app)
        url = _sheet(app, mode="edit")
        page = _Page(_get(url))
        live = current_sheet(app.store, "Tight waist", "gi")
        roll = live.classes[1].lessons[2]
        trilemma = live.classes[1].lessons[0]
        page = _Page(_post(url, _form(page, f"remove-{roll.id}")["inputs"]))
        page = _Page(_post(url, _form(page, f"remove-{trilemma.id}")["inputs"]))
        after_second = current_sheet(app.store, "Tight waist", "gi")
        last_block = after_second.classes[0].lessons[0]
        remaining = after_second.classes[0].lessons[2]
        page = _Page(_post(url, _form(page, f"remove-{last_block.id}")["inputs"]))
        refused = _Page(_post(url, _form(page, f"remove-{remaining.id}")["inputs"]))
        after_refuse = current_sheet(app.store, "Tight waist", "gi")
        knee = _named(app.store, "Knee lever")
        live_page = _Page(_get(url))
        sparring_fields = dict(_form(live_page, f"add-map-{knee.id}")["inputs"])
        sparring_fields["kind"] = "sparring"
        sparring_fields["class_index"] = "new"
        sparring_fields["scenario"] = "Half guard bottom."
        opened = _Page(_post(url, sparring_fields))
        game_fields = dict(_form(opened, f"add-map-{knee.id}")["inputs"])
        game_fields["kind"] = "game"
        game_fields["class_index"] = "new"
        game_fields["condition"] = "Bottom must sweep."
        game_class = _Page(_post(url, game_fields))
        drill_fields = dict(_form(game_class, f"add-map-{knee.id}")["inputs"])
        drill_fields["kind"] = "drill"
        drill_fields["class_index"] = "new"
        drill_fields["partner_job"] = "Start light; add frames."
        drill_class = _Page(_post(url, drill_fields))
        final = current_sheet(app.store, "Tight waist", "gi")

    assert len(after_second.classes) == 1
    assert after_second.classes[0].lessons
    assert len(after_refuse.classes) == 1
    assert after_refuse.classes[0].lessons
    assert "lesson" in refused.markup.casefold()
    assert len(final.classes) == 4
    assert [lesson.kind for lesson in final.classes[-1].lessons] == ["drill"]
    assert [lesson.kind for lesson in final.classes[-2].lessons] == ["game"]
    assert [lesson.kind for lesson in final.classes[-3].lessons] == ["sparring"]
    assert "max_classes" not in inspect.getsource(inspect.getmodule(open_sheet))
    assert any(
        item.lesson.kind == "sparring" and item.lesson.scenario == "Half guard bottom."
        for item in app.store.custom_lessons()
    )
    assert "class-card" in drill_class.markup


def test_add_lesson_pulls_custom_search_hierarchy_or_map_and_place_saves(tmp_path):
    with CoachApp(tmp_path) as app:
        _pack(app)
        store = app.store
        session = design_session(store, "Tight waist", "gi")
        old = _named(store, "Old school sweep")
        knee = _named(store, "Knee lever")
        custom = store.put_custom_lesson(
            CustomLesson(
                lesson=Lesson(
                    kind="sparring",
                    target=old.id,
                    scenario="Half guard, both may work.",
                )
            )
        )
        url = _sheet(app, mode="edit")
        page = _Page(_get(url))
        sources = add_lesson_sources(store, session)
        pulled = pull_custom(store, custom.id)
        placed_custom = _Page(
            _post(url, _form(page, f"add-custom-{custom.id}")["inputs"])
        )
        searched = _Page(
            _post(
                url,
                {
                    **_form(placed_custom, "search-library")["inputs"],
                    "position": "Half guard",
                    "sweep": "sweep",
                    "ruleset": "gi",
                },
            )
        )
        search_add = dict(_form(searched, f"add-search-{old.id}")["inputs"])
        search_add["kind"] = "technique"
        search_add["class_index"] = "0"
        placed_search = _Page(_post(url, search_add))
        browse_start = _Page(
            _post(url, _form(placed_search, "browse-start-half-guard")["inputs"])
        )
        browse_type = _Page(
            _post(url, _form(browse_start, "browse-type-sweep")["inputs"])
        )
        browse_end = _Page(
            _post(url, _form(browse_type, "browse-end-side-control")["inputs"])
        )
        hierarchy_add = dict(_form(browse_end, f"add-hierarchy-{old.id}")["inputs"])
        hierarchy_add["kind"] = "technique"
        hierarchy_add["class_index"] = "0"
        placed_hierarchy = _Page(_post(url, hierarchy_add))
        map_add = dict(_form(placed_hierarchy, f"add-map-{knee.id}")["inputs"])
        map_add["kind"] = "drill"
        map_add["class_index"] = "1"
        map_add["partner_job"] = "Hold the underhook."
        placed_map = _Page(_post(url, map_add))

    assert any(item.id == custom.id for item in sources.custom)
    assert knee.id in sources.map_moves
    assert pulled[0].scenario == "Half guard, both may work."
    assert any(
        lesson.kind == "sparring" and lesson.scenario == pulled[0].scenario
        for lesson in store.lessons()
    )
    assert "Old school sweep" in searched.markup
    assert any(
        lesson.kind == "technique" and lesson.target == old.id
        for lesson in store.lessons()
    )
    glued = [
        lesson
        for lesson in store.lessons()
        if lesson.kind == "drill" and lesson.target == old.id
    ]
    assert glued
    assert "Half guard" in browse_start.markup or "half-guard" in browse_start.markup
    assert any(
        form["id"] == f"add-hierarchy-{old.id}" for form in browse_end.forms
    )
    assert any(
        lesson.kind == "drill" and lesson.partner_job == "Hold the underhook."
        for lesson in store.lessons()
    )
    saved = store.custom_lessons()
    assert any(
        item.lesson.kind == "sparring"
        and item.lesson.scenario == "Half guard, both may work."
        for item in saved
    )
    assert any(
        item.lesson.kind == "drill" and item.lesson.partner_job == "Hold the underhook."
        for item in saved
    )
    assert "class-card" in placed_custom.markup
    assert "class-card" in placed_map.markup
    assert place_lesson is not None
    assert class_cards is not None
    assert set_mode is not None
    assert set_purpose is not None
    assert add_lesson is not None
    assert remove_lesson is not None
    assert drag_lesson is not None


def test_sheet_screen_calls_domain_apis_and_skips_prototype_html():
    import coach_app.ui_sheet as ui_sheet

    source = inspect.getsource(ui_sheet)
    folded = source.casefold()
    assert "open_sheet" in source
    assert "set_mode" in source
    assert "add_lesson" in source
    assert "remove_lesson" in source
    assert "drag_lesson" in source
    assert "set_purpose" in source
    assert "class_cards" in source
    assert "add_lesson_sources" in source
    assert "place_lesson" in source
    assert "pull_custom" in source
    assert "put_sheet" in source
    assert "put_class" not in source
    assert "put_lesson" not in source
    assert "_sheets" not in source
    assert "_design_sessions" not in source
    assert "prototypes" not in folded
    assert "sample-unit-topic10" not in folded
    assert "playwright" not in folded
    assert "selenium" not in folded
    assert "react" not in folded
    assert "vue" not in folded
    assert "d3" not in folded
    assert "playback" not in folded
    assert "max_classes" not in folded
    assert "<html" not in folded
