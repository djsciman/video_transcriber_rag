from __future__ import annotations

import gc
import json
import os
import re
import shutil
import sys
import time
from dataclasses import dataclass, replace
from datetime import date
from pathlib import Path

from .artwork import product_fanart, product_poster, write_posters
from .chapters import chapters_have_timeline, probe_chapter_titles, remux_with_chapters
from .concat import concat_with_chapters
from .errors import MatchError, UsageError
from .fanatics_search import csv_hint_url, lookup_candidates
from .httputil import DEFAULT_USER_AGENT
from .layout import child_dirs, detect_layout, dir_has_videos, list_videos, season_source_name
from .match import group_matches_by_volume, match_season
from .models import Chapter, ChapterMatch, EpisodePlan, SeasonPlan, ShowPlan
from .naming import (
    SXXEYY,
    is_generic_season_name,
    parse_video,
    pick_volume_title,
    season_folder_name,
    season_folder_number,
    series_stem,
    show_slug,
    show_title,
    volume_episode_filename,
)
from .nfo import write_episode_nfo, write_season_nfo, write_tvshow_nfo
from .scrape.base import fetch_product
from .split import remux_copy


@dataclass
class RuntimeOptions:
    apply: bool = False
    container: str = "keep"
    extras_policy: str = "extras"
    skip_chapters: bool = False
    combine_volumes: bool = True
    season_order: list[str] | None = None
    user_agent: str = DEFAULT_USER_AGENT
    ffmpeg: str | None = None
    ffprobe: str | None = None
    json_out: bool = False
    stdin: object | None = None
    stderr: object | None = None
    repair: bool = False
    repair_steps: set[str] | None = None


def parse_url_arg(raw: str) -> tuple[str | None, str]:
    text = raw.strip()
    if text.startswith("http://") or text.startswith("https://"):
        return None, text
    if "=" in text:
        key, url = text.split("=", 1)
        key, url = key.strip(), url.strip()
        if key and (url.startswith("http://") or url.startswith("https://")):
            raise UsageError(
                f"Invalid --url {raw!r}. Use a single product URL per instructional folder, "
                "not SeasonFolder=https://..."
            )
    raise UsageError(f"Invalid --url {raw!r}. Use a bare https URL.")


def _url_aliases(source_name: str, folder_name: str, show_folder: str) -> list[str]:
    names = [source_name, folder_name, show_folder, series_stem(show_folder)]
    extras: list[str] = []
    for name in names:
        number = season_folder_number(name)
        if number is not None:
            extras.append(f"Season {number}")
            extras.append(f"Season {number:02d}")
    seen: set[str] = set()
    out: list[str] = []
    for name in names + extras:
        key = name.strip().lower()
        if name.strip() and key not in seen:
            seen.add(key)
            out.append(name.strip())
    return out


def resolve_season_url(
    source_name: str,
    folder_name: str,
    keyed: dict[str, str],
    bare_urls: list[str],
    nested: bool,
    season_count: int,
    show_folder: str = "",
) -> str | None:
    supplied = list(keyed.values()) + list(bare_urls)
    if season_count == 1 and len(supplied) == 1:
        return supplied[0]
    lowered = {k.lower(): v for k, v in keyed.items()}
    for candidate in _url_aliases(source_name, folder_name, show_folder):
        url = lowered.get(candidate.lower())
        if url:
            return url
    if not nested and len(bare_urls) == 1:
        return bare_urls[0]
    if nested and season_count == 1 and len(bare_urls) == 1:
        return bare_urls[0]
    return None


