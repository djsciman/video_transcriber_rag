from __future__ import annotations

from urllib.parse import urlparse

from ..errors import ScrapeError
from ..models import Product
from .bjj_fanatics import BjjFanaticsScraper

SCRAPERS = [BjjFanaticsScraper()]


def fetch_product(url: str, user_agent: str | None = None) -> Product:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ScrapeError(f"Not a valid http(s) URL: {url}")
    for scraper in SCRAPERS:
        if scraper.can_handle(url):
            return scraper.fetch(url, user_agent=user_agent)
    raise ScrapeError(
        f"No scraper for host {parsed.netloc!r}. v1 supports bjjfanatics.com only."
    )
