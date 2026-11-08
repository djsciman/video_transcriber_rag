"""Read and Edit modes of the colored class-card sheet."""

from __future__ import annotations

import html
from urllib.parse import urlencode

from coach_app.app import Screen, add_screen, render_shell
from coach_app.build import DRAFT_COLUMNS, Draft, PackedClass
from coach_app.edit import (
    add_lesson,
    class_cards,
    drag_lesson,
    open_sheet,
    remove_lesson,
    set_mode,
    set_purpose,
)
from coach_app.library import add_lesson_sources, place_lesson, pull_custom
from coach_app.store import CuratedStore, CustomLesson, Lesson
from coach_app.ui_design import design_session

_STYLE = """
<style>
.page { max-width: none; width: 100%; }
.mode-tabs { display: flex; gap: 0.35rem; margin: 0 0 0.7rem; }
.mode-tabs .row-form { margin: 0; }
.mode-tabs button.on { background: #1c1917; color: #fff; }
.class-card {
  background: var(--paper); border: 2px solid var(--line); border-radius: 14px;
  overflow: hidden; margin: 0 0 1rem;
}
.sheet[data-mode="draft"] .class-card { border-style: dashed; }
.class-card .cut {
  display: flex; flex-wrap: wrap; align-items: center; gap: 0.55rem 1rem;
  padding: 0.7rem 1rem; background: #1c1917; color: #fafaf9;
}
.class-card .cut .n { font-size: 0.72rem; color: #a8a29e; }
.class-card .cut h3 {
  margin: 0; font-size: 1.05rem; font-family: var(--serif);
  color: #fafaf9; text-transform: none; letter-spacing: 0;
}
.class-card .purpose { color: #a8a29e; font-size: 0.85rem; margin-left: auto; }
table.sheet { width: 100%; border-collapse: collapse; table-layout: fixed; background: #fff; }
table.sheet th, table.sheet td {
  border-bottom: 1px solid var(--line); padding: 0.5rem 0.55rem; vertical-align: top; text-align: left;
}
table.sheet th {
  background: #f5f5f4; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.04em; color: var(--muted);
}
.col-check { width: 2.2rem; }
.col-edit { width: 8.5rem; }
.col-lesson { width: 28%; }
.col-type { width: 7.2rem; }
.col-target { width: 22%; }
tr.tech { background: linear-gradient(90deg, #dbeafe, #fff 42%); }
tr.drill { background: linear-gradient(90deg, #fef9c3, #fff 42%); }
tr.sparring { background: linear-gradient(90deg, #ffe4e6, #fff 42%); }
tr.game { background: linear-gradient(90deg, #ede9fe, #fff 42%); }
tr.glued td:first-child { box-shadow: inset 4px 0 0 #fb923c; }
.pill { display: inline-block; border-radius: 999px; padding: 0.12rem 0.55rem; font-size: 0.78rem; font-weight: 650; }
.pill-tech { background: #dbeafe; color: #1e3a8a; }
.pill-drill { background: #fef9c3; color: #854d0e; }
.pill-sparring { background: #ffe4e6; color: #9f1239; }
.pill-game { background: #ede9fe; color: #5b21b6; }
.pill-sys { background: #ccfbf1; color: #0f766e; }
.pill-move { background: #dbeafe; color: #1d4ed8; }
.pill-glue { background: #ffedd5; color: #9a3412; }
.pill-read { background: #ecfccb; color: #3f6212; }
.pill-edit { background: #ffedd5; color: #9a3412; }
.pill-draft { background: #fef3c7; color: #92400e; }
.steps { margin: 0.3rem 0 0; padding-left: 1.1rem; }
.steps li { margin: 0.2rem 0; }
.tiny { color: var(--muted); font-size: 0.78rem; display: block; }
.reason { color: var(--accent); font-weight: 650; }
.add-bar, .add-panel { margin: 0.55rem 0 0.7rem; }
.add-panel h3 { font-size: 0.86rem; margin: 0.6rem 0 0.35rem; }
.row-form { margin: 0 0 0.25rem; }
.row-form button { text-align: left; }
.edit-tools .row-form { display: inline-block; margin-right: 0.2rem; }
.check { text-align: center; }
.cut-purpose { display: flex; gap: 0.35rem; align-items: center; margin-left: auto; }
.cut-purpose input { min-width: 16rem; }
.source-list { display: flex; flex-wrap: wrap; gap: 0.35rem; }
.success-watch { margin: 0.55rem 0 0; padding: 0.55rem 0.7rem; border-top: 1px dashed var(--line); }
.success-watch h3 { font-size: 0.86rem; margin: 0 0 0.35rem; }
.success-watch fieldset { border: 0; padding: 0; margin: 0 0 0.35rem; }
.success-watch label { margin-right: 0.55rem; }
@media print {
  .success-watch, .success { display: none !important; }
}
</style>
"""


