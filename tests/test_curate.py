"""Curate a volume into accepted citations. Drive HTTP, then assert the store."""

from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from coach_app.app import CoachApp
from coach_app.store import CuratedStore


class _Page(HTMLParser):
    def __init__(self, markup: str) -> None:
        super().__init__()
        self.title = ""
        self.text_parts: list[str] = []
        self.links: list[tuple[str, str]] = []
        self.inputs: dict[str, str] = {}
        self.forms: list[dict[str, object]] = []
        self._in_title = False
        self._in_textarea = False
        self._textarea_name = ""
        self._textarea_parts: list[str] = []
        self._current_form: dict[str, object] | None = None
        self._current_href = ""
        self._link_text: list[str] = []
        self.feed(markup)

    def handle_starttag(self, tag, attrs) -> None:
        attrs = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "a":
            self._current_href = attrs.get("href", "")
            self._link_text = []
        elif tag == "form":
            self._current_form = {
                "action": attrs.get("action", ""),
                "method": attrs.get("method", "get").lower(),
                "inputs": {},
            }
        elif tag == "input":
            name = attrs.get("name")
            if name:
                value = attrs.get("value", "")
                self.inputs[name] = value
                if self._current_form is not None:
                    self._current_form["inputs"][name] = value
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
            if self._textarea_name:
                self.inputs[self._textarea_name] = value
                if self._current_form is not None:
                    self._current_form["inputs"][self._textarea_name] = value
            self._in_textarea = False
            self._textarea_name = ""
        elif tag == "form" and self._current_form is not None:
            self.forms.append(self._current_form)
            self._current_form = None

    def handle_data(self, data) -> None:
        if self._in_title:
            self.title += data
        if self._current_href:
            self._link_text.append(data)
        if self._in_textarea:
            self._textarea_parts.append(data)
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


def _write_volume(path: Path, volume: dict) -> Path:
    path.write_text(json.dumps(volume), encoding="utf-8")
    return path


def _closed_guard_volume() -> dict:
    return {
        "video_file": "Closed Guard.mp4",
        "chapters": [
            {"title": "Closed Guard", "start": 0.0, "end": 120.0},
            {"title": "Arm Bar", "start": 120.0, "end": 240.0},
        ],
        "segments": [
            {
                "start": 10.0,
                "end": 14.0,
                "text": "from closed guard",
                "source": "SPEECH",
            },
            {
                "start": 40.0,
                "end": 50.0,
                "text": "your inside arm shoots the underhook",
                "source": "SPEECH",
            },
            {
                "start": 130.0,
                "end": 140.0,
                "text": "break the grip and finish the arm bar",
                "source": "SPEECH",
            },
        ],
    }


def _untitled_volume() -> dict:
    return {
        "video_file": "Volume 8.mp4",
        "chapters": [
            {
                "title": "11 Z GUARD, KIMURA, AND NARRATED ROLLING",
                "start": 0.0,
                "end": 9581.0,
            }
        ],
        "segments": [
            {"start": 3.0, "end": 8.0, "text": "Zeg guard", "source": "SPEECH"},
            {"start": 70.0, "end": 80.0, "text": "stay in Z-guard", "source": "SPEECH"},
        ],
    }


def _knee_cut_volume() -> dict:
    return {
        "video_file": "Half Guard Passing and Dynamic Pins - Volume 1.mp4",
        "chapters": [
            {"title": "The knee cut", "start": 0.0, "end": 180.0},
            {"title": "Frame", "start": 180.0, "end": 300.0},
        ],
        "segments": [
            {
                "start": 12.5,
                "end": 20.0,
                "text": "frame the far hip",
                "source": "SPEECH",
            },
            {
                "start": 90.0,
                "end": 100.0,
                "text": "cut the knee to mount",
                "source": "SPEECH",
            },
            {
                "start": 200.0,
                "end": 210.0,
                "text": "build the frame",
                "source": "SPEECH",
            },
        ],
    }


def _load(app: CoachApp, volume_path: Path, *, instructor: str, instructional: str) -> _Page:
    return _Page(
        _post(
            _curate_url(app),
            {
                "action": "load",
                "volume_path": str(volume_path),
                "instructor": instructor,
                "instructional": instructional,
            },
        )
    )


def _proposal_form(page: _Page, movement: str) -> dict[str, object]:
    for form in page.forms:
        inputs = form["inputs"]
        raw = inputs.get("proposal")
        if not raw:
            continue
        proposal = json.loads(raw)
        if proposal.get("movement") == movement:
            return form
    raise AssertionError(f"no proposal form for {movement!r}")


