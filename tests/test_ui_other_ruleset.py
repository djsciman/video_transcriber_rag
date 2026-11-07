"""Mark and welcome other-ruleset material. Drive HTTP, then the store.

Headed browser is unavailable in this environment; urllib is the stand-in.
"""

from __future__ import annotations

import inspect
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

from coach_app.app import CoachApp
from coach_app.store import CuratedStore, Instructional
from coach_app.topics import OTHER_RULESET_CAVEAT


class _Page(HTMLParser):
    def __init__(self, markup: str) -> None:
        super().__init__()
        self.markup = markup
        self.text_parts: list[str] = []
        self.links: list[tuple[str, str]] = []
        self.forms: list[dict[str, object]] = []
        self._current_form: dict[str, object] | None = None
        self._current_href = ""
        self._link_text: list[str] = []
        self.feed(markup)

    def handle_starttag(self, tag, attrs) -> None:
        attrs = dict(attrs)
        if tag == "a":
            self._current_href = attrs.get("href", "")
            self._link_text = []
        elif tag == "form":
            self._current_form = {
                "action": attrs.get("action", ""),
                "method": attrs.get("method", "get").lower(),
                "id": attrs.get("id", ""),
                "inputs": {},
                "buttons": [],
            }
        elif tag == "input":
            name = attrs.get("name", "")
            if name and self._current_form is not None:
                self._current_form["inputs"][name] = attrs.get("value", "")
        elif tag == "button":
            name = attrs.get("name", "")
            value = attrs.get("value", "")
            if self._current_form is not None:
                self._current_form["buttons"].append({"name": name, "value": value})
                if name:
                    self._current_form["inputs"].setdefault(name, value)

    def handle_endtag(self, tag) -> None:
        if tag == "a":
            self.links.append((self._current_href, "".join(self._link_text).strip()))
            self._current_href = ""
            self._link_text = []
        elif tag == "form" and self._current_form is not None:
            self.forms.append(self._current_form)
            self._current_form = None

    def handle_data(self, data) -> None:
        if self._current_href:
            self._link_text.append(data)
        self.text_parts.append(data)

    @property
    def text(self) -> str:
        return " ".join(part.strip() for part in self.text_parts if part.strip())


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


def _curate_url(app: CoachApp) -> str:
    return app.url.rstrip("/") + "/curate"


def _knee_cut_volume() -> dict:
    return {
        "video_file": "Half Guard Passing and Dynamic Pins - Volume 1.mp4",
        "chapters": [{"title": "The knee cut", "start": 0.0, "end": 180.0}],
        "segments": [
            {
                "start": 12.5,
                "end": 20.0,
                "text": "frame the far hip",
                "source": "SPEECH",
            },
        ],
    }


def _write_volume(path: Path, volume: dict) -> Path:
    path.write_text(json.dumps(volume), encoding="utf-8")
    return path


def _accept_gi(store: CuratedStore):
    return store.accept(
        {
            "movement": "Knee cut",
            "instructor": "John Danaher",
            "chapter": "The knee cut",
            "cleaned_statement": "Frame the far hip and cut the knee to mount.",
            "step_bullets": ("Frame the far hip.", "Cut the knee to mount."),
            "details": ({"speech_start": 12.5, "text": "frame the far hip"},),
        },
        instructional="Half Guard Passing and Dynamic Pins",
        video_file="Half Guard Passing and Dynamic Pins - Volume 1.mp4",
    )


def _accept_no_gi(store: CuratedStore):
    return store.accept(
        {
            "movement": "Arm drag",
            "instructor": "John Danaher",
            "chapter": "The arm drag",
            "cleaned_statement": "Pull the arm and take the back.",
            "step_bullets": ("Pull the arm.", "Take the back."),
            "details": ({"speech_start": 8.0, "text": "pull the arm"},),
        },
        instructional="Master The Move Arm Drags",
        video_file="Master The Move Arm Drags - Volume 1.mp4",
    )


def _mark_form(page: _Page, citation_id: str) -> dict[str, object]:
    for form in page.forms:
        inputs = form["inputs"]
        if inputs.get("citation_id") == citation_id and inputs.get("action") == "mark":
            return form
    raise AssertionError("accepted showing is missing the mark-aside form")


def _welcome_form(page: _Page, instructional: str) -> dict[str, object]:
    for form in page.forms:
        inputs = form["inputs"]
        if inputs.get("instructional") == instructional and "welcome" in {
            button["name"] for button in form["buttons"]
        } | set(inputs):
            return form
    raise AssertionError(f"topic page is missing the welcome form for {instructional!r}")


def _open_topic(app: CoachApp, name: str, ruleset: str) -> _Page:
    return _Page(
        _post(
            urljoin(app.url, "/topics"),
            {"name": name, "ruleset": ruleset},
        )
    )


