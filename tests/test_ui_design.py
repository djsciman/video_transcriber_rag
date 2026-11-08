"""Design the unit on the mental map. Drive HTTP, then the store and session.

Headed browser is unavailable in this environment; urllib is the stand-in.
"""

from __future__ import annotations

import inspect
from html.parser import HTMLParser
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from coach_app.app import CoachApp
from coach_app.build import BuildAdvisor, convert, propose
from coach_app.design import ADD_WALK, citations_on_mark, walk_options
from coach_app.placement import put_catalog_system
from coach_app.store import Citation, CuratedStore, EnrichmentNode
from coach_app.ui_design import design_session
from coach_app.ui_sheet import current_sheet
from tests.test_build import TIGHT_WAIST_PARAGRAPH


class _Page(HTMLParser):
    def __init__(self, markup: str) -> None:
        super().__init__()
        self.markup = markup
        self.title = ""
        self.text_parts: list[str] = []
        self.links: list[tuple[str, str]] = []
        self.forms: list[dict[str, object]] = []
        self.sections: dict[str, str] = {}
        self._in_title = False
        self._in_textarea = False
        self._textarea_name = ""
        self._textarea_parts: list[str] = []
        self._current_href = ""
        self._link_text: list[str] = []
        self._current_form: dict[str, object] | None = None
        self._section_id = ""
        self._section_parts: list[str] = []
        self.feed(markup)

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
            name = attrs.get("name")
            if name and self._current_form is not None:
                self._current_form["inputs"][name] = attrs.get("value", "")
        elif tag == "textarea":
            self._in_textarea = True
            self._textarea_name = attrs.get("name", "")
            self._textarea_parts = []
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


def _design(app: CoachApp, name: str = "Tight waist", ruleset: str = "gi") -> str:
    return app.url.rstrip("/") + "/design?" + urlencode({"name": name, "ruleset": ruleset})


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


def _named(store: CuratedStore, name: str):
    matches = [
        node
        for node in store.enrichment_nodes()
        if node.kind == "named move" and node.name == name
    ]
    assert len(matches) == 1, name
    return matches[0]


def _mark_keys(session):
    return {(mark.kind, mark.target) for mark in session.marks}


def _open_topic(app: CoachApp, name: str = "Tight waist", ruleset: str = "gi") -> None:
    _post(app.url.rstrip("/") + "/topics", {"name": name, "ruleset": ruleset})


def _install_tight_waist(store: CuratedStore) -> None:
    if any(
        node.kind == "named move" and node.name == "Knee lever"
        for node in store.enrichment_nodes()
    ):
        return

    def named_move(name, type_of_move, end_id, start_id="half-guard"):
        return store.put_enrichment_node(
            EnrichmentNode(
                kind="named move",
                name=name,
                start_id=start_id,
                type_of_move=type_of_move,
                end_id=end_id,
            )
        )

    named_move("Knee lever", "transition", "half-guard")
    named_move("Tight waist", "transition", "half-guard")
    named_move("Far-leg come-up", "sweep", "side-control")
    named_move("Roll-through sweep", "sweep", "side-control")
    named_move("Back take from tight waist", "back-take", "back-control")
    put_catalog_system(
        store,
        "Tight waist trilemma",
        (
            _named(store, "Far-leg come-up").id,
            _named(store, "Roll-through sweep").id,
            _named(store, "Back take from tight waist").id,
        ),
    )


def _link(store: CuratedStore, named_move, **fields) -> Citation:
    return store.put_citation(Citation(named_move_id=named_move.id, **fields))


