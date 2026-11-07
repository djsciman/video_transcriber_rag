"""Open and remove a topic from the home screen. Drive HTTP, then the store."""

from __future__ import annotations

import inspect
from html.parser import HTMLParser
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

from coach_app.app import CoachApp
from coach_app.store import (
    Class,
    CuratedStore,
    Lesson,
    OtherRulesetChoice,
    SetAside,
    Topic,
    Unit,
)


class _Page(HTMLParser):
    def __init__(self, markup: str) -> None:
        super().__init__()
        self.text_parts: list[str] = []
        self.links: list[tuple[str, str]] = []
        self.forms: list[dict[str, object]] = []
        self.fields: list[dict[str, str]] = []
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
                "fields": [],
            }
        elif tag in {"input", "button", "select", "textarea"}:
            name = attrs.get("name", "")
            field = {
                "tag": tag,
                "name": name,
                "type": attrs.get("type", "submit" if tag == "button" else "text"),
                "value": attrs.get("value", ""),
            }
            self.fields.append(field)
            if self._current_form is not None:
                self._current_form["fields"].append(field)

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


def _open_form(page: _Page) -> dict[str, object]:
    for form in page.forms:
        names = {field["name"] for field in form["fields"]}
        if "name" in names and "ruleset" in names and "video_root" not in names:
            return form
    raise AssertionError("home is missing the open-topic form")


def _remove_form(page: _Page) -> dict[str, object]:
    for form in page.forms:
        names = {field["name"] for field in form["fields"]}
        if "remove" in names:
            return form
    raise AssertionError("topic page is missing the remove form")


def _topic_units(store: CuratedStore, name: str, ruleset: str) -> tuple[Unit, ...]:
    return tuple(
        unit
        for unit in store.units()
        if unit.topic_name == name and unit.topic_ruleset == ruleset
    )


def _editable_named(page: _Page, name: str) -> list[dict[str, str]]:
    return [
        field
        for field in page.fields
        if field["name"] == name and field["type"] not in {"hidden", "submit"}
    ]


def test_submit_name_and_ruleset_lists_the_topic_on_home(tmp_path):
    with CoachApp(tmp_path) as app:
        home = _Page(_get(app.url))
        form = _open_form(home)
        markup = _post(
            urljoin(app.url, form["action"]),
            {"name": "Knee cut", "ruleset": "gi"},
        )
        listed = _Page(_get(app.url))

    assert "Knee cut" in _Page(markup).text
    assert any("Knee cut" in label and "gi" in label for _, label in listed.links)
    store = CuratedStore.open(tmp_path)
    assert store.topic("Knee cut", "gi") is not None
    assert store.topic("Knee cut", "gi").name == "Knee cut"
    assert store.topic("Knee cut", "gi").ruleset == "gi"
    units = _topic_units(store, "Knee cut", "gi")
    assert len(units) == 1


def test_blank_submit_opens_nothing_and_trailing_spaces_strip(tmp_path):
    with CoachApp(tmp_path) as app:
        form = _open_form(_Page(_get(app.url)))
        action = urljoin(app.url, form["action"])
        blank = _Page(_post(action, {"name": "   ", "ruleset": "gi"}))
        _post(action, {"name": "Knee cut  ", "ruleset": "no-gi"})
        home = _Page(_get(app.url))

    assert "No topics yet." in blank.text
    assert any("Knee cut" in label and "no-gi" in label for _, label in home.links)
    assert all("Knee cut  " not in label for _, label in home.links)
    store = CuratedStore.open(tmp_path)
    assert store.topics() == (store.topic("Knee cut", "no-gi"),)
    assert store.topic("Knee cut  ", "no-gi") is None
    assert store.topic("Knee cut", "no-gi").name == "Knee cut"
    assert len(_topic_units(store, "Knee cut", "no-gi")) == 1


def test_same_pair_reopens_the_kept_topic_and_its_unit(tmp_path):
    with CoachApp(tmp_path) as app:
        form = _open_form(_Page(_get(app.url)))
        action = urljoin(app.url, form["action"])
        _post(action, {"name": "Knee cut  ", "ruleset": "gi"})
        first = CuratedStore.open(tmp_path)
        first_unit = _topic_units(first, "Knee cut", "gi")[0]
        _post(action, {"name": "Knee cut", "ruleset": "gi"})
        home = _Page(_get(app.url))

    labels = [label for _, label in home.links if "Knee cut" in label]
    assert len(labels) == 1
    store = CuratedStore.open(tmp_path)
    assert store.topics() == (store.topic("Knee cut", "gi"),)
    units = _topic_units(store, "Knee cut", "gi")
    assert len(units) == 1
    assert units[0].id == first_unit.id


