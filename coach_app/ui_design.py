"""Design screen: unordered mental map driven by the add walk."""

from __future__ import annotations

import html
import json
from dataclasses import replace
from urllib.parse import urlencode

from coach_app.app import Screen, add_screen, render_shell
from coach_app.build import DRAFT_COLUMNS, BuildAdvisor, Draft, convert, propose
from coach_app.design import (
    ADD_WALK,
    AddWalk,
    add_named_move,
    choose_citation,
    citations_on_mark,
    delete_mark,
    edit_mark,
    open_design,
    pick,
    walk_options,
    walk_step,
)
from coach_app.store import CuratedStore, PackedClass

_EMPTY_CONVERT = "The map has no named moves or systems to convert."
_ADVISOR = BuildAdvisor()

_STYLE = """
<style>
.page { max-width: none; width: 100%; }
.design-stack { display: flex; flex-direction: column; gap: 0.7rem; }
#add-walk .row-form { display: inline-block; margin: 0 0.25rem 0.25rem 0; }
#add-walk .row-form button { width: auto; text-align: left; }
.row-form { margin: 0 0 0.25rem; }
.row-form button { width: 100%; text-align: left; }
.map-stage, #map-stage, #design-map { width: 100%; }
.catalog-crumbs { display: flex; flex-wrap: wrap; align-items: center; gap: 0.2rem 0.3rem; margin: 0 0 0.55rem; }
.catalog-crumbs button {
  border: 0; background: #1c1917; color: #fff; border-radius: 999px;
  padding: 0.18rem 0.55rem; cursor: pointer; font: inherit; font-size: 0.78rem;
}
.catalog-crumbs .sep { color: var(--muted); font-size: 0.78rem; }
.map-stage {
  background: #fff; border: 1px solid var(--line); border-radius: 14px;
  min-height: 42vh; height: 46vh; overflow: hidden; position: relative;
}
.map-stage svg { width: 100%; height: calc(46vh - 3.5rem); min-height: 22rem; cursor: crosshair; display: block; }
.graph-toolbar {
  display: flex; flex-wrap: wrap; align-items: center; gap: 0.45rem 1rem;
  padding: 0.45rem 0.7rem; border-bottom: 1px solid var(--line); background: #fff;
  position: relative; z-index: 3;
}
.map-stage.panning { cursor: grabbing; }
.graph-empty {
  position: absolute; left: 50%; top: 50%; transform: translate(-50%, -50%);
  color: var(--muted); text-align: center; max-width: 28rem; pointer-events: none;
}
.mark-list { list-style: none; padding: 0; margin: 0; font-size: 0.86rem; }
.mark-list li { margin: 0.2rem 0; }
.cite { display: block; font-size: 0.86rem; margin: 0.25rem 0; }
textarea { font: inherit; border: 1px solid var(--line); border-radius: 8px; padding: 0.35rem 0.55rem; width: 100%; min-height: 4.5rem; }
.hint { color: var(--muted); font-size: 0.78rem; margin: 0.25rem 0 0.45rem; }
.prompt-actions { display: flex; flex-wrap: wrap; gap: 0.4rem; }
.prompt-panel .row-form button { width: auto; }
.class-card {
  background: var(--paper); border: 2px dashed var(--line); border-radius: 14px;
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
.class-card .purpose { color: #a8a29e; font-size: 0.85rem; margin-left: auto; }
table.sheet { width: 100%; border-collapse: collapse; table-layout: fixed; background: #fff; }
table.sheet th, table.sheet td {
  border-bottom: 1px solid var(--line); padding: 0.5rem 0.55rem; vertical-align: top; text-align: left;
}
table.sheet th {
  background: #f5f5f4; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.04em; color: var(--muted);
}
.col-lesson { width: 32%; }
.col-type { width: 7.2rem; }
.col-target { width: 22%; }
.col-run { width: auto; }
tr.tech { background: linear-gradient(90deg, #dbeafe, #fff 42%); }
tr.drill { background: linear-gradient(90deg, #fef9c3, #fff 42%); }
tr.glued td:first-child { box-shadow: inset 4px 0 0 #fb923c; }
.pill-tech { background: #dbeafe; color: #1e3a8a; }
.pill-drill { background: #fef9c3; color: #854d0e; }
.pill-sys { background: #ccfbf1; color: #0f766e; }
.pill-move { background: #dbeafe; color: #1d4ed8; }
.pill-glue { background: #ffedd5; color: #9a3412; }
.pill-draft { background: #fef3c7; color: #92400e; }
.reason { color: var(--accent); font-weight: 650; }
.steps { margin: 0.3rem 0 0; padding-left: 1.1rem; }
.steps li { margin: 0.2rem 0; }
.tiny { color: var(--muted); font-size: 0.78rem; display: block; }
</style>
"""

_TYPE_STYLE = {
    "transition": {"fill": "#0f766e", "shape": "rect"},
    "sweep": {"fill": "#1d4ed8", "shape": "diamond"},
    "back-take": {"fill": "#c2410c", "shape": "hex"},
    "pass": {"fill": "#7c3aed", "shape": "rect"},
    "escape": {"fill": "#15803d", "shape": "circle"},
    "takedown": {"fill": "#a16207", "shape": "triangle"},
    "submission": {"fill": "#be123c", "shape": "diamond"},
}


