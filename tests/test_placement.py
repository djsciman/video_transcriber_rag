"""Citations belong to named moves. Uncategorized stays off lessons and Design marks."""

from __future__ import annotations

import inspect

from coach_app.placement import (
    PlacementAdvisor,
    PlacementDecision,
    apply_placement_decisions,
    citations_for_design_mark,
    citations_for_lesson,
    enter_citations,
    propose_placement_pass,
    put_catalog_system,
    validate_lesson_connection,
    write_coach_authored_citation,
)
from coach_app.store import Citation, CuratedStore, EnrichmentNode


class MappingAdvisor:
    """Stand-in that maps movement names to named-move ids. Does not name a vendor."""

    def __init__(self, mapping):
        self.mapping = mapping
        self.calls = []

    def propose(self, citation, named_moves):
        self.calls.append(citation.id)
        return self.mapping.get(citation.movement, "")


def _named_move(store, name):
    return store.put_enrichment_node(EnrichmentNode(kind="named move", name=name))


def test_uncategorized_citations_are_withheld_from_lessons_and_design_marks():
    store = CuratedStore()
    hip = _named_move(store, "Hip bump sweep")
    linked = store.put_citation(
        Citation(movement="Hip bump sweep", named_move_id=hip.id)
    )
    store.put_citation(Citation(movement="Unplaced hip bump"))

    offered_on_lesson = citations_for_lesson(store, hip.id)
    offered_on_mark = citations_for_design_mark(store, hip.id)

    assert offered_on_lesson == (linked,)
    assert offered_on_mark == (linked,)
    assert all(item.named_move_id == hip.id for item in offered_on_lesson)
    assert any(not item.named_move_id for item in store.citations())
    assert citations_for_design_mark(store, "") == ()


def test_lesson_on_a_system_offers_the_union_of_member_citations():
    store = CuratedStore()
    hip = _named_move(store, "Hip bump sweep")
    kimura = _named_move(store, "Kimura from closed guard")
    triangle = _named_move(store, "Triangle from closed guard")
    system = put_catalog_system(
        store,
        "Closed guard trilemma",
        (hip.id, kimura.id, triangle.id),
    )
    hip_cite = store.put_citation(
        Citation(movement="Hip bump", named_move_id=hip.id)
    )
    kimura_cite = store.put_citation(
        Citation(movement="Kimura", named_move_id=kimura.id)
    )
    store.put_citation(Citation(movement="Loose hip bump"))

    offered = citations_for_lesson(store, system.id)

    assert offered == (hip_cite, kimura_cite)
    assert triangle.id not in {item.named_move_id for item in offered}


def test_lesson_connects_to_exactly_one_named_move_or_exactly_one_system():
    validate_lesson_connection(named_move_id="hip-bump")
    validate_lesson_connection(system_id="closed-guard-trilemma")
    try:
        validate_lesson_connection()
    except ValueError as error:
        assert "named move" in str(error)
        assert "system" in str(error)
    else:
        raise AssertionError("expected xor failure when neither target is set")
    try:
        validate_lesson_connection(
            named_move_id="hip-bump",
            system_id="closed-guard-trilemma",
        )
    except ValueError as error:
        assert "exactly one" in str(error)
    else:
        raise AssertionError("expected xor failure when both targets are set")
    try:
        citations_for_lesson(CuratedStore(), "")
    except ValueError as error:
        assert "exactly one" in str(error)
    else:
        raise AssertionError("expected an empty lesson target to fail xor")


def test_new_citations_get_one_proposed_placement_pass():
    store = CuratedStore()
    hip = _named_move(store, "Hip bump sweep")
    older = store.put_citation(Citation(movement="Older leftover"))
    advisor = MappingAdvisor({"Hip bump sweep": hip.id})

    stored, proposals = enter_citations(
        store,
        (Citation(movement="Hip bump sweep"), Citation(movement="Unknown sit-up")),
        advisor,
    )

    assert [item.citation_id for item in proposals] == [item.id for item in stored]
    assert proposals[0].named_move_id == hip.id
    assert proposals[1].named_move_id == ""
    assert older.id not in {item.citation_id for item in proposals}
    assert advisor.calls == [item.id for item in stored]
    assert all(not item.named_move_id for item in stored)


