"""Prepare upserts techniques and concepts into the extracted index."""

from __future__ import annotations

import io
import json
from pathlib import Path

from bjj_pipeline import prepare
from bjj_pipeline.prepare import ingest_prepared_corpus, prepare_volume
from coach_app.extracted_index import ExtractedIndex
from tests.test_extracted_index import (
    INTRODUCTION_CONCEPT,
    PROCESS_TECHNIQUE,
    RESHOOT_TECHNIQUE,
    VIDEO_FILE,
    _stub_embedder,
)

SHOW = "Butterfly by Marcelo Garcia"
SEGMENTS = [
    {"start": 10.0, "end": 20.0, "text": "in guard"},
    {"start": 290.0, "end": 310.0, "text": "straddling the start"},
    {"start": 300.0, "end": 320.0, "text": "at the pass"},
]


def _write_volume(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _two_chapter_payload() -> dict:
    return {
        "video_file": VIDEO_FILE,
        "chapters": [
            {"title": "INTRODUCTION", "start": 0.0, "end": 300.0},
            {"title": "BUTTERFLY SWEEP PROCESS", "start": 300.0, "end": 600.0},
        ],
        "language": "en",
        "segments": list(SEGMENTS),
    }


def _process_completer(_prompt: str) -> str:
    return json.dumps(
        {
            "transcript_cleaned": "pared",
            "concepts": [INTRODUCTION_CONCEPT],
            "suggested_tags": ["butterfly"],
            "techniques": [PROCESS_TECHNIQUE],
        }
    )


def test_prepare_writes_process_into_extracted_index(tmp_path: Path):
    corpus = tmp_path / "corpus"
    json_path = corpus / SHOW / "Season 01" / "vol.json"
    _write_volume(json_path, _two_chapter_payload())
    index = ExtractedIndex(embedder=_stub_embedder)

    code = prepare_volume(
        json_path, corpus, completer=_process_completer, extracted_index=index
    )

    assert code == 0
    techniques = [row for row in index.rows() if row.kind == "technique"]
    assert len(techniques) == 2
    process = [
        row for row in techniques if row.chapter_title == "BUTTERFLY SWEEP PROCESS"
    ]
    assert len(process) == 1
    assert process[0].status == "unreviewed"
    assert process[0].named_move == "Butterfly sweep"
    assert process[0].video_file == VIDEO_FILE
    assert process[0].chapter_start == 300.0
    assert process[0].array_index == 0


def test_nested_raw_only_volume_adds_no_rows(tmp_path: Path):
    corpus = tmp_path / "corpus"
    json_path = corpus / SHOW / "Season 01" / "vol.json"
    _write_volume(json_path, _two_chapter_payload())
    index = ExtractedIndex(embedder=_stub_embedder)

    code = prepare_volume(json_path, corpus, extracted_index=index)

    assert code == 0
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert "transcript_raw" in data["chapters"][0]
    assert "techniques" not in data["chapters"][0]
    assert "concepts" not in data["chapters"][0]
    assert index.rows() == ()


def _empty_techniques_completer(_prompt: str) -> str:
    return json.dumps(
        {
            "transcript_cleaned": "pared",
            "concepts": [INTRODUCTION_CONCEPT],
            "suggested_tags": ["butterfly"],
            "techniques": [],
        }
    )


def test_empty_techniques_still_insert_concept_rows(tmp_path: Path):
    corpus = tmp_path / "corpus"
    json_path = corpus / SHOW / "Season 01" / "vol.json"
    _write_volume(json_path, _two_chapter_payload())
    index = ExtractedIndex(embedder=_stub_embedder)

    code = prepare_volume(
        json_path,
        corpus,
        completer=_empty_techniques_completer,
        extracted_index=index,
    )

    assert code == 0
    rows = index.rows()
    assert all(row.kind == "concept" for row in rows)
    assert {row.concept for row in rows} == {INTRODUCTION_CONCEPT}
    assert {row.chapter_title for row in rows} == {
        "INTRODUCTION",
        "BUTTERFLY SWEEP PROCESS",
    }


def _sibling_completer(prompt: str) -> str:
    if "chapter: BUTTERFLY SWEEP PROCESS" in prompt:
        techniques = [PROCESS_TECHNIQUE, RESHOOT_TECHNIQUE]
        concepts: list[str] = []
    else:
        techniques = []
        concepts = [INTRODUCTION_CONCEPT]
    return json.dumps(
        {
            "transcript_cleaned": "pared",
            "concepts": concepts,
            "suggested_tags": ["butterfly"],
            "techniques": techniques,
        }
    )


def test_later_prepare_replaces_unreviewed_and_leaves_reviewed(tmp_path: Path):
    corpus = tmp_path / "corpus"
    json_path = corpus / SHOW / "Season 01" / "vol.json"
    _write_volume(json_path, _two_chapter_payload())
    index = ExtractedIndex(embedder=_stub_embedder)
    prepare_volume(
        json_path, corpus, completer=_sibling_completer, extracted_index=index
    )
    techniques = [
        row
        for row in index.rows()
        if row.kind == "technique" and row.chapter_title == "BUTTERFLY SWEEP PROCESS"
    ]
    assert len(techniques) == 2
    index.accept(techniques[0])

    data = json.loads(json_path.read_text(encoding="utf-8"))
    process_chapter = data["chapters"][1]
    rewritten_process = dict(PROCESS_TECHNIQUE)
    rewritten_process["main_ideas"] = "This rewrite must not land on a reviewed row."
    rewritten_reshoot = dict(RESHOOT_TECHNIQUE)
    rewritten_reshoot["main_ideas"] = "Reshoot from the middle."
    process_chapter["techniques"] = [rewritten_process, rewritten_reshoot]
    process_chapter["concepts"] = ["Hooks stay heavy."]
    _write_volume(json_path, data)

    code = prepare_volume(json_path, corpus, extracted_index=index)

    assert code == 0
    rows = [
        row
        for row in index.rows()
        if row.chapter_title == "BUTTERFLY SWEEP PROCESS"
    ]
    techniques = [row for row in rows if row.kind == "technique"]
    concepts = [row for row in rows if row.kind == "concept"]
    assert len(techniques) == 2
    assert techniques[0].status == "reviewed"
    assert techniques[0].main_ideas == PROCESS_TECHNIQUE["main_ideas"]
    assert techniques[1].status == "unreviewed"
    assert techniques[1].main_ideas == "Reshoot from the middle."
    assert techniques[1].end_position == "mount*"
    assert [row.concept for row in concepts] == ["Hooks stay heavy."]


def test_folder_walk_ingests_prepared_json_without_force(tmp_path: Path):
    corpus = tmp_path / "corpus"
    prepared = corpus / SHOW / "Season 01" / "vol.json"
    nested_raw = corpus / SHOW / "Season 01" / "raw.json"
    _write_volume(
        prepared,
        {
            "video_file": VIDEO_FILE,
            "chapters": [
                {
                    "title": "INTRODUCTION",
                    "start": 0.0,
                    "end": 191.0,
                    "transcript_raw": "<0.00> intro",
                    "concepts": [INTRODUCTION_CONCEPT],
                    "techniques": [],
                },
                {
                    "title": "BUTTERFLY SWEEP PROCESS",
                    "start": 1055.0,
                    "end": 1627.0,
                    "transcript_raw": "<1055.00> process",
                    "techniques": [PROCESS_TECHNIQUE],
                    "concepts": [],
                },
            ],
        },
    )
    _write_volume(
        nested_raw,
        {
            "video_file": "Other Volume.mp4",
            "chapters": [
                {
                    "title": "Guard",
                    "start": 0.0,
                    "end": 300.0,
                    "transcript_raw": "<10.00> already nested",
                },
                {
                    "title": "Pass",
                    "start": 300.0,
                    "end": 600.0,
                    "transcript_raw": "<300.00> already nested",
                },
            ],
        },
    )
    index = ExtractedIndex(embedder=_stub_embedder)

    ingest_prepared_corpus(corpus, index)

    techniques = [row for row in index.rows() if row.kind == "technique"]
    concepts = [row for row in index.rows() if row.kind == "concept"]
    assert len(techniques) == 1
    assert techniques[0].named_move == "Butterfly sweep"
    assert techniques[0].status == "unreviewed"
    assert techniques[0].chapter_title == "BUTTERFLY SWEEP PROCESS"
    assert techniques[0].video_file == VIDEO_FILE
    assert len(concepts) == 1
    assert concepts[0].concept == INTRODUCTION_CONCEPT
    assert all(row.video_file != "Other Volume.mp4" for row in index.rows())


def test_run_ingests_already_prepared_json_without_force(tmp_path: Path):
    library = tmp_path / "lib"
    season = library / SHOW / "Season 01"
    season.mkdir(parents=True)
    video = season / VIDEO_FILE
    video.write_bytes(b"fake-video")
    corpus = tmp_path / "corpus"
    json_path = corpus / SHOW / "Season 01" / Path(VIDEO_FILE).with_suffix(".json")
    _write_volume(
        json_path,
        {
            "video_file": VIDEO_FILE,
            "chapters": [
                {
                    "title": "INTRODUCTION",
                    "start": 0.0,
                    "end": 191.0,
                    "transcript_raw": "<0.00> intro",
                    "concepts": [INTRODUCTION_CONCEPT],
                    "techniques": [],
                },
                {
                    "title": "BUTTERFLY SWEEP PROCESS",
                    "start": 1055.0,
                    "end": 1627.0,
                    "transcript_raw": "<1055.00> process",
                    "techniques": [PROCESS_TECHNIQUE],
                    "concepts": [],
                },
            ],
        },
    )
    index = ExtractedIndex(embedder=_stub_embedder)
    before = json_path.read_bytes()

    code = prepare.run(library, corpus, extracted_index=index, stdout=io.StringIO())

    assert code == 0
    assert json_path.read_bytes() == before
    techniques = [row for row in index.rows() if row.kind == "technique"]
    concepts = [row for row in index.rows() if row.kind == "concept"]
    assert len(techniques) == 1
    assert techniques[0].named_move == "Butterfly sweep"
    assert techniques[0].status == "unreviewed"
    assert len(concepts) == 1
    assert concepts[0].concept == INTRODUCTION_CONCEPT


def test_parser_extracted_index_path():
    args = prepare.build_parser().parse_args(
        [
            "--library",
            "lib",
            "--corpus",
            "corpus",
            "--extracted-index",
            "extracted.sqlite",
        ]
    )
    assert args.extracted_index == Path("extracted.sqlite")
    defaulted = prepare.build_parser().parse_args(
        ["--library", "lib", "--corpus", "corpus"]
    )
    assert defaulted.extracted_index is None
    assert defaulted.method == "staged"
    assert defaulted.llm is False

