"""Finder writes, Accept, rewrite, and optional corpus write-back on ExtractedIndex."""

from __future__ import annotations

import json
from copy import deepcopy

import pytest

from coach_app.extracted_index import ExtractedIndex
from tests.test_extracted_index import (
    INTRODUCTION_CONCEPT,
    PROCESS_TECHNIQUE,
    RESHOOT_TECHNIQUE,
    VIDEO_FILE,
    _introduction_chapter,
    _process_chapter,
    _stub_embedder,
    _volume,
)

CORRECTED_STEP = "1. Close the distance and reshoot from the middle."


class CountingEmbedder:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def __call__(self, text: str) -> list[float]:
        self.calls.append(text)
        return [0.0] * 8


def _reshoot_chapter(**overrides) -> dict:
    chapter = {
        "title": "SHOOT & RESHOOT",
        "start": 1627.0,
        "end": 1897.0,
        "techniques": [RESHOOT_TECHNIQUE],
    }
    chapter.update(overrides)
    return chapter


def test_save_keeps_unreviewed_and_trailing_star():
    index = ExtractedIndex(embedder=_stub_embedder)
    index.ingest_chapter(_volume(), _reshoot_chapter())
    row = index.rows()[0]
    index.save(row, {"technique_steps": CORRECTED_STEP})
    saved = index.rows()[0]
    assert saved.status == "unreviewed"
    assert saved.technique_steps == CORRECTED_STEP
    assert saved.end_position == "mount*"
    assert saved.extract["end_position"] == "mount*"
    assert saved.named_move == "Butterfly sweep"


def test_save_and_accept_strips_star_and_stamps_reviewed():
    index = ExtractedIndex(embedder=_stub_embedder)
    index.ingest_chapter(_volume(), _reshoot_chapter())
    row = index.rows()[0]
    index.save_and_accept(row, {"technique_steps": CORRECTED_STEP})
    accepted = index.rows()[0]
    assert accepted.status == "reviewed"
    assert accepted.technique_steps == CORRECTED_STEP
    assert accepted.end_position == "mount"
    assert accepted.extract["end_position"] == "mount"


def test_accept_in_place_stamps_reviewed_and_strips_stars():
    index = ExtractedIndex(embedder=_stub_embedder)
    index.ingest_chapter(_volume(), _reshoot_chapter())
    row = index.rows()[0]
    index.accept(row)
    accepted = index.rows()[0]
    assert accepted.status == "reviewed"
    assert accepted.end_position == "mount"
    assert accepted.extract["end_position"] == "mount"
    assert accepted.named_move == "Butterfly sweep"
    assert accepted.technique_steps == RESHOOT_TECHNIQUE["technique_steps"]


def test_multi_select_writes_dirty_occupancy_and_leaves_mixed_named_move():
    index = ExtractedIndex(embedder=_stub_embedder)
    index.ingest_chapter(
        _volume(),
        _process_chapter(
            techniques=[
                PROCESS_TECHNIQUE,
                {**RESHOOT_TECHNIQUE, "named_move": "X-guard sweep"},
            ]
        ),
    )
    rows = [row for row in index.rows() if row.kind == "technique"]
    assert rows[0].named_move == "Butterfly sweep"
    assert rows[1].named_move == "X-guard sweep"
    index.save_many(rows, {"start_occupancy": "top"})
    saved = [row for row in index.rows() if row.kind == "technique"]
    assert saved[0].start_occupancy == "top"
    assert saved[1].start_occupancy == "top"
    assert saved[0].named_move == "Butterfly sweep"
    assert saved[1].named_move == "X-guard sweep"
    assert saved[0].status == "unreviewed"
    assert saved[1].status == "unreviewed"


def test_save_and_accept_many_stamps_and_strips_each_row():
    index = ExtractedIndex(embedder=_stub_embedder)
    index.ingest_chapter(
        _volume(),
        _process_chapter(
            techniques=[
                PROCESS_TECHNIQUE,
                {**RESHOOT_TECHNIQUE, "named_move": "X-guard sweep"},
            ]
        ),
    )
    rows = [row for row in index.rows() if row.kind == "technique"]
    index.save_and_accept_many(rows, {"start_occupancy": "top"})
    saved = [row for row in index.rows() if row.kind == "technique"]
    assert {row.status for row in saved} == {"reviewed"}
    assert saved[0].start_occupancy == "top"
    assert saved[1].start_occupancy == "top"
    assert saved[0].end_position == "half-guard"
    assert saved[1].end_position == "mount"
    assert saved[0].named_move == "Butterfly sweep"
    assert saved[1].named_move == "X-guard sweep"


def test_concept_rows_reject_accept():
    index = ExtractedIndex(embedder=_stub_embedder)
    index.ingest_chapter(_volume(), _introduction_chapter())
    concept = index.rows()[0]
    with pytest.raises(ValueError):
        index.accept(concept)
    with pytest.raises(ValueError):
        index.save_and_accept(concept, {})
    leftover = index.rows()[0]
    assert leftover.kind == "concept"
    assert leftover.status == ""
    assert leftover.concept == INTRODUCTION_CONCEPT