def design_session(store: CuratedStore, name: str = "", ruleset: str = ""):
    held = store.design_session(name, ruleset)
    if held is None:
        held = open_design(topic_name=name, topic_ruleset=ruleset)
        if name and ruleset:
            store.put_design_session(held)
    return held


def get_design(app, fields: dict[str, list[str]] | None = None) -> str:
    fields = fields or {}
    store = app.store
    name, ruleset = _topic(store, fields)
    bundle = _bundle(app, store, name, ruleset)
    session = bundle["session"]
    body = (
        _STYLE
        + '<div class="design-stack">\n'
        + _prompt_panel(name, ruleset, bundle)
        + _walk_panel(store, session, name, ruleset, bundle)
        + _map_panel(store, session, name, ruleset, bundle)
        + _draft_panel(store, bundle, name, ruleset)
        + "</div>\n"
        + _map_script()
    )
    title = f"Design · {name}" if name else "Design"
    return render_shell(title=title, current="design", body=body)


def post_design(app, fields: dict[str, list[str]]) -> str:
    store = app.store
    name, ruleset = _topic(store, fields)
    bundle = _bundle(app, store, name, ruleset)
    session = bundle["session"]
    action = _field(fields, "action")
    if action == "propose":
        result = propose(store, session, _field(fields, "paragraph"), _ADVISOR)
        bundle["session"] = result.session
        bundle["paragraph"] = result.paragraph
        bundle["draft"] = result.draft
        bundle["convert_reason"] = ""
        bundle["adding"] = False
    elif action == "convert":
        result = convert(store, session, _ADVISOR)
        if result.draft is None:
            bundle["convert_reason"] = _EMPTY_CONVERT
        else:
            bundle["draft"] = result.draft
            bundle["convert_reason"] = ""
    elif action == "start":
        bundle["session"] = replace(session, walk=AddWalk(), selected_id="")
        bundle["adding"] = True
    elif action == "reset":
        bundle["session"] = open_design(topic_name=name, topic_ruleset=ruleset)
        bundle["notes"] = {}
        bundle["adding"] = False
    elif action == "edit":
        bundle["session"] = edit_mark(session, _field(fields, "mark_id"))
        bundle["adding"] = False
    elif action == "delete":
        mark_id = _field(fields, "mark_id")
        bundle["session"] = delete_mark(session, mark_id)
        bundle["notes"].pop(mark_id, None)
    elif action == "citation":
        bundle["session"] = choose_citation(
            store, session, _field(fields, "mark_id"), _field(fields, "citation_id")
        )
    elif action == "notes":
        bundle["notes"][_field(fields, "mark_id")] = _field(fields, "notes")
    elif action == "nearby":
        bundle["session"] = _start_nearby(store, session, _field(fields, "mark_id"))
        bundle["adding"] = True
    elif action == "rewind":
        bundle["session"] = replace(session, walk=_rewound(session.walk, _field(fields, "step")))
        bundle["adding"] = True
    else:
        step = walk_step(session)
        value = _field(fields, step)
        if not value and step == "named move":
            value = _field(fields, "named_move")
        if not value:
            value = _field(fields, "value")
        if value:
            bundle["session"] = pick(store, session, value)
            bundle["adding"] = bool(bundle["session"].walk.family)
    _commit(store, bundle)
    return _location(name, ruleset)


def _bundle(app, store: CuratedStore, name: str, ruleset: str) -> dict:
    if name and ruleset:
        store.set_current_topic(name, ruleset)
    extras = app.design_ui.setdefault(
        (name, ruleset),
        {
            "notes": {},
            "adding": False,
            "paragraph": "",
            "draft": None,
            "convert_reason": "",
        },
    )
    extras["session"] = design_session(store, name, ruleset)
    if extras.get("draft") is None:
        extras["draft"] = _draft_from_store(store, name, ruleset)
    extras["adding"] = extras.get("adding") or bool(extras["session"].walk.family)
    return extras


def _commit(store: CuratedStore, bundle: dict) -> None:
    session = bundle["session"]
    store.put_design_session(session)
    draft = bundle.get("draft")
    if draft is None:
        return
    from coach_app.edit import open_sheet

    existing = store.sheet(session.topic_name, session.topic_ruleset)
    mode = existing.mode if existing is not None else "read"
    store.put_sheet(open_sheet(store, draft, mode))


def _draft_from_store(store: CuratedStore, name: str, ruleset: str):
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


def _location(name: str, ruleset: str) -> str:
    if name and ruleset:
        return "/design?" + urlencode({"name": name, "ruleset": ruleset})
    return "/design"


def _start_nearby(store: CuratedStore, session, mark_id: str):
    mark = next((item for item in session.marks if item.id == mark_id), None)
    if mark is None:
        return replace(session, walk=AddWalk(), selected_id="")
    start = store.enrichment_node(mark.start_id) if mark.start_id else None
    family = start.family if start is not None else ""
    return replace(
        session,
        walk=AddWalk(
            family=family,
            position_id=mark.start_id,
            occupancy=mark.occupancy,
        ),
        selected_id="",
    )


def _rewound(walk: AddWalk, step: str) -> AddWalk:
    if step == "family":
        return AddWalk()
    if step == "position":
        return AddWalk(family=walk.family)
    if step == "occupancy":
        return AddWalk(family=walk.family, position_id=walk.position_id)
    if step == "type":
        return AddWalk(
            family=walk.family, position_id=walk.position_id, occupancy=walk.occupancy
        )
    if step == "end":
        return AddWalk(
            family=walk.family,
            position_id=walk.position_id,
            occupancy=walk.occupancy,
            type_of_move=walk.type_of_move,
        )
    return walk


