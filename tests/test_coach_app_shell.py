"""Coach-facing application shell. Drive HTTP, then assert through the store."""

import inspect
import subprocess
import sys
from html.parser import HTMLParser
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from coach_app.app import CoachApp
from coach_app.store import CuratedStore, Topic


class _Page(HTMLParser):
    def __init__(self, markup: str) -> None:
        super().__init__()
        self.title = ""
        self.text_parts: list[str] = []
        self.links: list[tuple[str, str]] = []
        self.inputs: dict[str, str] = {}
        self.forms: list[dict[str, object]] = []
        self._in_title = False
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

    def handle_endtag(self, tag) -> None:
        if tag == "title":
            self._in_title = False
        elif tag == "a":
            self.links.append((self._current_href, "".join(self._link_text).strip()))
            self._current_href = ""
            self._link_text = []
        elif tag == "form" and self._current_form is not None:
            self.forms.append(self._current_form)
            self._current_form = None

    def handle_data(self, data) -> None:
        if self._in_title:
            self.title += data
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


def test_coach_opens_home_and_empty_topics_are_valid(tmp_path):
    with CoachApp(tmp_path) as app:
        markup = _get(app.url)
    page = _Page(markup)

    assert "coach" in page.title.lower()
    assert any(href == "/" and label == "Home" for href, label in page.links)
    assert "No topics yet." in page.text
    assert "student login" not in page.text.lower()
    assert "PROTOTYPE" not in markup
    assert "Load sample" not in markup
    store = CuratedStore.open(tmp_path)
    assert store.topics() == ()


def test_home_lists_topics_already_in_the_store(tmp_path):
    seeded = CuratedStore.open(tmp_path)
    seeded.put_topic(Topic(name="Knee cut", ruleset="gi"))

    with CoachApp(tmp_path) as app:
        page = _Page(_get(app.url))

    assert "Knee cut" in page.text
    assert "gi" in page.text
    store = CuratedStore.open(tmp_path)
    assert store.topics()[0].name == "Knee cut"
    assert store.topics()[0].ruleset == "gi"


def test_coach_sets_video_root_and_transcript_folder_from_the_form(tmp_path):
    with CoachApp(tmp_path) as app:
        home = _Page(_get(app.url))
        form = next(item for item in home.forms if "video_root" in item["inputs"])
        action = form["action"]
        assert form["method"] == "post"
        assert "video_root" in form["inputs"]
        assert "transcript_folder" in form["inputs"]
        markup = _post(
            app.url.rstrip("/") + action,
            {
                "video_root": r"D:\BJJ library",
                "transcript_folder": "Half Guard Passing and Dynamic Pins",
            },
        )
        page = _Page(markup)

    assert page.inputs["video_root"] == r"D:\BJJ library"
    assert page.inputs["transcript_folder"] == (
        "Half Guard Passing and Dynamic Pins"
    )
    store = CuratedStore.open(tmp_path)
    assert store.video_root() == r"D:\BJJ library"
    assert store.transcript_folder() == "Half Guard Passing and Dynamic Pins"


def test_closing_and_opening_again_keeps_settings(tmp_path):
    with CoachApp(tmp_path) as app:
        _post(
            app.url.rstrip("/") + "/settings",
            {
                "video_root": r"E:\instructionals",
                "transcript_folder": "The Handle",
            },
        )

    with CoachApp(tmp_path) as later:
        page = _Page(_get(later.url))

    assert page.inputs["video_root"] == r"E:\instructionals"
    assert page.inputs["transcript_folder"] == "The Handle"
    store = CuratedStore.open(tmp_path)
    assert store.video_root() == r"E:\instructionals"
    assert store.transcript_folder() == "The Handle"


def test_first_launch_has_the_live_catalog(tmp_path):
    with CoachApp(tmp_path) as app:
        _get(app.url)

    store = CuratedStore.open(tmp_path)
    named = tuple(
        node for node in store.enrichment_nodes() if node.kind == "named move"
    )
    assert named
    assert any(node.name == "Knee slice pass" for node in named)


def test_first_launch_keeps_an_already_imported_catalog(tmp_path):
    existing = CuratedStore.open(tmp_path)
    knee = next(
        node
        for node in existing.enrichment_nodes()
        if node.kind == "named move" and node.name == "Knee slice pass"
    )
    existing.rename_enrichment_node(knee.id, "Coach knee slice")

    with CoachApp(tmp_path) as app:
        _get(app.url)

    store = CuratedStore.open(tmp_path)
    assert store.enrichment_node(knee.id).name == "Coach knee slice"
    assert all(
        node.name != "Knee slice pass"
        for node in store.enrichment_nodes()
        if node.kind == "named move"
    )


def test_module_help_is_for_the_coach():
    result = subprocess.run(
        [sys.executable, "-m", "coach_app", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "coach" in result.stdout.lower()
    assert "student login" not in result.stdout.lower()
    assert "127.0.0.1" in result.stdout
    assert "0.0.0.0" not in result.stdout
    help_text = result.stdout.casefold()
    assert "this machine" in help_text or "localhost" in help_text or "127.0.0.1" in result.stdout
    from coach_app.app import CoachApp

    assert inspect.signature(CoachApp.__init__).parameters["host"].default == "127.0.0.1"
