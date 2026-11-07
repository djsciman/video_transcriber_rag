"""Pack the Design map into a first Draft. Stand in the advisor."""

from __future__ import annotations

import inspect
from dataclasses import replace

from coach_app.briefing import BriefingAdvisor
from coach_app.build import BuildAdvisor, convert, propose
from coach_app.design import open_design, sample_tight_waist
from coach_app.store import Citation, CuratedStore, Lesson, Unit
from coach_app.topics import open_topic

from tests.test_design import _named, _tight_waist_catalog


TIGHT_WAIST_PARAGRAPH = (
    "Build a gi Tight waist unit where students win the underhook, "
    "make tight waist home, then branch the trilemma under rising partner jobs."
)


class ConflictingBuildAdvisor(BuildAdvisor):
    """Stand-in that flags two same-ruleset methods as a conflict."""

    def __init__(self, movements):
        self.movements = frozenset(movements)

    def disagreeing_sides(self, topic, citations):
        sides = tuple(
            citation
            for citation in citations
            if citation.movement in self.movements
        )
        if len(sides) < 2:
            return ()
        return sides


def _technique_names(store, packed_class):
    names = []
    for lesson in packed_class.lessons:
        if lesson.kind != "technique":
            continue
        node = store.enrichment_node(lesson.target)
        names.append(node.name if node is not None else lesson.target)
    return names


def _link(store, named_move, **fields) -> Citation:
    return store.put_citation(
        Citation(named_move_id=named_move.id, **fields)
    )


