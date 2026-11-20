"""Design a unit as an unordered mental map. Uncategorized stays off marks."""

from __future__ import annotations

import copy
import inspect
import json
from pathlib import Path

from coach_app.design import (
    ADD_WALK,
    add_system,
    choose_citation,
    citations_on_mark,
    delete_mark,
    edit_mark,
    ends_at,
    named_moves_at,
    occupancies_at,
    open_design,
    pick,
    sample_tight_waist,
    types_at,
    walk_options,
    walk_step,
)
from coach_app.placement import citations_for_design_mark, put_catalog_system
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


def _named(store: CuratedStore, name: str) -> EnrichmentNode:
    matches = [
        node
        for node in store.enrichment_nodes()
        if node.kind == "named move" and node.name == name
    ]
    assert len(matches) == 1, name
    return matches[0]


def _tight_waist_catalog() -> CuratedStore:
    store = CuratedStore()
    store.put_enrichment_node(
        EnrichmentNode(kind="position", name="Half guard", id="half-guard", family="guard")
    )
    store.put_enrichment_node(
        EnrichmentNode(
            kind="position", name="Side control", id="side-control", family="pin"
        )
    )
    store.put_enrichment_node(
        EnrichmentNode(
            kind="position", name="Back control", id="back-control", family="back"
        )
    )
    store.put_enrichment_node(
        EnrichmentNode(kind="position", name="Closed guard", id="closed-guard", family="guard")
    )
    store.put_enrichment_node(
        EnrichmentNode(kind="position", name="Standing", id="standing", family="standing")
    )
    for type_id, label in (
        ("transition", "Transition"),
        ("sweep", "Sweep"),
        ("pass", "Pass"),
        ("escape", "Escape"),
        ("takedown", "Takedown"),
        ("submission", "Submission"),
        ("back-take", "Back take"),
    ):
        store.put_enrichment_node(
            EnrichmentNode(kind="type of move", name=label, id=type_id)
        )
    store.put_enrichment_node(
        EnrichmentNode(kind="submission", name="Armbar", id="armbar")
    )

    def named_move(name, type_of_move, end_id, start_id="half-guard"):
        return store.put_enrichment_node(
            EnrichmentNode(
                kind="named move",
                name=name,
                start_id=start_id,
                type_of_move=type_of_move,
                end_id=end_id,
            )
        )

    named_move("Knee lever", "transition", "half-guard")
    named_move("Tight waist", "transition", "half-guard")
    named_move("Far-leg come-up", "sweep", "side-control")
    named_move("Roll-through sweep", "sweep", "side-control")
    named_move("Back take from tight waist", "back-take", "back-control")
    named_move("Old school sweep", "sweep", "side-control")
    named_move("Knee slice pass", "pass", "side-control")
    named_move("Armbar from closed guard", "submission", "armbar", start_id="closed-guard")
    put_catalog_system(
        store,
        "Tight waist trilemma",
        (
            _named(store, "Far-leg come-up").id,
            _named(store, "Roll-through sweep").id,
            _named(store, "Back take from tight waist").id,
        ),
    )
    return store


def _mark_keys(session):
    return {(mark.kind, mark.target) for mark in session.marks}


def test_add_walk_replaces_the_type_mark_with_the_named_move():
    store = _tight_waist_catalog()
    session = open_design(topic_name="Tight waist", topic_ruleset="gi")
    old_school = _named(store, "Old school sweep")

    assert ADD_WALK == (
        "family",
        "position",
        "occupancy",
        "type",
        "end",
        "named move",
    )
    assert walk_step(session) == "family"
    assert "guard" in walk_options(store, session)

    session = pick(store, session, "guard")
    assert walk_step(session) == "position"
    assert "half-guard" in walk_options(store, session)

    session = pick(store, session, "half-guard")
    assert walk_step(session) == "occupancy"
    assert walk_options(store, session) == occupancies_at(store, "half-guard")

    session = pick(store, session, "bottom")
    assert walk_step(session) == "type"
    assert ("occupancy", "bottom") in _mark_keys(session)
    assert "sweep" in walk_options(store, session)
    assert "escape" not in walk_options(store, session)

    session = pick(store, session, "sweep")
    assert walk_step(session) == "end"
    assert ("type", "sweep") in _mark_keys(session)
    assert "side-control" in walk_options(store, session)

    session = pick(store, session, "side-control")
    assert walk_step(session) == "named move"
    assert old_school.id in walk_options(store, session)

    session = pick(store, session, old_school.id)
    keys = _mark_keys(session)
    assert ("type", "sweep") not in keys
    assert ("named move", old_school.id) in keys
    assert ("occupancy", "bottom") in keys
    assert walk_step(session) == "family"


