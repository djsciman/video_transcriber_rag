#!/usr/bin/env python3
"""Report how complete a video library is against the organizer rubric.

Prints aggregate percents, then writes a markdown drill-down of every video
or instructional that does not meet a check. The drill-down is written next
to this script as completeness_scan_results_<date-time>.md unless --output
is set.

A video meets the combined-volume check when it is one file per volume, not
a per-chapter clip (Fanatics ``id-vol-ch-`` names, ``NN.NN - title`` names,
or a Jellyfin SxxEyy file whose title is not a Volume/DVD name and whose
container has fewer than two chapters). Volume part files (VOL1PT1) are
still uncombined.

Named chapters means two or more container chapters with at least one title
that is not a generic ``Chapter N``.

Video NFO means a sidecar ``.nfo`` next to the video. Instructional NFO
means ``tvshow.nfo`` in that show folder under the library root.

Playback uses ffprobe to open the file, then ffmpeg decodes one second at
the start and one second at the midpoint. Use --skip-decode to open only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from . import batch_panoscribe
from .batch_panoscribe import io_path, output_path_for, walk_videos
from .organizer.layout import IGNORE_DIR_NAMES
from .organizer.naming import VOL, parse_video

_HERE = Path(__file__).resolve().parent
_REPO = _HERE.parent if _HERE.name == "bjj_pipeline" else _HERE

InspectVideo = Callable[[Path], "VideoInspection"]

GENERIC_CHAPTER_TITLE = re.compile(
    r"^(chapter(\s+\d+)?|untitled|continued)$",
    re.IGNORECASE,
)
SKIP_INSTRUCTIONAL_NAMES = {name.lower() for name in IGNORE_DIR_NAMES} | {"scripts"}
DECODE_SECONDS = 1.0
PROBE_TIMEOUT = 60
DECODE_TIMEOUT = 120


@dataclass
class VideoInspection:
    """Container open, chapters, and optional decode result for one file."""

    open_ok: bool
    open_error: str = ""
    duration: float | None = None
    chapters: list[dict] = field(default_factory=list)
    decode_ok: bool = True
    decode_error: str = ""


@dataclass
class Gap:
    """One library item that does not meet a rubric check."""

    path: str
    notes: list[str] = field(default_factory=list)


@dataclass
class ScanReport:
    scanned_at: str
    library: Path
    transcripts: Path
    video_count: int
    instructional_count: int
    combined_count: int
    named_chapters_count: int
    video_nfo_count: int
    instructional_nfo_count: int
    playback_error_count: int
    missing_transcript_count: int
    split_by_chapters: list[Gap]
    missing_named_chapters: list[Gap]
    missing_video_nfo: list[Gap]
    missing_instructional_nfo: list[Gap]
    playback_errors: list[Gap]
    missing_transcripts: list[Gap]


def percent(part: int, whole: int) -> str:
    if whole == 0:
        return "n/a"
    return f"{100.0 * part / whole:.1f}%"


def _logical_rel(path: Path, root: Path) -> Path:
    try:
        return path.relative_to(io_path(root))
    except ValueError:
        return Path(os.path.relpath(path, start=os.path.abspath(root)))


def display_rel(path: Path, root: Path) -> str:
    return str(_logical_rel(path, root))


def list_instructionals(library: Path) -> list[Path]:
    """Return immediate show folders under the library root."""
    root = io_path(library)
    if not root.is_dir():
        return []
    found: list[Path] = []
    for child in sorted(root.iterdir(), key=lambda p: p.name.lower()):
        if not child.is_dir() or child.name.startswith("."):
            continue
        if child.name.lower() in SKIP_INSTRUCTIONAL_NAMES:
            continue
        found.append(library / child.name)
    return found


def has_nfo(path: Path) -> bool:
    return io_path(path).is_file()


def video_nfo_path(video: Path) -> Path:
    return video.with_suffix(".nfo")


def transcript_exists(path: Path) -> bool:
    return io_path(path).is_file()


def is_generic_chapter_title(title: str) -> bool:
    return not str(title or "").strip() or bool(
        GENERIC_CHAPTER_TITLE.fullmatch(str(title).strip())
    )


def has_named_chapters(chapters: list[dict]) -> bool:
    if len(chapters) < 2:
        return False
    return any(not is_generic_chapter_title(ch.get("title") or "") for ch in chapters)


def has_volume_token(text: str) -> bool:
    return bool(VOL.search(text or ""))


def is_combined_volume(video: Path, chapters: list[dict]) -> bool:
    """True when the file is a volume, not a per-chapter clip."""
    parsed = parse_video(video)
    if parsed.is_segmented_name:
        return False
    if parsed.part_number is not None:
        return False
    if len(chapters) >= 2:
        return True
    stem = video.stem
    title = parsed.local_title or ""
    if has_volume_token(stem) or has_volume_token(title):
        return True
    if parsed.already_named:
        return False
    return True


def split_reason(video: Path, chapters: list[dict]) -> str:
    parsed = parse_video(video)
    if parsed.is_segmented_name:
        if parsed.volume_number is not None and parsed.chapter_number is not None:
            return (
                f"segmented filename (volume {parsed.volume_number} "
                f"chapter {parsed.chapter_number})"
            )
        return "segmented filename"
    if parsed.part_number is not None:
        return f"volume part file (part {parsed.part_number})"
    if parsed.already_named:
        title = parsed.local_title or video.stem
        return (
            f"Jellyfin episode titled {title!r} with "
            f"{len(chapters)} container chapter(s)"
        )
    return "not a combined volume"


def _chapter_bound(chapter: dict, key: str) -> float:
    raw = chapter.get(f"{key}_time")
    if raw is not None and raw != "N/A":
        return float(raw)
    ticks = float(chapter.get(key) or 0)
    num, den = str(chapter.get("time_base") or "1/1").split("/", 1)
    return ticks * float(num) / float(den)


def _chapters_from_payload(payload: dict) -> list[dict]:
    raw: list[dict] = []
    for index, chapter in enumerate(payload.get("chapters") or [], start=1):
        tags = chapter.get("tags") or {}
        title = ""
        for key, value in tags.items():
            if key.lower() == "title" and value is not None and str(value).strip():
                title = str(value).strip()
                break
        if not title:
            title = f"Chapter {index}"
        start = _chapter_bound(chapter, "start")
        end = _chapter_bound(chapter, "end")
        raw.append({"title": title, "start": start, "end": end})
    return batch_panoscribe.normalize_container_chapters(raw)


def default_probe(video: Path) -> VideoInspection:
    path = io_path(video)
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        "-show_chapters",
        str(path),
    ]
    try:
        result = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=PROBE_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return VideoInspection(open_ok=False, open_error="ffprobe timed out")
    except OSError as exc:
        return VideoInspection(open_ok=False, open_error=str(exc))

    stderr = (result.stderr or "").strip()
    if result.returncode != 0:
        return VideoInspection(
            open_ok=False,
            open_error=stderr or f"ffprobe exited {result.returncode}",
        )
    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        return VideoInspection(open_ok=False, open_error=f"ffprobe JSON invalid: {exc}")

    streams = payload.get("streams") or []
    if not streams:
        return VideoInspection(
            open_ok=False,
            open_error=stderr or "ffprobe reported no streams",
            chapters=_chapters_from_payload(payload),
        )
    duration = None
    raw_duration = (payload.get("format") or {}).get("duration")
    if raw_duration not in (None, "", "N/A"):
        try:
            duration = float(raw_duration)
        except ValueError:
            duration = None
    error = stderr
    return VideoInspection(
        open_ok=True,
        open_error=error,
        duration=duration,
        chapters=_chapters_from_payload(payload),
    )


def default_decode_sample(video: Path, start: float, seconds: float) -> tuple[bool, str]:
    path = io_path(video)
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-nostdin",
        "-v",
        "error",
        "-xerror",
        "-ss",
        f"{start:.3f}",
        "-t",
        f"{seconds:.3f}",
        "-i",
        str(path),
        "-f",
        "null",
        "-",
    ]
    try:
        result = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=DECODE_TIMEOUT,
        )
    except subprocess.TimeoutExpired:
        return False, f"ffmpeg timed out decoding {seconds:.1f}s at {start:.1f}s"
    except OSError as exc:
        return False, str(exc)
    stderr = (result.stderr or "").strip()
    if result.returncode != 0:
        return False, stderr or f"ffmpeg exited {result.returncode} at {start:.1f}s"
    if stderr:
        return False, stderr
    return True, ""


def inspect_with_tools(video: Path, *, skip_decode: bool) -> VideoInspection:
    inspection = default_probe(video)
    if skip_decode or not inspection.open_ok:
        return inspection
    starts = [0.0]
    if inspection.duration is not None and inspection.duration > DECODE_SECONDS * 3:
        starts.append(inspection.duration / 2.0)
    errors: list[str] = []
    for start in starts:
        ok, error = default_decode_sample(video, start, DECODE_SECONDS)
        if not ok:
            errors.append(error)
    if errors:
        inspection.decode_ok = False
        inspection.decode_error = "; ".join(errors)
    return inspection


def plays_ok(inspection: VideoInspection) -> bool:
    return inspection.open_ok and inspection.decode_ok


def playback_notes(inspection: VideoInspection) -> list[str]:
    notes: list[str] = []
    if not inspection.open_ok:
        notes.append(inspection.open_error or "file did not open")
    elif inspection.open_error:
        notes.append(inspection.open_error)
    if not inspection.decode_ok:
        notes.append(inspection.decode_error or "decode failed")
    return notes


def named_chapter_notes(chapters: list[dict]) -> list[str]:
    if not chapters:
        return ["0 container chapters"]
    titles = [str(ch.get("title") or "").strip() or "(empty)" for ch in chapters]
    preview = ", ".join(titles[:8])
    if len(titles) > 8:
        preview += f", … ({len(titles)} total)"
    if len(chapters) < 2:
        return [f"{len(chapters)} container chapter(s): {preview}"]
    return [f"{len(chapters)} generic chapter titles: {preview}"]


def scan(
    library: Path,
    transcripts: Path,
    *,
    inspect_video: InspectVideo | None = None,
    skip_decode: bool = False,
    clock: Callable[[], datetime] | None = None,
) -> ScanReport:
    library = Path(library)
    transcripts = Path(transcripts)
    when = (clock or datetime.now)()
    inspect = inspect_video or (lambda path: inspect_with_tools(path, skip_decode=skip_decode))

    videos = walk_videos(library)
    instructionals = list_instructionals(library)

    split_by_chapters: list[Gap] = []
    missing_named_chapters: list[Gap] = []
    missing_video_nfo: list[Gap] = []
    playback_errors: list[Gap] = []
    missing_transcripts: list[Gap] = []

    combined_count = 0
    named_count = 0
    video_nfo_count = 0
    playback_error_count = 0
    missing_transcript_count = 0

    total = len(videos)
    for index, video in enumerate(videos, start=1):
        if index == 1 or index % 25 == 0 or index == total:
            print(f"Scanning videos {index}/{total}", flush=True)
        rel = display_rel(video, library)
        logical = library / _logical_rel(video, library)
        inspection = inspect(video)
        chapters = inspection.chapters if inspection.open_ok else []

        if is_combined_volume(logical, chapters):
            combined_count += 1
        else:
            split_by_chapters.append(Gap(rel, [split_reason(logical, chapters)]))

        if has_named_chapters(chapters):
            named_count += 1
        else:
            notes = named_chapter_notes(chapters)
            if not inspection.open_ok:
                notes = [inspection.open_error or "file did not open"] + notes
            missing_named_chapters.append(Gap(rel, notes))

        nfo = video_nfo_path(logical)
        if has_nfo(nfo):
            video_nfo_count += 1
        else:
            missing_video_nfo.append(Gap(rel, ["no sidecar .nfo"]))

        if plays_ok(inspection):
            pass
        else:
            playback_error_count += 1
            playback_errors.append(Gap(rel, playback_notes(inspection)))

        dest = output_path_for(logical, library, transcripts)
        if transcript_exists(dest):
            pass
        else:
            missing_transcript_count += 1
            missing_transcripts.append(
                Gap(rel, [f"missing {display_rel(dest, transcripts)}"])
            )

    missing_instructional_nfo: list[Gap] = []
    instructional_nfo_count = 0
    for folder in instructionals:
        nfo = folder / "tvshow.nfo"
        if has_nfo(nfo):
            instructional_nfo_count += 1
        else:
            missing_instructional_nfo.append(
                Gap(display_rel(folder, library), ["no tvshow.nfo"])
            )

    return ScanReport(
        scanned_at=when.strftime("%Y-%m-%d %H:%M:%S"),
        library=library,
        transcripts=transcripts,
        video_count=len(videos),
        instructional_count=len(instructionals),
        combined_count=combined_count,
        named_chapters_count=named_count,
        video_nfo_count=video_nfo_count,
        instructional_nfo_count=instructional_nfo_count,
        playback_error_count=playback_error_count,
        missing_transcript_count=missing_transcript_count,
        split_by_chapters=split_by_chapters,
        missing_named_chapters=missing_named_chapters,
        missing_video_nfo=missing_video_nfo,
        missing_instructional_nfo=missing_instructional_nfo,
        playback_errors=playback_errors,
        missing_transcripts=missing_transcripts,
    )


def _gap_block(title: str, gaps: list[Gap]) -> list[str]:
    lines = [f"## {title}", "", f"{len(gaps)} item(s).", ""]
    if not gaps:
        lines.append("None.")
        lines.append("")
        return lines
    for gap in gaps:
        lines.append(f"- `{gap.path}`")
        for note in gap.notes:
            lines.append(f"  - {note}")
    lines.append("")
    return lines


def format_aggregate(report: ScanReport) -> str:
    v = report.video_count
    i = report.instructional_count
    rows = [
        (
            "Videos combined into volumes (not split by chapters)",
            report.combined_count,
            v,
        ),
        ("Videos with named chapters", report.named_chapters_count, v),
        ("Videos with NFO metadata", report.video_nfo_count, v),
        ("Instructionals with NFO metadata", report.instructional_nfo_count, i),
        (
            "Videos that play without errors",
            v - report.playback_error_count,
            v,
        ),
        (
            "Videos with corresponding transcripts",
            v - report.missing_transcript_count,
            v,
        ),
    ]
    lines = [
        f"Scanned {report.scanned_at}",
        f"Video library: {report.library}",
        f"Transcript root: {report.transcripts}",
        f"Videos: {v}",
        f"Instructionals: {i}",
        "",
    ]
    for label, part, whole in rows:
        lines.append(f"{label}: {part}/{whole} ({percent(part, whole)})")
    return "\n".join(lines)


def format_markdown(report: ScanReport) -> str:
    v = report.video_count
    i = report.instructional_count
    lines = [
        "# Completeness scan",
        "",
        f"Scanned: {report.scanned_at}",
        "",
        f"- Video library: `{report.library}`",
        f"- Transcript root: `{report.transcripts}`",
        f"- Videos: {v}",
        f"- Instructionals: {i}",
        "",
        "## Aggregate",
        "",
        "| Check | Count | Total | Percent |",
        "| --- | ---: | ---: | ---: |",
        (
            f"| Videos combined into volumes (not split by chapters) | "
            f"{report.combined_count} | {v} | {percent(report.combined_count, v)} |"
        ),
        (
            f"| Videos with named chapters | {report.named_chapters_count} | "
            f"{v} | {percent(report.named_chapters_count, v)} |"
        ),
        (
            f"| Videos with NFO metadata | {report.video_nfo_count} | "
            f"{v} | {percent(report.video_nfo_count, v)} |"
        ),
        (
            f"| Instructionals with NFO metadata | "
            f"{report.instructional_nfo_count} | {i} | "
            f"{percent(report.instructional_nfo_count, i)} |"
        ),
        (
            f"| Videos that play without errors | "
            f"{v - report.playback_error_count} | {v} | "
            f"{percent(v - report.playback_error_count, v)} |"
        ),
        (
            f"| Videos with corresponding transcripts | "
            f"{v - report.missing_transcript_count} | {v} | "
            f"{percent(v - report.missing_transcript_count, v)} |"
        ),
        "",
        "Every aggregate percent is a meeting rate. Items below do not meet "
        "the rubric.",
        "",
    ]
    lines.extend(_gap_block("Videos split by chapters (not combined)", report.split_by_chapters))
    lines.extend(_gap_block("Videos without named chapters", report.missing_named_chapters))
    lines.extend(_gap_block("Videos without NFO metadata", report.missing_video_nfo))
    lines.extend(
        _gap_block(
            "Instructionals without NFO metadata",
            report.missing_instructional_nfo,
        )
    )
    lines.extend(
        _gap_block(
            "Videos that do not play or open with errors",
            report.playback_errors,
        )
    )
    lines.extend(
        _gap_block(
            "Videos without corresponding transcripts",
            report.missing_transcripts,
        )
    )
    return "\n".join(lines).rstrip() + "\n"


def default_output_path(when: datetime, repo: Path | None = None) -> Path:
    stamp = when.strftime("%Y-%m-%d_%H%M%S")
    return (repo or _REPO) / f"completeness_scan_results_{stamp}.md"


def write_report(report: ScanReport, output_path: Path) -> Path:
    dest = io_path(output_path)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(format_markdown(report), encoding="utf-8")
    return output_path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scan a video library and transcript tree for completeness."
    )
    parser.add_argument(
        "library",
        type=Path,
        help="Video library root (instructional show folders)",
    )
    parser.add_argument(
        "transcripts",
        type=Path,
        help="Transcript root that mirrors the video tree as JSON",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=(
            "Markdown drill-down path. Default: "
            "completeness_scan_results_<date-time>.md in the repo root"
        ),
    )
    parser.add_argument(
        "--skip-decode",
        action="store_true",
        help="Open each file with ffprobe only; do not decode samples with ffmpeg",
    )
    return parser


def run(
    library: Path,
    transcripts: Path,
    *,
    output: Path | None = None,
    skip_decode: bool = False,
    inspect_video: InspectVideo | None = None,
    clock: Callable[[], datetime] | None = None,
    require_tools: bool | None = None,
) -> int:
    library = Path(library)
    transcripts = Path(transcripts)
    if not io_path(library).is_dir():
        print(f"Error: {library} is not a directory", file=sys.stderr)
        return 1
    if not io_path(transcripts).is_dir():
        print(f"Error: {transcripts} is not a directory", file=sys.stderr)
        return 1

    needs_tools = inspect_video is None
    if require_tools is None:
        require_tools = needs_tools
    if require_tools:
        if not batch_panoscribe.command_available("ffprobe"):
            print("Error: ffprobe is not available", file=sys.stderr)
            return 1
        if not skip_decode and not batch_panoscribe.command_available("ffmpeg"):
            print("Error: ffmpeg is not available", file=sys.stderr)
            return 1

    when = (clock or datetime.now)()
    report = scan(
        library,
        transcripts,
        inspect_video=inspect_video,
        skip_decode=skip_decode,
        clock=lambda: when,
    )
    print(format_aggregate(report))
    dest = output if output is not None else default_output_path(when)
    written = write_report(report, dest)
    print(f"\nWrote {written}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return run(
        args.library,
        args.transcripts,
        output=args.output,
        skip_decode=args.skip_decode,
    )


if __name__ == "__main__":
    sys.exit(main())
