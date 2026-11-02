from __future__ import annotations

import sys
from dataclasses import dataclass, field

from .artwork import product_fanart, product_poster
from .chapters import chapters_have_timeline, probe_chapter_count
from .layout import child_dirs, dir_has_videos, list_videos
from .match import flatten_chapters
from .models import ShowPlan
from .naming import season_folder_number
from .pipeline import RuntimeOptions

FIX_LABELS = {
    "B": "Write or refresh show tvshow.nfo, poster, folder.jpg, and fanart",
    "C": "Create Season ## folders, season.nfo, and season posters, and move that season's videos there",
    "D": "Combine chapter clips into one file per volume",
    "E": "Write chapter markers into volume files that have timestamps",
    "F": "Rename episodes to the Jellyfin filename and write each episode .nfo",
    "G": "Move unmatched leftovers into extras/",
}


@dataclass
class CheckItem:
    label: str
    done: bool
    detail: str = ""
    letter: str | None = None


@dataclass
class FolderCheck:
    heading: str
    items: list[CheckItem] = field(default_factory=list)


@dataclass
class RepairReport:
    folders: list[FolderCheck]

    def needed_letters(self) -> list[str]:
        found: list[str] = []
        for folder in self.folders:
            for item in folder.items:
                if item.done or not item.letter or item.letter in found:
                    continue
                found.append(item.letter)
        return sorted(found)


def _box(item: CheckItem) -> str:
    mark = "x" if item.done else " "
    detail = f" ({item.detail})" if item.detail else ""
    return f"  [{mark}] {item.label}{detail}"


def format_report(report: RepairReport) -> str:
    lines: list[str] = []
    for index, folder in enumerate(report.folders):
        if index:
            lines.append("")
        lines.append(folder.heading)
        indent = "" if folder.heading.startswith("Show:") else "  "
        for item in folder.items:
            lines.append(indent + _box(item))
    return "\n".join(lines).rstrip() + "\n"


def format_fixes(letters: list[str]) -> str:
    lines = ["", "Fixes:"]
    for letter in letters:
        lines.append(f"  {letter}. {FIX_LABELS[letter]}")
    lines.append("")
    lines.append("Apply all, or list letters (A, C): ")
    return "\n".join(lines)


def parse_repair_answer(text: str, available: list[str]) -> set[str] | None:
    raw = text.strip().lower()
    if not raw:
        return None
    allowed = set(available)
    if raw == "all":
        return set(allowed)
    letters = [part.strip().upper() for part in raw.split(",") if part.strip()]
    if not letters or any(len(letter) != 1 or letter not in allowed for letter in letters):
        return None
    return set(letters)


def prompt_repair_steps(available: list[str], stdin, stderr) -> set[str]:
    while True:
        stderr.write("Apply all, or list letters (A, C): ")
        stderr.flush()
        line = stdin.readline()
        if not line:
            return set()
        chosen = parse_repair_answer(line, available)
        if chosen is not None:
            return chosen
        stderr.write("Reply all, or letters such as A, C.\n")


def _file_ok(folder, name: str) -> bool:
    return (folder / name).is_file()


def _poster_expected(plan: ShowPlan, *, show: bool) -> bool:
    if show and plan.show_product and product_poster(plan.show_product):
        return True
    if show and any(product_poster(season.product) for season in plan.seasons):
        return True
    return False


def _fanart_expected(plan: ShowPlan) -> bool:
    if plan.show_product and product_fanart(plan.show_product):
        return True
    return any(product_fanart(season.product) for season in plan.seasons)


def _chapter_marks_present(path) -> bool:
    try:
        return probe_chapter_count(path, "ffprobe") > 0
    except Exception:
        return False