def _accepted_form(page: _Page, movement: str) -> dict[str, object]:
    for form in page.forms:
        inputs = form["inputs"]
        if inputs.get("citation_id") and inputs.get("movement") == movement:
            return form
    raise AssertionError(f"no accepted form for {movement!r}")


def test_curate_is_on_the_nav(tmp_path):
    with CoachApp(tmp_path) as app:
        home = _Page(_get(app.url))
        page = _Page(_get(_curate_url(app)))

    assert any(href == "/curate" and label == "Curate" for href, label in home.links)
    assert "volume" in page.text.casefold()
    assert "PROTOTYPE" not in page.text
    store = CuratedStore.open(tmp_path)
    assert store.citations() == ()
    assert store.volumes() == ()


def test_nested_parts_visible_and_untitled_parts_called_out(tmp_path):
    nested = _write_volume(tmp_path / "closed.json", _closed_guard_volume())
    untitled = _write_volume(tmp_path / "untitled.json", _untitled_volume())

    with CoachApp(tmp_path) as app:
        nested_page = _load(
            app,
            nested,
            instructor="John Danaher",
            instructional="Closed Guard",
        )
        untitled_page = _load(
            app,
            untitled,
            instructor="Lachlan Giles",
            instructional="Half Guard Anthology",
        )

    assert "Closed Guard" in nested_page.text
    assert "Arm Bar" in nested_page.text
    assert "from closed guard" in nested_page.text
    assert "finish the arm bar" in nested_page.text
    assert "Untitled" in untitled_page.text
    assert "Zeg guard" in untitled_page.text
    store = CuratedStore.open(tmp_path)
    assert store.citations() == ()
    assert store.volumes() == ()


def test_proposed_statements_appear_before_the_store_writes(tmp_path):
    volume = _write_volume(tmp_path / "closed.json", _closed_guard_volume())

    with CoachApp(tmp_path) as app:
        page = _load(
            app,
            volume,
            instructor="John Danaher",
            instructional="Closed Guard",
        )

    form = _proposal_form(page, "Closed Guard")
    proposal = json.loads(form["inputs"]["proposal"])
    assert proposal["movement"] == "Closed Guard"
    assert proposal["chapter"] == "Closed Guard"
    assert "from closed guard" in page.text
    assert "proposal" in form["inputs"]
    store = CuratedStore.open(tmp_path)
    assert store.citations() == ()
    assert store.instructionals() == ()
    assert store.volumes() == ()


def test_correct_then_accept_writes_the_citation(tmp_path):
    volume = _write_volume(tmp_path / "closed.json", _closed_guard_volume())

    with CoachApp(tmp_path) as app:
        page = _load(
            app,
            volume,
            instructor="John Danaher",
            instructional="Closed Guard",
        )
        form = _proposal_form(page, "Closed Guard")
        inputs = dict(form["inputs"])
        _post(
            _curate_url(app),
            {
                "action": "accept",
                "proposal": inputs["proposal"],
                "instructor": inputs.get("instructor", "John Danaher"),
                "instructional": inputs.get("instructional", "Closed Guard"),
                "video_file": inputs.get("video_file", "Closed Guard.mp4"),
                "movement": "Overclasp",
                "step_bullets": "Sit up.\nShoot the underhook.",
            },
        )

    store = CuratedStore.open(tmp_path)
    assert len(store.citations()) == 1
    citation = store.citations()[0]
    assert citation.movement == "Overclasp"
    assert citation.step_bullets == ("Sit up.", "Shoot the underhook.")
    assert citation.cleaned_statement == "Sit up. Shoot the underhook."
    assert citation.instructor == "John Danaher"
    assert citation.instructional == "Closed Guard"
    assert citation.volume == "Closed Guard.mp4"
    assert citation.chapter == "Closed Guard"
    assert store.volumes()[0].video_file_name == "Closed Guard.mp4"
    assert store.instructionals()[0].name == "Closed Guard"


def test_dismiss_writes_nothing(tmp_path):
    volume = _write_volume(tmp_path / "closed.json", _closed_guard_volume())

    with CoachApp(tmp_path) as app:
        page = _load(
            app,
            volume,
            instructor="John Danaher",
            instructional="Closed Guard",
        )
        form = _proposal_form(page, "Closed Guard")
        after = _Page(
            _post(
                _curate_url(app),
                {
                    "action": "dismiss",
                    "proposal": form["inputs"]["proposal"],
                    "instructor": "John Danaher",
                    "instructional": "Closed Guard",
                    "video_file": "Closed Guard.mp4",
                },
            )
        )

    assert "from closed guard" not in after.text.casefold() or "Overclasp" not in after.text
    remaining = [
        json.loads(form["inputs"]["proposal"])
        for form in after.forms
        if form["inputs"].get("proposal")
    ]
    assert all(item["movement"] != "Closed Guard" for item in remaining)
    store = CuratedStore.open(tmp_path)
    assert store.citations() == ()
    assert store.volumes() == ()
    assert store.instructionals() == ()


