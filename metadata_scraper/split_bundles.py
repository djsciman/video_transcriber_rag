#!/usr/bin/env python3
"""Split bundle shows so each instructional is its own one-season show."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from bjj_organizer.errors import OrganizerError  # noqa: E402
from bjj_organizer.httputil import DEFAULT_USER_AGENT  # noqa: E402
from bjj_organizer.split_bundles import (  # noqa: E402
    apply_bundles,
    default_resolve_product,
    discover_bundles,
    format_report,
    has_problems,
    plan_bundles,
)


def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Move each season of a bundle show into its own show folder with a single "
            "Season 01, and rewrite tvshow, season, and episode NFO."
        )
    )
    parser.add_argument(
        "--library",
        type=Path,
        default=None,
        help="Library root to scan. Defaults to the current working directory.",
    )
    parser.add_argument(
        "--folder",
        type=Path,
        default=None,
        help="Split this bundle show only, instead of scanning the library",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Move files and write NFO. Default is a dry-run that prints the plan.",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="Do not fetch Fanatics. Name each show from the bundle namedseason.",
    )
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    return parser


def main(argv: list[str] | None = None) -> int:
    _configure_stdio()
    args = build_parser().parse_args(argv)
    library = args.library if args.library is not None else Path.cwd()
    try:
        shows, note = discover_bundles(library, args.folder)
    except OrganizerError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return exc.exit_code
    if note:
        sys.stdout.write(note + "\n")
        return 0
    resolve = None if args.offline else default_resolve_product(args.user_agent)
    try:
        bundles = plan_bundles(shows, offline=args.offline, resolve_product=resolve)
    except OrganizerError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return exc.exit_code
    if args.apply:
        apply_bundles(bundles)
    sys.stdout.write(format_report(bundles, applied=args.apply))
    if has_problems(bundles):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
