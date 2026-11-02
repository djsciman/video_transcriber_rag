from __future__ import annotations

from pathlib import Path

from .chapters import probe_chapter_count, probe_duration_ms, remux_with_chapters, run_command
from .errors import FfmpegError
from .models import Chapter
from .split import ensure_split_space, probe_split_ok


def chapters_from_durations(titles: list[str], durations_ms: list[int]) -> list[Chapter]:
    chapters: list[Chapter] = []
    cursor = 0
    for title, duration in zip(titles, durations_ms, strict=True):
        name = (title or "").strip() or "Chapter"
        if duration <= 0:
            continue
        chapters.append(Chapter(name, cursor))
        cursor += duration
    return chapters


def concat_list_line(path: Path) -> str:
    posix = path.resolve().as_posix().replace("'", r"'\''")
    return f"file '{posix}'"


def write_concat_list(paths: list[Path], list_path: Path) -> None:
    text = "\n".join(concat_list_line(p) for p in paths) + "\n"
    list_path.write_text(text, encoding="utf-8")


def build_concat_cmd(ffmpeg: str, list_path: Path, dest: Path) -> list[str]:
    return [
        ffmpeg,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_path),
        "-c",
        "copy",
        "-dn",
        "-ignore_unknown",
        str(dest),
    ]


def concat_with_chapters(
    sources: list[Path],
    dest: Path,
    titles: list[str],
    ffmpeg: str,
    ffprobe: str,
    skip_chapters: bool = False,
) -> None:
    if not sources:
        raise FfmpegError("No source files to concatenate")
    dest.parent.mkdir(parents=True, exist_ok=True)
    total = sum(p.stat().st_size for p in sources if p.exists())
    ensure_split_space(dest.parent, total)
    durations = [probe_duration_ms(path, ffprobe) for path in sources]
    chapters = chapters_from_durations(titles, durations)
    list_path = dest.with_name(f".{dest.stem}.concat.txt")
    concat_temp = dest.with_name(f".{dest.stem}.concat.tmp{dest.suffix}")
    try:
        write_concat_list(sources, list_path)
        cmd = build_concat_cmd(ffmpeg, list_path, concat_temp)
        result = run_command(cmd)
        if result.returncode != 0:
            raise FfmpegError(
                f"ffmpeg concat failed for {dest.name}: {result.stderr.strip()[-2000:]}"
            )
        if not probe_split_ok(concat_temp, ffprobe):
            raise FfmpegError(f"Concat produced no video for {dest.name}; originals left untouched")
        if skip_chapters or not chapters:
            if dest.exists() and dest.resolve() not in {p.resolve() for p in sources} and dest.resolve() != concat_temp.resolve():
                dest.unlink()
            concat_temp.replace(dest)
        else:
            remux_with_chapters(
                concat_temp,
                dest,
                chapters,
                ffmpeg,
                ffprobe,
                mov_faststart=dest.suffix.lower() in {".mp4", ".m4v"},
            )
            if concat_temp.exists() and concat_temp.resolve() != dest.resolve():
                concat_temp.unlink()
            if probe_chapter_count(dest, ffprobe) < 1:
                raise FfmpegError(f"Concat remux produced no chapters for {dest.name}")
        dest_resolved = dest.resolve()
        for source in sources:
            if source.exists() and source.resolve() != dest_resolved:
                source.unlink()
            leftover_nfo = source.with_suffix(".nfo")
            if leftover_nfo.exists() and leftover_nfo.suffix.lower() == ".nfo":
                leftover_nfo.unlink()
    except Exception:
        if concat_temp.exists() and (not dest.exists() or concat_temp.resolve() != dest.resolve()):
            concat_temp.unlink()
        raise
    finally:
        if list_path.exists():
            list_path.unlink()
