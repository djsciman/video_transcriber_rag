"""Open a topic and welcome other-ruleset instructionals through the facade."""

from __future__ import annotations

import inspect

from coach_app.store import (
    Citation,
    Class,
    CuratedStore,
    Instructional,
    Lesson,
    OtherRulesetChoice,
    SetAside,
    Showing,
    Topic,
    Unit,
)
from coach_app.topics import (
    mark_other_ruleset_showing,
    open_topic,
    other_ruleset_instructionals,
    remove_topic,
    same_ruleset_citations,
    welcome_other_ruleset,
)


class TopicAdvisor:
    """Stand-in that offers other-ruleset instructionals. Does not name a vendor."""

    def offers(self, store: CuratedStore, topic: Topic):
        return other_ruleset_instructionals(store, topic)


def _accept_gi(store: CuratedStore, movement="Knee cut") -> Citation:
    return store.accept(
        {
            "movement": movement,
            "instructor": "John Danaher",
            "chapter": "The knee cut",
            "cleaned_statement": "Frame the far hip and cut the knee to mount.",
            "step_bullets": ("Frame the far hip.", "Cut the knee to mount."),
            "details": ({"speech_start": 12.5, "text": "frame the far hip"},),
        },
        instructional="Half Guard Passing and Dynamic Pins",
        video_file="Half Guard Passing and Dynamic Pins - Volume 1.mp4",
    )


def _accept_no_gi(store: CuratedStore, movement="Arm drag") -> Citation:
    return store.accept(
        {
            "movement": movement,
            "instructor": "John Danaher",
            "chapter": "The arm drag",
            "cleaned_statement": "Pull the arm and take the back.",
            "step_bullets": ("Pull the arm.", "Take the back."),
            "details": ({"speech_start": 8.0, "text": "pull the arm"},),
        },
        instructional="Master The Move Arm Drags",
        video_file="Master The Move Arm Drags - Volume 1.mp4",
    )


def test_open_strips_trailing_spaces_and_reopens_the_same_kept_name():
    store = CuratedStore()

    first = open_topic(store, "Knee cut  ", "gi")
    again = open_topic(store, "Knee cut", "gi")
    padded = open_topic(store, "Knee cut   ", "gi")

    assert first.name == "Knee cut"
    assert first.ruleset == "gi"
    assert again is first or (again.name, again.ruleset) == (first.name, first.ruleset)
    assert padded.name == "Knee cut"
    assert store.topics() == (store.topic("Knee cut", "gi"),)
    assert store.topic("Knee cut  ", "gi") is None


def test_other_characters_including_spelling_open_a_new_topic():
    store = CuratedStore()
    open_topic(store, "Knee cut", "gi")

    typo = open_topic(store, "Kneet cut", "gi")
    case = open_topic(store, "knee cut", "gi")
    inner = open_topic(store, "Knee  cut", "gi")
    hyphen = open_topic(store, "Knee-cut", "gi")

    names = {(topic.name, topic.ruleset) for topic in store.topics()}
    assert names == {
        ("Knee cut", "gi"),
        ("Kneet cut", "gi"),
        ("knee cut", "gi"),
        ("Knee  cut", "gi"),
        ("Knee-cut", "gi"),
    }
    assert typo.name == "Kneet cut"
    assert case.name == "knee cut"
    assert inner.name == "Knee  cut"
    assert hyphen.name == "Knee-cut"


def test_blank_name_does_not_open_and_leading_space_is_kept():
    store = CuratedStore()

    assert open_topic(store, "   ", "gi") is None
    assert open_topic(store, "", "no-gi") is None
    assert store.topics() == ()

    leading = open_topic(store, " Knee cut", "gi")
    assert leading.name == " Knee cut"
    assert store.topic(" Knee cut", "gi") == leading
    assert store.topic("Knee cut", "gi") is None


def test_gi_and_no_gi_namesakes_are_different_topics():
    store = CuratedStore()
    gi = open_topic(store, "Knee cut", "gi")
    no_gi = open_topic(store, "Knee cut", "no-gi")

    assert gi != no_gi
    assert store.topic("Knee cut", "gi").ruleset == "gi"
    assert store.topic("Knee cut", "no-gi").ruleset == "no-gi"
    assert store.topics() == (gi, no_gi)


def test_name_and_ruleset_stay_fixed_on_an_open_topic():
    store = CuratedStore()
    store.put_topic(Topic(name="Knee cut", ruleset="gi", system="Cut to mount."))
    opened = open_topic(store, "Knee cut  ", "gi")

    assert opened.name == "Knee cut"
    assert opened.ruleset == "gi"
    assert opened.system == "Cut to mount."
    assert store.topic("Knee cut", "gi").system == "Cut to mount."
    source = inspect.getsource(open_topic)
    assert "rename" not in source.casefold()


