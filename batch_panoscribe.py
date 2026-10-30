#!/usr/bin/env python3
"""
Complete each volume transcript in one batch run.

Speech is requested only when the transcript has no speech list. Chapters are
copied from the video container when the stored list is missing or differs.
The video file name is written when it is missing, empty, or different.
Existing speech stays in place.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable

VIDEO_EXTS = {".mp4", ".mkv", ".avi", ".mov", ".webm", ".m4v", ".flv", ".wmv"}

# MAX_PATH includes the terminating NUL, so a normal Windows path of 260
# characters or more fails to open with FileNotFoundError. LongPathsEnabled
# is off on this machine. The \\?\ prefix bypasses that limit.
_WINDOWS_MAX_PATH = 260

_HOTWORD_FILLER = {
    "intro",
    "introduction",
    "to",
    "the",
    "a",
    "an",
    "of",
    "and",
    "in",
    "on",
    "for",
    "with",
    "overview",
    "summary",
    "conclusion",
    "troubleshooting",
    "important",
    "concepts",
    "concept",
    "main",
    "attacks",
    "attack",
    "chapter",
}

_HOTWORD_TOKEN_LIMIT = 223

ChapterCommand = Callable[[Path], list[dict]]
SpeechCommand = Callable[[Path, Path, str | None, bool], None]
TokenCounter = Callable[[str], int]


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


def round_chapter_time(value: float) -> float:
    return round(float(value) * 1000.0) / 1000.0


def normalize_container_chapters(raw_chapters: list[dict]) -> list[dict]:
    """Normalize container chapters to stored transcript shape."""
    chapters = []
    for index, chapter in enumerate(raw_chapters, start=1):
        title = str(chapter.get("title") or "").strip()
        if not title:
            title = f"Chapter {index}"
        chapters.append(
            {
                "title": title,
                "start": round_chapter_time(chapter["start"]),
                "end": round_chapter_time(chapter["end"]),
            }
        )
    return chapters


def extract_chapters(video_path: Path) -> list[dict]:
    """Read container chapters via ffprobe.

    Each entry is ``{"title", "start", "end"}`` with times in seconds,
    matching transcript segment timestamps.
    """
    video_path = io_path(video_path)
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_chapters",
        str(video_path),
    ]
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    payload = json.loads(result.stdout or "{}")
    chapters = []
    for index, chapter in enumerate(payload.get("chapters") or [], start=1):
        chapters.append(
            {
                "title": _chapter_title(chapter, index),
                "start": _chapter_seconds(chapter, "start"),
                "end": _chapter_seconds(chapter, "end"),
            }
        )
    return normalize_container_chapters(chapters)


def output_path_for(video: Path, input_dir: Path, output_dir: Path) -> Path:
    """JSON path that mirrors ``video``'s location under ``input_dir``."""
    rel = video.relative_to(input_dir)
    return output_dir / rel.with_suffix(".json")


def walk_videos(input_dir: Path) -> list[Path]:
    """Return video files under ``input_dir``, using extended paths on Windows."""
    root = io_path(input_dir)
    videos: list[Path] = []
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            path = Path(dirpath) / name
            if is_video(path):
                videos.append(path)
    videos.sort(key=lambda p: str(p).lower())
    return videos


def transcripts_by_video(input_dir: Path, output_dir: Path) -> list[tuple[Path, list[Path]]]:
    """Pair each transcript path with the videos that mirror onto it.

    Two videos that share a folder and a file name aside from the extension
    land on one transcript. Callers must not pick between them.
    """
    grouped: dict[Path, list[Path]] = {}
    order: list[Path] = []
    for video in walk_videos(input_dir):
        # Rebuild a path relative to input_dir without the extended prefix.
        try:
            rel = video.relative_to(io_path(input_dir))
        except ValueError:
            rel = Path(os.path.relpath(video, start=os.path.abspath(input_dir)))
        logical_video = input_dir / rel
        out = output_path_for(logical_video, input_dir, output_dir)
        if out not in grouped:
            order.append(out)
            grouped[out] = []
        grouped[out].append(logical_video)
    return [(out, grouped[out]) for out in order]