def current_sheet(store: CuratedStore, name: str, ruleset: str, mode: str = ""):
    wanted = _mode(mode) if mode else ""
    held = store.sheet(name, ruleset)
    draft = _draft(store, name, ruleset)
    if draft is not None and held is not None:
        if getattr(held.unit, "id", "") != getattr(draft.unit, "id", ""):
            held = None
    if held is None:
        if draft is None:
            return None
        held = open_sheet(store, draft, wanted or "read")
        store.put_sheet(held)
    elif wanted and held.mode != wanted:
        held = set_mode(held, wanted)
        store.put_sheet(held)
    return held


def get_sheet(app, fields: dict[str, list[str]] | None = None) -> str:
    fields = fields or {}
    store = app.store
    name, ruleset = _topic(store, fields)
    mode = _field(fields, "mode")
    sheet = current_sheet(store, name, ruleset, mode)
    ui = _ui(app, name, ruleset)
    if sheet is not None:
        ui["mode"] = sheet.mode
    session = design_session(store, name, ruleset) if name else None
    body = _STYLE + _sheet_section(store, sheet, ui, name, ruleset, session)
    title = f"Sheet · {name}" if name else "Sheet"
    return render_shell(title=title, current="sheet", body=body)


def post_sheet(app, fields: dict[str, list[str]]) -> str:
    store = app.store
    name, ruleset = _topic(store, fields)
    ui = _ui(app, name, ruleset)
    action = _field(fields, "action")
    mode = _field(fields, "mode") or ui.get("mode") or "read"
    ui["error"] = ""
    sheet = current_sheet(store, name, ruleset, mode if action == "mode" else "")
    if action == "mode":
        sheet = current_sheet(store, name, ruleset, mode)
    elif action == "purpose" and sheet is not None:
        sheet = _try(ui, lambda: set_purpose(
            store, set_mode(sheet, "edit"), int(_field(fields, "class_index") or "0"),
            _field(fields, "purpose"),
        ))
    elif action == "remove" and sheet is not None:
        sheet = _try(ui, lambda: remove_lesson(
            store, set_mode(sheet, "edit"), _field(fields, "lesson_id")
        ))
    elif action == "drag" and sheet is not None:
        sheet = _try(ui, lambda: drag_lesson(
            store,
            set_mode(sheet, "edit"),
            _field(fields, "lesson_id"),
            class_index=int(_field(fields, "class_index") or "0"),
            index=int(_field(fields, "index") or "0"),
        ))
    elif action == "search":
        ui["search"] = {
            "position": _field(fields, "position"),
            "sweep": _field(fields, "sweep"),
            "submission": _field(fields, "submission"),
            "instructor": _field(fields, "instructor"),
            "ruleset": _field(fields, "ruleset") or ruleset,
            "query": _field(fields, "query"),
        }
    elif action == "browse":
        walk = ui.setdefault("browse", {"start": "", "type_of_move": "", "end": ""})
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
    elif action == "add" and sheet is not None:
        sheet = _try(ui, lambda: _add(store, set_mode(sheet, "edit"), fields))
    if sheet is not None:
        store.put_sheet(sheet)
        ui["mode"] = sheet.mode
    return _location(name, ruleset, ui.get("mode") or "read")


