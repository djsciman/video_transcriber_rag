"""Custom library and unit history screens outside unit build."""

from __future__ import annotations

import html
from urllib.parse import urlencode

from coach_app.app import Screen, add_screen, render_shell
from coach_app.build import DRAFT_COLUMNS
from coach_app.library import (
    browse_library,
    copy_history,
    create_custom,
    delete_custom,
    edit_custom,
    save_history,
    search_library,
)
from coach_app.store import CuratedStore, CustomLesson, Lesson
from coach_app.ui_sheet import current_sheet

_STYLE = """
<style>
.page { max-width: none; width: 100%; }
.row-form { margin: 0 0 0.25rem; }
.row-form button { text-align: left; }
.row-form button.on { background: #ffedd5; }
.class-card {
  background: var(--paper); border: 2px solid var(--line); border-radius: 14px;
  overflow: hidden; margin: 0 0 1rem;
}
.class-card .cut {
  display: flex; flex-wrap: wrap; align-items: center; gap: 0.55rem 1rem;
  padding: 0.7rem 1rem; background: #1c1917; color: #fafaf9;
}
.class-card .cut .n { font-size: 0.72rem; color: #a8a29e; }
.class-card .cut h3 {
  margin: 0; font-size: 1.05rem; font-family: var(--serif);
  color: #fafaf9; text-transform: none; letter-spacing: 0;
}
table.sheet { width: 100%; border-collapse: collapse; table-layout: fixed; background: #fff; }
table.sheet th, table.sheet td {
  border-bottom: 1px solid var(--line); padding: 0.5rem 0.55rem; vertical-align: top; text-align: left;
}
table.sheet th {
  background: #f5f5f4; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.04em; color: var(--muted);
}
tr.tech { background: linear-gradient(90deg, #dbeafe, #fff 42%); }
tr.drill { background: linear-gradient(90deg, #fef9c3, #fff 42%); }
tr.sparring { background: linear-gradient(90deg, #ffe4e6, #fff 42%); }
tr.game { background: linear-gradient(90deg, #ede9fe, #fff 42%); }
.pill { display: inline-block; border-radius: 999px; padding: 0.12rem 0.55rem; font-size: 0.78rem; font-weight: 650; }
.pill-tech { background: #dbeafe; color: #1e3a8a; }
.pill-drill { background: #fef9c3; color: #854d0e; }
.pill-sparring { background: #ffe4e6; color: #9f1239; }
.pill-game { background: #ede9fe; color: #5b21b6; }
.pill-sys { background: #ccfbf1; color: #0f766e; }
.pill-move { background: #dbeafe; color: #1d4ed8; }
.tiny { color: var(--muted); font-size: 0.78rem; display: block; }
.source-list { display: flex; flex-wrap: wrap; gap: 0.35rem; }
.library-layout { display: grid; grid-template-columns: 1fr 1fr; gap: 0.7rem; }
.leaf {
  border: 1px solid var(--line); border-radius: 10px;
  padding: 0.5rem 0.6rem; margin: 0.35rem 0; background: #fff;
}
.edit-row { display: flex; flex-wrap: wrap; gap: 0.35rem; align-items: end; }
.edit-row label { margin: 0; }
</style>
"""


def get_custom(app, fields: dict[str, list[str]] | None = None) -> str:
    store = app.store
    walk = app.library_walk
    search = app.library_search
    body = (
        _STYLE
        + _create_panel()
        + _library_list(store)
        + _search_panel(search)
        + _search_results(store, search)
        + _browse_panel(store, walk)
    )
    return render_shell(title="Custom", current="custom", body=body)


