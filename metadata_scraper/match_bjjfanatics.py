"""Match local instructional folder names to BJJ Fanatics product pages."""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from difflib import SequenceMatcher
from typing import Any

ROOT = r"W:\BJJ Instructional Videos"
OUT_CSV = os.path.join(ROOT, "bjjfanatics_matches.csv")
SKIP_FOLDERS = {"scripts"}
SEARCH_LIMIT = 10
MIN_SCORE = 0.42
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
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

# Folder-name aliases when the local title is abbreviated vs the store listing.
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


def tokens(text: str) -> list[str]:
    text = text.lower().replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return [t for t in text.split() if t and t not in STOPWORDS]


def score_match(folder: str, title: str) -> float:
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
        score -= 0.18
    if folder_set <= title_set:
        score += 0.08
    return score


def clean_url(path: str) -> str:
    parsed = urllib.parse.urlparse(path)
    return urllib.parse.urlunparse(
        ("https", "bjjfanatics.com", parsed.path, "", "", "")
    )


def search_products(query: str) -> list[dict[str, Any]]:
    params = urllib.parse.urlencode(
        {
            "q": query,
            "resources[type]": "product",
            "resources[limit]": str(SEARCH_LIMIT),
        }
    )
    url = f"https://bjjfanatics.com/search/suggest.json?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data.get("resources", {}).get("results", {}).get("products", []) or []
        except urllib.error.HTTPError as exc:
            if exc.code in (429, 500, 502, 503) and attempt < 3:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise
        except (TimeoutError, urllib.error.URLError):
            if attempt < 3:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise
    return []


def collect_folders(include_subfolders: bool) -> list[tuple[str, str]]:
    """Return (folder_path, search_name) pairs.

    search_name is the folder name, or 'parent child' for subfolders so
    names like 'Season 1' still match the parent series.
    """
    items: list[tuple[str, str]] = []
    top_names = [
        name
        for name in sorted(os.listdir(ROOT), key=str.lower)
        if os.path.isdir(os.path.join(ROOT, name)) and name not in SKIP_FOLDERS
    ]
    for name in top_names:
        top_path = os.path.join(ROOT, name)
        items.append((top_path, name))
        if not include_subfolders:
            continue
        sub_names = [
            sub
            for sub in sorted(os.listdir(top_path), key=str.lower)
            if os.path.isdir(os.path.join(top_path, sub))
        ]
        for sub in sub_names:
            items.append((os.path.join(top_path, sub), f"{name} {sub}"))
    return items


def pick_best(folder: str, products: list[dict[str, Any]]) -> tuple[str, str, float]:
    best_url = ""
    best_title = ""
    best_score = 0.0
    for product in products:
        title = product.get("title") or ""
        handle = product.get("handle") or ""
        raw_url = product.get("url") or (f"/products/{handle}" if handle else "")
        if not title or not raw_url:
            continue
        s = score_match(folder, title)
        if s > best_score:
            best_score = s
            best_title = title
            best_url = clean_url(raw_url)
    if best_score < MIN_SCORE:
        return "", best_title, best_score
    return best_url, best_title, best_score


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Match local instructional folders to BJJ Fanatics product pages."
    )
    parser.add_argument(
        "--subfolders",
        action="store_true",
        help="Also match one level of subfolders under each top-level folder.",
    )
    args = parser.parse_args()

    folders = collect_folders(include_subfolders=args.subfolders)

    rows: list[dict[str, str]] = []
    for i, (folder_path, search_name) in enumerate(folders, start=1):
        leaf_name = os.path.basename(folder_path)
        query = QUERY_OVERRIDES.get(leaf_name) or QUERY_OVERRIDES.get(search_name, search_name)
        print(f"[{i}/{len(folders)}] Searching: {search_name}")
        try:
            products = search_products(query)
            url, title, s = pick_best(search_name, products)
            if not url and query != search_name:
                products = search_products(search_name)
                url, title, s = pick_best(search_name, products)
            if not url and search_name != leaf_name:
                products = search_products(leaf_name)
                url, title, s = pick_best(leaf_name, products)
        except Exception as exc:  # noqa: BLE001
            print(f"  ERROR: {exc}")
            url, title, s = "", "", 0.0
        print(f"  -> {url or '(no match)'}  [{title}] score={s:.3f}")
        rows.append(
            {
                "folder_path": folder_path,
                "product_url": url,
            }
        )
        time.sleep(0.35)

    with open(OUT_CSV, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=["folder_path", "product_url"])
        writer.writeheader()
        writer.writerows(rows)

    matched = sum(1 for row in rows if row["product_url"])
    print(f"\nWrote {len(rows)} rows ({matched} matched) to {OUT_CSV}")


if __name__ == "__main__":
    main()
