"""Coach screen: review proposed named-move links and write coach-authored citations."""

from __future__ import annotations

import html

from coach_app.app import Screen, add_screen, render_shell
from coach_app.placement import (
    PlacementAdvisor,
    PlacementDecision,
    apply_placement_decisions,
    propose_placement_pass,
    write_coach_authored_citation,
)
from coach_app.store import Citation, CuratedStore, EnrichmentNode

_ADVISOR = PlacementAdvisor()
_STYLE = """
<style>
#placement-pass .cite-list {
  list-style: none;
  padding: 0;
  margin: 0;
  max-height: 70vh;
  overflow: auto;
}
.cite-list > li { border-top: 1px solid var(--line); padding: .85rem 0; }
.cite-list > li:first-child { border-top: 0; }
.cite-head { display: flex; flex-wrap: wrap; gap: .4rem .6rem; align-items: center; margin-bottom: .35rem; font-weight: 650; }
.cite-meta { color: var(--muted); font-size: .86rem; margin-bottom: .35rem; }
.steps { margin: .35rem 0 0; padding-left: 1.15rem; max-width: 72ch; }
.steps li { margin: .28rem 0; }
.leaf {
  border: 1px solid var(--line);
  border-radius: 10px;
  padding: 0.5rem 0.6rem;
  margin: 0.35rem 0;
  background: #fff;
}
.xref { color: var(--muted); font-size: 0.8rem; margin: 0.2rem 0 0; }
.actions { display: flex; gap: .45rem; margin-top: .45rem; }
textarea { font: inherit; border: 1px solid var(--line); border-radius: 8px; padding: .35rem .55rem; width: 100%; min-height: 4.5rem; }
select { font: inherit; border: 1px solid var(--line); border-radius: 8px; padding: .35rem .55rem; background: #fff; width: 100%; }
</style>
"""


def get_place(store: CuratedStore) -> str:
    named_moves = _named_moves(store)
    proposals = propose_placement_pass(store, _ADVISOR)
    body = _STYLE + _pass_panel(store, proposals, named_moves) + _author_panel(named_moves)
    return render_shell(title="Place citations", current="place", body=body)


def post_place(store: CuratedStore, fields: dict[str, list[str]]) -> str:
    action = _field(fields, "action")
    if action in {"accept", "correct", "skip"}:
        named_move_id = _field(fields, "named_move_id")
        if action == "accept" and not named_move_id:
            named_move_id = _field(fields, "proposed_named_move_id")
        apply_placement_decisions(
            store,
            (
                PlacementDecision(
                    citation_id=_field(fields, "citation_id"),
                    action=action,
                    named_move_id=named_move_id,
                ),
            ),
        )
    elif action == "author":
        movement = _field(fields, "movement")
        if movement:
            write_coach_authored_citation(
                store,
                movement=movement,
                step_bullets=_bullets(_field(fields, "step_bullets")),
                named_move_id=_field(fields, "named_move_id"),
            )
    return "/place"


def _pass_panel(
    store: CuratedStore,
    proposals,
    named_moves: tuple[EnrichmentNode, ...],
) -> str:
    if not proposals:
        body = '<p class="empty">No uncategorized citations.</p>'
    else:
        cards = []
        for proposal in proposals:
            citation = store.citation(proposal.citation_id)
            if citation is None:
                continue
            cards.append(_citation_card(store, citation, proposal.named_move_id, named_moves))
        body = f'<ul class="cite-list">{"".join(cards)}</ul>'
    return (
        '<section class="panel" id="placement-pass">\n'
        "<h2>Placement review</h2>\n"
        f"{body}\n"
        "</section>\n"
    )