def test_marking_a_showing_stores_a_caveat(tmp_path):
    seeded = CuratedStore.open(tmp_path)
    citation = _accept_gi(seeded)
    volume = _write_volume(tmp_path / "knee.json", _knee_cut_volume())

    with CoachApp(tmp_path) as app:
        _post(
            _curate_url(app),
            {
                "action": "load",
                "volume_path": str(volume),
                "instructor": "John Danaher",
                "instructional": "Half Guard Passing and Dynamic Pins",
            },
        )
        page = _Page(_get(_curate_url(app)))
        form = _mark_form(page, citation.id)
        marked = _Page(_post(_curate_url(app), dict(form["inputs"])))

    assert OTHER_RULESET_CAVEAT in marked.text
    assert "caveat" in marked.text.casefold()
    store = CuratedStore.open(tmp_path)
    stored = store.citation(citation.id)
    assert stored is not None
    assert stored.showings[0].caveat == OTHER_RULESET_CAVEAT
    assert store.lessons() == ()


def test_open_topic_offers_each_matching_other_ruleset_instructional(tmp_path):
    seeded = CuratedStore.open(tmp_path)
    _accept_gi(seeded)
    _accept_no_gi(seeded)
    seeded.put_instructional(
        Instructional(
            instructor="Jacob Couch",
            name="Finishing Leg Locks",
            ruleset="no-gi",
        )
    )

    with CoachApp(tmp_path) as app:
        page = _open_topic(app, "Knee cut", "gi")
        form = _welcome_form(page, "Master The Move Arm Drags")

    assert "Master The Move Arm Drags" in page.text
    assert "Finishing Leg Locks" not in page.text
    names = [
        form["inputs"].get("instructional")
        for form in page.forms
        if "welcome" in {button["name"] for button in form["buttons"]} | set(form["inputs"])
    ]
    assert names == ["Master The Move Arm Drags"]
    values = {button["value"] for button in form["buttons"] if button["name"] == "welcome"}
    assert "yes" in values
    assert "no" in values
    store = CuratedStore.open(tmp_path)
    assert store.other_ruleset_choice(
        "Knee cut", "gi", "Master The Move Arm Drags"
    ) is None
    assert store.lessons() == ()


def test_welcome_yes_or_no_is_kept_and_a_later_choice_replaces(tmp_path):
    seeded = CuratedStore.open(tmp_path)
    _accept_no_gi(seeded)

    with CoachApp(tmp_path) as app:
        page = _open_topic(app, "Knee cut", "gi")
        form = _welcome_form(page, "Master The Move Arm Drags")
        fields = dict(form["inputs"])
        fields["welcome"] = "yes"
        welcomed = _Page(_post(urljoin(app.url, form["action"]), fields))
        store = CuratedStore.open(tmp_path)
        choice = store.other_ruleset_choice(
            "Knee cut", "gi", "Master The Move Arm Drags"
        )
        assert choice is not None
        assert choice.yes is True
        assert choice.caveat == OTHER_RULESET_CAVEAT
        assert OTHER_RULESET_CAVEAT in welcomed.text
        assert store.lessons() == ()

        later_form = _welcome_form(welcomed, "Master The Move Arm Drags")
        later_fields = dict(later_form["inputs"])
        later_fields["welcome"] = "no"
        declined = _Page(_post(urljoin(app.url, later_form["action"]), later_fields))

    store = CuratedStore.open(tmp_path)
    replaced = store.other_ruleset_choice(
        "Knee cut", "gi", "Master The Move Arm Drags"
    )
    assert replaced is not None
    assert replaced.yes is False
    assert not getattr(replaced, "caveat", None)
    assert OTHER_RULESET_CAVEAT not in declined.text
    assert store.lessons() == ()


def test_welcomed_instructional_does_not_pack_a_lesson(tmp_path):
    seeded = CuratedStore.open(tmp_path)
    _accept_no_gi(seeded)

    with CoachApp(tmp_path) as app:
        page = _open_topic(app, "Knee cut", "gi")
        form = _welcome_form(page, "Master The Move Arm Drags")
        fields = dict(form["inputs"])
        fields["welcome"] = "yes"
        _post(urljoin(app.url, form["action"]), fields)

    store = CuratedStore.open(tmp_path)
    assert store.other_ruleset_choice(
        "Knee cut", "gi", "Master The Move Arm Drags"
    ).yes is True
    assert store.lessons() == ()
    assert store.classes() == ()


def test_screens_call_domain_helpers_and_do_not_import_prototypes():
    import coach_app.ui_curate as curate
    import coach_app.ui_topics as topics

    curate_source = inspect.getsource(curate)
    topic_source = inspect.getsource(topics)
    for source in (curate_source, topic_source):
        lowered = source.casefold()
        assert "prototypes/" not in source
        assert "playwright" not in lowered
        assert "selenium" not in lowered
        assert "browser" not in lowered
        assert "convert(" not in source
    assert "mark_other_ruleset_showing" in curate_source
    assert "welcome_other_ruleset" in topic_source
    assert "other_ruleset_instructionals" in topic_source
    assert "OTHER_RULESET_CAVEAT" in topic_source
    assert "OTHER_RULESET_CAVEAT" in curate_source