def post_custom(app, fields: dict[str, list[str]]) -> str:
    store = app.store
    action = _field(fields, "action")
    if action == "create":
        lesson = _lesson_from(fields)
        if lesson.target:
            create_custom(store, lesson)
    elif action == "edit":
        custom_id = _field(fields, "custom_id")
        lesson = _lesson_from(fields)
        if custom_id and lesson.target:
            edit_custom(store, custom_id, lesson)
    elif action == "delete":
        custom_id = _field(fields, "custom_id")
        if custom_id:
            delete_custom(store, custom_id)
    elif action == "search":
        state = app.library_search
        for key in ("position", "sweep", "submission", "instructor", "ruleset", "query"):
            state[key] = _field(fields, key)
        state["ran"] = "1"
    elif action == "browse":
        walk = app.library_walk
        if "start" in fields:
            walk["start"] = _field(fields, "start")
            if "type_of_move" not in fields:
                walk["type_of_move"] = ""
                walk["end"] = ""
        if "type_of_move" in fields:
            walk["type_of_move"] = _field(fields, "type_of_move")
            if "end" not in fields:
                walk["end"] = ""
        if "end" in fields:
            walk["end"] = _field(fields, "end")
    return "/custom"


def get_history(store: CuratedStore, fields: dict[str, list[str]] | None = None) -> str:
    fields = fields or {}
    name, ruleset = _topic(store, fields)
    body = _STYLE + _save_panel(name, ruleset) + _history_list(store)
    return render_shell(title="History", current="history", body=body)


def post_history(store: CuratedStore, fields: dict[str, list[str]]) -> str:
    action = _field(fields, "action")
    name, ruleset = _topic(store, fields)
    if action == "copy":
        history_id = _field(fields, "history_id")
        if history_id:
            copied = copy_history(store, history_id)
            _hold_copied(store, copied)
            return _sheet_location(copied.unit.topic_name, copied.unit.topic_ruleset, "edit")
        return "/history"
    if action == "save":
        sheet = current_sheet(store, name, ruleset) if name else None
        if sheet is not None:
            save_history(store, sheet)
    return "/history"


def _create_panel() -> str:
    return (
        '<section class="panel" id="create-custom-panel">\n'
        "<h2>Custom</h2>\n"
        '<form id="create-custom" method="post" action="/custom">\n'
        '<input type="hidden" name="action" value="create">\n'
        '<label for="create-kind">Kind</label>\n'
        '<input id="create-kind" name="kind" type="text" value="drill">\n'
        '<label for="create-target">Named move or system</label>\n'
        '<input id="create-target" name="target" type="text">\n'
        '<label for="create-job">Partner job</label>\n'
        '<input id="create-job" name="partner_job" type="text">\n'
        '<label for="create-scenario">Scenario</label>\n'
        '<input id="create-scenario" name="scenario" type="text">\n'
        '<label for="create-condition">Condition</label>\n'
        '<input id="create-condition" name="condition" type="text">\n'
        '<button type="submit">Create</button>\n'
        "</form>\n"
        "</section>\n"
    )


def _library_list(store: CuratedStore) -> str:
    customs = store.custom_lessons()
    if not customs:
        body = '<p class="empty">No Custom lessons yet.</p>\n'
    else:
        body = "".join(_custom_card(store, custom) for custom in customs)
    return (
        '<section class="panel" id="custom-library">\n'
        "<h2>Saved lessons</h2>\n"
        f"{body}"
        "</section>\n"
    )


def _custom_card(store: CuratedStore, custom: CustomLesson) -> str:
    lesson = custom.lesson
    node = store.enrichment_node(lesson.target) if lesson.target else None
    target = node.name if node is not None else lesson.target
    kind = "system" if node is not None and node.kind == "system" else "named move"
    pill = "sys" if kind == "system" else "move"
    row_kind = "tech" if lesson.kind == "technique" else lesson.kind
    field = {
        "drill": ("Partner job", lesson.partner_job),
        "sparring": ("Scenario", lesson.scenario),
        "game": ("Condition", lesson.condition),
        "technique": ("Partner job", lesson.partner_job),
    }.get(lesson.kind, ("", ""))
    return (
        f'<div class="class-card" data-custom="{html.escape(custom.id, quote=True)}">\n'
        '<div class="cut">'
        '<span class="n">CUSTOM</span>'
        f"<h3>{html.escape(target)}</h3>"
        f'<span class="pill pill-{html.escape(row_kind)}">{html.escape(lesson.kind)}</span>'
        "</div>\n"
        '<table class="sheet"><tbody>'
        f'<tr class="{html.escape(row_kind)}">'
        f'<td><span class="pill pill-{pill}">{html.escape(kind)}</span> '
        f"<strong>{html.escape(target)}</strong></td>"
        f'<td><span class="tiny">{html.escape(field[0])}</span>'
        f"<div>{html.escape(field[1])}</div></td>"
        "</tr></tbody></table>\n"
        f"{_edit_form(custom)}"
        f"{_delete_form(custom.id)}"
        "</div>\n"
    )


