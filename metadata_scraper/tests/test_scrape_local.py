from pathlib import Path

from bjj_organizer.pipeline import parse_url_arg
from bjj_organizer.scrape.base import fetch_product
from bjj_organizer.scrape.local import (
    LocalCourseScraper,
    chapters_from_entries,
    file_url_to_path,
    product_from_payload,
)

COURSE = {
    "title": "The Hip Bump",
    "instructor": "Ryan Hall",
    "plot": "Master the hip bump.",
    "volumes": [
        {
            "name": "Volume 1",
            "chapters": [
                {"title": "Introduction", "duration_ms": 33_000},
                {"title": "Shapes and Expectations", "duration_ms": 332_000},
                {"title": "Principles - Base Kuzushi", "duration_ms": 462_000},
            ],
        },
        {
            "name": "Volume 2",
            "chapters": [
                {"title": "Bump Sweep - Bump 1 (Standard Bump)", "duration_ms": 388_000},
                {"title": "Bump 2 (Collar Tie Bump)", "duration_ms": 312_000},
            ],
        },
    ],
}


def test_duration_entries_become_start_times():
    chapters = chapters_from_entries(COURSE["volumes"][0]["chapters"])
    assert [chapter.title for chapter in chapters] == [
        "Introduction",
        "Shapes and Expectations",
        "Principles - Base Kuzushi",
    ]
    assert [chapter.start_ms for chapter in chapters] == [0, 33_000, 365_000]


def test_local_payload_builds_product():
    product = product_from_payload(COURSE, "file:///course.json")
    assert product.instructor == "Ryan Hall"
    assert [volume.name for volume in product.volumes] == ["Volume 1", "Volume 2"]
    assert product.volumes[1].chapters[1].start_ms == 388_000
    assert product.studio == "BJJ Fanatics"
    assert product.source_url == "file:///course.json"


def test_local_payload_keeps_studio_and_source_url():
    payload = dict(COURSE)
    payload["studio"] = "BudoVideos"
    payload["source_url"] = "https://budovideos.com/products/worm-guard-4-dvd-set-by-keenan-cornelius-preowned"
    product = product_from_payload(payload, "file:///course.json")
    assert product.studio == "BudoVideos"
    assert product.source_url.endswith("preowned")


def test_fetch_product_reads_sibling_json_for_pdf(tmp_path: Path):
    pdf = tmp_path / "bjjfanatics_course.pdf"
    pdf.write_bytes(b"%PDF")
    (tmp_path / "bjjfanatics_course.json").write_text(
        __import__("json").dumps(COURSE),
        encoding="utf-8",
    )
    product = fetch_product(pdf.as_uri())
    assert product.title == "The Hip Bump"
    assert len(product.volumes) == 2


def test_local_scraper_handles_file_urls(tmp_path: Path):
    scraper = LocalCourseScraper()
    json_path = tmp_path / "course.json"
    json_path.write_text("{}", encoding="utf-8")
    assert scraper.can_handle(json_path.as_uri())
    assert scraper.can_handle((tmp_path / "bjjfanatics_course.pdf").as_uri())
    assert not scraper.can_handle("https://bjjfanatics.com/products/x")


def test_file_url_to_path_drive_and_unc():
    drive = file_url_to_path("file:///W:/Hall%20-%20Hip%20Bump/bjjfanatics_course.pdf")
    assert drive == Path(r"W:\Hall - Hip Bump\bjjfanatics_course.pdf")
    unc = file_url_to_path(
        "file://SERVER/TVLear/BJJ%20Instructional%20Videos%20Jellyfin/Hall%20-%20Hip%20Bump/bjjfanatics_course.pdf"
    )
    assert unc == Path(
        r"\\SERVER\TVLear\BJJ Instructional Videos Jellyfin\Hall - Hip Bump\bjjfanatics_course.pdf"
    )


def test_parse_url_arg_accepts_local_course_path(tmp_path: Path):
    json_path = tmp_path / "bjjfanatics_course.json"
    json_path.write_text("{}", encoding="utf-8")
    key, url = parse_url_arg(str(json_path))
    assert key is None
    assert url == json_path.resolve().as_uri()