def test_correct_after_accept_replaces_and_remove_drops(tmp_path):
    volume = _write_volume(tmp_path / "knee.json", _knee_cut_volume())

    with CoachApp(tmp_path) as app:
        page = _load(
            app,
            volume,
            instructor="John Danaher",
            instructional="Half Guard Passing and Dynamic Pins",
        )
        form = _proposal_form(page, "The knee cut")
        accepted = _Page(
            _post(
                _curate_url(app),
                {
                    "action": "accept",
                    "proposal": form["inputs"]["proposal"],
                    "instructor": form["inputs"].get(
                        "instructor", "John Danaher"
                    ),
                    "instructional": form["inputs"].get(
                        "instructional", "Half Guard Passing and Dynamic Pins"
                    ),
                    "video_file": form["inputs"].get(
                        "video_file",
                        "Half Guard Passing and Dynamic Pins - Volume 1.mp4",
                    ),
                    "movement": form["inputs"].get("movement", "The knee cut"),
                    "step_bullets": form["inputs"].get("step_bullets", ""),
                },
            )
        )
        accepted_form = _accepted_form(accepted, "The knee cut")
        citation_id = accepted_form["inputs"]["citation_id"]
        corrected = _Page(
            _post(
                _curate_url(app),
                {
                    "action": "correct",
                    "citation_id": citation_id,
                    "movement": "Knee slice",
                    "step_bullets": (
                        "Inside arm shoots the underhook under their inside arm.\n"
                        "Outside arm blocks their outside arm from the crossface."
                    ),
                },
            )
        )

        store = CuratedStore.open(tmp_path)
        assert len(store.citations()) == 1
        citation = store.citations()[0]
        assert citation.id == citation_id
        assert citation.movement == "Knee slice"
        assert citation.step_bullets[0].startswith("Inside arm")
        assert citation.instructor == "John Danaher"
        assert citation.instructional == "Half Guard Passing and Dynamic Pins"
        assert citation.volume == (
            "Half Guard Passing and Dynamic Pins - Volume 1.mp4"
        )
        assert citation.chapter == "The knee cut"
        assert citation.showings
        assert "The knee cut" not in corrected.text or "Knee slice" in corrected.text
        assert "Knee slice" in corrected.text

        _post(
            _curate_url(app),
            {"action": "remove", "citation_id": citation_id},
        )

    store = CuratedStore.open(tmp_path)
    assert store.citations() == ()
    assert store.citation(citation_id) is None


def test_playback_available_and_missing_still_show_timestamp_and_volume(tmp_path):
    volume = _write_volume(tmp_path / "knee.json", _knee_cut_volume())
    library = tmp_path / "library"
    folder = library / "Half Guard Passing and Dynamic Pins"
    folder.mkdir(parents=True)
    video = folder / "Half Guard Passing and Dynamic Pins - Volume 1.mp4"
    video.write_bytes(b"")

    with CoachApp(tmp_path) as app:
        _post(
            app.url.rstrip("/") + "/settings",
            {
                "video_root": str(library),
                "transcript_folder": "Half Guard Passing and Dynamic Pins",
            },
        )
        present = _load(
            app,
            volume,
            instructor="John Danaher",
            instructional="Half Guard Passing and Dynamic Pins",
        )
        assert "12.5" in present.text
        assert "Half Guard Passing and Dynamic Pins - Volume 1.mp4" in present.text
        assert "available" in present.text.casefold()

        form = _proposal_form(present, "The knee cut")
        accepted = _Page(
            _post(
                _curate_url(app),
                {
                    "action": "accept",
                    "proposal": form["inputs"]["proposal"],
                    "instructor": "John Danaher",
                    "instructional": "Half Guard Passing and Dynamic Pins",
                    "video_file": (
                        "Half Guard Passing and Dynamic Pins - Volume 1.mp4"
                    ),
                    "movement": "The knee cut",
                    "step_bullets": form["inputs"].get("step_bullets", ""),
                },
            )
        )
        assert "12.5" in accepted.text
        assert "available" in accepted.text.casefold()

        video.unlink()
        missing = _Page(_get(_curate_url(app)))

    assert "12.5" in missing.text
    assert "Half Guard Passing and Dynamic Pins - Volume 1.mp4" in missing.text
    assert "missing" in missing.text.casefold()
    store = CuratedStore.open(tmp_path)
    assert store.citations()
    assert store.citations()[0].showings[0].timestamp == 12.5
