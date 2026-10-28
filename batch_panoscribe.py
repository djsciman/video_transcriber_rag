#!/usr/bin/env python3
"""
Recursively process video files with panoscribe.
Preserves subdirectory structure in the output directory.

Speech is transcribed with on-screen OCR off by default. Chapter titles and
timestamps from the video container are written into the transcript JSON.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v", ".flv", ".wmv"}


def is_video(path: Path) -> bool:
    return path.suffix.lower() in VIDEO_EXTS


def _chapter_seconds(chapter: dict, key: str) -> float:
    """Return a chapter boundary in seconds.

    Prefer ffprobe's ``start_time`` / ``end_time`` (already seconds). Fall
    back to the integer tick divided by ``time_base``.
    """
    raw = chapter.get(f"{key}_time")
    if raw is not None and raw != "N/A":
        return float(raw)
    ticks = float(chapter[key])
    num, den = str(chapter.get("time_base") or "1/1").split("/", 1)
    return ticks * float(num) / float(den)


def _chapter_title(chapter: dict, index: int) -> str:
    tags = chapter.get("tags") or {}
    for key, value in tags.items():
        if key.lower() == "title" and value is not None and str(value).strip():
            return str(value).strip()
    return f"Chapter {index}"


def extract_chapters(video_path: Path) -> list[dict]:
    """Read container chapters via ffprobe.

    Each entry is ``{"title", "start", "end"}`` with times in seconds,
    matching transcript segment timestamps.
    """
    cmd = [
        "ffprobe",
        "-v", "error",
        "-print_format", "json",
        "-show_chapters",
        str(video_path),
    ]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    payload = json.loads(result.stdout or "{}")
    chapters = []
    for index, chapter in enumerate(payload.get("chapters") or [], start=1):
        chapters.append({
            "title": _chapter_title(chapter, index),
            "start": _chapter_seconds(chapter, "start"),
            "end": _chapter_seconds(chapter, "end"),
        })
    return chapters


def write_chapters(output_path: Path, chapters: list[dict]) -> None:
    """Insert ``chapters`` at the top of a panoscribe transcript JSON file."""
    data = json.loads(output_path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        data = {"segments": data}
    if not isinstance(data, dict):
        raise ValueError(f"Unexpected transcript JSON in {output_path}")

    segments = data.get("segments")
    rest = {key: value for key, value in data.items() if key not in ("chapters", "segments")}
    ordered = {"chapters": chapters}
    ordered.update(rest)
    if "segments" in data or segments is not None:
        ordered["segments"] = segments

    output_path.write_text(
        json.dumps(ordered, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def output_path_for(video: Path, input_dir: Path, output_dir: Path) -> Path:
    """JSON path that mirrors ``video``'s location under ``input_dir``."""
    rel = video.relative_to(input_dir)
    return output_dir / rel.with_suffix(".json")


def ask_overwrite(existing: list[tuple[Path, Path]]) -> bool:
    """Ask once whether existing transcripts should be overwritten.

    Empty input, ``n``, and ``no`` mean no. A non-interactive stdin also
    means no, so a piped run cannot wipe transcripts by accident.
    """
    print(f"\nAlready processed: {len(existing)}")
    for video, _out in existing:
        print(f"  {video}")

    if not sys.stdin.isatty():
        print("Not a terminal; leaving existing transcripts and processing new videos only.")
        return False

    while True:
        try:
            answer = input("Overwrite them and reprocess every video? [y/N]: ").strip().lower()
        except EOFError:
            print()
            return False
        if answer in ("y", "yes"):
            return True
        if answer in ("", "n", "no"):
            return False
        print("Please answer y or n.")


def process_file(
    input_path: Path,
    output_path: Path,
    ocr: bool,
    transcribe: bool,
) -> bool:
    if not transcribe:
        print(f"SKIP  {input_path} (transcription disabled; panoscribe has no OCR-only mode)")
        return True

    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "panoscribe", "transcribe",
        str(input_path),
        "--format", "json",
        "--output", str(output_path),
    ]
    cmd.append("--ocr" if ocr else "--no-ocr")

    print(f"START {input_path} (ocr={'on' if ocr else 'off'})")
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"OK    {output_path}")
    except subprocess.CalledProcessError as e:
        print(f"FAIL  {input_path}")
        print(e.stderr)
        return False

    if not output_path.exists():
        print(f"FAIL  {input_path} (transcript missing, chapters not written)")
        return False

    try:
        chapters = extract_chapters(input_path)
        write_chapters(output_path, chapters)
    except (subprocess.CalledProcessError, json.JSONDecodeError, ValueError, OSError) as e:
        detail = e.stderr if isinstance(e, subprocess.CalledProcessError) else e
        print(f"FAIL  {input_path} (chapters)")
        print(detail)
        return False

    print(f"CHAP  {len(chapters)} chapter(s) -> {output_path}")
    return True


def main():
    parser = argparse.ArgumentParser(description="Batch panoscribe on a directory tree.")
    parser.add_argument("input_dir", type=Path, help="Root directory of videos")
    parser.add_argument("output_dir", type=Path, help="Root directory for JSON outputs")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing transcripts without asking",
    )
    parser.add_argument(
        "--ocr",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Enable or disable on-screen OCR (default: disabled). Passes --ocr/--no-ocr to panoscribe.",
    )
    parser.add_argument(
        "--transcribe",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Enable or disable speech transcription (default: enabled). "
             "panoscribe has no OCR-only mode; --no-transcribe skips the file.",
    )
    args = parser.parse_args()

    if not args.input_dir.is_dir():
        print(f"Error: {args.input_dir} is not a directory", file=sys.stderr)
        sys.exit(1)

    videos = [p for p in args.input_dir.rglob("*") if p.is_file() and is_video(p)]
    print(f"Found {len(videos)} video(s)")

    paired = [
        (video, output_path_for(video, args.input_dir, args.output_dir))
        for video in videos
    ]
    existing = [(video, out) for video, out in paired if out.exists()]
    if not existing:
        overwrite = False
    elif args.force:
        overwrite = True
        print(f"Already processed: {len(existing)} (overwriting because --force)")
    else:
        overwrite = ask_overwrite(existing)

    if overwrite:
        queue = paired
        skipped = 0
    else:
        queue = [(video, out) for video, out in paired if not out.exists()]
        skipped = len(existing)

    if not queue:
        print("\nNothing to process.")
        print(f"\nDone. Processed: 0  Failed: 0  Skipped: {skipped}")
        return

    ok = fail = 0
    for video, out in queue:
        if process_file(
            video,
            out,
            ocr=args.ocr,
            transcribe=args.transcribe,
        ):
            ok += 1
        else:
            fail += 1

    print(f"\nDone. Processed: {ok}  Failed: {fail}  Skipped: {skipped}")


if __name__ == "__main__":
    main()
