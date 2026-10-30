"""Write a chapter-markers CSV from title-card color frames, and embed it.

A frame opens a chapter when more than --fraction (default 0.75) of its
pixels fall within the HSV tolerance of the given color. The chapter runs
until the next such frame, and the last chapter runs until the end of the
video. When the first match is more than a second in, a lead-in chapter
starts at 00:00:00.000. A long card is marked again every --gap seconds
(default 30). Consecutive chapters of that length are merged into one.
A chapter shorter than --min-seconds (default 10) is then merged into the
chapter after it. A short final chapter is merged into the one before it.
The title is OCR of the title card for --title-seconds after the card
starts (default 6). Slides are joined with " -- ", and repeated text is
kept once. A frame that fails the plate test ends the title. The opening
disclaimer is not used: naming starts at the first matched card, and a
paragraph longer than 160 characters is skipped. A card with no text is
titled continued. Those titles are written
to the timestamp CSV and to the chapter-names CSV. Without --apply, only
those files are written. With --apply, an existing chapter CSV is embedded
and the video is not scanned again. With --apply and no chapter CSV, the
scan runs and the new chapters are embedded.

The file is written next to the video as <video stem>_chapters.csv:

  Chapter,StartTimestamp,EndTimestamp
  Chapter 1,00:00:00.000,00:03:39.040
  Chapter 2,00:03:39.040,00:08:59.120

Color matching uses the same HSV tolerances as find_color_frames.
Pass --samples with timestamps of known title cards to use their
predominant color instead of a hex. That color must cover more than
--fraction of every sample (default 0.75). When it does not, a frame
matches on pixels with saturation above 0.50 and value below 0.45,
if that share clears the same fraction. A hex scan that finds nothing
uses that same dark-saturated test. With no --samples and no hex, one
frame a second is scored for color concentration and dark saturation.
A metric whose high scores form a rare cluster, separated from the
lesson by a gap, supplies the chapter test. A matching run is two
adjacent samples from that one-second pass.

Embedding reads that CSV together with <video stem>_chapternames.csv and
writes the named chapters into the video. Streams are copied, not
re-encoded. The original file is replaced only after the new chapters
probe back correctly.

  python generate_chapters.py "Volume 1.mp4" 1a3c8e --apply
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
# Read title cards from the matched frame through this many seconds.
TITLE_WINDOW_SECONDS = 6.0
# How often to look at a frame inside that window.
TITLE_SAMPLE_SECONDS = 0.5
# The opening disclaimer is a paragraph. Title cards are a short line.
DISCLAIMER_CHAR_LIMIT = 160
# Used when that frame has no readable text.
CONTINUED_TITLE = "continued"


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


def merge_gap_chapters(rows, gap):
    """Join a consecutive run of gap-length chapters into one chapter.

    A card that stays up longer than `gap` is marked again at each gap,
    so the file contains a row of chapters that are each `gap` seconds
    long. One of those is left as it is. Two or more in a row become a
    single chapter from the first start to the last end.
    """
    merged = []
    run_start = None
    run_end = None

    def flush():
        nonlocal run_start, run_end
        if run_start is None:
            return
        merged.append(("Chapter", run_start, run_end))
        run_start = None
        run_end = None

    for _title, start, end in rows:
        length = end - start
        if gap - 0.001 <= length < gap + 0.25:
            if run_start is None:
                run_start = start
            run_end = end
            continue
        flush()
        merged.append(("Chapter", start, end))
    flush()
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


def load_named_chapters(video, times_path=None):
    """Pair timestamp rows with names. Both files must have the same count."""
    video = Path(video)
    times_path = Path(times_path) if times_path is not None else output_path(video)
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


def apply_chapters(video, times_path=None):
    """Remux `video` so its chapters match the two sidecar CSVs."""
    video = Path(video)
    if not video.is_file():
        sys.exit(f"video not found: {video}")
    chapters = load_named_chapters(video, times_path)
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
        # MP4 stores chapters as one text data stream. WebM and Matroska
        # store them in the container, which the chapter list check covers.
        if video.suffix.lower() in {".webm", ".mkv"}:
            if data_streams:
                sys.exit(f"{video.name}: remux added a data stream")
        elif len(data_streams) != 1 or data_streams[0].get("codec_tag_string") != "text":
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


def ocr_text(engine, frame):
    """Read one title card. `frame` is RGB from the same decode as the scan."""
    cv2 = find_color_frames._cv2()
    result = engine(cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
    parts = []
    for text in result.txts or ():
        cleaned = " ".join(text.split())
        if cleaned:
            parts.append(cleaned)
    return " ".join(parts)


def _compact_title(text):
    """Compare slides with spaces and case ignored."""
    return "".join(text.casefold().split())


def _same_slide(a, b):
    """True when two readings are the same card.

    One extra digit counts as the same card. OCR turns "ARMS 1" into
    "ARMS 51" that way. A different digit, such as "ARMS 1" and "ARMS 2",
    stays a different card.
    """
    if a == b:
        return True
    if abs(len(a) - len(b)) != 1:
        return False
    short, long = (a, b) if len(a) < len(b) else (b, a)
    for index, char in enumerate(long):
        if char.isdigit() and long[:index] + long[index + 1:] == short:
            return True
    return False


def _clearer_title(new, old):
    """Prefer the reading with the extra digit removed, then the one with word spaces."""
    new_key = _compact_title(new)
    old_key = _compact_title(old)
    if len(new_key) != len(old_key):
        return len(new_key) < len(old_key)
    return new.count(" ") > old.count(" ")


def _remember_title(pieces, text):
    key = _compact_title(text)
    if not key or len(text) > DISCLAIMER_CHAR_LIMIT:
        return
    for index, existing in enumerate(pieces):
        if _same_slide(key, _compact_title(existing)):
            if _clearer_title(text, existing):
                pieces[index] = text
            return
    pieces.append(text)


def card_anchor(start, end, matches):
    """First scanned match inside this chapter, or the chapter start."""
    for timestamp, _share in matches:
        if start - 0.001 <= timestamp < end:
            return timestamp
    return start


def frame_still_card(frame, mode, color, hue, sat, val, fraction, auto=None):
    """True when the frame still passes the test that opened the chapter."""
    if mode == "auto":
        matched, _share = find_color_frames.auto_match(frame, auto)
        return matched
    if mode == "dark":
        share = find_color_frames.dark_saturated_share(frame)
    else:
        share = find_color_frames._coverage(frame, color, hue, sat, val)
    return share > fraction


def collect_title(engine, video, anchor, duration, window, mode, color, hue, sat, val, fraction, auto=None):
    """OCR title slides from `anchor` through `window` seconds.

    Frames before the first card are skipped, so an opening disclaimer
    is not the name. After a card has matched, the first frame that fails
    the plate test ends collection. A repeat with different spacing, or
    one extra OCR digit, is the same slide. The reading with word spaces
    and without that digit is kept.
    """
    pieces = []
    started = False
    offset = 0.0
    while offset <= window + 1e-6:
        when = anchor + offset
        offset += TITLE_SAMPLE_SECONDS
        if when >= duration:
            break
        frame = find_color_frames.read_frame(video, when)
        if not frame_still_card(frame, mode, color, hue, sat, val, fraction, auto):
            if started:
                break
            continue
        started = True
        _remember_title(pieces, ocr_text(engine, frame))
    if not pieces:
        return CONTINUED_TITLE
    return " -- ".join(pieces)


def title_chapters(video, rows, duration, matches, mode, color, hue, sat, val, fraction, window, auto=None):
    """Replace placeholder titles with the text on the title cards."""
    try:
        from rapidocr import RapidOCR
    except ImportError:
        sys.exit("rapidocr is required to read chapter titles")
    engine = RapidOCR()
    titled = []
    for _title, start, end in rows:
        anchor = card_anchor(start, end, matches)
        title = collect_title(
            engine, video, anchor, duration, window,
            mode, color, hue, sat, val, fraction, auto,
        )
        titled.append((title, start, end))
        line = (
            f"{find_color_frames.format_timestamp(start)}  "
            f"{find_color_frames.format_timestamp(anchor)}  {title}"
        )
        try:
            print(line)
        except UnicodeEncodeError:
            encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
            sys.stdout.buffer.write(line.encode(encoding, errors="replace") + b"\n")
            sys.stdout.buffer.flush()
    return titled


def write_names(path, video, rows):
    volume = Path(video).stem
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Volume", "Chapter"])
        for title, _start, _end in rows:
            writer.writerow([volume, title])


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


def configure_stdio():
    """Let chapter titles print on a Windows console that is not UTF-8."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            pass