def assess(plan: ShowPlan, options: RuntimeOptions) -> RepairReport:
    show_dir = plan.source_dir
    show_items: list[CheckItem] = []
    show_items.append(CheckItem("tvshow.nfo", _file_ok(show_dir, "tvshow.nfo"), letter="B"))
    poster_expected = _poster_expected(plan, show=True)
    show_items.append(
        CheckItem(
            "poster.jpg",
            (not poster_expected) or _file_ok(show_dir, "poster.jpg"),
            "" if poster_expected else "no poster on the product page",
            letter="B" if poster_expected else None,
        )
    )
    show_items.append(
        CheckItem(
            "folder.jpg",
            (not poster_expected) or _file_ok(show_dir, "folder.jpg"),
            "" if poster_expected else "no poster on the product page",
            letter="B" if poster_expected else None,
        )
    )
    fanart_expected = _fanart_expected(plan)
    show_items.append(
        CheckItem(
            "fanart.jpg",
            (not fanart_expected) or _file_ok(show_dir, "fanart.jpg"),
            "" if fanart_expected else "no wide image on the product page",
            letter="B" if fanart_expected else None,
        )
    )
    show_items.append(
        CheckItem(
            "show folder name",
            show_dir.name == plan.dest_name,
            "" if show_dir.name == plan.dest_name else plan.dest_name,
            letter="B",
        )
    )
    season_dirs_ready = all(
        (show_dir / season.dest_name).is_dir() and season_folder_number(season.dest_name) is not None
        for season in plan.seasons
    )
    show_items.append(
        CheckItem(
            "seasons named Season 01, Season 02, ...",
            season_dirs_ready,
            letter="C",
        )
    )
    folders = [FolderCheck(f"Show: {plan.title}", show_items)]

    for season in plan.seasons:
        dest_dir = show_dir / season.dest_name
        items: list[CheckItem] = []
        if season.match_error:
            items.append(CheckItem("course match", False, season.match_error))
            folders.append(FolderCheck(season.source_dir.name, items))
            continue
        season_ready = dest_dir.is_dir() and season_folder_number(season.dest_name) is not None
        items.append(CheckItem("Season ## folder", season_ready, season.dest_name, letter="C"))
        items.append(CheckItem("season.nfo", _file_ok(dest_dir, "season.nfo"), letter="C"))
        season_poster = product_poster(season.product) is not None
        items.append(
            CheckItem(
                "poster.jpg",
                (not season_poster) or _file_ok(dest_dir, "poster.jpg"),
                "" if season_poster else "no poster on the product page",
                letter="C" if season_poster else None,
            )
        )

        multi = [ep for ep in season.episodes if len(ep.concat_sources) > 1]
        if not multi or not options.combine_volumes:
            items.append(CheckItem("chapter clips combined into volumes", True, "one file per volume", letter="D"))
        else:
            loose = 0
            for episode in multi:
                dest = dest_dir / episode.dest_name
                if not dest.is_file():
                    loose += len(episode.concat_sources)
                    continue
                for source in episode.concat_sources:
                    if source.exists() and source.resolve() != dest.resolve():
                        loose += 1
            items.append(
                CheckItem(
                    "chapter clips combined into volumes",
                    loose == 0,
                    "" if loose == 0 else f"{loose} clips still separate",
                    letter="D",
                )
            )

        if season.keep_dest:
            items.append(
                CheckItem(
                    "chapter markers on each volume",
                    True,
                    "already written in the volume file",
                    letter="E",
                )
            )
            timed = []
        else:
            timed = [
                ep
                for ep in season.episodes
                if options.combine_volumes
                and chapters_have_timeline(ep.chapters)
                and not options.skip_chapters
            ]
        if not timed:
            items.append(
                CheckItem(
                    "chapter markers on each volume",
                    True,
                    "chapter markers skipped" if options.skip_chapters else "no timestamps on the course page",
                    letter="E",
                )
            )
        else:
            marked = 0
            for episode in timed:
                dest = dest_dir / episode.dest_name
                if dest.is_file() and _chapter_marks_present(dest):
                    marked += 1
            items.append(
                CheckItem(
                    "chapter markers on each volume",
                    marked == len(timed),
                    "" if marked == len(timed) else f"{marked} of {len(timed)}",
                    letter="E",
                )
            )

        if season.keep_dest:
            items.append(
                CheckItem(
                    "course chapters present",
                    True,
                    season.warnings[0] if season.warnings else "already combined",
                )
            )
        else:
            expected = len(flatten_chapters(season.product.volumes))
            present = (
                sum(len(ep.chapters) for ep in season.episodes)
                if options.combine_volumes
                else len(season.episodes)
            )
            items.append(
                CheckItem(
                    "course chapters present",
                    expected == 0 or present >= expected,
                    f"{present} of {expected}",
                )
            )

        named = 0
        nfos = 0
        total = len(season.episodes)
        for episode in season.episodes:
            dest = dest_dir / episode.dest_name
            if dest.is_file():
                named += 1
            if dest.with_suffix(".nfo").is_file():
                nfos += 1
        items.append(
            CheckItem(
                "episode filenames",
                total == 0 or named == total,
                f"{named} of {total}",
                letter="F",
            )
        )
        items.append(
            CheckItem(
                "episode NFOs",
                total == 0 or nfos == total,
                f"{nfos} of {total}",
                letter="F",
            )
        )

        if not season.extras:
            items.append(CheckItem("leftovers moved to extras/", True, "none", letter="G"))
        else:
            still = [extra for extra in season.extras if extra.exists()]
            items.append(
                CheckItem(
                    "leftovers moved to extras/",
                    not still,
                    "none" if not still else f"{len(still)} still outside extras/",
                    letter="G",
                )
            )
        folders.append(FolderCheck(season.source_dir.name, items))
    return RepairReport(folders)