def test_submission_skips_end_and_stays_end_only():
    store = _tight_waist_catalog()
    armbar = _named(store, "Armbar from closed guard")
    session = open_design()
    session = pick(store, session, "guard")
    session = pick(store, session, "closed-guard")
    session = pick(store, session, "bottom")
    session = pick(store, session, "submission")

    assert walk_step(session) == "named move"
    assert armbar.id in walk_options(store, session)
    assert armbar.end_occupancy == ""
    assert "closed-guard" not in ends_at(store, "closed-guard", "bottom", "submission")

    session = pick(store, session, armbar.id)
    assert ("named move", armbar.id) in _mark_keys(session)
    assert ("type", "submission") not in _mark_keys(session)


def test_occupancy_filters_match_locked_sides_and_landing():
    store = _imported_store()

    assert occupancies_at(store, "half-guard") == ("bottom", "top")
    assert occupancies_at(store, "closed-guard") == ("bottom", "top")
    assert occupancies_at(store, "standing") == ("neutral",)
    assert occupancies_at(store, "side-control") == ("bottom", "top")

    half_bottom = types_at(store, "half-guard", "bottom")
    half_top = types_at(store, "half-guard", "top")
    closed_bottom = types_at(store, "closed-guard", "bottom")
    standing_neutral = types_at(store, "standing", "neutral")
    pin_bottom = types_at(store, "side-control", "bottom")

    assert "escape" not in closed_bottom
    assert "escape" not in half_bottom
    assert "escape" in pin_bottom
    assert "pass" in half_top
    assert "pass" not in half_bottom
    assert "sweep" in half_bottom
    assert "sweep" not in half_top
    assert "takedown" in standing_neutral
    assert "takedown" not in half_bottom
    assert "takedown" not in closed_bottom
    assert "transition" in half_bottom
    assert "transition" not in half_top

    knee = _named(store, "Knee slice pass")
    old_school = _named(store, "Old school sweep")
    deep_half = _named(store, "Deep half entry")
    assert knee.start_occupancy == "top"
    assert knee.end_occupancy == "top"
    assert old_school.start_occupancy == "bottom"
    assert old_school.end_occupancy == "top"
    assert knee.id in named_moves_at(store, "half-guard", "top", "pass")
    assert knee.id not in named_moves_at(store, "half-guard", "bottom")
    assert old_school.id in named_moves_at(store, "half-guard", "bottom", "sweep")
    assert old_school.id not in named_moves_at(store, "half-guard", "top")

    transition_ends = ends_at(store, "half-guard", "bottom", "transition")
    assert "deep-half-guard" in transition_ends
    assert "side-control" not in transition_ends
    assert deep_half.end_occupancy == "bottom"
    assert deep_half.id in named_moves_at(
        store, "half-guard", "bottom", "transition", "deep-half-guard"
    )


def test_left_click_edits_and_right_click_deletes():
    store = _tight_waist_catalog()
    session = sample_tight_waist(store)
    named = next(mark for mark in session.marks if mark.kind == "named move")

    edited = edit_mark(session, named.id)
    assert edited.selected_id == named.id
    assert _mark_keys(edited) == _mark_keys(session)

    deleted = delete_mark(edited, named.id)
    assert named.id not in {mark.id for mark in deleted.marks}
    assert ("named move", named.target) not in _mark_keys(deleted)
    assert deleted.selected_id != named.id


