"""Completeness scan behavior through temporary trees and stand-in probes."""

from __future__ import annotations

import io
import tempfile
import unittest
import unittest.mock
from contextlib import redirect_stdout
from datetime import datetime
from pathlib import Path

import completeness_scan
from completeness_scan import VideoInspection


def _write_video(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    completeness_scan.io_path(path).write_bytes(b"fake-video")
    return path


def _write_text(path: Path, text: str = "x") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    completeness_scan.io_path(path).write_text(text, encoding="utf-8")
    return path


def _named_chapters() -> list[dict]:
    return [
        {"title": "Introduction", "start": 0.0, "end": 10.0},
        {"title": "Arm Bar", "start": 10.0, "end": 20.0},
    ]


def _inspect(
    chapters: list[dict] | None = None,
    *,
    open_ok: bool = True,
    open_error: str = "",
    duration: float = 60.0,
    decode_ok: bool = True,
    decode_error: str = "",
) -> VideoInspection:
    return VideoInspection(
        open_ok=open_ok,
        open_error=open_error,
        duration=duration,
        chapters=list(chapters or []),
        decode_ok=decode_ok,
        decode_error=decode_error,
    )


def _by_name(mapping: dict[str, VideoInspection]):
    def inspect(path: Path) -> VideoInspection:
        if path.name in mapping:
            return mapping[path.name]
        for key, value in mapping.items():
            if path.as_posix().endswith(key):
                return value
        return _inspect(chapters=_named_chapters())

    return inspect


class CombinedVolumeTests(unittest.TestCase):
    def test_fanatics_segment_is_split(self):
        path = Path("4533018132578-01-01- Introduction.mp4")
        self.assertFalse(completeness_scan.is_combined_volume(path, []))
        self.assertIn("segmented", completeness_scan.split_reason(path, []))

    def test_named_segment_is_split(self):
        path = Path("01.02 - Collar And Sleeve.mp4")
        self.assertFalse(completeness_scan.is_combined_volume(path, []))

    def test_volume_part_is_uncombined(self):
        path = Path("VOL1PT1 - Stance - Feet to Floor.mp4")
        self.assertFalse(completeness_scan.is_combined_volume(path, []))
        self.assertIn("part", completeness_scan.split_reason(path, []))

    def test_jellyfin_volume_title_is_combined_without_chapters(self):
        path = Path("Show by Coach - S01E01 - Volume 1.mp4")
        self.assertTrue(completeness_scan.is_combined_volume(path, []))

    def test_jellyfin_chapter_title_without_markers_is_split(self):
        path = Path("Feet To Floor - S01E01 - Stance.mp4")
        self.assertFalse(completeness_scan.is_combined_volume(path, []))

    def test_jellyfin_chapter_title_with_markers_is_combined(self):
        path = Path("Triangles - S01E01 - Triangles.mp4")
        self.assertTrue(completeness_scan.is_combined_volume(path, _named_chapters()))

    def test_trailing_disc_file_is_combined(self):
        path = Path("FinishingleglocksbyJacobCouch1.mp4")
        self.assertTrue(completeness_scan.is_combined_volume(path, []))


class NamedChapterTests(unittest.TestCase):
    def test_two_named_titles_pass(self):
        self.assertTrue(completeness_scan.has_named_chapters(_named_chapters()))

    def test_generic_titles_fail(self):
        chapters = [
            {"title": "Chapter 1", "start": 0.0, "end": 10.0},
            {"title": "Chapter 2", "start": 10.0, "end": 20.0},
        ]
        self.assertFalse(completeness_scan.has_named_chapters(chapters))

    def test_single_chapter_fails(self):
        chapters = [{"title": "Stance", "start": 0.0, "end": 600.0}]
        self.assertFalse(completeness_scan.has_named_chapters(chapters))

    def test_empty_fails(self):
        self.assertFalse(completeness_scan.has_named_chapters([]))


class ScanTreeTests(unittest.TestCase):
    def test_aggregate_and_markdown_list_gaps(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            library = root / "videos"
            transcripts = root / "json"
            clock = lambda: datetime(2026, 11, 4, 15, 30, 45)

            combined = (
                library
                / "Inside Passing by Wardzinski"
                / "Season 01"
                / "Inside Passing by Wardzinski - S01E01 - Volume 1.mp4"
            )
            split = library / "Collar Sleeve" / "01.02 - Collar And Sleeve.mp4"
            broken = library / "Broken Show" / "broken.mp4"
            _write_video(combined)
            _write_video(split)
            _write_video(broken)
            _write_text(combined.with_suffix(".nfo"), "<episodedetails/>")
            _write_text(
                library / "Inside Passing by Wardzinski" / "tvshow.nfo",
                "<tvshow/>",
            )
            _write_text(
                transcripts
                / "Inside Passing by Wardzinski"
                / "Season 01"
                / "Inside Passing by Wardzinski - S01E01 - Volume 1.json",
                "{}",
            )

            inspect = _by_name(
                {
                    combined.name: _inspect(chapters=_named_chapters()),
                    split.name: _inspect(chapters=[]),
                    broken.name: _inspect(
                        chapters=[],
                        open_ok=False,
                        open_error="Invalid data found",
                        decode_ok=False,
                        decode_error="decode skipped",
                    ),
                }
            )
            dest = root / "report.md"
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                status = completeness_scan.run(
                    library,
                    transcripts,
                    output=dest,
                    inspect_video=inspect,
                    clock=clock,
                    require_tools=False,
                )
            self.assertEqual(status, 0)
            out = stdout.getvalue()
            self.assertIn("Videos combined into volumes", out)
            self.assertIn("2/3 (66.7%)", out)
            self.assertIn("Videos with named chapters: 1/3 (33.3%)", out)
            self.assertIn("Videos with NFO metadata: 1/3 (33.3%)", out)
            self.assertIn("Instructionals with NFO metadata: 1/3 (33.3%)", out)
            self.assertIn(
                "Videos that play without errors: 2/3 (66.7%)",
                out,
            )
            self.assertIn(
                "Videos with corresponding transcripts: 1/3 (33.3%)",
                out,
            )
            self.assertTrue(dest.is_file())
            md = dest.read_text(encoding="utf-8")
            self.assertIn("# Completeness scan", md)
            self.assertIn("## Videos split by chapters (not combined)", md)
            self.assertIn("01.02 - Collar And Sleeve.mp4", md)
            self.assertIn("## Videos without named chapters", md)
            self.assertIn("broken.mp4", md)
            self.assertIn("Invalid data found", md)
            self.assertIn("## Videos without NFO metadata", md)
            self.assertIn("## Instructionals without NFO metadata", md)
            self.assertIn("`Collar Sleeve`", md)
            self.assertIn("`Broken Show`", md)
            self.assertIn("no tvshow.nfo", md)
            self.assertIn("| Videos that play without errors | 2 | 3 | 66.7% |", md)
            self.assertIn("| Videos with corresponding transcripts | 1 | 3 | 33.3% |", md)
            self.assertIn("## Videos that do not play or open with errors", md)
            self.assertIn("## Videos without corresponding transcripts", md)
            self.assertNotIn("Inside Passing by Wardzinski - S01E01 - Volume 1.mp4", md.split("## Videos split by chapters")[1].split("## ")[0])

    def test_default_output_name_uses_clock(self):
        when = datetime(2026, 11, 4, 15, 30, 45)
        path = completeness_scan.default_output_path(when, Path("C:/repo"))
        self.assertEqual(path.name, "completeness_scan_results_2026-11-04_153045.md")

    def test_empty_library_is_zero_totals(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            library = root / "videos"
            transcripts = root / "json"
            library.mkdir()
            transcripts.mkdir()
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                status = completeness_scan.run(
                    library,
                    transcripts,
                    output=root / "out.md",
                    inspect_video=lambda path: _inspect(),
                    require_tools=False,
                )
            self.assertEqual(status, 0)
            self.assertIn("Videos: 0", stdout.getvalue())
            md = (root / "out.md").read_text(encoding="utf-8")
            self.assertIn("| Videos with named chapters | 0 | 0 | n/a |", md)

    def test_missing_library_exits_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            stdout = io.StringIO()
            stderr = io.StringIO()
            with redirect_stdout(stdout), unittest.mock.patch("sys.stderr", stderr):
                status = completeness_scan.run(
                    root / "missing",
                    root,
                    inspect_video=lambda path: _inspect(),
                    require_tools=False,
                )
            self.assertEqual(status, 1)
            self.assertIn("is not a directory", stderr.getvalue())

    def test_probe_payload_reads_named_chapters(self):
        payload = {
            "chapters": [
                {
                    "start_time": "0.000",
                    "end_time": "10.000",
                    "tags": {"title": "Introduction"},
                },
                {
                    "start_time": "10.000",
                    "end_time": "20.000",
                    "tags": {"title": "Arm Bar"},
                },
            ]
        }
        chapters = completeness_scan._chapters_from_payload(payload)
        self.assertTrue(completeness_scan.has_named_chapters(chapters))
        self.assertEqual(chapters[1]["title"], "Arm Bar")


if __name__ == "__main__":
    unittest.main()