def test_coach_accepts_corrects_or_skips_in_one_list_and_can_repeat_later():
    store = CuratedStore()
    hip = _named_move(store, "Hip bump sweep")
    kimura = _named_move(store, "Kimura from closed guard")
    advisor = MappingAdvisor(
        {
            "Hip bump sweep": hip.id,
            "Kimura from closed guard": hip.id,
            "Triangle from closed guard": kimura.id,
        }
    )
    stored, proposals = enter_citations(
        store,
        (
            Citation(movement="Hip bump sweep"),
            Citation(movement="Kimura from closed guard"),
            Citation(movement="Triangle from closed guard"),
        ),
        advisor,
    )
    hip_cite, kimura_cite, triangle_cite = stored

    apply_placement_decisions(
        store,
        (
            PlacementDecision(
                citation_id=proposals[0].citation_id,
                action="accept",
                named_move_id=proposals[0].named_move_id,
            ),
            PlacementDecision(
                citation_id=proposals[1].citation_id,
                action="correct",
                named_move_id=kimura.id,
            ),
            PlacementDecision(citation_id=proposals[2].citation_id, action="skip"),
        ),
    )

    assert store.citation(hip_cite.id).named_move_id == hip.id
    assert store.citation(kimura_cite.id).named_move_id == kimura.id
    assert store.citation(triangle_cite.id).named_move_id == ""
    assert citations_for_lesson(store, hip.id) == (store.citation(hip_cite.id),)
    assert citations_for_design_mark(store, kimura.id) == (
        store.citation(kimura_cite.id),
    )
    assert citations_for_design_mark(store, hip.id) == (store.citation(hip_cite.id),)

    later = propose_placement_pass(store, advisor)
    assert [item.citation_id for item in later] == [triangle_cite.id]
    apply_placement_decisions(
        store,
        (
            PlacementDecision(
                citation_id=triangle_cite.id,
                action="correct",
                named_move_id=kimura.id,
            ),
        ),
    )
    assert store.citation(triangle_cite.id).named_move_id == kimura.id
    assert propose_placement_pass(store, advisor) == ()


def test_coach_authored_citation_has_no_playback_and_can_belong_to_a_named_move():
    store = CuratedStore()
    hip = _named_move(store, "Hip bump sweep")

    placed = write_coach_authored_citation(
        store,
        movement="Hip bump sweep",
        step_bullets=("Sit up", "Post the base hand", "Bump and roll"),
        named_move_id=hip.id,
    )
    loose = write_coach_authored_citation(
        store,
        movement="House sit-up",
        step_bullets=("Post and bump",),
    )

    assert placed.movement == "Hip bump sweep"
    assert placed.step_bullets == ("Sit up", "Post the base hand", "Bump and roll")
    assert placed.instructional is None
    assert placed.volume is None
    assert placed.chapter is None
    assert placed.showings == ()
    assert placed.named_move_id == hip.id
    assert store.citation(placed.id) == placed
    assert all(showing.playback_link is None for showing in placed.showings)
    assert citations_for_lesson(store, hip.id) == (placed,)
    assert citations_for_design_mark(store, hip.id) == (placed,)
    assert loose.named_move_id == ""
    assert loose not in citations_for_lesson(store, hip.id)
    assert loose not in citations_for_design_mark(store, hip.id)


def test_placement_stand_in_does_not_name_a_vendor_or_open_a_browser():
    source = inspect.getsource(__import__("coach_app.placement", fromlist=["*"]))
    folded = source.casefold()
    assert "openai" not in folded
    assert "anthropic" not in folded
    assert "browser" not in folded
    advisor = PlacementAdvisor()
    assert callable(advisor.propose)
