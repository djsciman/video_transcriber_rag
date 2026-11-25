"""Hop walk and sibling lookup through the extracted-index facade."""

from __future__ import annotations

from coach_app.extracted_index import ExtractedIndex
from tests.test_extracted_index import (
    INTRODUCTION_CONCEPT,
    PROCESS_TECHNIQUE,
    RESHOOT_TECHNIQUE,
    VIDEO_FILE,
    _introduction_chapter,
    _process_chapter,
    _volume,
)

CLOSED_GUARD_TECHNIQUE = {
    **PROCESS_TECHNIQUE,
    "named_move": "Hip bump sweep",
    "start_position": "closed-guard",
    "end_position": "mount",
}

DANAHER_VOLUME = {
    "video_file": "Enter The System - S01E01 - Volume 1.mp4",
    "instructor": "John Danaher",
    "instructional": "Enter The System",
}

DANAHER_CHAPTER = {
    "title": "CLOSED GUARD SWEEP",
    "start": 10.0,
    "end": 90.0,
    "techniques": [CLOSED_GUARD_TECHNIQUE],
}


def _reshoot_chapter(**overrides) -> dict:
    chapter = {
        "title": "SHOOT & RESHOOT",
        "start": 1627.0,
        "end": 1897.0,
        "techniques": [RESHOOT_TECHNIQUE],
    }
    chapter.update(overrides)
    return chapter


def _index_with_process_reshoot_and_intro() -> ExtractedIndex:
    index = ExtractedIndex()
    index.ingest_chapter(_volume(), _process_chapter())
    index.ingest_chapter(_volume(), _reshoot_chapter())
    index.ingest_chapter(_volume(), _introduction_chapter())
    return index


def test_hop_walk_bottom_butterfly_sweep_returns_process_and_reshoot():
    index = _index_with_process_reshoot_and_intro()
    hits = index.hop_walk(
        start_occupancy="bottom",
        start_position="butterfly-guard",
        move_type="sweep",
    )
    assert [row.kind for row in hits] == ["technique", "technique"]
    assert {row.chapter_title for row in hits} == {
        "BUTTERFLY SWEEP PROCESS",
        "SHOOT & RESHOOT",
    }
    assert {row.end_position for row in hits} == {"half-guard", "mount*"}
    assert all(row.named_move == "Butterfly sweep" for row in hits)


def test_hop_walk_ors_selected_start_positions():
    index = ExtractedIndex()
    index.ingest_chapter(_volume(), _process_chapter())
    index.ingest_chapter(DANAHER_VOLUME, DANAHER_CHAPTER)
    both = index.hop_walk(start_position=["butterfly-guard", "closed-guard"])
    assert {row.start_position for row in both} == {"butterfly-guard", "closed-guard"}
    closed_only = index.hop_walk(start_position="closed-guard")
    assert [row.start_position for row in closed_only] == ["closed-guard"]
    assert [row.named_move for row in closed_only] == ["Hip bump sweep"]


def test_hop_walk_mount_chip_matches_starred_end_position():
    index = _index_with_process_reshoot_and_intro()
    hits = index.hop_walk(end_position="mount")
    assert [row.chapter_title for row in hits] == ["SHOOT & RESHOOT"]
    assert hits[0].end_position == "mount*"
    assert hits[0].extract["end_position"] == "mount*"


def test_hop_walk_excludes_concept_rows():
    index = _index_with_process_reshoot_and_intro()
    hits = index.hop_walk()
    assert hits
    assert all(row.kind == "technique" for row in hits)
    assert INTRODUCTION_CONCEPT not in {row.concept for row in hits}


def test_hop_walk_filters_instructor():
    index = ExtractedIndex()
    index.ingest_chapter(_volume(), _process_chapter())
    index.ingest_chapter(DANAHER_VOLUME, DANAHER_CHAPTER)
    marcelo = index.hop_walk(instructor="Marcelo Garcia")
    assert [row.instructor for row in marcelo] == ["Marcelo Garcia"]
    assert [row.named_move for row in marcelo] == ["Butterfly sweep"]
    danaher = index.hop_walk(instructor="John Danaher")
    assert [row.instructor for row in danaher] == ["John Danaher"]
    assert [row.named_move for row in danaher] == ["Hip bump sweep"]


def test_hop_walk_flags_unreviewed_techniques():
    index = _index_with_process_reshoot_and_intro()
    hits = index.hop_walk(
        start_occupancy="bottom",
        start_position="butterfly-guard",
        move_type="sweep",
    )
    assert hits
    assert all(row.status == "unreviewed" for row in hits)


def test_siblings_by_keys_return_techniques_and_concepts_from_chapter():
    index = ExtractedIndex()
    index.ingest_chapter(
        _volume(),
        _process_chapter(concepts=[INTRODUCTION_CONCEPT]),
    )
    siblings = index.siblings(
        "Butterfly by Marcelo Garcia",
        VIDEO_FILE,
        "BUTTERFLY SWEEP PROCESS",
        1055.0,
    )
    assert {row.kind for row in siblings} == {"technique", "concept"}
    assert {row.named_move for row in siblings if row.kind == "technique"} == {
        "Butterfly sweep"
    }
    assert {row.concept for row in siblings if row.kind == "concept"} == {
        INTRODUCTION_CONCEPT
    }


def test_siblings_of_row_return_other_rows_from_chapter():
    index = ExtractedIndex()
    index.ingest_chapter(
        _volume(),
        _process_chapter(concepts=[INTRODUCTION_CONCEPT]),
    )
    technique = next(row for row in index.rows() if row.kind == "technique")
    siblings = index.siblings(technique)
    assert [row.kind for row in siblings] == ["concept"]
    assert siblings[0].concept == INTRODUCTION_CONCEPT
    assert siblings[0].chapter_title == technique.chapter_title
    assert siblings[0].chapter_start == technique.chapter_start
    assert siblings[0].video_file == technique.video_file
    assert siblings[0].instructional == technique.instructional
