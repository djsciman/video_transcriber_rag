from datetime import date
from pathlib import Path

from bjj_organizer.models import Chapter, EpisodePlan, Product, SeasonPlan, ShowPlan, Volume
from bjj_organizer.nfo import episode_xml, season_xml, tvshow_xml, write_tvshow_nfo


def _product() -> Product:
    return Product(
        title="Closed Guard",
        instructor="John Danaher",
        plot="A plot.",
        premiered=date(2018, 6, 1),
        year=2018,
        tags=["Instructional", "Fundamentals"],
        unique_ids={"bjjfanatics": "123"},
        images=[],
        volumes=[Volume("Volume 1", (Chapter("Intro", 0),))],
        source_url="https://bjjfanatics.com/products/x",
    )


def _show() -> ShowPlan:
    product = _product()
    season = SeasonPlan(
        source_dir=Path("Closed Guard"),
        source_name="Closed Guard",
        dest_name="Season 01",
        number=1,
        product=product,
        episodes=[
            EpisodePlan(
                source=Path("a.mp4"),
                dest_dir=Path("Season 01"),
                dest_name="01.01 - Overview.mp4",
                season=1,
                episode=1,
                title="1.1 Overview",
                chapters=[Chapter("Overview", 0)],
                extension=".mp4",
                volume_number=1,
                chapter_number=1,
                chapter_title="Overview",
                volume_name="Volume 1",
                mode="segmented",
            )
        ],
    )
    return ShowPlan(
        source_dir=Path("Go Further Faster"),
        dest_name="Go Further Faster by John Danaher",
        title="Go Further Faster by John Danaher",
        instructors=["John Danaher"],
        seasons=[season],
        year=2018,
        premiered=date(2018, 6, 1),
        plot="A plot.\n\nSeasons:\n1. Closed Guard",
        unique_id="show:go-further-faster-by-john-danaher",
        nested=True,
    )


def test_tvshow_nfo_lockdata_and_namedseason(tmp_path: Path):
    plan = _show()
    xml = tvshow_xml(plan)
    blob = __import__("xml.etree.ElementTree", fromlist=["tostring"]).tostring(xml, encoding="unicode")
    assert "<lockdata>false</lockdata>" in blob
    assert "<lockedfields>Name|Overview|Genres|Studios|Tags|Cast</lockedfields>" in blob
    assert 'type="bjjfanatics"' in blob
    assert "namedseason" in blob
    assert "Closed Guard" in blob
    path = write_tvshow_nfo(plan, tmp_path)
    text = path.read_text(encoding="utf-8")
    assert text.startswith('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>')


def test_season_and_episode_nfo():
    plan = _show()
    season = plan.seasons[0]
    season_blob = __import__("xml.etree.ElementTree", fromlist=["tostring"]).tostring(
        season_xml(plan, season), encoding="unicode"
    )
    assert "<seasonnumber>1</seasonnumber>" in season_blob
    assert "<title>Closed Guard</title>" in season_blob
    ep_blob = __import__("xml.etree.ElementTree", fromlist=["tostring"]).tostring(
        episode_xml(plan, season, season.episodes[0]), encoding="unicode"
    )
    assert "<title>1.1 Overview</title>" in ep_blob
    assert "<plot>Overview</plot>" in ep_blob
    assert "<episode>1</episode>" in ep_blob
    assert "<season>1</season>" in ep_blob
    assert "<lockdata>false</lockdata>" in ep_blob


def test_episode_nfo_plot_lists_chapter_titles():
    plan = _show()
    season = plan.seasons[0]
    ep_blob = __import__("xml.etree.ElementTree", fromlist=["tostring"]).tostring(
        episode_xml(plan, season, season.episodes[0]), encoding="unicode"
    )
    assert "<plot>Overview</plot>" in ep_blob
