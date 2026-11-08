"""Print view for the duplex advising packet from packet() page records."""

from __future__ import annotations

import html
from urllib.parse import urlencode

from coach_app.app import Screen, add_screen, render_shell
from coach_app.build import DRAFT_COLUMNS
from coach_app.print_packet import MARGIN_IN, PRINT_CSS, PrintPage, packet
from coach_app.store import CuratedStore
from coach_app.ui_design import design_session
from coach_app.ui_sheet import current_sheet

_TYPE_FILL = {
    "occupancy": "#78716c",
    "system": "#c2410c",
    "transition": "#0f766e",
    "sweep": "#1d4ed8",
    "back-take": "#c2410c",
    "named move": "#1d4ed8",
}

_STYLE = f"""
<style>
{PRINT_CSS}
.print-toolbar {{ display: flex; flex-wrap: wrap; gap: 0.45rem; margin: 0 0 0.7rem; }}
.print-canvas {{
  page: canvas;
  break-after: page;
  page-break-after: always;
  margin: 0 0 1rem;
}}
.print-canvas svg {{
  width: 100%;
  height: 6.9in;
  max-height: 6.9in;
  border: 1px solid #1c1917;
  background: #fff;
  display: block;
}}
.class-card {{
  page: class-card;
  break-inside: avoid-page;
  page-break-inside: avoid;
  background: var(--paper);
  border: 2px solid var(--line);
  border-radius: 14px;
  overflow: hidden;
  margin: 0 0 1rem;
}}
.class-card .cut {{
  display: flex; flex-wrap: wrap; align-items: center; gap: 0.55rem 1rem;
  padding: 0.7rem 1rem; background: #1c1917; color: #fafaf9;
}}
.class-card .cut .n {{ font-size: 0.72rem; color: #a8a29e; }}
.class-card .cut h3 {{
  margin: 0; font-size: 1.05rem; font-family: var(--serif);
  color: #fafaf9; text-transform: none; letter-spacing: 0;
}}
.class-card .purpose {{ color: #a8a29e; font-size: 0.85rem; margin-left: auto; }}
table.sheet {{ width: 100%; border-collapse: collapse; table-layout: fixed; background: #fff; }}
table.sheet th, table.sheet td {{
  border-bottom: 1px solid var(--line); padding: 0.5rem 0.55rem; vertical-align: top; text-align: left;
}}
table.sheet th {{
  background: #f5f5f4; font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.04em; color: var(--muted);
}}
.col-lesson {{ width: 32%; }}
.col-type {{ width: 7.2rem; }}
.col-target {{ width: 22%; }}
.col-run {{ width: auto; }}
tr.tech {{ background: linear-gradient(90deg, #dbeafe, #fff 42%); }}
tr.drill {{ background: linear-gradient(90deg, #fef9c3, #fff 42%); }}
tr.sparring {{ background: linear-gradient(90deg, #ffe4e6, #fff 42%); }}
tr.game {{ background: linear-gradient(90deg, #ede9fe, #fff 42%); }}
tr.glued td:first-child {{ box-shadow: inset 4px 0 0 #fb923c; }}
.pill {{ display: inline-block; border-radius: 999px; padding: 0.12rem 0.55rem; font-size: 0.78rem; font-weight: 650; }}
.pill-tech {{ background: #dbeafe; color: #1e3a8a; }}
.pill-drill {{ background: #fef9c3; color: #854d0e; }}
.pill-sparring {{ background: #ffe4e6; color: #9f1239; }}
.pill-game {{ background: #ede9fe; color: #5b21b6; }}
.pill-sys {{ background: #ccfbf1; color: #0f766e; }}
.pill-move {{ background: #dbeafe; color: #1d4ed8; }}
.pill-glue {{ background: #ffedd5; color: #9a3412; }}
.steps {{ margin: 0.3rem 0 0; padding-left: 1.1rem; }}
.steps li {{ margin: 0.2rem 0; }}
.tiny {{ color: var(--muted); font-size: 0.78rem; display: block; }}
.unit-para, .success {{ display: none !important; }}
@media print {{
  header, nav, .print-toolbar, header .meta {{ display: none !important; }}
  body {{ background: #fff; }}
  .page {{ max-width: none; width: 100%; margin: 0; padding: 0; }}
  main {{ margin: 0; }}
  .class-card, .print-canvas {{ box-shadow: none; border-radius: 0; }}
  .cut {{ -webkit-print-color-adjust: exact; print-color-adjust: exact; }}
  tr.tech {{ background: #dbeafe; }}
  tr.drill {{ background: #fef9c3; }}
  tr.sparring {{ background: #ffe4e6; }}
  tr.game {{ background: #ede9fe; }}
}}
</style>
"""