def test_design_is_on_the_nav_without_prototype_chrome(tmp_path):
    with CoachApp(tmp_path) as app:
        home = _Page(_get(app.url))
        _open_topic(app)
        page = _Page(_get(_design(app)))

    assert any(href == "/design" and label == "Design" for href, label in home.links)
    assert "add-walk" in page.sections
    assert "map-stage" in page.sections or "design-map" in page.markup
    assert "unit-prompt" in page.sections or 'id="unit-prompt"' in page.markup
    assert "draft" in page.sections or 'id="draft"' in page.markup
    prompt_at = page.markup.find('id="unit-prompt"')
    walk_at = page.markup.find('id="add-walk"')
    canvas_at = page.markup.find('id="map-stage"')
    draft_at = page.markup.find('id="draft"')
    assert 0 <= prompt_at < walk_at < canvas_at < draft_at
    assert "grid-template-columns: minmax(16rem, 22rem)" not in page.markup
    layout_slice = page.markup[walk_at:canvas_at]
    assert "design-layout" not in layout_slice
    assert "Propose canvas and Draft" in page.markup
    assert "Convert canvas to Draft" in page.markup
    assert "Recenter" in page.markup
    assert "Zoom" in page.markup
    assert "Reset marks" in page.markup
    assert "PROTOTYPE" not in page.markup
    assert "Load sample" not in page.markup
    assert "Guided walkthroughs" not in page.markup
    assert "variant" not in page.markup.lower()
    assert "PROTOTYPE" not in home.markup


def test_add_walk_places_occupancy_type_and_named_move_then_replaces_type(tmp_path):
    with CoachApp(tmp_path) as app:
        _open_topic(app)
        url = _design(app)
        store = app.store
        old_school = _named(store, "Old school sweep")
        page = _Page(_get(url))
        assert ADD_WALK[0] in {form["id"].split("-", 1)[0] for form in page.forms}

        page = _Page(_post(url, _form(page, "family-guard")["inputs"]))
        page = _Page(_post(url, _form(page, "position-half-guard")["inputs"]))
        page = _Page(_post(url, _form(page, "occupancy-bottom")["inputs"]))
        after_occ = design_session(store, "Tight waist", "gi")
        assert ("occupancy", "bottom") in _mark_keys(after_occ)
        assert "bottom" in page.markup
        assert "type-sweep" in {form["id"] for form in page.forms}
        assert "type-escape" not in {form["id"] for form in page.forms}

        page = _Page(_post(url, _form(page, "type-sweep")["inputs"]))
        after_type = design_session(store, "Tight waist", "gi")
        assert ("type", "sweep") in _mark_keys(after_type)
        assert "Sweep" in page.markup or "sweep" in page.markup
        page = _Page(_post(url, _form(page, "end-side-control")["inputs"]))
        page = _Page(_post(url, _form(page, f"named-move-{old_school.id}")["inputs"]))

        session = design_session(store, "Tight waist", "gi")
        keys = _mark_keys(session)

    assert "Old school sweep" in page.markup
    assert ("named move", old_school.id) in keys
    assert ("occupancy", "bottom") in keys
    assert ("type", "sweep") not in keys
    store = CuratedStore.open(tmp_path)
    assert store.classes() == ()
    assert store.lessons() == ()
    assert old_school.start_occupancy == "bottom"


def test_family_filters_occupancy_and_type_on_closed_guard_bottom(tmp_path):
    with CoachApp(tmp_path) as app:
        _open_topic(app)
        url = _design(app)
        page = _Page(_get(url))
        page = _Page(_post(url, _form(page, "family-guard")["inputs"]))
        page = _Page(_post(url, _form(page, "position-closed-guard")["inputs"]))
        occ_ids = {form["id"] for form in page.forms}
        assert "occupancy-bottom" in occ_ids
        assert "occupancy-top" in occ_ids
        assert "occupancy-neutral" not in occ_ids
        page = _Page(_post(url, _form(page, "occupancy-bottom")["inputs"]))
        type_ids = {form["id"] for form in page.forms}
        session = design_session(app.store, "Tight waist", "gi")

    assert "type-escape" not in type_ids
    assert "type-pass" not in type_ids
    assert "type-takedown" not in type_ids
    assert "type-sweep" in type_ids
    assert "escape" not in walk_options(app.store, session)
    assert ("occupancy", "bottom") in _mark_keys(session)


