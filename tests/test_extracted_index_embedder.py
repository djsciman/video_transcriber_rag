"""Default MiniLM-L6 embedder through the extracted-index facade."""

from __future__ import annotations

import sys

import pytest

from coach_app import extracted_index as extracted_index_mod
from coach_app.extracted_index import ExtractedIndex
from tests.test_extracted_index import (
    INTRODUCTION_CONCEPT,
    PROCESS_TECHNIQUE,
    _introduction_chapter,
    _process_chapter,
    _volume,
)

MINILM_L6 = "sentence-transformers/all-MiniLM-L6-v2"
MINILM_DIM = 384
FAKE_VECTOR = tuple(0.25 for _ in range(MINILM_DIM))
PROCESS_EMBEDDED_TEXT = (
    "Butterfly sweep "
    "1. Butterfly guard, bottom: close the distance with a strong posture. "
    "Attack so he has to defend; push his elbow in and go immediately."
)


class FakeTextEmbedding:
    """Stand-in for FastEmbed TextEmbedding. No model download."""

    def __init__(self, *args, **kwargs):
        if args:
            kwargs.setdefault("model_name", args[0])
        self.model_name = kwargs.get("model_name")
        self.providers = kwargs.get("providers")
        self.texts: list[str] = []

    def embed(self, texts):
        self.texts.extend(texts)
        for _ in texts:
            yield list(FAKE_VECTOR)

    def query_embed(self, texts):
        raise AssertionError("MiniLM-L6 uses no query prefix")


@pytest.fixture
def fake_fastembed(monkeypatch):
    instances: list[FakeTextEmbedding] = []

    def factory(*args, **kwargs):
        instance = FakeTextEmbedding(*args, **kwargs)
        instances.append(instance)
        return instance

    monkeypatch.setattr(
        extracted_index_mod, "TextEmbedding", factory, raising=False
    )
    return instances


def test_importing_extracted_index_does_not_import_fastembed():
    assert "fastembed" not in sys.modules


def test_default_ingest_stores_384d_minilm_vector_for_technique(fake_fastembed):
    index = ExtractedIndex()
    index.ingest_chapter(_volume(), _process_chapter())
    rows = index.rows()
    technique = rows[0]
    vector = index.embedding(technique)
    assert fake_fastembed[0].model_name == MINILM_L6
    assert fake_fastembed[0].providers == ["CPUExecutionProvider"]
    assert fake_fastembed[0].texts == [PROCESS_EMBEDDED_TEXT]
    assert vector == FAKE_VECTOR
    assert len(vector) == MINILM_DIM


def test_default_ingest_stores_384d_minilm_vector_for_concept(fake_fastembed):
    index = ExtractedIndex()
    index.ingest_chapter(_volume(), _introduction_chapter())
    concept = index.rows()[0]
    vector = index.embedding(concept)
    assert fake_fastembed[0].model_name == MINILM_L6
    assert fake_fastembed[0].texts == [INTRODUCTION_CONCEPT]
    assert vector == FAKE_VECTOR
    assert len(vector) == MINILM_DIM


def test_embed_query_uses_same_minilm_model(fake_fastembed):
    index = ExtractedIndex()
    vector = index.embed_query("reshoot from butterfly")
    assert fake_fastembed[0].model_name == MINILM_L6
    assert fake_fastembed[0].providers == ["CPUExecutionProvider"]
    assert fake_fastembed[0].texts == ["reshoot from butterfly"]
    assert tuple(vector) == FAKE_VECTOR
    assert len(vector) == MINILM_DIM
