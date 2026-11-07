"""Record topic system words and set-asides. Stand in the advisor."""

from __future__ import annotations

import inspect
from dataclasses import fields

from coach_app.placement import put_catalog_system, validate_lesson_connection
from coach_app.store import CuratedStore, EnrichmentNode, SetAside, Topic, Unit
from coach_app.system import (
    SystemAdvisor,
    choose_system,
    end_set_aside,
    set_aside,
    system_conflicts,
)
from coach_app.topics import open_topic


class CompatibleAdvisor(SystemAdvisor):
    """Stand-in that lets one earlier system sit with one side."""

    def __init__(self, compatible):
        self.compatible = frozenset(compatible)

    def cannot_follow_together(self, earlier_system, side):
        return (earlier_system, side) not in self.compatible


def test_system_words_start_empty_replace_in_place_and_keep_no_history():
    store = CuratedStore()
    topic = open_topic(store, "Knee cut", "gi")

    assert topic.system == ""
    assert store.topic("Knee cut", "gi").system == ""
    assert not hasattr(topic, "system_history")
    assert not hasattr(store, "system_history")

    first = choose_system(store, topic, "Cut to mount.")
    later = choose_system(store, topic, "Knee slice then mount.")

    stored = store.topic("Knee cut", "gi")
    assert first.system == "Cut to mount."
    assert later.system == "Knee slice then mount."
    assert stored.system == "Knee slice then mount."
    assert stored.name == "Knee cut"
    assert stored.ruleset == "gi"
    assert store.topics() == (stored,)
    assert store.topic("Knee cut", "gi") is later or stored == later


def test_chosen_system_remains_after_its_unit_and_shows_on_a_later_topic():
    store = CuratedStore()
    knee_cut = open_topic(store, "Knee cut", "gi")
    choose_system(store, knee_cut, "Cut to mount.")
    store.put_unit(
        Unit(topic_name="Knee cut", topic_ruleset="gi", paragraph="Cut until mount.")
    )
    no_gi = open_topic(store, "Knee cut", "no-gi")
    choose_system(store, no_gi, "Arm drag to the back.")
    later = open_topic(store, "Half guard pass", "gi")
    empty = open_topic(store, "Toreando", "gi")
    sides = ("camp a tight waist", "sit up and elevate")

    unfinished = open_topic(store, "Knee shield", "gi")
    choose_system(store, unfinished, "Frame and recover.")

    assert store.topic("Knee cut", "gi").system == "Cut to mount."
    assert store.units()

    notes = system_conflicts(store, later, sides, SystemAdvisor())
    names = {note.earlier_topic_name: note.system for note in notes}

    assert names["Knee cut"] == "Cut to mount."
    assert names["Knee shield"] == "Frame and recover."
    assert "Toreando" not in names
    assert "Half guard pass" not in names
    assert all(note.system != "Arm drag to the back." for note in notes)
    assert {note.side for note in notes} == set(sides)
    choose_system(store, later, "Pass from the tight waist.")
    after_choice = system_conflicts(store, later, sides, SystemAdvisor())
    assert any(note.earlier_topic_name == "Knee cut" for note in after_choice)
    assert store.topic("Knee cut", "gi").system == "Cut to mount."


def test_combinable_teachings_stay_off_the_note_and_unsure_still_shows():
    store = CuratedStore()
    earlier = open_topic(store, "Half guard", "gi")
    choose_system(store, earlier, "Underhook.")
    topic = open_topic(store, "Half guard pass", "gi")
    sit_up = "sit up and elevate"
    camp = "camp a tight waist"

    unsure = system_conflicts(store, topic, (sit_up, camp), SystemAdvisor())
    filtered = system_conflicts(
        store,
        topic,
        (sit_up, camp),
        CompatibleAdvisor({("Underhook.", sit_up)}),
    )

    assert {(note.system, note.side) for note in unsure} == {
        ("Underhook.", sit_up),
        ("Underhook.", camp),
    }
    assert {(note.system, note.side) for note in filtered} == {("Underhook.", camp)}


