"""Turn each season of a bundle show into its own one-season show."""

from __future__ import annotations

import re
import shutil
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Callable

from .artwork import download_image, product_poster
from .errors import OrganizerError
from .httputil import DEFAULT_USER_AGENT, fetch_json
from .models import Product, SeasonPlan, ShowPlan
from .naming import SEASON_FOLDER, VIDEO_EXTS, sanitize_filename, show_title
from .nfo import XML_DECL, write_season_nfo, write_tvshow_nfo
from .scrape.bjj_fanatics import json_url_for, product_from_payloads

EPISODE_NAME = re.compile(
    r"^(?P<prefix>.+) - S(?P<season>\d+)E(?P<episode>\d+) - (?P<rest>.+)$",
    re.IGNORECASE,
)
_SHOW_META = re.compile(
    r"^(?:poster|folder|fanart|thumb|landscape|banner)\.(?:jpg|jpeg|png|webp)$",
    re.IGNORECASE,
)
_SEASON_THUMB = re.compile(
    r"^season\d*-thumb\.(?:jpg|jpeg|png|webp)$",
    re.IGNORECASE,
)
_POSTER_NAMES = ("poster.jpg", "poster.png", "poster.webp")
# Classic MAX_PATH is 260 characters including the terminating NUL.
PATH_LIMIT = 259
_KEEP_IF_PRESENT = {"season.nfo", *_POSTER_NAMES}


@dataclass
class PlannedFile:
    source_name: str
    dest_name: str
    warning: str = ""


@dataclass
class SeasonSplit:
    source_dir: Path
    number: int
    dest_dir: Path
    title: str
    file_prefix: str
    product: Product | None = None
    files: list[PlannedFile] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    skipped: bool = False
    skip_reason: str = ""
    fetch_failed: bool = False
    completed: bool = False
    poster: Path | None = None


@dataclass
class BundleSplit:
    source_dir: Path
    seasons: list[SeasonSplit]
    leftovers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def season_directories(show: Path) -> list[tuple[int, Path]]:
    found: list[tuple[int, Path]] = []
    if not show.is_dir():
        return found
    for child in show.iterdir():
        if not child.is_dir():
            continue
        match = SEASON_FOLDER.match(child.name)
        if match:
            found.append((int(match.group(1)), child))
    return sorted(found, key=lambda item: item[0])


def discover_bundles(library: Path, folder: Path | None) -> tuple[list[Path], str]:
    if folder is not None:
        if not folder.is_dir():
            raise OrganizerError(f"Folder does not exist: {folder}")
        if len(season_directories(folder)) < 2:
            return [], f"{folder} is not a bundle show (needs two or more Season folders)."
        return [folder], ""
    if not library.is_dir():
        raise OrganizerError(f"Library does not exist: {library}")
    found = [
        child
        for child in sorted(library.iterdir(), key=lambda path: path.name.lower())
        if child.is_dir() and len(season_directories(child)) >= 2
    ]
    return found, ""


def plan_bundles(
    shows: list[Path],
    *,
    offline: bool,
    resolve_product: Callable[[str], Product] | None = None,
) -> list[BundleSplit]:
    return [
        _plan_show(show, offline=offline, resolve_product=resolve_product)
        for show in shows
    ]


def format_report(bundles: list[BundleSplit], *, applied: bool) -> str:
    if not bundles:
        return "No bundle shows with two or more seasons.\n"
    lines: list[str] = []
    for bundle in bundles:
        lines.append(str(bundle.source_dir))
        for season in bundle.seasons:
            label = f"Season {season.number:02d}"
            if season.skipped:
                lines.append(f"  skip {label}: {season.skip_reason}")
                continue
            lines.append(f"  {label} -> {season.dest_dir}")
            for planned in season.files:
                lines.append(f"    {planned.source_name}")
                if planned.warning:
                    lines.append(f"      warning: {planned.warning}")
                elif planned.dest_name != planned.source_name:
                    lines.append(f"      -> {planned.dest_name}")
            for warning in season.warnings:
                lines.append(f"    warning: {warning}")
            for error in season.errors:
                lines.append(f"    error: {error}")
        for warning in bundle.warnings:
            lines.append(f"  warning: {warning}")
        if bundle.leftovers:
            lines.append("  remains in the bundle folder:")
            for name in bundle.leftovers:
                lines.append(f"    {name}")
    if applied:
        lines.append("Applied.")
    else:
        lines.append("Dry run. Pass --apply to move files.")
    return "\n".join(lines) + "\n"