def test_propose_fills_canvas_and_draft_from_the_unit_paragraph():
    store = _tight_waist_catalog()
    session = open_design(topic_name="Tight waist", topic_ruleset="gi")

    result = propose(store, session, TIGHT_WAIST_PARAGRAPH, BuildAdvisor())

    named = {
        store.enrichment_node(mark.target).name
        for mark in result.session.marks
        if mark.kind == "named move"
    }
    systems = {
        store.enrichment_node(mark.target).name
        for mark in result.session.marks
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
    assert result.paragraph == TIGHT_WAIST_PARAGRAPH
    assert result.draft is not None
    assert result.draft.unit.paragraph == TIGHT_WAIST_PARAGRAPH
    assert result.draft.unit.topic_name == "Tight waist"
    assert result.draft.unit.topic_ruleset == "gi"
    assert store.unit(result.draft.unit.id) == result.draft.unit
    assert len(result.draft.classes) == 2
    assert all(packed.class_record in store.classes() for packed in result.draft.classes)
    assert all(
        lesson in store.lessons()
        for packed in result.draft.classes
        for lesson in packed.lessons
    )


def test_convert_packs_a_hand_built_canvas_and_refuses_an_empty_map():
    store = _tight_waist_catalog()
    empty = open_design(topic_name="Tight waist", topic_ruleset="gi")
    refused = convert(store, empty, BuildAdvisor())
    occupancy_marks = tuple(
        mark for mark in sample_tight_waist(store).marks if mark.kind == "occupancy"
    )
    occupancy_only = convert(
        store, replace(empty, marks=occupancy_marks), BuildAdvisor()
    )

    assert refused.draft is None
    assert refused.session.marks == ()
    assert occupancy_only.draft is None
    assert store.units() == ()
    assert store.classes() == ()
    assert store.lessons() == ()

    packed = convert(store, sample_tight_waist(store), BuildAdvisor())
    assert packed.draft is not None
    assert packed.paragraph == ""
    assert packed.session.marks == sample_tight_waist(store).marks
    assert len(packed.draft.classes) == 2
    assert store.unit(packed.draft.unit.id) == packed.draft.unit


def test_first_draft_is_glued_technique_plus_drill_with_class_cuts_and_partner_jobs():
    store = _tight_waist_catalog()
    result = convert(store, sample_tight_waist(store), BuildAdvisor())
    draft = result.draft

    assert draft is not None
    assert len(draft.classes) == 2
    for packed in draft.classes:
        lessons = packed.lessons
        assert lessons
        assert len(lessons) % 2 == 0
        for index in range(0, len(lessons), 2):
            technique = lessons[index]
            drill = lessons[index + 1]
            assert technique.kind == "technique"
            assert drill.kind == "drill"
            assert technique.target == drill.target
            assert drill.partner_job
            assert technique.partner_job == ""
    class1, class2 = draft.classes
    assert _technique_names(store, class1) == ["Knee lever", "Tight waist"]
    assert _technique_names(store, class2) == [
        "Tight waist trilemma",
        "Roll-through sweep",
    ]


def test_pinned_system_packs_as_one_glued_block_unless_a_member_is_isolated():
    store = _tight_waist_catalog()
    result = convert(store, sample_tight_waist(store), BuildAdvisor())
    names = [
        name
        for packed in result.draft.classes
        for name in _technique_names(store, packed)
    ]
    trilemma = next(
        node for node in store.enrichment_nodes() if node.name == "Tight waist trilemma"
    )
    roll = _named(store, "Roll-through sweep")
    far_leg = _named(store, "Far-leg come-up")
    back_take = _named(store, "Back take from tight waist")
    packed_targets = {
        lesson.target
        for packed in result.draft.classes
        for lesson in packed.lessons
    }

    assert names.count("Tight waist trilemma") == 1
    assert "Roll-through sweep" in names
    assert "Far-leg come-up" not in names
    assert "Back take from tight waist" not in names
    assert trilemma.id in packed_targets
    assert roll.id in packed_targets
    assert far_leg.id not in packed_targets
    assert back_take.id not in packed_targets
    system_block = result.draft.classes[1].lessons[0:2]
    assert system_block[0].kind == "technique"
    assert system_block[0].target == trilemma.id
    assert system_block[1].kind == "drill"
    assert system_block[1].target == trilemma.id


def test_citations_fall_back_to_the_first_linked_preferring_specific_named_move_cites():
    store = _tight_waist_catalog()
    roll = _named(store, "Roll-through sweep")
    far_leg = _named(store, "Far-leg come-up")
    trilemma_cite = _link(
        store,
        roll,
        movement="The Trilemma - Tight Waist Series",
        step_bullets=("hold tight waist as the home system",),
    )
    roll_cite = _link(
        store,
        roll,
        movement="Roll Through Sweeps - From tight waist",
        step_bullets=("roll them through toward the outside",),
    )
    far_cite = _link(
        store,
        far_leg,
        movement="Far-leg come-up from tight waist",
        step_bullets=("come up and capture their outside ankle",),
    )
    session = sample_tight_waist(store)
    chosen = _link(
        store,
        _named(store, "Knee lever"),
        movement="Chosen knee lever",
        step_bullets=("inside foot place next to their inside knee",),
    )
    session = replace(
        session,
        chosen_citations=(
            (_named(store, "Knee lever").id, chosen.id),
        ),
    )

    result = convert(store, session, BuildAdvisor())
    by_target = {
        lesson.target: lesson
        for packed in result.draft.classes
        for lesson in packed.lessons
        if lesson.kind == "technique"
    }
    trilemma = next(
        node for node in store.enrichment_nodes() if node.name == "Tight waist trilemma"
    )

    assert by_target[_named(store, "Knee lever").id].citations == (chosen.id,)
    assert by_target[roll.id].citations == (roll_cite.id,)
    assert trilemma_cite.id not in by_target[roll.id].citations
    assert by_target[trilemma.id].citations == (trilemma_cite.id,)
    assert far_cite.id not in by_target[trilemma.id].citations
    assert far_cite.id not in by_target[roll.id].citations


def test_other_side_of_disagreement_is_the_partner_job_stub():
    store = _tight_waist_catalog()
    tight = _named(store, "Tight waist")
    open_topic(store, "Tight waist", "gi")
    chosen = store.accept(
        {
            "movement": "Tight Waist Series - Winning from underhooks",
            "instructor": "John Danaher",
            "chapter": "Winning From Underhooks - The Tight Waist Series",
            "cleaned_statement": "inside arm wrap the tight waist around their waist",
            "step_bullets": ("inside arm wrap the tight waist around their waist",),
            "details": ({"speech_start": 460.91, "text": "wrap the tight waist"},),
        },
        instructional="Half Guard BJJ Fundamentals - Go Further Faster",
        video_file="Underhooks and Roll Through Sweep.mp4",
        ruleset="gi",
    )
    camp = store.accept(
        {
            "movement": "Never camp the tight waist from half guard",
            "instructor": "Lachlan Giles",
            "chapter": "Sit up instead of a tight waist",
            "cleaned_statement": "inside shoulder sit up to their inside shoulder",
            "step_bullets": (
                "inside shoulder sit up to their inside shoulder",
                "hips elevate instead of wrapping a tight waist",
            ),
            "details": ({"speech_start": 100.0, "text": "sit up"},),
        },
        instructional="Half Guard Anthology Gi",
        video_file="Half Guard Anthology Gi - Volume 1.mp4",
        ruleset="gi",
    )
    store.put_citation(replace(chosen, named_move_id=tight.id))
    store.put_citation(replace(camp, named_move_id=tight.id))
    advisor = ConflictingBuildAdvisor({chosen.movement, camp.movement})

    result = convert(store, sample_tight_waist(store), advisor)
    drill = next(
        lesson
        for packed in result.draft.classes
        for lesson in packed.lessons
        if lesson.kind == "drill" and lesson.target == tight.id
    )

    technique = next(
        lesson
        for packed in result.draft.classes
        for lesson in packed.lessons
        if lesson.kind == "technique" and lesson.target == tight.id
    )
    assert camp.step_bullets[0] in drill.partner_job
    assert chosen.id in technique.citations


def test_draft_is_a_no_edit_layout_b_proposal_without_playback_or_class_cap():
    store = _tight_waist_catalog()
    result = propose(
        store,
        open_design(topic_name="Tight waist", topic_ruleset="gi"),
        TIGHT_WAIST_PARAGRAPH,
        BuildAdvisor(),
    )
    draft = result.draft
    source = inspect.getsource(inspect.getmodule(propose))
    folded = source.casefold()

    assert result.paragraph == TIGHT_WAIST_PARAGRAPH
    assert result.session.marks
    assert draft.layout == "B"
    assert draft.editable is False
    assert draft.columns == ("Lesson", "Type", "Target", "What to run")
    assert "playback" not in {column.casefold() for column in draft.columns}
    assert "playback" not in folded
    assert "browser" not in folded
    assert "pdf" not in folded
    assert "openai" not in folded
    assert "anthropic" not in folded
    assert "prototypes" not in folded
    assert "max_classes" not in folded
    assert not hasattr(draft, "add_lesson")
    assert not hasattr(draft, "remove_lesson")
    assert list(inspect.signature(propose).parameters) == [
        "store",
        "session",
        "paragraph",
        "advisor",
    ]
    assert list(inspect.signature(convert).parameters) == [
        "store",
        "session",
        "advisor",
    ]
    advisor = BuildAdvisor()
    assert callable(advisor.design_from_paragraph)
    assert callable(advisor.isolate_member)
    assert isinstance(advisor, BriefingAdvisor) or callable(
        getattr(advisor, "disagreeing_sides", None)
    )
    assert store.units()
    assert isinstance(store.units()[0], Unit)
    assert all(isinstance(lesson, Lesson) for lesson in store.lessons())
