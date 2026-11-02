from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlparse, urlunparse

from .httputil import DEFAULT_USER_AGENT, fetch_json

SEARCH_LIMIT = 10
MIN_SCORE = 0.42
STOPWORDS = {
    "the",
    "a",
    "an",
    "by",
    "for",
    "of",
    "and",
    "vol",
    "volume",
    "dvd",
    "instructional",
}

QUERY_OVERRIDES: dict[str, str] = {
    "Butterfly by Marcelo Garcia": "Complete Butterfly Guard Marcelo Garcia",
    "Jay Rods Judo": "Jay Rods Judo Jay Rodriguez",
    "Keenan Cornelius - Legacy Worm Guard": "Worm Guard Keenan Cornelius",
    "Master The Move by John Danaher": "Master The Move Arm Drags John Danaher",
    "Open Guard Vol 2 by John Danaher": "Open Guard Volume 2 John Danaher",
    "Standing2Ground Bundle by John Danaher": "Standing To Ground Bundle John Danaher",
    "The Fastest Way by John Danaher": "The Fastest Way To Increase Your Submission Percentage No Gi John Danaher",
    "Ultimate Tachi Waza": "Ultimate Tachi Waza Travis Stevens",
    "Upper Body Takedowns": "Upper Body Takedowns John Danaher",
    "Feet To Floor by John Danaher": "Feet To Floor John Danaher",
    "New Wave Jiu Jitsu": "New Wave Jiu Jitsu John Danaher",
}


@dataclass(frozen=True)
class ProductHit:
    title: str
    url: str
    score: float


def tokens(text: str) -> list[str]:
    text = text.lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return [t for t in text.split() if t and t not in STOPWORDS]


def score_match(folder: str, title: str, *, prefer_bundle: bool = False) -> float:
    folder_tokens = tokens(folder)
    title_tokens = tokens(title)
    if not folder_tokens or not title_tokens:
        return 0.0
    folder_set = set(folder_tokens)
    title_set = set(title_tokens)
    overlap = folder_set & title_set
    recall = len(overlap) / len(folder_set)
    precision = len(overlap) / len(title_set)
    seq = SequenceMatcher(None, " ".join(folder_tokens), " ".join(title_tokens)).ratio()
    score = (0.50 * recall) + (0.20 * precision) + (0.30 * seq)
    if "bundle" in title_set and "bundle" not in folder_set:
        # Season searches penalize bundles. The show-folder search prefers them.
        score += 0.18 if prefer_bundle else -0.18
    if folder_set <= title_set:
        score += 0.08
    return score


def clean_url(path: str) -> str:
    parsed = urlparse(path)
    return urlunparse(("https", "bjjfanatics.com", parsed.path, "", "", ""))


def search_products(query: str, user_agent: str = DEFAULT_USER_AGENT) -> list[dict[str, Any]]:
    params = urlencode(
        {
            "q": query,
            "resources[type]": "product",
            "resources[limit]": str(SEARCH_LIMIT),
        }
    )
    url = f"https://bjjfanatics.com/search/suggest.json?{params}"
    data = fetch_json(url, user_agent=user_agent)
    return data.get("resources", {}).get("results", {}).get("products", []) or []


def rank_products(
    folder: str,
    products: list[dict[str, Any]],
    min_score: float = MIN_SCORE,
    *,
    prefer_bundle: bool = False,
) -> list[ProductHit]:
    hits: list[ProductHit] = []
    seen: set[str] = set()
    for product in products:
        title = product.get("title") or ""
        handle = product.get("handle") or ""
        raw_url = product.get("url") or (f"/products/{handle}" if handle else "")
        if not title or not raw_url:
            continue
        url = clean_url(raw_url)
        score = score_match(folder, title, prefer_bundle=prefer_bundle)
        if score < min_score:
            continue
        if url in seen:
            continue
        seen.add(url)
        hits.append(ProductHit(title=title, url=url, score=score))
    hits.sort(key=lambda hit: hit.score, reverse=True)
    return hits


def csv_hint_url(folder: Path) -> str | None:
    name = folder.name.lower()
    resolved = str(folder.resolve()).lower()
    csv_paths: list[Path] = []
    seen: set[Path] = set()
    candidates = [parent / "bjjfanatics_matches.csv" for parent in (folder, *folder.parents)]
    candidates.append(Path(__file__).resolve().parents[2] / "bjjfanatics_matches.csv")
    for candidate in candidates:
        try:
            key = candidate.resolve()
        except OSError:
            key = candidate
        if key in seen:
            continue
        seen.add(key)
        if candidate.is_file():
            csv_paths.append(candidate)
    for csv_path in csv_paths:
        try:
            with csv_path.open(encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                for row in reader:
                    path = (row.get("folder_path") or "").strip()
                    url = (row.get("product_url") or "").strip()
                    if not path or not url:
                        continue
                    if path.lower() == resolved or Path(path).name.lower() == name:
                        return url
        except OSError:
            continue
    return None


def _merge_hits(primary: list[ProductHit], extra: list[ProductHit]) -> list[ProductHit]:
    by_url: dict[str, ProductHit] = {hit.url: hit for hit in primary}
    for hit in extra:
        current = by_url.get(hit.url)
        if current is None or hit.score > current.score:
            by_url[hit.url] = hit
    return sorted(by_url.values(), key=lambda hit: hit.score, reverse=True)


def lookup_candidates(
    folder_name: str,
    user_agent: str = DEFAULT_USER_AGENT,
    search=search_products,
    *,
    prefer_bundle: bool = False,
) -> list[ProductHit]:
    query = QUERY_OVERRIDES.get(folder_name, folder_name)
    products = search(query)
    hits = rank_products(folder_name, products, prefer_bundle=prefer_bundle)
    if prefer_bundle and not any("bundle" in hit.title.lower() for hit in hits):
        extra_query = query if query.lower().rstrip().endswith(" bundle") else f"{query} bundle"
        if extra_query != query:
            hits = _merge_hits(
                hits,
                rank_products(folder_name, search(extra_query), prefer_bundle=True),
            )
    if not hits and query != folder_name:
        products = search(folder_name)
        hits = rank_products(folder_name, products, prefer_bundle=prefer_bundle)
    return hits


def hit_from_url(folder_name: str, url: str, *, prefer_bundle: bool = False) -> ProductHit:
    slug = url.rstrip("/").split("/")[-1].replace("-", " ")
    return ProductHit(
        title=slug,
        url=url,
        score=score_match(folder_name, slug, prefer_bundle=prefer_bundle),
    )