def has_problems(bundles: list[BundleSplit]) -> bool:
    """True when a season was skipped, a fetch failed, or a file could not be renamed."""
    for bundle in bundles:
        if bundle.warnings:
            return True
        for season in bundle.seasons:
            if season.skipped or season.fetch_failed or season.errors:
                return True
            if any(item.warning.startswith("no SxxEyy") for item in season.files):
                return True
    return False


def apply_bundles(bundles: list[BundleSplit]) -> None:
    for bundle in bundles:
        moved_all = True
        for season in bundle.seasons:
            if season.skipped:
                moved_all = False
                continue
            if not _apply_season(season):
                moved_all = False
        if moved_all:
            _cleanup_bundle(bundle)


def default_resolve_product(user_agent: str = DEFAULT_USER_AGENT) -> Callable[[str], Product]:
    def resolve(handle: str) -> Product:
        url = f"https://bjjfanatics.com/products/{handle}"
        payload = fetch_json(json_url_for(url), user_agent=user_agent)
        return product_from_payloads(payload, "", url)

    return resolve


def _plan_show(
    show: Path,
    *,
    offline: bool,
    resolve_product: Callable[[str], Product] | None,
) -> BundleSplit:
    show_root = _parse_xml(show / "tvshow.nfo") if (show / "tvshow.nfo").is_file() else None
    named = _named_seasons(show_root) if show_root is not None else {}
    director = _instructor_name(show_root) if show_root is not None else ""
    claimed: set[str] = set()
    seasons: list[SeasonSplit] = []
    for number, season_dir in season_directories(show):
        seasons.append(
            _plan_season(
                show,
                number,
                season_dir,
                named.get(number, ""),
                director,
                offline=offline,
                resolve_product=resolve_product,
                claimed=claimed,
            )
        )
    return BundleSplit(
        source_dir=show,
        seasons=seasons,
        leftovers=_leftovers(show),
    )


def _plan_season(
    show: Path,
    number: int,
    season_dir: Path,
    named_season: str,
    director: str,
    *,
    offline: bool,
    resolve_product: Callable[[str], Product] | None,
    claimed: set[str],
) -> SeasonSplit:
    season_root = _parse_xml(season_dir / "season.nfo") if (season_dir / "season.nfo").is_file() else None
    ids = _unique_ids(season_root) if season_root is not None else {}
    handle = ids.get("bjjfanatics-handle", "")
    product: Product | None = None
    warnings: list[str] = []
    if not offline and handle:
        resolver = resolve_product or default_resolve_product()
        try:
            product = resolver(handle)
        except OrganizerError as exc:
            split = _blank_season(season_dir, number, show.parent / "skipped")
            split.skipped = True
            split.fetch_failed = True
            split.skip_reason = f"could not fetch {handle}: {exc}"
            return split
    if product is not None:
        pretty = show_title(product.title, [product.instructor] if product.instructor else [])
        if product.unique_ids:
            ids = dict(product.unique_ids)
    else:
        label = named_season or season_dir.name
        pretty = show_title(label, [director] if director else [])
        if not handle:
            warnings.append("no Fanatics handle; title taken from the show named season")
        product = _offline_product(pretty, director, ids, season_root)
    folder_name = sanitize_filename(pretty)
    dest = _destination(show.parent, folder_name)
    key = dest.name.lower()
    split = SeasonSplit(
        source_dir=season_dir,
        number=number,
        dest_dir=dest,
        title=pretty,
        file_prefix=folder_name,
        product=product,
        warnings=warnings,
        poster=_find_poster(season_dir),
    )
    if key in claimed:
        split.skipped = True
        split.skip_reason = f"another instructional in this run uses {dest}"
        return split
    same_show = _same_show(dest, ids.get("bjjfanatics", ""))
    if dest.exists() and any(dest.iterdir()) and not same_show:
        split.skipped = True
        split.skip_reason = f"destination already exists: {dest}"
        return split
    if dest.exists():
        split.file_prefix = dest.name
    claimed.add(key)
    split.files, notes = _planned_files(season_dir, split.file_prefix, dest / "Season 01")
    split.warnings.extend(notes)
    dest_has_poster = _find_poster(dest) is not None or _find_poster(dest / "Season 01") is not None
    if split.poster is None and not dest_has_poster:
        image = product_poster(product) if product else None
        if image is not None:
            split.warnings.append("season poster is missing; it will be downloaded on apply")
        else:
            split.warnings.append("season poster is missing")
    return split


