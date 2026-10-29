#!/usr/bin/env python3
"""
Recursively process video files with panoscribe.
Preserves subdirectory structure in the output directory.

Speech is transcribed with on-screen OCR off by default. Chapter titles and
timestamps from the video container are written into the transcript JSON.
Each transcript also records the source video's file name in ``video_file``.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v", ".flv", ".wmv"}

# MAX_PATH includes the terminating NUL, so a normal Windows path of 260
# characters or more fails to open with FileNotFoundError. LongPathsEnabled
# is off on this machine. The \\?\ prefix bypasses that limit.
_WINDOWS_MAX_PATH = 260


def io_path(path: Path) -> Path:
    """Return ``path`` in a form this operating system can open and create.

    Short paths are unchanged. On Windows, a path of 260 characters or more
    is returned with the extended-length ``\\\\?\\`` prefix so later
    ``exists``, ``read_text``, and ``write_text`` calls see the same file.
    """
    if os.name != "nt":
        return path
    absolute = os.path.abspath(path)
    if absolute.startswith("\\\\?\\") or len(absolute) < _WINDOWS_MAX_PATH:
        return path
    if absolute.startswith("\\\\"):
        absolute = "\\\\?\\UNC\\" + absolute[2:]
    else:
        absolute = "\\\\?\\" + absolute
    return Path(absolute)


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
    video_path = io_path(video_path)
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


def _as_transcript_dict(data, output_path: Path) -> dict:
    if isinstance(data, list):
        data = {"segments": data}
    if not isinstance(data, dict):
        raise ValueError(f"Unexpected transcript JSON in {output_path}")
    return data


def _write_transcript(output_path: Path, data: dict) -> None:
    io_path(output_path).write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def write_chapters(output_path: Path, chapters: list[dict], video_file: str) -> None:
    """Insert chapters and the source video file name into a transcript JSON file.

    ``video_file`` is the video's file name, including its extension. The
    transcript's folder already mirrors the video's folder.
    """
    path = io_path(output_path)
    data = _as_transcript_dict(json.loads(path.read_text(encoding="utf-8")), path)

    segments = data.get("segments")
    rest = {
        key: value
        for key, value in data.items()
        if key not in ("video_file", "chapters", "segments")
    }
    ordered = {"video_file": video_file, "chapters": chapters}
    ordered.update(rest)
    if "segments" in data or segments is not None:
        ordered["segments"] = segments

    _write_transcript(path, ordered)


def stamp_video_file(output_path: Path, video_file: str) -> str:
    """Record ``video_file`` on an existing transcript without other edits.

    Returns ``written``, ``same``, or ``missing``. A transcript that already
    stores this file name is left untouched.
    """
    path = io_path(output_path)
    if not path.exists():
        return "missing"
    data = _as_transcript_dict(json.loads(path.read_text(encoding="utf-8")), path)
    if data.get("video_file") == video_file:
        return "same"

    ordered = {"video_file": video_file}
    for key, value in data.items():
        if key != "video_file":
            ordered[key] = value
    _write_transcript(path, ordered)
    return "written"


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

    source = io_path(input_path)
    target = io_path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "panoscribe", "transcribe",
        str(source),
        "--format", "json",
        "--output", str(target),
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

    if not target.exists():
        print(f"FAIL  {input_path} (transcript missing, chapters not written)")
        return False

    try:
        chapters = extract_chapters(source)
        write_chapters(target, chapters, input_path.name)
    except (subprocess.CalledProcessError, json.JSONDecodeError, ValueError, OSError) as e:
        detail = e.stderr if isinstance(e, subprocess.CalledProcessError) else e
        print(f"FAIL  {input_path} (chapters)")
        print(detail)
        return False

    print(f"CHAP  {len(chapters)} chapter(s) -> {output_path}")
    return True


def transcripts_by_video(input_dir: Path, output_dir: Path) -> list[tuple[Path, list[Path]]]:
    """Pair each transcript path with the videos that mirror onto it.

    Two videos that share a folder and a file name aside from the extension
    land on one transcript. Callers must not pick between them.
    """
    videos = [p for p in input_dir.rglob("*") if p.is_file() and is_video(p)]
    grouped: dict[Path, list[Path]] = {}
    order: list[Path] = []
    for video in videos:
        out = output_path_for(video, input_dir, output_dir)
        if out not in grouped:
            order.append(out)
            grouped[out] = []
        grouped[out].append(video)
    return [(out, grouped[out]) for out in order]


def stamp_transcripts(pairs: list[tuple[Path, list[Path]]]) -> None:
    """Write each video file name into its existing transcript, then stop."""
    written = same = missing = fail = 0
    for out, videos in pairs:
        if len(videos) != 1:
            fail += 1
            print(f"FAIL  {len(videos)} videos share {out}")
            for video in videos:
                print(f"      {video}")
            continue
        video = videos[0]
        try:
            result = stamp_video_file(out, video.name)
        except (json.JSONDecodeError, ValueError, OSError) as e:
            fail += 1
            print(f"FAIL  {out}")
            print(e)
            continue
        if result == "written":
            written += 1
            print(f"NAME  {video.name} -> {out}")
        elif result == "same":
            same += 1
        else:
            missing += 1
    print(
        f"\nDone. Named: {written}  Already named: {same}  "
        f"No transcript: {missing}  Failed: {fail}"
    )


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
        "--stamp-video-file",
        action="store_true",
        help="Write each video's file name into its existing transcript JSON and exit. Does not transcribe.",
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

    pairs = transcripts_by_video(args.input_dir, args.output_dir)
    video_count = sum(len(videos) for _out, videos in pairs)
    print(f"Found {video_count} video(s)")
    if args.stamp_video_file:
        stamp_transcripts(pairs)
        return

    paired = []
    for out, videos in pairs:
        if len(videos) != 1:
            print(f"FAIL  {len(videos)} videos share {out}")
            for video in videos:
                print(f"      {video}")
            continue
        paired.append((videos[0], out))
    existing = [(video, out) for video, out in paired if io_path(out).exists()]
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
        queue = [(video, out) for video, out in paired if not io_path(out).exists()]
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