def test_set_aside_stores_the_pair_several_can_sit_and_ending_shows_again():
    store = CuratedStore()
    knee_cut = open_topic(store, "Knee cut", "gi")
    toreando = open_topic(store, "Toreando", "gi")
    other = open_topic(store, "Knee cut", "no-gi")
    choose_system(store, knee_cut, "Cut to mount.")
    choose_system(store, toreando, "Circle the legs.")
    choose_system(store, other, "Arm drag to the back.")
    topic = open_topic(store, "Half guard pass", "gi")
    sides = ("camp a tight waist",)

    first = set_aside(store, topic, knee_cut)
    second = set_aside(store, topic, toreando)

    stored = store.set_asides("Half guard pass", "gi")
    assert stored == (first, second)
    assert first.topic_name == "Half guard pass"
    assert first.topic_ruleset == "gi"
    assert first.earlier_topic_name == "Knee cut"
    assert first.earlier_topic_ruleset == "gi"
    assert second.earlier_topic_name == "Toreando"
    hidden = system_conflicts(store, topic, sides, SystemAdvisor())
    assert hidden == ()

    elsewhere = open_topic(store, "Butterfly", "gi")
    still_shown = system_conflicts(store, elsewhere, sides, SystemAdvisor())
    assert {note.earlier_topic_name for note in still_shown} >= {"Knee cut", "Toreando"}

    end_set_aside(store, topic, knee_cut)
    remaining = store.set_asides("Half guard pass", "gi")
    assert remaining == (second,)
    shown_again = system_conflicts(store, topic, sides, SystemAdvisor())
    assert [note.earlier_topic_name for note in shown_again] == ["Knee cut"]
    assert shown_again[0].system == "Cut to mount."

    set_aside(store, topic, knee_cut)
    assert {record.earlier_topic_name for record in store.set_asides("Half guard pass", "gi")} == {
        "Toreando",
        "Knee cut",
    }
    assert system_conflicts(store, topic, sides, SystemAdvisor()) == ()


def test_advisor_reads_live_words_and_stores_no_frozen_copy():
    store = CuratedStore()
    knee_cut = open_topic(store, "Knee cut", "gi")
    choose_system(store, knee_cut, "Cut to mount.")
    topic = open_topic(store, "Half guard pass", "gi")
    sides = ("camp a tight waist",)

    set_aside(store, topic, knee_cut)
    record = store.set_asides("Half guard pass", "gi")[0]
    choose_system(store, knee_cut, "Knee slice then mount.")

    assert {field.name for field in fields(SetAside)} == {
        "topic_name",
        "topic_ruleset",
        "earlier_topic_name",
        "earlier_topic_ruleset",
    }
    assert not hasattr(record, "system")
    assert store.topic("Knee cut", "gi").system == "Knee slice then mount."
    assert system_conflicts(store, topic, sides, SystemAdvisor()) == ()

    end_set_aside(store, topic, knee_cut)
    notes = system_conflicts(store, topic, sides, SystemAdvisor())
    assert notes[0].earlier_topic_name == "Knee cut"
    assert notes[0].system == "Knee slice then mount."
    choose_system(store, knee_cut, "Cut, freeze, mount.")
    live = system_conflicts(store, topic, sides, SystemAdvisor())
    assert live[0].system == "Cut, freeze, mount."
    assert store.topic("Knee cut", "gi").system == "Cut, freeze, mount."


def test_catalog_system_and_topic_system_words_stay_distinct():
    store = CuratedStore()
    hip = store.put_enrichment_node(EnrichmentNode(kind="named move", name="Hip bump"))
    kimura = store.put_enrichment_node(EnrichmentNode(kind="named move", name="Kimura"))
    catalog = put_catalog_system(store, "Closed guard trilemma", (hip.id, kimura.id))
    topic = open_topic(store, "Closed guard", "gi")
    chosen = choose_system(
        store, topic, "Hip bump until they post, then kimura."
    )

    assert catalog.kind == "system"
    assert catalog.name == "Closed guard trilemma"
    assert catalog.aliases == (hip.id, kimura.id)
    assert chosen.system == "Hip bump until they post, then kimura."
    assert store.topic("Closed guard", "gi").system == chosen.system
    assert store.enrichment_node(catalog.id) == catalog
    assert store.enrichment_node(catalog.id).kind == "system"
    assert not isinstance(chosen, EnrichmentNode)
    validate_lesson_connection(system_id=catalog.id)
    assert all(node.kind != "topic" for node in store.enrichment_nodes())


def test_system_module_does_not_name_a_vendor():
    source = inspect.getsource(inspect.getmodule(choose_system))
    lowered = source.casefold()
    assert "browser" not in lowered
    assert "ffmpeg" not in lowered
    assert "whisper" not in lowered
    assert "openai" not in lowered
    assert "anthropic" not in lowered
    assert "sqlite" not in lowered
    advisor = SystemAdvisor()
    assert callable(advisor.cannot_follow_together)
    assert advisor.cannot_follow_together("Underhook.", "camp a tight waist") is True
