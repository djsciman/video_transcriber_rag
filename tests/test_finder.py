"""Finder organizes the live enrichment catalog. Drive HTTP, then assert the store.

Headed browser is unavailable in this environment; urllib is the stand-in.
"""

from __future__ import annotations

import inspect
from html.parser import HTMLParser
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from coach_app.app import CoachApp
from coach_app.library import search_library
from coach_app.placement import citations_for_design_mark, citations_for_lesson, put_catalog_system
from coach_app.store import Citation, CuratedStore, Instructional


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
        self._current_href = ""
        self._link_text: list[str] = []
        self._current_form: dict[str, object] | None = None
        self._select_name = ""
        self._select_selected = False
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


def _finder(app: CoachApp) -> str:
    return app.url.rstrip("/") + "/finder"


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


def test_finder_is_on_the_nav_without_prototype_chrome(tmp_path):
    with CoachApp(tmp_path) as app:
        home = _Page(_get(app.url))
        page = _Page(_get(_finder(app)))

    assert any(href == "/finder" and label == "Finder" for href, label in home.links)
    assert "Starting position" in page.text
    assert "Type of move" in page.text
    assert "Ending position or submission" in page.text
    assert "Named-move leaves" in page.text
    assert "Uncategorized" in page.text
    assert "PROTOTYPE" not in page.markup
    assert "Load sample" not in page.markup
    assert "Guided walkthroughs" not in page.markup
    assert "Current state" not in page.markup
    assert "variant" not in page.markup.lower()
    assert "PROTOTYPE" not in home.markup


def test_hierarchy_browse_and_search_reach_named_moves(tmp_path):
    with CoachApp(tmp_path) as app:
        url = _finder(app)
        page = _Page(_get(url))
        starts = _form(page, "start-half-guard")
        assert starts["method"] == "post"
        assert starts["action"] == "/finder"
        page = _Page(_post(url, starts["inputs"]))
        assert "Pass" in page.sections.get("types", "")
        page = _Page(_post(url, _form(page, "type-pass")["inputs"]))
        assert "Side control" in page.sections.get("ends", "")
        page = _Page(_post(url, _form(page, "end-side-control")["inputs"]))
        assert "Knee slice pass" in page.sections.get("named-moves", "")

        search = _form(page, "search")
        fields = dict(search["inputs"])
        fields["query"] = "Morote-gari"
        found = _Page(_post(url, fields))

    assert "Double leg takedown" in found.sections.get("search-results", found.text)
    store = CuratedStore.open(tmp_path)
    hits = store.search_enrichment("Morote-gari")
    assert any(node.name == "Double leg takedown" for node in hits)
    knee = _named(store, "Knee slice pass")
    assert knee.start_id == "half-guard"
    assert knee.type_of_move == "pass"
    assert knee.end_id == "side-control"


def test_one_position_identity_and_submissions_are_end_only(tmp_path):
    with CoachApp(tmp_path) as app:
        url = _finder(app)
        page = _Page(_get(url))
        starts = page.sections.get("starts", "")
        assert "Mount" in starts
        assert "Loop choke" not in starts
        mount_start = _form(page, "start-mount")["inputs"]["start"]

        page = _Page(_post(url, _form(page, "start-closed-guard")["inputs"]))
        page = _Page(_post(url, _form(page, "type-sweep")["inputs"]))
        ends = page.sections.get("ends", "")
        assert "Mount" in ends
        assert "position" in ends
        mount_end = _form(page, "end-mount")["inputs"]["end"]
        assert mount_start == mount_end == "mount"

        page = _Page(_get(url))
        page = _Page(_post(url, _form(page, "start-closed-guard")["inputs"]))
        page = _Page(_post(url, _form(page, "type-submission")["inputs"]))
        assert "Armbar" in page.sections.get("ends", "")
        assert "submission" in page.sections.get("ends", "")
        assert "start-loop-choke" not in {form["id"] for form in page.forms}

        found = _Page(
            _post(url, {"action": "search", "query": "Loop choke"})
        )

    assert "Loop choke" in found.sections.get("search-results", found.text)
    store = CuratedStore.open(tmp_path)
    starts = store.browse_hierarchy()
    assert all(node.kind == "position" for node in starts)
    assert "Loop choke" not in {node.name for node in starts}
    loop = next(node for node in store.enrichment_nodes() if node.name == "Loop choke")
    assert loop.kind == "submission"
    mounts = [node for node in store.enrichment_nodes() if node.name == "Mount"]
    assert len(mounts) == 1
    assert mounts[0].id == "mount"


