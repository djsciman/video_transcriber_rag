import json
from pathlib import Path

from bjj_organizer.scrape.bjj_fanatics import (
    clean_plot,
    course_content_url_for,
    html_url_for,
    parse_course_content,
    parse_description_volumes,
    parse_timestamp_ms,
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


def test_course_row_swaps_when_clock_is_first():
    html = """
    <div class="product__course-content-accordion">
      <h3 class="product__course-title">Volume 1</h3>
      <div class="product__course-content">
        <table>
          <tr><td>4:20</td><td>The Criteria for Takedown Selection for Jiu Jitsu</td></tr>
          <tr><td>40:15:00</td><td>The First Precursor Skill of the Standing Position: Stance</td></tr>
          <tr><td>1:00:35</td><td>Left &amp; Right Stances</td></tr>
        </table>
      </div>
    </div>
    """
    volumes = parse_course_content(html)
    assert [chapter.title for chapter in volumes[0].chapters] == [
        "The Criteria for Takedown Selection for Jiu Jitsu",
        "The First Precursor Skill of the Standing Position: Stance",
        "Left & Right Stances",
    ]
    assert volumes[0].chapters[0].start_ms == (4 * 60 + 20) * 1000
    assert volumes[0].chapters[1].start_ms == (40 * 60 + 15) * 1000
    assert volumes[0].chapters[2].start_ms == ((1 * 3600) + 35) * 1000


def test_course_row_swaps_when_range_is_first():
    html = """
    <div class="product__course-content-accordion">
      <h3 class="product__course-title">Volume 1</h3>
      <div class="product__course-content">
        <table>
          <tr><td>0 - 3:32</td><td>Theory - What is the value of the open guard position?</td></tr>
          <tr><td>3:32 - 10:08</td><td>a contradiction in Jiu-Jitsu</td></tr>
        </table>
      </div>
    </div>
    """
    volumes = parse_course_content(html)
    assert [chapter.title for chapter in volumes[0].chapters] == [
        "Theory - What is the value of the open guard position?",
        "a contradiction in Jiu-Jitsu",
    ]
    assert volumes[0].chapters[0].start_ms == 0
    assert volumes[0].chapters[1].start_ms == (3 * 60 + 32) * 1000


def test_excel_clock_and_semicolon_stamps():
    assert parse_timestamp_ms("40:15:00") == (40 * 60 + 15) * 1000
    assert parse_timestamp_ms("1:00:35") == ((1 * 3600) + 35) * 1000
    assert parse_timestamp_ms("23;53 - 27:33") == (23 * 60 + 53) * 1000


def test_excel_hour_stamp_demoted_when_later_row_is_smaller():
    html = """
    <div class="product__course-content-accordion">
      <h3 class="product__course-title">Volume 8</h3>
      <div class="product__course-content">
        <table>
          <tr><td>4:45</td><td>Phase 2: Capture the Leg</td></tr>
          <tr><td>17:04:00</td><td>Phase 3: Transfer to the High Leg</td></tr>
          <tr><td>18:55:00</td><td>Head Position</td></tr>
          <tr><td>24:59:00</td><td>The Instant Off Balance</td></tr>
        </table>
      </div>
    </div>
    """
    volumes = parse_course_content(html)
    starts = [chapter.start_ms for chapter in volumes[0].chapters]
    assert starts == [
        (4 * 60 + 45) * 1000,
        (17 * 60 + 4) * 1000,
        (18 * 60 + 55) * 1000,
        (24 * 60 + 59) * 1000,
    ]


def test_excel_stamp_with_dropped_tens_digit():
    html = """
    <div class="product__course-content-accordion">
      <h3 class="product__course-title">Volume 5</h3>
      <div class="product__course-content">
        <table>
          <tr><td>53:14:00</td><td>Ability To Get Opponent’s Head Over The Ankle You Are Attacking</td></tr>
          <tr><td>8:06:00</td><td>Ability To Keep Opponent’s Head Same Height As Yours</td></tr>
          <tr><td>1:02:38</td><td>Ability To Go From One Ankle To Another</td></tr>
        </table>
      </div>
    </div>
    """
    volumes = parse_course_content(html)
    starts = [chapter.start_ms for chapter in volumes[0].chapters]
    assert starts == [
        (53 * 60 + 14) * 1000,
        (58 * 60 + 6) * 1000,
        ((1 * 3600) + (2 * 60) + 38) * 1000,
    ]


def test_short_clock_after_hour_stamp_is_hour_minute():
    html = """
    <div class="product__course-content-accordion">
      <h3 class="product__course-title">Volume 2</h3>
      <div class="product__course-content">
        <table>
          <tr><td>1:40:27</td><td>Strategy 2</td></tr>
          <tr><td>1:44</td><td>Strategy 3</td></tr>
          <tr><td>1:50</td><td>Strategy 4</td></tr>
        </table>
      </div>
    </div>
    """
    volumes = parse_course_content(html)
    starts = [chapter.start_ms for chapter in volumes[0].chapters]
    assert starts == [
        ((1 * 3600) + (40 * 60) + 27) * 1000,
        ((1 * 3600) + (44 * 60)) * 1000,
        ((1 * 3600) + (50 * 60)) * 1000,
    ]


def test_course_content_url_uses_v2_view():
    url = "https://bjjfanatics.com/products/the-half-guard-anthology-by-lachlan-giles?_pos=1&_sid=x&view=course-content-v2"
    assert html_url_for(url) == "https://bjjfanatics.com/products/the-half-guard-anthology-by-lachlan-giles"
    assert course_content_url_for(url) == (
        "https://bjjfanatics.com/products/the-half-guard-anthology-by-lachlan-giles"
        "?view=course-content-v2"
    )


def test_figure_table_ranges_without_accordion():
    html = """
<figure class="table">
    <table>
           <tbody>
               <tr>
                   <td>1 OVERVIEW AND GENERAL CONCEPTS</td>
                   <td>0:00 - 12:12</td>
               </tr>
               <tr>
                   <td>2 ENTRIES</td>
                   <td>12:12 - 13:33</td>
               </tr>
               <tr>
                   <td>STANDING OPPONENT</td>
                   <td>13:33 - 20:31</td>
               </tr>
               <tr>
                   <td>KNEELING OPPONENT</td>
                   <td>20:31 - 28:12</td>
               </tr>
               <tr>
                   <td>BRINGING IT TOGETHER</td>
                   <td>28:12 - 31:50</td>
               </tr>
           </tbody>
       </table>
    </figure>
"""
    volumes = parse_course_content(html)
    assert len(volumes) == 1
    titles = [chapter.title for chapter in volumes[0].chapters]
    starts = [chapter.start_ms for chapter in volumes[0].chapters]
    assert titles == [
        "1 OVERVIEW AND GENERAL CONCEPTS",
        "2 ENTRIES",
        "STANDING OPPONENT",
        "KNEELING OPPONENT",
        "BRINGING IT TOGETHER",
    ]
    assert starts == [
        0,
        (12 * 60 + 12) * 1000,
        (13 * 60 + 33) * 1000,
        (20 * 60 + 31) * 1000,
        (28 * 60 + 12) * 1000,
    ]


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
