"""Open and remove a topic from the coach screens."""

from __future__ import annotations

import html
from urllib.parse import urlencode

from coach_app.app import Screen, add_screen, render_shell
from coach_app.store import CuratedStore, Unit
from coach_app.topics import open_topic, remove_topic


def topic_location(name: str, ruleset: str) -> str:
    return "/topics?" + urlencode({"name": name, "ruleset": ruleset})


def _first(fields: dict[str, list[str]], key: str) -> str:
    values = fields.get(key) or [""]
    return values[0] if values else ""


def _ensure_unit(store: CuratedStore, name: str, ruleset: str) -> Unit:
    for unit in store.units():
        if unit.topic_name == name and unit.topic_ruleset == ruleset:
            return unit
    return store.put_unit(Unit(topic_name=name, topic_ruleset=ruleset))


def render_topic(store: CuratedStore, fields: dict[str, list[str]]) -> str:
    name = _first(fields, "name")
    ruleset = _first(fields, "ruleset")
    topic = store.topic(name, ruleset)
    if topic is None:
        body = (
            '<section class="panel">\n'
            '<p class="empty">That topic is not open.</p>\n'
            "</section>\n"
        )
        return render_shell(title="Topic", current="home", body=body)
    escaped_name = html.escape(topic.name)
    escaped_ruleset = html.escape(topic.ruleset)
    body = (
        '<section class="panel">\n'
        f"<h2>{escaped_name} ({escaped_ruleset})</h2>\n"
        '<form method="post" action="/topics">\n'
        f'<input type="hidden" name="name" value="{html.escape(topic.name, quote=True)}">\n'
        f'<input type="hidden" name="ruleset" value="{html.escape(topic.ruleset, quote=True)}">\n'
        '<input type="hidden" name="remove" value="1">\n'
        '<button type="submit">Remove</button>\n'
        "</form>\n"
        "</section>\n"
    )
    return render_shell(
        title=f"{topic.name} ({topic.ruleset})",
        current="home",
        body=body,
    )


def submit_topic(store: CuratedStore, fields: dict[str, list[str]]) -> str:
    name = _first(fields, "name")
    ruleset = _first(fields, "ruleset")
    if _first(fields, "remove"):
        remove_topic(store, name, ruleset)
        return "/"
    topic = open_topic(store, name, ruleset)
    if topic is None:
        return "/"
    _ensure_unit(store, topic.name, topic.ruleset)
    return topic_location(topic.name, topic.ruleset)


add_screen(Screen("topic", "/topics", "", get=render_topic, post=submit_topic))
