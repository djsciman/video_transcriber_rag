"""Sentence find with stub chat and cosine bands on the extracted-index facade."""

from __future__ import annotations

import json

import pytest

from coach_app.extracted_index import ExtractedIndex
from tests.test_extracted_index import (
    INTRODUCTION_CONCEPT,
    PROCESS_TECHNIQUE,
    RESHOOT_TECHNIQUE,
    _introduction_chapter,
    _process_chapter,
    _stub_embedder,
    _volume,
)

TYPED_SENTENCE = "how do I reshoot the butterfly sweep when he puts his weight on me"
FIND_STRING = "reshoot butterfly sweep from bottom"
FIND_VECTOR = [1.0, 0.0]
TYPED_VECTOR = [0.0, 1.0]
RESHOOT_VECTOR = [1.0, 0.0]
KEYWORD_ONLY_VECTOR = [0.9, 0.1]
CONCEPT_VECTOR = [0.5, 0.5]
PROCESS_VECTOR = [0.1, 0.9]
SECOND_FULL_VECTOR = [0.2, 0.98]

PROCESS_EMBED_TEXT = (
    "Butterfly sweep "
    "1. Butterfly guard, bottom: close the distance with a strong posture. "
    "Attack so he has to defend; push his elbow in and go immediately."
)
RESHOOT_EMBED_TEXT = (
    "Butterfly sweep "
    "1. Butterfly guard, bottom: close the distance and commit to the sweep. "
    "Do not back away when he sinks his weight. Reshoot from the middle."
)
KEYWORD_ONLY_TECHNIQUE = {
    "named_move": "Knee slice",
    "ruleset": "no-gi",
    "move_type": "pass",
    "start_occupancy": "top",
    "start_position": "half-guard",
    "end_occupancy": "top",
    "end_position": "side-control",
    "technique_steps": "Pin the knee and slice through.",
    "main_ideas": "Reshoot is a different movement.",
    "source_time_ranges": [],
    "suggested_tags": ["reshoot"],
}
KEYWORD_ONLY_EMBED_TEXT = (
    "Knee slice Pin the knee and slice through. Reshoot is a different movement."
)
SECOND_FULL_TECHNIQUE = {
    **RESHOOT_TECHNIQUE,
    "end_position": "half-guard",
    "technique_steps": "Keep the hook and finish the sweep.",
    "main_ideas": "Reshoot if he posts the far hand.",
    "suggested_tags": ["reshoot"],
}
SECOND_FULL_EMBED_TEXT = (
    "Butterfly sweep Keep the hook and finish the sweep. "
    "Reshoot if he posts the far hand."
)


def _reshoot_chapter(**overrides) -> dict:
    chapter = {
        "title": "SHOOT & RESHOOT",
        "start": 1627.0,
        "end": 1897.0,
        "techniques": [RESHOOT_TECHNIQUE],
    }
    chapter.update(overrides)
    return chapter


def _keyword_only_chapter() -> dict:
    return {
        "title": "KNEE SLICE",
        "start": 400.0,
        "end": 500.0,
        "techniques": [KEYWORD_ONLY_TECHNIQUE],
    }


def _second_full_chapter() -> dict:
    return {
        "title": "SECOND SWEEP",
        "start": 700.0,
        "end": 800.0,
        "techniques": [SECOND_FULL_TECHNIQUE],
    }


def _planted_embedder(table: dict[str, list[float]]):
    def embed(text: str) -> list[float]:
        return list(table.get(text, TYPED_VECTOR))

    return embed


def _band_embedder():
    return _planted_embedder(
        {
            FIND_STRING: FIND_VECTOR,
            TYPED_SENTENCE: TYPED_VECTOR,
            RESHOOT_EMBED_TEXT: RESHOOT_VECTOR,
            KEYWORD_ONLY_EMBED_TEXT: KEYWORD_ONLY_VECTOR,
            INTRODUCTION_CONCEPT: CONCEPT_VECTOR,
            PROCESS_EMBED_TEXT: PROCESS_VECTOR,
            SECOND_FULL_EMBED_TEXT: SECOND_FULL_VECTOR,
        }
    )


