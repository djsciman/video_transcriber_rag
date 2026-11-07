from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

from .errors import FfmpegError
from .models import Chapter


def chapters_have_timeline(chapters: list[Chapter] | tuple[Chapter, ...]) -> bool:
    """True when a later chapter starts after 0, so markers can be placed."""
    return any(ch.title.strip() and ch.start_ms > 0 for ch in chapters)


def build_ffmetadata(chapters: list[Chapter], duration_ms: int) -> str:
    usable = [ch for ch in chapters if ch.title.strip() and ch.start_ms < duration_ms]
    # Several titles all at 0 are a contents list, not a timeline. Writing them
    # would turn the last title into one chapter spanning the whole file.
    if len(usable) > 1 and not chapters_have_timeline(usable):
        return ""
    if not usable:
        return ""
    lines = [";FFMETADATA1"]
    for index, chapter in enumerate(usable):
        start = chapter.start_ms
        if index + 1 < len(usable):
            end = min(usable[index + 1].start_ms, duration_ms)
        else:
            end = duration_ms
        if end <= start:
            continue
        title = chapter.title.replace("=", "\\=").replace(";", "\\;").replace("#", "\\#")
        lines.extend(
            [
                "[CHAPTER]",
                "TIMEBASE=1/1000",
                f"START={start}",
                f"END={end}",
                f"title={title}",
            ]
        )
    return "\n".join(lines) + "\n"


def run_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return run_command(args)


def av_copy_flags(dest: Path, mov_faststart: bool = True) -> list[str]:
    """Copy only A/V. Source files often carry data streams (codec none)
    that the MP4 muxer cannot store when -map 0 is used."""
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


def probe_duration_ms(path: Path, ffprobe: str) -> int:
    result = _run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            str(path),
        ]
    )
    if result.returncode != 0:
        raise FfmpegError(f"ffprobe failed on {path.name}: {result.stderr.strip()}")
    try:
        seconds = float(result.stdout.strip())
    except ValueError as exc:
        raise FfmpegError(f"ffprobe returned no duration for {path.name}") from exc
    return int(seconds * 1000)


def probe_chapter_titles(path: Path, ffprobe: str) -> list[str]:
    result = _run(
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
        raise FfmpegError(f"ffprobe chapters failed on {path.name}: {result.stderr.strip()}")
    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise FfmpegError(f"ffprobe chapters JSON invalid for {path.name}") from exc
    titles: list[str] = []
    for chapter in payload.get("chapters") or []:
        tags = chapter.get("tags") or {}
        title = str(tags.get("title") or "").strip()
        if title:
            titles.append(title)
    return titles


def probe_chapter_count(path: Path, ffprobe: str) -> int:
    result = _run(
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
        raise FfmpegError(f"ffprobe chapters failed on {path.name}: {result.stderr.strip()}")
    try:
        payload = json.loads(result.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise FfmpegError(f"ffprobe chapters JSON invalid for {path.name}") from exc
    return len(payload.get("chapters") or [])


def ensure_disk_space(path: Path, file_size: int) -> None:
    usage = shutil.disk_usage(path)
    needed = (2 * file_size) + 100 * 1024 * 1024
    if usage.free < needed:
        raise FfmpegError(
            f"Not enough free disk space to remux {path.name} "
            f"(need ~{needed // (1024 * 1024)} MiB)"
        )


def build_ffmpeg_cmd(
    ffmpeg: str,
    source: Path,
    meta_path: Path,
    dest: Path,
    mov_faststart: bool,
) -> list[str]:
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
    ]
    cmd.append(str(dest))
    return cmd


def remux_with_chapters(
    source: Path,
    dest: Path,
    chapters: list[Chapter],
    ffmpeg: str,
    ffprobe: str,
    mov_faststart: bool,
) -> None:
    duration_ms = probe_duration_ms(source, ffprobe)
    metadata = build_ffmetadata(chapters, duration_ms)
    if not metadata:
        raise FfmpegError(f"No usable chapters for {source.name}")
    ensure_disk_space(source.parent, source.stat().st_size)
    meta_path = source.parent / f".{source.stem}.ffmeta.tmp"
    temp_path = dest.with_name(f".{dest.stem}.chapters.tmp{dest.suffix}")
    try:
        meta_path.write_text(metadata, encoding="utf-8")
        cmd = build_ffmpeg_cmd(ffmpeg, source, meta_path, temp_path, mov_faststart)
        result = _run(cmd)
        if result.returncode != 0:
            raise FfmpegError(f"ffmpeg remux failed for {source.name}: {result.stderr.strip()[-2000:]}")
        if probe_chapter_count(temp_path, ffprobe) < 1:
            raise FfmpegError(f"Remux produced no chapters for {source.name}; original left untouched")
        temp_path.replace(dest)
    finally:
        if meta_path.exists():
            meta_path.unlink()
        if temp_path.exists() and temp_path != dest:
            temp_path.unlink()