def _add(store, sheet, fields):
    source = _field(fields, "source")
    class_index = _class_index(_field(fields, "class_index"))
    index = _index(_field(fields, "index"))
    if source == "custom" or _field(fields, "custom_id"):
        copies = pull_custom(store, _field(fields, "custom_id"))
        glued = copies[1] if len(copies) > 1 else None
        return place_lesson(
            store, sheet, copies[0], class_index=class_index, index=index, glued=glued
        )
    kind = _field(fields, "kind") or "technique"
    lesson = Lesson(
        kind=kind,
        target=_field(fields, "target"),
        partner_job=_field(fields, "partner_job"),
        scenario=_field(fields, "scenario"),
        condition=_field(fields, "condition"),
    )
    return place_lesson(store, sheet, lesson, class_index=class_index, index=index)


def _try(ui, op):
    try:
        return op()
    except ValueError as error:
        ui["error"] = str(error)
        return ui.get("sheet")


def _sheet_section(store, sheet, ui, name, ruleset, session) -> str:
    mode = (sheet.mode if sheet is not None else ui.get("mode")) or "read"
    error = ui.get("error") or ""
    reason = f'<p class="reason">{html.escape(error)}</p>\n' if error else ""
    tabs = _mode_tabs(name, ruleset, mode)
    if sheet is None or not sheet.classes:
        body = reason + '<p class="empty">No packed classes yet. Propose or convert on Design first.</p>\n'
    else:
        body = reason + "".join(
            _class_card(store, sheet, packed, cards, index, name, ruleset)
            for index, (packed, cards) in enumerate(zip(sheet.classes, class_cards(store, sheet)))
        )
        if mode == "edit":
            body += _add_panel(store, ui, name, ruleset, session)
    print_href = ""
    if name and ruleset:
        print_href = (
            '<p class="sheet-modes">'
            f'<a href="/print?{urlencode({"name": name, "ruleset": ruleset})}">'
            "Print duplex packet</a></p>\n"
        )
    return (
        f'<section class="panel sheet" id="sheet" data-mode="{html.escape(mode, quote=True)}">\n'
        f'<h2>Unit sheet</h2>\n'
        f'<span class="pill pill-{html.escape(mode)}">{html.escape(mode.title())}</span>\n'
        f"{print_href}{tabs}{body}"
        "</section>\n"
    )


def _mode_tabs(name, ruleset, mode: str) -> str:
    buttons = []
    for key, label in (("read", "Read"), ("edit", "Edit")):
        on = " on" if key == mode else ""
        buttons.append(
            _form(
                f"mode-{key}",
                name,
                ruleset,
                {"action": "mode", "mode": key},
                label,
                button_class=on.strip(),
            )
        )
    return f'<div class="mode-tabs">{"".join(buttons)}</div>\n'


def _class_card(store, sheet, packed, cards, index: int, name, ruleset) -> str:
    mode = sheet.mode
    rows = []
    for card in cards:
        lesson = card.lesson
        row_kind = "tech" if lesson.kind == "technique" else lesson.kind
        glued = " glued" if card.glued else ""
        extra = ""
        if mode == "read":
            extra = (
                f'<td class="check"><input type="checkbox" '
                f'aria-label="Ran {html.escape(card.target, quote=True)}"></td>'
            )
        elif mode == "edit":
            extra = f'<td class="edit-tools">{_edit_tools(lesson, name, ruleset, index)}</td>'
        rows.append(
            f'<tr class="{html.escape(row_kind)}{glued}" data-lesson="{html.escape(lesson.id, quote=True)}">'
            f"{extra}"
            f'<td class="cell-lesson">{_lesson_cell(card)}</td>'
            f'<td class="cell-type"><span class="pill pill-{html.escape(row_kind)}">{html.escape(lesson.kind)}</span></td>'
            f'<td class="cell-target">{_target_cell(store, lesson, card)}</td>'
            f'<td class="cell-run">{_run_cell(card)}</td>'
            "</tr>"
        )
    heads = []
    if mode == "read":
        heads.append('<th class="check">Ran</th>')
    if mode == "edit":
        heads.append("<th></th>")
    heads.extend(f"<th>{html.escape(column)}</th>" for column in sheet.columns or DRAFT_COLUMNS)
    purpose = packed.class_record.purpose
    if mode == "edit":
        purpose_html = (
            f'<form id="purpose-{index}" class="cut-purpose" method="post" action="/sheet">'
            f"{_topic_hidden(name, ruleset)}"
            '<input type="hidden" name="action" value="purpose">'
            f'<input type="hidden" name="class_index" value="{index}">'
            f'<input name="purpose" type="text" value="{html.escape(purpose, quote=True)}" '
            'placeholder="Purpose">'
            '<button type="submit">Save purpose</button>'
            "</form>"
        )
    else:
        purpose_html = f'<div class="purpose">{html.escape(purpose)}</div>'
    return (
        f'<div class="class-card" data-class="{index}">\n'
        '<div class="cut">'
        '<span class="n">CUT</span>'
        f"<h3>Class {index + 1}</h3>"
        f"{purpose_html}"
        "</div>\n"
        '<table class="sheet">\n'
        f"<thead><tr>{''.join(heads)}</tr></thead>\n"
        f"<tbody>{''.join(rows)}</tbody>\n"
        "</table>\n"
        + (_success_watch() if mode == "read" else "")
        + "</div>\n"
    )