def _words_from_title(title: str) -> list[str]:
    # Drop brackets/parens; split on whitespace. Punctuation that sits alone
    # between spaces (e.g. " - ") is removed as its own token. Leading and
    # trailing punctuation on a token is stripped; hyphen, slash, and
    # apostrophe inside a word stay.
    text = re.sub(r"[()\[\]{}]", "", title)
    words: list[str] = []
    for token in text.split():
        if re.fullmatch(r"[^\w]+", token, flags=re.UNICODE):
            continue
        token = re.sub(r"^[^\w]+|[^\w]+$", "", token, flags=re.UNICODE)
        if not token:
            continue
        if re.fullmatch(r"\d+", token):
            continue
        if token.lower() in _HOTWORD_FILLER:
            continue
        words.append(token)
    return words


def build_hotword_string(
    titles: list[str],
    count_hotword_tokens: TokenCounter,
) -> str | None:
    """Build a hotword string from container chapter titles."""
    kept: list[str] = []
    seen: set[str] = set()
    for title in titles:
        candidates = _words_from_title(title)
        fresh = [word for word in candidates if word.lower() not in seen]
        if not fresh:
            continue
        trial = " ".join(kept + fresh)
        if count_hotword_tokens(trial) > _HOTWORD_TOKEN_LIMIT:
            break
        for word in fresh:
            seen.add(word.lower())
            kept.append(word)
    if not kept:
        return None
    return " ".join(kept)


_tokenizer = None


def default_count_hotword_tokens(text: str) -> int:
    """Count hotword tokens the way faster-whisper does, with a leading space."""
    global _tokenizer
    if _tokenizer is None:
        from tokenizers import Tokenizer

        candidates = []
        hub = Path.home() / ".cache" / "huggingface" / "hub"
        if hub.is_dir():
            for model_dir in hub.glob("models--*whisper*"):
                snaps = model_dir / "snapshots"
                if snaps.is_dir():
                    for snap in snaps.iterdir():
                        tok = snap / "tokenizer.json"
                        if tok.is_file():
                            candidates.append(tok)
        if not candidates:
            raise RuntimeError("Whisper tokenizer.json not found for hotword counting")
        # Prefer large-v3-turbo when present.
        preferred = [p for p in candidates if "large-v3-turbo" in str(p)]
        _tokenizer = Tokenizer.from_file(str((preferred or candidates)[0]))
    return len(_tokenizer.encode(" " + text.strip(), add_special_tokens=False).ids)


def chapters_equal(left: list[dict], right: list[dict]) -> bool:
    if len(left) != len(right):
        return False
    for a, b in zip(left, right):
        if a.get("title") != b.get("title"):
            return False
        try:
            if abs(float(a["start"]) - float(b["start"])) > 0.001:
                return False
            if abs(float(a["end"]) - float(b["end"])) > 0.001:
                return False
        except (TypeError, ValueError, KeyError):
            return False
    return True