def _blank_season(season_dir: Path, number: int, dest: Path) -> SeasonSplit:
    return SeasonSplit(
        source_dir=season_dir,
        number=number,
        dest_dir=dest,
        title="",
        file_prefix="",
    )


def _offline_product(
    title: str,
    instructor: str,
    ids: dict[str, str],
    season_root: ET.Element | None,
) -> Product:
    premiered = _premiered(season_root)
    return Product(
        title=title,
        instructor=instructor,
        plot="",
        premiered=premiered,
        year=premiered.year if premiered else None,
        tags=["Instructional"],
        unique_ids=dict(ids),
        images=[],
        volumes=[],
    )


def _destination(parent: Path, folder_name: str) -> Path:
    for child in parent.iterdir():
        if child.is_dir() and child.name.lower() == folder_name.lower():
            return child
    return parent / folder_name


def _planned_files(
    season_dir: Path,
    file_prefix: str,
    dest_season: Path,
) -> tuple[list[PlannedFile], list[str]]:
    planned: list[PlannedFile] = []
    notes: list[str] = []
    for child in sorted(season_dir.iterdir(), key=lambda path: path.name.lower()):
        if not child.is_file():
            continue
        dest_name = _episode_filename(child.name, file_prefix, dest_season)
        warning = ""
        suffix = child.suffix.lower()
        if suffix in VIDEO_EXTS and not EPISODE_NAME.match(child.name):
            warning = "no SxxEyy token; file will keep its name"
        elif suffix == ".nfo" and child.name.lower() != "season.nfo" and not EPISODE_NAME.match(child.name):
            warning = "no SxxEyy token; episode NFO will keep its name"
        if suffix in VIDEO_EXTS or (suffix == ".nfo" and child.name.lower() != "season.nfo"):
            planned.append(PlannedFile(child.name, dest_name, warning))
            preferred = _renamed(child.name, file_prefix)
            if dest_name != preferred and not warning:
                notes.append(f"shortened {child.name} to {dest_name} so the path fits on Windows")
    return planned, notes


def _renamed(filename: str, file_prefix: str) -> str:
    match = EPISODE_NAME.match(filename)
    if not match:
        return filename
    episode = int(match.group("episode"))
    return f"{file_prefix} - S01E{episode:02d} - {match.group('rest')}"


def _episode_filename(filename: str, file_prefix: str, dest_season: Path) -> str:
    """Pick a name whose full path stays within PATH_LIMIT."""
    match = EPISODE_NAME.match(filename)
    if not match:
        if _fits(dest_season, filename):
            return filename
        return _truncate_to_fit(dest_season, "", filename)
    episode = int(match.group("episode"))
    rest = match.group("rest")
    full = _renamed(filename, file_prefix)
    if _fits(dest_season, full):
        return full
    short = f"S01E{episode:02d} - {rest}"
    if _fits(dest_season, short):
        return short
    return _truncate_to_fit(dest_season, f"S01E{episode:02d} - ", rest)


def _fits(directory: Path, name: str) -> bool:
    return len(str(directory / name)) <= PATH_LIMIT


def _truncate_to_fit(directory: Path, label: str, rest: str) -> str:
    suffix = Path(rest).suffix
    stem = rest[: -len(suffix)] if suffix else rest
    available = PATH_LIMIT - len(str(directory)) - 1 - len(label) - len(suffix)
    trimmed = stem[: max(available, 1)].rstrip(" .")
    return f"{label}{trimmed}{suffix}"


def _same_show(dest: Path, product_id: str) -> bool:
    if not product_id or not dest.is_dir():
        return False
    return _unique_ids(_parse_xml(dest / "tvshow.nfo")).get("bjjfanatics") == product_id


def _apply_season(season: SeasonSplit) -> bool:
    if season.product is None:
        season.errors.append("missing product metadata")
        return False
    dest_season = season.dest_dir / "Season 01"
    try:
        dest_season.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        season.errors.append(f"could not create {dest_season}: {exc}")
        return False
    moved_nfos: list[Path] = []
    moved_any = False
    for child in list(season.source_dir.iterdir()):
        if child.name.lower() in _KEEP_IF_PRESENT and (dest_season / child.name).exists():
            try:
                child.unlink()
            except OSError as exc:
                season.errors.append(f"could not remove leftover {child.name}: {exc}")
            continue
        dest_name = _episode_filename(child.name, season.file_prefix, dest_season)
        target = dest_season / dest_name
        if target.exists():
            season.errors.append(f"left in place because {target.name} already exists")
            continue
        try:
            _move(child, target)
            moved_any = True
        except OSError as exc:
            season.errors.append(f"could not move {child.name}: {exc}")
            continue
        if target.suffix.lower() == ".nfo" and target.name.lower() != "season.nfo":
            moved_nfos.append(target)
    if any(season.source_dir.iterdir()):
        season.errors.append(f"source season still has files: {season.source_dir}")
        if moved_any or moved_nfos:
            _finish_metadata(season, dest_season, moved_nfos)
        return False
    try:
        _remove_dir(season.source_dir)
    except OSError as exc:
        season.errors.append(f"could not remove empty season folder: {exc}")
        _finish_metadata(season, dest_season, moved_nfos)
        return False
    _finish_metadata(season, dest_season, moved_nfos)
    season.completed = True
    return True