def _success_watch() -> str:
    scale = ("none", "some", "most", "all")
    def group(legend: str) -> str:
        choices = "".join(
            f'<label><input type="radio"> {html.escape(item)}</label>'
            for item in scale
        )
        return f"<fieldset><legend>{html.escape(legend)}</legend>{choices}</fieldset>"
    return (
        '<div class="success-watch success" id="success-watch">\n'
        "<h3>Success watch</h3>\n"
        + group("Attempting")
        + group("Completing or coming close against a better partner")
        + "</div>\n"
    )


def _edit_tools(lesson, name, ruleset, class_index: int) -> str:
    return (
        f'<form id="drag-{html.escape(lesson.id, quote=True)}" class="row-form" '
        'method="post" action="/sheet">'
        f"{_topic_hidden(name, ruleset)}"
        '<input type="hidden" name="action" value="drag">'
        f'<input type="hidden" name="lesson_id" value="{html.escape(lesson.id, quote=True)}">'
        '<label>Class <input type="number" name="class_index" '
        f'value="{class_index}"></label>'
        '<label>Index <input type="number" name="index" value="0"></label>'
        '<button type="submit">Move</button>'
        "</form>"
        + _form(
            f"remove-{lesson.id}",
            name,
            ruleset,
            {"action": "remove", "lesson_id": lesson.id},
            "Remove",
            button_class="warn",
        )
    )


def _lesson_cell(card) -> str:
    title = card.target
    if card.lesson.kind == "drill":
        title = f"{card.target} drill"
    extra = ""
    if card.glued and card.lesson.kind == "technique":
        extra += ' <span class="pill pill-glue">+ drill</span>'
    if card.glued and card.lesson.kind == "drill":
        extra += ' <span class="pill pill-glue">follows technique</span>'
    return f"<strong>{html.escape(title)}</strong>{extra}"


def _target_cell(store, lesson, card) -> str:
    node = store.enrichment_node(lesson.target) if lesson.target else None
    kind = "system" if node is not None and node.kind == "system" else "named move"
    pill = "sys" if kind == "system" else "move"
    label = html.escape(card.target or (node.name if node is not None else lesson.target))
    return (
        f'<span class="pill pill-{pill}">{html.escape(kind)}</span> '
        f"<strong>{label}</strong>"
    )


def _run_cell(card) -> str:
    lesson = card.lesson
    if lesson.kind == "technique":
        if not card.what_to_run:
            return '<span class="tiny">No citations chosen yet.</span>'
        items = "".join(f"<li>{html.escape(item)}</li>" for item in card.what_to_run)
        return f'<ul class="steps">{items}</ul>'
    label = {
        "drill": "Partner job",
        "sparring": "Scenario",
        "game": "Condition",
    }.get(lesson.kind, "")
    text = card.what_to_run[0] if card.what_to_run else ""
    heading = f'<span class="tiny">{label}</span>' if label else ""
    return f"{heading}<div>{html.escape(text)}</div>"


