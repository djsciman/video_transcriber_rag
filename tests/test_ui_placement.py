"""Review citation placement and coach-authored citations. Drive HTTP, then the store.

Headed browser is unavailable in this environment; urllib is the stand-in.
"""

from __future__ import annotations

import inspect
from html.parser import HTMLParser
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from coach_app.app import CoachApp
from coach_app.placement import citations_for_design_mark, citations_for_lesson
from coach_app.store import Citation, CuratedStore


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
        elif tag == "select":
            name = attrs.get("name")
            if name and self._current_form is not None:
                self._current_form["inputs"].setdefault(name, "")
                self._current_form["_select"] = name
        elif tag == "option" and self._current_form is not None:
            name = self._current_form.get("_select")
            if name and "selected" in attrs:
                self._current_form["inputs"][name] = attrs.get("value", "")
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
        elif tag == "select" and self._current_form is not None:
            self._current_form.pop("_select", None)
        elif tag == "form" and self._current_form is not None:
            self._current_form.pop("_select", None)
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


def _place(app: CoachApp) -> str:
    return app.url.rstrip("/") + "/place"


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


def _citation_form(page: _Page, citation_id: str) -> dict[str, object]:
    for form in page.forms:
        if form["inputs"].get("citation_id") == citation_id:
            return form
    raise AssertionError(citation_id)


def _named(store: CuratedStore, name: str):
    matches = [
        node
        for node in store.enrichment_nodes()
        if node.kind == "named move" and node.name == name
    ]
    assert len(matches) == 1, name
    return matches[0]


def test_place_is_on_the_nav_without_prototype_chrome(tmp_path):
    with CoachApp(tmp_path) as app:
        home = _Page(_get(app.url))
        page = _Page(_get(_place(app)))

    assert any(
        href == "/place" and label in {"Place", "Placement"}
        for href, label in home.links
    )
    assert "placement-pass" in page.sections
    assert "PROTOTYPE" not in page.markup
    assert "Load sample" not in page.markup
    assert "variant" not in page.markup.lower()
    store = CuratedStore.open(tmp_path)
    assert all(citation.named_move_id for citation in store.citations()) or store.citations() == ()


def test_new_citations_appear_in_one_scrollable_pass(tmp_path):
    seeded = CuratedStore.open(tmp_path)
    hip = _named(seeded, "Hip bump sweep")
    linked = seeded.put_citation(
        Citation(movement="Already placed hip bump", named_move_id=hip.id)
    )
    hip_cite = seeded.put_citation(
        Citation(
            movement="Hip bump sweep",
            instructor="John Danaher",
            instructional="Closed Guard",
            volume="Closed Guard.mp4",
            chapter="Hip bump",
            step_bullets=("Sit up", "Post the base hand"),
        )
    )
    unknown = seeded.put_citation(Citation(movement="Unknown sit-up"))

    with CoachApp(tmp_path) as app:
        page = _Page(_get(_place(app)))

    pass_text = page.sections["placement-pass"]
    assert "Hip bump sweep" in pass_text
    assert "Unknown sit-up" in pass_text
    assert "Sit up" in pass_text
    assert "Post the base hand" in pass_text
    assert "John Danaher" in pass_text
    assert "Closed Guard" in pass_text
    assert "overflow" in page.markup
    assert linked.movement not in pass_text
    hip_form = _citation_form(page, hip_cite.id)
    unknown_form = _citation_form(page, unknown.id)
    assert hip_form["method"] == "post"
    assert hip_form["action"] == "/place"
    assert hip_form["inputs"].get("named_move_id") == hip.id
    assert unknown_form["inputs"].get("named_move_id") in {"", None}
    store = CuratedStore.open(tmp_path)
    assert store.citation(hip_cite.id).named_move_id == ""
    assert store.citation(unknown.id).named_move_id == ""


def test_accept_or_correct_writes_one_named_move_link_and_skip_leaves_uncategorized(
    tmp_path,
):
    seeded = CuratedStore.open(tmp_path)
    hip = _named(seeded, "Hip bump sweep")
    kimura = _named(seeded, "Kimura from closed guard")
    hip_cite = seeded.put_citation(Citation(movement="Hip bump sweep"))
    kimura_cite = seeded.put_citation(
        Citation(movement="Kimura from closed guard")
    )
    leftover = seeded.put_citation(Citation(movement="Loose triangle"))

    with CoachApp(tmp_path) as app:
        url = _place(app)
        page = _Page(_get(url))
        hip_form = _citation_form(page, hip_cite.id)
        kimura_form = _citation_form(page, kimura_cite.id)
        leftover_form = _citation_form(page, leftover.id)
        assert hip_form["inputs"].get("named_move_id") == hip.id
        assert kimura_form["inputs"].get("named_move_id") == kimura.id

        after_accept = _Page(
            _post(
                url,
                {
                    "action": "accept",
                    "citation_id": hip_cite.id,
                    "named_move_id": hip_form["inputs"].get("named_move_id", hip.id),
                },
            )
        )
        _post(
            url,
            {
                "action": "correct",
                "citation_id": kimura_cite.id,
                "named_move_id": hip.id,
            },
        )
        after_skip = _Page(
            _post(
                url,
                {
                    "action": "skip",
                    "citation_id": leftover.id,
                    "named_move_id": leftover_form["inputs"].get("named_move_id", ""),
                },
            )
        )

    store = CuratedStore.open(tmp_path)
    assert store.citation(hip_cite.id).named_move_id == hip.id
    assert store.citation(kimura_cite.id).named_move_id == hip.id
    assert store.citation(leftover.id).named_move_id == ""
    assert hip_cite.id not in {
        form["inputs"].get("citation_id") for form in after_accept.forms
    }
    remaining = {
        form["inputs"].get("citation_id") for form in after_skip.forms
    }
    assert leftover.id in remaining
    assert hip_cite.id not in remaining
    assert kimura_cite.id not in remaining
    assert citations_for_lesson(store, hip.id) == (
        store.citation(hip_cite.id),
        store.citation(kimura_cite.id),
    )
    assert leftover.id not in {
        item.id for item in citations_for_lesson(store, hip.id)
    }


