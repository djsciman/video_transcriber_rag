#!/usr/bin/env python3
"""Organize a local BJJ instructional folder using a product-page URL."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from bjj_organizer.errors import OrganizerError, UsageError  # noqa: E402
from bjj_organizer.httputil import DEFAULT_USER_AGENT  # noqa: E402
from bjj_organizer.pipeline import RuntimeOptions, run  # noqa: E402
from bjj_organizer.repair import FIX_LABELS, parse_repair_answer  # noqa: E402


def _configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            reconfigure(encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Scrape a BJJ Fanatics product page and reorganize a local instructional "
            "folder as a Jellyfin/TMM TV show (NFO, artwork, volumes with named chapters)."
        )
    )
    parser.add_argument("--folder", required=True, type=Path, help="Show root folder")
    parser.add_argument(
        "--url",
        action="append",
        dest="urls",
        default=[],
        help=(
            "Product URL for this instructional folder. "
            "If omitted, search BJJ Fanatics and ask to confirm."
        ),
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write files. Default is a dry-run that prints the plan and exits.",
    )
    parser.add_argument(
        "--season-order",
        default="",
        help="Comma-separated child folder names overriding publish-date season numbers",
    )
    parser.add_argument(
        "--container",
        choices=("keep", "mkv"),
        default="keep",
        help="keep original container (default) or remux/concat to mkv",
    )
    parser.add_argument(
        "--extras-policy",
        choices=("extras", "skip"),
        default="extras",
        help="Move unmatched leftover videos into extras/ (default) or leave them",
    )
    parser.add_argument(
        "--skip-chapters",
        action="store_true",
        help=(
            "Do not inject chapter markers. "
            "Segmented chapter files are still concatenated into volumes."
        ),
    )
    parser.add_argument("--ffmpeg", default=None, help="ffmpeg binary (default: PATH)")
    parser.add_argument("--ffprobe", default=None, help="ffprobe binary (default: PATH)")
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    parser.add_argument("--json", action="store_true", dest="json_out", help="Print plan JSON to stdout")
    parser.add_argument(
        "--repair",
        action="store_true",
        help="Scan the show, print a checklist, and apply only the fixes you confirm",
    )
    parser.add_argument(
        "--repair-steps",
        default="",
        help='With --repair, apply these steps without a prompt: all, or letters such as "A, C"',
    )
    return parser


def _parse_repair_steps(text: str) -> set[str] | None:
    if not text.strip():
        return None
    if text.strip().lower() == "all":
        return {"ALL"}
    chosen = parse_repair_answer(text, list(FIX_LABELS))
    if chosen is None:
        raise UsageError(f'--repair-steps must be all or letters such as "B, C". Got {text!r}.')
    return chosen


def main(argv: list[str] | None = None) -> int:
    _configure_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)
    order = [part.strip() for part in args.season_order.split(",") if part.strip()]
    try:
        repair_steps = _parse_repair_steps(args.repair_steps)
        options = RuntimeOptions(
            apply=args.apply,
            container=args.container,
            extras_policy=args.extras_policy,
            skip_chapters=args.skip_chapters,
            season_order=order or None,
            user_agent=args.user_agent,
            ffmpeg=args.ffmpeg,
            ffprobe=args.ffprobe,
            json_out=args.json_out,
            repair=args.repair or repair_steps is not None,
            repair_steps=repair_steps,
        )
        return run(args.folder, args.urls, options)
    except OrganizerError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return exc.exit_code


if __name__ == "__main__":
    sys.exit(main())
