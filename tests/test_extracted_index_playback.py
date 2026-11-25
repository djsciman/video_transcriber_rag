"""Playback resolve and cleaned-speech lookup on the extracted-index facade."""

from __future__ import annotations

import json
from pathlib import Path

from tests.test_extracted_index import (
    PROCESS_TECHNIQUE,
    VIDEO_FILE,
    _introduction_chapter,
    _process_chapter,
    _stub_embedder,
    _volume,
)

from coach_app.extracted_index import ExtractedIndex

FOLDER = "Butterfly by Marcelo Garcia/Season 01"
JSON_NAME = "marcelo-butterfly-s01e01.json"


def test_process_showing_speech_start_is_range_start_not_chapter_start():
    index = ExtractedIndex(embedder=_stub_embedder)
    index.ingest_chapter(_volume(), _process_chapter())
    technique = [row for row in index.rows() if row.kind == "technique"][0]
    assert technique.chapter_start == 1055.0
    assert len(technique.showings) == 1
    assert technique.showings[0].start == 1036.24
    assert technique.showings[0].end == 1603.98


def test_empty_source_time_ranges_yield_no_showing():
    index = ExtractedIndex(embedder=_stub_embedder)
    technique = dict(PROCESS_TECHNIQUE)
    technique["source_time_ranges"] = []
    index.ingest_chapter(_volume(), _process_chapter(techniques=[technique]))
    row = index.rows()[0]
    assert row.kind == "technique"
    assert row.chapter_start == 1055.0
    assert row.showings == ()


def test_missing_video_returns_unavailable_and_keeps_the_row(tmp_path):
    index = ExtractedIndex(embedder=_stub_embedder)
    json_path = f"{FOLDER}/{JSON_NAME}"
    index.ingest_chapter(
        _volume(),
        _process_chapter(),
        corpus_json_path=json_path,
    )
    folder = tmp_path / "Butterfly by Marcelo Garcia" / "Season 01"
    folder.mkdir(parents=True)
    (folder / Path(VIDEO_FILE).with_suffix(".nfo")).write_text("artwork", encoding="utf-8")
    row = index.rows()[0]
    playback = index.resolve_playback(row, row.showings[0], video_root=tmp_path)
    assert playback.available is False
    assert playback.speech_start == 1036.24
    assert playback.path.name == VIDEO_FILE
    assert playback.path == tmp_path / "Butterfly by Marcelo Garcia" / "Season 01" / VIDEO_FILE
    assert index.rows()[0].named_move == "Butterfly sweep"


PROCESS_CLEANED = "Push the elbow in and go immediately with the butterfly sweep."


def _write_volume_json(path: Path, chapters) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"video_file": VIDEO_FILE, "chapters": list(chapters)}),
        encoding="utf-8",
    )


def test_cleaned_speech_uses_stored_json_path_not_video_file_stem(tmp_path):
    json_rel = f"{FOLDER}/{JSON_NAME}"
    assert Path(JSON_NAME).stem != Path(VIDEO_FILE).stem
    _write_volume_json(
        tmp_path / json_rel,
        [
            {
                "title": "BUTTERFLY SWEEP PROCESS",
                "start": 1055.0,
                "end": 1627.0,
                "transcript_cleaned": PROCESS_CLEANED,
                "transcript_raw": "raw process speech",
            }
        ],
    )
    index = ExtractedIndex(embedder=_stub_embedder)
    index.ingest_chapter(_volume(), _process_chapter(), corpus_json_path=json_rel)
    row = index.rows()[0]
    assert row.corpus_json_path == json_rel
    assert not Path(row.corpus_json_path).is_absolute()
    assert "transcript_cleaned" not in (row.extract or {})
    assert index.cleaned_speech(row, tmp_path) == PROCESS_CLEANED


def test_duplicate_introduction_titles_are_distinguished_by_start(tmp_path):
    json_rel = f"{FOLDER}/{JSON_NAME}"
    first_cleaned = "First introduction cleaned speech."
    second_cleaned = "Second introduction cleaned speech."
    _write_volume_json(
        tmp_path / json_rel,
        [
            {
                "title": "INTRODUCTION",
                "start": 0.0,
                "end": 191.0,
                "transcript_cleaned": first_cleaned,
            },
            {
                "title": "INTRODUCTION",
                "start": 900.0,
                "end": 1100.0,
                "transcript_cleaned": second_cleaned,
            },
        ],
    )
    index = ExtractedIndex(embedder=_stub_embedder)
    index.ingest_chapter(
        _volume(),
        _introduction_chapter(),
        corpus_json_path=json_rel,
    )
    index.ingest_chapter(
        _volume(),
        _introduction_chapter(start=900.0, end=1100.0, concepts=["Later intro."]),
        corpus_json_path=json_rel,
    )
    by_start = {row.chapter_start: row for row in index.rows() if row.kind == "concept"}
    assert by_start[0.0].chapter_title == "INTRODUCTION"
    assert by_start[900.0].chapter_title == "INTRODUCTION"
    assert index.cleaned_speech(by_start[0.0], tmp_path) == first_cleaned
    assert index.cleaned_speech(by_start[900.0], tmp_path) == second_cleaned


