"""Reference-free quality scores for compare-llm chapter pares."""

from __future__ import annotations

import pytest

from bjj_pipeline.llm_metrics import (
    rank_disagreements,
    score_chapter,
    summarize_provider,
    token_f1,
    tokens,
)


def test_tokens_strip_timestamps_and_case():
    assert tokens("<10.00> Keep the elbow tight") == ["keep", "the", "elbow", "tight"]


def test_token_f1_identical_and_partial():
    assert token_f1("keep the elbow tight", "keep the elbow tight") == 1.0
    # overlap {the}: precision 1/3, recall 1/4, F1 2/7
    assert token_f1("keep the elbow tight", "finish the choke") == pytest.approx(2 / 7)


def test_score_chapter_coverage_and_novel_tokens():
    chapter = {
        "title": "Armbar from closed guard",
        "start": 0.0,
        "end": 300.0,
        "transcript_raw": "<10.00> keep the elbow tight and finish",
        "transcript_cleaned": "keep the elbow tight now",
        "concepts": ["Keep the elbow tight."],
        "suggested_tags": ["elbow"],
        "techniques": [
            {
                "named_move": "Armbar from closed guard",
                "source_time_ranges": ["10.00-20.00"],
                "end_position": "mount*",
            }
        ],
    }
    score = score_chapter(chapter)
    assert score["has_cleaned"] is True
    assert score["raw_cover"] == 4 / 6
    assert score["novel_frac"] == 1 / 5
    assert score["cleaned_raw_ratio"] == pytest.approx(24 / 39)
    assert score["leftover_timestamps"] == 0
    assert score["technique_count"] == 1
    assert score["duplicate_named_moves"] == 0
    assert score["starred_fields"] == 1
    assert score["out_of_bounds_ranges"] == 0
    assert score["empty_extract_on_move_title"] is False


def test_score_flags_empty_extract_duplicates_and_bad_ranges():
    chapter = {
        "title": "Flying armbar",
        "start": 0.0,
        "end": 60.0,
        "transcript_raw": "<1.00> fly the armbar <5.00> keep going",
        "transcript_cleaned": "<1.00> fly the armbar",
        "concepts": [],
        "suggested_tags": [],
        "techniques": [
            {
                "named_move": "Flying armbar",
                "source_time_ranges": ["10.00-90.00"],
            },
            {
                "named_move": "Flying armbar",
                "source_time_ranges": ["5.00-8.00"],
            },
        ],
    }
    score = score_chapter(chapter)
    assert score["empty_extract_on_move_title"] is False
    assert score["duplicate_named_moves"] == 1
    assert score["out_of_bounds_ranges"] == 1
    assert score["leftover_timestamps"] == 1

    empty = dict(chapter)
    empty["techniques"] = []
    assert score_chapter(empty)["empty_extract_on_move_title"] is True
    overview = dict(empty)
    overview["title"] = "Overview of the system"
    assert score_chapter(overview)["empty_extract_on_move_title"] is False


def test_summarize_provider_medians_and_counts():
    a = score_chapter(
        {
            "title": "Guard",
            "start": 0.0,
            "end": 10.0,
            "transcript_raw": "keep the elbow tight extra words here",
            "transcript_cleaned": "keep the elbow tight",
            "techniques": [],
        }
    )
    b = score_chapter(
        {
            "title": "Sweep",
            "start": 0.0,
            "end": 10.0,
            "transcript_raw": "keep the elbow tight extra words here",
            "transcript_cleaned": "keep the elbow tight extra",
            "techniques": [{"named_move": "Sweep", "source_time_ranges": []}],
        }
    )
    summary = summarize_provider([a, b])
    assert summary["cleaned_chapters"] == 2
    assert summary["median_raw_cover"] == pytest.approx(9 / 14)
    assert summary["empty_extract_on_move_title"] == 1
    assert summary["technique_count_mean"] == 0.5


def test_rank_disagreements_puts_lowest_f1_first():
    rows = rank_disagreements(
        [
            {
                "path": "show/a.json",
                "title": "Agree",
                "by_provider": {
                    "xai": "keep the elbow tight",
                    "openai": "keep the elbow tight",
                    "anthropic": "keep the elbow tight",
                },
            },
            {
                "path": "show/b.json",
                "title": "Disagree",
                "by_provider": {
                    "xai": "keep the elbow tight",
                    "openai": "finish the choke now",
                    "anthropic": "keep the elbow tight",
                },
            },
        ],
        limit=10,
    )
    assert rows[0]["title"] == "Disagree"
    assert rows[0]["mean_pairwise_f1"] < rows[1]["mean_pairwise_f1"]
    assert rows[0]["pair_f1"]["openai/xai"] == token_f1(
        "keep the elbow tight", "finish the choke now"
    )
