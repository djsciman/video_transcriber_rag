from __future__ import annotations

import shutil
from pathlib import Path

from bjj_pipeline.remux import (
    VERIFY_COUNT,
    av_copy_flags,
    build_ffmpeg_cmd,
    chapter_count,
    chapter_titles,
    remux_chapters,
    run_command,
)

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


def _run(args: list[str]):
    return run_command(args)


def probe_duration_ms(path: Path, ffprobe: str, command=None) -> int:
    run = command or _run
    result = run(
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


def probe_chapter_titles(path: Path, ffprobe: str, command=None) -> list[str]:
    return chapter_titles(path, ffprobe, command=command)


def probe_chapter_count(path: Path, ffprobe: str, command=None) -> int:
    return chapter_count(path, ffprobe, command=command)


def ensure_disk_space(path: Path, file_size: int) -> None:
    usage = shutil.disk_usage(path)
    needed = (2 * file_size) + 100 * 1024 * 1024
    if usage.free < needed:
        raise FfmpegError(
            f"Not enough free disk space to remux {path.name} "
            f"(need ~{needed // (1024 * 1024)} MiB)"
        )


def remux_with_chapters(
    source: Path,
    dest: Path,
    chapters: list[Chapter],
    ffmpeg: str,
    ffprobe: str,
    mov_faststart: bool,
    command=None,
) -> None:
    duration_ms = probe_duration_ms(source, ffprobe, command=command)
    metadata = build_ffmetadata(chapters, duration_ms)
    if not metadata:
        raise FfmpegError(f"No usable chapters for {source.name}")
    ensure_disk_space(source.parent, source.stat().st_size)
    remux_chapters(
        source,
        dest,
        metadata,
        ffmpeg=ffmpeg,
        ffprobe=ffprobe,
        verify=VERIFY_COUNT,
        mov_faststart=mov_faststart,
        command=command,
    )
