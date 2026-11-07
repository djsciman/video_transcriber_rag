"""Finder screen: browse, search, and organize the live enrichment catalog."""

from __future__ import annotations

import html

from coach_app.app import Screen, add_screen, render_shell
from coach_app.store import CuratedStore, EnrichmentNode

_FAMILY_ORDER = (
    "standing",
    "guard",
    "leg-entanglement",
    "passing",
    "pin",
    "turtle",
    "back",
    "other",
)
_STYLE = """
<style>
.finder-layout { display: grid; grid-template-columns: 1fr 1fr; gap: 0.7rem; }
.row-form { margin: 0 0 0.2rem; }
.row-form button {
  width: 100%;
  text-align: left;
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
}
.row-form button.on { background: #ffedd5; }
.family {
  font-size: 0.68rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--muted);
  padding: 0.45rem 0 0.15rem;
}
.leaf, .cite {
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 0.5rem 0.6rem;
  margin: 0.35rem 0;
  background: #fff;
}
.cite { border-style: dashed; }
.xref { color: var(--muted); font-size: 0.8rem; margin: 0.2rem 0 0; }
.count { color: var(--muted); font-size: 0.78rem; }
</style>
"""


def get_finder(store: CuratedStore) -> str:
    walk = _walk(store)
    starts = store.browse_hierarchy()
    types = store.browse_hierarchy(walk["start"]) if walk["start"] else ()
    ends = (
        store.browse_hierarchy(walk["start"], walk["type_of_move"])
        if walk["start"] and walk["type_of_move"]
        else ()
    )
    leaves = _named_moves(store, walk["start"], walk["type_of_move"], walk["end"])
    hits = store.search_enrichment(walk["query"]) if walk["query"] else ()
    uncategorized = tuple(
        citation for citation in store.citations() if not citation.named_move_id
    )
    body = (
        _STYLE
        + _search_panel(walk)
        + _search_results(hits)
        + '<div class="finder-layout">\n'
        + _starts_panel(starts, walk)
        + _types_panel(types, walk)
        + _ends_panel(ends, walk)
        + _leaves_panel(leaves, walk)
        + "</div>\n"
        + _uncategorized_panel(uncategorized)
        + _organize_panel(walk)
    )
    return render_shell(title="Finder", current="finder", body=body)


def post_finder(store: CuratedStore, fields: dict[str, list[str]]) -> str:
    action = _field(fields, "action")
    walk = _walk(store)
    if action == "search":
        walk["query"] = _field(fields, "query")
    elif action == "select_start":
        walk["start"] = _field(fields, "start")
        walk["type_of_move"] = ""
        walk["end"] = ""
    elif action == "select_type":
        walk["type_of_move"] = _field(fields, "type_of_move")
        walk["end"] = ""
    elif action == "select_end":
        walk["end"] = _field(fields, "end")
    elif action == "add":
        _add_node(store, fields)
    elif action == "rename":
        node_id = _field(fields, "node_id")
        name = _field(fields, "name")
        if node_id and name:
            store.rename_enrichment_node(node_id, name)
    elif action == "move":
        node_id = _field(fields, "node_id")
        if node_id:
            store.move_enrichment_node(
                node_id,
                start_id=_field(fields, "start_id"),
                type_of_move=_field(fields, "type_of_move"),
                end_id=_field(fields, "end_id"),
            )
    elif action == "delete":
        node_id = _field(fields, "node_id")
        if node_id:
            store.delete_enrichment_node(node_id)
    return "/finder"


def _add_node(store: CuratedStore, fields: dict[str, list[str]]) -> None:
    kind = _field(fields, "kind")
    name = _field(fields, "name")
    if not name:
        return
    if kind == "position":
        store.put_enrichment_node(
            EnrichmentNode(
                kind="position",
                name=name,
                family=_field(fields, "family") or "other",
            )
        )
        return
    if kind == "type of move":
        store.put_enrichment_node(EnrichmentNode(kind="type of move", name=name))
        return
    if kind == "submission":
        store.put_enrichment_node(EnrichmentNode(kind="submission", name=name))
        return
    if kind == "named move":
        store.put_enrichment_node(
            EnrichmentNode(
                kind="named move",
                name=name,
                start_id=_field(fields, "start_id"),
                type_of_move=_field(fields, "type_of_move"),
                end_id=_field(fields, "end_id"),
                ruleset=_field(fields, "ruleset") or "both",
            )
        )


def _walk(store: CuratedStore) -> dict[str, str]:
    walk = getattr(store, "_finder_walk", None)
    if not isinstance(walk, dict):
        walk = {"start": "", "type_of_move": "", "end": "", "query": ""}
        store._finder_walk = walk
    return walk


