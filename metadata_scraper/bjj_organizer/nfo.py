from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path

from .models import EpisodePlan, SeasonPlan, ShowPlan

XML_DECL = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'


def _text(parent: ET.Element, tag: str, value: str | int | None) -> None:
    if value is None or value == "":
        return
    child = ET.SubElement(parent, tag)
    child.text = str(value)


def _uniqueid(parent: ET.Element, id_type: str, value: str, default: bool = False) -> None:
    el = ET.SubElement(parent, "uniqueid", type=id_type)
    if default:
        el.set("default", "true")
    el.text = value


# Lock title and plot only. lockdata=true freezes the season number too, and
# Jellyfin will not read <season> again. A null season is shown as Season Unknown
# in addition to the Season 01 folder.
LOCKED_FIELDS = "Name|Overview|Genres|Studios|Tags|Cast"


def _lock_metadata(parent: ET.Element) -> None:
    _text(parent, "lockedfields", LOCKED_FIELDS)
    _text(parent, "lockdata", "false")


def _actor(parent: ET.Element, name: str, role: str = "Instructor", order: int = 0) -> None:
    actor = ET.SubElement(parent, "actor")
    _text(actor, "name", name)
    _text(actor, "role", role)
    _text(actor, "order", order)


def _write(root: ET.Element, path: Path) -> None:
    ET.indent(root, space="  ")
    body = ET.tostring(root, encoding="unicode")
    path.write_text(XML_DECL + body + "\n", encoding="utf-8")


def tvshow_xml(plan: ShowPlan) -> ET.Element:
    root = ET.Element("tvshow")
    _text(root, "title", plan.title)
    _text(root, "plot", plan.plot)
    if plan.premiered:
        _text(root, "premiered", plan.premiered.isoformat())
    if plan.year:
        _text(root, "year", plan.year)
    _text(root, "studio", "BJJ Fanatics")
    if len(plan.instructors) == 1:
        _text(root, "director", plan.instructors[0])
    for index, name in enumerate(plan.instructors):
        _actor(root, name, order=index)
    _text(root, "genre", "Sports")
    ET.SubElement(root, "genre").text = "Martial Arts"
    _text(root, "tag", "Instructional")
    for season in plan.seasons:
        named = ET.SubElement(root, "namedseason", number=str(season.number))
        named.text = season.source_name
    show_ids = plan.show_product.unique_ids if plan.show_product else {}
    product_id = show_ids.get("bjjfanatics")
    if product_id:
        _uniqueid(root, "bjjfanatics", product_id, default=True)
        handle = show_ids.get("bjjfanatics-handle")
        if handle:
            _uniqueid(root, "bjjfanatics-handle", handle)
    else:
        _uniqueid(root, "bjjfanatics", plan.unique_id, default=True)
    _lock_metadata(root)
    return root


def season_xml(show: ShowPlan, season: SeasonPlan) -> ET.Element:
    root = ET.Element("season")
    _text(root, "title", season.source_name)
    _text(root, "seasonnumber", season.number)
    plot = season.product.plot
    _text(root, "plot", plot)
    if season.product.premiered:
        _text(root, "premiered", season.product.premiered.isoformat())
    if season.product.instructor:
        _text(root, "director", season.product.instructor)
        _actor(root, season.product.instructor)
    product_id = season.product.unique_ids.get("bjjfanatics")
    if product_id:
        _uniqueid(root, "bjjfanatics", product_id, default=True)
    handle = season.product.unique_ids.get("bjjfanatics-handle")
    if handle:
        _uniqueid(root, "bjjfanatics-handle", handle)
    for tag in season.product.tags:
        _text(root, "tag", tag)
    _lock_metadata(root)
    return root


def episode_xml(show: ShowPlan, season: SeasonPlan, episode: EpisodePlan) -> ET.Element:
    root = ET.Element("episodedetails")
    _text(root, "title", episode.title)
    _text(root, "showtitle", show.title)
    _text(root, "season", episode.season)
    _text(root, "episode", episode.episode)
    titles = [ch.title for ch in episode.chapters if ch.title.strip()]
    if season.combine_volumes or len(titles) > 1:
        plot = "; ".join(titles)
    else:
        plot = episode.volume_name or (
            f"Volume {episode.volume_number}" if episode.volume_number else ""
        )
    _text(root, "plot", plot)
    aired = season.product.premiered
    if aired:
        _text(root, "aired", aired.isoformat())
    if season.product.instructor:
        _text(root, "director", season.product.instructor)
    _lock_metadata(root)
    return root


def write_tvshow_nfo(plan: ShowPlan, folder: Path) -> Path:
    path = folder / "tvshow.nfo"
    _write(tvshow_xml(plan), path)
    return path


def write_season_nfo(show: ShowPlan, season: SeasonPlan, folder: Path) -> Path:
    path = folder / "season.nfo"
    _write(season_xml(show, season), path)
    return path


def write_episode_nfo(show: ShowPlan, season: SeasonPlan, episode: EpisodePlan, video_path: Path) -> Path:
    path = video_path.with_suffix(".nfo")
    _write(episode_xml(show, season, episode), path)
    return path