def parse_sample_time(text):
    """Accept seconds, MM:SS, or HH:MM:SS, with an optional fraction."""
    raw = text.strip()
    if ":" not in raw:
        try:
            seconds = float(raw)
        except ValueError:
            raise argparse.ArgumentTypeError(f"expected a timestamp, got {text!r}") from None
        if seconds < 0:
            raise argparse.ArgumentTypeError("sample timestamps must be >= 0")
        return seconds
    parts = raw.split(":")
    try:
        if len(parts) == 2:
            minutes, seconds = parts
            total = int(minutes) * 60 + float(seconds)
        elif len(parts) == 3:
            hours, minutes, seconds = parts
            total = int(hours) * 3600 + int(minutes) * 60 + float(seconds)
        else:
            raise ValueError
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected a timestamp, got {text!r}") from None
    if total < 0:
        raise argparse.ArgumentTypeError("sample timestamps must be >= 0")
    return total


def _sample_frames(video, samples):
    duration = video_duration(video)
    frames = []
    for seconds in samples:
        if seconds >= duration:
            sys.exit(
                f"sample {find_color_frames.format_timestamp(seconds)} "
                f"is past the end of the video "
                f"({find_color_frames.format_timestamp(duration)})"
            )
        frames.append(find_color_frames.read_frame(video, seconds))
    return frames


