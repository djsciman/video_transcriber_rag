from __future__ import annotations

import re
from datetime import date, datetime
from html import unescape
from urllib.parse import urlparse, urlunparse

from bs4 import BeautifulSoup

from ..errors import ScrapeError
from ..httputil import DEFAULT_USER_AGENT, fetch_json, fetch_text
from ..models import Chapter, Product, ProductImage, Volume

PLOT_STOP_HEADINGS = (
    "check out a free sample",
    "so, what exactly do you get",
    "so, what's on the series",
    "so, whats on the series",
)
SKIP_TAGS = {
    "above-30",
    "above-60",
    "facebook",
    "new",
    "show_more_app",
    "instagram",
    "youtube",
}


def _clock_to_ms(text: str) -> int | None:
    if re.fullmatch(r"\d+", text):
        return int(text) * 1000
    parts = text.split(":")
    if not all(part.isdigit() for part in parts) or len(parts) not in {2, 3}:
        return None
    nums = [int(part) for part in parts]
    if len(nums) == 2:
        minutes, seconds = nums
        hours = 0
    else:
        hours, minutes, seconds = nums
        # Spreadsheet exports dump mm:ss as hh:mm:ss (40:15:00 is 40:15).
        if hours > 23 and seconds == 0:
            minutes, seconds = hours, minutes
            hours = 0
    return ((hours * 3600) + (minutes * 60) + seconds) * 1000


def parse_timestamp_ms(raw: str) -> int | None:
    text = raw.strip().replace(";", ":")
    # Ranges are "0 - 11:55" or, on some pages, "0- 2:44".
    if "-" in text:
        left, right = re.split(r"\s*-\s*", text, maxsplit=1)
        if _clock_to_ms(right.strip()) is not None:
            text = left.strip()
    if not text:
        return None
    return _clock_to_ms(text)


def json_url_for(product_url: str) -> str:
    parsed = urlparse(product_url)
    path = parsed.path.rstrip("/")
    if not path.endswith(".json"):
        path = f"{path}.json"
    return urlunparse(("https", parsed.netloc, path, "", "", ""))


def html_url_for(product_url: str) -> str:
    parsed = urlparse(product_url)
    path = parsed.path.rstrip("/")
    if path.endswith(".json"):
        path = path[: -len(".json")]
    return urlunparse(("https", parsed.netloc, path, "", "", ""))


def course_content_url_for(product_url: str) -> str:
    """Shopify alternate template with Course Content ``figure.table`` rows."""
    parsed = urlparse(html_url_for(product_url))
    return urlunparse(("https", parsed.netloc, parsed.path, "", "view=course-content-v2", ""))