class TranscriptError(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def inspect_transcript(path: Path) -> tuple[dict | None, dict]:
    """Load a transcript and report which fields are present.

    Returns ``(data_or_None_if_missing, info)`` where ``info`` has:
    ``segments_present``, ``segments``, ``chapters_present``, ``chapters``,
    ``video_file_present``, ``video_file``.
    """
    io_target = io_path(path)
    if not io_target.exists():
        return None, {
            "segments_present": False,
            "segments": None,
            "chapters_present": False,
            "chapters": None,
            "video_file_present": False,
            "video_file": None,
        }

    try:
        raw = json.loads(io_target.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as e:
        raise TranscriptError("unreadable") from e

    if isinstance(raw, list):
        data: dict = {"segments": raw}
    elif isinstance(raw, dict):
        data = dict(raw)
    else:
        raise TranscriptError("wrong shape")

    if "segments" in data:
        if not isinstance(data["segments"], list):
            raise TranscriptError("wrong shape")
        segments_present = True
        segments = data["segments"]
    else:
        segments_present = False
        segments = None

    if "chapters" in data:
        chapters = data["chapters"]
        if not isinstance(chapters, list):
            raise TranscriptError("wrong shape")
        for chapter in chapters:
            if not isinstance(chapter, dict):
                raise TranscriptError("wrong shape")
            title = chapter.get("title")
            if not isinstance(title, str) or not title.strip():
                raise TranscriptError("wrong shape")
            for key in ("start", "end"):
                value = chapter.get(key)
                if isinstance(value, bool) or not isinstance(value, (int, float)):
                    raise TranscriptError("wrong shape")
        chapters_present = True
    else:
        chapters_present = False
        chapters = None

    if "video_file" in data:
        video_file = data["video_file"]
        if video_file is None:
            raise TranscriptError("wrong shape")
        if not isinstance(video_file, str):
            raise TranscriptError("wrong shape")
        if video_file == "":
            video_file_present = False
            video_file = None
        else:
            video_file_present = True
    else:
        video_file_present = False
        video_file = None

    return data, {
        "segments_present": segments_present,
        "segments": segments,
        "chapters_present": chapters_present,
        "chapters": chapters,
        "video_file_present": video_file_present,
        "video_file": video_file,
    }


def _compose_transcript(
    existing: dict | None,
    *,
    segments: list | None,
    language: str | None,
    chapters: list | None,
    set_chapters: bool,
    video_file: str | None,
    set_video_file: bool,
) -> dict:
    ordered: dict = {}
    if set_video_file and video_file is not None:
        ordered["video_file"] = video_file
    elif existing and isinstance(existing.get("video_file"), str) and existing["video_file"]:
        ordered["video_file"] = existing["video_file"]

    if set_chapters:
        ordered["chapters"] = chapters if chapters is not None else []
    elif existing and "chapters" in existing:
        ordered["chapters"] = existing["chapters"]

    skip = {"video_file", "chapters", "segments", "language"}
    if existing:
        for key, value in existing.items():
            if key in skip or key in ordered:
                continue
            ordered[key] = value

    if language is not None:
        ordered["language"] = language
    elif existing and "language" in existing:
        ordered["language"] = existing["language"]

    if segments is not None:
        ordered["segments"] = segments
    elif existing and "segments" in existing:
        ordered["segments"] = existing["segments"]

    return ordered


def _atomic_write_json(path: Path, data: dict) -> None:
    target = io_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(target.parent),
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(json.dumps(data, indent=2, ensure_ascii=False) + "\n")
        os.replace(tmp_path, target)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink()
        raise


def default_speech_command(
    video_path: Path,
    aside_path: Path,
    hotwords: str | None,
    ocr: bool,
) -> None:
    """Transcribe with faster-whisper hotwords; panoscribe CLI cannot take them."""
    from panoscribe.asr.whisper import WhisperTranscriber
    from panoscribe.audio import extract_audio
    from panoscribe.config import PanoScribeConfig
    from panoscribe.output import Transcript, write_json
    from panoscribe.pipeline import process_single_video

    source = io_path(video_path)
    aside = io_path(aside_path)
    aside.parent.mkdir(parents=True, exist_ok=True)

    if ocr:
        config = PanoScribeConfig()
        original = WhisperTranscriber.transcribe

        def transcribe_with_hotwords(self, audio_path: Path):
            pipeline = self._ensure_loaded()
            kwargs = {
                "language": self._config.whisper_language,
                "batch_size": self._config.whisper_batch_size,
                "vad_filter": True,
                "word_timestamps": False,
                "task": self._config.whisper_task,
            }
            if hotwords:
                kwargs["hotwords"] = hotwords
            segments_gen, info = pipeline.transcribe(str(audio_path), **kwargs)
            from panoscribe.output import TranscriptSegment

            segment_language = (
                "en" if self._config.whisper_task == "translate" else info.language
            )
            segments = [
                TranscriptSegment(
                    start=float(s.start),
                    end=float(s.end),
                    text=s.text.strip(),
                    asr_logprob=getattr(s, "avg_logprob", None),
                    language=segment_language,
                )
                for s in segments_gen
            ]
            return segments, info.language

        WhisperTranscriber.transcribe = transcribe_with_hotwords  # type: ignore[method-assign]
        try:
            process_single_video(
                str(source),
                config,
                aside,
                ocr_active=True,
                output_format="json",
            )
        finally:
            WhisperTranscriber.transcribe = original  # type: ignore[method-assign]
        return

    config = PanoScribeConfig()
    with tempfile.TemporaryDirectory(prefix="batch_panoscribe_") as tmp:
        audio_path = extract_audio(source, Path(tmp) / "audio.wav")
        engine = WhisperTranscriber(config)
        pipeline = engine._ensure_loaded()
        kwargs = {
            "language": config.whisper_language,
            "batch_size": config.whisper_batch_size,
            "vad_filter": True,
            "word_timestamps": False,
            "task": config.whisper_task,
        }
        if hotwords:
            kwargs["hotwords"] = hotwords
        segments_gen, info = pipeline.transcribe(str(audio_path), **kwargs)
        from panoscribe.output import TranscriptSegment

        segment_language = "en" if config.whisper_task == "translate" else info.language
        segments = [
            TranscriptSegment(
                start=float(s.start),
                end=float(s.end),
                text=s.text.strip(),
                asr_logprob=getattr(s, "avg_logprob", None),
                language=segment_language,
            )
            for s in segments_gen
        ]
        write_json(Transcript(segments=segments, language=info.language), aside)


def command_available(name: str) -> bool:
    return shutil.which(name) is not None


def speech_program_available() -> bool:
    if command_available("panoscribe"):
        return True
    try:
        import panoscribe  # noqa: F401

        return True
    except ImportError:
        return False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Complete each volume transcript without repeating speech."
    )
    parser.add_argument("input_dir", type=Path, help="Root directory of videos")
    parser.add_argument("output_dir", type=Path, help="Root directory for JSON outputs")
    parser.add_argument(
        "--ocr",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Enable or disable on-screen OCR (default: disabled). "
        "Passed only when speech is requested.",
    )
    return parser


def _fail_line(label: str, reason: str, detail: str = "") -> None:
    suffix = f" ({reason})"
    if detail:
        suffix += f": {detail}"
    print(f"FAIL  {label}{suffix}")


def process_volume(
    video: Path,
    output_path: Path,
    *,
    ocr: bool,
    speech_command: SpeechCommand,
    chapter_command: ChapterCommand,
    count_hotword_tokens: TokenCounter,
) -> str:
    """Process one volume. Returns created, updated, unchanged, or a fail reason."""
    try:
        existing, info = inspect_transcript(output_path)
    except TranscriptError as e:
        _fail_line(str(video), e.reason)
        return f"fail:{e.reason}"

    need_speech = not info["segments_present"]
    container_chapters = None
    container_error = None
    hotwords = None

    # Always need the container when creating/updating chapters, and before speech
    # so hotwords can be built. A failure is recorded and speech may still run.
    try:
        container_chapters = normalize_container_chapters(chapter_command(io_path(video)))
    except Exception as e:
        container_error = e

    if need_speech:
        if container_chapters is not None:
            hotwords = build_hotword_string(
                [chapter["title"] for chapter in container_chapters],
                count_hotword_tokens,
            )
        aside_path = None
        try:
            io_path(output_path).parent.mkdir(parents=True, exist_ok=True)
            fd, aside_name = tempfile.mkstemp(
                prefix=f".{output_path.stem}.speech.",
                suffix=".json",
                dir=str(io_path(output_path).parent),
            )
            os.close(fd)
            aside_path = Path(aside_name)
            speech_command(io_path(video), io_path(aside_path), hotwords, ocr)
            speech_payload = json.loads(io_path(aside_path).read_text(encoding="utf-8"))
            if isinstance(speech_payload, list):
                speech_segments = speech_payload
                speech_language = None
            elif isinstance(speech_payload, dict):
                speech_segments = speech_payload.get("segments")
                if not isinstance(speech_segments, list):
                    raise RuntimeError("speech result missing segments list")
                speech_language = speech_payload.get("language")
            else:
                raise RuntimeError("speech result has unexpected shape")
        except Exception as e:
            detail = e.stderr if isinstance(e, subprocess.CalledProcessError) else e
            _fail_line(str(video), "speech", str(detail))
            return "fail:speech"
        finally:
            if aside_path is not None:
                io_path(aside_path).unlink(missing_ok=True)
    else:
        speech_segments = info["segments"]
        speech_language = None

    set_chapters = False
    new_chapters = info["chapters"]
    chapter_fail = False

    if container_error is not None:
        chapter_fail = True
    elif container_chapters is not None:
        if not info["chapters_present"]:
            set_chapters = True
            new_chapters = container_chapters
        elif not container_chapters:
            # Empty container leaves an existing valid list in place.
            set_chapters = False
            new_chapters = info["chapters"]
        elif not chapters_equal(info["chapters"], container_chapters):
            set_chapters = True
            new_chapters = container_chapters

    set_video_file = False
    new_video_file = info["video_file"]
    if not info["video_file_present"] or info["video_file"] != video.name:
        set_video_file = True
        new_video_file = video.name

    changed = need_speech or set_chapters or set_video_file
    if not changed:
        if chapter_fail:
            _fail_line(str(video), "chapters", str(container_error))
            return "fail:chapters"
        return "unchanged"

    if chapter_fail:
        # Save speech and/or video_file when missing; never touch chapters.
        composed = _compose_transcript(
            existing,
            segments=speech_segments if need_speech else (existing or {}).get("segments"),
            language=speech_language if need_speech else None,
            chapters=None,
            set_chapters=False,
            video_file=new_video_file,
            set_video_file=set_video_file or (need_speech and existing is None),
        )
    else:
        composed = _compose_transcript(
            existing,
            segments=speech_segments if need_speech else (existing or {}).get("segments"),
            language=speech_language if need_speech else None,
            chapters=new_chapters,
            set_chapters=set_chapters,
            video_file=new_video_file,
            set_video_file=set_video_file or (need_speech and existing is None),
        )

    try:
        _atomic_write_json(output_path, composed)
    except Exception as e:
        _fail_line(str(video), "speech" if need_speech else "chapters", str(e))
        return "fail:write"

    if chapter_fail:
        _fail_line(str(video), "chapters", str(container_error))
        return "fail:chapters"

    if existing is None:
        print(f"CREATE {video} -> {output_path}")
        return "created"
    print(f"UPDATE {video} -> {output_path}")
    return "updated"


def run(
    input_dir: Path,
    output_dir: Path,
    *,
    ocr: bool = False,
    speech_command: SpeechCommand | None = None,
    chapter_command: ChapterCommand | None = None,
    speech_available: bool | None = None,
    chapter_available: bool | None = None,
    count_hotword_tokens: TokenCounter | None = None,
) -> int:
    """Complete every volume under ``input_dir``. Returns process exit status."""
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)

    if not io_path(input_dir).is_dir():
        print(f"Error: {input_dir} is not a directory", file=sys.stderr)
        return 1

    if chapter_available is None:
        chapter_available = command_available("ffprobe")
    if not chapter_available:
        print("Error: ffprobe is not available", file=sys.stderr)
        return 1

    speech_command = speech_command or default_speech_command
    chapter_command = chapter_command or extract_chapters
    count_hotword_tokens = count_hotword_tokens or default_count_hotword_tokens

    pairs = transcripts_by_video(input_dir, output_dir)
    if not pairs:
        print("Found 0 video(s)")
        print("\nDone. Created: 0  Updated: 0  Unchanged: 0  Failed: 0")
        return 0

    # Decide whether any volume needs speech before checking the speech program.
    needs_speech = False
    for out, videos in pairs:
        if len(videos) != 1:
            continue
        try:
            _existing, info = inspect_transcript(out)
        except TranscriptError:
            continue
        if not info["segments_present"]:
            needs_speech = True

    if needs_speech:
        if speech_available is None:
            speech_available = speech_program_available()
        if not speech_available:
            print("Error: speech program is not available", file=sys.stderr)
            return 1

    print(f"Found {sum(len(videos) for _out, videos in pairs)} video(s)")

    created = updated = unchanged = failed = 0
    for out, videos in pairs:
        if len(videos) != 1:
            failed += 1
            print(f"FAIL  {len(videos)} videos share {out} (shared path)")
            for video in videos:
                print(f"      {video}")
            continue

        video = videos[0]
        result = process_volume(
            video,
            out,
            ocr=ocr,
            speech_command=speech_command,
            chapter_command=chapter_command,
            count_hotword_tokens=count_hotword_tokens,
        )
        if result == "created":
            created += 1
        elif result == "updated":
            updated += 1
        elif result == "unchanged":
            unchanged += 1
        else:
            failed += 1

    print(
        f"\nDone. Created: {created}  Updated: {updated}  "
        f"Unchanged: {unchanged}  Failed: {failed}"
    )
    return 1 if failed else 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return run(args.input_dir, args.output_dir, ocr=args.ocr)


if __name__ == "__main__":
    sys.exit(main())
