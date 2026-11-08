"""Briefing memo screen. Drive HTTP, then the store and brief_topic.

Headed browser is unavailable in this environment; urllib is the stand-in.
"""

from __future__ import annotations

import inspect
from html.parser import HTMLParser
from urllib.parse import urlencode, urljoin, urlparse
from urllib.request import Request, urlopen

from coach_app.app import CoachApp
from coach_app.briefing import BriefingAdvisor, brief_topic
from coach_app.store import CuratedStore, SetAside
from coach_app.system import choose_system, system_conflicts, SystemAdvisor
from coach_app.topics import open_topic
from tests.test_briefing import (
    ConflictingAdvisor,
    _accept,
    _half_guard_fixtures,
    _knee_lever_bullets,
)


class _Page(HTMLParser):
    def __init__(self, markup: str) -> None:
        super().__init__()
        self.markup = markup
        self.title = ""
        self.text_parts: list[str] = []
        self.links: list[tuple[str, str]] = []
        self.sections: dict[str, str] = {}
        self.forms: list[dict[str, object]] = []
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
        if data.strip() and not self._in_textarea:
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


def _form(page: _Page, action: str, **matches: str) -> dict[str, object]:
    for form in page.forms:
        inputs = form["inputs"]
        if inputs.get("action") != action:
            continue
        if all(inputs.get(key) == value for key, value in matches.items()):
            return form
    raise AssertionError(f"missing {action} form {matches}")


def _briefing_url(app: CoachApp, name: str, ruleset: str) -> str:
    return app.url.rstrip("/") + "/briefing?" + urlencode(
        {"name": name, "ruleset": ruleset}
    )


def _open_topic_page(app: CoachApp, name: str, ruleset: str) -> _Page:
    return _Page(
        _get(
            app.url.rstrip("/")
            + "/topics?"
            + urlencode({"name": name, "ruleset": ruleset})
        )
    )


def test_briefing_names_the_open_topic(tmp_path):
    seeded = CuratedStore.open(tmp_path)
    topic, *_rest = _half_guard_fixtures(seeded)

    with CoachApp(tmp_path) as app:
        page = _Page(_get(_briefing_url(app, topic.name, topic.ruleset)))

    assert topic.name in page.text
    assert topic.ruleset in page.text
    assert "half guard" in page.title.casefold() or "half guard" in page.text.casefold()
    store = CuratedStore.open(tmp_path)
    memo = brief_topic(store, "half guard", "gi", BriefingAdvisor())
    assert memo.topic_name == topic.name == "half guard"
    assert memo.topic_ruleset == topic.ruleset == "gi"
    assert store.topic("half guard", "gi") == topic


def test_same_ruleset_citations_show_bullets_and_playback(tmp_path):
    seeded = CuratedStore.open(tmp_path)
    topic, underhook, tight_waist, _giles, knee_cut = _half_guard_fixtures(seeded)

    with CoachApp(tmp_path) as app:
        page = _Page(_get(_briefing_url(app, topic.name, topic.ruleset)))

    same = page.sections.get("same-ruleset", page.text)
    assert underhook.movement in same
    assert tight_waist.movement in same
    assert knee_cut.movement not in same
    assert "John Danaher" in same
    assert "Half Guard BJJ Fundamentals - Go Further Faster" in same
    assert "Getting to Underhooks" in same
    for bullet in _knee_lever_bullets():
        assert bullet in same
    assert "inside arm" in same
    assert "their inside arm" in same or "their waist" in same
    assert "@5.26" in page.markup
    assert underhook.volume in same
    store = CuratedStore.open(tmp_path)
    memo = brief_topic(store, "half guard", "gi", BriefingAdvisor())
    movements = {citation.movement for citation in memo.same_ruleset_citations}
    assert underhook.movement in movements
    assert tight_waist.movement in movements
    assert knee_cut.movement not in movements
    shown = next(
        citation
        for citation in memo.same_ruleset_citations
        if citation.movement == underhook.movement
    )
    assert shown.step_bullets == _knee_lever_bullets()
    assert shown.showings[0].playback_link.endswith("@5.26")