def confirm_product_url(
    label: str,
    hits: list,
    stdin,
    stderr,
    *,
    optional: bool = False,
    heading: str | None = None,
) -> str | None:
    if stdin is None or stderr is None or not hasattr(stdin, "isatty") or not stdin.isatty():
        raise UsageError(
            f"No --url for {label!r}. Pass --url or run in a terminal to confirm a lookup."
        )
    if not hits:
        if optional:
            stderr.write(
                f"No BJJ Fanatics match for {label!r}. Show metadata will use the seasons.\n"
            )
            return None
        raise MatchError(
            f"No BJJ Fanatics match for {label!r}. Pass --url https://bjjfanatics.com/products/..."
        )
    stderr.write((heading or f"No --url for: {label}") + "\n")
    for index, hit in enumerate(hits, start=1):
        stderr.write(
            f"Best match ({index}/{len(hits)}):\n"
            f"  {hit.title}\n"
            f"  {hit.url}\n"
            f"  score={hit.score:.2f}\n"
            "Use this URL? [y/N/q] "
        )
        stderr.flush()
        reply = (stdin.readline() or "").strip().lower()
        if reply in {"y", "yes"}:
            return hit.url
        if reply in {"q", "quit"}:
            raise UsageError("URL lookup cancelled")
    if optional:
        stderr.write(
            f"No remaining BJJ Fanatics matches for {label!r}. Show metadata will use the seasons.\n"
        )
        return None
    raise MatchError(
        f"No remaining BJJ Fanatics matches for {label!r}. Pass --url explicitly."
    )


def lookup_season_url(
    folder: Path,
    source_name: str,
    season_count: int,
    options: RuntimeOptions,
    exclude_urls: set[str] | None = None,
    hint_folder: Path | None = None,
) -> str:
    blocked = exclude_urls or set()
    hint = csv_hint_url(hint_folder or folder)
    if hint and hint not in blocked:
        return hint
    label = folder.name
    if season_count > 1 and source_name and not is_generic_season_name(source_name):
        label = f"{folder.name} {source_name}"
    hits = lookup_candidates(label, user_agent=options.user_agent)
    if label != folder.name:
        extra = lookup_candidates(source_name, user_agent=options.user_agent)
        seen = {hit.url for hit in hits}
        hits.extend(hit for hit in extra if hit.url not in seen)
        hits.sort(key=lambda hit: hit.score, reverse=True)
    hits = [hit for hit in hits if hit.url not in blocked]
    stdin = options.stdin if options.stdin is not None else sys.stdin
    stderr = options.stderr if options.stderr is not None else sys.stderr
    url = confirm_product_url(label, hits, stdin, stderr)
    if not url:
        raise MatchError(f"No BJJ Fanatics match for {label!r}. Pass --url explicitly.")
    return url


