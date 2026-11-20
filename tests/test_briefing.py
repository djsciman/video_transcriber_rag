"""Return a briefing memo from store citations. Stand in the advisor."""

from __future__ import annotations

import inspect

from coach_app.briefing import BriefingAdvisor, brief_topic
from coach_app.store import Citation, CuratedStore
from coach_app.topics import open_topic, welcome_other_ruleset


class ConflictingAdvisor(BriefingAdvisor):
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


def _accept(
    store: CuratedStore,
    *,
    movement: str,
    instructor: str,
    instructional: str,
    video_file: str,
    chapter: str,
    cleaned_statement: str,
    step_bullets: tuple[str, ...],
    speech_start: float,
    ruleset: str,
) -> Citation:
    return store.accept(
        {
            "movement": movement,
            "instructor": instructor,
            "chapter": chapter,
            "cleaned_statement": cleaned_statement,
            "step_bullets": step_bullets,
            "details": ({"speech_start": speech_start, "text": cleaned_statement},),
        },
        instructional=instructional,
        video_file=video_file,
        ruleset=ruleset,
    )


def _knee_lever_bullets():
    return (
        "inside foot place next to their inside knee",
        "inside arm shoots the underhook under their inside arm",
        "outside arm blocks their outside arm from the crossface",
    )


def _tight_waist_bullets():
    return (
        "inside arm wrap the tight waist around their waist",
        "outside arm block their outside arm",
        "body get off the flat back onto the outside hip from half guard",
    )


def _giles_underhook_bullets():
    return (
        "torso sit up until your inside shoulder meets their inside shoulder",
        "inside arm do not reach from flat under their inside armpit",
        "hips bump forward and scoot down around the corner toward the outside",
    )


def _half_guard_fixtures(store: CuratedStore, *, welcome_giles: bool = True):
    danaher_underhook = _accept(
        store,
        movement="Knee Lever - Get the underhook from half guard bottom",
        instructor="John Danaher",
        instructional="Half Guard BJJ Fundamentals - Go Further Faster",
        video_file=(
            "Half Guard BJJ Fundamentals - Go Further Faster by John Danaher "
            "- S01E04 - Underhooks and Roll Through Sweep.mp4"
        ),
        chapter="Getting to Underhooks",
        cleaned_statement=" ".join(_knee_lever_bullets()),
        step_bullets=_knee_lever_bullets(),
        speech_start=5.26,
        ruleset="gi",
    )
    danaher_tight_waist = _accept(
        store,
        movement="Tight Waist Series - Winning from underhooks",
        instructor="John Danaher",
        instructional="Half Guard BJJ Fundamentals - Go Further Faster",
        video_file=(
            "Half Guard BJJ Fundamentals - Go Further Faster by John Danaher "
            "- S01E04 - Underhooks and Roll Through Sweep.mp4"
        ),
        chapter="Winning From Underhooks - The Tight Waist Series",
        cleaned_statement=" ".join(_tight_waist_bullets()),
        step_bullets=_tight_waist_bullets(),
        speech_start=460.91,
        ruleset="gi",
    )
    giles = _accept(
        store,
        movement="Underhook Switch - Getting the underhook",
        instructor="Lachlan Giles",
        instructional="Half Guard Anthology",
        video_file="Half Guard Anthology by Lachlan Giles - S01E03 - Volume 3.mp4",
        chapter="ATTACKS: GETTING THE UNDERHOOK",
        cleaned_statement=(
            "From half guard, sit up until the inside shoulders meet "
            "and secure the underhook."
        ),
        step_bullets=_giles_underhook_bullets(),
        speech_start=516.56,
        ruleset="no-gi",
    )
    knee_cut = _accept(
        store,
        movement="Knee cut",
        instructor="John Danaher",
        instructional="Half Guard Passing and Dynamic Pins",
        video_file="Half Guard Passing and Dynamic Pins - Volume 1.mp4",
        chapter="The knee cut",
        cleaned_statement="Frame the far hip and cut the knee to mount.",
        step_bullets=("Frame the far hip.", "Cut the knee to mount."),
        speech_start=12.5,
        ruleset="gi",
    )
    topic = open_topic(store, "half guard", "gi")
    if welcome_giles:
        welcome_other_ruleset(store, topic, "Half Guard Anthology", True)
    return topic, danaher_underhook, danaher_tight_waist, giles, knee_cut


def test_memo_names_open_topic_and_same_ruleset_citations():
    store = CuratedStore()
    topic, underhook, tight_waist, _giles, knee_cut = _half_guard_fixtures(store)

    memo = brief_topic(store, "half guard", "gi", BriefingAdvisor())

    assert memo.topic_name == topic.name == "half guard"
    assert memo.topic_ruleset == topic.ruleset == "gi"
    movements = {citation.movement for citation in memo.same_ruleset_citations}
    assert underhook.movement in movements
    assert tight_waist.movement in movements
    assert knee_cut.movement not in movements
    shown = next(
        citation
        for citation in memo.same_ruleset_citations
        if citation.movement == underhook.movement
    )
    assert shown.instructor == "John Danaher"
    assert shown.instructional == (
        "Half Guard BJJ Fundamentals - Go Further Faster"
    )
    assert shown.volume == underhook.volume
    assert shown.chapter == "Getting to Underhooks"
    assert shown.step_bullets == _knee_lever_bullets()
    assert shown.showings[0].playback_link
    assert shown.showings[0].playback_link.endswith("@5.26")


