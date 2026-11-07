"""Match local instructional folder names to BJJ Fanatics product pages."""

from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path
from typing import Any, Callable

from .organizer.fanatics_search import lookup_candidates, search_products

SKIP_FOLDERS = {"scripts"}
SearchFn = Callable[[str], list[dict[str, Any]]]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Match local instructional folders to BJJ Fanatics product pages."
    )
    parser.add_argument(
        "--library",
        type=Path,
        required=True,
        help="Library root of instructional folders.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="CSV path to write (folder_path, product_url).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-search folders that already have a product URL in the output CSV.",
    )
    parser.add_argument(
        "--subfolders",
        action="store_true",
        help="Also match one level of subfolders under each top-level folder.",
    )
    return parser


def collect_folders(library: Path, include_subfolders: bool) -> list[tuple[Path, str]]:
    """Return (folder_path, search_name) pairs.

    search_name is the folder name, or 'parent child' for subfolders so
    names like 'Season 1' still match the parent series.
    """
    items: list[tuple[Path, str]] = []
    if not library.is_dir():
        return items
    tops = sorted(
        (
            child
            for child in library.iterdir()
            if child.is_dir() and child.name not in SKIP_FOLDERS
        ),
        key=lambda path: path.name.lower(),
    )
    for top in tops:
        items.append((top, top.name))
        if not include_subfolders:
            continue
        subs = sorted(
            (child for child in top.iterdir() if child.is_dir()),
            key=lambda path: path.name.lower(),
        )
        for sub in subs:
            items.append((sub, f"{top.name} {sub.name}"))
    return items


def _load_existing(csv_path: Path) -> dict[str, str]:
    if not csv_path.is_file():
        return {}
    found: dict[str, str] = {}
    try:
        with csv_path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                path = (row.get("folder_path") or "").strip()
                url = (row.get("product_url") or "").strip()
                if not path:
                    continue
                try:
                    key = str(Path(path).resolve())
                except OSError:
                    key = path
                found[key] = url
    except OSError:
        return {}
    return found


def main(
    argv: list[str] | None = None,
    *,
    search: SearchFn | None = None,
) -> int:
    args = build_parser().parse_args(argv)
    live = search is None
    search_fn = search or search_products
    folders = collect_folders(args.library, include_subfolders=args.subfolders)
    existing = {} if args.force else _load_existing(args.output)
    rows: list[dict[str, str]] = []
    for i, (folder_path, search_name) in enumerate(folders, start=1):
        key = str(folder_path.resolve())
        prior = existing.get(key, "").strip()
        if prior:
            print(f"[{i}/{len(folders)}] Skipping (existing URL): {search_name}")
            print(f"  -> {prior}")
            rows.append({"folder_path": key, "product_url": prior})
            continue
        print(f"[{i}/{len(folders)}] Searching: {search_name}")
        url = ""
        title = ""
        score = 0.0
        try:
            hits = lookup_candidates(search_name, search=search_fn)
            if hits:
                url, title, score = hits[0].url, hits[0].title, hits[0].score
        except Exception as exc:  # noqa: BLE001
            print(f"  ERROR: {exc}")
        print(f"  -> {url or '(no match)'}  [{title}] score={score:.3f}")
        rows.append({"folder_path": key, "product_url": url})
        if live:
            time.sleep(0.35)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["folder_path", "product_url"])
        writer.writeheader()
        writer.writerows(rows)

    matched = sum(1 for row in rows if row["product_url"])
    print(f"\nWrote {len(rows)} rows ({matched} matched) to {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
