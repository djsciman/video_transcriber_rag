"""Accept-time ruleset lock and open-time playback path resolution."""

from __future__ import annotations

from pathlib import Path

LOCKED_INSTRUCTIONAL_RULESETS = {
    "Finishing Leg Locks": "no-gi",
    "Master The Move Arm Drags": "no-gi",
    "Master The Move The Side Crucifix": "no-gi",
    "Jay Rods Judo": "no-gi",
    "Half Guard Passing and Dynamic Pins": "gi",
    "Mastering The Knee Weave System": "gi",
}

_VIDEO_SUFFIXES = frozenset({".mp4", ".mkv", ".mov", ".avi", ".webm", ".m4v"})


def instructional_ruleset(name: str, ruleset: str | None = None) -> str:
    return LOCKED_INSTRUCTIONAL_RULESETS.get(name, ruleset or "")


def playback_handle(video_file: str, timestamp: float) -> str:
    return f"{video_file}@{timestamp}"


def apply_statement_edits(statement: dict, *, movement=None, step_bullets=None) -> dict:
    draft = dict(statement)
    if movement is not None:
        draft["movement"] = movement
    if step_bullets is not None:
        bullets = tuple(step_bullets)
        draft["step_bullets"] = bullets
        draft["cleaned_statement"] = " ".join(bullets)
    return draft


def resolve_video_playback(
    *,
    video_root,
    transcript_folder: str,
    video_file: str,
    speech_start: float,
) -> tuple[Path, float, bool]:
    named = Path(video_root) / transcript_folder / video_file
    available = named.is_file() and named.suffix.casefold() in _VIDEO_SUFFIXES
    return named, float(speech_start), available
