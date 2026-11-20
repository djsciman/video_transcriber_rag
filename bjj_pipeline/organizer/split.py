from __future__ import annotations

import shutil
from pathlib import Path

from .chapters import av_copy_flags, probe_duration_ms, run_command
from .errors import FfmpegError


def ensure_split_space(path: Path, file_size: int) -> None:
    usage = shutil.disk_usage(path)
    needed = file_size + 100 * 1024 * 1024
    if usage.free < needed:
        raise FfmpegError(
            f"Not enough free disk space to split {path.name} "
            f"(need ~{needed // (1024 * 1024)} MiB)"
        )


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
