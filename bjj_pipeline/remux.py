"""One remux path and one container-chapter reader for organize and visual embed."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Callable

from .organizer.errors import FfmpegError

VERIFY_COUNT = "count"
VERIFY_STRICT = "strict"

Command = Callable[[list[str]], subprocess.CompletedProcess[str]]


class RemuxError(FfmpegError):
    """ffmpeg remux or ffprobe chapter read failed."""


def run_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")


def av_copy_flags(dest: Path, mov_faststart: bool = True) -> list[str]:
    """Copy only A/V. Source files often carry data streams (codec none)
    that the MP4 muxer cannot store when -map 0 is used.

    MP4 faststart and -sn stay on MP4/M4V. WebM and Matroska keep chapters
    in the container, so those flags are not applied.
    """
    cmd = [
        "-map",
        "0:v:0?",
        "-map",
        "0:a?",
        "-c",
        "copy",
        "-dn",
        "-ignore_unknown",
    ]
    suffix = dest.suffix.lower()
    if suffix in {".mp4", ".m4v"}:
        cmd.append("-sn")
        if mov_faststart:
            cmd.extend(["-movflags", "use_metadata_tags+faststart"])
    return cmd


def build_ffmpeg_cmd(
    ffmpeg: str,
    source: Path,
    meta_path: Path,
    dest: Path,
    mov_faststart: bool = True,
    *,
    verify: str = VERIFY_COUNT,
) -> list[str]:
    if verify == VERIFY_STRICT:
        return [
            ffmpeg,
            "-y",
            "-v",
            "error",
            "-i",
            str(source),
            "-f",
            "ffmetadata",
            "-i",
            str(meta_path),
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
            str(dest),
        ]
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(source),
        "-i",
        str(meta_path),
        *av_copy_flags(dest, mov_faststart=mov_faststart),
        "-map_chapters",
        "1",
        str(dest),
    ]
    return cmd


def chapter_tag_title(chapter: dict) -> str:
    tags = chapter.get("tags") or {}
    for key, value in tags.items():
        if key.lower() == "title" and value is not None and str(value).strip():
            return str(value).strip()
    return ""


def chapter_seconds(chapter: dict, key: str) -> float:
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


def read_ffprobe_chapters(
    path: Path,
    ffprobe: str = "ffprobe",
    *,
    command: Command | None = None,
) -> list[dict]:
    """Return the raw ffprobe ``chapters`` list for ``path``."""
    run = command or run_command
    result = run(
        [
            ffprobe,
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_chapters",
            str(path),
        ]
    )
    if result.returncode != 0:
        raise RemuxError(f"ffprobe chapters failed on {path.name}: {result.stderr.strip()}")
    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise RemuxError(f"ffprobe chapters JSON invalid for {path.name}") from exc
    return list(payload.get("chapters") or [])


def read_container_chapters(
    path: Path,
    ffprobe: str = "ffprobe",
    *,
    command: Command | None = None,
) -> list[dict]:
    """Return chapters as ``{title, start, end}`` with times in seconds."""
    rows = []
    for chapter in read_ffprobe_chapters(path, ffprobe, command=command):
        rows.append(
            {
                "title": chapter_tag_title(chapter),
                "start": chapter_seconds(chapter, "start"),
                "end": chapter_seconds(chapter, "end"),
            }
        )
    return rows


def chapter_count(
    path: Path,
    ffprobe: str = "ffprobe",
    *,
    command: Command | None = None,
) -> int:
    return len(read_ffprobe_chapters(path, ffprobe, command=command))


def chapter_titles(
    path: Path,
    ffprobe: str = "ffprobe",
    *,
    command: Command | None = None,
) -> list[str]:
    return [row["title"] for row in read_container_chapters(path, ffprobe, command=command) if row["title"]]


def probe_media(
    path: Path,
    ffprobe: str = "ffprobe",
    *,
    command: Command | None = None,
) -> dict:
    run = command or run_command
    result = run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_format",
            "-show_streams",
            "-show_chapters",
            "-of",
            "json",
            str(path),
        ]
    )
    if result.returncode != 0:
        raise RemuxError(f"ffprobe failed on {path.name}: {result.stderr.strip()}")
    try:
        return json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise RemuxError(f"ffprobe JSON invalid for {path.name}") from exc


def media_signature(info: dict) -> list[tuple]:
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


def embedded_chapters(info: dict) -> list[tuple[str, int, int]]:
    rows = []
    for chapter in info.get("chapters", []):
        title = (chapter.get("tags") or {}).get("title", "")
        start = int(round(float(chapter["start_time"]) * 1000))
        end = int(round(float(chapter["end_time"]) * 1000))
        rows.append((title, start, end))
    return rows


def _verify_count(path: Path, ffprobe: str, command: Command | None, label: str) -> None:
    if chapter_count(path, ffprobe, command=command) < 1:
        raise RemuxError(f"Remux produced no chapters for {label}; original left untouched")


def _verify_strict(
    path: Path,
    dest: Path,
    *,
    ffprobe: str,
    command: Command | None,
    before: dict,
    duration: float,
    expected: list[tuple[str, int, int]],
) -> None:
    after = probe_media(path, ffprobe, command=command)
    label = dest.name
    if media_signature(after) != media_signature(before):
        raise RemuxError(f"{label}: remux changed the video or audio; left the original in place")
    data_streams = [
        stream for stream in after.get("streams", []) if stream.get("codec_type") == "data"
    ]
    # MP4 stores chapters as one text data stream. WebM and Matroska
    # store them in the container, which the chapter list check covers.
    suffix = dest.suffix.lower()
    if suffix in {".webm", ".mkv"}:
        if data_streams:
            raise RemuxError(f"{label}: remux added a data stream")
    elif len(data_streams) != 1 or data_streams[0].get("codec_tag_string") != "text":
        raise RemuxError(f"{label}: remux did not write a single chapter track")
    after_duration = float(after["format"]["duration"])
    if abs(after_duration - duration) > 0.05:
        raise RemuxError(
            f"{label}: duration changed from {duration:.3f}s to {after_duration:.3f}s"
        )
    if embedded_chapters(after) != expected:
        raise RemuxError(f"{label}: embedded chapters do not match the CSV files")


def remux_chapters(
    source: Path,
    dest: Path,
    metadata: str,
    *,
    ffmpeg: str,
    ffprobe: str,
    verify: str = VERIFY_STRICT,
    expected_chapters: list[tuple[str, int, int]] | None = None,
    before: dict | None = None,
    duration: float | None = None,
    mov_faststart: bool = True,
    command: Command | None = None,
    temp_path: Path | None = None,
) -> None:
    """Remux ``source`` onto ``dest`` with ffmetadata chapters.

    Visual embed defaults to strict verify (media signature, duration,
    embedded chapter list, MP4 text data stream vs WebM/MKV with no extra
    data stream). Organize passes ``verify=count``.
    """
    run = command or run_command
    dest.parent.mkdir(parents=True, exist_ok=True)
    meta_path = source.parent / f".{source.stem}.ffmeta.tmp"
    temp = temp_path or dest.with_name(f".{dest.stem}.chapters.tmp{dest.suffix}")
    try:
        meta_path.write_text(metadata, encoding="utf-8")
        cmd = build_ffmpeg_cmd(
            ffmpeg,
            source,
            meta_path,
            temp,
            mov_faststart=mov_faststart,
            verify=verify,
        )
        result = run(cmd)
        if result.returncode != 0:
            if verify == VERIFY_STRICT:
                raise RemuxError(
                    f"ffmpeg exited {result.returncode} for {source.name}\n{result.stderr}"
                )
            raise RemuxError(
                f"ffmpeg remux failed for {source.name}: {result.stderr.strip()[-2000:]}"
            )
        if verify == VERIFY_COUNT:
            _verify_count(temp, ffprobe, command, source.name)
        else:
            info = before if before is not None else probe_media(source, ffprobe, command=command)
            length = duration if duration is not None else float(info["format"]["duration"])
            expected = expected_chapters if expected_chapters is not None else embedded_chapters(info)
            _verify_strict(
                temp,
                dest,
                ffprobe=ffprobe,
                command=command,
                before=info,
                duration=length,
                expected=expected,
            )
        os.replace(temp, dest)
    finally:
        if meta_path.exists():
            meta_path.unlink()
        if temp.exists() and temp != dest:
            temp.unlink()