def _color_failure_lines(samples, frames, hue, sat, val):
    lines = []
    for seconds, frame in zip(samples, frames):
        own, share = find_color_frames.dominant_rgb(frame, hue, sat, val)
        own_hex = f"{own[0]:02X}{own[1]:02X}{own[2]:02X}"
        weakest = min(
            find_color_frames._coverage(other, own, hue, sat, val) for other in frames
        )
        lines.append(
            f"sample {find_color_frames.format_timestamp(seconds)}  "
            f"#{own_hex} covers {share * 100:.1f}% of this frame "
            f"and {weakest * 100:.1f}% of the weakest sample"
        )
    return lines


def plate_from_samples(video, samples, hue, sat, val, fraction):
    """Return ("color", rgb) or ("dark", None) for the sample title cards.

    One hex plate is preferred. When that plate stays at or below
    `fraction` on any sample, dark saturated pixels are used if they
    clear `fraction` on every sample.
    """
    frames = _sample_frames(video, samples)
    rgb, coverages = find_color_frames.predominant_color(
        frames, hue, sat, val, fraction
    )
    hex_color = f"{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"
    if min(coverages) > fraction:
        for seconds, share in zip(samples, coverages):
            print(
                f"sample {find_color_frames.format_timestamp(seconds)}  "
                f"{share * 100:.1f}%"
            )
        print(f"plate color #{hex_color}")
        return "color", rgb
    bounds = find_color_frames.dark_saturated_bounds()
    dark_shares = [
        find_color_frames.dark_saturated_share(frame, bounds) for frame in frames
    ]
    if min(dark_shares) > fraction:
        for seconds, share in zip(samples, dark_shares):
            print(
                f"sample {find_color_frames.format_timestamp(seconds)}  "
                f"{share * 100:.1f}% dark saturated"
            )
        print(
            f"#{hex_color} covers at most {min(coverages) * 100:.1f}%, "
            f"under {fraction * 100:.1f}%; matching pixels with "
            f"saturation > {find_color_frames.DARK_SAT_MIN:.2f} and "
            f"value < {find_color_frames.DARK_VAL_MAX:.2f}"
        )
        return "dark", None
    lines = _color_failure_lines(samples, frames, hue, sat, val)
    for seconds, share in zip(samples, dark_shares):
        lines.append(
            f"sample {find_color_frames.format_timestamp(seconds)}  "
            f"{share * 100:.1f}% dark saturated"
        )
    lines.append(
        f"no plate covers more than {fraction * 100:.1f}% of every sample"
    )
    sys.exit("\n".join(lines))