def test_named_move_mark_withholds_uncategorized_citations():
    store = _tight_waist_catalog()
    tight_waist = _named(store, "Tight waist")
    linked = store.put_citation(
        Citation(movement="Tight waist", named_move_id=tight_waist.id)
    )
    store.put_citation(Citation(movement="Uncategorized tight waist"))
    session = sample_tight_waist(store)
    mark = next(
        item
        for item in session.marks
        if item.kind == "named move" and item.target == tight_waist.id
    )

    session = edit_mark(session, mark.id)
    offered = citations_on_mark(store, session, mark.id)
    assert offered == (linked,)
    assert offered == citations_for_design_mark(store, tight_waist.id)
    assert all(item.named_move_id == tight_waist.id for item in offered)

    refused = choose_citation(store, session, mark.id, "missing")
    assert refused.chosen_citations == session.chosen_citations

    chosen = choose_citation(store, session, mark.id, linked.id)
    assert (tight_waist.id, linked.id) in chosen.chosen_citations
    uncategorized = next(
        item for item in store.citations() if not item.named_move_id
    )
    still = choose_citation(store, chosen, mark.id, uncategorized.id)
    assert (tight_waist.id, uncategorized.id) not in still.chosen_citations


def test_tight_waist_sample_is_unordered_and_does_not_pack():
    store = _tight_waist_catalog()
    session = sample_tight_waist(store)
    named = {
        store.enrichment_node(mark.target).name
        for mark in session.marks
        if mark.kind == "named move"
    }
    systems = {
        store.enrichment_node(mark.target).name
        for mark in session.marks
        if mark.kind == "system"
    }
    assert named >= {
        "Knee lever",
        "Tight waist",
        "Far-leg come-up",
        "Roll-through sweep",
        "Back take from tight waist",
    }
    assert "Tight waist trilemma" in systems
    assert session.topic_name == "Tight waist"
    assert session.topic_ruleset == "gi"
    assert not hasattr(session, "classes")
    assert not hasattr(session, "lessons")
    assert store.classes() == ()
    assert store.lessons() == ()

    trilemma = next(node for node in store.enrichment_nodes() if node.kind == "system")
    pinned = add_system(store, open_design(), trilemma.id)
    assert ("system", trilemma.id) in _mark_keys(pinned)
    assert {mark.target for mark in pinned.marks if mark.kind == "named move"} == set(
        trilemma.members
    )


def test_dropping_a_member_drops_only_that_system():
    store = _tight_waist_catalog()
    session = sample_tight_waist(store)
    roll = _named(store, "Roll-through sweep")
    knee = _named(store, "Knee lever")
    trilemma = next(node for node in store.enrichment_nodes() if node.kind == "system")
    roll_mark = next(
        mark
        for mark in session.marks
        if mark.kind == "named move" and mark.target == roll.id
    )

    deleted = delete_mark(session, roll_mark.id)
    remaining = {
        store.enrichment_node(mark.target).name
        for mark in deleted.marks
        if mark.kind == "named move"
    }
    systems = {mark.target for mark in deleted.marks if mark.kind == "system"}

    assert roll.name not in remaining
    assert knee.name in remaining
    assert "Tight waist" in remaining
    assert trilemma.id not in systems
    assert ("named move", knee.id) in _mark_keys(deleted)


def test_design_does_not_organize_the_catalog_or_pack_classes():
    source = inspect.getsource(__import__("coach_app.design", fromlist=["*"]))
    folded = source.casefold()
    assert "put_class" not in folded
    assert "put_lesson" not in folded
    assert "put_enrichment_node" not in folded
    assert "rename_enrichment" not in folded
    assert "delete_enrichment" not in folded
    assert "import_enrichment_seed" not in folded
    assert "prototypes" not in folded
    assert "browser" not in folded
    session = open_design()
    assert session.marks == ()
    assert walk_step(session) == "family"