def _unique_instructors(names: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for name in names:
        key = name.strip().lower()
        if name.strip() and key not in seen:
            seen.add(key)
            out.append(name.strip())
    return out


def _season_sort_key(plan: SeasonPlan, order: dict[str, int]) -> tuple[int, str, str]:
    if plan.source_name.lower() in order:
        return (order[plan.source_name.lower()], "", "")
    published = plan.product.premiered or date.max
    return (10_000, published.isoformat(), plan.source_name.lower())


def _unique_paths(items: list[ChapterMatch]) -> list[Path]:
    paths: list[Path] = []
    seen: set[Path] = set()
    for item in items:
        path = item.parsed.path
        key = path
        try:
            key = path.resolve()
        except OSError:
            pass
        if key in seen:
            continue
        seen.add(key)
        paths.append(path)
    return paths


def _episodes_from_match(
    items: list[ChapterMatch],
    mode: str,
    options: RuntimeOptions,
    folder: Path,
) -> list[EpisodePlan]:
    episodes: list[EpisodePlan] = []
    for index, group in enumerate(group_matches_by_volume(items), start=1):
        first = group[0]
        sources = _unique_paths(group)
        ext = first.parsed.extension
        if options.container == "mkv":
            ext = ".mkv"
        title = pick_volume_title(first.parsed, first.volume_name, first.volume_number)
        chapters: list[Chapter] = []
        for item in group:
            if item.toc:
                chapters.extend(item.toc)
            else:
                chapters.append(Chapter(item.chapter_title, item.chapter.start_ms))
        episodes.append(
            EpisodePlan(
                source=sources[0],
                dest_dir=folder,
                dest_name="",
                season=0,
                episode=index,
                title=title,
                chapters=chapters,
                extension=ext,
                volume_number=first.volume_number,
                chapter_number=1,
                chapter_title=title,
                volume_name=first.volume_name,
                mode=mode,
                concat_sources=sources,
            )
        )
    return episodes


def _norm_title(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _find_combined_episode(
    show_dir: Path,
    source_dir: Path,
    files: list[Path],
    options: RuntimeOptions,
) -> Path | None:
    """Return an episode that already contains every clip in this folder."""
    parsed = [parse_video(path) for path in files]
    if len(parsed) < 2 or any(item.chapter_number is None for item in parsed):
        return None
    wanted = {_norm_title(item.local_title or item.path.stem) for item in parsed}
    wanted.discard("")
    if len(wanted) < 2:
        return None
    ffprobe = options.ffprobe or "ffprobe"
    for season_dir in child_dirs(show_dir):
        if season_folder_number(season_dir.name) is None:
            continue
        if season_dir.resolve() == source_dir.resolve():
            continue
        for video in list_videos(season_dir):
            try:
                found = {_norm_title(title) for title in probe_chapter_titles(video, ffprobe)}
            except Exception:
                continue
            if wanted <= found:
                return video
    return None


def _season_already_combined(
    source_dir: Path,
    source_name: str,
    product,
    files: list[Path],
    episode_path: Path,
    options: RuntimeOptions,
) -> SeasonPlan:
    match = SXXEYY.search(episode_path.stem)
    season_number = int(match.group(1)) if match else (season_folder_number(episode_path.parent.name) or 0)
    episode_number = int(match.group(2)) if match else 1
    try:
        titles = probe_chapter_titles(episode_path, options.ffprobe or "ffprobe")
    except Exception:
        titles = []
    episode = EpisodePlan(
        source=episode_path,
        dest_dir=episode_path.parent,
        dest_name=episode_path.name,
        season=season_number,
        episode=episode_number,
        title=f"Volume {episode_number}",
        chapters=[Chapter(title, 0) for title in titles],
        extension=episode_path.suffix,
        volume_number=episode_number,
        chapter_number=1,
        chapter_title=f"Volume {episode_number}",
        volume_name=f"Volume {episode_number}",
        mode="volume",
        concat_sources=[episode_path],
    )
    return SeasonPlan(
        source_dir=source_dir,
        source_name=source_name,
        dest_name=episode_path.parent.name,
        number=season_number,
        product=product,
        episodes=[episode],
        extras=list(files),
        warnings=[f"Chapter clips are already combined into {episode_path.name}"],
        mode="volume",
        combine_volumes=True,
        keep_dest=True,
    )


def build_plan(
    folder: Path,
    url_args: list[str],
    options: RuntimeOptions,
    scrape_product=fetch_product,
) -> ShowPlan:
    folder = folder.resolve()
    kind, season_dirs = detect_layout(folder)
    nested = kind == "nested"
    parent_series_warning = None
    if kind == "leaf":
        siblings = [
            d.name
            for d in child_dirs(folder.parent)
            if d.resolve() != folder.resolve() and dir_has_videos(d)
        ]
        if siblings:
            parent_series_warning = (
                f"{folder.name} looks like a season of {folder.parent.name} "
                f"(siblings include {', '.join(siblings[:6])}"
                f"{'…' if len(siblings) > 6 else ''}). "
                "Organize this instructional folder on its own; leftover bundle siblings "
                "stay out of the pipeline until flattened by hand."
            )

    work_dirs = season_dirs if nested else [folder]
    if nested:
        topic_dirs = [path for path in season_dirs if season_folder_number(path.name) is None]
        if topic_dirs and len(topic_dirs) < len(season_dirs):
            # Season 01 next to the original download folders is output from an
            # earlier run, not another season to match.
            work_dirs = topic_dirs
    if nested and len(work_dirs) > 1:
        names = ", ".join(path.name for path in work_dirs[:6])
        extra = "…" if len(work_dirs) > 6 else ""
        raise UsageError(
            f"{folder.name} looks like a leftover bundle of {len(work_dirs)} instructionals "
            f"({names}{extra}). Organize each instructional folder on its own; "
            "flatten leftover bundles by hand."
        )

    keyed: dict[str, str] = {}
    bare: list[str] = []
    for raw in url_args:
        key, url = parse_url_arg(raw)
        if key is None:
            bare.append(url)
        else:
            keyed[key] = url
    if len(bare) + len(keyed) > 1:
        raise UsageError("A one-season show takes at most one --url")

    season_plans: list[SeasonPlan] = []
    warnings: list[str] = []
    if parent_series_warning:
        warnings.append(parent_series_warning)

    show_url: str | None = None
    show_product = None
    season_keyed = keyed
    season_bare = bare

    exclude_urls: set[str] = set()
    if show_url:
        show_product = scrape_product(show_url, user_agent=options.user_agent)
        show_product.volumes = []
        exclude_urls.add(show_url)

    for source_dir in work_dirs:
        source_name = season_source_name(source_dir) if nested else series_stem(folder.name)
        url = resolve_season_url(
            source_name,
            source_dir.name,
            season_keyed,
            season_bare,
            nested=nested,
            season_count=len(work_dirs),
            show_folder=folder.name,
        )
        if not url:
            url = lookup_season_url(
                folder,
                source_name,
                len(work_dirs),
                options,
                exclude_urls=exclude_urls,
                hint_folder=source_dir,
            )
        product = scrape_product(url, user_agent=options.user_agent)
        if (not nested) or is_generic_season_name(source_name):
            source_name = product.title or source_name
        files = list_videos(source_dir)
        stem = series_stem(folder.name)
        existing = _find_combined_episode(folder, source_dir, files, options)
        if existing is not None:
            season_plans.append(
                _season_already_combined(source_dir, source_name, product, files, existing, options)
            )
            warnings.append(
                f"{source_dir.name}: chapter clips are already combined into {existing.name}"
            )
            continue
        try:
            matched = match_season(
                files,
                product.volumes,
                season_title=source_name,
                show_stem=stem,
                skip_chapters=options.skip_chapters,
            )
        except MatchError as exc:
            message = str(exc).splitlines()[0]
            warnings.append(f"{source_dir.name}: {message}")
            season_plans.append(
                SeasonPlan(
                    source_dir=source_dir,
                    source_name=source_name,
                    dest_name="",
                    number=0,
                    product=product,
                    warnings=[message],
                    mode="volume",
                    combine_volumes=True,
                    match_error=message,
                )
            )
            continue
        warnings.extend(matched.warnings)
        season = SeasonPlan(
            source_dir=source_dir,
            source_name=source_name,
            dest_name="",
            number=0,
            product=product,
            extras=matched.extras,
            warnings=matched.warnings,
            mode=matched.mode,
            combine_volumes=True,
        )
        season.episodes = _episodes_from_match(matched.items, matched.mode, options, folder)
        season_plans.append(season)

    missing = [s for s in season_plans if not s.product.source_url]
    if missing:
        raise MatchError("Internal error: season missing product URL")

    order = {name.strip().lower(): i for i, name in enumerate(options.season_order or []) if name.strip()}
    season_plans.sort(key=lambda s: _season_sort_key(s, order))
    used_numbers = {
        number
        for path in child_dirs(folder)
        if (number := season_folder_number(path.name)) is not None
    }
    number = 1
    for season in season_plans:
        if season.keep_dest:
            dest_dir = folder / season.dest_name
            for episode in season.episodes:
                episode.season = season.number
                episode.dest_dir = dest_dir
            continue
        while number in used_numbers:
            number += 1
        season.number = number
        season.dest_name = season_folder_name(number)
        used_numbers.add(number)
        number += 1
        dest_dir = folder / season.dest_name
        for episode in season.episodes:
            episode.season = season.number
            episode.dest_dir = dest_dir

    instructors = _unique_instructors([s.product.instructor for s in season_plans])
    if show_product and show_product.instructor:
        instructors = _unique_instructors([show_product.instructor])
    title = show_title(folder.name, instructors)
    for season in season_plans:
        for episode in season.episodes:
            if season.keep_dest:
                continue
            episode.dest_name = volume_episode_filename(
                title,
                episode.season,
                episode.episode,
                episode.title,
                episode.extension,
            )

    if show_product and show_product.premiered:
        earliest = show_product.premiered
    else:
        earliest = min((s.product.premiered for s in season_plans if s.product.premiered), default=None)
    plot_parts: list[str] = []
    if show_product and show_product.plot:
        plot_parts.append(show_product.plot)
    elif season_plans[0].product.plot:
        plot_parts.append(season_plans[0].product.plot)
    if len(season_plans) > 1:
        listing = "\n".join(f"{s.number}. {s.source_name}" for s in season_plans)
        plot_parts.append("Seasons:\n" + listing)
    plot = "\n\n".join(plot_parts)
    product_id = show_product.unique_ids.get("bjjfanatics") if show_product else ""
    unique_id = product_id or show_slug(title)

    return ShowPlan(
        source_dir=folder,
        dest_name=title,
        title=title,
        instructors=instructors,
        seasons=season_plans,
        year=earliest.year if earliest else None,
        premiered=earliest,
        plot=plot,
        unique_id=unique_id,
        warnings=warnings,
        nested=nested,
        combine_volumes=True,
        show_url=show_url or "",
        show_product=show_product,
    )


def format_plan(plan: ShowPlan) -> str:
    lines = [
        f"Show: {plan.title}",
        *( [f"Show URL: {plan.show_url}"] if plan.show_url else [] ),
        f"Folder: {plan.source_dir}",
        f"Will rename folder: {'no' if plan.source_dir.name == plan.dest_name else plan.dest_name}",
        f"Instructors: {', '.join(plan.instructors) or '(none)'}",
        f"Seasons: {len(plan.seasons)}",
        "Combine volumes: yes",
        "",
    ]
    for season in plan.seasons:
        published = season.product.premiered.isoformat() if season.product.premiered else "unknown date"
        lines.append(
            f"  {season.dest_name}  {season.source_name}  ({published})  "
            f"{len(season.episodes)} episodes  mode={season.mode}  from {season.source_dir.name}"
        )
        for episode in season.episodes:
            if episode.concat_sources:
                lines.append(f"    {episode.title}  -> {episode.dest_name}")
                for source in episode.concat_sources:
                    lines.append(f"      {source.name}")
                for chapter in episode.chapters:
                    lines.append(f"      chapter {chapter.title}")
            else:
                lines.append(
                    f"    {episode.title}  <- {episode.source.name}  -> {episode.dest_name}"
                )
        for extra in season.extras:
            lines.append(f"    extra: {extra.name}")
        lines.append("")
    if plan.warnings:
        lines.append("Warnings:")
        for warning in plan.warnings:
            lines.append(f"  - {warning}")
    return "\n".join(lines).rstrip() + "\n"


def _fmt_ms(ms: int) -> str:
    seconds = ms / 1000
    if seconds >= 3600:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours}:{minutes:02d}:{secs:06.3f}"
    minutes = int(seconds // 60)
    secs = seconds % 60
    return f"{minutes}:{secs:06.3f}"


def plan_to_json(plan: ShowPlan) -> dict:
    return {
        "title": plan.title,
        "show_url": plan.show_url,
        "folder": str(plan.source_dir),
        "dest_name": plan.dest_name,
        "instructors": plan.instructors,
        "year": plan.year,
        "combine_volumes": plan.combine_volumes,
        "seasons": [
            {
                "number": s.number,
                "title": s.source_name,
                "dest": s.dest_name,
                "url": s.product.source_url,
                "mode": s.mode,
                "episodes": [
                    {
                        "episode": e.episode,
                        "title": e.title,
                        "source": str(e.source),
                        "dest": e.dest_name,
                        "volume": e.volume_number,
                        "chapter": e.chapter_number,
                        "split_start_ms": e.split_start_ms,
                        "split_end_ms": e.split_end_ms,
                        "concat_sources": [str(p) for p in e.concat_sources],
                    }
                    for e in s.episodes
                ],
                "extras": [str(p) for p in s.extras],
            }
            for s in plan.seasons
        ],
        "warnings": plan.warnings,
    }


def _tool(name: str, override: str | None) -> str:
    if override:
        return override
    path = shutil.which(name) or shutil.which(f"{name}.exe")
    if not path:
        raise UsageError(f"{name} was not found on PATH. Install ffmpeg or pass --{name}.")
    return path


def _leave_directory(path: Path) -> None:
    try:
        cwd = Path.cwd().resolve()
        target = path.resolve()
        if cwd == target or target in cwd.parents:
            os.chdir(path.parent)
    except OSError:
        pass


def rename_directory(source: Path, dest: Path, attempts: int = 8) -> bool:
    """Rename a folder, retrying SMB/Windows locks. Returns False if still locked."""
    if dest.exists():
        raise MatchError(f"Cannot rename show folder; {dest} already exists")
    _leave_directory(source)
    gc.collect()
    last: OSError | None = None
    for attempt in range(attempts):
        try:
            source.rename(dest)
            return True
        except OSError as exc:
            last = exc
            winerror = getattr(exc, "winerror", None)
            if winerror not in {5, 32} and not isinstance(exc, PermissionError):
                raise
            time.sleep(0.4 * (attempt + 1))
    sys.stderr.write(
        f"warning: could not rename folder (Windows often locks this on network shares):\n"
        f"  {source}\n"
        f"  -> {dest}\n"
        f"  {last}\n"
        f"  Files are already organized inside the original folder. "
        f"Rename it in Explorer when nothing has it open.\n"
    )
    return False


def _clear_dest(dest: Path, sources: list[Path] | None = None) -> None:
    source_keys = set()
    for path in sources or []:
        try:
            source_keys.add(path.resolve())
        except OSError:
            source_keys.add(path)
    if dest.exists():
        try:
            resolved = dest.resolve()
        except OSError:
            resolved = dest
        if resolved not in source_keys:
            dest.unlink()
    nfo = dest.with_suffix(".nfo")
    if nfo.exists():
        nfo.unlink()


def _move_file(source: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if source.resolve() == dest.resolve():
        return
    _clear_dest(dest, [source])
    shutil.move(str(source), str(dest))


def _wants_chapter_remux(episode: EpisodePlan, options: RuntimeOptions) -> bool:
    if options.skip_chapters:
        return False
    titled = [ch for ch in episode.chapters if ch.title.strip()]
    if len(titled) > 1 and not chapters_have_timeline(titled):
        return False
    return any(ch.title.strip() for ch in episode.chapters)


def _needs_ffmpeg(plan: ShowPlan, options: RuntimeOptions) -> bool:
    if options.container == "mkv":
        return True
    for season in plan.seasons:
        for episode in season.episodes:
            if len(episode.concat_sources) > 1:
                return True
            if _wants_chapter_remux(episode, options):
                return True
    return False


def _place_single_file(
    source: Path,
    dest: Path,
    episode: EpisodePlan,
    options: RuntimeOptions,
    ffmpeg: str | None,
    ffprobe: str | None,
) -> None:
    if options.container == "mkv" and not _wants_chapter_remux(episode, options):
        assert ffmpeg and ffprobe
        remux_copy(source, dest, ffmpeg, ffprobe)
        if source.exists() and source.resolve() != dest.resolve():
            source.unlink()
        return
    if _wants_chapter_remux(episode, options):
        assert ffmpeg and ffprobe
        remux_with_chapters(
            source,
            dest,
            episode.chapters,
            ffmpeg,
            ffprobe,
            mov_faststart=dest.suffix.lower() in {".mp4", ".m4v"},
        )
        if source.exists() and source.resolve() != dest.resolve():
            source.unlink()
        return
    _move_file(source, dest)


def _repair_step(options: RuntimeOptions, letter: str) -> bool:
    if options.repair_steps is None:
        return True
    return letter in options.repair_steps


def _move_keeping_name(sources: list[Path], dest_dir: Path) -> None:
    for source in sources:
        if not source.exists():
            continue
        target = dest_dir / source.name
        if source.resolve() == target.resolve():
            continue
        _move_file(source, target)


def apply_plan(plan: ShowPlan, options: RuntimeOptions) -> None:
    ffmpeg = ffprobe = None
    needs_media = _needs_ffmpeg(plan, options) and (
        options.repair_steps is None or bool(options.repair_steps & {"D", "E", "F"})
    )
    if needs_media:
        ffmpeg = _tool("ffmpeg", options.ffmpeg)
        ffprobe = _tool("ffprobe", options.ffprobe)

    show_dir = plan.source_dir
    show_poster_written = False
    if _repair_step(options, "B") and plan.show_product:
        poster = product_poster(plan.show_product)
        if poster:
            write_posters(show_dir, poster, user_agent=options.user_agent, also_folder_jpg=True)
            fanart = product_fanart(plan.show_product)
            if fanart:
                from .artwork import download_image

                download_image(fanart.url, show_dir / "fanart.jpg", user_agent=options.user_agent)
            show_poster_written = True

    full_apply = options.repair_steps is None
    place_options = options if full_apply or _repair_step(options, "E") else replace(options, skip_chapters=True)
    for season in plan.seasons:
        dest_dir = show_dir / season.dest_name
        if any(_repair_step(options, letter) for letter in "CDEFG"):
            dest_dir.mkdir(parents=True, exist_ok=True)
        if _repair_step(options, "C"):
            poster = product_poster(season.product)
            if poster:
                write_posters(dest_dir, poster, user_agent=options.user_agent, also_folder_jpg=False)
                if not show_poster_written:
                    write_posters(show_dir, poster, user_agent=options.user_agent, also_folder_jpg=True)
                    fanart = product_fanart(season.product)
                    if fanart:
                        from .artwork import download_image

                        download_image(fanart.url, show_dir / "fanart.jpg", user_agent=options.user_agent)
                    show_poster_written = True
            write_season_nfo(plan, season, dest_dir)

        for episode in season.episodes:
            dest = dest_dir / episode.dest_name
            sources = episode.concat_sources or [episode.source]
            if len(sources) > 1:
                if not _repair_step(options, "D"):
                    if _repair_step(options, "C"):
                        _move_keeping_name(sources, dest_dir)
                    continue
                assert ffmpeg and ffprobe
                titles = [ch.title for ch in episode.chapters] or [episode.title]
                if len(titles) < len(sources):
                    titles = titles + [f"Chapter {i}" for i in range(len(titles) + 1, len(sources) + 1)]
                concat_with_chapters(
                    sources,
                    dest,
                    titles[: len(sources)],
                    ffmpeg,
                    ffprobe,
                    skip_chapters=place_options.skip_chapters,
                )
                if _repair_step(options, "F"):
                    write_episode_nfo(plan, season, episode, dest)
                continue
            if not (_repair_step(options, "F") or _repair_step(options, "E")):
                if _repair_step(options, "C"):
                    _move_keeping_name(sources, dest_dir)
                continue
            _place_single_file(sources[0], dest, episode, place_options, ffmpeg, ffprobe)
            if _repair_step(options, "F"):
                write_episode_nfo(plan, season, episode, dest)

        if _repair_step(options, "G") and options.extras_policy == "extras" and season.extras:
            extras_dir = dest_dir / "extras"
            extras_dir.mkdir(exist_ok=True)
            for extra in season.extras:
                if extra.exists():
                    _move_file(extra, extras_dir / extra.name)

        if (
            season.source_dir != dest_dir
            and season.source_dir.exists()
            and season.source_dir != show_dir
        ):
            leftover = [p for p in season.source_dir.iterdir() if p.name not in {".", ".."}]
            if not leftover:
                season.source_dir.rmdir()

    if _repair_step(options, "B"):
        write_tvshow_nfo(plan, show_dir)

        if plan.dest_name != show_dir.name:
            dest_show = show_dir.with_name(plan.dest_name)
            rename_directory(show_dir, dest_show)


def run(
    folder: Path,
    url_args: list[str],
    options: RuntimeOptions,
    scrape_product=fetch_product,
) -> int:
    if options.repair or options.repair_steps is not None:
        from .repair import run_repair

        return run_repair(folder, url_args, options, scrape_product=scrape_product)
    plan = build_plan(folder, url_args, options, scrape_product=scrape_product)
    text = format_plan(plan)
    if options.json_out:
        json.dump(plan_to_json(plan), sys.stdout, indent=2)
        sys.stdout.write("\n")
        sys.stderr.write(text)
        if not options.apply:
            sys.stderr.write("\nDry-run only. Pass --apply to write files.\n")
    else:
        sys.stdout.write(text)
        if not options.apply:
            sys.stderr.write("Dry-run only. Pass --apply to write files.\n")
    if not options.apply:
        return 0
    apply_plan(plan, options)
    sys.stderr.write("Apply complete.\n")
    return 0
