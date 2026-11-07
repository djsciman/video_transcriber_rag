"""Open and remove a topic, and welcome other-ruleset instructionals."""

from __future__ import annotations

import html
from urllib.parse import urlencode

from coach_app.app import Screen, add_screen, render_shell
from coach_app.store import CuratedStore, Instructional, Topic, Unit
from coach_app.topics import (
    OTHER_RULESET_CAVEAT,
    open_topic,
    other_ruleset_instructionals,
    remove_topic,
    welcome_other_ruleset,
)

_STYLE = """
.caveat-box {
  background: #fef9c3;
  border: 1px solid #fde047;
  border-radius: 10px;
  padding: 1rem 1.1rem;
  margin: 0.45rem 0 0;
  max-width: 72ch;
}
.pill {
  display: inline-block;
  border-radius: 999px;
  padding: 0.12rem 0.55rem;
  font-size: 0.78rem;
  font-weight: 650;
  margin-right: 0.35rem;
}
.pill-caveat { background: #fef9c3; color: #854d0e; border: 1px solid #ca8a04; }
.actions { display: flex; gap: 0.45rem; margin-top: 0.45rem; }
"""


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
    briefing_href = "/briefing?" + urlencode(
        {"name": topic.name, "ruleset": topic.ruleset}
    )
    design_href = "/design?" + urlencode({"name": topic.name, "ruleset": topic.ruleset})
    body = (
        f"<style>{_STYLE}</style>\n"
        '<section class="panel">\n'
        f"<h2>{escaped_name} ({escaped_ruleset})</h2>\n"
        f'<p><a href="{html.escape(briefing_href, quote=True)}">Briefing</a></p>\n'
        f'<p><a href="{html.escape(design_href, quote=True)}">Design</a></p>\n'
        '<form method="post" action="/topics">\n'
        f'<input type="hidden" name="name" value="{html.escape(topic.name, quote=True)}">\n'
        f'<input type="hidden" name="ruleset" value="{html.escape(topic.ruleset, quote=True)}">\n'
        '<input type="hidden" name="remove" value="1">\n'
        '<button type="submit">Remove</button>\n'
        "</form>\n"
        "</section>\n"
        f"{_other_ruleset_panel(store, topic)}"
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
    if _first(fields, "welcome"):
        topic = store.topic(name, ruleset)
        instructional = _first(fields, "instructional")
        if topic is not None and instructional:
            welcome_other_ruleset(
                store, topic, instructional, _first(fields, "welcome") == "yes"
            )
        return topic_location(name, ruleset)
    topic = open_topic(store, name, ruleset)
    if topic is None:
        return "/"
    _ensure_unit(store, topic.name, topic.ruleset)
    return topic_location(topic.name, topic.ruleset)


def _other_ruleset_panel(store: CuratedStore, topic: Topic) -> str:
    offered = other_ruleset_instructionals(store, topic)
    if not offered:
        return (
            '<section class="panel" id="other-ruleset">\n'
            "<h2>Other-ruleset instructionals</h2>\n"
            '<p class="empty">No matching instructionals of the other ruleset.</p>\n'
            "</section>\n"
        )
    items = "".join(_welcome_card(store, topic, instructional) for instructional in offered)
    return (
        '<section class="panel" id="other-ruleset">\n'
        "<h2>Other-ruleset instructionals</h2>\n"
        f"<ul>{items}</ul>\n"
        "</section>\n"
    )


def _welcome_card(
    store: CuratedStore, topic: Topic, instructional: Instructional
) -> str:
    choice = store.other_ruleset_choice(topic.name, topic.ruleset, instructional.name)
    caveat = ""
    if choice is not None and choice.yes:
        caveat = getattr(choice, "caveat", "") or OTHER_RULESET_CAVEAT
    caveat_box = ""
    if caveat:
        caveat_box = (
            '<div class="caveat-box">'
            '<span class="pill pill-caveat">caveat</span> '
            f"{html.escape(caveat)}"
            "</div>\n"
        )
    return (
        "<li>\n"
        f"<div>{html.escape(instructional.name)} ({html.escape(instructional.ruleset)})</div>\n"
        '<form method="post" action="/topics">\n'
        f'<input type="hidden" name="name" value="{html.escape(topic.name, quote=True)}">\n'
        f'<input type="hidden" name="ruleset" value="{html.escape(topic.ruleset, quote=True)}">\n'
        f'<input type="hidden" name="instructional" value="{html.escape(instructional.name, quote=True)}">\n'
        '<div class="actions">\n'
        '<button type="submit" name="welcome" value="yes">Yes</button>\n'
        '<button type="submit" name="welcome" value="no">No</button>\n'
        "</div>\n"
        "</form>\n"
        f"{caveat_box}"
        "</li>\n"
    )


add_screen(Screen("topic", "/topics", "", get=render_topic, post=submit_topic))
