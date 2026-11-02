import json
from pathlib import Path

from bjj_organizer.scrape.bjj_fanatics import (
    clean_plot,
    parse_course_content,
    parse_description_volumes,
    pick_poster,
    product_from_payloads,
)

FIXTURES = Path(__file__).parent / "fixtures"


def test_course_row_keeps_chapter_when_range_hyphen_has_no_space():
    html = """
    <div class="product__course-content-accordion">
      <h3 class="product__course-title">Volume 2</h3>
      <div class="product__course-content">
        <table>
          <tr><td>quick switch steering wheel sweep</td><td>0- 2:44</td></tr>
          <tr><td>whizzer sweep</td><td>2:44 - 7:13</td></tr>
        </table>
      </div>
    </div>
    """
    volumes = parse_course_content(html)
    assert [chapter.title for chapter in volumes[0].chapters] == [
        "quick switch steering wheel sweep",
        "whizzer sweep",
    ]
    assert volumes[0].chapters[0].start_ms == 0
    assert volumes[0].chapters[1].start_ms == (2 * 60 + 44) * 1000


def test_parse_course_content_fixture():
    html = (FIXTURES / "craig_funk_course.html").read_text(encoding="utf-8")
    volumes = parse_course_content(html)
    assert [v.name for v in volumes] == ["Volume 1", "Volume 2", "Volume 3", "Volume 4"]
    assert volumes[0].chapters[0].title == "Intro"
    assert volumes[0].chapters[0].start_ms == 0
    assert volumes[0].chapters[1].title == "BJJ Fundamentals - What to Expect"
    assert volumes[0].chapters[1].start_ms == 65_000
    belt = [c for c in volumes[0].chapters if "Tie Your Pants" in c.title][0]
    assert belt.start_ms == ((1 * 3600) + (1 * 60) + 11) * 1000
    assert len(volumes[3].chapters) >= 8


def test_product_from_json_and_html():
    data = json.loads((FIXTURES / "craig_funk_product.json").read_text(encoding="utf-8"))
    html = (FIXTURES / "craig_funk_course.html").read_text(encoding="utf-8")
    product = product_from_payloads(data, html, "https://bjjfanatics.com/products/beginner-beginner-bjj-by-craig-funk")
    assert product.title == "Beginner Beginner BJJ by Craig Funk"
    assert product.instructor == "Craig Funk"
    assert product.year == 2021
    assert product.unique_ids["bjjfanatics"] == "6599488045154"
    assert "Check out a free sample" not in product.plot
    assert "Jumpstart" in product.plot
    poster = pick_poster(product.images)
    assert poster is not None
    assert "Coverback" not in poster.url
    assert "Cover.jpg" in poster.url or "Cover" in poster.url
    assert "Fundamentals" in product.tags
    assert len(product.volumes) == 4


DESCRIPTION_PARTS = """
<p>The best no-gi grappler on Earth shares his seated open guard.</p>
<!-- split -->
<h2>So, What Exactly Is On This Series?</h2>
<p>Across 8-volumes, learn the system behind the open guard.</p>
<p><span><strong>Part 1:</strong></span></p>
<ul>
  <li>Intro</li>
  <li>Goal setting</li>
</ul>
<p><img alt="" src="https://example.com/gordon.jpg"></p>
<p><span><strong>Part 7 Rolling:</strong></span></p>
<ul>
  <li>Placido</li>
  <li>Jack&nbsp;</li>
</ul>
<p><span><strong>Part 8 Rolling Commentary:</strong></span></p>
<ul>
  <li>Shawn</li>
</ul>
"""


def test_description_parts_become_volumes_without_timestamps():
    volumes = parse_description_volumes(DESCRIPTION_PARTS)
    assert [volume.name for volume in volumes] == [
        "Volume 1",
        "Volume 7 Rolling",
        "Volume 8 Rolling Commentary",
    ]
    assert [chapter.title for chapter in volumes[0].chapters] == ["Intro", "Goal setting"]
    assert volumes[1].chapters[1].title == "Jack"
    assert all(chapter.start_ms == 0 for volume in volumes for chapter in volume.chapters)


def test_product_uses_description_when_page_has_no_accordion():
    data = {
        "product": {
            "title": "Systematically Attacking From Open Guard Seated Position by Gordon Ryan",
            "vendor": "Gordon Ryan",
            "body_html": DESCRIPTION_PARTS,
            "id": 4461188546658,
            "published_at": "2020-07-08T07:28:42-04:00",
            "tags": "MC_Guard",
            "images": [],
        }
    }
    product = product_from_payloads(data, "<html><body></body></html>", "https://bjjfanatics.com/products/x")
    assert [volume.name for volume in product.volumes] == [
        "Volume 1",
        "Volume 7 Rolling",
        "Volume 8 Rolling Commentary",
    ]
    assert "Goal setting" not in product.plot
    assert "seated open guard" in product.plot


def test_accordion_wins_over_description_parts():
    data = json.loads((FIXTURES / "craig_funk_product.json").read_text(encoding="utf-8"))
    data["product"]["body_html"] = DESCRIPTION_PARTS
    html = (FIXTURES / "craig_funk_course.html").read_text(encoding="utf-8")
    product = product_from_payloads(
        data,
        html,
        "https://bjjfanatics.com/products/beginner-beginner-bjj-by-craig-funk",
    )
    assert [volume.name for volume in product.volumes] == ["Volume 1", "Volume 2", "Volume 3", "Volume 4"]
    assert product.volumes[0].chapters[1].start_ms == 65_000


def test_plot_stops_at_split():
    html = "Hello<!-- split -->IGNORE ME"
    assert clean_plot(html) == "Hello"
    assert "IGNORE" not in clean_plot(html)