def _add_panel(store, ui, name, ruleset, session) -> str:
    search = ui.get("search") or {}
    browse = ui.get("browse") or {"start": "", "type_of_move": "", "end": ""}
    filters = {key: value for key, value in search.items() if value}
    for key, value in browse.items():
        if value:
            filters[key] = value
    sources = add_lesson_sources(store, session, **filters)
    return (
        '<section class="add-panel" id="add-lesson">\n'
        "<h3>Add a lesson</h3>\n"
        f"{_search_form(name, ruleset, search)}"
        f"{_browse_panel(store, name, ruleset, browse)}"
        f"{_custom_list(sources.custom, name, ruleset)}"
        f"{_hit_list('search', sources.search, name, ruleset)}"
        f"{_hit_list('hierarchy', sources.hierarchy, name, ruleset)}"
        f"{_map_list(store, sources.map_moves, name, ruleset)}"
        "</section>\n"
    )


def _search_form(name, ruleset, search) -> str:
    fields = (
        ("position", "Position"),
        ("sweep", "Sweep"),
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
        f'<form id="search-library" method="post" action="/sheet">'
        f"{_topic_hidden(name, ruleset)}"
        '<input type="hidden" name="action" value="search">'
        + "".join(inputs)
        + '<button type="submit">Search</button></form>\n'
    )


def _browse_panel(store, name, ruleset, browse) -> str:
    starts = store.browse_hierarchy()
    bits = []
    for node in starts:
        bits.append(
            _form(
                f"browse-start-{node.id}",
                name,
                ruleset,
                {"action": "browse", "start": node.id},
                html.escape(node.name),
            )
        )
    if browse.get("start"):
        for node in store.browse_hierarchy(browse["start"]):
            bits.append(
                _form(
                    f"browse-type-{node.id}",
                    name,
                    ruleset,
                    {
                        "action": "browse",
                        "start": browse["start"],
                        "type_of_move": node.id,
                    },
                    html.escape(node.name),
                )
            )
    if browse.get("start") and browse.get("type_of_move"):
        for node in store.browse_hierarchy(browse["start"], browse["type_of_move"]):
            bits.append(
                _form(
                    f"browse-end-{node.id}",
                    name,
                    ruleset,
                    {
                        "action": "browse",
                        "start": browse["start"],
                        "type_of_move": browse["type_of_move"],
                        "end": node.id,
                    },
                    html.escape(node.name),
                )
            )
    return f'<div class="source-list" id="hierarchy-browse">{"".join(bits)}</div>\n'


def _custom_list(customs, name, ruleset) -> str:
    if not customs:
        return ""
    items = []
    for custom in customs:
        label = custom.lesson.kind
        items.append(
            _add_form(
                f"add-custom-{custom.id}",
                name,
                ruleset,
                {"action": "add", "source": "custom", "custom_id": custom.id},
                html.escape(f"Custom {label}"),
            )
        )
    return "<h3>Custom</h3>\n" + "".join(items)


def _hit_list(kind: str, hits, name, ruleset) -> str:
    items = []
    seen = set()
    for hit in hits:
        if isinstance(hit, CustomLesson):
            hit_id = hit.id
            fields = {"action": "add", "source": "custom", "custom_id": hit.id}
            label = f"Custom {hit.lesson.kind}"
        else:
            hit_id = getattr(hit, "id", "")
            if not hit_id:
                continue
            fields = {
                "action": "add",
                "source": kind,
                "target": hit_id,
            }
            label = getattr(hit, "name", hit_id)
        form_id = f"add-{kind}-{hit_id}"
        if form_id in seen:
            continue
        seen.add(form_id)
        items.append(_add_form(form_id, name, ruleset, fields, html.escape(label)))
    if not items:
        return ""
    return f"<h3>{html.escape(kind.title())}</h3>\n" + "".join(items)


def _map_list(store, move_ids, name, ruleset) -> str:
    items = []
    for target in move_ids:
        node = store.enrichment_node(target)
        label = node.name if node is not None else target
        items.append(
            _add_form(
                f"add-map-{target}",
                name,
                ruleset,
                {
                    "action": "add",
                    "source": "map",
                    "target": target,
                },
                html.escape(label),
            )
        )
    if not items:
        return ""
    return "<h3>On the map</h3>\n" + "".join(items)