def test_uncategorized_bucket_is_visible_and_withheld_from_lessons(tmp_path):
    seeded = CuratedStore.open(tmp_path)
    hip = _named(seeded, "Hip bump sweep")
    linked = seeded.put_citation(
        Citation(movement="Hip bump sweep", named_move_id=hip.id)
    )
    seeded.put_citation(Citation(movement="Knee weave pass"))

    with CoachApp(tmp_path) as app:
        page = _Page(_get(_finder(app)))

    uncat = page.sections.get("uncategorized", "")
    assert "Knee weave pass" in uncat
    assert "Uncategorized" in uncat
    assert "Hip bump sweep" not in uncat

    store = CuratedStore.open(tmp_path)
    offered_on_lesson = citations_for_lesson(store, hip.id)
    offered_on_mark = citations_for_design_mark(store, hip.id)
    assert offered_on_lesson == (linked,)
    assert offered_on_mark == (linked,)
    assert all(item.named_move_id == hip.id for item in offered_on_lesson)
    assert any(not item.named_move_id for item in store.citations())


def test_add_rename_move_delete_keep_or_drop_citation_links(tmp_path):
    seeded = CuratedStore.open(tmp_path)
    half = next(node for node in seeded.enrichment_nodes() if node.name == "Half guard")
    knee = _named(seeded, "Knee slice pass")
    old_school = _named(seeded, "Old school sweep")
    knee_citation = seeded.put_citation(
        Citation(movement="Knee cut", named_move_id=knee.id)
    )
    sweep_citation = seeded.put_citation(
        Citation(movement="Old school", named_move_id=old_school.id)
    )

    with CoachApp(tmp_path) as app:
        url = _finder(app)
        page = _Page(_get(url))
        add_fields = dict(_form(page, "add")["inputs"])
        add_fields.update({"kind": "position", "name": "Coach position", "family": "guard"})
        page = _Page(_post(url, add_fields))
        assert "Coach position" in page.sections.get("starts", page.text)

        rename_fields = dict(_form(page, "rename")["inputs"])
        rename_fields.update({"node_id": half.id, "name": "Half-guard"})
        page = _Page(_post(url, rename_fields))
        assert "Half-guard" in page.text

        rename_fields = dict(_form(page, "rename")["inputs"])
        rename_fields.update({"node_id": knee.id, "name": "Knee cut pass"})
        _post(url, rename_fields)

        move_fields = dict(_form(page, "move")["inputs"])
        move_fields.update(
            {
                "node_id": knee.id,
                "start_id": "mount",
                "type_of_move": "pass",
                "end_id": "side-control",
            }
        )
        _post(url, move_fields)

        delete_fields = dict(_form(page, "delete")["inputs"])
        delete_fields.update({"node_id": old_school.id})
        _post(url, delete_fields)

    store = CuratedStore.open(tmp_path)
    added = next(node for node in store.enrichment_nodes() if node.name == "Coach position")
    assert added.kind == "position"
    assert added.family == "guard"
    assert store.enrichment_node(half.id).name == "Half-guard"
    assert store.enrichment_node(knee.id).name == "Knee cut pass"
    assert store.citation(knee_citation.id).named_move_id == knee.id
    moved = store.enrichment_node(knee.id)
    assert moved.start_id == "mount"
    assert moved.type_of_move == "pass"
    assert moved.end_id == "side-control"
    assert store.enrichment_node(old_school.id) is None
    assert store.citation(sweep_citation.id).named_move_id == ""