def test_empty_canvas_add_keeps_existing_marks(tmp_path):
    with CoachApp(tmp_path) as app:
        _open_topic(app)
        url = _design(app)
        old_school = _named(app.store, "Old school sweep")
        page = _Page(_get(url))
        for form_id in (
            "family-guard",
            "position-half-guard",
            "occupancy-bottom",
            "type-sweep",
            "end-side-control",
            f"named-move-{old_school.id}",
        ):
            page = _Page(_post(url, _form(page, form_id)["inputs"]))
        before = design_session(app.store, "Tight waist", "gi")
        start = _form(page, "start-add")
        after_page = _Page(_post(url, start["inputs"]))
        after = design_session(app.store, "Tight waist", "gi")

    assert ("named move", old_school.id) in _mark_keys(before)
    assert _mark_keys(after) == _mark_keys(before)
    assert "Old school sweep" in after_page.markup
    assert "stroke-dasharray" in after_page.markup
    assert "draft" in after_page.markup


def test_left_click_edits_and_right_click_deletes(tmp_path):
    with CoachApp(tmp_path) as app:
        _open_topic(app)
        url = _design(app)
        old_school = _named(app.store, "Old school sweep")
        page = _Page(_get(url))
        for form_id in (
            "family-guard",
            "position-half-guard",
            "occupancy-bottom",
            "type-sweep",
            "end-side-control",
            f"named-move-{old_school.id}",
        ):
            page = _Page(_post(url, _form(page, form_id)["inputs"]))
        session = design_session(app.store, "Tight waist", "gi")
        named = next(mark for mark in session.marks if mark.kind == "named move")
        edited = _Page(_post(url, _form(page, f"edit-{named.id}")["inputs"]))
        selected = design_session(app.store, "Tight waist", "gi")
        assert selected.selected_id == named.id
        assert "edit-mark" in edited.sections
        assert "Old school sweep" in edited.sections.get("edit-mark", edited.text)
        assert "Coach notes" in edited.sections.get("edit-mark", edited.text)
        deleted = _Page(_post(url, _form(edited, f"delete-{named.id}")["inputs"]))
        after = design_session(app.store, "Tight waist", "gi")

    assert ("named move", old_school.id) not in _mark_keys(after)
    assert old_school.id not in {mark.target for mark in after.marks}
    assert "Old school sweep" not in deleted.sections.get("marks", "")


def test_named_move_edit_withholds_uncategorized_citations(tmp_path):
    seeded = CuratedStore.open(tmp_path)
    old_school = _named(seeded, "Old school sweep")
    linked = seeded.put_citation(
        Citation(movement="Old school grip", named_move_id=old_school.id)
    )
    seeded.put_citation(Citation(movement="Uncategorized tight waist"))

    with CoachApp(tmp_path) as app:
        _open_topic(app)
        url = _design(app)
        page = _Page(_get(url))
        for form_id in (
            "family-guard",
            "position-half-guard",
            "occupancy-bottom",
            "type-sweep",
            "end-side-control",
            f"named-move-{old_school.id}",
        ):
            page = _Page(_post(url, _form(page, form_id)["inputs"]))
        session = design_session(app.store, "Tight waist", "gi")
        mark = next(
            item
            for item in session.marks
            if item.kind == "named move" and item.target == old_school.id
        )
        edited = _Page(_post(url, _form(page, f"edit-{mark.id}")["inputs"]))
        panel = edited.sections.get("edit-mark", "")
        offered = citations_on_mark(
            app.store, design_session(app.store, "Tight waist", "gi"), mark.id
        )
        _post(
            url,
            {
                **_form(edited, f"citation-{linked.id}")["inputs"],
                "citation_id": linked.id,
            },
        )
        chosen = design_session(app.store, "Tight waist", "gi")

    assert linked.movement in panel
    assert "Uncategorized tight waist" not in panel
    assert offered == (linked,)
    assert all(item.named_move_id == old_school.id for item in offered)
    assert (old_school.id, linked.id) in chosen.chosen_citations
    store = CuratedStore.open(tmp_path)
    assert store.classes() == ()
    assert any(not item.named_move_id for item in store.citations())


def test_pan_zoom_recenter_exist_and_design_does_not_pack(tmp_path):
    with CoachApp(tmp_path) as app:
        _open_topic(app)
        page = _Page(_get(_design(app)))

    lowered = page.markup.casefold()
    assert "recenter" in lowered
    assert "zoom" in lowered
    assert "reset marks" in lowered
    assert "applypan" in lowered or "ui.pan" in page.markup
    assert "leader" in lowered or "layoutlabels" in lowered
    assert "put_class" not in lowered
    store = CuratedStore.open(tmp_path)
    assert store.classes() == ()
    assert store.lessons() == ()