def _edit_form(custom: CustomLesson) -> str:
    lesson = custom.lesson
    return (
        f'<form id="edit-{html.escape(custom.id, quote=True)}" class="edit-row" '
        'method="post" action="/custom">\n'
        '<input type="hidden" name="action" value="edit">\n'
        f'<input type="hidden" name="custom_id" value="{html.escape(custom.id, quote=True)}">\n'
        '<label>Kind<input name="kind" type="text" '
        f'value="{html.escape(lesson.kind, quote=True)}"></label>\n'
        '<label>Target<input name="target" type="text" '
        f'value="{html.escape(lesson.target, quote=True)}"></label>\n'
        '<label>Partner job<input name="partner_job" type="text" '
        f'value="{html.escape(lesson.partner_job, quote=True)}"></label>\n'
        '<label>Scenario<input name="scenario" type="text" '
        f'value="{html.escape(lesson.scenario, quote=True)}"></label>\n'
        '<label>Condition<input name="condition" type="text" '
        f'value="{html.escape(lesson.condition, quote=True)}"></label>\n'
        '<button type="submit">Save</button>\n'
        "</form>\n"
    )


def _delete_form(custom_id: str) -> str:
    return (
        f'<form id="delete-{html.escape(custom_id, quote=True)}" class="row-form" '
        'method="post" action="/custom">\n'
        '<input type="hidden" name="action" value="delete">\n'
        f'<input type="hidden" name="custom_id" value="{html.escape(custom_id, quote=True)}">\n'
        '<button type="submit" class="warn">Delete</button>\n'
        "</form>\n"
    )


def _search_panel(search: dict[str, str]) -> str:
    fields = (
        ("position", "Position"),
        ("sweep", "Sweep"),
        ("submission", "Submission"),
        ("instructor", "Instructor"),
        ("ruleset", "Ruleset"),
        ("query", "Query"),
    )
    inputs = []
    for key, label in fields:
        value = html.escape(search.get(key, ""), quote=True)
        inputs.append(
            f'<label>{html.escape(label)}<input type="text" name="{key}" value="{value}"></label>'
        )
    return (
        '<section class="panel" id="search-panel">\n'
        "<h2>Search</h2>\n"
        '<form id="search-library" method="post" action="/custom">\n'
        '<input type="hidden" name="action" value="search">\n'
        + "".join(inputs)
        + '<button type="submit">Search</button>\n'
        "</form>\n"
        "</section>\n"
    )


def _search_results(store: CuratedStore, search: dict[str, str]) -> str:
    if not search.get("ran"):
        return ""
    filters = {
        key: search.get(key, "")
        for key in ("position", "sweep", "submission", "instructor", "ruleset", "query")
    }
    hits = search_library(store, **filters)
    cards = []
    for hit in hits:
        if isinstance(hit, CustomLesson):
            cards.append(_custom_card(store, hit))
        else:
            cards.append(
                '<div class="leaf">'
                f'<div class="name">{html.escape(getattr(hit, "name", ""))}</div>'
                f'<div class="tiny">{html.escape(getattr(hit, "kind", ""))}</div>'
                "</div>"
            )
    body = "".join(cards) if cards else '<p class="empty">No matches.</p>\n'
    return (
        '<section class="panel" id="search-results">\n'
        "<h2>Search results</h2>\n"
        f"{body}"
        "</section>\n"
    )


