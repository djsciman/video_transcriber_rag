"""One command that sequences match, organize, detect, and transcribe."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Callable, Sequence, TextIO

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
for path in (SCRIPT_DIR, REPO_ROOT):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from match_bjjfanatics import collect_folders  # noqa: E402

DEFAULT_STAGES = ("match", "organize", "detect", "transcribe")
STAGE_CHOICES = ("match", "organize", "detect", "transcribe", "embed")

MatchFn = Callable[[Path], str]
OrganizeFn = Callable[..., int]
DetectFn = Callable[..., int]
TranscribeFn = Callable[..., int]
ChapterCountFn = Callable[[Path], int]


def _print(stdout: TextIO, status: str, stage: str, name: str, reason: str = "") -> None:
    line = f"{status:<4}  {stage:<10}  {name}"
    if reason:
        line += f"  ({reason})"
    stdout.write(line + "\n")


def _default_match(folder: Path) -> str:
    from bjj_organizer.fanatics_search import lookup_candidates

    hits = lookup_candidates(folder.name)
    return hits[0].url if hits else ""


def _default_organize(folder: Path, url: str | None, *, apply: bool) -> int:
    from bjj_organizer.errors import OrganizerError
    from bjj_organizer.pipeline import RuntimeOptions, run

    try:
        return run(folder, [url] if url else [], RuntimeOptions(apply=apply))
    except OrganizerError:
        return 1


def _default_detect(video: Path, *, force: bool, apply: bool) -> int:
    import generate_chapters

    return generate_chapters.run(video, force=force, apply=apply)


def _default_transcribe(video: Path, output: Path, *, force: bool) -> int:
    import batch_panoscribe

    result = batch_panoscribe.process_volume(
        video,
        output,
        ocr=False,
        force=force,
        speech_command=batch_panoscribe.default_speech_command,
        chapter_command=batch_panoscribe.extract_chapters,
        count_hotword_tokens=batch_panoscribe.default_count_hotword_tokens,
    )
    return 0 if result in {"created", "updated", "unchanged"} else 1


def _default_chapter_count(video: Path) -> int:
    from bjj_organizer.chapters import probe_chapter_count

    return probe_chapter_count(video, "ffprobe")


def _chapter_sidecar(video: Path) -> Path:
    import generate_chapters

    return generate_chapters.output_path(video)


def _uncombined_parents(videos: Sequence[Path], counts: dict[Path, int]) -> set[Path]:
    from completeness_scan import is_combined_volume

    grouped: dict[Path, list[Path]] = {}
    for video in videos:
        grouped.setdefault(video.parent, []).append(video)
    skipped: set[Path] = set()
    for parent, group in grouped.items():
        if len(group) < 2:
            continue
        if any(
            is_combined_volume(video, [{}] * max(counts.get(video, 0), 0))
            for video in group
        ):
            continue
        skipped.add(parent)
    return skipped


def _load_csv(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    found: dict[str, str] = {}
    try:
        with path.open(encoding="utf-8", newline="") as handle:
            for row in csv.DictReader(handle):
                folder = (row.get("folder_path") or "").strip()
                url = (row.get("product_url") or "").strip()
                if not folder:
                    continue
                try:
                    key = str(Path(folder).resolve())
                except OSError:
                    key = folder
                found[key] = url
    except OSError:
        return {}
    return found


def _write_csv(path: Path, rows: dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["folder_path", "product_url"])
        writer.writeheader()
        for folder_path, url in rows.items():
            writer.writerow({"folder_path": folder_path, "product_url": url})


def _csv_url(rows: dict[str, str], folder: Path) -> str:
    try:
        key = str(folder.resolve())
    except OSError:
        key = str(folder)
    return (rows.get(key) or "").strip()


def _forced(stage: str, force: bool, force_stage: str | None) -> bool:
    return force or force_stage == stage


def _selected_stages(stages: Sequence[str] | None, embed: bool) -> list[str]:
    chosen = list(stages) if stages is not None else list(DEFAULT_STAGES)
    if embed and "embed" not in chosen:
        chosen.append("embed")
    return chosen


def _organize_done(folder: Path) -> bool:
    from bjj_organizer.naming import season_folder_number

    if not (folder / "tvshow.nfo").is_file():
        return False
    try:
        children = folder.iterdir()
    except OSError:
        return False
    return any(child.is_dir() and season_folder_number(child.name) is not None for child in children)


def _walk_volumes(folder: Path) -> list[Path]:
    import batch_panoscribe

    return batch_panoscribe.walk_videos(folder)


def _transcript_done(output: Path) -> bool:
    import batch_panoscribe

    try:
        _data, info = batch_panoscribe.inspect_transcript(output)
    except batch_panoscribe.TranscriptError:
        return False
    return bool(info["segments_present"])


def _stream_isatty(stdin, isatty: bool | None) -> bool:
    if isatty is not None:
        return isatty
    check = getattr(stdin, "isatty", None)
    return bool(check()) if callable(check) else False


def run(
    library: Path,
    corpus: Path,
    *,
    matches: Path | None = None,
    apply: bool = False,
    force: bool = False,
    force_stage: str | None = None,
    embed: bool = False,
    stages: Sequence[str] | None = None,
    match: MatchFn | None = None,
    organize: OrganizeFn | None = None,
    detect: DetectFn | None = None,
    transcribe: TranscribeFn | None = None,
    chapter_count: ChapterCountFn | None = None,
    stdin=None,
    stdout: TextIO | None = None,
    isatty: bool | None = None,
) -> int:
    library = Path(library)
    corpus = Path(corpus)
    matches_path = Path(matches) if matches is not None else library / "bjjfanatics_matches.csv"
    stdout = stdout if stdout is not None else sys.stdout
    stdin = stdin if stdin is not None else sys.stdin
    tty = _stream_isatty(stdin, isatty)
    match_fn = match or _default_match
    organize_fn = organize or _default_organize
    detect_fn = detect or _default_detect
    transcribe_fn = transcribe or _default_transcribe
    chapter_count_fn = chapter_count or _default_chapter_count
    selected = _selected_stages(stages, embed)
    csv_rows = _load_csv(matches_path)
    failed = False

    folders = [folder for folder, _name in collect_folders(library, include_subfolders=False)]
    for folder in folders:
        key = str(folder.resolve())
        url = _csv_url(csv_rows, folder)

        if "match" in selected:
            has_url = bool(url)
            redo = _forced("match", force, force_stage)
            if has_url and not redo:
                _print(stdout, "SKIP", "match", folder.name)
            elif not apply:
                _print(stdout, "RUN", "match", folder.name)
            else:
                try:
                    found = (match_fn(folder) or "").strip()
                except Exception as exc:  # noqa: BLE001
                    _print(stdout, "FAIL", "match", folder.name, str(exc))
                    failed = True
                else:
                    url = found
                    csv_rows[key] = found
                    _write_csv(matches_path, csv_rows)
                    _print(stdout, "RUN", "match", folder.name)

        if "organize" in selected:
            redo = _forced("organize", force, force_stage)
            done = _organize_done(folder)
            if done and not redo:
                _print(stdout, "SKIP", "organize", folder.name)
            elif not url and not tty and (apply or "match" not in selected):
                _print(stdout, "FAIL", "organize", folder.name, "no product URL")
                failed = True
            elif not url and not apply:
                _print(stdout, "RUN", "organize", folder.name)
            else:
                try:
                    code = organize_fn(folder, url or None, apply=apply)
                except Exception as exc:  # noqa: BLE001
                    _print(stdout, "FAIL", "organize", folder.name, str(exc))
                    failed = True
                else:
                    if code:
                        _print(stdout, "FAIL", "organize", folder.name)
                        failed = True
                    else:
                        _print(stdout, "RUN", "organize", folder.name)

        if "detect" in selected:
            redo = _forced("detect", force, force_stage)
            videos = _walk_volumes(folder)
            counts: dict[Path, int] = {}
            for video in videos:
                try:
                    counts[video] = int(chapter_count_fn(video))
                except Exception as exc:  # noqa: BLE001
                    _print(stdout, "FAIL", "detect", _rel(library, video), str(exc))
                    failed = True
            uncombined = (
                set()
                if force_stage == "detect"
                else _uncombined_parents(videos, counts)
            )
            warned: set[Path] = set()
            for video in videos:
                if video not in counts:
                    continue
                label = _rel(library, video)
                parent = video.parent
                if parent in uncombined:
                    if parent not in warned:
                        stdout.write(
                            f"WARN  detect      {_rel(library, parent)}  "
                            "(uncombined chapter files)\n"
                        )
                        warned.add(parent)
                    _print(stdout, "SKIP", "detect", label, "uncombined chapter files")
                    continue
                if counts[video] > 0:
                    _print(stdout, "SKIP", "detect", label, "container chapters")
                    continue
                if _chapter_sidecar(video).is_file() and not redo:
                    _print(stdout, "SKIP", "detect", label, "sidecar exists")
                    continue
                if not apply:
                    _print(stdout, "RUN", "detect", label)
                    continue
                try:
                    code = detect_fn(video, force=redo, apply=False)
                except Exception as exc:  # noqa: BLE001
                    _print(stdout, "FAIL", "detect", label, str(exc))
                    failed = True
                else:
                    if code:
                        _print(stdout, "FAIL", "detect", label)
                        failed = True
                    else:
                        _print(stdout, "RUN", "detect", label)

        if "transcribe" in selected:
            redo = _forced("transcribe", force, force_stage)
            for video in _walk_volumes(folder):
                output = _transcript_path(library, corpus, video)
                done = _transcript_done(output)
                label = _rel(library, video)
                if done and not redo:
                    _print(stdout, "SKIP", "transcribe", label)
                    continue
                if not apply:
                    _print(stdout, "RUN", "transcribe", label)
                    continue
                try:
                    code = transcribe_fn(video, output, force=redo)
                except Exception as exc:  # noqa: BLE001
                    _print(stdout, "FAIL", "transcribe", label, str(exc))
                    failed = True
                else:
                    if code:
                        _print(stdout, "FAIL", "transcribe", label)
                        failed = True
                    else:
                        _print(stdout, "RUN", "transcribe", label)

        if "embed" in selected:
            redo = _forced("embed", force, force_stage)
            if not apply:
                for video in _walk_volumes(folder):
                    _print(stdout, "RUN", "embed", _rel(library, video))
                continue
            for video in _walk_volumes(folder):
                try:
                    code = detect_fn(video, force=redo, apply=True)
                except Exception as exc:  # noqa: BLE001
                    _print(stdout, "FAIL", "embed", _rel(library, video), str(exc))
                    failed = True
                else:
                    if code:
                        _print(stdout, "FAIL", "embed", _rel(library, video))
                        failed = True
                    else:
                        _print(stdout, "RUN", "embed", _rel(library, video))

    return 1 if failed else 0


def _rel(library: Path, path: Path) -> str:
    try:
        return str(path.relative_to(library))
    except ValueError:
        return str(path)


def _transcript_path(library: Path, corpus: Path, video: Path) -> Path:
    import batch_panoscribe

    return batch_panoscribe.output_path_for(video, library, corpus)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Match, organize, detect, and transcribe a library of instructionals."
    )
    parser.add_argument("--library", type=Path, required=True, help="Root of instructional folders.")
    parser.add_argument("--corpus", type=Path, required=True, help="Root for transcript JSON.")
    parser.add_argument(
        "--matches",
        type=Path,
        default=None,
        help="Match CSV path (default: LIBRARY/bjjfanatics_matches.csv).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write match, organize, detect sidecars, and transcribe. Default is a dry run.",
    )
    parser.add_argument("--force", action="store_true", help="Re-run every selected stage.")
    parser.add_argument(
        "--force-stage",
        choices=STAGE_CHOICES,
        default=None,
        help="Re-run only this stage.",
    )
    parser.add_argument(
        "--embed",
        action="store_true",
        help="Embed sidecar chapter files into volumes. Apply does not imply embed.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return run(
        args.library,
        args.corpus,
        matches=args.matches,
        apply=args.apply,
        force=args.force,
        force_stage=args.force_stage,
        embed=args.embed,
    )


if __name__ == "__main__":
    sys.exit(main())