def test_design_screen_calls_domain_apis_and_skips_prototype_html():
    import coach_app.ui_design as ui_design

    source = inspect.getsource(ui_design)
    folded = source.casefold()
    assert "open_design" in source
    assert "walk_options" in source
    assert "pick(" in source
    assert "add_named_move" in source
    assert "edit_mark" in source
    assert "delete_mark" in source
    assert "citations_on_mark" in source
    assert "choose_citation" in source
    assert "ADD_WALK" in source
    assert "propose(" in source
    assert "convert(" in source
    assert "BuildAdvisor" in source
    assert "put_design_session" in source
    assert "_design_sessions" not in source
    assert "put_class" not in source
    assert "put_lesson" not in source
    assert "put_enrichment_node" not in source
    assert "prototypes" not in folded
    assert "unit-design-topic28" not in folded
    assert "design-to-draft-topic30" not in folded
    assert "playwright" not in folded
    assert "selenium" not in folded
    assert "react" not in folded
    assert "vue" not in folded
    assert "d3" not in folded
    assert "playback" not in folded


def test_propose_fills_canvas_and_draft_from_the_unit_paragraph(tmp_path):
    with CoachApp(tmp_path) as app:
        _open_topic(app)
        _install_tight_waist(app.store)
        knee = _named(app.store, "Knee lever")
        cite = _link(
            app.store,
            knee,
            movement="Knee lever from half guard",
            step_bullets=(
                "inside foot place next to their inside knee",
                "cut the knee through to mount",
            ),
        )
        url = _design(app)
        page = _Page(
            _post(
                url,
                {
                    **_form(_Page(_get(url)), "propose-draft")["inputs"],
                    "paragraph": TIGHT_WAIST_PARAGRAPH,
                    "action": "propose",
                },
            )
        )
        session = design_session(app.store, "Tight waist", "gi")
        draft_html = page.sections.get("draft", page.text)
        named = {
            app.store.enrichment_node(mark.target).name
            for mark in session.marks
            if mark.kind == "named move"
        }
        packed = [
            packed
            for packed in app.store.classes()
        ]
        lessons = list(app.store.lessons())

    assert named >= {
        "Knee lever",
        "Tight waist",
        "Far-leg come-up",
        "Roll-through sweep",
        "Back take from tight waist",
    }
    assert any(
        app.store.enrichment_node(mark.target).name == "Tight waist trilemma"
        for mark in session.marks
        if mark.kind == "system"
    )
    assert "Knee lever" in page.markup
    assert "Tight waist trilemma" in page.markup
    assert TIGHT_WAIST_PARAGRAPH in page.markup
    units = [
        unit
        for unit in CuratedStore.open(tmp_path).units()
        if unit.topic_name == "Tight waist" and unit.topic_ruleset == "gi"
    ]
    assert len(units) == 1
    assert units[0].paragraph == TIGHT_WAIST_PARAGRAPH
    store = CuratedStore.open(tmp_path)
    assert len(store.classes()) == 2
    assert store.lessons()
    assert cite.id in {cid for lesson in store.lessons() for cid in lesson.citations}
    assert "inside foot place next to their inside knee" in draft_html
    assert "cut the knee through to mount" in draft_html
    assert "Coach fills the partner job." in draft_html
    assert "Playback" not in draft_html
    assert "contenteditable" not in page.markup.casefold()
    assert 'border-style: dashed' in page.markup or "dashed" in page.markup
    assert "class-card" in page.markup
    assert packed and lessons
    techniques = [lesson for lesson in store.lessons() if lesson.kind == "technique"]
    assert _named(store, "Knee lever").id in {lesson.target for lesson in techniques}
    assert propose is not None
    assert BuildAdvisor is not None