def test_other_ruleset_asks_why_paths_differ_and_shows_caveat_lists(tmp_path):
    seeded = CuratedStore.open(tmp_path)
    topic, _underhook, _tight_waist, giles, _knee_cut = _half_guard_fixtures(seeded)

    with CoachApp(tmp_path) as app:
        page = _Page(_get(_briefing_url(app, topic.name, topic.ruleset)))

    other = page.sections.get("other-ruleset-briefing", page.text)
    folded = other.casefold()
    assert "why" in folded
    assert "differ" in folded
    assert "winner" not in folded
    assert giles.movement in other
    assert "may transfer" in folded
    assert "depends" in folded
    store = CuratedStore.open(tmp_path)
    memo = brief_topic(store, "half guard", "gi", BriefingAdvisor())
    assert giles in memo.other_ruleset_citations
    assert "why" in memo.other_ruleset_question.casefold()
    assert "differ" in memo.other_ruleset_question.casefold()
    assert not hasattr(memo, "winner")
    assert memo.caveat is not None
    assert memo.caveat.may_transfer
    assert memo.caveat.depends_on_unshared_tools
    for item in memo.caveat.may_transfer:
        assert item in other
    for item in memo.caveat.depends_on_unshared_tools:
        assert item in other


def test_unwelcomed_other_ruleset_stays_off_the_screen(tmp_path):
    seeded = CuratedStore.open(tmp_path)
    topic, *_rest = _half_guard_fixtures(seeded, welcome_giles=False)

    with CoachApp(tmp_path) as app:
        page = _Page(_get(_briefing_url(app, topic.name, topic.ruleset)))

    assert "Underhook Switch" not in page.text
    assert "why" not in page.text.casefold() or "differ" not in page.text.casefold()
    store = CuratedStore.open(tmp_path)
    memo = brief_topic(store, "half guard", "gi", BriefingAdvisor())
    assert memo.other_ruleset_citations == ()
    assert memo.caveat is None
    assert memo.other_ruleset_question == ""


def test_same_ruleset_disagreement_shows_both_sides_with_citations(tmp_path):
    seeded = CuratedStore.open(tmp_path)
    topic, underhook, tight_waist, giles, _knee_cut = _half_guard_fixtures(seeded)
    camp = _accept(
        seeded,
        movement="Never camp the tight waist from half guard",
        instructor="Lachlan Giles",
        instructional="Half Guard Anthology Gi",
        video_file="Half Guard Anthology Gi - Volume 1.mp4",
        chapter="Sit up instead of a tight waist",
        cleaned_statement=(
            "From half guard never camp a tight waist; sit up and elevate."
        ),
        step_bullets=(
            "inside shoulder sit up to their inside shoulder",
            "hips elevate instead of wrapping a tight waist",
        ),
        speech_start=100.0,
        ruleset="gi",
    )
    advisor = ConflictingAdvisor({tight_waist.movement, camp.movement})

    with CoachApp(tmp_path) as app:
        agreeing = _Page(_get(_briefing_url(app, topic.name, topic.ruleset)))
        app.store._briefing_advisor = advisor
        page = _Page(_get(_briefing_url(app, topic.name, topic.ruleset)))

    assert "disagreement" not in agreeing.sections
    disagreement = page.sections.get("disagreement", "")
    assert disagreement
    assert tight_waist.movement in disagreement
    assert camp.movement in disagreement
    assert "John Danaher" in disagreement
    assert "Lachlan Giles" in disagreement
    assert giles.movement not in disagreement
    store = CuratedStore.open(tmp_path)
    memo = brief_topic(store, "half guard", "gi", advisor)
    sides = {side.citation.movement for side in memo.disagreement}
    assert tight_waist.movement in sides
    assert camp.movement in sides
    assert giles.movement not in sides
    assert len(memo.disagreement) == 2
    assert store.topic(topic.name, topic.ruleset) == topic
    assert underhook.movement in {
        citation.movement for citation in memo.same_ruleset_citations
    }


