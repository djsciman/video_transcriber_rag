from __future__ import annotations

import re
from pathlib import Path

from .models import ParsedVideo

VIDEO_EXTS = {".mp4", ".mkv", ".webm", ".m4v"}
ILLEGAL_FS = re.compile(r'[<>:"/\\|?*]')
YOUTUBE_ID = re.compile(r"\s*\[[a-zA-Z0-9_-]{10,13}\]\s*")
# Jellyfin treats "Pt 1" / "Part 1" as an episode number with no season, which
# puts the same files in Season 1 and Season Unknown.
_PART_NUMBER = re.compile(r"\b(?:Pt|Part)\.?\s+(\d+)\b", re.IGNORECASE)
_PART_WORDS = {
    1: "One",
    2: "Two",
    3: "Three",
    4: "Four",
    5: "Five",
    6: "Six",
    7: "Seven",
    8: "Eight",
    9: "Nine",
    10: "Ten",
    11: "Eleven",
    12: "Twelve",
    13: "Thirteen",
    14: "Fourteen",
    15: "Fifteen",
    16: "Sixteen",
    17: "Seventeen",
    18: "Eighteen",
    19: "Nineteen",
    20: "Twenty",
}
BY_SUFFIX = re.compile(r"\s+by\s+.+$", re.IGNORECASE)
SEASON_FOLDER = re.compile(r"^Season\s*(\d+)$", re.IGNORECASE)
SXXEYY = re.compile(r"S(\d{1,2})E(\d{1,3})", re.IGNORECASE)
NEW_TOKEN = re.compile(r"(?<![A-Za-z])NEW(?![A-Za-z])", re.IGNORECASE)
# Stripped so a trailing disc number still parses (…4EXECUTIVESUMMARY → volume 4).
# It is a real course volume on some pages, not a side file.
SUMMARY_TOKEN = re.compile(r"(executive\s*summary|executivesummary)", re.IGNORECASE)
EXTRA_TOKEN = re.compile(r"(\bbonus\b|\bsample\b)", re.IGNORECASE)
VOL_PART = re.compile(
    r"(?:VOL(?:UME)?|DVD)\s*(\d+)\s*(?:PT|PART)\s*(\d+)",
    re.IGNORECASE,
)
VOL = re.compile(r"(?:DVD|VOL(?:UME)?)\s*(\d+)", re.IGNORECASE)
# "OpenGuardVolume2byJohnDanaher1": Volume 2 is the product title, 1 is the disc.
BY_DISC = re.compile(
    r"(?:^|[^A-Za-z])by\s*[A-Za-z].*?(\d+)\s*$",
    re.IGNORECASE,
)
LEADING_NUM = re.compile(r"^(\d+)\s*[-._)]\s*(.+)$")
LEADING_NUM_SPACE = re.compile(r"^(\d+)\s+(.+)$")
TRAILING_NUM = re.compile(r"^(.*?)(\d+)$")
FANATICS_SEGMENT = re.compile(r"^(\d{6,})-(\d{1,2})-(\d{1,2})-\s*(.+)$")
NAMED_SEGMENT = re.compile(r"^(\d{1,2})\.(\d{1,2})\s*[-–]\s*(.+)$")


def collapse_video_stem(path: Path) -> tuple[str, str]:
    suffix = path.suffix.lower()
    stem = path.stem
    ext = suffix if suffix in VIDEO_EXTS else suffix
    while Path(stem).suffix.lower() in VIDEO_EXTS:
        nested = Path(stem).suffix.lower()
        stem = Path(stem).stem
        if nested in VIDEO_EXTS:
            ext = nested
    return stem, ext


def jellyfin_safe_name(name: str) -> str:
    """Rewrite part-numbers Jellyfin would parse as a season-less episode."""

    def repl(match: re.Match[str]) -> str:
        number = int(match.group(1))
        word = _PART_WORDS.get(number)
        if word:
            return f"Part {word}"
        return f"PartNo{number}"

    return _PART_NUMBER.sub(repl, name)


