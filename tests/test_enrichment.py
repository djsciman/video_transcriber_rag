"""Live enrichment catalog: seed import, occupancy, browse, and coach edits."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from coach_app.store import Citation, CuratedStore, EnrichmentNode

_COMMITTED_SEED = (
    Path(__file__).resolve().parents[1] / "docs" / "enrichment-seed" / "seed.json"
)


def _seed_copy() -> dict:
    return copy.deepcopy(json.loads(_COMMITTED_SEED.read_text(encoding="utf-8")))


def _imported_store() -> CuratedStore:
    store = CuratedStore()
    store.import_enrichment_seed(_seed_copy())
    return store


def _nodes_of(store: CuratedStore, kind: str) -> tuple[EnrichmentNode, ...]:
    return tuple(node for node in store.enrichment_nodes() if node.kind == kind)


def _named(store: CuratedStore, name: str) -> EnrichmentNode:
    matches = [node for node in _nodes_of(store, "named move") if node.name == name]
    assert len(matches) == 1, name
    return matches[0]


def test_import_unifies_one_position_identity_and_keeps_submissions_end_only():
    store = _imported_store()
    positions = _nodes_of(store, "position")
    submissions = _nodes_of(store, "submission")
    named_moves = _nodes_of(store, "named move")
    types = _nodes_of(store, "type of move")

    assert len(positions) == 36
    assert len(submissions) == 26
    assert len(named_moves) == 149
    assert len(types) == 7
    assert len([node for node in positions if node.id == "mount"]) == 1
    assert len([node for node in positions if node.name == "Mount"]) == 1

    loop = next(node for node in submissions if node.name == "Loop choke")
    assert loop.kind == "submission"
    starts = store.browse_hierarchy()
    assert all(node.kind == "position" for node in starts)
    assert "Loop choke" not in {node.name for node in starts}
    assert all(move.start_id != loop.id for move in named_moves)

    z_guard = next(node for node in positions if node.name == "Z-guard")
    assert z_guard.id == "z-guard"
    assert z_guard.family == "guard"


def test_named_move_occupancy_is_inferred_from_type_and_landing():
    store = _imported_store()

    knee = _named(store, "Knee slice pass")
    assert knee.start_id == "half-guard"
    assert knee.type_of_move == "pass"
    assert knee.end_id == "side-control"
    assert knee.start_occupancy == "top"
    assert knee.end_occupancy == "top"
    assert knee.ruleset == "both"

    old_school = _named(store, "Old school sweep")
    assert old_school.start_id == "half-guard"
    assert old_school.type_of_move == "sweep"
    assert old_school.start_occupancy == "bottom"
    assert old_school.end_occupancy == "top"

    hip_bump = _named(store, "Hip bump sweep")
    mount = next(node for node in _nodes_of(store, "position") if node.name == "Mount")
    assert hip_bump.end_id == mount.id
    assert hip_bump.start_occupancy == "bottom"
    assert hip_bump.end_occupancy == "top"
    assert any(move.start_id == mount.id for move in _nodes_of(store, "named move"))

    double_leg = _named(store, "Double leg takedown")
    assert double_leg.start_occupancy == "neutral"
    assert double_leg.end_occupancy == "top"

    chair_sit = _named(store, "Chair sit escape")
    assert chair_sit.start_occupancy == "bottom"
    assert chair_sit.end_occupancy == "bottom"

    deep_half = _named(store, "Deep half entry")
    assert deep_half.type_of_move == "transition"
    assert deep_half.start_occupancy == "bottom"
    assert deep_half.end_occupancy == "bottom"

    armbar = _named(store, "Armbar from closed guard")
    assert armbar.end_id == "armbar"
    assert armbar.start_occupancy == "bottom"
    assert armbar.end_occupancy == ""

    bow = _named(store, "Bow and arrow choke")
    assert bow.ruleset == "gi"


def test_search_finds_judo_cross_ref_on_the_bjj_named_move():
    store = _imported_store()
    hits = store.search_enrichment("Morote-gari")
    assert any(node.name == "Double leg takedown" for node in hits)
    double_leg = _named(store, "Double leg takedown")
    assert "Morote-gari" in double_leg.cross_refs


def test_hierarchy_browse_walks_start_then_type_then_end_or_submission():
    store = _imported_store()
    starts = store.browse_hierarchy()
    assert any(node.name == "Half guard" and node.id == "half-guard" for node in starts)

    types = store.browse_hierarchy(start="half-guard")
    assert {node.kind for node in types} == {"type of move"}
    assert {node.name for node in types} >= {"Pass", "Sweep", "Transition", "Back take"}

    ends = store.browse_hierarchy(start="half-guard", type_of_move="pass")
    assert any(node.name == "Side control" and node.kind == "position" for node in ends)
    assert all(node.kind in {"position", "submission"} for node in ends)

    submissions = store.browse_hierarchy(start="closed-guard", type_of_move="submission")
    assert any(node.name == "Armbar" and node.kind == "submission" for node in submissions)


def test_import_is_one_time_and_corpus_does_not_rewrite_the_tree():
    store = _imported_store()
    added = store.put_enrichment_node(
        EnrichmentNode(kind="position", name="Coach position", family="guard")
    )
    count = len(store.enrichment_nodes())
    store.put_citation(Citation(movement="Knee cut from a raw volume"))
    store.import_enrichment_seed(_seed_copy())
    assert len(store.enrichment_nodes()) == count
    assert store.enrichment_node(added.id) == added
    assert len(_nodes_of(store, "position")) == 37


def test_coach_add_infers_occupancy_on_the_live_copy():
    store = _imported_store()
    start = store.put_enrichment_node(
        EnrichmentNode(kind="position", name="Worm half", family="guard")
    )
    move = store.put_enrichment_node(
        EnrichmentNode(
            kind="named move",
            name="Coach worm sweep",
            start_id=start.id,
            type_of_move="sweep",
            end_id="mount",
            ruleset="no-gi",
        )
    )
    assert move.start_occupancy == "bottom"
    assert move.end_occupancy == "top"
    assert move.ruleset == "no-gi"
    assert store.enrichment_node(move.id) == move


def test_rename_and_move_keep_citation_links():
    store = _imported_store()
    half = next(node for node in _nodes_of(store, "position") if node.name == "Half guard")
    knee = _named(store, "Knee slice pass")
    citation = store.put_citation(
        Citation(movement="Knee cut", named_move_id=knee.id)
    )

    renamed = store.rename_enrichment_node(half.id, "Half-guard")
    assert renamed.id == half.id
    assert store.enrichment_node(half.id).name == "Half-guard"
    assert store.citation(citation.id).named_move_id == knee.id
    assert store.enrichment_node(knee.id).start_id == half.id

    store.rename_enrichment_node(knee.id, "Knee cut pass")
    assert store.enrichment_node(knee.id).name == "Knee cut pass"
    assert store.citation(citation.id).named_move_id == knee.id

    moved = store.move_enrichment_node(
        knee.id,
        start_id="mount",
        type_of_move="pass",
        end_id="side-control",
    )
    assert moved.id == knee.id
    assert moved.start_id == "mount"
    assert moved.type_of_move == "pass"
    assert moved.end_id == "side-control"
    assert moved.start_occupancy == "top"
    assert moved.end_occupancy == "top"
    assert store.citation(citation.id).named_move_id == knee.id


def test_delete_uncategorizes_citations():
    store = _imported_store()
    knee = _named(store, "Knee slice pass")
    old_school = _named(store, "Old school sweep")
    knee_citation = store.put_citation(
        Citation(movement="Knee cut", named_move_id=knee.id)
    )
    sweep_citation = store.put_citation(
        Citation(movement="Old school", named_move_id=old_school.id)
    )

    store.delete_enrichment_node(knee.id)
    assert store.enrichment_node(knee.id) is None
    assert store.citation(knee_citation.id).named_move_id == ""
    assert store.citation(sweep_citation.id).named_move_id == old_school.id

    half = next(node for node in _nodes_of(store, "position") if node.name == "Half guard")
    store.delete_enrichment_node(half.id)
    assert store.enrichment_node(half.id) is None
    assert store.enrichment_node(old_school.id) is None
    assert store.citation(sweep_citation.id).named_move_id == ""
