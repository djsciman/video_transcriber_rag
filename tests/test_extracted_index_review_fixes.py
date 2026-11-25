"""Review fixes for spec #124: prepare credits, settings path, filled ruleset."""

from __future__ import annotations

from pathlib import Path

from bjj_pipeline.prepare import prepare_volume
from coach_app.extracted_index import ExtractedIndex
from coach_app.settings import extracted_index_path, set_extracted_index_path
from tests.test_extracted_index import (
    PROCESS_TECHNIQUE,
    VIDEO_FILE,
    _stub_embedder,
)
from tests.test_extracted_index_sentence_find import (
    FIND_STRING,
    PROCESS_EMBED_TEXT,
    TYPED_SENTENCE,
)
from tests.test_prepare_extracted_index import (
    SHOW,
    _process_completer,
    _two_chapter_payload,
    _write_volume,
)

GI_TECHNIQUE = {
    **PROCESS_TECHNIQUE,
    "ruleset": "gi",
    "technique_steps": "Collar grip then sweep.",
    "main_ideas": "Use the lapel.",
}
GI_EMBED_TEXT = "Butterfly sweep Collar grip then sweep. Use the lapel."
GI_VECTOR = [0.0, 1.0]
NOGI_VECTOR = [1.0, 0.0]
FIND_VECTOR = [1.0, 0.0]


def _gi_chapter() -> dict:
    return {
        "title": "GI BUTTERFLY SWEEP",
        "start": 200.0,
        "end": 400.0,
        "techniques": [GI_TECHNIQUE],
    }


def _ruleset_embedder():
    table = {
        FIND_STRING: FIND_VECTOR,
        PROCESS_EMBED_TEXT: NOGI_VECTOR,
        GI_EMBED_TEXT: GI_VECTOR,
        TYPED_SENTENCE: [0.0, 1.0],
    }

    def embed(text: str) -> list[float]:
        return list(table.get(text, [0.0, 1.0]))

    return embed


def test_prepare_ingested_rows_keep_instructor_for_hop_walk_and_siblings(
    tmp_path: Path,
):
    corpus = tmp_path / "corpus"
    json_path = corpus / SHOW / "Season 01" / "vol.json"
    _write_volume(json_path, _two_chapter_payload())
    index = ExtractedIndex(embedder=_stub_embedder)

    code = prepare_volume(
        json_path, corpus, completer=_process_completer, extracted_index=index
    )

    assert code == 0
    marcelo = index.hop_walk(instructor="Marcelo Garcia")
    assert marcelo
    assert all(row.instructor == "Marcelo Garcia" for row in marcelo)
    assert all(row.instructional == SHOW for row in marcelo)
    process = next(
        row for row in marcelo if row.chapter_title == "BUTTERFLY SWEEP PROCESS"
    )
    siblings = index.siblings(process)
    assert {row.kind for row in siblings} == {"concept"}
    assert all(row.instructional == SHOW for row in siblings)
    assert all(row.video_file == VIDEO_FILE for row in siblings)


def test_extracted_index_path_is_a_coach_setting(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("COACH_APP_SETTINGS_PATH", str(tmp_path / "settings.json"))
    location = tmp_path / "library" / "extracted.sqlite"

    set_extracted_index_path(location)

    assert extracted_index_path() == location
    monkeypatch.setenv("COACH_APP_SETTINGS_PATH", str(tmp_path / "other.json"))
    assert extracted_index_path() is None


def test_prepare_upserts_when_extracted_index_setting_is_set(
    tmp_path: Path, monkeypatch
):
    monkeypatch.setenv("COACH_APP_SETTINGS_PATH", str(tmp_path / "settings.json"))
    location = tmp_path / "extracted.sqlite"
    set_extracted_index_path(location)
    original_open = ExtractedIndex.open

    def open_with_stub(path, *, embedder=None, chat=None):
        return original_open(
            path, embedder=embedder or _stub_embedder, chat=chat
        )

    monkeypatch.setattr(ExtractedIndex, "open", open_with_stub)
    corpus = tmp_path / "corpus"
    json_path = corpus / SHOW / "Season 01" / "vol.json"
    _write_volume(json_path, _two_chapter_payload())

    code = prepare_volume(json_path, corpus, completer=_process_completer)

    assert code == 0
    index = ExtractedIndex.open(location, embedder=_stub_embedder)
    hits = index.hop_walk(instructor="Marcelo Garcia")
    assert hits
    assert {row.chapter_title for row in hits} == {
        "INTRODUCTION",
        "BUTTERFLY SWEEP PROCESS",
    }
    index.close()


def test_filled_ruleset_constrains_sentence_find_full_match_band():
    def chat(_sentence: str) -> dict:
        return {
            "start_occupancy": "bottom",
            "start_position": "butterfly-guard",
            "move_type": "sweep",
            "ruleset": "gi",
            "keywords": [],
            "find_string": FIND_STRING,
        }

    index = ExtractedIndex(embedder=_ruleset_embedder(), chat=chat)
    index.ingest_chapter(
        {
            "video_file": VIDEO_FILE,
            "instructor": "Marcelo Garcia",
            "instructional": SHOW,
        },
        {
            "title": "BUTTERFLY SWEEP PROCESS",
            "start": 1055.0,
            "end": 1627.0,
            "techniques": [PROCESS_TECHNIQUE],
        },
    )
    index.ingest_chapter(
        {
            "video_file": VIDEO_FILE,
            "instructor": "Marcelo Garcia",
            "instructional": SHOW,
        },
        _gi_chapter(),
    )

    hits = index.sentence_find(TYPED_SENTENCE, kind="techniques")
    assert [row.ruleset for row in hits] == ["gi", "no-gi"]
    assert hits[0].chapter_title == "GI BUTTERFLY SWEEP"


def test_unfilled_ruleset_does_not_drop_differing_rulesets():
    def chat(_sentence: str) -> dict:
        return {
            "start_occupancy": "bottom",
            "start_position": "butterfly-guard",
            "move_type": "sweep",
            "ruleset": "",
            "keywords": [],
            "find_string": FIND_STRING,
        }

    index = ExtractedIndex(embedder=_ruleset_embedder(), chat=chat)
    index.ingest_chapter(
        {
            "video_file": VIDEO_FILE,
            "instructor": "Marcelo Garcia",
            "instructional": SHOW,
        },
        {
            "title": "BUTTERFLY SWEEP PROCESS",
            "start": 1055.0,
            "end": 1627.0,
            "techniques": [PROCESS_TECHNIQUE],
        },
    )
    index.ingest_chapter(
        {
            "video_file": VIDEO_FILE,
            "instructor": "Marcelo Garcia",
            "instructional": SHOW,
        },
        _gi_chapter(),
    )

    hits = index.sentence_find(TYPED_SENTENCE, kind="techniques")
    assert [row.ruleset for row in hits] == ["no-gi", "gi"]