def _walk_panel(store, session, name, ruleset, bundle) -> str:
    step = walk_step(session)
    crumbs = _crumbs(store, session, name, ruleset)
    options = "".join(
        _pick_form(store, session, step, option, name, ruleset)
        for option in walk_options(store, session)
    )
    if not options:
        options = '<p class="hint">No options on this path.</p>'
    heading = {
        "family": "Family",
        "position": "Position",
        "occupancy": "Occupancy",
        "type": "Type of move",
        "end": "End position",
        "named move": "Named move",
    }.get(step, step)
    return (
        '<section class="panel" id="add-walk">\n'
        "<h2>Add to the map</h2>\n"
        f"{crumbs}"
        f"<h3>{html.escape(heading)}</h3>\n"
        f"{options}\n"
        "</section>\n"
    )


def _crumbs(store, session, name, ruleset) -> str:
    walk = session.walk
    bits = []
    if walk.family:
        bits.append(("family", _option_label(store, "family", walk.family)))
    if walk.position_id:
        bits.append(("position", _option_label(store, "position", walk.position_id)))
    if walk.occupancy:
        bits.append(("occupancy", walk.occupancy))
    if walk.type_of_move:
        bits.append(("type", _option_label(store, "type", walk.type_of_move)))
    if walk.end_id:
        bits.append(("end", _option_label(store, "end", walk.end_id)))
    if not bits:
        return ""
    parts = []
    for i, (step, label) in enumerate(bits):
        if i:
            parts.append('<span class="sep">/</span>')
        parts.append(
            _form(
                f"rewind-{step}",
                name,
                ruleset,
                {"action": "rewind", "step": step},
                html.escape(label),
            )
        )
    return f'<div class="catalog-crumbs">{"".join(parts)}</div>\n'


def _pick_form(store, session, step, option, name, ruleset) -> str:
    value = str(option)
    label = _option_label(store, step, value)
    slug = _step_slug(step)
    return _form(
        f"{slug}-{value}",
        name,
        ruleset,
        {step: value},
        html.escape(label),
        button_class="pick",
    )


def _map_panel(store, session, name, ruleset, bundle) -> str:
    adding = bundle["adding"] or bool(session.walk.family)
    payload = _payload(store, session, bundle, adding)
    toolbar = (
        '<div class="graph-toolbar">\n'
        + _form("start-add", name, ruleset, {"action": "start"}, "Add to the map", button_class="icon-btn primary")
        + '<button type="button" id="zoom-out" class="icon-btn">Zoom −</button>\n'
        + '<button type="button" id="zoom-in" class="icon-btn">Zoom +</button>\n'
        + '<button type="button" id="recenter" class="icon-btn">Recenter</button>\n'
        + '<button type="button" id="reset-marks" class="icon-btn">Reset marks</button>\n'
        + _form("reset-design", name, ruleset, {"action": "reset"}, "Clear design")
        + "</div>\n"
    )
    empty = ""
    if not session.marks and not adding:
        empty = (
            '<div class="graph-empty"><span>Add to the map. Family, then position, '
            "occupancy, type of move, end position, named move. Right-drag pans.</span></div>\n"
        )
    return (
        '<section class="panel" id="map-stage">\n'
        '<div class="map-stage" id="map-host">\n'
        f"{toolbar}{empty}"
        f"{_svg(store, session, adding)}\n"
        f"{_mark_list(store, session, name, ruleset)}\n"
        f"{_edit_panel(store, session, name, ruleset, bundle)}\n"
        f'<script type="application/json" id="design-state">{html.escape(json.dumps(payload), quote=True)}</script>\n'
        "</div>\n"
        "</section>\n"
    )