def test_pass_can_run_again_on_uncategorized(tmp_path):
    seeded = CuratedStore.open(tmp_path)
    hip = _named(seeded, "Hip bump sweep")
    kimura = _named(seeded, "Kimura from closed guard")
    leftover = seeded.put_citation(Citation(movement="House sit-up"))

    with CoachApp(tmp_path) as app:
        url = _place(app)
        page = _Page(_get(url))
        _post(
            url,
            {
                "action": "skip",
                "citation_id": leftover.id,
                "named_move_id": _citation_form(page, leftover.id)["inputs"].get(
                    "named_move_id", ""
                ),
            },
        )
        later = _Page(_get(url))
        _post(
            url,
            {
                "action": "correct",
                "citation_id": leftover.id,
                "named_move_id": kimura.id,
            },
        )
        done = _Page(_get(url))

    store = CuratedStore.open(tmp_path)
    assert leftover.id in {
        form["inputs"].get("citation_id") for form in later.forms
    }
    assert leftover.movement in later.sections["placement-pass"]
    assert leftover.id not in {
        form["inputs"].get("citation_id") for form in done.forms
    }
    assert store.citation(leftover.id).named_move_id == kimura.id
    assert citations_for_design_mark(store, kimura.id) == (
        store.citation(leftover.id),
    )
    assert citations_for_design_mark(store, hip.id) == ()


def test_coach_authored_citation_stores_movement_and_bullets_on_a_named_move(
    tmp_path,
):
    seeded = CuratedStore.open(tmp_path)
    hip = _named(seeded, "Hip bump sweep")

    with CoachApp(tmp_path) as app:
        url = _place(app)
        page = _Page(_get(url))
        author = _form(page, "author")
        fields = dict(author["inputs"])
        fields.update(
            {
                "action": "author",
                "movement": "Hip bump sweep",
                "step_bullets": "Sit up\nPost the base hand\nBump and roll",
                "named_move_id": hip.id,
            }
        )
        _post(url, fields)

    store = CuratedStore.open(tmp_path)
    assert len(store.citations()) == 1
    placed = store.citations()[0]
    assert placed.movement == "Hip bump sweep"
    assert placed.step_bullets == ("Sit up", "Post the base hand", "Bump and roll")
    assert placed.instructional is None
    assert placed.volume is None
    assert placed.chapter is None
    assert placed.showings == ()
    assert placed.named_move_id == hip.id
    assert all(showing.playback_link is None for showing in placed.showings)
    assert citations_for_lesson(store, hip.id) == (placed,)
    assert citations_for_design_mark(store, hip.id) == (placed,)


def test_uncategorized_citations_stay_off_lessons_and_design_marks(tmp_path):
    seeded = CuratedStore.open(tmp_path)
    hip = _named(seeded, "Hip bump sweep")
    linked = seeded.put_citation(
        Citation(movement="Hip bump sweep", named_move_id=hip.id)
    )
    loose = seeded.put_citation(Citation(movement="Unplaced hip bump"))

    with CoachApp(tmp_path) as app:
        page = _Page(_get(_place(app)))
        _post(
            _place(app),
            {
                "action": "skip",
                "citation_id": loose.id,
            },
        )

    store = CuratedStore.open(tmp_path)
    on_pass = {
        form["inputs"].get("citation_id")
        for form in page.forms
        if form["inputs"].get("citation_id")
    }
    assert loose.movement in page.sections["placement-pass"]
    assert loose.id in on_pass
    assert linked.id not in on_pass
    assert store.citation(loose.id).named_move_id == ""
    assert citations_for_lesson(store, hip.id) == (linked,)
    assert citations_for_design_mark(store, hip.id) == (linked,)
    assert loose not in citations_for_lesson(store, hip.id)
    assert loose not in citations_for_design_mark(store, hip.id)


def test_placement_screen_does_not_import_prototype_html():
    import coach_app.ui_placement as ui_placement

    source = inspect.getsource(ui_placement)
    folded = source.casefold()
    assert "prototypes" not in folded
    assert "sample-analysis-topic8" not in folded
    assert "enrichment-categories-topic26" not in folded
    assert "<html" not in folded
    assert "propose_placement_pass" in source
    assert "apply_placement_decisions" in source
    assert "write_coach_authored_citation" in source
    assert "PlacementAdvisor" in source
    assert "PlacementDecision" in source