def _chat_bottom_butterfly_sweep_reshoot(sentence: str) -> dict:
    assert sentence == TYPED_SENTENCE
    return {
        "start_occupancy": "bottom",
        "start_position": "butterfly-guard",
        "move_type": "sweep",
        "keywords": ["reshoot"],
        "find_string": FIND_STRING,
        "advice": "Teach him to hip out first.",
    }


def _index_for_bands(chat=_chat_bottom_butterfly_sweep_reshoot) -> ExtractedIndex:
    index = ExtractedIndex(embedder=_band_embedder(), chat=chat)
    index.ingest_chapter(_volume(), _process_chapter())
    index.ingest_chapter(_volume(), _reshoot_chapter())
    index.ingest_chapter(_volume(), _keyword_only_chapter())
    index.ingest_chapter(_volume(), _introduction_chapter())
    return index


def test_full_hop_and_keyword_match_outranks_keyword_only_row():
    index = _index_for_bands()
    hits = index.sentence_find(TYPED_SENTENCE)
    titles = [row.chapter_title for row in hits]
    assert titles[0] == "SHOOT & RESHOOT"
    assert titles.index("SHOOT & RESHOOT") < titles.index("KNEE SLICE")
    assert hits[0].end_position == "mount*"
    assert hits[0].status == "unreviewed"


def test_sentence_find_embeds_chat_english_not_typed_sentence():
    index = ExtractedIndex(embedder=_band_embedder(), chat=_chat_bottom_butterfly_sweep_reshoot)
    index.ingest_chapter(_volume(), _reshoot_chapter())
    index.ingest_chapter(_volume(), _second_full_chapter())
    hits = index.sentence_find(TYPED_SENTENCE, kind="techniques")
    assert [row.chapter_title for row in hits] == ["SHOOT & RESHOOT", "SECOND SWEEP"]


def test_concept_row_is_never_a_full_hop_match():
    index = _index_for_bands()
    hits = index.sentence_find(TYPED_SENTENCE)
    titles = [row.chapter_title for row in hits]
    assert "INTRODUCTION" in titles
    assert titles.index("SHOOT & RESHOOT") < titles.index("INTRODUCTION")
    concept = next(row for row in hits if row.kind == "concept")
    assert concept.concept == INTRODUCTION_CONCEPT
    assert concept.named_move == ""


def test_kind_filter_techniques_excludes_concepts():
    index = _index_for_bands()
    hits = index.sentence_find(TYPED_SENTENCE, kind="techniques")
    assert hits
    assert all(row.kind == "technique" for row in hits)
    assert "INTRODUCTION" not in [row.chapter_title for row in hits]


def test_kind_filter_concepts_returns_concept_rows_in_lower_band():
    index = _index_for_bands()
    hits = index.sentence_find(TYPED_SENTENCE, kind="concepts")
    assert [row.kind for row in hits] == ["concept"]
    assert [row.concept for row in hits] == [INTRODUCTION_CONCEPT]


def test_unfilled_end_position_does_not_drop_differing_rows():
    def chat(sentence: str) -> dict:
        return {
            "start_occupancy": "bottom",
            "start_position": "butterfly-guard",
            "move_type": "sweep",
            "end_position": "",
            "keywords": [],
            "find_string": FIND_STRING,
        }

    index = ExtractedIndex(embedder=_band_embedder(), chat=chat)
    index.ingest_chapter(_volume(), _process_chapter())
    index.ingest_chapter(_volume(), _reshoot_chapter())
    hits = index.sentence_find(TYPED_SENTENCE, kind="techniques")
    titles = [row.chapter_title for row in hits]
    assert "SHOOT & RESHOOT" in titles
    assert "BUTTERFLY SWEEP PROCESS" in titles
    assert {row.end_position for row in hits} == {"mount*", "half-guard"}


def test_starred_mount_counts_as_mount_hop_hit():
    def chat(sentence: str) -> dict:
        return {
            "start_occupancy": "bottom",
            "start_position": "butterfly-guard",
            "move_type": "sweep",
            "end_position": "mount",
            "keywords": ["reshoot"],
            "find_string": FIND_STRING,
        }

    index = _index_for_bands(chat=chat)
    hits = index.sentence_find(TYPED_SENTENCE)
    assert hits[0].chapter_title == "SHOOT & RESHOOT"
    assert hits[0].end_position == "mount*"


