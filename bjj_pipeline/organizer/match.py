from __future__ import annotations

from pathlib import Path

from .chapters import chapters_have_timeline
from .errors import MatchError
from .models import Chapter, ChapterMatch, ParsedVideo, SeasonMatch, Volume
from .naming import parse_video, pick_chapter_title


def parse_videos(
    files: list[Path],
    season_title: str = "",
    show_stem: str = "",
) -> list[ParsedVideo]:
    return [parse_video(path, season_title=season_title, show_stem=show_stem) for path in files]


def _sort_key(item: ParsedVideo) -> tuple[int, int, str]:
    vol = item.volume_number if item.volume_number is not None else 10_000
    part = item.part_number if item.part_number is not None else 0
    return (vol, part, item.path.name.lower())


def _segment_sort_key(item: ParsedVideo) -> tuple[int, int, str]:
    vol = item.volume_number if item.volume_number is not None else 10_000
    ch = item.chapter_number if item.chapter_number is not None else 0
    return (vol, ch, item.path.name.lower())


def flatten_chapters(volumes: list[Volume]) -> list[tuple[int, int, Volume, Chapter]]:
    out: list[tuple[int, int, Volume, Chapter]] = []
    for v_idx, volume in enumerate(volumes, start=1):
        chapters = volume.chapters or (Chapter(volume.name or f"Volume {v_idx}", 0),)
        for c_idx, chapter in enumerate(chapters, start=1):
            out.append((v_idx, c_idx, volume, chapter))
    return out


def detect_media_mode(parsed: list[ParsedVideo], volumes: list[Volume]) -> str:
    work = [p for p in parsed if not p.is_extra]
    file_count = len(work)
    volume_count = len(volumes)
    chapter_count = len(flatten_chapters(volumes)) if volumes else 0
    if any(p.is_segmented_name for p in work):
        return "segmented"
    if not volumes:
        raise MatchError("Product page has no Course Content volumes to match against")
    if file_count == chapter_count and file_count != volume_count:
        return "segmented"
    if file_count == chapter_count == volume_count:
        return "segmented"
    numbered = [p for p in work if p.volume_number is not None]
    if volume_count and (file_count == volume_count or len(numbered) >= volume_count):
        return "volume"
    raise MatchError(
        f"Cannot tell segmented vs volume layout: {file_count} local file(s), "
        f"{volume_count} scraped volume(s), {chapter_count} scraped chapter(s)."
    )


def match_volumes(
    files: list[Path],
    volumes: list[Volume],
    season_title: str = "",
    show_stem: str = "",
) -> tuple[list[tuple[ParsedVideo, Volume]], list[Path], list[str]]:
    parsed = parse_videos(files, season_title=season_title, show_stem=show_stem)
    warnings: list[str] = []
    extras: list[Path] = []
    numbered: dict[tuple[int, int], list[ParsedVideo]] = {}
    unparsed: list[ParsedVideo] = []

    for item in parsed:
        if item.is_extra:
            extras.append(item.path)
            continue
        if item.volume_number is None:
            unparsed.append(item)
            continue
        key = (item.volume_number, item.part_number or 0)
        numbered.setdefault(key, []).append(item)

    chosen: list[ParsedVideo] = []
    for key, group in sorted(numbered.items()):
        if len(group) == 1:
            chosen.append(group[0])
            continue
        news = [g for g in group if g.is_new]
        if len(news) == 1:
            chosen.append(news[0])
            extras.extend(g.path for g in group if g is not news[0])
            warnings.append(f"Using NEW file for volume {key[0]}: {news[0].path.name}")
            continue
        names = ", ".join(g.path.name for g in group)
        raise MatchError(f"Duplicate volume {key[0]} with no single NEW winner: {names}")

    chosen.sort(key=_sort_key)

    if not volumes:
        raise MatchError("Product page has no Course Content volumes to match against")

    if not chosen and unparsed:
        if len(unparsed) == len(volumes):
            unparsed.sort(key=lambda p: p.path.name.lower())
            warnings.append("No volume numbers in filenames; pairing by sorted name")
            pairs = list(zip(unparsed, volumes, strict=True))
            return pairs, extras, warnings
        raise MatchError(
            f"Could not parse volume numbers and file count ({len(unparsed)}) "
            f"does not match scraped volumes ({len(volumes)})"
        )

    if unparsed:
        extras.extend(p.path for p in unparsed)
        warnings.append(
            f"{len(unparsed)} file(s) had no volume number and were treated as extras"
        )

    if len(chosen) < len(volumes):
        local = [f"{c.volume_number}: {c.path.name}" for c in chosen]
        scraped = [v.name for v in volumes]
        raise MatchError(
            "Fewer local videos than scraped volumes; refusing to guess.\n"
            f"  Local ({len(chosen)}): {local}\n"
            f"  Scraped ({len(volumes)}): {scraped}"
        )

    if len(chosen) > len(volumes):
        extras.extend(c.path for c in chosen[len(volumes) :])
        warnings.append(
            f"{len(chosen) - len(volumes)} leftover video(s) after matching volumes; "
            "they will follow --extras-policy"
        )
        chosen = chosen[: len(volumes)]

    pairs = list(zip(chosen, volumes, strict=True))
    return pairs, extras, warnings