def auto_from_video(video, hue, sat, val):
    """Score the file once and choose the card tests from the high clusters.

    Also returns one (timestamp, matched, share) row per sample, including
    misses, after the plate test. Scaled frames are dropped before return.
    """
    def on_sample(timestamp):
        if timestamp > 0 and timestamp % 60 == 0:
            print(f"scored {find_color_frames.format_timestamp(timestamp)}", flush=True)

    rows = find_color_frames.score_timeline(
        video, hue, sat, val, on_sample=on_sample,
    )
    spec = find_color_frames.auto_spec(rows, hue, sat, val)
    if spec is None:
        rows.clear()
        sys.exit("no abnormal color concentration or dark saturation in this video")
    if spec["dark_cut"] is None:
        print("dark saturated: no separate high cluster")
    else:
        count = sum(1 for row in rows if row[1] > spec["dark_cut"])
        print(
            f"dark saturated cut {spec['dark_cut'] * 100:.1f}% "
            f"({count} of {len(rows)} samples)"
        )
    if not spec["plates"]:
        print("color concentration: no separate high cluster")
    else:
        cut = spec["plates"][0][1]
        count = sum(1 for row in rows if row[2] > cut)
        hexes = ", ".join(
            f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}" for rgb, _cut, _ranges in spec["plates"]
        )
        print(f"color cut {cut * 100:.1f}% plate {hexes} ({count} of {len(rows)} samples)")
    matched_rows = [
        (row[0], *find_color_frames.auto_match(row[4], spec))
        for row in rows
    ]
    rows.clear()
    return spec, matched_rows


def detection_requested(argv):
    """True when this command carries a plate color or a detection option."""
    flags = {
        "--fraction",
        "--gap",
        "--min-seconds",
        "--hue",
        "--sat",
        "--val",
        "--output",
        "--samples",
    }
    for arg in argv:
        if arg in flags or arg.startswith("--output="):
            return True
        if arg.startswith("-"):
            continue
        raw = arg[1:] if arg.startswith("#") else arg
        if len(raw) == 6 and all(char in "0123456789abcdefABCDEF" for char in raw):
            return True
    return False