def test_chat_failure_leaves_hop_walk_and_keyword_search_and_returns_no_rows():
    def fail_chat(_sentence: str):
        raise RuntimeError("anthropic auth failed")

    index = ExtractedIndex(embedder=_stub_embedder, chat=fail_chat)
    index.ingest_chapter(_volume(), _reshoot_chapter())
    index.ingest_chapter(_volume(), _introduction_chapter())
    assert index.sentence_find(TYPED_SENTENCE) == ()
    hops = index.hop_walk(
        start_occupancy="bottom",
        start_position="butterfly-guard",
        move_type="sweep",
    )
    assert [row.chapter_title for row in hops] == ["SHOOT & RESHOOT"]
    assert [row.chapter_title for row in index.keyword_search("reshoot")] == [
        "SHOOT & RESHOOT"
    ]


def test_production_chat_skips_missing_keys_and_does_not_hang(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("XAI_API_KEY", raising=False)

    def boom(*_args, **_kwargs):
        raise AssertionError("missing keys must not call a vendor")

    monkeypatch.setattr(
        "coach_app.extracted_index.complete_sentence_find_vendor", boom
    )
    index = ExtractedIndex(embedder=_stub_embedder)
    index.ingest_chapter(_volume(), _reshoot_chapter())
    assert index.sentence_find(TYPED_SENTENCE) == ()
    assert [row.chapter_title for row in index.keyword_search("reshoot")] == [
        "SHOOT & RESHOOT"
    ]


def test_production_chat_tries_anthropic_then_openai_then_xai(monkeypatch):
    seen: list[tuple[str, str]] = []

    def fake_complete(prompt, *, provider, model, **_kwargs):
        seen.append((provider, model))
        raise RuntimeError("quota exhausted")

    monkeypatch.setenv("ANTHROPIC_API_KEY", "ant")
    monkeypatch.setenv("OPENAI_API_KEY", "oai")
    monkeypatch.setenv("XAI_API_KEY", "xai")
    monkeypatch.setattr(
        "coach_app.extracted_index.complete_sentence_find_vendor", fake_complete
    )
    index = ExtractedIndex(embedder=_stub_embedder)
    index.ingest_chapter(_volume(), _reshoot_chapter())
    assert index.sentence_find(TYPED_SENTENCE) == ()
    assert seen == [
        ("anthropic", "claude-haiku-5-5"),
        ("openai", "gpt-5.4-mini"),
        ("xai", "grok-4.3"),
    ]
    assert [row.chapter_title for row in index.hop_walk(end_position="mount")] == [
        "SHOOT & RESHOOT"
    ]


def test_production_chat_stops_after_first_successful_vendor(monkeypatch):
    seen: list[str] = []

    def fake_complete(prompt, *, provider, model, **_kwargs):
        seen.append(provider)
        assert prompt == TYPED_SENTENCE
        return json.dumps(
            {
                "start_occupancy": "bottom",
                "start_position": "butterfly-guard",
                "move_type": "sweep",
                "keywords": ["reshoot"],
                "find_string": FIND_STRING,
            }
        )

    monkeypatch.setenv("ANTHROPIC_API_KEY", "ant")
    monkeypatch.setenv("OPENAI_API_KEY", "oai")
    monkeypatch.setenv("XAI_API_KEY", "xai")
    monkeypatch.setattr(
        "coach_app.extracted_index.complete_sentence_find_vendor", fake_complete
    )
    index = ExtractedIndex(embedder=_band_embedder())
    index.ingest_chapter(_volume(), _reshoot_chapter())
    index.ingest_chapter(_volume(), _keyword_only_chapter())
    hits = index.sentence_find(TYPED_SENTENCE)
    assert seen == ["anthropic"]
    assert hits[0].chapter_title == "SHOOT & RESHOOT"


def test_kind_filter_rejects_unknown_value():
    index = _index_for_bands()
    with pytest.raises(ValueError, match="techniques"):
        index.sentence_find(TYPED_SENTENCE, kind="moves")