def _add_form(form_id, name, ruleset, fields: dict[str, str], label: str) -> str:
    hidden = [_topic_hidden(name, ruleset)]
    hidden.extend(
        f'<input type="hidden" name="{html.escape(key, quote=True)}" '
        f'value="{html.escape(str(val), quote=True)}">'
        for key, val in fields.items()
    )
    kinds = "".join(
        f'<option value="{html.escape(kind)}">{html.escape(kind)}</option>'
        for kind in ("technique", "sparring", "game", "drill")
    )
    return (
        f'<form id="{html.escape(form_id, quote=True)}" class="row-form add-lesson-form" '
        'method="post" action="/sheet">'
        + "".join(hidden)
        + f'<label>Kind <select name="kind">{kinds}</select></label>'
        '<label>Class <input type="text" name="class_index" value=""></label>'
        '<label>Index <input type="text" name="index" value=""></label>'
        '<label>Partner job <input type="text" name="partner_job" value=""></label>'
        '<label>Scenario <input type="text" name="scenario" value=""></label>'
        '<label>Condition <input type="text" name="condition" value=""></label>'
        f'<button type="submit">{label}</button>'
        "</form>"
    )


def _draft(store, name, ruleset):
    held = store.sheet(name, ruleset)
    if held is not None:
        return Draft(
            unit=held.unit,
            classes=held.classes,
            layout=getattr(held, "layout", "B"),
            columns=tuple(getattr(held, "columns", DRAFT_COLUMNS)),
        )
    unit = next(
        (
            item
            for item in store.units()
            if item.topic_name == name and item.topic_ruleset == ruleset
        ),
        None,
    )
    if unit is None:
        return None
    packed = []
    for class_record in store.classes():
        if class_record.unit_id != unit.id:
            continue
        lessons = tuple(
            lesson for lesson in store.lessons() if lesson.class_id == class_record.id
        )
        if lessons:
            packed.append(PackedClass(class_record=class_record, lessons=lessons))
    if not packed:
        return None
    return Draft(unit=unit, classes=tuple(packed))


def _ui(app, name, ruleset) -> dict:
    table = app.sheet_ui
    key = (name, ruleset)
    held = table.get(key)
    if held is None:
        held = {
            "mode": "read",
            "error": "",
            "search": {},
            "browse": {"start": "", "type_of_move": "", "end": ""},
        }
        table[key] = held
    return held


def _topic(store, fields: dict[str, list[str]]) -> tuple[str, str]:
    name = _field(fields, "name")
    ruleset = _field(fields, "ruleset")
    if name and ruleset:
        store.set_current_topic(name, ruleset)
        return name, ruleset
    last = store.current_topic()
    if last:
        return last
    topics = store.topics()
    if topics:
        return topics[0].name, topics[0].ruleset
    return "", ""


def _location(name: str, ruleset: str, mode: str) -> str:
    query = {}
    if name and ruleset:
        query["name"] = name
        query["ruleset"] = ruleset
    if mode:
        query["mode"] = mode
    if query:
        return "/sheet?" + urlencode(query)
    return "/sheet"


def _form(form_id, name, ruleset, fields: dict[str, str], label: str, button_class: str = "") -> str:
    hidden = [_topic_hidden(name, ruleset)]
    hidden.extend(
        f'<input type="hidden" name="{html.escape(key, quote=True)}" '
        f'value="{html.escape(str(val), quote=True)}">'
        for key, val in fields.items()
    )
    cls = f' class="{button_class}"' if button_class else ""
    return (
        f'<form id="{html.escape(form_id, quote=True)}" class="row-form" method="post" action="/sheet">'
        + "".join(hidden)
        + f'<button type="submit"{cls}>{label}</button>'
        "</form>"
    )


def _topic_hidden(name: str, ruleset: str) -> str:
    return (
        f'<input type="hidden" name="name" value="{html.escape(name, quote=True)}">'
        f'<input type="hidden" name="ruleset" value="{html.escape(ruleset, quote=True)}">'
    )


def _field(fields: dict[str, list[str]], key: str) -> str:
    values = fields.get(key) or [""]
    return (values[0] if values else "").strip()


def _class_index(raw: str):
    if raw in {"", "new"}:
        return None
    return int(raw)


def _index(raw: str):
    if raw == "":
        return None
    return int(raw)


def _mode(mode: str) -> str:
    key = str(mode or "").casefold()
    if key not in {"read", "edit", "draft"}:
        return "read"
    return key


add_screen(Screen("sheet", "/sheet", "Sheet", get=get_sheet, post=post_sheet))