def main():
    configure_stdio()
    # `--apply video` embeds sidecars that already exist. A color or a
    # detection flag selects the combined command instead.
    if "--apply" in sys.argv[1:] and not detection_requested(sys.argv[1:]):
        plain = [arg for arg in sys.argv[1:] if arg != "--apply"]
        videos = [arg for arg in plain if not arg.startswith("-")]
        # A video that already has a chapter file is embedded. A video
        # with no chapter file is detected from the histogram below.
        if not videos or all(output_path(Path(video)).is_file() for video in videos):
            apply_cli(plain)
            return
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", help="video file to scan")
    parser.add_argument(
        "color",
        nargs="?",
        type=find_color_frames.parse_hex,
        help="target color as RRGGBB hex, with or without a leading #",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="embed the chapter CSV into the video. Scan first when that file is missing",
    )
    parser.add_argument(
        "--fraction",
        type=float,
        default=0.75,
        help="title card when more than this share of the frame matches (default 0.75)",
    )
    parser.add_argument(
        "--gap",
        type=float,
        default=30.0,
        help="minimum seconds between chapter starts (default 30)",
    )
    parser.add_argument(
        "--min-seconds",
        type=float,
        default=MIN_CHAPTER_SECONDS,
        help="merge chapters shorter than this many seconds (default 10)",
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
    parser.add_argument(
        "--title-seconds",
        type=float,
        default=TITLE_WINDOW_SECONDS,
        help="seconds of title cards to read after the card starts (default 6)",
    )
    parser.add_argument(
        "--samples",
        nargs="+",
        type=parse_sample_time,
        help=(
            "timestamps of known title cards (seconds, MM:SS, or HH:MM:SS). "
            "The predominant color that covers more than --fraction of each "
            "frame becomes the plate color. Otherwise pixels with saturation "
            "above 0.50 and value below 0.45 are used when they clear that fraction. "
            "Omit this, and omit the hex color, to find cards from the whole-file histogram"
        ),
    )
    args = parser.parse_args()
    if not 0.0 <= args.fraction <= 1.0:
        sys.exit("--fraction must be between 0 and 1")
    if args.gap < 0:
        sys.exit("--gap must be >= 0")
    if args.min_seconds < 0:
        sys.exit("--min-seconds must be >= 0")
    if args.title_seconds < 0:
        sys.exit("--title-seconds must be >= 0")

    chapter_file = Path(args.output) if args.output is not None else output_path(args.video)
    if args.apply and chapter_file.is_file():
        print(f"using existing {chapter_file}")
        apply_chapters(args.video, chapter_file)
        return
    mode = "color"
    auto = None
    if args.samples:
        mode, args.color = plate_from_samples(
            args.video,
            args.samples,
            args.hue,
            args.sat,
            args.val,
            args.fraction,
        )
    elif args.color is None:
        mode = "auto"
        auto, auto_rows = auto_from_video(args.video, args.hue, args.sat, args.val)

    if mode == "auto":
        found = find_color_frames.scan_auto(auto_rows, args.gap)
    elif mode == "dark":
        found = find_color_frames.scan_dark_saturated(
            args.video,
            args.gap,
            args.fraction,
        )
    else:
        mode, found = find_color_frames.scan_frames(
            args.video,
            args.color,
            args.gap,
            args.hue,
            args.sat,
            args.val,
            args.fraction,
        )
        if mode == "dark":
            print(
                "no color matches; scanning for pixels with "
                f"saturation > {find_color_frames.DARK_SAT_MIN:.2f} and "
                f"value < {find_color_frames.DARK_VAL_MAX:.2f}",
                file=sys.stderr,
            )
    if not found:
        print("no matches", file=sys.stderr)
        sys.exit(1)

    duration = video_duration(args.video)
    rows = merge_short_chapters(
        merge_gap_chapters(
            chapter_rows(found, duration),
            args.gap,
        ),
        minimum=args.min_seconds,
    )
    rows = title_chapters(
        args.video,
        rows,
        duration,
        found,
        mode,
        args.color,
        args.hue,
        args.sat,
        args.val,
        args.fraction,
        args.title_seconds,
        auto,
    )
    destination = chapter_file
    write_csv(destination, rows)
    names = names_path(args.video)
    write_names(names, args.video, rows)

    for timestamp, fraction in found:
        print(
            f"{find_color_frames.format_timestamp(timestamp)}  "
            f"{fraction * 100:.1f}%"
        )
    print(f"wrote {len(rows)} chapters to {destination}")
    print(f"wrote {len(rows)} names to {names}")
    if args.apply:
        apply_chapters(args.video, destination)


if __name__ == "__main__":
    main()