def _citation_card(
    store: CuratedStore,
    citation: Citation,
    proposed_id: str,
    named_moves: tuple[EnrichmentNode, ...],
) -> str:
    proposed = store.enrichment_node(proposed_id) if proposed_id else None
    meta = " · ".join(
        part
        for part in (
            citation.instructor or "",
            citation.instructional or "",
            citation.volume or "",
            citation.chapter or "",
        )
        if part
    )
    meta_html = (
        f'<div class="cite-meta">{html.escape(meta)}</div>\n' if meta else ""
    )
    return (
        "<li>\n"
        f'<div class="cite-head">{html.escape(citation.movement)}</div>\n'
        f"{meta_html}"
        f"{_steps(citation.step_bullets)}"
        f"{_proposed_leaf(store, proposed)}"
        f'<form id="place-{html.escape(citation.id, quote=True)}" method="post" action="/place">\n'
        f'<input type="hidden" name="citation_id" value="{html.escape(citation.id, quote=True)}">\n'
        f'<input type="hidden" name="proposed_named_move_id" value="{html.escape(proposed_id, quote=True)}">\n'
        '<label>Named move</label>\n'
        f'<select name="named_move_id">{_named_move_options(named_moves, proposed_id)}</select>\n'
        '<div class="actions">\n'
        '<button type="submit" name="action" value="accept">Accept</button>\n'
        '<button type="submit" name="action" value="correct">Correct</button>\n'
        '<button type="submit" name="action" value="skip">Skip</button>\n'
        "</div>\n"
        "</form>\n"
        "</li>\n"
    )


def _proposed_leaf(store: CuratedStore, node: EnrichmentNode | None) -> str:
    if node is None:
        return '<p class="xref">No proposed named-move link.</p>\n'
    aliases = (
        f'<div class="xref">Also: {html.escape(", ".join(node.aliases))}</div>'
        if node.aliases
        else ""
    )
    path = _named_move_path(store, node)
    path_html = f'<div class="xref">{html.escape(path)}</div>' if path else ""
    return (
        '<div class="leaf">'
        f'<div class="name">Proposed: {html.escape(node.name)} '
        f'<span class="xref">{html.escape(node.ruleset or "both")}</span></div>'
        f"{path_html}{aliases}"
        "</div>\n"
    )


def _named_move_path(store: CuratedStore, node: EnrichmentNode) -> str:
    start = store.enrichment_node(node.start_id) if node.start_id else None
    end = store.enrichment_node(node.end_id) if node.end_id else None
    bits = []
    if start is not None:
        bits.append(start.name)
    if node.type_of_move:
        bits.append(node.type_of_move)
    if end is not None:
        bits.append(end.name)
    return " · ".join(bits)


def _author_panel(named_moves: tuple[EnrichmentNode, ...]) -> str:
    return (
        '<section class="panel" id="coach-authored">\n'
        "<h2>Coach-authored citation</h2>\n"
        '<form id="author" method="post" action="/place">\n'
        '<input type="hidden" name="action" value="author">\n'
        '<label for="author-movement">Movement name</label>\n'
        '<input id="author-movement" name="movement" type="text">\n'
        '<label for="author-steps">Step bullets</label>\n'
        '<textarea id="author-steps" name="step_bullets"></textarea>\n'
        '<label for="author-named-move">Named move</label>\n'
        f'<select id="author-named-move" name="named_move_id">{_named_move_options(named_moves, "")}</select>\n'
        '<button type="submit">Write</button>\n'
        "</form>\n"
        "</section>\n"
    )


def _named_moves(store: CuratedStore) -> tuple[EnrichmentNode, ...]:
    return tuple(
        sorted(
            (node for node in store.enrichment_nodes() if node.kind == "named move"),
            key=lambda node: node.name.casefold(),
        )
    )


def _named_move_options(named_moves: tuple[EnrichmentNode, ...], selected: str) -> str:
    empty = " selected" if not selected else ""
    options = [f'<option value=""{empty}>Uncategorized</option>']
    for node in named_moves:
        mark = " selected" if node.id == selected else ""
        options.append(
            f'<option value="{html.escape(node.id, quote=True)}"{mark}>'
            f"{html.escape(node.name)}</option>"
        )
    return "\n".join(options)


def _steps(bullets: tuple[str, ...]) -> str:
    if not bullets:
        return ""
    items = "".join(f"<li>{html.escape(bullet)}</li>" for bullet in bullets)
    return f'<ul class="steps">{items}</ul>\n'


def _field(fields: dict[str, list[str]], name: str) -> str:
    values = fields.get(name) or [""]
    return (values[0] if values else "").strip()


def _bullets(text: str) -> tuple[str, ...]:
    return tuple(line.strip() for line in text.splitlines() if line.strip())


add_screen(Screen("place", "/place", "Place", get=get_place, post=post_place))