def _match_from_filenames(work: list[ParsedVideo]) -> SeasonMatch:
    items: list[ChapterMatch] = []
    for parsed in sorted(work, key=_segment_sort_key):
        v_num = parsed.volume_number or 1
        c_num = parsed.chapter_number or 1
        title = parsed.local_title or f"Chapter {c_num}"
        items.append(
            ChapterMatch(
                parsed=parsed,
                volume_name=f"Volume {v_num}",
                chapter=Chapter(title, 0),
                volume_number=v_num,
                chapter_number=c_num,
                mode="segmented",
                chapter_title=title,
            )
        )
    return SeasonMatch(mode="segmented", items=items, extras=[], warnings=[])


def _contiguous(numbers: list[int]) -> bool:
    return bool(numbers) and numbers == list(range(numbers[0], numbers[-1] + 1))


def _align_bundle_volume_numbers(
    by_key: dict[tuple[int, int], list[ParsedVideo]],
    flat: list[tuple[int, int, Volume, Chapter]],
) -> tuple[dict[tuple[int, int], list[ParsedVideo]], str | None]:
    """Map bundle-wide disc numbers onto one product's restarted volume list.

    The No Gi Open Guard downloads keep a single sequence: K Guard is 01-08,
    De La Riva is 09-16, RDLR is 17-24. Each product page numbers its own
    course content from Volume 1.
    """
    if not by_key or not flat:
        return by_key, None
    local_vols = sorted({vol for vol, _ in by_key})
    scraped_vols = sorted({vol for vol, _, _, _ in flat})
    if len(local_vols) != len(scraped_vols):
        return by_key, None
    if not _contiguous(local_vols) or not _contiguous(scraped_vols):
        return by_key, None
    offset = local_vols[0] - scraped_vols[0]
    if offset == 0:
        return by_key, None
    shifted: dict[tuple[int, int], list[ParsedVideo]] = {}
    for (vol, chapter), group in by_key.items():
        shifted.setdefault((vol - offset, chapter), []).extend(group)

    def _hits(keys: dict[tuple[int, int], list[ParsedVideo]]) -> int:
        return sum(1 for vol, chapter, _, _ in flat if (vol, chapter) in keys)

    # Disc 9 of a 9-volume product collides with that product's own Volume 9.
    # Shift only when the bundle alignment matches more chapters than the raw numbers.
    if _hits(shifted) <= _hits(by_key):
        return by_key, None
    note = (
        f"Filename volumes {local_vols[0]}-{local_vols[-1]} continue a bundle sequence; "
        f"aligned to course volumes {scraped_vols[0]}-{scraped_vols[-1]}"
    )
    return shifted, note