def _named_moves(store: CuratedStore, start: str, type_of_move: str, end: str):
    if not (start and type_of_move and end):
        return ()
    return tuple(
        node
        for node in store.enrichment_nodes()
        if node.kind == "named move"
        and node.start_id == start
        and node.type_of_move == type_of_move
        and node.end_id == end
    )


def _search_panel(walk: dict[str, str]) -> str:
    query = html.escape(walk["query"], quote=True)
    return (
        '<section class="panel" id="search-panel">\n'
        "<h2>Search</h2>\n"
        '<form id="search" method="post" action="/finder">\n'
        '<input type="hidden" name="action" value="search">\n'
        '<label for="query">Search names, aliases, judo, wrestling</label>\n'
        f'<input id="query" name="query" type="search" value="{query}">\n'
        '<button type="submit">Search</button>\n'
        "</form>\n"
        "</section>\n"
    )


def _search_results(hits: tuple[EnrichmentNode, ...]) -> str:
    if not hits:
        return ""
    items = []
    for node in hits:
        detail = html.escape(node.kind)
        if node.cross_refs:
            detail += " · " + html.escape(", ".join(node.cross_refs))
        items.append(
            '<div class="leaf">'
            f'<div class="name">{html.escape(node.name)}</div>'
            f'<div class="xref">{detail}</div>'
            "</div>"
        )
    return (
        '<section class="panel" id="search-results">\n'
        "<h2>Search results</h2>\n"
        + "\n".join(items)
        + "\n</section>\n"
    )


def _starts_panel(starts: tuple[EnrichmentNode, ...], walk: dict[str, str]) -> str:
    grouped: dict[str, list[EnrichmentNode]] = {}
    for node in starts:
        grouped.setdefault(node.family or "other", []).append(node)
    families = [fam for fam in _FAMILY_ORDER if fam in grouped]
    families.extend(fam for fam in grouped if fam not in _FAMILY_ORDER)
    rows = []
    for family in families:
        rows.append(f'<div class="family">{html.escape(family.replace("-", " "))}</div>')
        for node in grouped[family]:
            rows.append(
                _select_row(
                    form_id=f"start-{node.id}",
                    action="select_start",
                    fields={"start": node.id},
                    label=node.name,
                    selected=walk["start"] == node.id,
                )
            )
    return (
        '<section class="panel" id="starts">\n'
        "<h2>Starting position</h2>\n"
        + "\n".join(rows)
        + "\n</section>\n"
    )


def _types_panel(types: tuple[EnrichmentNode, ...], walk: dict[str, str]) -> str:
    if not walk["start"]:
        body = '<p class="xref">Pick a starting position.</p>'
    else:
        body = "\n".join(
            _select_row(
                form_id=f"type-{node.id}",
                action="select_type",
                fields={"type_of_move": node.id},
                label=node.name,
                selected=walk["type_of_move"] == node.id,
            )
            for node in types
        )
    return (
        '<section class="panel" id="types">\n'
        "<h2>Type of move</h2>\n"
        f"{body}\n"
        "</section>\n"
    )


def _ends_panel(ends: tuple[EnrichmentNode, ...], walk: dict[str, str]) -> str:
    if not walk["type_of_move"]:
        body = '<p class="xref">Pick a type of move.</p>'
    else:
        body = "\n".join(
            _select_row(
                form_id=f"end-{node.id}",
                action="select_end",
                fields={"end": node.id},
                label=node.name,
                selected=walk["end"] == node.id,
                extra=node.kind,
            )
            for node in ends
        )
    return (
        '<section class="panel" id="ends">\n'
        "<h2>Ending position or submission</h2>\n"
        f"{body}\n"
        "</section>\n"
    )


def _leaves_panel(leaves: tuple[EnrichmentNode, ...], walk: dict[str, str]) -> str:
    if not walk["end"]:
        body = '<p class="xref">Pick an ending.</p>'
    else:
        cards = []
        for node in leaves:
            aliases = (
                f'<div class="xref">Also: {html.escape(", ".join(node.aliases))}</div>'
                if node.aliases
                else ""
            )
            refs = (
                f'<div class="xref">{html.escape(" · ".join(node.cross_refs))}</div>'
                if node.cross_refs
                else ""
            )
            cards.append(
                '<div class="leaf">'
                f'<div class="name">{html.escape(node.name)} '
                f'<span class="count">{html.escape(node.ruleset or "both")}</span></div>'
                f"{aliases}{refs}"
                "</div>"
            )
        body = "\n".join(cards)
    return (
        '<section class="panel" id="named-moves">\n'
        "<h2>Named-move leaves</h2>\n"
        f"{body}\n"
        "</section>\n"
    )