def _finish_metadata(season: SeasonSplit, dest_season: Path, moved_nfos: list[Path]) -> None:
    """Write show metadata, or leave an existing show NFO in place and update episodes."""
    show_nfo = season.dest_dir / "tvshow.nfo"
    if not show_nfo.is_file():
        _write_season_metadata(season, dest_season)
        return
    if not (dest_season / "season.nfo").is_file():
        show_plan, season_plan = _metadata_plans(season)
        write_season_nfo(show_plan, season_plan, dest_season)
    if _find_poster(season.dest_dir) is None:
        _copy_artwork(season, dest_season)
    title = _direct_child_text(_parse_xml(show_nfo), "title") or season.title
    for path in moved_nfos:
        if path.is_file():
            _rewrite_episode_nfo(path, title)


def _write_season_metadata(season: SeasonSplit, dest_season: Path) -> None:
    assert season.product is not None
    show_plan, season_plan = _metadata_plans(season)
    write_tvshow_nfo(show_plan, season.dest_dir)
    write_season_nfo(show_plan, season_plan, dest_season)
    _copy_artwork(season, dest_season)
    for path in dest_season.iterdir():
        if path.is_file() and path.suffix.lower() == ".nfo" and path.name.lower() != "season.nfo":
            _rewrite_episode_nfo(path, season.title)


def _metadata_plans(season: SeasonSplit) -> tuple[ShowPlan, SeasonPlan]:
    assert season.product is not None
    product = season.product
    instructors = [product.instructor] if product.instructor else []
    season_plan = SeasonPlan(
        source_dir=season.source_dir,
        source_name=season.title,
        dest_name="Season 01",
        number=1,
        product=product,
    )
    show_plan = ShowPlan(
        source_dir=season.source_dir,
        dest_name=season.dest_dir.name,
        title=season.title,
        instructors=instructors,
        seasons=[season_plan],
        year=product.year,
        premiered=product.premiered,
        plot=product.plot,
        unique_id=product.unique_ids.get("bjjfanatics", season.title),
        show_product=product,
    )
    return show_plan, season_plan


def _copy_artwork(season: SeasonSplit, dest_season: Path) -> None:
    poster = _find_poster(dest_season)
    if poster is None and season.product is not None:
        image = product_poster(season.product)
        if image is not None:
            try:
                poster = download_image(image.url, dest_season / "poster.jpg")
            except OrganizerError as exc:
                season.errors.append(f"could not download poster: {exc}")
            else:
                season.warnings = [
                    warning
                    for warning in season.warnings
                    if not warning.startswith("season poster is missing")
                ]
    if poster is None:
        return
    data = poster.read_bytes()
    for name in ("poster.jpg", "folder.jpg", "fanart.jpg"):
        target = season.dest_dir / name
        if target.resolve() != poster.resolve():
            target.write_bytes(data)
    season_poster = dest_season / "poster.jpg"
    if season_poster.resolve() != poster.resolve():
        season_poster.write_bytes(data)


def _rewrite_episode_nfo(path: Path, show_title_text: str) -> None:
    root = _parse_xml(path)
    if root is None or _local(root.tag) != "episodedetails":
        return
    _set_child(root, "showtitle", show_title_text)
    _set_child(root, "season", "1")
    ET.indent(root, space="  ")
    body = ET.tostring(root, encoding="unicode")
    path.write_text(XML_DECL + body + "\n", encoding="utf-8")