def _svg(store, session, adding: bool) -> str:
    nodes = []
    width, height = 1200, 640
    marks = session.marks
    for i, mark in enumerate(marks):
        x = 220 + (i % 5) * 160
        y = 160 + (i // 5) * 120
        style = _TYPE_STYLE.get(mark.type_of_move or mark.target, {})
        fill = style.get("fill", "#78716c")
        dash = ""
        if mark.kind == "occupancy":
            fill = "#78716c"
        elif mark.kind == "system":
            fill = "#c2410c"
        nodes.append(
            f'<g class="mark" data-mark="{html.escape(mark.id, quote=True)}" '
            f'data-kind="{html.escape(mark.kind, quote=True)}" '
            f'data-target="{html.escape(mark.target, quote=True)}">'
            f'<circle cx="{x}" cy="{y}" r="16" fill="{fill}" stroke="#1c1917" stroke-width="2"></circle>'
            f'<line class="leader" x1="{x}" y1="{y}" x2="{x + 22}" y2="{y - 22}" '
            f'stroke="#a8a29e" stroke-width="1" pointer-events="none"></line>'
            f'<text x="{x + 24}" y="{y - 24}">{html.escape(_mark_label(store, mark))}</text>'
            "</g>"
        )
    if adding:
        nodes.append(
            '<g class="mark draft" data-mark="draft" data-kind="draft">'
            '<circle class="draft" cx="480" cy="280" r="18" fill="#fff" stroke="#1c1917" '
            'stroke-width="2.5" stroke-dasharray="5 4"></circle>'
            '<text x="504" y="276">New mark</text>'
            "</g>"
        )
    return (
        f'<svg id="design-map" viewBox="0 0 {width} {height}" preserveAspectRatio="xMidYMid meet">'
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff" pointer-events="all"></rect>'
        f'<g id="world">{"".join(nodes)}</g>'
        "</svg>"
    )


def _mark_list(store, session, name, ruleset) -> str:
    if not session.marks:
        items = '<li class="empty">No marks yet.</li>'
    else:
        rows = []
        for mark in session.marks:
            label = html.escape(_mark_label(store, mark))
            rows.append(
                f'<li data-kind="{html.escape(mark.kind, quote=True)}" '
                f'data-id="{html.escape(mark.id, quote=True)}">{label}'
                + _form(
                    f"edit-{mark.id}",
                    name,
                    ruleset,
                    {"action": "edit", "mark_id": mark.id},
                    "Edit",
                )
                + _form(
                    f"delete-{mark.id}",
                    name,
                    ruleset,
                    {"action": "delete", "mark_id": mark.id},
                    "Delete",
                )
                + _form(
                    f"nearby-{mark.id}",
                    name,
                    ruleset,
                    {"action": "nearby", "mark_id": mark.id},
                    "Add nearby",
                )
                + "</li>"
            )
        items = "".join(rows)
    return f'<section id="marks"><ul class="mark-list">{items}</ul></section>\n'


def _edit_panel(store, session, name, ruleset, bundle) -> str:
    mark = next((item for item in session.marks if item.id == session.selected_id), None)
    if mark is None:
        return ""
    title = html.escape(_mark_label(store, mark))
    notes = html.escape(bundle["notes"].get(mark.id, ""))
    cites = ""
    if mark.kind == "named move":
        offered = citations_on_mark(store, session, mark.id)
        chosen = {pair[1] for pair in session.chosen_citations if pair[0] == mark.target}
        cards = []
        for citation in offered:
            on = " chosen" if citation.id in chosen else ""
            label = "Chosen" if citation.id in chosen else "Use citation"
            cards.append(
                f'<div class="cite{on}">{html.escape(citation.movement)}'
                + _form(
                    f"citation-{citation.id}",
                    name,
                    ruleset,
                    {
                        "action": "citation",
                        "mark_id": mark.id,
                        "citation_id": citation.id,
                    },
                    label,
                )
                + "</div>"
            )
        cites = "".join(cards) or '<p class="hint">No linked citations.</p>'
    return (
        '<section class="panel" id="edit-mark">\n'
        f"<h2>Edit</h2>\n"
        f"<p>{title}</p>\n"
        f"{cites}\n"
        f'<form id="notes-{html.escape(mark.id, quote=True)}" method="post" action="/design">\n'
        f"{_topic_hidden(name, ruleset)}"
        '<input type="hidden" name="action" value="notes">\n'
        f'<input type="hidden" name="mark_id" value="{html.escape(mark.id, quote=True)}">\n'
        '<label for="coach-notes">Coach notes</label>\n'
        f'<textarea id="coach-notes" name="notes">{notes}</textarea>\n'
        '<button type="submit">Save notes</button>\n'
        "</form>\n"
        "</section>\n"
    )


def _prompt_panel(name, ruleset, bundle) -> str:
    paragraph = html.escape(bundle.get("paragraph") or "")
    return (
        '<section class="panel prompt-panel" id="unit-prompt">\n'
        "<h2>Unit paragraph</h2>\n"
        '<p class="hint">This prompt proposes the Design canvas and the Draft under it.</p>\n'
        '<form id="propose-draft" method="post" action="/design">\n'
        f"{_topic_hidden(name, ruleset)}"
        '<input type="hidden" name="action" value="propose">\n'
        '<label for="prompt-text">Prompt</label>\n'
        f'<textarea id="prompt-text" name="paragraph">{paragraph}</textarea>\n'
        '<div class="prompt-actions">'
        '<button type="submit">Propose canvas and Draft</button>'
        "</div>\n"
        "</form>\n"
        '<form id="convert-draft" class="row-form" method="post" action="/design">\n'
        f"{_topic_hidden(name, ruleset)}"
        '<input type="hidden" name="action" value="convert">\n'
        '<button type="submit">Convert canvas to Draft</button>\n'
        "</form>\n"
        "</section>\n"
    )


def _draft_panel(store, bundle, name="", ruleset="") -> str:
    reason = bundle.get("convert_reason") or ""
    draft = bundle.get("draft")
    reason_html = (
        f'<p class="reason" id="convert-reason">{html.escape(reason)}</p>\n' if reason else ""
    )
    if draft is None or not draft.classes:
        body = (
            reason_html
            + '<p class="empty">No first list yet. Propose from the paragraph, or convert the canvas.</p>\n'
        )
    else:
        body = reason_html + "".join(
            _class_card(store, packed, index)
            for index, packed in enumerate(draft.classes)
        )
    modes = ""
    if name and ruleset:
        query = urlencode({"name": name, "ruleset": ruleset})
        modes = (
            '<p class="sheet-modes">'
            f'<a href="/sheet?{query}&amp;mode=read">Read</a> '
            f'<a href="/sheet?{query}&amp;mode=edit">Edit</a> '
            f'<a href="/print?{query}">Print duplex packet</a>'
            "</p>\n"
        )
    return (
        '<section class="panel" id="draft">\n'
        "<h2>Draft</h2>\n"
        '<span class="pill pill-draft">Build proposal</span>\n'
        f"{modes}{body}"
        "</section>\n"
    )


def _class_card(store, packed, index: int) -> str:
    lessons = packed.lessons
    rows = []
    for i, lesson in enumerate(lessons):
        prev = lessons[i - 1] if i else None
        nxt = lessons[i + 1] if i + 1 < len(lessons) else None
        glued = _glued(lesson, nxt) or _follows(prev, lesson)
        follow = _follows(prev, lesson)
        kind = html.escape(lesson.kind)
        row_kind = "tech" if lesson.kind == "technique" else kind
        rows.append(
            f'<tr class="{row_kind}{" glued" if glued else ""}">'
            f'<td class="cell-lesson">{_lesson_cell(store, lesson, _glued(lesson, nxt), follow)}</td>'
            f'<td class="cell-type"><span class="pill pill-{row_kind}">{kind}</span></td>'
            f'<td class="cell-target">{_target_cell(store, lesson)}</td>'
            f'<td class="cell-run">{_what_to_run(store, lesson)}</td>'
            "</tr>"
        )
    heads = "".join(f"<th>{html.escape(column)}</th>" for column in DRAFT_COLUMNS)
    purpose = html.escape(packed.class_record.purpose) if packed.class_record.purpose else ""
    return (
        f'<div class="class-card" data-class="{index}">\n'
        '<div class="cut">'
        '<span class="n">CUT</span>'
        f"<h3>Class {index + 1}</h3>"
        f'<div class="purpose">{purpose}</div>'
        "</div>\n"
        '<table class="sheet">\n'
        '<colgroup><col class="col-lesson"><col class="col-type">'
        '<col class="col-target"><col class="col-run"></colgroup>\n'
        f"<thead><tr>{heads}</tr></thead>\n"
        f"<tbody>{''.join(rows)}</tbody>\n"
        "</table>\n"
        "</div>\n"
    )


def _glued(lesson, nxt) -> bool:
    return (
        nxt is not None
        and lesson.kind == "technique"
        and nxt.kind == "drill"
        and nxt.target == lesson.target
    )


def _follows(prev, lesson) -> bool:
    return (
        prev is not None
        and prev.kind == "technique"
        and lesson.kind == "drill"
        and prev.target == lesson.target
    )


def _lesson_cell(store, lesson, glue: bool, follow: bool) -> str:
    name = html.escape(_target_name(store, lesson.target))
    title = f"{name} drill" if lesson.kind == "drill" else name
    extra = ""
    if glue:
        extra += ' <span class="pill pill-glue">+ drill</span>'
    if follow:
        extra += ' <span class="pill pill-glue">follows technique</span>'
    return f"<strong>{title}</strong>{extra}"


def _target_cell(store, lesson) -> str:
    node = store.enrichment_node(lesson.target) if lesson.target else None
    kind = "system" if node is not None and node.kind == "system" else "named move"
    pill = "sys" if kind == "system" else "move"
    label = html.escape(node.name if node is not None else lesson.target)
    return (
        f'<span class="pill pill-{pill}">{html.escape(kind)}</span> '
        f"<strong>{label}</strong>"
    )


def _what_to_run(store, lesson) -> str:
    if lesson.kind == "technique":
        bullets = []
        for citation_id in lesson.citations:
            citation = store.citation(citation_id)
            if citation is not None:
                bullets.extend(citation.step_bullets)
        if not bullets:
            return '<span class="tiny">No citations chosen yet.</span>'
        items = "".join(f"<li>{html.escape(bullet)}</li>" for bullet in bullets)
        return f'<ul class="steps">{items}</ul>'
    if lesson.kind == "drill":
        job = html.escape(lesson.partner_job) if lesson.partner_job else ""
        return f'<span class="tiny">Partner job</span><div>{job}</div>'
    return ""


def _target_name(store, target_id: str) -> str:
    node = store.enrichment_node(target_id) if target_id else None
    return node.name if node is not None else target_id


def _payload(store, session, bundle, adding: bool) -> dict:
    marks = []
    for mark in session.marks:
        marks.append(
            {
                "id": mark.id,
                "kind": mark.kind,
                "target": mark.target,
                "label": _mark_label(store, mark),
                "start_id": mark.start_id,
                "occupancy": mark.occupancy,
                "type_of_move": mark.type_of_move,
                "end_id": mark.end_id,
                "style": _TYPE_STYLE.get(mark.type_of_move or "", {"fill": "#78716c", "shape": "circle"}),
            }
        )
    return {
        "marks": marks,
        "selected_id": session.selected_id,
        "adding": adding,
        "draft_label": "New mark",
    }


def _mark_label(store, mark) -> str:
    if mark.kind == "occupancy":
        start = store.enrichment_node(mark.start_id) if mark.start_id else None
        where = start.name if start is not None else mark.start_id
        return f"{where} · {mark.target}".strip(" ·")
    if mark.kind == "type":
        return _option_label(store, "type", mark.target)
    node = store.enrichment_node(mark.target)
    if node is not None:
        return node.name
    return mark.target


def _option_label(store, step: str, value: str) -> str:
    if step in {"position", "end", "named move", "type"}:
        node = store.enrichment_node(value)
        if node is not None:
            return node.name
        if step == "type":
            for node in store.enrichment_nodes():
                if node.kind == "type of move" and (
                    node.id == value or node.name.casefold() == value.casefold()
                ):
                    return node.name
    if step == "family":
        return value.replace("-", " ")
    return value


def _form(form_id, name, ruleset, fields: dict[str, str], label: str, button_class: str = "") -> str:
    hidden = [_topic_hidden(name, ruleset)]
    hidden.extend(
        f'<input type="hidden" name="{html.escape(key, quote=True)}" '
        f'value="{html.escape(str(val), quote=True)}">'
        for key, val in fields.items()
    )
    cls = f' class="{button_class}"' if button_class else ""
    return (
        f'<form id="{html.escape(form_id, quote=True)}" class="row-form" method="post" action="/design">'
        + "".join(hidden)
        + f'<button type="submit"{cls}>{label}</button>'
        "</form>"
    )


def _topic_hidden(name: str, ruleset: str) -> str:
    return (
        f'<input type="hidden" name="name" value="{html.escape(name, quote=True)}">'
        f'<input type="hidden" name="ruleset" value="{html.escape(ruleset, quote=True)}">'
    )


def _field(fields: dict[str, list[str]], name: str) -> str:
    values = fields.get(name) or [""]
    return (values[0] if values else "").strip()


def _step_slug(step: str) -> str:
    return step.replace(" ", "-")


def _map_script() -> str:
    return r"""
<script>
(function () {
  var host = document.getElementById("map-host");
  var svg = document.getElementById("design-map");
  var raw = document.getElementById("design-state");
  if (!host || !svg || !raw) return;
  var state;
  try { state = JSON.parse(raw.textContent); } catch (err) { return; }
  var ui = { pan: { x: 0, y: 0 }, zoom: 1, markPos: {}, labelSize: 16, dragging: null, panning: false, moved: false };
  var width = 1200, height = 640;

  function svgEl(name, attrs) {
    var n = document.createElementNS("http://www.w3.org/2000/svg", name);
    Object.keys(attrs || {}).forEach(function (k) { n.setAttribute(k, attrs[k]); });
    return n;
  }
  function applyPan() {
    var world = svg.querySelector("#world");
    if (world) world.setAttribute("transform", "translate(" + ui.pan.x + " " + ui.pan.y + ") scale(" + (ui.zoom || 1) + ")");
  }
  ui.applyPan = applyPan;
  function submitForm(id) {
    var form = document.getElementById(id);
    if (form) form.submit();
  }
  function layoutLabels(nodes, fontSize, w, h) {
    var char = fontSize * 0.62;
    nodes.forEach(function (n) {
      n.labW = Math.max(28, String(n.label).length * char);
      n.labH = fontSize + 8;
      var ang = Math.atan2(n.y - h / 2, n.x - w / 2);
      var r = n.r + fontSize + 10;
      n.lx = n.x + Math.cos(ang) * r;
      n.ly = n.y + Math.sin(ang) * r;
      n.anchor = Math.cos(ang) > 0.25 ? "start" : (Math.cos(ang) < -0.25 ? "end" : "middle");
    });
    function box(n) {
      var x = n.lx;
      if (n.anchor === "end") x = n.lx - n.labW;
      if (n.anchor === "middle") x = n.lx - n.labW / 2;
      return { x: x, y: n.ly - n.labH / 2, w: n.labW, h: n.labH };
    }
    for (var iter = 0; iter < 28; iter++) {
      for (var i = 0; i < nodes.length; i++) {
        var A = box(nodes[i]);
        nodes.forEach(function (m) {
          var nx1 = m.x - m.r - 6, ny1 = m.y - m.r - 6;
          var nx2 = m.x + m.r + 6, ny2 = m.y + m.r + 6;
          var ox = Math.min(A.x + A.w, nx2) - Math.max(A.x, nx1);
          var oy = Math.min(A.y + A.h, ny2) - Math.max(A.y, ny1);
          if (ox > 0 && oy > 0) {
            var dx = (A.x + A.w / 2) - m.x;
            var dy = (A.y + A.h / 2) - m.y;
            var d = Math.sqrt(dx * dx + dy * dy) || 1;
            nodes[i].lx += (dx / d) * (ox * 0.4 + 2);
            nodes[i].ly += (dy / d) * (oy * 0.4 + 2);
          }
        });
        for (var j = i + 1; j < nodes.length; j++) {
          var B = box(nodes[j]);
          var ox = Math.min(A.x + A.w, B.x + B.w) - Math.max(A.x, B.x);
          var oy = Math.min(A.y + A.h, B.y + B.h) - Math.max(A.y, B.y);
          if (ox > 0 && oy > 0) {
            var sign = (nodes[j].ly - nodes[i].ly) >= 0 ? 1 : -1;
            nodes[i].ly -= sign * (oy / 2 + 2);
            nodes[j].ly += sign * (oy / 2 + 2);
          }
        }
        nodes[i].lx = Math.max(8 + nodes[i].labW / 4, Math.min(w - 8 - nodes[i].labW / 4, nodes[i].lx));
        nodes[i].ly = Math.max(fontSize, Math.min(h - 4, nodes[i].ly));
      }
    }
  }
  function worldToScreen(wx, wy) {
    var pt = svg.createSVGPoint();
    pt.x = ui.pan.x + (ui.zoom || 1) * wx;
    pt.y = ui.pan.y + (ui.zoom || 1) * wy;
    var ctm = svg.getScreenCTM();
    if (!ctm) return { x: wx, y: wy };
    var s = pt.matrixTransform(ctm);
    return { x: s.x, y: s.y };
  }
  function worldPoint(clientX, clientY) {
    var pt = svg.createSVGPoint();
    pt.x = clientX;
    pt.y = clientY;
    var ctm = svg.getScreenCTM();
    if (!ctm) return { x: clientX, y: clientY };
    var p = pt.matrixTransform(ctm.inverse());
    var z = ui.zoom || 1;
    return { x: (p.x - ui.pan.x) / z, y: (p.y - ui.pan.y) / z };
  }
  function appendMarkShape(g, n, fill, stroke, sw) {
    var shape = (n.style && n.style.shape) || "circle";
    if (shape === "diamond") {
      g.appendChild(svgEl("polygon", {
        points: [n.x, n.y - n.r, n.x + n.r, n.y, n.x, n.y + n.r, n.x - n.r, n.y].join(" "),
        fill: fill, stroke: stroke, "stroke-width": String(sw)
      }));
    } else if (shape === "hex") {
      var pts = [];
      for (var i = 0; i < 6; i++) {
        var a = Math.PI / 3 * i - Math.PI / 6;
        pts.push((n.x + Math.cos(a) * n.r) + "," + (n.y + Math.sin(a) * n.r));
      }
      g.appendChild(svgEl("polygon", { points: pts.join(" "), fill: fill, stroke: stroke, "stroke-width": String(sw) }));
    } else if (shape === "triangle") {
      g.appendChild(svgEl("polygon", {
        points: [n.x, n.y - n.r, n.x + n.r, n.y + n.r, n.x - n.r, n.y + n.r].join(" "),
        fill: fill, stroke: stroke, "stroke-width": String(sw)
      }));
    } else if (shape === "rect") {
      g.appendChild(svgEl("rect", {
        x: String(n.x - n.r), y: String(n.y - n.r), width: String(n.r * 2), height: String(n.r * 2), rx: "4",
        fill: fill, stroke: stroke, "stroke-width": String(sw)
      }));
    } else {
      g.appendChild(svgEl("circle", {
        cx: String(n.x), cy: String(n.y), r: String(n.r), fill: fill, stroke: stroke, "stroke-width": String(sw)
      }));
    }
  }

  var nodes = [];
  (state.marks || []).forEach(function (mark, i) {
    var n = {
      id: mark.id, kind: mark.kind, label: mark.label, style: mark.style || {},
      r: mark.kind === "occupancy" ? 26 : 16,
      x: 220 + (i % 5) * 160, y: 160 + Math.floor(i / 5) * 120
    };
    if (ui.markPos[n.id]) { n.x = ui.markPos[n.id].x; n.y = ui.markPos[n.id].y; }
    nodes.push(n);
  });
  if (state.adding) {
    nodes.push({ id: "draft", kind: "draft", label: state.draft_label || "New mark", style: {}, r: 18, x: 480, y: 280 });
  }

  var world = svg.querySelector("#world");
  if (!world) {
    world = svgEl("g");
    world.setAttribute("id", "world");
    svg.appendChild(world);
  }
  var linkG = svgEl("g");
  var nodeG = svgEl("g");
  var labelG = svgEl("g");
  world.innerHTML = "";
  world.appendChild(linkG);
  world.appendChild(nodeG);
  world.appendChild(labelG);
  applyPan();

  function paintGraph() {
    applyPan();
    for (var i = 0; i < nodes.length; i++) {
      for (var j = i + 1; j < nodes.length; j++) {
        var a = nodes[i], b = nodes[j];
        var dx = b.x - a.x, dy = b.y - a.y;
        var dist = Math.sqrt(dx * dx + dy * dy) || 1;
        var min = a.r + b.r + 28;
        if (dist < min) {
          var p = (min - dist) / dist * 0.5;
          a.x -= dx * p; a.y -= dy * p; b.x += dx * p; b.y += dy * p;
        }
      }
    }
    nodes.forEach(function (n) { if (n.id !== "draft") ui.markPos[n.id] = { x: n.x, y: n.y }; });
    layoutLabels(nodes, ui.labelSize, width, height);
    linkG.innerHTML = "";
    nodeG.innerHTML = "";
    labelG.innerHTML = "";
    nodes.forEach(function (n) {
      var leader = svgEl("line", {
        x1: String(n.x), y1: String(n.y), x2: String(n.lx), y2: String(n.ly),
        stroke: "#a8a29e", "stroke-width": "1", "pointer-events": "none", "class": "leader"
      });
      labelG.appendChild(leader);
      var lab = svgEl("text", {
        x: String(n.lx), y: String(n.ly), "text-anchor": n.anchor, fill: "#1c1917",
        "font-size": String(ui.labelSize), "data-mark": n.id
      });
      lab.textContent = n.label;
      labelG.appendChild(lab);
      var g = svgEl("g", { "data-mark": n.id, style: "cursor:grab" });
      var fill = (n.style && n.style.fill) || (n.kind === "occupancy" ? "#78716c" : "#1d4ed8");
      if (n.kind === "draft") {
        g.appendChild(svgEl("circle", {
          cx: String(n.x), cy: String(n.y), r: String(n.r), fill: "#fff", stroke: "#1c1917",
          "stroke-width": "2.5", "stroke-dasharray": "5 4", "class": "draft"
        }));
      } else if (n.kind === "occupancy" || n.kind === "system") {
        g.appendChild(svgEl("circle", {
          cx: String(n.x), cy: String(n.y), r: String(n.r),
          fill: n.kind === "system" ? "#c2410c" : fill, stroke: "#1c1917", "stroke-width": "3"
        }));
      } else {
        appendMarkShape(g, n, fill, "#1c1917", 2);
      }
      nodeG.appendChild(g);
    });
  }
  paintGraph();

  function nodeById(id) {
    for (var i = 0; i < nodes.length; i++) if (nodes[i].id === id) return nodes[i];
    return null;
  }
  function hitMarkAt(e) {
    var el = e.target;
    while (el && el !== svg && el !== host) {
      var id = el.getAttribute && el.getAttribute("data-mark");
      if (id && id !== "draft") return nodeById(id);
      el = el.parentNode;
    }
    var ctm = svg.getScreenCTM();
    var scale = ctm ? (Math.hypot(ctm.a, ctm.b) || 1) : 1;
    var z = ui.zoom || 1;
    var best = null, bestD = 1e9;
    nodes.forEach(function (n) {
      if (n.kind === "draft") return;
      var s = worldToScreen(n.x, n.y);
      var d = Math.hypot(e.clientX - s.x, e.clientY - s.y);
      var hitR = Math.max(36, (n.r + 28) * z * scale);
      if (d < hitR && d < bestD) { best = n; bestD = d; }
      if (n.lx != null) {
        var ls = worldToScreen(n.lx, n.ly);
        var ld = Math.hypot(e.clientX - ls.x, e.clientY - ls.y);
        if (ld < 32 && ld < bestD) { best = n; bestD = ld; }
      }
    });
    return best;
  }

  host.addEventListener("click", function (e) {
    if (e.target.closest && e.target.closest(".graph-toolbar")) return;
    if (ui.moved || ui.panning) { e.preventDefault(); return; }
    var hit = hitMarkAt(e);
    if (hit && hit.kind !== "draft") {
      e.preventDefault();
      submitForm("edit-" + hit.id);
      return;
    }
    if (!state.adding) submitForm("start-add");
  }, true);
  host.addEventListener("dblclick", function (e) {
    var hit = hitMarkAt(e);
    if (hit && hit.kind !== "draft") {
      e.preventDefault();
      submitForm("nearby-" + hit.id);
    }
  });
  host.addEventListener("contextmenu", function (e) {
    e.preventDefault();
    var hit = hitMarkAt(e);
    if (hit && hit.kind !== "draft") submitForm("delete-" + hit.id);
  });
  svg.addEventListener("pointerdown", function (e) {
    var hit = hitMarkAt(e);
    if (e.button === 2) {
      if (hit) return;
      ui.panning = true;
      ui.moved = false;
      host.classList.add("panning");
      ui.panFrom = { x: e.clientX, y: e.clientY, px: ui.pan.x, py: ui.pan.y };
      try { svg.setPointerCapture(e.pointerId); } catch (err) {}
      return;
    }
    if (hit && hit.kind !== "draft") {
      ui.dragging = hit;
      ui.moved = false;
      ui.dragFrom = { x: e.clientX, y: e.clientY };
      try { svg.setPointerCapture(e.pointerId); } catch (err) {}
    }
  });
  svg.addEventListener("pointermove", function (e) {
    if (ui.panning && ui.panFrom) {
      ui.pan = { x: ui.panFrom.px + (e.clientX - ui.panFrom.x), y: ui.panFrom.py + (e.clientY - ui.panFrom.y) };
      ui.moved = true;
      applyPan();
      return;
    }
    if (ui.dragging && ui.dragFrom) {
      if (Math.hypot(e.clientX - ui.dragFrom.x, e.clientY - ui.dragFrom.y) > 6) ui.moved = true;
      var p = worldPoint(e.clientX, e.clientY);
      ui.dragging.x = p.x;
      ui.dragging.y = p.y;
      paintGraph();
    }
  });
  svg.addEventListener("pointerup", function () {
    ui.panning = false;
    ui.dragging = null;
    host.classList.remove("panning");
    setTimeout(function () { ui.moved = false; }, 120);
  });

  var zoomIn = document.getElementById("zoom-in");
  var zoomOut = document.getElementById("zoom-out");
  var recenter = document.getElementById("recenter");
  var resetMarks = document.getElementById("reset-marks");
  if (zoomIn) zoomIn.addEventListener("click", function () {
    ui.zoom = Math.min(2.5, Math.round((ui.zoom + 0.15) * 100) / 100);
    applyPan();
  });
  if (zoomOut) zoomOut.addEventListener("click", function () {
    ui.zoom = Math.max(0.5, Math.round((ui.zoom - 0.15) * 100) / 100);
    applyPan();
  });
  if (recenter) recenter.addEventListener("click", function () {
    ui.pan = { x: 0, y: 0 };
    ui.zoom = 1;
    applyPan();
  });
  if (resetMarks) resetMarks.addEventListener("click", function () {
    ui.markPos = {};
    ui.pan = { x: 0, y: 0 };
    ui.zoom = 1;
    nodes.forEach(function (n, i) {
      if (n.kind === "draft") { n.x = 480; n.y = 280; return; }
      n.x = 220 + (i % 5) * 160;
      n.y = 160 + Math.floor(i / 5) * 120;
    });
    paintGraph();
  });
})();
</script>
"""


add_screen(Screen("design", "/design", "Design", get=get_design, post=post_design))
