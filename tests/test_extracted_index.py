"""Extracted-index facade ingest. Assert rows through the public seam."""

from __future__ import annotations

from coach_app.extracted_index import ExtractedIndex

VIDEO_FILE = "Butterfly by Marcelo Garcia - S01E01 - Volume 1.mp4"
INTRODUCTION_CONCEPT = "Butterfly guard forces the opponent to engage."

PROCESS_TECHNIQUE = {
    "named_move": "Butterfly sweep",
    "ruleset": "no-gi",
    "move_type": "sweep",
    "start_occupancy": "bottom",
    "start_position": "butterfly-guard",
    "end_occupancy": "top",
    "end_position": "half-guard",
    "technique_steps": (
        "1. Butterfly guard, bottom: close the distance with a strong posture."
    ),
    "main_ideas": "Attack so he has to defend; push his elbow in and go immediately.",
    "source_time_ranges": ["1036.24-1603.98"],
    "suggested_tags": ["push the elbow in", "go immediately"],
}

RESHOOT_TECHNIQUE = {
    "named_move": "Butterfly sweep",
    "ruleset": "no-gi",
    "move_type": "sweep",
    "start_occupancy": "bottom",
    "start_position": "butterfly-guard",
    "end_occupancy": "top",
    "end_position": "mount*",
    "technique_steps": "1. Butterfly guard, bottom: close the distance and commit to the sweep.",
    "main_ideas": "Do not back away when he sinks his weight. Reshoot from the middle.",
    "source_time_ranges": ["1637.22-1869.25"],
    "suggested_tags": ["do not back away", "reshoot from the middle"],
}


def _stub_embedder(_text: str) -> list[float]:
    return [0.0] * 8


def _volume() -> dict:
    return {
        "video_file": VIDEO_FILE,
        "instructor": "Marcelo Garcia",
        "instructional": "Butterfly by Marcelo Garcia",
    }


def _process_chapter(**overrides) -> dict:
    chapter = {
        "title": "BUTTERFLY SWEEP PROCESS",
        "start": 1055.0,
        "end": 1627.0,
        "techniques": [PROCESS_TECHNIQUE],
    }
    chapter.update(overrides)
    return chapter


def _introduction_chapter(**overrides) -> dict:
    chapter = {
        "title": "INTRODUCTION",
        "start": 0.0,
        "end": 191.0,
        "concepts": [INTRODUCTION_CONCEPT],
    }
    chapter.update(overrides)
    return chapter


def test_ingest_process_and_introduction_concept():
    index = ExtractedIndex(embedder=_stub_embedder)
    index.ingest_chapter(_volume(), _process_chapter())
    index.ingest_chapter(_volume(), _introduction_chapter())
    rows = index.rows()
    techniques = [row for row in rows if row.kind == "technique"]
    concepts = [row for row in rows if row.kind == "concept"]
    assert len(techniques) == 1
    assert len(concepts) == 1
    technique = techniques[0]
    assert technique.status == "unreviewed"
    assert technique.named_move == "Butterfly sweep"
    assert technique.end_position == "half-guard"
    assert technique.video_file == VIDEO_FILE
    assert technique.chapter_title == "BUTTERFLY SWEEP PROCESS"
    assert technique.chapter_start == 1055.0
    assert technique.array_index == 0
    concept = concepts[0]
    assert concept.status == ""
    assert concept.concept == INTRODUCTION_CONCEPT
    assert concept.named_move == ""
    assert concept.start_position == ""
    assert concept.end_position == ""
    assert concept.chapter_title == "INTRODUCTION"
    assert concept.array_index == 0


def test_empty_techniques_add_no_technique_row():
    index = ExtractedIndex(embedder=_stub_embedder)
    index.ingest_chapter(_volume(), _introduction_chapter(techniques=[]))
    rows = index.rows()
    assert [row.kind for row in rows] == ["concept"]
    assert rows[0].concept == INTRODUCTION_CONCEPT


def test_missing_techniques_add_no_technique_row():
    index = ExtractedIndex(embedder=_stub_embedder)
    index.ingest_chapter(_volume(), _introduction_chapter())
    assert all(row.kind != "technique" for row in index.rows())


def test_empty_concepts_add_no_concept_row():
    index = ExtractedIndex(embedder=_stub_embedder)
    index.ingest_chapter(_volume(), _process_chapter(concepts=[]))
    rows = index.rows()
    assert [row.kind for row in rows] == ["technique"]
    assert rows[0].named_move == "Butterfly sweep"


def test_hops_keep_trailing_star_as_written():
    index = ExtractedIndex(embedder=_stub_embedder)
    index.ingest_chapter(
        _volume(),
        {
            "title": "SHOOT & RESHOOT",
            "start": 1627.0,
            "end": 1897.0,
            "techniques": [RESHOOT_TECHNIQUE],
        },
    )
    technique = index.rows()[0]
    assert technique.kind == "technique"
    assert technique.end_position == "mount*"
    assert technique.extract["end_position"] == "mount*"
    assert technique.named_move == "Butterfly sweep"


def test_same_rewrite_identity_replaces_unreviewed():
    index = ExtractedIndex(embedder=_stub_embedder)
    index.ingest_chapter(_volume(), _process_chapter())
    rewritten = dict(PROCESS_TECHNIQUE)
    rewritten["main_ideas"] = "Reshoot from the middle."
    rewritten["named_move"] = "Butterfly sweep*"
    index.ingest_chapter(_volume(), _process_chapter(techniques=[rewritten]))
    techniques = [row for row in index.rows() if row.kind == "technique"]
    assert len(techniques) == 1
    assert techniques[0].main_ideas == "Reshoot from the middle."
    assert techniques[0].named_move == "Butterfly sweep*"
    assert techniques[0].array_index == 0
    assert techniques[0].chapter_start == 1055.0


def test_open_reopen_keeps_ingested_rows(tmp_path):
    location = tmp_path / "extracted.sqlite"
    index = ExtractedIndex.open(location, embedder=_stub_embedder)
    index.ingest_chapter(_volume(), _process_chapter())
    index.ingest_chapter(_volume(), _introduction_chapter())
    index.close()
    reopened = ExtractedIndex.open(location, embedder=_stub_embedder)
    rows = reopened.rows()
    techniques = [row for row in rows if row.kind == "technique"]
    concepts = [row for row in rows if row.kind == "concept"]
    assert len(techniques) == 1
    assert len(concepts) == 1
    assert techniques[0].named_move == "Butterfly sweep"
    assert techniques[0].status == "unreviewed"
    assert concepts[0].concept == INTRODUCTION_CONCEPT
    reopened.close()


def test_rewrite_identity_includes_chapter_start():
    index = ExtractedIndex(embedder=_stub_embedder)
    index.ingest_chapter(
        _volume(),
        {"title": "INTRODUCTION", "start": 0.0, "concepts": ["First."]},
    )
    index.ingest_chapter(
        _volume(),
        {"title": "INTRODUCTION", "start": 900.0, "concepts": ["Second."]},
    )
    concepts = [row for row in index.rows() if row.kind == "concept"]
    assert {row.concept for row in concepts} == {"First.", "Second."}