def test_convert_packs_a_hand_built_canvas_and_refuses_an_empty_map(tmp_path):
    with CoachApp(tmp_path) as app:
        _open_topic(app)
        url = _design(app)
        empty = _Page(
            _post(
                url,
                {
                    **_form(_Page(_get(url)), "convert-draft")["inputs"],
                    "action": "convert",
                },
            )
        )
        empty_store = list(app.store.classes()), list(app.store.lessons())
        old_school = _named(app.store, "Old school sweep")
        page = _Page(_get(url))
        for form_id in (
            "family-guard",
            "position-half-guard",
            "occupancy-bottom",
            "type-sweep",
            "end-side-control",
            f"named-move-{old_school.id}",
        ):
            page = _Page(_post(url, _form(page, form_id)["inputs"]))
        packed = _Page(
            _post(
                url,
                {
                    **_form(page, "convert-draft")["inputs"],
                    "action": "convert",
                },
            )
        )
        session = design_session(app.store, "Tight waist", "gi")
        draft_html = packed.sections.get("draft", packed.text)

    assert empty_store == ([], [])
    assert "no named moves or systems" in empty.markup.casefold()
    assert "Old school sweep" in packed.markup
    assert ("named move", old_school.id) in _mark_keys(session)
    store = CuratedStore.open(tmp_path)
    assert any(lesson.target == old_school.id for lesson in store.lessons())
    techniques = [lesson for lesson in store.lessons() if lesson.kind == "technique"]
    drills = [lesson for lesson in store.lessons() if lesson.kind == "drill"]
    assert techniques and drills
    assert techniques[0].target == drills[0].target
    assert "Coach fills the partner job." in draft_html
    assert "Playback" not in draft_html
    assert convert is not None


def test_first_draft_is_glued_dashed_class_cards_without_edit_or_playback(tmp_path):
    with CoachApp(tmp_path) as app:
        _open_topic(app)
        _install_tight_waist(app.store)
        url = _design(app)
        page = _Page(
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
        draft_html = page.sections.get("draft", page.text)
        store = app.store
        packed_classes = store.classes()
        lessons = store.lessons()
        names = []
        for lesson in lessons:
            if lesson.kind != "technique":
                continue
            node = store.enrichment_node(lesson.target)
            names.append(node.name if node is not None else lesson.target)

    assert len(packed_classes) == 2
    assert names == [
        "Knee lever",
        "Tight waist",
        "Tight waist trilemma",
        "Roll-through sweep",
    ]
    assert "Far-leg come-up" not in names
    assert "Back take from tight waist" not in names
    assert "Far-leg come-up" not in draft_html
    assert "Tight waist trilemma" in draft_html
    assert "Roll-through sweep" in draft_html
    assert "class-card" in page.markup
    assert "dashed" in page.markup
    assert "<th>Lesson</th>" in page.markup or ">Lesson</th>" in page.markup
    assert "What to run" in draft_html or "What to run" in page.markup
    assert "Playback" not in page.markup
    assert "contenteditable" not in page.markup.casefold()
    assert "Add: " not in draft_html
    assert 'class="tech' in page.markup
    assert 'class="drill' in page.markup
    for lesson in lessons:
        if lesson.kind == "drill":
            assert lesson.partner_job
            assert lesson.partner_job in draft_html
        if lesson.kind == "technique":
            assert lesson.partner_job == ""
    assert "Partner job" in draft_html


def test_restart_restores_map_marks_and_sheet(tmp_path):
    from tests.test_ui_sheet import _pack, _sheet

    with CoachApp(tmp_path) as first:
        _pack(first)
        session = design_session(first.store, "Tight waist", "gi")
        marks = _mark_keys(session)
        live_sheet = current_sheet(first.store, "Tight waist", "gi")

    with CoachApp(tmp_path) as later:
        restored = design_session(later.store, "Tight waist", "gi")
        design = _Page(_get(_design(later)))
        sheet = _Page(_get(_sheet(later, mode="read")))
        later_sheet = current_sheet(later.store, "Tight waist", "gi")

    assert marks
    assert _mark_keys(restored) == marks
    assert "Knee lever" in design.markup
    assert "Knee lever" in sheet.markup
    assert later_sheet is not None
    assert live_sheet is not None
    assert len(later_sheet.classes) == len(live_sheet.classes)
