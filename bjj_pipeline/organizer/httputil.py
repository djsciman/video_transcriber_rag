from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from typing import Any

from .errors import ScrapeError

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
TIMEOUT = 20
RETRIES = 1


def fetch_bytes(url: str, user_agent: str = DEFAULT_USER_AGENT) -> tuple[bytes, str]:
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    last_error: Exception | None = None
    attempts = RETRIES + 1
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                content_type = resp.headers.get("Content-Type", "")
                return resp.read(), content_type
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code in {429, 500, 502, 503} and attempt < attempts - 1:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise ScrapeError(f"HTTP {exc.code} fetching {url}") from exc
        except (TimeoutError, urllib.error.URLError) as exc:
            last_error = exc
            if attempt < attempts - 1:
                time.sleep(1.5 * (attempt + 1))
                continue
            raise ScrapeError(f"Failed to fetch {url}: {exc}") from exc
    raise ScrapeError(f"Failed to fetch {url}: {last_error}")


def fetch_text(url: str, user_agent: str = DEFAULT_USER_AGENT) -> str:
    data, _ = fetch_bytes(url, user_agent)
    return data.decode("utf-8", errors="replace")


def fetch_json(url: str, user_agent: str = DEFAULT_USER_AGENT) -> Any:
    text = fetch_text(url, user_agent)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise ScrapeError(f"Invalid JSON from {url}") from exc
