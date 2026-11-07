from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path


@dataclass(frozen=True)
class Chapter:
    title: str
    start_ms: int


@dataclass(frozen=True)
class Volume:
    name: str
    chapters: tuple[Chapter, ...]


@dataclass(frozen=True)
class ProductImage:
    url: str
    width: int
    height: int
    alt: str
    position: int


@dataclass
class Product:
    title: str
    instructor: str
    plot: str
    premiered: date | None
    year: int | None
    tags: list[str]
    unique_ids: dict[str, str]
    images: list[ProductImage]
    volumes: list[Volume]
    studio: str = "BJJ Fanatics"
    source_url: str = ""

    @property
    def published_at(self) -> datetime | None:
        if self.premiered is None:
            return None
        return datetime(self.premiered.year, self.premiered.month, self.premiered.day)


@dataclass
class ParsedVideo:
    path: Path
    volume_number: int | None
    part_number: int | None
    is_new: bool
    is_extra: bool
    local_title: str | None
    already_named: bool
    extension: str
    chapter_number: int | None = None
    is_segmented_name: bool = False


@dataclass
class ChapterMatch:
    parsed: ParsedVideo
    volume_name: str
    chapter: Chapter
    volume_number: int
    chapter_number: int
    mode: str
    chapter_title: str
    split_start_ms: int | None = None
    split_end_ms: int | None = None
    # Chapter titles from a description list that has no start times.
    toc: tuple[Chapter, ...] = ()


@dataclass
class SeasonMatch:
    mode: str
    items: list[ChapterMatch]
    extras: list[Path]
    warnings: list[str]


@dataclass
class EpisodePlan:
    source: Path
    dest_dir: Path
    dest_name: str
    season: int
    episode: int
    title: str
    chapters: list[Chapter]
    extension: str
    extra: bool = False
    volume_number: int = 1
    chapter_number: int = 1
    chapter_title: str = ""
    volume_name: str = ""
    mode: str = "segmented"
    split_start_ms: int | None = None
    split_end_ms: int | None = None
    concat_sources: list[Path] = field(default_factory=list)


@dataclass
class SeasonPlan:
    source_dir: Path
    source_name: str
    dest_name: str
    number: int
    product: Product
    episodes: list[EpisodePlan] = field(default_factory=list)
    extras: list[Path] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    mode: str = "volume"
    combine_volumes: bool = True
    match_error: str = ""
    keep_dest: bool = False


@dataclass
class ShowPlan:
    source_dir: Path
    dest_name: str
    title: str
    instructors: list[str]
    seasons: list[SeasonPlan]
    year: int | None
    premiered: date | None
    plot: str
    unique_id: str
    warnings: list[str] = field(default_factory=list)
    nested: bool = False
    combine_volumes: bool = True
    show_url: str = ""
    show_product: Product | None = None
