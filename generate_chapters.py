"""Write a chapter-markers CSV from title-card color frames, and embed it.

Each frame find_color_frames accepts opens a chapter. The chapter runs
until the next match, and the last chapter runs until the end of the
video. When the first match is more than a second in, a lead-in chapter
starts at 00:00:00.000. A chapter shorter than 10 seconds is then merged
into the chapter after it. A short final chapter is merged into the one
before it.

The file is written next to the video as <video stem>_chapters.csv:

  Chapter,StartTimestamp,EndTimestamp
  Chapter 1,00:00:00.000,00:03:39.040
  Chapter 2,00:03:39.040,00:08:59.120

Color matching uses the same HSV tolerances as find_color_frames.

Embedding reads that CSV together with <video stem>_chapternames.csv and
writes the named chapters into the video. Streams are copied, not
re-encoded. The original file is replaced only after the new chapters
probe back correctly.

  python generate_chapters.py --apply
  python generate_chapters.py --apply "Volume 1.mp4"
"""

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import find_color_frames


# A match this close to 00:00:00 is the opening chapter, not a second one.
LEAD_IN_SECONDS = 1.0
# Chapters shorter than this are merged into the following chapter.
MIN_CHAPTER_SECONDS = 10.0


def video_duration(video):
    probe = shutil.which("ffprobe")
    if probe is None:
        sys.exit("ffprobe not found on PATH")
    out = subprocess.run(
        [
            probe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            video,
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if not out or out == "N/A":
        sys.exit("ffprobe returned no duration")
    return float(out)


def chapter_rows(matches, duration):
    """Build (title, start, end) rows from match timestamps in seconds."""
    starts = [timestamp for timestamp, _pixel in matches]
    if not starts:
        return []
    if starts[0] > LEAD_IN_SECONDS:
        starts.insert(0, 0.0)
    rows = []
    for index, start in enumerate(starts):
        end = starts[index + 1] if index + 1 < len(starts) else duration
        rows.append((f"Chapter {index + 1}", start, end))
    return rows


def merge_short_chapters(rows, minimum=MIN_CHAPTER_SECONDS):
    """Drop chapters shorter than `minimum` by joining them to the next one.

    The merged chapter keeps the earlier start and the later end. Several
    short chapters in a row collapse forward until the result is long enough
    or only the final chapter remains. A short final chapter joins the one
    before it. Titles are renumbered.
    """
    pending = list(rows)
    merged = []
    index = 0
    while index < len(pending):
        title, start, end = pending[index]
        if end - start < minimum and index + 1 < len(pending):
            next_title, _next_start, next_end = pending[index + 1]
            pending[index + 1] = (next_title, start, next_end)
            index += 1
            continue
        merged.append((title, start, end))
        index += 1
    if len(merged) >= 2 and merged[-1][2] - merged[-1][1] < minimum:
        title, start, _end = merged[-2]
        merged[-2] = (title, start, merged[-1][2])
        merged.pop()
    return [
        (f"Chapter {number}", start, end)
        for number, (_title, start, end) in enumerate(merged, start=1)
    ]


def parse_timestamp(text):
    hours, minutes, seconds = text.strip().split(":")
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def read_csv(path):
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = []
        for row in reader:
            rows.append(
                (
                    row["Chapter"],
                    parse_timestamp(row["StartTimestamp"]),
                    parse_timestamp(row["EndTimestamp"]),
                )
            )
        return rows


def output_path(video):
    path = Path(video)
    return path.with_name(f"{path.stem}_chapters.csv")


def names_path(video):
    path = Path(video)
    return path.with_name(f"{path.stem}_chapternames.csv")


def read_chapter_names(path):
    with Path(path).open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames or []
        if "Volume" not in fields or "Chapter" not in fields:
            sys.exit(f"{path} must have Volume and Chapter columns")
        rows = []
        for row in reader:
            volume = (row.get("Volume") or "").strip()
            title = (row.get("Chapter") or "").strip()
            if not volume or not title:
                sys.exit(f"{path} has a blank volume or chapter name")
            rows.append((volume, title))
    if not rows:
        sys.exit(f"{path} has no chapters")
    volumes = {volume for volume, _title in rows}
    if len(volumes) != 1:
        listed = ", ".join(sorted(volumes))
        sys.exit(f"{path} lists more than one volume: {listed}")
    return rows[0][0], [title for _volume, title in rows]


def load_named_chapters(video):
    """Pair timestamp rows with names. Both files must have the same count."""
    video = Path(video)
    times_path = output_path(video)
    titles_path = names_path(video)
    for path in (times_path, titles_path):
        if not path.is_file():
            sys.exit(f"missing {path.name} for {video.name}")
    times = read_csv(times_path)
    volume, titles = read_chapter_names(titles_path)
    if not video.stem.endswith(volume):
        sys.exit(f"{video.name} does not match volume {volume!r} in {titles_path.name}")
    if len(times) != len(titles):
        sys.exit(
            f"{video.name}: {len(times)} timestamps in {times_path.name}, "
            f"{len(titles)} names in {titles_path.name}"
        )
    named = []
    previous_end = None
    for (_placeholder, start, end), title in zip(times, titles):
        if end <= start:
            sys.exit(f"{video.name}: {title!r} ends at or before it starts")
        if previous_end is None:
            if start > 0.001:
                sys.exit(f"{video.name}: first chapter starts at {start}, expected 0")
        elif abs(start - previous_end) > 0.001:
            sys.exit(f"{video.name}: {title!r} does not continue from the previous chapter")
        named.append((title, start, end))
        previous_end = end
    return named


def ffmeta_escape(text):
    escaped = []
    for char in text:
        if char in "\\=;#":
            escaped.append("\\" + char)
        elif char == "\n":
            escaped.append("\\\n")
        else:
            escaped.append(char)
    return "".join(escaped)


def write_ffmetadata(path, chapters):
    lines = [";FFMETADATA1"]
    for title, start, end in chapters:
        lines.extend(
            [
                "[CHAPTER]",
                "TIMEBASE=1/1000",
                f"START={int(round(start * 1000))}",
                f"END={int(round(end * 1000))}",
                f"title={ffmeta_escape(title)}",
            ]
        )
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def probe(video):
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        sys.exit("ffprobe not found on PATH")
    out = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_format",
            "-show_streams",
            "-show_chapters",
            "-of",
            "json",
            str(video),
        ],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return json.loads(out)


def embedded_chapters(info):
    rows = []
    for chapter in info.get("chapters", []):
        title = (chapter.get("tags") or {}).get("title", "")
        start = int(round(float(chapter["start_time"]) * 1000))
        end = int(round(float(chapter["end_time"]) * 1000))
        rows.append((title, start, end))
    return rows


def expected_chapters(chapters):
    return [
        (title, int(round(start * 1000)), int(round(end * 1000)))
        for title, start, end in chapters
    ]


def media_signature(info):
    """Video and audio identity. Chapter data is compared separately."""
    rows = []
    for stream in info.get("streams", []):
        kind = stream.get("codec_type")
        if kind not in ("video", "audio"):
            continue
        rows.append(
            (
                kind,
                stream.get("codec_name"),
                stream.get("width"),
                stream.get("height"),
                stream.get("sample_rate"),
                stream.get("channels"),
                stream.get("nb_frames"),
            )
        )
    return rows


def apply_chapters(video):
    """Remux `video` so its chapters match the two sidecar CSVs."""
    video = Path(video)
    if not video.is_file():
        sys.exit(f"video not found: {video}")
    chapters = load_named_chapters(video)
    before = probe(video)
    duration = float(before["format"]["duration"])
    last_end = chapters[-1][2]
    if abs(last_end - duration) > 1.0:
        sys.exit(
            f"{video.name}: last chapter ends at {last_end:.3f}s, "
            f"video duration is {duration:.3f}s"
        )

    temp = video.with_name(f"{video.stem}.tmp-chapters{video.suffix}")
    meta_fd, meta_name = tempfile.mkstemp(prefix="chapters-", suffix=".ffmeta")
    os.close(meta_fd)
    meta = Path(meta_name)
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        sys.exit("ffmpeg not found on PATH")
    try:
        write_ffmetadata(meta, chapters)
        result = subprocess.run(
            [
                ffmpeg,
                "-y",
                "-v",
                "error",
                "-i",
                str(video),
                "-f",
                "ffmetadata",
                "-i",
                str(meta),
                "-map",
                "0:v",
                "-map",
                "0:a",
                "-map_metadata",
                "0",
                "-map_chapters",
                "1",
                "-c",
                "copy",
                str(temp),
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            sys.exit(f"ffmpeg exited {result.returncode} for {video.name}\n{result.stderr}")
        after = probe(temp)
        if media_signature(after) != media_signature(before):
            sys.exit(f"{video.name}: remux changed the video or audio; left the original in place")
        data_streams = [
            stream for stream in after.get("streams", []) if stream.get("codec_type") == "data"
        ]
        if len(data_streams) != 1 or data_streams[0].get("codec_tag_string") != "text":
            sys.exit(f"{video.name}: remux did not write a single chapter track")
        after_duration = float(after["format"]["duration"])
        if abs(after_duration - duration) > 0.05:
            sys.exit(
                f"{video.name}: duration changed from {duration:.3f}s to {after_duration:.3f}s"
            )
        got = embedded_chapters(after)
        want = expected_chapters(chapters)
        if got != want:
            sys.exit(f"{video.name}: embedded chapters do not match the CSV files")
        os.replace(temp, video)
    finally:
        meta.unlink(missing_ok=True)
        if temp.exists():
            temp.unlink()
    print(f"applied {len(chapters)} chapters to {video.name}")


def videos_with_sidecars(directory):
    found = []
    for video in sorted(Path(directory).glob("*.mp4")):
        if ".tmp-chapters" in video.name:
            continue
        if output_path(video).is_file() and names_path(video).is_file():
            found.append(video)
    return found


def apply_cli(argv):
    parser = argparse.ArgumentParser(
        prog="generate_chapters.py --apply",
        description="Embed chapters from the sidecar CSV files into the videos.",
    )
    parser.add_argument(
        "videos",
        nargs="*",
        help="video files to update (default: every mp4 in the current directory with both CSV files)",
    )
    args = parser.parse_args(argv)
    videos = [Path(video) for video in args.videos] if args.videos else videos_with_sidecars(Path.cwd())
    if not videos:
        sys.exit("no videos with chapter sidecars found")
    failed = False
    for video in videos:
        try:
            apply_chapters(video)
        except SystemExit as exc:
            failed = True
            message = exc.code if isinstance(exc.code, str) else "apply failed"
            print(message, file=sys.stderr)
    if failed:
        sys.exit(1)


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Chapter", "StartTimestamp", "EndTimestamp"])
        for title, start, end in rows:
            writer.writerow(
                [
                    title,
                    find_color_frames.format_timestamp(start),
                    find_color_frames.format_timestamp(end),
                ]
            )


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--apply":
        apply_cli(sys.argv[2:])
        return
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", help="video file to scan")
    parser.add_argument(
        "color",
        type=find_color_frames.parse_hex,
        help="target color as RRGGBB hex, with or without a leading #",
    )
    parser.add_argument("--x", type=int, default=5, help="pixel column, 0-based (default 5)")
    parser.add_argument("--y", type=int, default=5, help="pixel row, 0-based (default 5)")
    parser.add_argument(
        "--gap",
        type=float,
        default=10.0,
        help="minimum seconds between chapter starts (default 10)",
    )
    parser.add_argument(
        "--hue",
        type=float,
        default=8.0,
        help="max hue difference in degrees (default 8)",
    )
    parser.add_argument(
        "--sat",
        type=float,
        default=0.08,
        help="max saturation difference, 0 to 1 (default 0.08)",
    )
    parser.add_argument(
        "--val",
        type=float,
        default=0.10,
        help="max value difference, 0 to 1 (default 0.10)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="CSV path (default: <video stem>_chapters.csv next to the video)",
    )
    args = parser.parse_args()
    if args.x < 0 or args.y < 0:
        sys.exit("--x and --y must be >= 0")
    if args.gap < 0:
        sys.exit("--gap must be >= 0")

    _fps, found = find_color_frames.scan(
        args.video,
        args.color,
        args.x,
        args.y,
        args.gap,
        args.hue,
        args.sat,
        args.val,
    )
    if not found:
        print("no matches", file=sys.stderr)
        sys.exit(1)

    rows = merge_short_chapters(chapter_rows(found, video_duration(args.video)))
    destination = args.output if args.output is not None else output_path(args.video)
    write_csv(destination, rows)

    for timestamp, pixel in found:
        print(
            f"{find_color_frames.format_timestamp(timestamp)}  "
            f"#{pixel[0]:02X}{pixel[1]:02X}{pixel[2]:02X}"
        )
    print(f"wrote {len(rows)} chapters to {destination}")


if __name__ == "__main__":
    main()