def _browse_panel(store: CuratedStore, walk: dict[str, str]) -> str:
    starts = browse_library(store)
    start_bits = []
    for node in starts:
        start_bits.append(
            _browse_form(
                f"browse-start-{node.id}",
                {"action": "browse", "start": node.id},
                node.name,
                selected=walk["start"] == node.id,
            )
        )
    types_body = '<p class="tiny">Pick a starting position.</p>'
    if walk["start"]:
        types_body = "".join(
            _browse_form(
                f"browse-type-{node.id}",
                {
                    "action": "browse",
                    "start": walk["start"],
                    "type_of_move": node.id,
                },
                node.name,
                selected=walk["type_of_move"] == node.id,
            )
            for node in browse_library(store, start=walk["start"])
        )
    ends_body = '<p class="tiny">Pick a type of move.</p>'
    if walk["start"] and walk["type_of_move"]:
        ends_body = "".join(
            _browse_form(
                f"browse-end-{node.id}",
                {
                    "action": "browse",
                    "start": walk["start"],
                    "type_of_move": walk["type_of_move"],
                    "end": node.id,
                },
                node.name,
                selected=walk["end"] == node.id,
            )
            for node in browse_library(
                store, start=walk["start"], type_of_move=walk["type_of_move"]
            )
        )
    leaves = ""
    if walk["start"] and walk["type_of_move"] and walk["end"]:
        items = browse_library(
            store,
            start=walk["start"],
            type_of_move=walk["type_of_move"],
            end=walk["end"],
        )
        cards = []
        for item in items:
            if isinstance(item, CustomLesson):
                cards.append(_custom_card(store, item))
            else:
                cards.append(
                    '<div class="leaf">'
                    f'<div class="name">{html.escape(getattr(item, "name", ""))}</div>'
                    f'<div class="tiny">{html.escape(getattr(item, "kind", ""))}</div>'
                    "</div>"
                )
        leaves = (
            '<section class="panel" id="named-moves">\n'
            "<h2>Named-move leaves</h2>\n"
            + "".join(cards)
            + "</section>\n"
        )
    return (
        '<div class="library-layout">\n'
        '<section class="panel" id="starts">\n'
        "<h2>Starting position</h2>\n"
        f'<div class="source-list">{"".join(start_bits)}</div>\n'
        "</section>\n"
        '<section class="panel" id="types">\n'
        "<h2>Type of move</h2>\n"
        f"{types_body}\n"
        "</section>\n"
        '<section class="panel" id="ends">\n'
        "<h2>Ending position or submission</h2>\n"
        f"{ends_body}\n"
        "</section>\n"
        "</div>\n"
        f"{leaves}"
    )


def _browse_form(form_id: str, fields: dict[str, str], label: str, selected: bool = False) -> str:
    hidden = "".join(
        f'<input type="hidden" name="{html.escape(name, quote=True)}" '
        f'value="{html.escape(value, quote=True)}">'
        for name, value in fields.items()
    )
    on = " on" if selected else ""
    return (
        f'<form id="{html.escape(form_id, quote=True)}" class="row-form" '
        'method="post" action="/custom">'
        f"{hidden}"
        f'<button type="submit" class="row{on}">{html.escape(label)}</button>'
        "</form>"
    )


def _save_panel(name: str, ruleset: str) -> str:
    return (
        '<section class="panel" id="save-history-panel">\n'
        "<h2>History</h2>\n"
        '<form id="save-history" method="post" action="/history">\n'
        '<input type="hidden" name="action" value="save">\n'
        f'<input type="hidden" name="name" value="{html.escape(name, quote=True)}">\n'
        f'<input type="hidden" name="ruleset" value="{html.escape(ruleset, quote=True)}">\n'
        '<button type="submit">Save unit</button>\n'
        "</form>\n"
        "</section>\n"
    )