def test_briefing_does_not_split_classes(tmp_path):
    seeded = CuratedStore.open(tmp_path)
    topic, *_rest = _half_guard_fixtures(seeded)

    with CoachApp(tmp_path) as app:
        page = _Page(_get(_briefing_url(app, topic.name, topic.ruleset)))

    folded = page.text.casefold()
    assert "class card" not in folded
    assert "class-split" not in folded
    assert "class split" not in folded
    store = CuratedStore.open(tmp_path)
    memo = brief_topic(store, "half guard", "gi", BriefingAdvisor())
    assert not hasattr(memo, "classes")
    assert not hasattr(memo, "class_split")
    assert store.classes() == ()
    assert store.lessons() == ()


def test_topic_page_links_to_the_briefing(tmp_path):
    seeded = CuratedStore.open(tmp_path)
    topic, *_rest = _half_guard_fixtures(seeded)

    with CoachApp(tmp_path) as app:
        topic_page = _open_topic_page(app, topic.name, topic.ruleset)
        href = next(
            h
            for h, label in topic_page.links
            if "briefing" in label.casefold() or "briefing" in h.casefold()
        )
        briefing = _Page(_get(urljoin(app.url, href)))

    parsed = urlparse(href)
    assert parsed.path == "/briefing"
    assert topic.name in briefing.text
    assert topic.ruleset in briefing.text
    store = CuratedStore.open(tmp_path)
    assert store.topic(topic.name, topic.ruleset) == topic


def test_screens_call_brief_topic_and_do_not_import_prototypes():
    import coach_app.ui_briefing as ui

    source = inspect.getsource(ui)
    lowered = source.casefold()
    assert "brief_topic" in source
    assert "BriefingAdvisor" in source
    assert "choose_system" in source
    assert "set_aside" in source
    assert "end_set_aside" in source
    assert "system_conflicts" in source
    assert "prototypes/" not in source
    assert "sample-analysis-topic8" not in lowered
    assert "playwright" not in lowered
    assert "selenium" not in lowered
    assert "browser" not in lowered
    assert "put_class" not in source
    assert "put_lesson" not in source
    assert "<html" not in source
    assert "system_history" not in source
    assert "pill-nogi" not in source
    assert 'class="question"' not in source
    assert "pill-no-gi" in source


def _camp_citation(store: CuratedStore):
    return _accept(
        store,
        movement="Never camp the tight waist from half guard",
        instructor="Lachlan Giles",
        instructional="Half Guard Anthology Gi",
        video_file="Half Guard Anthology Gi - Volume 1.mp4",
        chapter="Sit up instead of a tight waist",
        cleaned_statement=(
            "From half guard never camp a tight waist; sit up and elevate."
        ),
        step_bullets=(
            "inside shoulder sit up to their inside shoulder",
            "hips elevate instead of wrapping a tight waist",
        ),
        speech_start=100.0,
        ruleset="gi",
    )


def _conflict_advisor(tight_waist, camp) -> ConflictingAdvisor:
    return ConflictingAdvisor({tight_waist.movement, camp.movement})


def test_system_words_start_empty_and_replace_in_place(tmp_path):
    seeded = CuratedStore.open(tmp_path)
    topic, *_rest = _half_guard_fixtures(seeded)

    with CoachApp(tmp_path) as app:
        empty = _Page(_get(_briefing_url(app, topic.name, topic.ruleset)))
        form = _form(empty, "choose_system")
        assert form["method"] == "post"
        assert form["action"] == "/briefing"
        assert form["inputs"].get("words") == ""
        first = _Page(
            _post(
                app.url.rstrip("/") + form["action"],
                {**form["inputs"], "words": "Cut to mount."},
            )
        )
        later_form = _form(first, "choose_system")
        later = _Page(
            _post(
                app.url.rstrip("/") + later_form["action"],
                {**later_form["inputs"], "words": "Knee slice then mount."},
            )
        )

    system = later.sections.get("system", later.text)
    assert later_form["inputs"].get("words") == "Cut to mount."
    assert _form(later, "choose_system")["inputs"].get("words") == "Knee slice then mount."
    assert "Cut to mount." not in system
    assert "history" not in system.casefold()
    store = CuratedStore.open(tmp_path)
    stored = store.topic("half guard", "gi")
    assert stored is not None
    assert stored.system == "Knee slice then mount."
    assert not hasattr(stored, "system_history")
    assert not hasattr(store, "system_history")
    assert store.topics()