def format_local_checklist(folder) -> str:
    """Disk-only checklist used when the course page could not be matched."""
    lines = [f"Show: {folder.name}"]
    for name in ("tvshow.nfo", "poster.jpg", "folder.jpg", "fanart.jpg"):
        mark = "x" if _file_ok(folder, name) else " "
        lines.append(f"  [{mark}] {name}")
    seasons = [path for path in child_dirs(folder) if dir_has_videos(path)]
    leaf = not seasons and bool(list_videos(folder))
    targets = seasons or ([folder] if leaf else [])
    ready = bool(targets) and all(season_folder_number(path.name) is not None for path in targets) and not leaf
    lines.append(f"  [{'x' if ready else ' '}] seasons named Season 01, Season 02, ...")
    for season in targets:
        lines.append("")
        lines.append(season.name if season != folder else folder.name)
        season_ready = season_folder_number(season.name) is not None and not leaf
        lines.append(f"    [{'x' if season_ready else ' '}] Season ## folder")
        lines.append(f"    [{'x' if _file_ok(season, 'season.nfo') else ' '}] season.nfo")
        lines.append(f"    [{'x' if _file_ok(season, 'poster.jpg') else ' '}] poster.jpg")
        videos = list_videos(season)
        nfos = sum(1 for video in videos if video.with_suffix(".nfo").is_file())
        lines.append(f"    [ ] chapter clips combined into volumes ({len(videos)} video(s) on disk)")
        lines.append("    [ ] chapter markers on each volume (course match failed)")
        lines.append("    [ ] course chapters present (course match failed)")
        lines.append(f"    [ ] episode filenames ({len(videos)} video(s) still under the original names)")
        lines.append(f"    [{'x' if videos and nfos == len(videos) else ' '}] episode NFOs ({nfos} of {len(videos)})")
        lines.append("    [ ] leftovers moved to extras/ (course match failed)")
    lines.append("")
    lines.append("Course match failed. No fixes can run until that succeeds.")
    return "\n".join(lines).rstrip() + "\n"


def run_repair(folder, url_args, options: RuntimeOptions, scrape_product) -> int:
    from .errors import MatchError
    from .pipeline import apply_plan, build_plan

    try:
        plan = build_plan(folder, url_args, options, scrape_product=scrape_product)
    except MatchError as exc:
        sys.stdout.write(format_local_checklist(folder))
        sys.stderr.write(f"error: {exc}\n")
        return exc.exit_code

    report = assess(plan, options)
    sys.stdout.write(format_report(report))
    letters = report.needed_letters()
    if not letters:
        sys.stderr.write("Nothing to repair.\n")
        return 0
    sys.stdout.write(format_fixes(letters))
    chosen = read_repair_choice(options, letters)
    if not chosen:
        return 0
    options.repair_steps = chosen
    apply_plan(plan, options)
    sys.stderr.write("Repair complete.\n")
    return 0


def read_repair_choice(options: RuntimeOptions, available: list[str]) -> set[str]:
    if options.repair_steps is not None:
        if "ALL" in options.repair_steps:
            return set(available)
        unknown = options.repair_steps - set(FIX_LABELS)
        if unknown:
            from .errors import UsageError

            raise UsageError(
                f"Unknown repair step(s): {', '.join(sorted(unknown))}. Use {', '.join(FIX_LABELS)}."
            )
        return set(options.repair_steps)
    stdin = options.stdin if options.stdin is not None else sys.stdin
    stderr = options.stderr if options.stderr is not None else sys.stderr
    if not (hasattr(stdin, "isatty") and stdin.isatty()):
        stderr.write("Pass --repair-steps all or --repair-steps A,C to apply.\n")
        return set()
    return prompt_repair_steps(available, stdin, stderr)
