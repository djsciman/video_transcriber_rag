"""Prepare nests raw chapter speech onto a transcribed volume JSON."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

from bjj_pipeline.prepare import prepare_volume

SHOW = "Arm Bars Enter The System by John Danaher"
VOLUME = "Arm Bars Enter The System by John Danaher - S01E01 - Volume 1.mp4"
SEGMENTS = [
    {"start": 10.0, "end": 20.0, "text": "in guard"},
    {"start": 290.0, "end": 310.0, "text": "straddling the start"},
    {"start": 300.0, "end": 320.0, "text": "at the pass"},
    {"start": 400.0, "end": 410.0, "text": "in pass"},
    {"start": 900.0, "end": 910.0, "text": "after chapters"},
]


def _write_volume(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _two_chapter_payload() -> dict:
    return {
        "video_file": VOLUME,
        "chapters": [
            {"title": "Guard", "start": 0.0, "end": 300.0},
            {"title": "Pass", "start": 300.0, "end": 600.0},
        ],
        "language": "en",
        "segments": list(SEGMENTS),
    }


def test_prepare_overwrites_in_place_and_copies_overlapping_span(tmp_path: Path):
    corpus = tmp_path / "corpus"
    json_path = corpus / SHOW / "Season 01" / "vol.json"
    _write_volume(json_path, _two_chapter_payload())

    prepare_volume(json_path, corpus)

    assert list(corpus.rglob("*.json")) == [json_path]
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["segments"] == SEGMENTS
    guard, passing = data["chapters"]
    assert "<290.00>" in guard["transcript_raw"]
    assert "<290.00>" in passing["transcript_raw"]
    assert "straddling the start" in guard["transcript_raw"]
    assert "straddling the start" in passing["transcript_raw"]
    assert "<300.00>" in guard["transcript_raw"]
    assert "<300.00>" in passing["transcript_raw"]
    assert "after chapters" not in guard["transcript_raw"]
    assert "after chapters" not in passing["transcript_raw"]
    assert data["segments"][4]["text"] == "after chapters"
    assert "transcript_cleaned" not in guard
    assert "suggested_tags" not in guard


def test_empty_previous_on_first_and_empty_next_on_last(tmp_path: Path):
    corpus = tmp_path / "corpus"
    json_path = corpus / SHOW / "Season 01" / "vol.json"
    _write_volume(json_path, _two_chapter_payload())

    prepare_volume(json_path, corpus)

    data = json.loads(json_path.read_text(encoding="utf-8"))
    guard, passing = data["chapters"]
    assert guard["previous_chapter"] == ""
    assert guard["next_chapter"] == "Pass"
    assert passing["previous_chapter"] == "Guard"
    assert passing["next_chapter"] == ""


def test_credits_from_show_folder_and_video_file(tmp_path: Path):
    corpus = tmp_path / "corpus"
    json_path = corpus / SHOW / "Season 01" / "vol.json"
    _write_volume(json_path, _two_chapter_payload())

    prepare_volume(json_path, corpus)

    data = json.loads(json_path.read_text(encoding="utf-8"))
    for chapter in data["chapters"]:
        assert chapter["instructor"] == "John Danaher"
        assert chapter["instructional"] == SHOW
        assert chapter["volume"] == VOLUME


def test_instructor_from_nfo_director_when_library_show_exists(tmp_path: Path):
    corpus = tmp_path / "corpus"
    library = tmp_path / "library"
    show = "Arm Bars Enter The System by Wrong Name"
    json_path = corpus / show / "Season 01" / "vol.json"
    payload = _two_chapter_payload()
    payload["video_file"] = "Arm Bars.mp4"
    _write_volume(json_path, payload)
    nfo = library / show / "tvshow.nfo"
    nfo.parent.mkdir(parents=True)
    nfo.write_text(
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        "<tvshow>\n"
        "  <director>John Danaher</director>\n"
        "  <actor><name>Someone Else</name></actor>\n"
        "</tvshow>\n",
        encoding="utf-8",
    )

    prepare_volume(json_path, corpus, library)

    chapter = json.loads(json_path.read_text(encoding="utf-8"))["chapters"][0]
    assert chapter["instructor"] == "John Danaher"
    assert chapter["instructional"] == show
    assert chapter["volume"] == "Arm Bars.mp4"


def test_instructor_from_nfo_actor_when_director_missing(tmp_path: Path):
    corpus = tmp_path / "corpus"
    library = tmp_path / "library"
    show = "Half Guard Anthology"
    json_path = corpus / show / "vol.json"
    payload = _two_chapter_payload()
    payload["video_file"] = "Half Guard.mp4"
    _write_volume(json_path, payload)
    nfo = library / show / "tvshow.nfo"
    nfo.parent.mkdir(parents=True)
    nfo.write_text(
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        "<tvshow>\n"
        "  <actor><name>Lachlan Giles</name></actor>\n"
        "</tvshow>\n",
        encoding="utf-8",
    )

    prepare_volume(json_path, corpus, library)

    chapter = json.loads(json_path.read_text(encoding="utf-8"))["chapters"][0]
    assert chapter["instructor"] == "Lachlan Giles"
    assert chapter["instructional"] == show


def test_instructor_empty_without_nfo_or_by_suffix(tmp_path: Path):
    corpus = tmp_path / "corpus"
    show = "Uncredited Instructional"
    json_path = corpus / show / "vol.json"
    _write_volume(json_path, _two_chapter_payload())

    prepare_volume(json_path, corpus)

    chapter = json.loads(json_path.read_text(encoding="utf-8"))["chapters"][0]
    assert chapter["instructor"] == ""
    assert chapter["instructional"] == show


def test_empty_chapters_leave_file_unchanged(tmp_path: Path):
    corpus = tmp_path / "corpus"
    json_path = corpus / SHOW / "Season 01" / "vol.json"
    payload = _two_chapter_payload()
    payload["chapters"] = []
    _write_volume(json_path, payload)
    before = json_path.read_bytes()

    prepare_volume(json_path, corpus)

    assert json_path.read_bytes() == before


def test_missing_chapters_leave_file_unchanged(tmp_path: Path):
    corpus = tmp_path / "corpus"
    json_path = corpus / SHOW / "Season 01" / "vol.json"
    payload = _two_chapter_payload()
    del payload["chapters"]
    _write_volume(json_path, payload)
    before = json_path.read_bytes()

    prepare_volume(json_path, corpus)

    assert json_path.read_bytes() == before


def test_one_chapter_covering_whole_recording_leave_file_unchanged(tmp_path: Path):
    corpus = tmp_path / "corpus"
    json_path = corpus / SHOW / "Season 01" / "vol.json"
    payload = {
        "video_file": VOLUME,
        "chapters": [{"title": "Volume 1", "start": 0.0, "end": 1000.0}],
        "language": "en",
        "segments": list(SEGMENTS),
    }
    _write_volume(json_path, payload)
    before = json_path.read_bytes()

    prepare_volume(json_path, corpus)

    assert json_path.read_bytes() == before


def test_prepare_has_no_completer_parameter():
    params = inspect.signature(prepare_volume).parameters
    assert "completer" not in params
    assert "model" not in params
    assert list(params) == ["json_path", "corpus_root", "video_library_root"]