def test_later_runtime_keeps_catalog_edits(tmp_path):
    with CoachApp(tmp_path) as app:
        url = _finder(app)
        page = _Page(_get(url))
        fields = dict(_form(page, "add")["inputs"])
        fields.update({"kind": "position", "name": "Worm half", "family": "guard"})
        _post(url, fields)
        knee = _named(app.store, "Knee slice pass")
        rename = dict(_form(page, "rename")["inputs"])
        rename.update({"node_id": knee.id, "name": "Coach knee slice"})
        _post(url, rename)

    with CoachApp(tmp_path) as later:
        url = _finder(later)
        page = _Page(_get(url))
        found = _Page(_post(url, {"action": "search", "query": "Coach knee slice"}))

    assert "Worm half" in page.text
    assert "Coach knee slice" in found.text
    store = CuratedStore.open(tmp_path)
    assert any(node.name == "Worm half" for node in store.enrichment_nodes())
    assert any(node.name == "Coach knee slice" for node in store.enrichment_nodes())
    assert all(
        node.name != "Knee slice pass"
        for node in store.enrichment_nodes()
        if node.kind == "named move"
    )


def test_finder_does_not_import_prototype_html():
    import coach_app.ui_finder as ui_finder

    source = inspect.getsource(ui_finder)
    folded = source.casefold()
    assert "prototypes" not in folded
    assert "enrichment-categories-topic26" not in folded
    assert "<html" not in folded
    assert "put_enrichment_node" in source
    assert "rename_enrichment_node" in source
    assert "move_enrichment_node" in source
    assert "delete_enrichment_node" in source
    assert "browse_hierarchy" in source
    assert "search_enrichment" in source or "search_library" in source
    assert "put_catalog_system" in source


def test_dimensional_search_shows_matching_named_moves(tmp_path):
    seeded = CuratedStore.open(tmp_path)
    old = _named(seeded, "Old school sweep")
    seeded.put_instructional(
        Instructional(instructor="Emily Kwok", name="Old School", ruleset="gi")
    )
    seeded.put_citation(
        Citation(
            movement="Old school sweep",
            instructor="Emily Kwok",
            instructional="Old School",
            named_move_id=old.id,
        )
    )

    with CoachApp(tmp_path) as app:
        url = _finder(app)
        page = _Page(_get(url))
        search = dict(_form(page, "search")["inputs"])
        assert "position" in search
        assert "sweep" in search or "type" in page.markup.casefold()
        assert "submission" in search
        assert "instructor" in search
        assert "ruleset" in search
        search.update(
            {
                "position": "Half guard",
                "sweep": "sweep",
                "instructor": "Emily Kwok",
                "ruleset": "gi",
            }
        )
        found = _Page(_post(url, search))

    results = found.sections.get("search-results", found.text)
    assert "Old school sweep" in results
    store = CuratedStore.open(tmp_path)
    hits = search_library(
        store,
        position="Half guard",
        sweep="sweep",
        instructor="Emily Kwok",
        ruleset="gi",
    )
    assert any(getattr(hit, "name", None) == "Old school sweep" for hit in hits)


def test_finder_adds_and_lists_catalog_systems(tmp_path):
    seeded = CuratedStore.open(tmp_path)
    come_up = next(
        node
        for node in seeded.enrichment_nodes()
        if node.kind == "named move" and node.name == "Old school sweep"
    )
    knee = _named(seeded, "Knee slice pass")

    with CoachApp(tmp_path) as app:
        url = _finder(app)
        page = _Page(_get(url))
        add_fields = dict(_form(page, "add")["inputs"])
        assert add_fields["kind"]
        assert "system" in page.markup.casefold()
        add_fields.update(
            {
                "kind": "system",
                "name": "Half guard dilemma",
                "members": f"{come_up.id},{knee.id}",
            }
        )
        page = _Page(_post(url, add_fields))

    assert "Half guard dilemma" in page.text
    store = CuratedStore.open(tmp_path)
    systems = [node for node in store.enrichment_nodes() if node.kind == "system"]
    added = next(node for node in systems if node.name == "Half guard dilemma")
    assert len(added.members) >= 2
    assert come_up.id in added.members
    assert knee.id in added.members
    assert put_catalog_system is not None