def test_conflicting_earlier_systems_show_topic_name_and_live_words(tmp_path):
    seeded = CuratedStore.open(tmp_path)
    topic, _underhook, tight_waist, _giles, _knee_cut = _half_guard_fixtures(seeded)
    camp = _camp_citation(seeded)
    knee_cut = open_topic(seeded, "Knee cut", "gi")
    toreando = open_topic(seeded, "Toreando", "gi")
    other = open_topic(seeded, "Knee cut", "no-gi")
    choose_system(seeded, knee_cut, "Cut to mount.")
    choose_system(seeded, toreando, "Circle the legs.")
    choose_system(seeded, other, "Arm drag to the back.")
    empty = open_topic(seeded, "Butterfly", "gi")
    advisor = _conflict_advisor(tight_waist, camp)

    with CoachApp(tmp_path) as app:
        app.store._briefing_advisor = advisor
        page = _Page(_get(_briefing_url(app, topic.name, topic.ruleset)))

    disagreement = page.sections.get("disagreement", "")
    assert "Knee cut" in disagreement
    assert "Cut to mount." in disagreement
    assert "Toreando" in disagreement
    assert "Circle the legs." in disagreement
    assert "Arm drag to the back." not in disagreement
    assert "Butterfly" not in disagreement
    assert empty.system == ""
    store = CuratedStore.open(tmp_path)
    notes = system_conflicts(
        store,
        store.topic(topic.name, topic.ruleset),
        (tight_waist, camp),
        SystemAdvisor(),
    )
    names = {note.earlier_topic_name: note.system for note in notes}
    assert names["Knee cut"] == "Cut to mount."
    assert names["Toreando"] == "Circle the legs."
    assert "Butterfly" not in names
    assert all(note.system != "Arm drag to the back." for note in notes)


def test_set_aside_hides_and_ending_shows_again(tmp_path):
    seeded = CuratedStore.open(tmp_path)
    topic, _underhook, tight_waist, _giles, _knee_cut = _half_guard_fixtures(seeded)
    camp = _camp_citation(seeded)
    knee_cut = open_topic(seeded, "Knee cut", "gi")
    choose_system(seeded, knee_cut, "Cut to mount.")
    advisor = _conflict_advisor(tight_waist, camp)

    with CoachApp(tmp_path) as app:
        app.store._briefing_advisor = advisor
        page = _Page(_get(_briefing_url(app, topic.name, topic.ruleset)))
        hidden = _Page(
            _post(
                app.url.rstrip("/") + "/briefing",
                dict(_form(page, "set_aside", earlier_name="Knee cut")["inputs"]),
            )
        )
        disagreement = hidden.sections.get("disagreement", "")
        assert "Cut to mount." not in disagreement
        shown = _Page(
            _post(
                app.url.rstrip("/") + "/briefing",
                dict(
                    _form(hidden, "end_set_aside", earlier_name="Knee cut")["inputs"]
                ),
            )
        )

    assert "Cut to mount." in shown.sections.get("disagreement", "")
    assert "Knee cut" in shown.sections.get("disagreement", "")
    store = CuratedStore.open(tmp_path)
    assert store.set_asides("half guard", "gi") == ()
    notes = system_conflicts(
        store,
        store.topic("half guard", "gi"),
        (tight_waist, camp),
        SystemAdvisor(),
    )
    assert [note.earlier_topic_name for note in notes] == ["Knee cut", "Knee cut"]
    assert notes[0].system == "Cut to mount."