def test_later_ingest_replaces_unreviewed_and_concepts_leaves_reviewed():
    index = ExtractedIndex(embedder=_stub_embedder)
    chapter = _process_chapter(
        techniques=[PROCESS_TECHNIQUE, RESHOOT_TECHNIQUE],
        concepts=["Keep the hooks in."],
    )
    index.ingest_chapter(_volume(), chapter)
    techniques = [row for row in index.rows() if row.kind == "technique"]
    index.accept(techniques[0])
    rewritten_process = dict(PROCESS_TECHNIQUE)
    rewritten_process["main_ideas"] = "This rewrite must not land on a reviewed row."
    rewritten_reshoot = dict(RESHOOT_TECHNIQUE)
    rewritten_reshoot["main_ideas"] = "Reshoot from the middle."
    index.ingest_chapter(
        _volume(),
        _process_chapter(
            techniques=[rewritten_process, rewritten_reshoot],
            concepts=["Hooks stay heavy."],
        ),
    )
    rows = index.rows()
    techniques = [row for row in rows if row.kind == "technique"]
    concepts = [row for row in rows if row.kind == "concept"]
    assert len(techniques) == 2
    assert techniques[0].status == "reviewed"
    assert techniques[0].main_ideas == PROCESS_TECHNIQUE["main_ideas"]
    assert techniques[0].named_move == "Butterfly sweep"
    assert techniques[1].status == "unreviewed"
    assert techniques[1].main_ideas == "Reshoot from the middle."
    assert techniques[1].end_position == "mount*"
    assert len(concepts) == 1
    assert concepts[0].concept == "Hooks stay heavy."


def test_optional_write_back_updates_only_matching_technique(tmp_path):
    other = dict(PROCESS_TECHNIQUE)
    other["named_move"] = "X-guard sweep"
    payload = {
        "video_file": VIDEO_FILE,
        "instructor": "Marcelo Garcia",
        "instructional": "Butterfly by Marcelo Garcia",
        "chapters": [
            {
                "title": "SHOOT & RESHOOT",
                "start": 1627.0,
                "end": 1897.0,
                "techniques": [deepcopy(RESHOOT_TECHNIQUE), deepcopy(other)],
                "concepts": ["Keep the hooks in."],
            }
        ],
    }
    corpus = tmp_path / "volume.json"
    corpus.write_text(json.dumps(payload), encoding="utf-8")
    index = ExtractedIndex(embedder=_stub_embedder)
    index.ingest_chapter(_volume(), payload["chapters"][0], corpus_json_path=corpus)
    row = [item for item in index.rows() if item.kind == "technique"][0]
    index.save(
        row,
        {"technique_steps": CORRECTED_STEP},
        write_back_corpus=True,
    )
    written = json.loads(corpus.read_text(encoding="utf-8"))
    techniques = written["chapters"][0]["techniques"]
    assert techniques[0]["technique_steps"] == CORRECTED_STEP
    assert techniques[0]["end_position"] == "mount*"
    assert techniques[1] == other
    assert written["chapters"][0]["concepts"] == ["Keep the hooks in."]


def test_write_back_after_save_and_accept_strips_star_in_corpus(tmp_path):
    payload = {
        "video_file": VIDEO_FILE,
        "chapters": [
            {
                "title": "SHOOT & RESHOOT",
                "start": 1627.0,
                "end": 1897.0,
                "techniques": [deepcopy(RESHOOT_TECHNIQUE)],
            }
        ],
    }
    corpus = tmp_path / "volume.json"
    corpus.write_text(json.dumps(payload), encoding="utf-8")
    index = ExtractedIndex(embedder=_stub_embedder)
    index.ingest_chapter(_volume(), payload["chapters"][0], corpus_json_path=corpus)
    index.save_and_accept(index.rows()[0], {}, write_back_corpus=True)
    written = json.loads(corpus.read_text(encoding="utf-8"))
    assert written["chapters"][0]["techniques"][0]["end_position"] == "mount"


def test_text_change_reembeds_including_accept_stripping_named_move_star():
    embedder = CountingEmbedder()
    starred = dict(RESHOOT_TECHNIQUE)
    starred["named_move"] = "Butterfly sweep*"
    index = ExtractedIndex(embedder=embedder)
    index.ingest_chapter(_volume(), _reshoot_chapter(techniques=[starred]))
    ingest_calls = len(embedder.calls)
    assert ingest_calls == 1
    index.save(index.rows()[0], {"technique_steps": CORRECTED_STEP})
    assert len(embedder.calls) == ingest_calls + 1
    index.accept(index.rows()[0])
    assert len(embedder.calls) == ingest_calls + 2
    accepted = index.rows()[0]
    assert accepted.named_move == "Butterfly sweep"
    assert accepted.status == "reviewed"


def test_status_only_accept_with_identical_embedded_text_skips_vector():
    embedder = CountingEmbedder()
    index = ExtractedIndex(embedder=embedder)
    index.ingest_chapter(_volume(), _reshoot_chapter())
    ingest_calls = len(embedder.calls)
    assert ingest_calls == 1
    index.accept(index.rows()[0])
    assert len(embedder.calls) == ingest_calls
    accepted = index.rows()[0]
    assert accepted.status == "reviewed"
    assert accepted.end_position == "mount"


def test_occupancy_only_save_does_not_reembed():
    embedder = CountingEmbedder()
    index = ExtractedIndex(embedder=embedder)
    index.ingest_chapter(_volume(), _process_chapter())
    ingest_calls = len(embedder.calls)
    index.save(index.rows()[0], {"start_occupancy": "top"})
    assert len(embedder.calls) == ingest_calls
    assert index.rows()[0].start_occupancy == "top"
    assert index.rows()[0].status == "unreviewed"
