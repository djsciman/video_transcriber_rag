"""Curated-store facade round-trips. Assert contents through the public seam."""

import inspect

from coach_app.store import (
    Citation,
    Class,
    CuratedStore,
    CustomLesson,
    EnrichmentNode,
    Instructional,
    Lesson,
    OtherRulesetChoice,
    SetAside,
    Showing,
    Topic,
    Unit,
    UnitHistory,
    Volume,
)


def test_instructional_round_trip():
    store = CuratedStore()
    written = store.put_instructional(
        Instructional(
            instructor="John Danaher",
            name="Half Guard Passing and Dynamic Pins",
            ruleset="gi",
        )
    )
    assert written.instructor == "John Danaher"
    assert written.name == "Half Guard Passing and Dynamic Pins"
    assert written.ruleset == "gi"
    assert store.instructional("Half Guard Passing and Dynamic Pins") == written
    assert store.instructionals() == (written,)


def test_volume_round_trip():
    store = CuratedStore()
    written = store.put_volume(
        Volume(
            instructional="Half Guard Passing and Dynamic Pins",
            video_file_name="Half Guard Passing and Dynamic Pins - Volume 1.mp4",
        )
    )
    assert written.instructional == "Half Guard Passing and Dynamic Pins"
    assert written.video_file_name == (
        "Half Guard Passing and Dynamic Pins - Volume 1.mp4"
    )
    assert (
        store.volume(
            instructional="Half Guard Passing and Dynamic Pins",
            video_file_name="Half Guard Passing and Dynamic Pins - Volume 1.mp4",
        )
        == written
    )
    assert store.volumes() == (written,)


def test_accepted_citation_round_trip():
    store = CuratedStore()
    written = store.put_citation(
        Citation(
            movement="Knee cut",
            instructor="John Danaher",
            instructional="Half Guard Passing and Dynamic Pins",
            volume="Half Guard Passing and Dynamic Pins - Volume 1.mp4",
            chapter="The knee cut",
            cleaned_statement="Frame the far hip and cut the knee to mount.",
            showings=(Showing(timestamp=12.5, playback_link="volume:1@12.5"),),
        )
    )
    assert written.movement == "Knee cut"
    assert written.instructor == "John Danaher"
    assert written.instructional == "Half Guard Passing and Dynamic Pins"
    assert written.volume == "Half Guard Passing and Dynamic Pins - Volume 1.mp4"
    assert written.chapter == "The knee cut"
    assert written.cleaned_statement == (
        "Frame the far hip and cut the knee to mount."
    )
    assert written.showings == (Showing(timestamp=12.5, playback_link="volume:1@12.5"),)
    assert written.id
    assert store.citation(written.id) == written
    assert store.citations() == (written,)


def test_coach_authored_citation_round_trip():
    store = CuratedStore()
    written = store.put_citation(
        Citation(
            movement="Hip bump sweep",
            step_bullets=("Sit up", "Post the base hand", "Bump and roll"),
        )
    )
    assert written.movement == "Hip bump sweep"
    assert written.step_bullets == ("Sit up", "Post the base hand", "Bump and roll")
    assert written.instructional is None
    assert written.volume is None
    assert written.chapter is None
    assert written.showings == ()
    assert store.citation(written.id) == written


def test_topic_round_trip():
    store = CuratedStore()
    written = store.put_topic(Topic(name="Knee cut", ruleset="gi"))
    assert written.name == "Knee cut"
    assert written.ruleset == "gi"
    assert written.system == ""
    assert store.topic(name="Knee cut", ruleset="gi") == written
    assert store.topics() == (written,)
    assert not hasattr(written, "citation_list")
    assert not hasattr(written, "disagreement")


def test_other_ruleset_choice_round_trip():
    store = CuratedStore()
    written = store.put_other_ruleset_choice(
        OtherRulesetChoice(
            topic_name="Knee cut",
            topic_ruleset="gi",
            instructional="Finishing Leg Locks",
            yes=True,
        )
    )
    assert written.topic_name == "Knee cut"
    assert written.topic_ruleset == "gi"
    assert written.instructional == "Finishing Leg Locks"
    assert written.yes is True
    assert (
        store.other_ruleset_choice(
            topic_name="Knee cut",
            topic_ruleset="gi",
            instructional="Finishing Leg Locks",
        )
        == written
    )
    later = store.put_other_ruleset_choice(
        OtherRulesetChoice(
            topic_name="Knee cut",
            topic_ruleset="gi",
            instructional="Finishing Leg Locks",
            yes=False,
        )
    )
    assert later.yes is False
    assert (
        store.other_ruleset_choice(
            topic_name="Knee cut",
            topic_ruleset="gi",
            instructional="Finishing Leg Locks",
        )
        == later
    )


