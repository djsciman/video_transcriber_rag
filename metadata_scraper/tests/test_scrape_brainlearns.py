from datetime import date
from pathlib import Path

from bjj_organizer.scrape.base import fetch_product
from bjj_organizer.scrape.brainlearns import BrainLearnsScraper, product_from_html
from bjj_organizer.scrape.bjj_fanatics import parse_description_volumes

FIXTURES = Path(__file__).parent / "fixtures"
URL = "https://brainlearns.org/courses/jacob-couch-finishing-leg-locks-daisy-fresh-style/"


def test_brainlearns_scraper_handles_host():
    scraper = BrainLearnsScraper()
    assert scraper.can_handle(URL)
    assert scraper.can_handle("https://www.brainlearns.org/courses/x/")
    assert not scraper.can_handle("https://bjjfanatics.com/products/x")


def test_couch_page_becomes_four_untimed_volumes():
    html = (FIXTURES / "jacob_couch_brainlearns.html").read_text(encoding="utf-8")
    product = product_from_html(html, URL)
    assert product.instructor == "Jacob Couch"
    assert product.title == "Finishing Leg Locks Daisy Fresh Style"
    assert product.premiered == date(2024, 1, 19)
    assert product.unique_ids["brainlearns"] == "jacob-couch-finishing-leg-locks-daisy-fresh-style"
    assert product.images == []
    assert "Join Daisy Fresh Star" in product.plot
    assert "PART 1" not in product.plot
    assert "New Year Offer" not in product.plot
    assert [volume.name for volume in product.volumes] == [
        "Volume 1",
        "Volume 2",
        "Volume 3",
        "Volume 4",
    ]
    assert [chapter.title for chapter in product.volumes[0].chapters] == [
        "INTRO",
        "APPALACHIAN MOUNTAIN",
        "INTRO TO DRILLS",
        "WARM UPS",
        "SAME SIDE SADDLE DRILL",
        "FAR SIDE SADDLE",
        "SWITCHING SIDES",
        "SHUCKYBEAN STRAIGHT ANKLE",
        "LOWER BODY POSITION",
        "CHEST POSITION",
        "WRIST AND ELBOW POSITION",
        "HOW TO ADJUST THE BITE",
    ]
    assert [chapter.title for chapter in product.volumes[1].chapters] == [
        "MOUNTAIN DEW MAYHEM OUTSIDE HEEL HOOK FINISHING DETAILS",
        "STANDARD OUTSIDE HEEL HOOK",
        "DOUBLE OUTSIDE",
        "OUTSIDE TRIANGLE",
        "CLASSIC REAP",
    ]
    assert product.volumes[2].chapters[0].title == "HOLLER HOOK INSIDE HEEL HOOK FINISHING DETAILS"
    assert [chapter.title for chapter in product.volumes[3].chapters][-1] == "OUTRO"
    assert all(chapter.start_ms == 0 for volume in product.volumes for chapter in volume.chapters)


def test_description_parts_keep_section_headings_until_next_part():
    html = (FIXTURES / "jacob_couch_brainlearns.html").read_text(encoding="utf-8")
    volumes = parse_description_volumes(html)
    assert len(volumes) == 4
    assert "Course Features" not in [chapter.title for volume in volumes for chapter in volume.chapters]


def test_fetch_product_routes_to_brainlearns(monkeypatch):
    html = (FIXTURES / "jacob_couch_brainlearns.html").read_text(encoding="utf-8")
    monkeypatch.setattr(
        "bjj_pipeline.organizer.scrape.brainlearns.fetch_text",
        lambda url, user_agent=None: html,
    )
    product = fetch_product(URL)
    assert product.title == "Finishing Leg Locks Daisy Fresh Style"
    assert len(product.volumes) == 4
