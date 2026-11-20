"""Place citations on named moves. Catalog organize stays on the finder."""

from __future__ import annotations

from dataclasses import dataclass, replace

from coach_app.store import (
    Citation,
    EnrichmentNode,
    system_members,
    validate_lesson_connection,
)


@dataclass(frozen=True)
class PlacementProposal:
    citation_id: str
    named_move_id: str = ""


@dataclass(frozen=True)
class PlacementDecision:
    citation_id: str
    action: str
    named_move_id: str = ""


class PlacementAdvisor:
    """Stand-in that matches a citation movement to a named move. Does not name a vendor."""

    def propose(self, citation, named_moves) -> str:
        needle = (citation.movement or "").strip().casefold()
        if not needle:
            return ""
        for node in named_moves:
            names = (node.name, *node.aliases, *node.cross_refs)
            if needle in {name.casefold() for name in names if name}:
                return node.id
        return ""


def citations_for_lesson(store, lesson_target):
    target = str(lesson_target or "").strip()
    if not target:
        validate_lesson_connection()
    wanted = set(_named_move_ids_for(store, target))
    wanted.discard("")
    return tuple(
        citation
        for citation in store.citations()
        if citation.named_move_id and citation.named_move_id in wanted
    )


def citations_for_design_mark(store, named_move_id):
    target = str(named_move_id or "").strip()
    if not target:
        return ()
    return tuple(
        citation
        for citation in store.citations()
        if citation.named_move_id == target
    )


def put_catalog_system(store, name, named_move_ids):
    members = tuple(named_move_ids)
    if len(members) < 2:
        raise ValueError("A catalog system is two or more named moves.")
    return store.put_enrichment_node(
        EnrichmentNode(kind="system", name=name, members=members)
    )


def write_coach_authored_citation(
    store,
    *,
    movement: str,
    step_bullets,
    named_move_id: str = "",
):
    return store.put_citation(
        Citation(
            movement=movement,
            step_bullets=tuple(step_bullets),
            named_move_id=named_move_id,
        )
    )


def enter_citations(store, citations, advisor):
    stored = tuple(store.put_citation(citation) for citation in citations)
    return stored, propose_placement_pass(store, advisor, citations=stored)


def propose_placement_pass(store, advisor, citations=None):
    named_moves = tuple(
        node for node in store.enrichment_nodes() if node.kind == "named move"
    )
    if citations is None:
        pool = [citation for citation in store.citations() if not citation.named_move_id]
    else:
        pool = [citation for citation in citations if not citation.named_move_id]
    return tuple(
        PlacementProposal(
            citation_id=citation.id,
            named_move_id=advisor.propose(citation, named_moves) or "",
        )
        for citation in pool
    )


def apply_placement_decisions(store, decisions):
    updated = []
    for decision in decisions:
        citation = store.citation(decision.citation_id)
        if citation is None:
            continue
        if decision.action == "skip":
            updated.append(citation)
            continue
        if decision.action not in {"accept", "correct"}:
            raise ValueError("Unknown placement action.")
        named_move_id = decision.named_move_id or ""
        if decision.action == "accept" and not named_move_id:
            updated.append(citation)
            continue
        written = store.put_citation(replace(citation, named_move_id=named_move_id))
        updated.append(written)
    return tuple(updated)


def _named_move_ids_for(store, lesson_target: str) -> tuple[str, ...]:
    node = store.enrichment_node(lesson_target)
    if node is not None and node.kind == "system":
        return system_members(node)
    return (lesson_target,)