def test_missing_json_leaves_row_and_returns_no_cleaned_speech(tmp_path):
    json_rel = f"{FOLDER}/{JSON_NAME}"
    index = ExtractedIndex(embedder=_stub_embedder)
    index.ingest_chapter(_volume(), _process_chapter(), corpus_json_path=json_rel)
    row = index.rows()[0]
    assert index.cleaned_speech(row, tmp_path) is None
    assert index.rows()[0].named_move == "Butterfly sweep"
    assert index.rows()[0].chapter_start == 1055.0


def test_missing_chapter_in_json_returns_no_cleaned_speech(tmp_path):
    json_rel = f"{FOLDER}/{JSON_NAME}"
    _write_volume_json(
        tmp_path / json_rel,
        [
            {
                "title": "INTRODUCTION",
                "start": 0.0,
                "end": 191.0,
                "transcript_cleaned": "Intro speech.",
            }
        ],
    )
    index = ExtractedIndex(embedder=_stub_embedder)
    index.ingest_chapter(_volume(), _process_chapter(), corpus_json_path=json_rel)
    row = index.rows()[0]
    assert index.cleaned_speech(row, tmp_path) is None
    assert index.rows()[0].named_move == "Butterfly sweep"


def test_cleaned_speech_opens_only_the_stored_json_path(tmp_path):
    stored_rel = f"{FOLDER}/{JSON_NAME}"
    other_rel = "Other Show/Season 01/other.json"
    _write_volume_json(
        tmp_path / stored_rel,
        [
            {
                "title": "BUTTERFLY SWEEP PROCESS",
                "start": 1055.0,
                "end": 1627.0,
                "transcript_cleaned": PROCESS_CLEANED,
            }
        ],
    )
    _write_volume_json(
        tmp_path / other_rel,
        [
            {
                "title": "BUTTERFLY SWEEP PROCESS",
                "start": 1055.0,
                "end": 1627.0,
                "transcript_cleaned": "Wrong volume cleaned speech.",
            }
        ],
    )
    index = ExtractedIndex(embedder=_stub_embedder)
    index.ingest_chapter(_volume(), _process_chapter(), corpus_json_path=stored_rel)
    row = index.rows()[0]
    assert index.cleaned_speech(row, tmp_path) == PROCESS_CLEANED
    assert index.cleaned_speech(row, tmp_path) != "Wrong volume cleaned speech."


def test_present_video_is_available(tmp_path):
    json_rel = f"{FOLDER}/{JSON_NAME}"
    index = ExtractedIndex(embedder=_stub_embedder)
    index.ingest_chapter(_volume(), _process_chapter(), corpus_json_path=json_rel)
    video = tmp_path / "Butterfly by Marcelo Garcia" / "Season 01" / VIDEO_FILE
    video.parent.mkdir(parents=True)
    video.write_bytes(b"")
    row = index.rows()[0]
    playback = index.resolve_playback(row, row.showings[0], video_root=tmp_path)
    assert playback.available is True
    assert playback.path == video
    assert playback.speech_start == 1036.24


def test_ingest_accepts_transcript_folder_when_json_is_a_basename(tmp_path):
    _write_volume_json(
        tmp_path / JSON_NAME,
        [
            {
                "title": "BUTTERFLY SWEEP PROCESS",
                "start": 1055.0,
                "end": 1627.0,
                "transcript_cleaned": PROCESS_CLEANED,
            }
        ],
    )
    video = tmp_path / "Butterfly by Marcelo Garcia" / "Season 01" / VIDEO_FILE
    video.parent.mkdir(parents=True)
    video.write_bytes(b"")
    index = ExtractedIndex(embedder=_stub_embedder)
    index.ingest_chapter(
        _volume(),
        _process_chapter(),
        corpus_json_path=JSON_NAME,
        transcript_folder=FOLDER,
    )
    row = index.rows()[0]
    assert row.transcript_folder == FOLDER
    assert row.corpus_json_path == JSON_NAME
    assert not Path(row.transcript_folder).is_absolute()
    playback = index.resolve_playback(row, row.showings[0], video_root=tmp_path)
    assert playback.available is True
    assert playback.path == video
    assert index.cleaned_speech(row, tmp_path) == PROCESS_CLEANED