def _match_segments(
    work: list[ParsedVideo],
    volumes: list[Volume],
) -> tuple[list[ChapterMatch], list[Path], list[str]]:
    warnings: list[str] = []
    extras: list[Path] = []
    flat = flatten_chapters(volumes)
    chosen = sorted(work, key=_segment_sort_key)
    items: list[ChapterMatch] = []

    keyed = all(p.volume_number is not None and p.chapter_number is not None for p in chosen)
    if keyed:
        by_key: dict[tuple[int, int], list[ParsedVideo]] = {}
        for parsed in chosen:
            key = (parsed.volume_number or 0, parsed.chapter_number or 0)
            by_key.setdefault(key, []).append(parsed)
        by_key, align_note = _align_bundle_volume_numbers(by_key, flat)
        if align_note:
            warnings.append(align_note)
        used: set[tuple[int, int]] = set()
        for v_num, c_num, volume, chapter in flat:
            group = by_key.get((v_num, c_num), [])
            if not group:
                continue
            parsed = group[0]
            if len(group) > 1:
                extras.extend(g.path for g in group[1:])
                warnings.append(
                    f"Duplicate {v_num}.{c_num}; using {parsed.path.name}"
                )
            title = pick_chapter_title(parsed, chapter.title, c_num)
            if parsed.local_title and chapter.title and parsed.local_title.lower() != chapter.title.lower():
                warnings.append(
                    f"Title mismatch {v_num}.{c_num}: file {parsed.local_title!r} vs scrape {chapter.title!r}"
                )
            items.append(
                ChapterMatch(
                    parsed=parsed,
                    volume_name=volume.name,
                    chapter=chapter,
                    volume_number=v_num,
                    chapter_number=c_num,
                    mode="segmented",
                    chapter_title=title,
                )
            )
            used.add((v_num, c_num))
        if len(items) < len(flat):
            missing = [f"{v}.{c} {ch.title}" for v, c, _, ch in flat if (v, c) not in used]
            # A handful of absent numbered clips is not a guess. A large gap is.
            if len(items) < len(flat) * 0.9:
                missing_keys = [f"{v}.{c}" for v, c, _, _ in flat if (v, c) not in used]
                raise MatchError(
                    "Fewer local videos than scraped chapters; refusing to guess.\n"
                    f"  Missing: {missing_keys}\n"
                    f"  Scraped ({len(flat)}): {[ch.title for _, _, _, ch in flat]}"
                )
            warnings.append(
                "Missing chapter file(s); they will be skipped: " + "; ".join(missing)
            )
        for key, group in by_key.items():
            if key not in used:
                extras.extend(p.path for p in group)
        if extras:
            warnings.append(
                f"{len(extras)} leftover video(s) after matching chapters; "
                "they will follow --extras-policy"
            )
        return items, extras, warnings

    if len(chosen) < len(flat):
        raise MatchError(
            "Fewer local videos than scraped chapters; refusing to guess.\n"
            f"  Local ({len(chosen)}): {[p.path.name for p in chosen]}\n"
            f"  Scraped ({len(flat)}): {[ch.title for _, _, _, ch in flat]}"
        )
    if len(chosen) > len(flat):
        extras.extend(p.path for p in chosen[len(flat) :])
        warnings.append(
            f"{len(chosen) - len(flat)} leftover video(s) after matching chapters; "
            "they will follow --extras-policy"
        )
        chosen = chosen[: len(flat)]
    for parsed, (v_num, c_num, volume, chapter) in zip(chosen, flat, strict=True):
        title = pick_chapter_title(parsed, chapter.title, c_num)
        items.append(
            ChapterMatch(
                parsed=parsed,
                volume_name=volume.name,
                chapter=chapter,
                volume_number=v_num,
                chapter_number=c_num,
                mode="segmented",
                chapter_title=title,
            )
        )
    return items, extras, warnings


