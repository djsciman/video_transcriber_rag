from __future__ import annotations

import json
import re
from datetime import date, datetime
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from ..errors import ScrapeError
from ..httputil import DEFAULT_USER_AGENT, fetch_text
from ..models import Product, ProductImage
from .bjj_fanatics import _part_heading, _plot_stop_heading, parse_description_volumes

_TITLE_SPLIT = re.compile(r"\s+[–—-]\s+")
_SITE_SUFFIX = re.compile(
    r"\s*[-–—|]\s*Supporting Your Learning and Development\s*$",
    re.IGNORECASE,
)


def _canonical_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.rstrip("/") + "/"
    return f"https://{parsed.netloc.lower()}{path}"


def _slug_from_url(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    return path.rsplit("/", 1)[-1]


def _split_instructor_title(heading: str) -> tuple[str, str]:
    text = _SITE_SUFFIX.sub("", heading).strip()
    match = _TITLE_SPLIT.split(text, maxsplit=1)
    if len(match) == 2 and match[0].strip() and match[1].strip():
        return match[0].strip(), match[1].strip()
    return "", text


def _parse_published(soup: BeautifulSoup) -> date | None:
    for script in soup.find_all("script", attrs={"type": "application/ld+json"}):
        raw = script.string or script.get_text() or ""
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        nodes = data.get("@graph") if isinstance(data, dict) else None
        candidates = nodes if isinstance(nodes, list) else [data]
        for node in candidates:
            if not isinstance(node, dict):
                continue
            value = node.get("datePublished")
            if not value:
                continue
            try:
                return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
            except ValueError:
                match = re.match(r"(\d{4})-(\d{2})-(\d{2})", str(value))
                if match:
                    return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
    return None


def _description_html(soup: BeautifulSoup) -> str:
    block = soup.select_one("#learn-press-course-description .thim-course-content")
    if block is None:
        block = soup.select_one("#learn-press-course-description")
    if block is None:
        block = soup.select_one(".course-description")
    return str(block) if block is not None else str(soup.body or soup)


def _plot_from_description(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all(["img", "iframe", "script", "style"]):
        tag.decompose()
    chunks: list[str] = []
    for node in soup.find_all(["p", "h1", "h2", "h3", "h4", "ul", "ol"]):
        if node.find_parent(["ul", "ol"]) is not None:
            continue
        text = re.sub(r"\s+", " ", node.get_text(" ", strip=True)).strip()
        if not text:
            continue
        if _part_heading(text) or _plot_stop_heading(text):
            break
        lowered = text.lower()
        if "new year offer" in lowered or "30% off" in lowered:
            continue
        if "this course is available" in lowered:
            continue
        if node.name in {"ul", "ol"}:
            items = [
                re.sub(r"\s+", " ", li.get_text(" ", strip=True)).strip()
                for li in node.find_all("li", recursive=False)
            ]
            chunks.extend(item for item in items if item)
            continue
        if node.name in {"h1", "h2", "h3", "h4"}:
            continue
        chunks.append(text)
    plot = "\n".join(chunks).strip()
    return plot


def _meta_int(soup: BeautifulSoup, property_name: str) -> int:
    tag = soup.select_one(f'meta[property="{property_name}"]')
    if tag is None:
        return 0
    try:
        return int(tag.get("content") or 0)
    except (TypeError, ValueError):
        return 0


def _images(soup: BeautifulSoup) -> list[ProductImage]:
    og = soup.select_one('meta[property="og:image"]')
    src = (og.get("content") if og else "") or ""
    if src.startswith("//"):
        src = "https:" + src
    if not src.startswith("http"):
        return []
    width = _meta_int(soup, "og:image:width")
    height = _meta_int(soup, "og:image:height")
    # Keep existing Fanatics covers when the mirror only has a landscape thumb.
    if not width or height < width:
        return []
    return [ProductImage(url=src, width=width, height=height, alt="", position=1)]


def product_from_html(html: str, source_url: str) -> Product:
    soup = BeautifulSoup(html, "lxml")
    heading = ""
    title_el = soup.select_one("h1.entry-title") or soup.select_one("h1")
    if title_el is not None:
        heading = re.sub(r"\s+", " ", title_el.get_text(" ", strip=True)).strip()
    if not heading:
        og = soup.select_one('meta[property="og:title"]')
        heading = (og.get("content") if og else "") or ""
        heading = _SITE_SUFFIX.sub("", heading).strip()
    instructor, title = _split_instructor_title(heading)
    if not title:
        raise ScrapeError("BrainLearns page is missing a title")
    description = _description_html(soup)
    volumes = parse_description_volumes(description)
    if not volumes:
        raise ScrapeError("BrainLearns page has no Part/Volume course contents")
    premiered = _parse_published(soup)
    slug = _slug_from_url(source_url)
    return Product(
        title=title,
        instructor=instructor,
        plot=_plot_from_description(description),
        premiered=premiered,
        year=premiered.year if premiered else None,
        tags=["Instructional"],
        unique_ids={"brainlearns": slug} if slug else {},
        images=_images(soup),
        volumes=volumes,
        source_url=_canonical_url(source_url),
    )


class BrainLearnsScraper:
    def can_handle(self, url: str) -> bool:
        host = urlparse(url).netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        return host == "brainlearns.org"

    def fetch(self, url: str, user_agent: str | None = None) -> Product:
        ua = user_agent or DEFAULT_USER_AGENT
        html = fetch_text(url, user_agent=ua)
        return product_from_html(html, url)