def _cleanup_bundle(bundle: BundleSplit) -> None:
    for child in list(bundle.source_dir.iterdir()):
        if child.is_dir() and SEASON_FOLDER.match(child.name):
            if any(child.iterdir()):
                bundle.warnings.append(f"left non-empty season folder {child.name}")
                return
            try:
                _remove_dir(child)
            except OSError as exc:
                bundle.warnings.append(f"could not remove {child.name}: {exc}")
                return
        elif child.is_file() and _is_show_meta(child.name):
            try:
                _remove_file(child)
            except OSError as exc:
                bundle.warnings.append(f"could not remove {child.name}: {exc}")
                return
    try:
        if bundle.source_dir.exists() and not any(bundle.source_dir.iterdir()):
            _remove_dir(bundle.source_dir)
    except OSError as exc:
        bundle.warnings.append(f"could not remove bundle folder: {exc}")


def _leftovers(show: Path) -> list[str]:
    names: list[str] = []
    for child in sorted(show.iterdir(), key=lambda path: path.name.lower()):
        if child.is_dir() and SEASON_FOLDER.match(child.name):
            continue
        if _is_show_meta(child.name):
            continue
        names.append(child.name)
    return names


def _is_show_meta(name: str) -> bool:
    lowered = name.lower()
    return lowered == "tvshow.nfo" or bool(_SHOW_META.match(name) or _SEASON_THUMB.match(name))


def _find_poster(folder: Path) -> Path | None:
    for name in _POSTER_NAMES:
        path = folder / name
        if path.is_file():
            return path
    return None


def _move(source: Path, dest: Path, attempts: int = 8) -> None:
    last: OSError | None = None
    for attempt in range(attempts):
        try:
            shutil.move(str(source), str(dest))
            return
        except OSError as exc:
            last = exc
            winerror = getattr(exc, "winerror", None)
            if winerror not in {5, 32} and not isinstance(exc, PermissionError):
                raise
            time.sleep(0.4 * (attempt + 1))
    assert last is not None
    raise last


def _remove_file(path: Path, attempts: int = 8) -> None:
    last: OSError | None = None
    for attempt in range(attempts):
        try:
            path.unlink()
            return
        except OSError as exc:
            last = exc
            winerror = getattr(exc, "winerror", None)
            if winerror not in {5, 32} and not isinstance(exc, PermissionError):
                raise
            time.sleep(0.4 * (attempt + 1))
    assert last is not None
    raise last


def _remove_dir(path: Path, attempts: int = 8) -> None:
    last: OSError | None = None
    for attempt in range(attempts):
        try:
            path.rmdir()
            return
        except OSError as exc:
            last = exc
            winerror = getattr(exc, "winerror", None)
            if winerror not in {5, 32} and not isinstance(exc, PermissionError):
                raise
            time.sleep(0.4 * (attempt + 1))
    assert last is not None
    raise last


def _parse_xml(path: Path) -> ET.Element | None:
    if not path.is_file():
        return None
    try:
        return ET.fromstring(path.read_text(encoding="utf-8-sig"))
    except ET.ParseError:
        return None


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _unique_ids(root: ET.Element | None) -> dict[str, str]:
    found: dict[str, str] = {}
    if root is None:
        return found
    for element in root.iter():
        if _local(element.tag) != "uniqueid":
            continue
        kind = element.attrib.get("type") or ""
        value = (element.text or "").strip()
        if kind and value:
            found[kind] = value
    return found


def _named_seasons(root: ET.Element | None) -> dict[int, str]:
    found: dict[int, str] = {}
    if root is None:
        return found
    for element in root.iter():
        if _local(element.tag) != "namedseason":
            continue
        number = element.attrib.get("number") or ""
        text = (element.text or "").strip()
        if number.isdigit() and text:
            found[int(number)] = text
    return found


def _direct_child_text(root: ET.Element | None, tag: str) -> str:
    if root is None:
        return ""
    for element in list(root):
        if _local(element.tag) == tag and (element.text or "").strip():
            return element.text.strip()
    return ""


def _instructor_name(root: ET.Element | None) -> str:
    if root is None:
        return ""
    for element in list(root):
        if _local(element.tag) == "director" and (element.text or "").strip():
            return element.text.strip()
    for actor in list(root):
        if _local(actor.tag) != "actor":
            continue
        for element in list(actor):
            if _local(element.tag) == "name" and (element.text or "").strip():
                return element.text.strip()
    return ""


def _premiered(root: ET.Element | None) -> date | None:
    if root is None:
        return None
    for element in list(root):
        if _local(element.tag) == "premiered" and (element.text or "").strip():
            raw = element.text.strip()
            try:
                return date.fromisoformat(raw[:10])
            except ValueError:
                return None
    return None


def _set_child(parent: ET.Element, tag: str, value: str) -> None:
    for element in list(parent):
        if _local(element.tag) == tag:
            element.text = value
            return
    child = ET.Element(tag)
    child.text = value
    parent.append(child)