def get_print(store: CuratedStore, fields: dict[str, list[str]] | None = None) -> str:
    fields = fields or {}
    name, ruleset = _topic(store, fields)
    session = design_session(store, name, ruleset) if name else None
    sheet = current_sheet(store, name, ruleset) if name else None
    if session is None:
        pages = (
            PrintPage(kind="canvas", orientation="landscape", margin_in=MARGIN_IN),
        )
    elif sheet is None:
        pages = (
            PrintPage(
                kind="canvas",
                orientation="landscape",
                margin_in=MARGIN_IN,
                marks=session.marks,
            ),
        )
    else:
        pages = packet(session, sheet, store)
    query = urlencode({"name": name, "ruleset": ruleset}) if name and ruleset else ""
    toolbar = (
        '<div class="print-toolbar">'
        '<button type="button" onclick="window.print()">Print duplex packet</button>'
        + (f'<a href="/design?{html.escape(query, quote=True)}">Design</a>' if query else "")
        + (f'<a href="/sheet?{html.escape(query, quote=True)}">Sheet</a>' if query else "")
        + "</div>\n"
    )
    body = _STYLE + toolbar + "".join(_page_html(store, page) for page in pages)
    title = f"Print · {name}" if name else "Print"
    return render_shell(title=title, current="print", body=body)


def _page_html(store, page: PrintPage) -> str:
    if page.kind == "canvas":
        return _canvas_html(store, page)
    return _class_card_html(store, page)


def _canvas_html(store, page: PrintPage) -> str:
    width, height = 1400, 960
    nodes = []
    for index, mark in enumerate(page.marks):
        x = int(width * 0.14) + (index % 5) * int(width * 0.16)
        y = int(height * 0.16) + (index // 5) * int(height * 0.18)
        fill = _TYPE_FILL.get(mark.type_of_move or mark.kind, "#78716c")
        label = html.escape(_mark_label(store, mark))
        nodes.append(
            f'<g class="mark" data-kind="{html.escape(mark.kind, quote=True)}">'
            f'<circle cx="{x}" cy="{y}" r="20" fill="{fill}" stroke="#1c1917" stroke-width="3"></circle>'
            f'<text x="{x + 28}" y="{y + 6}" font-size="18" fill="#1c1917">{label}</text>'
            "</g>"
        )
    return (
        f'<article class="print-canvas" data-kind="canvas" '
        f'data-orientation="{html.escape(page.orientation, quote=True)}" '
        f'data-margin="{page.margin_in}">\n'
        f'<svg viewBox="0 0 {width} {height}" preserveAspectRatio="xMidYMid meet">'
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="#ffffff"></rect>'
        f"{''.join(nodes)}"
        "</svg>\n"
        "</article>\n"
    )


def _class_card_html(store, page: PrintPage) -> str:
    index = 0 if page.class_index is None else page.class_index
    rows = []
    for card in page.cards:
        lesson = card.lesson
        row_kind = "tech" if lesson.kind == "technique" else lesson.kind
        glued = " glued" if card.glued else ""
        rows.append(
            f'<tr class="{html.escape(row_kind)}{glued}">'
            f'<td class="cell-lesson">{_lesson_cell(card)}</td>'
            f'<td class="cell-type"><span class="pill pill-{html.escape(row_kind)}">'
            f"{html.escape(lesson.kind)}</span></td>"
            f'<td class="cell-target">{_target_cell(store, lesson, card)}</td>'
            f'<td class="cell-run">{_run_cell(card)}</td>'
            "</tr>"
        )
    heads = "".join(f"<th>{html.escape(column)}</th>" for column in DRAFT_COLUMNS)
    purpose = html.escape(page.purpose)
    return (
        f'<article class="class-card" data-kind="class card" '
        f'data-orientation="{html.escape(page.orientation, quote=True)}" '
        f'data-class="{index}" data-margin="{page.margin_in}">\n'
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
        "</article>\n"
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


def _mark_label(store, mark) -> str:
    if mark.kind == "occupancy":
        start = store.enrichment_node(mark.start_id) if mark.start_id else None
        where = start.name if start is not None else mark.start_id
        return f"{where} · {mark.target}".strip(" ·")
    node = store.enrichment_node(mark.target) if mark.target else None
    if node is not None:
        return node.name
    return mark.target


def _topic(store, fields: dict[str, list[str]]) -> tuple[str, str]:
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


def _field(fields: dict[str, list[str]], key: str) -> str:
    values = fields.get(key) or [""]
    return (values[0] if values else "").strip()


add_screen(Screen("print", "/print", "", get=get_print))
