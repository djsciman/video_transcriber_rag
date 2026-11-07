"""Detect skip and force through sidecars, without opening a volume."""

from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import generate_chapters


def _write_video(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"fake-video")
    return path


SIDECAR = "Chapter,StartTimestamp,EndTimestamp\nChapter 1,00:00:00.000,00:01:00.000\n"


def _write_times_sidecar(video: Path, body: str = SIDECAR) -> Path:
    path = generate_chapters.output_path(video)
    path.write_text(body, encoding="utf-8")
    return path


def _detect_recorder(calls: list, *, status: int = 0, body: str = "scanned"):
    def detect(video: Path, chapter_file: Path) -> int:
        calls.append({"video": video.name, "chapter_file": chapter_file.name})
        chapter_file.write_text(body, encoding="utf-8")
        return status

    return detect


class DetectLibraryEntryTest(unittest.TestCase):
    def test_main_returns_0_when_times_sidecar_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            video = _write_video(Path(tmp) / "Vol1.mp4")
            sidecar = _write_times_sidecar(video)
            before = sidecar.read_text(encoding="utf-8")
            buf = io.StringIO()
            with redirect_stdout(buf):
                status = generate_chapters.main([str(video)])
            self.assertEqual(status, 0)
            self.assertEqual(sidecar.read_text(encoding="utf-8"), before)
            self.assertIn("using existing", buf.getvalue())


class DetectSkipTest(unittest.TestCase):
    def test_existing_times_sidecar_skips_scan_unless_force(self):
        with tempfile.TemporaryDirectory() as tmp:
            video = _write_video(Path(tmp) / "Vol1.mp4")
            sidecar = _write_times_sidecar(video)
            before = sidecar.read_text(encoding="utf-8")
            calls: list = []
            buf = io.StringIO()
            with redirect_stdout(buf):
                status = generate_chapters.run(
                    video,
                    detect_command=_detect_recorder(calls),
                )
            self.assertEqual(status, 0)
            self.assertEqual(calls, [])
            self.assertEqual(sidecar.read_text(encoding="utf-8"), before)
            self.assertIn(str(sidecar), buf.getvalue())

    def test_missing_times_sidecar_scans(self):
        with tempfile.TemporaryDirectory() as tmp:
            video = _write_video(Path(tmp) / "Vol1.mp4")
            sidecar = generate_chapters.output_path(video)
            calls: list = []
            status = generate_chapters.run(
                video,
                detect_command=_detect_recorder(calls, body="scanned"),
            )
            self.assertEqual(status, 0)
            self.assertEqual(calls, [{"video": "Vol1.mp4", "chapter_file": sidecar.name}])
            self.assertEqual(sidecar.read_text(encoding="utf-8"), "scanned")

    def test_force_scans_when_times_sidecar_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            video = _write_video(Path(tmp) / "Vol1.mp4")
            sidecar = _write_times_sidecar(video)
            calls: list = []
            status = generate_chapters.run(
                video,
                force=True,
                detect_command=_detect_recorder(calls, body="forced"),
            )
            self.assertEqual(status, 0)
            self.assertEqual(len(calls), 1)
            self.assertEqual(sidecar.read_text(encoding="utf-8"), "forced")

    def test_scan_failure_returns_status_instead_of_exiting(self):
        with tempfile.TemporaryDirectory() as tmp:
            video = _write_video(Path(tmp) / "Vol1.mp4")
            status = generate_chapters.run(
                video,
                detect_command=_detect_recorder([], status=1),
            )
            self.assertEqual(status, 1)


class DetectCliOptionsTest(unittest.TestCase):
    def test_force_flag_is_present(self):
        parser = generate_chapters.build_parser()
        forced = parser.parse_args(["Vol1.mp4", "--force"])
        applied = parser.parse_args(["Vol1.mp4", "--apply"])
        self.assertTrue(forced.force)
        self.assertTrue(applied.apply)


if __name__ == "__main__":
    unittest.main()
