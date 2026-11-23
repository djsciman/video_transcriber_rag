from __future__ import annotations

from urllib.parse import urlparse

from ..errors import ScrapeError
from ..models import Product
from .bjj_fanatics import BjjFanaticsScraper
from .brainlearns import BrainLearnsScraper
from .local import LocalCourseScraper

SCRAPERS = [BjjFanaticsScraper(), BrainLearnsScraper(), LocalCourseScraper()]


def fetch_product(url: str, user_agent: str | None = None) -> Product:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https", "file"}:
        raise ScrapeError(f"Not a valid URL: {url}")
    if parsed.scheme in {"http", "https"} and not parsed.netloc:
        raise ScrapeError(f"Not a valid http(s) URL: {url}")
    for scraper in SCRAPERS:
        if scraper.can_handle(url):
            return scraper.fetch(url, user_agent=user_agent)
    raise ScrapeError(
        f"No scraper for {parsed.scheme} {parsed.netloc or parsed.path!r}. "
        "Supported: bjjfanatics.com, brainlearns.org, and local file:// course JSON/PDF."
    )