def test_hyphen_and_space_are_distinct_topics(tmp_path):
    with CoachApp(tmp_path) as app:
        form = _open_form(_Page(_get(app.url)))
        action = urljoin(app.url, form["action"])
        _post(action, {"name": "Knee cut", "ruleset": "gi"})
        _post(action, {"name": "Knee-cut", "ruleset": "gi"})
        home = _Page(_get(app.url))

    labels = [label for _, label in home.links if "Knee" in label]
    assert any("Knee cut" in label and "Knee-cut" not in label for label in labels)
    assert any("Knee-cut" in label for label in labels)
    store = CuratedStore.open(tmp_path)
    names = {(topic.name, topic.ruleset) for topic in store.topics()}
    assert names == {("Knee cut", "gi"), ("Knee-cut", "gi")}
    assert len(_topic_units(store, "Knee cut", "gi")) == 1
    assert len(_topic_units(store, "Knee-cut", "gi")) == 1


def test_name_and_ruleset_are_fixed_on_the_open_topic(tmp_path):
    with CoachApp(tmp_path) as app:
        form = _open_form(_Page(_get(app.url)))
        _post(urljoin(app.url, form["action"]), {"name": "Knee cut", "ruleset": "gi"})
        home = _Page(_get(app.url))
        href = next(h for h, label in home.links if "Knee cut" in label and "gi" in label)
        page = _Page(_get(urljoin(app.url, href)))

    assert "Knee cut" in page.text
    assert "gi" in page.text
    assert _editable_named(page, "name") == []
    assert _editable_named(page, "ruleset") == []
    store = CuratedStore.open(tmp_path)
    opened = store.topic("Knee cut", "gi")
    assert opened.name == "Knee cut"
    assert opened.ruleset == "gi"


def test_remove_clears_belonging_records_and_the_pair_can_open_again(tmp_path):
    seeded = CuratedStore.open(tmp_path)
    seeded.put_topic(Topic(name="Knee cut", ruleset="gi", system="Cut to mount."))
    seeded.put_topic(Topic(name="Knee cut", ruleset="no-gi"))
    seeded.put_other_ruleset_choice(
        OtherRulesetChoice(
            topic_name="Knee cut",
            topic_ruleset="gi",
            instructional="Master The Move Arm Drags",
            yes=True,
        )
    )
    seeded.put_set_aside(
        SetAside(
            topic_name="Knee cut",
            topic_ruleset="gi",
            earlier_topic_name="Half guard",
            earlier_topic_ruleset="gi",
        )
    )
    unit = seeded.put_unit(Unit(topic_name="Knee cut", topic_ruleset="gi"))
    class_record = seeded.put_class(Class(purpose="Cut to mount.", unit_id=unit.id))
    seeded.put_lesson(
        Lesson(
            kind="drill",
            target="knee-cut",
            class_id=class_record.id,
            partner_job="Hold.",
        )
    )
    keep_unit = seeded.put_unit(Unit(topic_name="Knee cut", topic_ruleset="no-gi"))

    with CoachApp(tmp_path) as app:
        home = _Page(_get(app.url))
        href = next(
            h
            for h, label in home.links
            if "Knee cut" in label and "(gi)" in label and "no-gi" not in label
        )
        page = _Page(_get(urljoin(app.url, href)))
        form = _remove_form(page)
        fields = {
            field["name"]: field["value"]
            for field in form["fields"]
            if field["name"]
        }
        _post(urljoin(app.url, form["action"]), fields)
        after = _Page(_get(app.url))
        open_form = _open_form(after)
        _post(
            urljoin(app.url, open_form["action"]),
            {"name": "Knee cut", "ruleset": "gi"},
        )

    store = CuratedStore.open(tmp_path)
    assert store.topic("Knee cut", "no-gi") is not None
    assert store.unit(keep_unit.id) == keep_unit
    reopened = store.topic("Knee cut", "gi")
    assert reopened is not None
    assert reopened.name == "Knee cut"
    assert reopened.ruleset == "gi"
    assert reopened.system == ""
    assert store.other_ruleset_choice(
        "Knee cut", "gi", "Master The Move Arm Drags"
    ) is None
    assert store.set_asides("Knee cut", "gi") == ()
    assert store.unit(unit.id) is None
    assert store.class_record(class_record.id) is None
    gi_units = _topic_units(store, "Knee cut", "gi")
    assert len(gi_units) == 1
    assert gi_units[0].id != unit.id


def test_screens_call_open_and_remove_and_do_not_import_prototypes():
    import coach_app.ui_topics as ui

    source = inspect.getsource(ui)
    lowered = source.casefold()
    assert "open_topic" in source
    assert "remove_topic" in source
    assert "prototypes/" not in source
    assert "playwright" not in lowered
    assert "selenium" not in lowered
    assert "browser" not in lowered
