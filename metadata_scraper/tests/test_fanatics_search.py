from io import StringIO
from pathlib import Path

import pytest

from bjj_organizer.errors import MatchError, UsageError
from bjj_organizer.fanatics_search import ProductHit, lookup_candidates, rank_products, score_match
from bjj_organizer.pipeline import confirm_product_url


class _Stdin:
    def __init__(self, lines: list[str], tty: bool = True) -> None:
        self._lines = iter(lines)
        self._tty = tty

    def isatty(self) -> bool:
        return self._tty

    def readline(self) -> str:
        return next(self._lines)


def test_score_match_prefers_same_instructional():
    folder = "Half Guard Anthology by Lachlan Giles"
    good = "The Half Guard Anthology by Lachlan Giles"
    bundle = "The Half Guard Anthology Bundle by Lachlan Giles"
    other = "Systematically Attacking From Half Guard by Gordon Ryan"
    assert score_match(folder, good) > score_match(folder, other)
    assert score_match(folder, good) > score_match(folder, bundle)


def test_rank_products_orders_by_score():
    products = [
        {"title": "Unrelated Instructional by Someone", "handle": "unrelated", "url": "/products/unrelated"},
        {
            "title": "The Half Guard Anthology by Lachlan Giles",
            "handle": "the-half-guard-anthology-by-lachlan-giles",
            "url": "/products/the-half-guard-anthology-by-lachlan-giles",
        },
    ]
    hits = rank_products("Half Guard Anthology by Lachlan Giles", products)
    assert hits
    assert "half-guard-anthology" in hits[0].url


def test_score_match_prefers_instructional_over_bundle_listing():
    folder = "Go Further Faster By John Danaher"
    bundle = "Go Further Faster Bundle by John Danaher"
    half = "Half Guard: BJJ Fundamentals - Go Further Faster by John Danaher"
    assert score_match(folder, half) > score_match(folder, bundle)
    assert score_match(folder, half, prefer_bundle=True) > score_match(
        folder, bundle, prefer_bundle=True
    )


def test_lookup_candidates_does_not_search_for_a_bundle():
    queries: list[str] = []

    def search(query: str):
        queries.append(query)
        return [
            {
                "title": "Half Guard: BJJ Fundamentals - Go Further Faster by John Danaher",
                "handle": "half-guard-bjj-fundamentals-go-further-faster-by-john-danaher",
                "url": "/products/half-guard-bjj-fundamentals-go-further-faster-by-john-danaher",
            },
            {
                "title": "Go Further Faster Bundle by John Danaher",
                "handle": "go-further-faster-bundle-by-john-danher",
                "url": "/products/go-further-faster-bundle-by-john-danher",
            },
        ]

    hits = lookup_candidates("Go Further Faster By John Danaher", search=search)
    assert queries == ["Go Further Faster By John Danaher"]
    assert hits[0].url.endswith("/half-guard-bjj-fundamentals-go-further-faster-by-john-danaher")
    assert all(not query.endswith(" bundle") for query in queries)


def test_lookup_candidates_uses_injected_search():
    def search(query: str):
        assert "Half Guard" in query
        return [
            {
                "title": "The Half Guard Anthology by Lachlan Giles",
                "handle": "the-half-guard-anthology-by-lachlan-giles",
                "url": "/products/the-half-guard-anthology-by-lachlan-giles",
            }
        ]

    hits = lookup_candidates("Half Guard Anthology by Lachlan Giles", search=search)
    assert hits[0].url.endswith("/the-half-guard-anthology-by-lachlan-giles")


def test_confirm_advances_on_no_then_accepts():
    hits = [
        ProductHit("Wrong", "https://example.com/wrong", 0.5),
        ProductHit("Right", "https://example.com/right", 0.4),
    ]
    stderr = StringIO()
    url = confirm_product_url("Show", hits, _Stdin(["n\n", "y\n"]), stderr)
    assert url == "https://example.com/right"
    assert "Wrong" in stderr.getvalue()
    assert "Right" in stderr.getvalue()


def test_confirm_quit():
    hits = [ProductHit("A", "https://example.com/a", 0.9)]
    with pytest.raises(UsageError, match="cancelled"):
        confirm_product_url("Show", hits, _Stdin(["q\n"]), StringIO())


def test_confirm_requires_tty():
    hits = [ProductHit("A", "https://example.com/a", 0.9)]
    with pytest.raises(UsageError, match="terminal"):
        confirm_product_url("Show", hits, _Stdin(["y\n"], tty=False), StringIO())


def test_confirm_exhausted():
    hits = [ProductHit("A", "https://example.com/a", 0.9)]
    with pytest.raises(MatchError, match="No remaining"):
        confirm_product_url("Show", hits, _Stdin(["n\n"]), StringIO())