def _parse_premiered(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        match = re.match(r"(\d{4})-(\d{2})-(\d{2})", value)
        if match:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    return None


def clean_plot(body_html: str) -> str:
    if "<!-- split -->" in body_html:
        body_html = body_html.split("<!-- split -->", 1)[0]
    soup = BeautifulSoup(body_html, "lxml")
    for heading in soup.find_all(["h1", "h2", "h3"]):
        if heading.get_text(" ", strip=True).lower() in PLOT_STOP_HEADINGS:
            for sibling in list(heading.find_all_next()):
                sibling.decompose()
            heading.decompose()
            break
    text = soup.get_text("\n", strip=True)
    text = unescape(re.sub(r"\n{3,}", "\n\n", text)).strip()
    return text


def _product_tags(raw: str) -> list[str]:
    tags = ["Instructional"]
    for tag in (t.strip() for t in raw.split(",")):
        if not tag:
            continue
        lowered = tag.lower()
        if lowered in SKIP_TAGS or lowered.startswith("fighter_"):
            continue
        if tag.startswith("MC_"):
            tags.append(tag[3:])
        else:
            tags.append(tag)
    seen: set[str] = set()
    out: list[str] = []
    for tag in tags:
        key = tag.lower()
        if key not in seen:
            seen.add(key)
            out.append(tag)
    return out


def select_images(raw_images: list[dict]) -> list[ProductImage]:
    images: list[ProductImage] = []
    for item in raw_images:
        src = item.get("src") or ""
        if not src:
            continue
        if src.startswith("//"):
            src = "https:" + src
        images.append(
            ProductImage(
                url=src,
                width=int(item.get("width") or 0),
                height=int(item.get("height") or 0),
                alt=item.get("alt") or "",
                position=int(item.get("position") or 0),
            )
        )
    return images


def pick_poster(images: list[ProductImage]) -> ProductImage | None:
    portraits = []
    for image in images:
        blob = f"{image.url} {image.alt}".lower()
        if "coverback" in blob or "back.jpg" in blob:
            continue
        portraits.append(image)
    if not portraits:
        portraits = list(images)
    with_cover = [img for img in portraits if "cover" in f"{img.url} {img.alt}".lower()]
    candidates = with_cover or portraits
    candidates.sort(key=lambda img: (0 if img.height >= img.width else 1, img.position))
    return candidates[0] if candidates else None


def pick_fanart(images: list[ProductImage], poster: ProductImage | None) -> ProductImage | None:
    for image in images:
        if poster and image.url == poster.url:
            continue
        if image.width > image.height and image.width >= 800:
            blob = f"{image.url} {image.alt}".lower()
            if "coverback" in blob:
                continue
            return image
    return None


_PART_HEADING = re.compile(
    r"(?:part|volume|disc|dvd)\s*(\d+)\b[:\s-]*(.*)\Z",
    re.IGNORECASE,
)


def _part_heading(text: str) -> tuple[int, str] | None:
    cleaned = text.replace("\xa0", " ")
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if not cleaned or len(cleaned) > 60:
        return None
    match = _PART_HEADING.fullmatch(cleaned)
    if match is None:
        return None
    extra = match.group(2).strip(" :-")
    if len(extra) > 40:
        return None
    return int(match.group(1)), extra


def _chapter_title(text: str) -> str:
    title = text.replace("\xa0", " ")
    return re.sub(r"\s+", " ", title).strip()


def parse_description_volumes(html: str) -> list[Volume]:
    """Part/Volume headings and bullet lists from the product description.

    Older Fanatics pages omit the Course Content accordion and list each disc
    as "Part N" with technique names and no start times.
    """
    if not html or not html.strip():
        return []
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all(["img", "iframe", "script", "style"]):
        tag.decompose()
    nodes = [
        node
        for node in soup.find_all(["p", "h1", "h2", "h3", "h4", "ul", "ol"])
        if node.find_parent(["ul", "ol"]) is None
    ]
    volumes: list[Volume] = []
    index = 0
    while index < len(nodes):
        node = nodes[index]
        if node.name in {"ul", "ol"}:
            index += 1
            continue
        heading = _part_heading(node.get_text(" ", strip=True))
        if heading is None:
            index += 1
            continue
        number, extra = heading
        chapters: list[Chapter] = []
        cursor = index + 1
        while cursor < len(nodes):
            nxt = nodes[cursor]
            if nxt.name not in {"ul", "ol"} and _part_heading(nxt.get_text(" ", strip=True)):
                break
            if nxt.name in {"ul", "ol"}:
                for li in nxt.find_all("li", recursive=False):
                    title = _chapter_title(li.get_text(" ", strip=True))
                    if title:
                        chapters.append(Chapter(title=title, start_ms=0))
                cursor += 1
                break
            cursor += 1
        if chapters:
            name = f"Volume {number}"
            if extra:
                name = f"{name} {extra}"
            volumes.append(Volume(name=name, chapters=tuple(chapters)))
        index = cursor if cursor > index else index + 1
    return volumes


def _course_row(cells: list[str]) -> Chapter | None:
    """Read a two-cell course-content row as title + start time.

    Usual layout is title then stamp. Some Danaher pages reverse that
    (stamp or '0 - 3:32' range in the first cell, title in the second).
    """
    left, right = cells[0], cells[1]
    if left.upper() == "CHAPTER TITLE" or right.upper() == "CHAPTER TITLE":
        return None
    left_ms = parse_timestamp_ms(left)
    right_ms = parse_timestamp_ms(right)
    if left_ms is not None and right_ms is None:
        title, start_ms = right, left_ms
    elif right_ms is not None:
        title, start_ms = left, right_ms
    else:
        return None
    title = _chapter_title(title)
    if not title:
        return None
    return Chapter(title=title, start_ms=start_ms)


def _promote_hour_minute_stamps(chapters: list[Chapter]) -> list[Chapter]:
    """Treat a later ``1:44`` as 1:44:00 when mm:ss would jump backwards.

    Some Danaher tables mix ``1:15:45`` with ``1:44`` meaning one hour
    forty-four minutes, not one minute forty-four seconds.
    """
    if not chapters:
        return chapters
    out: list[Chapter] = []
    prev = -1
    for chapter in chapters:
        start = chapter.start_ms
        if 0 <= start < prev:
            total_sec = start // 1000
            minutes, seconds = divmod(total_sec, 60)
            if minutes <= 9:
                promoted = ((minutes * 3600) + (seconds * 60)) * 1000
                if promoted > prev:
                    start = promoted
        if start != chapter.start_ms:
            chapter = Chapter(title=chapter.title, start_ms=start)
        out.append(chapter)
        if start > prev:
            prev = start
    return out


def _demote_excel_hour_stamps(chapters: list[Chapter]) -> list[Chapter]:
    """Treat ``17:04:00`` as 17:04 when a later Excel ``24:59:00`` is smaller.

    Hours 1-23 with seconds 0 parse as H:MM:SS. In a mm:ss spreadsheet dump
    they are 17:04, and a later ``24:59:00`` (already demoted) exposes that.
    """
    if len(chapters) < 2:
        return chapters
    starts = [chapter.start_ms for chapter in chapters]
    out: list[Chapter] = []
    for index, chapter in enumerate(chapters):
        start = starts[index]
        hours, rem = divmod(start // 1000, 3600)
        minutes, seconds = divmod(rem, 60)
        later_smaller = [value for value in starts[index + 1 :] if value < start]
        if seconds == 0 and 1 <= hours <= 23 and later_smaller:
            as_mmss = (hours * 60 + minutes) * 1000
            prev = out[-1].start_ms if out else -1
            nxt = min(later_smaller)
            if prev < as_mmss < nxt:
                start = as_mmss
                starts[index] = start
        if start != chapter.start_ms:
            chapter = Chapter(title=chapter.title, start_ms=start)
        out.append(chapter)
    return out


def _repair_jumped_excel_stamps(chapters: list[Chapter]) -> list[Chapter]:
    """Fix ``8:06:00`` between ``53:14:00`` and ``1:02:38``.

    Excel dumps mm:ss as hh:mm:ss. A dropped tens digit turns 58:06 into
    8:06:00 (eight hours), which jumps past the next chapter.
    """
    if len(chapters) < 2:
        return chapters
    out = list(chapters)
    for index, chapter in enumerate(out):
        nxt = out[index + 1].start_ms if index + 1 < len(out) else None
        prev = out[index - 1].start_ms if index else -1
        start = chapter.start_ms
        if nxt is None or start <= nxt:
            continue
        total_sec = start // 1000
        hours, rem = divmod(total_sec, 3600)
        minutes, seconds = divmod(rem, 60)
        if seconds != 0 or hours == 0 or hours > 23:
            continue
        candidates = [(hours * 60 + minutes) * 1000]
        if prev > 0:
            prev_min = (prev // 1000) // 60
            tens = (prev_min % 60) // 10
            candidates.append(((tens * 10 + hours) * 60 + minutes) * 1000)
        for candidate in candidates:
            if prev < candidate < nxt:
                out[index] = Chapter(title=chapter.title, start_ms=candidate)
                break
    return out


def _normalize_stamps(chapters: list[Chapter]) -> list[Chapter]:
    return _repair_jumped_excel_stamps(
        _demote_excel_hour_stamps(_promote_hour_minute_stamps(chapters))
    )


def _chapters_from_table(table) -> list[Chapter]:
    chapters: list[Chapter] = []
    for row in table.select("tr"):
        cells = [c.get_text(" ", strip=True) for c in row.find_all(["td", "th"])]
        if len(cells) < 2:
            continue
        chapter = _course_row(cells)
        if chapter is None:
            continue
        chapters.append(chapter)
    return _normalize_stamps(chapters)


def parse_course_content(html: str) -> list[Volume]:
    soup = BeautifulSoup(html, "lxml")
    accordion = soup.select_one(".product__course-content-accordion")
    volumes: list[Volume] = []
    if accordion is not None:
        for heading in accordion.select("h3.product__course-title"):
            name = heading.get_text(" ", strip=True)
            name = re.sub(r"\s+", " ", name).strip()
            block = heading.find_next_sibling("div", class_="product__course-content")
            if block is None:
                continue
            chapters: list[Chapter] = []
            for table in block.select("table"):
                chapters.extend(_chapters_from_table(table))
            chapters = _normalize_stamps(chapters)
            volumes.append(Volume(name=name or f"Volume {len(volumes) + 1}", chapters=tuple(chapters)))
        if volumes:
            return volumes
    # Shopify course-content-v2 (and pasted HTML) uses figure.table without accordion.
    for figure in soup.select("figure.table"):
        chapters = []
        for table in figure.select("table"):
            chapters.extend(_chapters_from_table(table))
        chapters = _normalize_stamps(chapters)
        if chapters:
            volumes.append(Volume(name=f"Volume {len(volumes) + 1}", chapters=tuple(chapters)))
    return volumes


def product_from_payloads(json_data: dict, html: str, source_url: str) -> Product:
    product = json_data.get("product") if "product" in json_data else json_data
    if not isinstance(product, dict) or not product.get("title"):
        raise ScrapeError("Product JSON is missing a title")
    premiered = _parse_premiered(product.get("published_at"))
    images = select_images(product.get("images") or [])
    unique_ids = {}
    if product.get("id") is not None:
        unique_ids["bjjfanatics"] = str(product["id"])
    if product.get("handle"):
        unique_ids["bjjfanatics-handle"] = str(product["handle"])
    return Product(
        title=str(product["title"]).strip(),
        instructor=str(product.get("vendor") or "").strip(),
        plot=clean_plot(product.get("body_html") or ""),
        premiered=premiered,
        year=premiered.year if premiered else None,
        tags=_product_tags(product.get("tags") or ""),
        unique_ids=unique_ids,
        images=images,
        volumes=parse_course_content(html) or parse_description_volumes(str(product.get("body_html") or "")),
        source_url=source_url,
    )


class BjjFanaticsScraper:
    def can_handle(self, url: str) -> bool:
        host = urlparse(url).netloc.lower()
        return host == "bjjfanatics.com" or host.endswith(".bjjfanatics.com")

    def fetch(self, url: str, user_agent: str | None = None) -> Product:
        ua = user_agent or DEFAULT_USER_AGENT
        html_url = html_url_for(url)
        data = fetch_json(json_url_for(html_url), user_agent=ua)
        html = fetch_text(course_content_url_for(html_url), user_agent=ua)
        return product_from_payloads(data, html, html_url)