def test_step_bullets_name_body_parts_and_inside_outside():
    store = CuratedStore()
    _half_guard_fixtures(store)

    memo = brief_topic(store, "half guard", "gi", BriefingAdvisor())

    bullets = " ".join(
        bullet
        for citation in memo.same_ruleset_citations
        for bullet in citation.step_bullets
    )
    assert "inside arm" in bullets
    assert "shoots" in bullets or "wrap" in bullets
    assert "their inside arm" in bullets or "their waist" in bullets
    assert "outside arm" in bullets
    assert "their outside arm" in bullets


def test_other_ruleset_asks_why_paths_differ_and_does_not_pick_a_winner():
    store = CuratedStore()
    _topic, _underhook, _tight_waist, giles, _knee_cut = _half_guard_fixtures(
        store
    )

    memo = brief_topic(store, "half guard", "gi", BriefingAdvisor())

    assert giles in memo.other_ruleset_citations
    question = memo.other_ruleset_question.casefold()
    assert "why" in question
    assert "differ" in question
    assert "winner" not in question
    assert not hasattr(memo, "winner")
    assert memo.caveat is not None
    assert memo.caveat.may_transfer
    assert memo.caveat.depends_on_unshared_tools
    assert memo.disagreement == ()


def test_unwelcomed_other_ruleset_stays_off_the_memo():
    store = CuratedStore()
    _half_guard_fixtures(store, welcome_giles=False)

    memo = brief_topic(store, "half guard", "gi", BriefingAdvisor())

    assert memo.other_ruleset_citations == ()
    assert memo.caveat is None
    assert memo.other_ruleset_question == ""


def test_same_ruleset_disagreement_only_when_methods_conflict():
    store = CuratedStore()
    topic, underhook, tight_waist, giles, _knee_cut = _half_guard_fixtures(store)
    camp = _accept(
        store,
        movement="Never camp the tight waist from half guard",
        instructor="Lachlan Giles",
        instructional="Half Guard Anthology Gi",
        video_file="Half Guard Anthology Gi - Volume 1.mp4",
        chapter="Sit up instead of a tight waist",
        cleaned_statement=(
            "From half guard never camp a tight waist; sit up and elevate."
        ),
        step_bullets=(
            "inside shoulder sit up to their inside shoulder",
            "hips elevate instead of wrapping a tight waist",
        ),
        speech_start=100.0,
        ruleset="gi",
    )

    agreeing = brief_topic(store, "half guard", "gi", BriefingAdvisor())
    assert agreeing.disagreement == ()
    assert giles not in {
        side.citation for side in agreeing.disagreement
    }

    memo = brief_topic(
        store,
        "half guard",
        "gi",
        ConflictingAdvisor(
            {tight_waist.movement, camp.movement},
        ),
    )

    sides = {side.citation.movement for side in memo.disagreement}
    assert tight_waist.movement in sides
    assert camp.movement in sides
    assert giles.movement not in sides
    assert all(side.citation.instructor for side in memo.disagreement)
    assert len(memo.disagreement) == 2
    assert store.topic(topic.name, topic.ruleset) == topic
    assert underhook.movement in {
        citation.movement for citation in memo.same_ruleset_citations
    }


def test_other_side_available_as_partner_job():
    store = CuratedStore()
    _half_guard_fixtures(store)
    camp = _accept(
        store,
        movement="Never camp the tight waist from half guard",
        instructor="Lachlan Giles",
        instructional="Half Guard Anthology Gi",
        video_file="Half Guard Anthology Gi - Volume 1.mp4",
        chapter="Sit up instead of a tight waist",
        cleaned_statement=(
            "From half guard never camp a tight waist; sit up and elevate."
        ),
        step_bullets=(
            "inside shoulder sit up to their inside shoulder",
            "hips elevate instead of wrapping a tight waist",
        ),
        speech_start=100.0,
        ruleset="gi",
    )
    tight = next(
        citation
        for citation in store.citations()
        if citation.movement == "Tight Waist Series - Winning from underhooks"
    )

    memo = brief_topic(
        store,
        "half guard",
        "gi",
        ConflictingAdvisor({tight.movement, camp.movement}),
    )

    by_movement = {side.citation.movement: side for side in memo.disagreement}
    tight_side = by_movement[tight.movement]
    camp_side = by_movement[camp.movement]
    assert camp.step_bullets[0] in tight_side.partner_job
    assert tight.step_bullets[0] in camp_side.partner_job


def test_memo_does_not_split_classes():
    store = CuratedStore()
    _half_guard_fixtures(store)

    memo = brief_topic(store, "half guard", "gi", BriefingAdvisor())

    assert not hasattr(memo, "classes")
    assert not hasattr(memo, "class_split")
    assert store.classes() == ()
    assert store.lessons() == ()
    source = inspect.getsource(brief_topic)
    assert "put_class" not in source
    assert "put_lesson" not in source


def test_store_holds_no_disagreement_or_citation_list_on_the_topic():
    store = CuratedStore()
    topic, *_rest = _half_guard_fixtures(store)
    citations_before = store.citations()

    memo = brief_topic(store, "half guard", "gi", BriefingAdvisor())

    stored = store.topic("half guard", "gi")
    assert stored == topic
    assert not hasattr(stored, "disagreement")
    assert not hasattr(stored, "citation_list")
    assert stored.system == ""
    assert store.citations() == citations_before
    assert memo.same_ruleset_citations
    names = " ".join(
        name for name in dir(CuratedStore) if not name.startswith("_")
    ).casefold()
    assert "disagreement" not in names
    assert "citation_list" not in names


def test_briefing_stand_in_does_not_name_a_vendor_or_open_a_browser():
    source = inspect.getsource(
        inspect.getmodule(brief_topic)
    )
    lowered = source.casefold()
    assert "browser" not in lowered
    assert "ffmpeg" not in lowered
    assert "whisper" not in lowered
    advisor = BriefingAdvisor()
    assert callable(advisor.select)
    assert callable(advisor.disagreeing_sides)
