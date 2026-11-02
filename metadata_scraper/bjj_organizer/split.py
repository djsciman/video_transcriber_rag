from __future__ import annotations

import shutil
from pathlib import Path

from .chapters import av_copy_flags, probe_duration_ms, run_command
from .errors import FfmpegError
from .models import Chapter, EpisodePlan


def ms_to_seconds(ms: int) -> str:
    return f"{ms / 1000:.3f}"


def chapter_ranges(
    chapters: list[Chapter],
    duration_ms: int,
) -> list[tuple[Chapter, int, int]]:
    usable = [ch for ch in chapters if ch.title.strip() and ch.start_ms < duration_ms]
    out: list[tuple[Chapter, int, int]] = []
    for index, chapter in enumerate(usable):
        start = chapter.start_ms
        if index + 1 < len(usable):
            end = min(usable[index + 1].start_ms, duration_ms)
        else:
            end = duration_ms
        if end <= start:
            continue
        out.append((chapter, start, end))
    return out


def resolve_range(start_ms: int | None, end_ms: int | None, duration_ms: int) -> tuple[int, int] | None:
    start = 0 if start_ms is None else start_ms
    end = duration_ms if end_ms is None else end_ms
    if start >= duration_ms or end <= start:
        return None
    return start, min(end, duration_ms)


def ensure_split_space(path: Path, file_size: int) -> None:
    usage = shutil.disk_usage(path)
    needed = file_size + 100 * 1024 * 1024
    if usage.free < needed:
        raise FfmpegError(
            f"Not enough free disk space to split {path.name} "
            f"(need ~{needed // (1024 * 1024)} MiB)"
        )


def build_split_cmd(
    ffmpeg: str,
    source: Path,
    dest: Path,
    start_ms: int,
    end_ms: int,
) -> list[str]:
    cmd = [
        ffmpeg,
        "-y",
        "-ss",
        ms_to_seconds(start_ms),
        "-to",
        ms_to_seconds(end_ms),
        "-i",
        str(source),
        *av_copy_flags(dest, mov_faststart=True),
        "-avoid_negative_ts",
        "make_zero",
        str(dest),
    ]
    return cmd


def build_copy_cmd(ffmpeg: str, source: Path, dest: Path) -> list[str]:
    return [
        ffmpeg,
        "-y",
        "-i",
        str(source),
        *av_copy_flags(dest, mov_faststart=True),
        str(dest),
    ]


def probe_split_ok(path: Path, ffprobe: str) -> bool:
    if probe_duration_ms(path, ffprobe) <= 0:
        return False
    result = run_command(
        [
            ffprobe,
            "-v",
            "error",
            "-select_streams",
            "v",
            "-show_entries",
            "stream=codec_type",
            "-of",
            "csv=p=0",
            str(path),
        ]
    )
    return result.returncode == 0 and bool(result.stdout.strip())


def remux_copy(source: Path, dest: Path, ffmpeg: str, ffprobe: str) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    temp_path = dest.with_name(f".{dest.stem}.copy.tmp{dest.suffix}")
    try:
        cmd = build_copy_cmd(ffmpeg, source, temp_path)
        result = run_command(cmd)
        if result.returncode != 0:
            raise FfmpegError(
                f"ffmpeg remux failed for {source.name}: {result.stderr.strip()[-2000:]}"
            )
        if not probe_split_ok(temp_path, ffprobe):
            raise FfmpegError(f"Remux produced no video for {source.name}; original left untouched")
        temp_path.replace(dest)
    finally:
        if temp_path.exists() and temp_path != dest:
            temp_path.unlink()


def is_whole_file_copy(episodes: list[EpisodePlan]) -> bool:
    if len(episodes) != 1:
        return False
    episode = episodes[0]
    if episode.split_start_ms is None:
        return True
    return episode.split_start_ms == 0 and episode.split_end_ms is None


def split_source_into_episodes(
    source: Path,
    episodes: list[EpisodePlan],
    dest_dir: Path,
    ffmpeg: str,
    ffprobe: str,
) -> list[EpisodePlan]:
    """Split one volume file into chapter files. Returns episodes that were written."""
    duration_ms = probe_duration_ms(source, ffprobe)
    ensure_split_space(source.parent, source.stat().st_size)
    dest_dir.mkdir(parents=True, exist_ok=True)
    temps: list[tuple[Path, Path, EpisodePlan]] = []
    written: list[EpisodePlan] = []
    try:
        for episode in episodes:
            resolved = resolve_range(episode.split_start_ms, episode.split_end_ms, duration_ms)
            if resolved is None:
                continue
            start_ms, end_ms = resolved
            dest = dest_dir / episode.dest_name
            temp_path = dest.with_name(f".{dest.stem}.split.tmp{dest.suffix}")
            cmd = build_split_cmd(ffmpeg, source, temp_path, start_ms, end_ms)
            result = run_command(cmd)
            if result.returncode != 0:
                raise FfmpegError(
                    f"ffmpeg split failed for {source.name} -> {episode.dest_name}: "
                    f"{result.stderr.strip()[-2000:]}"
                )
            if not probe_split_ok(temp_path, ffprobe):
                raise FfmpegError(
                    f"Split produced no video for {episode.dest_name}; original left untouched"
                )
            temps.append((temp_path, dest, episode))
        if not temps:
            raise FfmpegError(f"No usable chapter ranges for {source.name}")
        for temp_path, dest, episode in temps:
            if dest.exists() and dest.resolve() not in {temp_path.resolve(), source.resolve()}:
                dest.unlink()
            dest.parent.mkdir(parents=True, exist_ok=True)
            temp_path.replace(dest)
            written.append(episode)
        dest_paths = { (dest_dir / ep.dest_name).resolve() for ep in written }
        if source.exists() and source.resolve() not in dest_paths:
            source.unlink()
        leftover_nfo = source.with_suffix(".nfo")
        if leftover_nfo.exists() and leftover_nfo.suffix.lower() == ".nfo":
            leftover_nfo.unlink()
        return written
    except Exception:
        for temp_path, _, _ in temps:
            if temp_path.exists():
                temp_path.unlink()
        raise
