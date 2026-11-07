from __future__ import annotations

from pathlib import Path

from .errors import ScrapeError
from .httputil import DEFAULT_USER_AGENT, fetch_bytes
from .models import Product, ProductImage
from .scrape.bjj_fanatics import pick_fanart, pick_poster


def _extension(content_type: str, url: str) -> str:
    lowered = content_type.lower()
    if "png" in lowered:
        return ".png"
    if "webp" in lowered:
        return ".webp"
    if "jpeg" in lowered or "jpg" in lowered:
        return ".jpg"
    path = url.split("?", 1)[0].lower()
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        if path.endswith(ext):
            return ".jpg" if ext == ".jpeg" else ext
    return ".jpg"


def download_image(url: str, dest: Path, user_agent: str = DEFAULT_USER_AGENT) -> Path:
    data, content_type = fetch_bytes(url, user_agent=user_agent)
    if len(data) < 100:
        raise ScrapeError(f"Image from {url} is empty")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    return dest


def write_posters(
    folder: Path,
    image: ProductImage,
    user_agent: str = DEFAULT_USER_AGENT,
    also_folder_jpg: bool = True,
) -> list[Path]:
    written: list[Path] = []
    poster = folder / "poster.jpg"
    download_image(image.url, poster, user_agent=user_agent)
    written.append(poster)
    if also_folder_jpg:
        folder_jpg = folder / "folder.jpg"
        folder_jpg.write_bytes(poster.read_bytes())
        written.append(folder_jpg)
    return written


def product_poster(product: Product) -> ProductImage | None:
    return pick_poster(product.images)


def product_fanart(product: Product) -> ProductImage | None:
    return pick_fanart(product.images, pick_poster(product.images))