def test_remove_clears_what_belonged_and_the_pair_can_open_again():
    store = CuratedStore()
    topic = open_topic(store, "Knee cut", "gi")
    open_topic(store, "Knee cut", "no-gi")
    store.put_topic(
        Topic(name="Knee cut", ruleset="gi", system="Cut to mount.")
    )
    store.put_other_ruleset_choice(
        OtherRulesetChoice(
            topic_name="Knee cut",
            topic_ruleset="gi",
            instructional="Master The Move Arm Drags",
            yes=True,
        )
    )
    store.put_set_aside(
        SetAside(
            topic_name="Knee cut",
            topic_ruleset="gi",
            earlier_topic_name="Half guard",
            earlier_topic_ruleset="gi",
        )
    )
    store.put_topic(Topic(name="Half guard", ruleset="gi", system="Underhook."))
    unit = store.put_unit(Unit(topic_name="Knee cut", topic_ruleset="gi"))
    class_record = store.put_class(Class(purpose="Cut to mount.", unit_id=unit.id))
    store.put_lesson(
        Lesson(kind="drill", target="knee-cut", class_id=class_record.id, partner_job="Hold.")
    )
    keep_unit = store.put_unit(Unit(topic_name="Knee cut", topic_ruleset="no-gi"))

    remove_topic(store, "Knee cut", "gi")

    assert store.topic("Knee cut", "gi") is None
    assert store.other_ruleset_choice(
        "Knee cut", "gi", "Master The Move Arm Drags"
    ) is None
    assert store.set_asides("Knee cut", "gi") == ()
    assert store.unit(unit.id) is None
    assert store.class_record(class_record.id) is None
    assert store.lessons() == ()
    assert store.topic("Knee cut", "no-gi") is not None
    assert store.unit(keep_unit.id) == keep_unit
    assert store.topic("Half guard", "gi").system == "Underhook."
    assert "._topics" not in inspect.getsource(remove_topic)
    assert "._other_ruleset" not in inspect.getsource(remove_topic)
    assert "._set_asides" not in inspect.getsource(remove_topic)

    reopened = open_topic(store, "Knee cut", "gi")
    assert reopened.name == "Knee cut"
    assert reopened.ruleset == "gi"
    assert reopened.system == ""
    assert topic.name == "Knee cut"


def test_same_ruleset_citations_need_no_extra_choice():
    store = CuratedStore()
    gi_citation = _accept_gi(store)
    no_gi_citation = _accept_no_gi(store)
    topic = open_topic(store, "Knee cut", "gi")

    selectable = same_ruleset_citations(store, topic)

    assert gi_citation in selectable
    assert no_gi_citation not in selectable
    assert store.other_ruleset_choice(
        topic.name, topic.ruleset, "Half Guard Passing and Dynamic Pins"
    ) is None
    assert store.lessons() == ()


def test_other_ruleset_mark_sits_on_a_showing_with_a_caveat():
    store = CuratedStore()
    citation = _accept_gi(store)
    showing = citation.showings[0]

    marked = mark_other_ruleset_showing(store, citation, showing)

    stored = store.citation(citation.id)
    assert stored is not None
    assert stored.showings[0].timestamp == showing.timestamp
    assert stored.showings[0].playback_link == showing.playback_link
    assert stored.showings[0].caveat
    assert marked.caveat == stored.showings[0].caveat


def test_after_open_each_matching_other_ruleset_instructional_is_offered():
    store = CuratedStore()
    _accept_gi(store)
    _accept_no_gi(store)
    store.put_instructional(
        Instructional(
            instructor="Jacob Couch",
            name="Finishing Leg Locks",
            ruleset="no-gi",
        )
    )
    topic = open_topic(store, "Knee cut", "gi")

    offered = TopicAdvisor().offers(store, topic)

    names = tuple(item.name for item in offered)
    assert "Master The Move Arm Drags" in names
    assert "Half Guard Passing and Dynamic Pins" not in names
    assert "Finishing Leg Locks" not in names
    assert all(item.ruleset == "no-gi" for item in offered)


def test_welcome_yes_carries_a_caveat_and_a_later_choice_replaces():
    store = CuratedStore()
    _accept_no_gi(store)
    topic = open_topic(store, "Knee cut", "gi")
    instructional = store.instructional("Master The Move Arm Drags")

    welcomed = welcome_other_ruleset(store, topic, instructional, True)
    stored = store.other_ruleset_choice(
        topic.name, topic.ruleset, "Master The Move Arm Drags"
    )

    assert stored is not None
    assert stored.yes is True
    assert stored.caveat
    assert welcomed.yes is True
    assert welcomed.caveat == stored.caveat
    assert store.lessons() == ()
    assert store.units() == ()

    later = welcome_other_ruleset(store, topic, "Master The Move Arm Drags", False)
    replaced = store.other_ruleset_choice(
        topic.name, topic.ruleset, "Master The Move Arm Drags"
    )
    assert later.yes is False
    assert replaced.yes is False
    assert replaced is later or replaced == later
    assert not getattr(replaced, "caveat", None)
    assert store.lessons() == ()


def test_topics_module_does_not_drive_a_browser_or_name_a_vendor():
    source = inspect.getsource(
        inspect.getmodule(open_topic)
    )
    lowered = source.casefold()
    assert "browser" not in lowered
    assert "ffmpeg" not in lowered
    assert "whisper" not in lowered
    assert callable(CuratedStore.remove_topic)
    opened = open_topic(CuratedStore(), "Knee cut", "gi")
    assert opened.name == "Knee cut"
