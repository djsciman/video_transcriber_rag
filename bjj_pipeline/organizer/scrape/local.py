from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import url2pathname

from ..errors import ScrapeError
from ..models import Chapter, Product, Volume


def file_url_to_path(url: str) -> Path:
    parsed = urlparse(url)
    if parsed.scheme != "file":
        return Path(url)
    path = unquote(parsed.path)
    if parsed.netloc:
        return Path(f"\\\\{parsed.netloc}{path.replace('/', '\\')}")
    return Path(url2pathname(path))


def _course_json_path(path: Path) -> Path:
    if path.suffix.lower() == ".json":
        return path
    sibling = path.with_suffix(".json")
    if sibling.is_file():
        return sibling
    raise ScrapeError(
        f"No course JSON next to {path.name}. "
        "Save parsed course contents as {path.stem}.json beside the PDF."
    )


def _parse_premiered(value: object) -> date | None:
    if not value:
        return None
    text = str(value)
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        if len(text) >= 10 and text[4] == "-" and text[7] == "-":
            return date.fromisoformat(text[:10])
    return None


def chapters_from_entries(entries: list[object]) -> tuple[Chapter, ...]:
    chapters: list[Chapter] = []
    start = 0
    for raw in entries:
        if not isinstance(raw, dict):
            continue
        title = str(raw.get("title") or "").strip()
        if not title:
            continue
        if raw.get("start_ms") is not None:
            start = int(raw["start_ms"])
        chapters.append(Chapter(title=title, start_ms=start))
        if raw.get("duration_ms") is not None:
            start += int(raw["duration_ms"])
    return tuple(chapters)


def product_from_payload(data: dict, source_url: str) -> Product:
    title = str(data.get("title") or "").strip()
    if not title:
        raise ScrapeError("Local course JSON is missing a title")
    volumes: list[Volume] = []
    for index, raw in enumerate(data.get("volumes") or [], start=1):
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("name") or f"Volume {index}").strip() or f"Volume {index}"
        chapters = chapters_from_entries(list(raw.get("chapters") or []))
        if not chapters:
            continue
        volumes.append(Volume(name=name, chapters=chapters))
    if not volumes:
        raise ScrapeError("Local course JSON has no volumes")
    premiered = _parse_premiered(data.get("premiered"))
    unique_ids = {}
    for key, value in dict(data.get("unique_ids") or {}).items():
        if value:
            unique_ids[str(key)] = str(value)
    tags = [str(tag) for tag in (data.get("tags") or ["Instructional"]) if str(tag).strip()]
    return Product(
        title=title,
        instructor=str(data.get("instructor") or "").strip(),
        plot=str(data.get("plot") or "").strip(),
        premiered=premiered,
        year=premiered.year if premiered else None,
        tags=tags or ["Instructional"],
        unique_ids=unique_ids,
        images=[],
        volumes=volumes,
        studio=str(data.get("studio") or "BJJ Fanatics").strip() or "BJJ Fanatics",
        source_url=str(data.get("source_url") or source_url).strip() or source_url,
    )


class LocalCourseScraper:
    def can_handle(self, url: str) -> bool:
        parsed = urlparse(url)
        if parsed.scheme not in {"file", ""}:
            return False
        suffix = Path(unquote(parsed.path)).suffix.lower()
        return suffix in {".json", ".pdf"}

    def fetch(self, url: str, user_agent: str | None = None) -> Product:
        del user_agent
        path = file_url_to_path(url)
        if not path.is_file() and path.suffix.lower() != ".json":
            raise ScrapeError(f"Local course file not found: {path}")
        json_path = _course_json_path(path)
        try:
            data = json.loads(json_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ScrapeError(f"Could not read course JSON {json_path}: {exc}") from exc
        if not isinstance(data, dict):
            raise ScrapeError(f"Course JSON {json_path} must be an object")
        return product_from_payload(data, url)