def test_set_aside_round_trip():
    store = CuratedStore()
    written = store.put_set_aside(
        SetAside(
            topic_name="Knee cut",
            topic_ruleset="gi",
            earlier_topic_name="Half guard",
            earlier_topic_ruleset="gi",
        )
    )
    assert written.topic_name == "Knee cut"
    assert written.earlier_topic_name == "Half guard"
    assert store.set_asides(topic_name="Knee cut", topic_ruleset="gi") == (written,)
    second = store.put_set_aside(
        SetAside(
            topic_name="Knee cut",
            topic_ruleset="gi",
            earlier_topic_name="Knee shield",
            earlier_topic_ruleset="gi",
        )
    )
    assert store.set_asides(topic_name="Knee cut", topic_ruleset="gi") == (
        written,
        second,
    )


def test_enrichment_node_round_trip():
    store = CuratedStore()
    position = store.put_enrichment_node(
        EnrichmentNode(kind="position", name="Half guard")
    )
    named_move = store.put_enrichment_node(
        EnrichmentNode(kind="named move", name="Old school sweep")
    )
    assert position.kind == "position"
    assert position.name == "Half guard"
    assert position.id
    assert named_move.kind == "named move"
    assert store.enrichment_node(position.id) == position
    assert store.enrichment_nodes() == (position, named_move)


def test_unit_round_trip():
    store = CuratedStore()
    written = store.put_unit(
        Unit(
            topic_name="Knee cut",
            topic_ruleset="gi",
            paragraph="Teach the knee cut to mount under resistance.",
        )
    )
    assert written.topic_name == "Knee cut"
    assert written.topic_ruleset == "gi"
    assert written.paragraph == "Teach the knee cut to mount under resistance."
    assert written.id
    assert store.unit(written.id) == written
    assert store.units() == (written,)


def test_class_round_trip():
    store = CuratedStore()
    written = store.put_class(Class(purpose="Hit the knee cut from half guard."))
    assert written.purpose == "Hit the knee cut from half guard."
    assert written.id
    assert store.class_record(written.id) == written
    assert store.classes() == (written,)


def test_lesson_round_trip():
    store = CuratedStore()
    technique = store.put_lesson(
        Lesson(kind="technique", target="Knee cut", citations=("c-knee",))
    )
    drill = store.put_lesson(
        Lesson(kind="drill", target="Knee cut", partner_job="Start light; add frames.")
    )
    sparring = store.put_lesson(
        Lesson(kind="sparring", target="Knee cut", scenario="Half guard, passer on top.")
    )
    game = store.put_lesson(
        Lesson(kind="game", target="Knee cut", condition="Passer must knee cut.")
    )
    assert technique.kind == "technique"
    assert technique.citations == ("c-knee",)
    assert drill.partner_job == "Start light; add frames."
    assert sparring.scenario == "Half guard, passer on top."
    assert game.condition == "Passer must knee cut."
    assert store.lesson(technique.id) == technique
    assert store.lessons() == (technique, drill, sparring, game)


def test_custom_lesson_round_trip():
    store = CuratedStore()
    lesson = Lesson(kind="drill", target="Knee cut", partner_job="Hold the underhook.")
    written = store.put_custom_lesson(CustomLesson(lesson=lesson))
    assert written.lesson == lesson
    assert written.id
    assert store.custom_lesson(written.id) == written
    assert store.custom_lessons() == (written,)


def test_unit_history_round_trip():
    store = CuratedStore()
    unit = store.put_unit(
        Unit(topic_name="Knee cut", topic_ruleset="gi", paragraph="First packing.")
    )
    written = store.put_unit_history(UnitHistory(unit=unit))
    assert written.unit == unit
    assert written.id
    assert store.unit_history(written.id) == written
    assert store.unit_histories() == (written,)


def _public_names(cls) -> list[str]:
    return [name for name in dir(cls) if not name.startswith("_")]


def test_students_never_query_the_facade():
    names = _public_names(CuratedStore)
    assert names
    assert all("student" not in name.lower() for name in names)


def test_one_facade_is_the_source_of_truth():
    import coach_app.store as store_mod

    stores = [
        name
        for name, obj in vars(store_mod).items()
        if isinstance(obj, type) and name.endswith("Store")
    ]
    assert stores == ["CuratedStore"]


def test_facade_stays_on_this_machine():
    parameters = list(inspect.signature(CuratedStore.__init__).parameters)
    assert parameters == ["self"]
    store = CuratedStore()
    written = store.put_instructional(
        Instructional(
            instructor="Jacob Couch",
            name="Finishing Leg Locks",
            ruleset="no-gi",
        )
    )
    assert store.instructional("Finishing Leg Locks") == written


def test_store_does_not_hold_cleanup_disagreement_or_topic_citation_list():
    names = " ".join(_public_names(CuratedStore)).lower()
    assert "cleanup" not in names
    assert "clean_up" not in names
    assert "disagreement" not in names
    assert "citation_list" not in names
    assert "part_list" not in names

