"""Keyword search with kind filter on the extracted-index facade."""

from __future__ import annotations

from coach_app.extracted_index import ExtractedIndex
from tests.test_extracted_index import (
    INTRODUCTION_CONCEPT,
    RESHOOT_TECHNIQUE,
    _introduction_chapter,
    _process_chapter,
    _stub_embedder,
    _volume,
)

UNDERHOOK_CONCEPT = "An underhook on the near side keeps him from flattening you."


def _reshoot_chapter(**overrides) -> dict:
    chapter = {
        "title": "SHOOT & RESHOOT",
        "start": 1627.0,
        "end": 1897.0,
        "techniques": [RESHOOT_TECHNIQUE],
    }
    chapter.update(overrides)
    return chapter


def _index_with_sample():
    index = ExtractedIndex(embedder=_stub_embedder)
    index.ingest_chapter(_volume(), _process_chapter())
    index.ingest_chapter(_volume(), _reshoot_chapter())
    index.ingest_chapter(_volume(), _introduction_chapter())
    index.ingest_chapter(
        _volume(),
        {
            "title": "UNDERHOOK THEORY",
            "start": 200.0,
            "end": 400.0,
            "concepts": [UNDERHOOK_CONCEPT],
        },
    )
    return index


def test_reshoot_hits_shoot_and_reshoot_technique():
    index = _index_with_sample()
    hits = index.keyword_search("reshoot")
    assert [row.chapter_title for row in hits] == ["SHOOT & RESHOOT"]
    assert all(row.kind == "technique" for row in hits)


def test_underhook_hits_concept_string():
    index = _index_with_sample()
    hits = index.keyword_search("underhook")
    assert [row.concept for row in hits] == [UNDERHOOK_CONCEPT]
    assert all(row.kind == "concept" for row in hits)


def test_kind_filter_techniques_omits_concepts():
    index = _index_with_sample()
    hits = index.keyword_search("butterfly", kind="techniques")
    assert hits
    assert all(row.kind == "technique" for row in hits)
    assert index.keyword_search("underhook", kind="techniques") == ()


def test_kind_filter_concepts_omits_techniques():
    index = _index_with_sample()
    hits = index.keyword_search("engage", kind="concepts")
    assert [row.concept for row in hits] == [INTRODUCTION_CONCEPT]
    assert all(row.kind == "concept" for row in hits)
    assert index.keyword_search("reshoot", kind="concepts") == ()


def test_kind_filter_both_returns_techniques_and_concepts():
    index = _index_with_sample()
    hits = index.keyword_search("butterfly", kind="both")
    kinds = {row.kind for row in hits}
    assert kinds == {"technique", "concept"}


def test_kind_filter_defaults_to_both():
    index = _index_with_sample()
    hits = index.keyword_search("butterfly")
    assert hits == index.keyword_search("butterfly", kind="both")
    assert {row.kind for row in hits} == {"technique", "concept"}


def test_keyword_search_does_not_call_chat():
    def _forbidden_chat(*_args, **_kwargs):
        raise AssertionError("keyword search must not call chat")

    index = ExtractedIndex(embedder=_stub_embedder, chat=_forbidden_chat)
    index.ingest_chapter(_volume(), _reshoot_chapter())
    hits = index.keyword_search("reshoot")
    assert [row.chapter_title for row in hits] == ["SHOOT & RESHOOT"]


def test_keyword_search_covers_named_move_instructor_instructional_title_steps_ideas_and_tags():
    volume = {
        "video_file": "field-coverage.mp4",
        "instructor": "Helio Gracie",
        "instructional": "Old School Fundamentals",
    }
    index = ExtractedIndex(embedder=_stub_embedder)
    index.ingest_chapter(
        volume,
        {
            "title": "Knee Slice Series",
            "start": 10.0,
            "techniques": [
                {
                    "named_move": "Armbar",
                    "ruleset": "gi",
                    "move_type": "submission",
                    "start_occupancy": "top",
                    "start_position": "mount",
                    "end_occupancy": "top",
                    "end_position": "mount",
                    "technique_steps": "Pin the near elbow and climb to high mount.",
                    "main_ideas": "Flatten him before isolating the arm.",
                    "suggested_tags": ["climb the mount", "isolate the arm"],
                }
            ],
        },
    )
    row = index.rows()[0]
    for query in (
        "armbar",
        "Helio",
        "Fundamentals",
        "Slice",
        "elbow",
        "Flatten",
        "isolate",
    ):
        hits = index.keyword_search(query)
        assert hits == (row,), query


def test_ingest_rewrite_updates_keyword_search():
    index = ExtractedIndex(embedder=_stub_embedder)
    index.ingest_chapter(_volume(), _process_chapter())
    assert [row.chapter_title for row in index.keyword_search("posture")] == [
        "BUTTERFLY SWEEP PROCESS"
    ]
    rewritten = dict(RESHOOT_TECHNIQUE)
    rewritten["technique_steps"] = "Commit to the sweep from butterfly."
    rewritten["main_ideas"] = "Reshoot from the middle."
    rewritten["suggested_tags"] = ["reshoot from the middle"]
    index.ingest_chapter(_volume(), _process_chapter(techniques=[rewritten]))
    assert index.keyword_search("posture") == ()
    assert [row.main_ideas for row in index.keyword_search("reshoot")] == [
        "Reshoot from the middle."
    ]


def test_keyword_search_survives_reopen(tmp_path):
    location = tmp_path / "extracted.sqlite"
    index = ExtractedIndex.open(location, embedder=_stub_embedder)
    index.ingest_chapter(_volume(), _reshoot_chapter())
    index.ingest_chapter(
        _volume(),
        {
            "title": "UNDERHOOK THEORY",
            "start": 200.0,
            "concepts": [UNDERHOOK_CONCEPT],
        },
    )
    index.close()
    reopened = ExtractedIndex.open(location, embedder=_stub_embedder)
    assert [row.chapter_title for row in reopened.keyword_search("reshoot")] == [
        "SHOOT & RESHOOT"
    ]
    assert [row.concept for row in reopened.keyword_search("underhook")] == [
        UNDERHOOK_CONCEPT
    ]
    reopened.close()
