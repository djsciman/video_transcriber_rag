"""Persisted curated store: a later runtime loads the same records."""

import copy
import json
from pathlib import Path

from coach_app.store import (
    Class,
    CuratedStore,
    CustomLesson,
    Lesson,
    OtherRulesetChoice,
    PackedClass,
    SetAside,
    Topic,
    Unit,
    UnitHistory,
)

_COMMITTED_SEED = (
    Path(__file__).resolve().parents[1] / "docs" / "enrichment-seed" / "seed.json"
)


def _seed_copy() -> dict:
    return copy.deepcopy(json.loads(_COMMITTED_SEED.read_text(encoding="utf-8")))


def test_later_runtime_sees_an_accepted_citation(tmp_path):
    first = CuratedStore.open(tmp_path)
    written = first.accept(
        {
            "movement": "Knee cut",
            "instructor": "John Danaher",
            "chapter": "The knee cut",
            "cleaned_statement": "Frame the far hip and cut the knee to mount.",
            "details": [{"speech_start": 12.5}],
        },
        instructional="Half Guard Passing and Dynamic Pins",
        video_file="Half Guard Passing and Dynamic Pins - Volume 1.mp4",
        ruleset="gi",
    )

    later = CuratedStore.open(tmp_path)

    assert later.citation(written.id) == written
    assert later.instructional("Half Guard Passing and Dynamic Pins") == (
        first.instructional("Half Guard Passing and Dynamic Pins")
    )
    assert later.volume(
        "Half Guard Passing and Dynamic Pins",
        "Half Guard Passing and Dynamic Pins - Volume 1.mp4",
    ) == first.volume(
        "Half Guard Passing and Dynamic Pins",
        "Half Guard Passing and Dynamic Pins - Volume 1.mp4",
    )
    assert later.citations() == (written,)


def test_video_root_and_transcript_folder_survive(tmp_path):
    first = CuratedStore.open(tmp_path)
    first.set_video_root(r"D:\BJJ library")
    first.set_transcript_folder("Half Guard Passing and Dynamic Pins")

    later = CuratedStore.open(tmp_path)

    assert later.video_root() == r"D:\BJJ library"
    assert later.transcript_folder() == "Half Guard Passing and Dynamic Pins"


def test_first_runtime_imports_consensus_seed(tmp_path):
    first = CuratedStore.open(tmp_path)
    named = tuple(
        node for node in first.enrichment_nodes() if node.kind == "named move"
    )
    positions = tuple(
        node for node in first.enrichment_nodes() if node.kind == "position"
    )
    assert named
    assert any(node.name == "Knee slice pass" for node in named)
    assert any(node.name == "Half guard" for node in positions)


def test_later_runtime_keeps_catalog_edits_and_skips_seed(tmp_path):
    first = CuratedStore.open(tmp_path)
    knee = next(
        node
        for node in first.enrichment_nodes()
        if node.kind == "named move" and node.name == "Knee slice pass"
    )
    first.rename_enrichment_node(knee.id, "Coach knee slice")
    first.delete_enrichment_node(
        next(
            node.id
            for node in first.enrichment_nodes()
            if node.kind == "named move" and node.name == "Old school sweep"
        )
    )

    later = CuratedStore.open(tmp_path)
    later.import_enrichment_seed(_seed_copy())

    assert later.enrichment_node(knee.id).name == "Coach knee slice"
    assert all(
        node.name != "Old school sweep"
        for node in later.enrichment_nodes()
        if node.kind == "named move"
    )
    assert all(
        node.name != "Knee slice pass"
        for node in later.enrichment_nodes()
        if node.kind == "named move"
    )


def test_later_runtime_sees_topics_units_and_history(tmp_path):
    first = CuratedStore.open(tmp_path)
    topic = first.put_topic(Topic(name="Knee cut", ruleset="gi", system="Cut to mount."))
    choice = first.put_other_ruleset_choice(
        OtherRulesetChoice(
            topic_name="Knee cut",
            topic_ruleset="gi",
            instructional="Finishing Leg Locks",
            yes=True,
        )
    )
    set_aside = first.put_set_aside(
        SetAside(
            topic_name="Knee cut",
            topic_ruleset="gi",
            earlier_topic_name="Half guard",
            earlier_topic_ruleset="gi",
        )
    )
    unit = first.put_unit(
        Unit(
            topic_name="Knee cut",
            topic_ruleset="gi",
            paragraph="Teach the knee cut under resistance.",
        )
    )
    class_record = first.put_class(
        Class(purpose="Hit the knee cut from half guard.", unit_id=unit.id)
    )
    lesson = first.put_lesson(
        Lesson(
            kind="drill",
            target="knee-cut",
            class_id=class_record.id,
            partner_job="Hold the underhook.",
        )
    )
    custom = first.put_custom_lesson(
        CustomLesson(
            lesson=Lesson(kind="drill", target="knee-cut", partner_job="Hold.")
        )
    )
    history = first.put_unit_history(
        UnitHistory(
            unit=unit,
            classes=(PackedClass(class_record=class_record, lessons=(lesson,)),),
        )
    )

    later = CuratedStore.open(tmp_path)

    assert later.topic("Knee cut", "gi") == topic
    assert later.other_ruleset_choice("Knee cut", "gi", "Finishing Leg Locks") == choice
    assert later.set_asides("Knee cut", "gi") == (set_aside,)
    assert later.unit(unit.id) == unit
    assert later.class_record(class_record.id) == class_record
    assert later.lesson(lesson.id) == lesson
    assert later.custom_lesson(custom.id) == custom
    assert later.unit_history(history.id) == history