def sanitize_filename(name: str, max_len: int = 150) -> str:
    cleaned = ILLEGAL_FS.sub("", name)
    cleaned = jellyfin_safe_name(cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip().rstrip(". ")
    if len(cleaned) > max_len:
        cleaned = cleaned[:max_len].rstrip(". ")
    return cleaned or "Untitled"


def series_stem(folder_name: str) -> str:
    return BY_SUFFIX.sub("", folder_name).strip() or folder_name.strip()


def show_title(folder_name: str, instructors: list[str]) -> str:
    stem = series_stem(folder_name)
    unique: list[str] = []
    seen: set[str] = set()
    for name in instructors:
        key = name.strip().lower()
        if name.strip() and key not in seen:
            seen.add(key)
            unique.append(name.strip())
    if len(unique) == 1:
        instructor = unique[0]
        if re.search(rf"\s+by\s+{re.escape(instructor)}\s*$", stem, re.IGNORECASE):
            return jellyfin_safe_name(stem)
        return jellyfin_safe_name(f"{stem} by {instructor}")
    if len(unique) > 1:
        if re.search(r"\s+by\s+various\s*$", stem, re.IGNORECASE):
            return jellyfin_safe_name(stem)
        return jellyfin_safe_name(f"{stem} by Various")
    return jellyfin_safe_name(stem)


def show_slug(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return f"show:{slug}"


def season_folder_name(number: int) -> str:
    return f"Season {number:02d}"


def season_folder_number(name: str) -> int | None:
    match = SEASON_FOLDER.match(name.strip())
    return int(match.group(1)) if match else None


def is_generic_season_name(name: str) -> bool:
    return season_folder_number(name or "") is not None


def _strip_noise(stem: str) -> str:
    text = YOUTUBE_ID.sub(" ", stem)
    text = text.replace("_", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _looks_descriptive(text: str) -> bool:
    if not text:
        return False
    if re.search(r"[a-z][A-Z]", text):
        return False
    if " " in text or "-" in text:
        return True
    return text.isalpha() and 2 <= len(text) <= 40


def _strip_suffixes(title: str, *suffixes: str) -> str:
    result = title.strip()
    changed = True
    while changed:
        changed = False
        for suffix in suffixes:
            suffix = suffix.strip()
            if not suffix:
                continue
            pattern = re.compile(rf"\s*[-–]\s*{re.escape(suffix)}\s*$", re.IGNORECASE)
            updated = pattern.sub("", result).strip()
            if updated != result:
                result = updated
                changed = True
    return result


def parse_video(path: Path, season_title: str = "", show_stem: str = "") -> ParsedVideo:
    stem, ext = collapse_video_stem(path)
    raw = _strip_noise(stem)
    is_new = bool(NEW_TOKEN.search(raw))
    is_extra = bool(EXTRA_TOKEN.search(raw))
    already_named = bool(SXXEYY.search(raw))
    working = NEW_TOKEN.sub(" ", raw)
    working = EXTRA_TOKEN.sub(" ", working)
    working = SUMMARY_TOKEN.sub(" ", working)
    working = re.sub(r"\s+", " ", working).strip()

    volume: int | None = None
    part: int | None = None
    chapter: int | None = None
    is_segmented_name = False
    remainder = working

    fan = FANATICS_SEGMENT.match(working)
    named = NAMED_SEGMENT.match(working)
    if fan:
        volume = int(fan.group(2))
        chapter = int(fan.group(3))
        remainder = fan.group(4).strip()
        is_segmented_name = True
    elif named:
        volume = int(named.group(1))
        chapter = int(named.group(2))
        remainder = named.group(3).strip()
        is_segmented_name = True
        already_named = True
    else:
        sxx = SXXEYY.search(working)
        if sxx:
            volume = int(sxx.group(2))
            remainder = working[sxx.end() :].lstrip(" -–") or working[: sxx.start()].rstrip(" -–")
        else:
            vol_part = VOL_PART.search(working)
            if vol_part:
                volume = int(vol_part.group(1))
                part = int(vol_part.group(2))
                remainder = (working[: vol_part.start()] + " " + working[vol_part.end() :]).strip()
            else:
                vol = VOL.search(working)
                if vol:
                    by_disc = BY_DISC.search(working[vol.end() :])
                    if by_disc:
                        volume = int(by_disc.group(1))
                        remainder = ""
                    else:
                        volume = int(vol.group(1))
                        remainder = (working[: vol.start()] + " " + working[vol.end() :]).strip()
                else:
                    lead = LEADING_NUM.match(working) or LEADING_NUM_SPACE.match(working)
                    if lead:
                        volume = int(lead.group(1))
                        remainder = lead.group(2).strip()
                    else:
                        compact = re.sub(r"[\s._-]+", "", working)
                        trail = TRAILING_NUM.match(compact)
                        if trail and trail.group(1) and not trail.group(1)[-1:].isdigit():
                            volume = int(trail.group(2))
                            remainder = trail.group(1)

    remainder = remainder.strip(" -._")
    remainder = _strip_suffixes(remainder, season_title, show_stem, series_stem(show_stem))
    local_title = remainder if _looks_descriptive(remainder) else None
    if local_title and not is_segmented_name:
        local_title = re.sub(r"^\d+\s*[-.]?\s*", "", local_title).strip() or local_title

    return ParsedVideo(
        path=path,
        volume_number=volume,
        part_number=part,
        is_new=is_new,
        is_extra=is_extra,
        local_title=local_title,
        already_named=already_named,
        extension=ext,
        chapter_number=chapter,
        is_segmented_name=is_segmented_name,
    )


def episode_filename(volume_number: int, chapter_number: int, title: str, ext: str) -> str:
    ep_title = sanitize_filename(title)
    suffix = ext if ext.startswith(".") else f".{ext}"
    return f"{volume_number:02d}.{chapter_number:02d} - {ep_title}{suffix}"


def volume_episode_filename(
    show_title_text: str,
    season: int,
    episode: int,
    title: str,
    ext: str,
) -> str:
    show = sanitize_filename(show_title_text)
    ep_title = sanitize_filename(title)
    suffix = ext if ext.startswith(".") else f".{ext}"
    return f"{show} - S{season:02d}E{episode:02d} - {ep_title}{suffix}"


def episode_display_title(volume_number: int, chapter_number: int, chapter_title: str) -> str:
    text = (chapter_title or "").strip() or f"Chapter {chapter_number}"
    return f"{volume_number}.{chapter_number} {text}"


def pick_volume_title(parsed: ParsedVideo, volume_name: str, volume_number: int) -> str:
    if not parsed.is_segmented_name and parsed.local_title:
        return parsed.local_title
    name = (volume_name or "").strip()
    if name:
        return name
    return f"Volume {volume_number}"


def pick_chapter_title(parsed: ParsedVideo, scraped_title: str, chapter_number: int) -> str:
    if parsed.is_segmented_name and parsed.local_title:
        return parsed.local_title
    scraped = (scraped_title or "").strip()
    if scraped:
        return scraped
    if parsed.local_title:
        return parsed.local_title
    return f"Chapter {chapter_number}"