def test_several_set_asides_sit_on_one_topic(tmp_path):
    seeded = CuratedStore.open(tmp_path)
    topic, _underhook, tight_waist, _giles, _knee_cut = _half_guard_fixtures(seeded)
    camp = _camp_citation(seeded)
    knee_cut = open_topic(seeded, "Knee cut", "gi")
    toreando = open_topic(seeded, "Toreando", "gi")
    choose_system(seeded, knee_cut, "Cut to mount.")
    choose_system(seeded, toreando, "Circle the legs.")
    advisor = _conflict_advisor(tight_waist, camp)

    with CoachApp(tmp_path) as app:
        app.store._briefing_advisor = advisor
        page = _Page(_get(_briefing_url(app, topic.name, topic.ruleset)))
        after_knee = _Page(
            _post(
                app.url.rstrip("/") + "/briefing",
                dict(_form(page, "set_aside", earlier_name="Knee cut")["inputs"]),
            )
        )
        after_both = _Page(
            _post(
                app.url.rstrip("/") + "/briefing",
                dict(
                    _form(after_knee, "set_aside", earlier_name="Toreando")["inputs"]
                ),
            )
        )

    disagreement = after_both.sections.get("disagreement", "")
    assert "Cut to mount." not in disagreement
    assert "Circle the legs." not in disagreement
    store = CuratedStore.open(tmp_path)
    stored = store.set_asides("half guard", "gi")
    assert {record.earlier_topic_name for record in stored} == {"Knee cut", "Toreando"}
    assert all(record.topic_name == "half guard" for record in stored)
    assert all(record.topic_ruleset == "gi" for record in stored)
    assert all(record.earlier_topic_ruleset == "gi" for record in stored)
    assert system_conflicts(
        store,
        store.topic("half guard", "gi"),
        (tight_waist, camp),
        SystemAdvisor(),
    ) == ()


def test_advisor_reads_live_words_and_stores_no_frozen_copy(tmp_path):
    seeded = CuratedStore.open(tmp_path)
    topic, _underhook, tight_waist, _giles, _knee_cut = _half_guard_fixtures(seeded)
    camp = _camp_citation(seeded)
    knee_cut = open_topic(seeded, "Knee cut", "gi")
    choose_system(seeded, knee_cut, "Cut to mount.")
    advisor = _conflict_advisor(tight_waist, camp)

    with CoachApp(tmp_path) as app:
        app.store._briefing_advisor = advisor
        page = _Page(_get(_briefing_url(app, topic.name, topic.ruleset)))
        _post(
            app.url.rstrip("/") + "/briefing",
            dict(_form(page, "set_aside", earlier_name="Knee cut")["inputs"]),
        )
        earlier = _Page(_get(_briefing_url(app, "Knee cut", "gi")))
        _post(
            app.url.rstrip("/") + "/briefing",
            {
                **_form(earlier, "choose_system")["inputs"],
                "words": "Knee slice then mount.",
            },
        )
        hidden = _Page(_get(_briefing_url(app, topic.name, topic.ruleset)))
        shown = _Page(
            _post(
                app.url.rstrip("/") + "/briefing",
                dict(
                    _form(hidden, "end_set_aside", earlier_name="Knee cut")["inputs"]
                ),
            )
        )
        _post(
            app.url.rstrip("/") + "/briefing",
            {
                **_form(earlier, "choose_system")["inputs"],
                "words": "Cut, freeze, mount.",
            },
        )
        live = _Page(_get(_briefing_url(app, topic.name, topic.ruleset)))

    disagreement = live.sections.get("disagreement", "")
    assert "Cut, freeze, mount." in disagreement
    assert "Cut to mount." not in disagreement
    assert "Knee slice then mount." not in disagreement
    store = CuratedStore.open(tmp_path)
    record = store.set_asides("half guard", "gi")
    assert record == ()
    assert {field.name for field in SetAside.__dataclass_fields__.values()} == {
        "topic_name",
        "topic_ruleset",
        "earlier_topic_name",
        "earlier_topic_ruleset",
    }
    assert store.topic("Knee cut", "gi").system == "Cut, freeze, mount."
    notes = system_conflicts(
        store,
        store.topic("half guard", "gi"),
        (tight_waist, camp),
        SystemAdvisor(),
    )
    assert notes[0].system == "Cut, freeze, mount."