def _expand_volumes(
    pairs: list[tuple[ParsedVideo, Volume]],
    skip_chapters: bool,
) -> list[ChapterMatch]:
    items: list[ChapterMatch] = []
    for v_idx, (parsed, volume) in enumerate(pairs, start=1):
        if skip_chapters:
            title = parsed.local_title or volume.name or f"Volume {v_idx}"
            items.append(
                ChapterMatch(
                    parsed=parsed,
                    volume_name=volume.name,
                    chapter=Chapter(title, 0),
                    volume_number=v_idx,
                    chapter_number=1,
                    mode="volume",
                    chapter_title=title,
                )
            )
            continue
        chapters = volume.chapters or (Chapter(volume.name or f"Volume {v_idx}", 0),)
        titled = tuple(ch for ch in chapters if ch.title.strip())
        if len(titled) > 1 and not chapters_have_timeline(titled):
            title = parsed.local_title or volume.name or f"Volume {v_idx}"
            items.append(
                ChapterMatch(
                    parsed=parsed,
                    volume_name=volume.name,
                    chapter=Chapter(title, 0),
                    volume_number=v_idx,
                    chapter_number=1,
                    mode="volume",
                    chapter_title=title,
                    toc=titled,
                )
            )
            continue
        for c_idx, chapter in enumerate(chapters, start=1):
            end = chapters[c_idx].start_ms if c_idx < len(chapters) else None
            items.append(
                ChapterMatch(
                    parsed=parsed,
                    volume_name=volume.name,
                    chapter=chapter,
                    volume_number=v_idx,
                    chapter_number=c_idx,
                    mode="volume",
                    chapter_title=chapter.title.strip() or f"Chapter {c_idx}",
                    split_start_ms=chapter.start_ms,
                    split_end_ms=end,
                )
            )
    return items


def match_season(
    files: list[Path],
    volumes: list[Volume],
    season_title: str = "",
    show_stem: str = "",
    skip_chapters: bool = False,
) -> SeasonMatch:
    parsed = parse_videos(files, season_title=season_title, show_stem=show_stem)
    extras: list[Path] = []
    work: list[ParsedVideo] = []
    for item in parsed:
        if item.is_extra:
            extras.append(item.path)
        else:
            work.append(item)

    if not volumes:
        if work and all(p.is_segmented_name for p in work):
            result = _match_from_filenames(work)
            result.extras = extras
            result.warnings.append("No Course Content; numbering from filenames")
            return result
        raise MatchError("Product page has no Course Content volumes to match against")

    mode = detect_media_mode(parsed, volumes)
    warnings: list[str] = []

    if mode == "segmented":
        items, seg_extras, seg_warnings = _match_segments(work, volumes)
        extras.extend(seg_extras)
        warnings.extend(seg_warnings)
        return SeasonMatch(mode="segmented", items=items, extras=extras, warnings=warnings)

    pairs, vol_extras, vol_warnings = match_volumes(
        files,
        volumes,
        season_title=season_title,
        show_stem=show_stem,
    )
    extras = vol_extras
    warnings.extend(vol_warnings)
    items = _expand_volumes(pairs, skip_chapters=skip_chapters)
    if any(item.toc for item in items):
        warnings.append(
            "Course content lists chapters without timestamps; keeping one file per volume"
        )
    return SeasonMatch(mode="volume", items=items, extras=extras, warnings=warnings)


def group_matches_by_volume(items: list[ChapterMatch]) -> list[list[ChapterMatch]]:
    groups: dict[int, list[ChapterMatch]] = {}
    order: list[int] = []
    for item in items:
        key = item.volume_number
        if key not in groups:
            order.append(key)
            groups[key] = []
        groups[key].append(item)
    return [groups[key] for key in order]