def _history_list(store: CuratedStore) -> str:
    entries = store.unit_histories()
    if not entries:
        body = '<p class="empty">No saved units yet.</p>\n'
    else:
        body = "".join(_history_card(store, entry) for entry in entries)
    return (
        '<section class="panel" id="history">\n'
        "<h2>Saved units</h2>\n"
        f"{body}"
        "</section>\n"
    )


def _history_card(store: CuratedStore, entry) -> str:
    unit = entry.unit
    cards = []
    for index, packed in enumerate(entry.classes):
        rows = []
        for lesson in packed.lessons:
            node = store.enrichment_node(lesson.target) if lesson.target else None
            target = node.name if node is not None else lesson.target
            row_kind = "tech" if lesson.kind == "technique" else lesson.kind
            rows.append(
                f'<tr class="{html.escape(row_kind)}">'
                f"<td><strong>{html.escape(target)}</strong></td>"
                f'<td><span class="pill pill-{html.escape(row_kind)}">{html.escape(lesson.kind)}</span></td>'
                f"<td>{html.escape(target)}</td>"
                "</tr>"
            )
        heads = "".join(f"<th>{html.escape(column)}</th>" for column in DRAFT_COLUMNS[:3])
        cards.append(
            f'<div class="class-card" data-class="{index}">\n'
            '<div class="cut">'
            '<span class="n">CUT</span>'
            f"<h3>Class {index + 1}</h3>"
            "</div>\n"
            '<table class="sheet">'
            f"<thead><tr>{heads}</tr></thead>"
            f"<tbody>{''.join(rows)}</tbody>"
            "</table>\n"
            "</div>\n"
        )
    copy = (
        f'<form id="copy-{html.escape(entry.id, quote=True)}" class="row-form" '
        'method="post" action="/history">\n'
        '<input type="hidden" name="action" value="copy">\n'
        f'<input type="hidden" name="history_id" value="{html.escape(entry.id, quote=True)}">\n'
        '<button type="submit">Copy to a new unit</button>\n'
        "</form>\n"
    )
    return (
        f'<article class="history-entry" data-history="{html.escape(entry.id, quote=True)}">\n'
        f"<h3>{html.escape(unit.topic_name)} ({html.escape(unit.topic_ruleset)})</h3>\n"
        f'<p class="tiny">{html.escape(unit.paragraph)}</p>\n'
        f"{copy}{''.join(cards)}"
        "</article>\n"
    )


def _hold_copied(store: CuratedStore, sheet) -> None:
    from coach_app.design import open_design

    name = sheet.unit.topic_name
    ruleset = sheet.unit.topic_ruleset
    if store.design_session(name, ruleset) is None:
        store.put_design_session(open_design(topic_name=name, topic_ruleset=ruleset))
    store.put_sheet(sheet)
    store.set_current_topic(name, ruleset)


def _lesson_from(fields: dict[str, list[str]]) -> Lesson:
    return Lesson(
        kind=_field(fields, "kind") or "drill",
        target=_field(fields, "target"),
        partner_job=_field(fields, "partner_job"),
        scenario=_field(fields, "scenario"),
        condition=_field(fields, "condition"),
    )


def _topic(store: CuratedStore, fields: dict[str, list[str]]) -> tuple[str, str]:
    name = _field(fields, "name")
    ruleset = _field(fields, "ruleset")
    if name and ruleset:
        return name, ruleset
    last = store.current_topic()
    if last:
        return last
    topics = store.topics()
    if topics:
        return topics[0].name, topics[0].ruleset
    return "", ""


def _sheet_location(name: str, ruleset: str, mode: str) -> str:
    query = {"name": name, "ruleset": ruleset, "mode": mode}
    return "/sheet?" + urlencode(query)


def _field(fields: dict[str, list[str]], key: str) -> str:
    values = fields.get(key) or [""]
    return (values[0] if values else "").strip()


add_screen(Screen("custom", "/custom", "Custom", get=get_custom, post=post_custom))
add_screen(Screen("history", "/history", "History", get=get_history, post=post_history))