def _uncategorized_panel(citations) -> str:
    if citations:
        cards = []
        for citation in citations:
            cards.append(
                '<div class="cite">'
                f"<strong>{html.escape(citation.movement)}</strong> "
                '<span class="count">Uncategorized</span>'
                "</div>"
            )
        body = "\n".join(cards)
    else:
        body = '<p class="empty">No uncategorized citations.</p>'
    return (
        '<section class="panel uncat" id="uncategorized">\n'
        "<h2>Uncategorized</h2>\n"
        f"{body}\n"
        "</section>\n"
    )


def _organize_panel(walk: dict[str, str]) -> str:
    start = html.escape(walk["start"], quote=True)
    move = html.escape(walk["type_of_move"], quote=True)
    end = html.escape(walk["end"], quote=True)
    return (
        '<section class="panel" id="organize">\n'
        "<h2>Organize</h2>\n"
        '<form id="add" method="post" action="/finder">\n'
        '<input type="hidden" name="action" value="add">\n'
        '<label for="add-kind">Kind</label>\n'
        '<select id="add-kind" name="kind">\n'
        '<option value="position">Position</option>\n'
        '<option value="type of move">Type of move</option>\n'
        '<option value="submission">Submission</option>\n'
        '<option value="named move">Named move</option>\n'
        "</select>\n"
        '<label for="add-name">Name</label>\n'
        '<input id="add-name" name="name" type="text">\n'
        '<label for="add-family">Family</label>\n'
        '<input id="add-family" name="family" type="text" value="guard">\n'
        '<label for="add-start">Start</label>\n'
        f'<input id="add-start" name="start_id" type="text" value="{start}">\n'
        '<label for="add-type">Type of move</label>\n'
        f'<input id="add-type" name="type_of_move" type="text" value="{move}">\n'
        '<label for="add-end">End</label>\n'
        f'<input id="add-end" name="end_id" type="text" value="{end}">\n'
        '<label for="add-ruleset">Ruleset</label>\n'
        '<input id="add-ruleset" name="ruleset" type="text" value="both">\n'
        '<button type="submit">Add</button>\n'
        "</form>\n"
        '<form id="rename" method="post" action="/finder">\n'
        '<input type="hidden" name="action" value="rename">\n'
        '<label for="rename-id">Node</label>\n'
        '<input id="rename-id" name="node_id" type="text">\n'
        '<label for="rename-name">New name</label>\n'
        '<input id="rename-name" name="name" type="text">\n'
        '<button type="submit">Rename</button>\n'
        "</form>\n"
        '<form id="move" method="post" action="/finder">\n'
        '<input type="hidden" name="action" value="move">\n'
        '<label for="move-id">Named move</label>\n'
        '<input id="move-id" name="node_id" type="text">\n'
        '<label for="move-start">Start</label>\n'
        f'<input id="move-start" name="start_id" type="text" value="{start}">\n'
        '<label for="move-type">Type of move</label>\n'
        f'<input id="move-type" name="type_of_move" type="text" value="{move}">\n'
        '<label for="move-end">End</label>\n'
        f'<input id="move-end" name="end_id" type="text" value="{end}">\n'
        '<button type="submit">Move named move</button>\n'
        "</form>\n"
        '<form id="delete" method="post" action="/finder">\n'
        '<input type="hidden" name="action" value="delete">\n'
        '<label for="delete-id">Node</label>\n'
        '<input id="delete-id" name="node_id" type="text">\n'
        '<button type="submit">Delete</button>\n'
        "</form>\n"
        "</section>\n"
    )


def _select_row(
    *,
    form_id: str,
    action: str,
    fields: dict[str, str],
    label: str,
    selected: bool,
    extra: str = "",
) -> str:
    hidden = [
        f'<input type="hidden" name="action" value="{html.escape(action, quote=True)}">'
    ]
    hidden.extend(
        f'<input type="hidden" name="{html.escape(name, quote=True)}" '
        f'value="{html.escape(value, quote=True)}">'
        for name, value in fields.items()
    )
    count = (
        f'<span class="count">{html.escape(extra)}</span>' if extra else ""
    )
    on = " on" if selected else ""
    return (
        f'<form id="{html.escape(form_id, quote=True)}" class="row-form" '
        'method="post" action="/finder">'
        + "".join(hidden)
        + f'<button type="submit" class="row{on}">{html.escape(label)}{count}</button>'
        "</form>"
    )


def _field(fields: dict[str, list[str]], name: str, default: str = "") -> str:
    values = fields.get(name) or [default]
    return (values[0] if values else default).strip()


add_screen(Screen("finder", "/finder", "Finder", get=get_finder, post=post_finder))
