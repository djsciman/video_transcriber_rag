"""Batch program behavior through temporary trees and stand-in commands."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from typing import Callable

import batch_panoscribe


def _write_video(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"fake-video")
    return path


def _read_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _speech_writer(
    segments: list | None = None,
    language: str = "en",
    *,
    fail: bool = False,
    calls: list | None = None,
) -> Callable:
    """Stand-in speech command that writes a speech result or fails."""

    def speech(video_path: Path, aside_path: Path, hotwords: str | None, ocr: bool) -> None:
        if calls is not None:
            calls.append(
                {
                    "video": video_path.name,
                    "aside": aside_path,
                    "hotwords": hotwords,
                    "ocr": ocr,
                }
            )
        if fail:
            raise RuntimeError("speech failed")
        payload = {
            "language": language,
            "segments": segments
            if segments is not None
            else [{"start": 0.0, "end": 1.0, "text": "hello", "source": "SPEECH"}],
        }
        aside_path.parent.mkdir(parents=True, exist_ok=True)
        aside_path.write_text(json.dumps(payload), encoding="utf-8")

    return speech


def _chapter_reader(
    chapters: list | None = None,
    *,
    fail: bool = False,
    calls: list | None = None,
) -> Callable:
    def chapters_cmd(video_path: Path) -> list:
        if calls is not None:
            calls.append(video_path.name)
        if fail:
            raise RuntimeError("chapters failed")
        return list(chapters or [])

    return chapters_cmd


def _run(
    input_dir: Path,
    output_dir: Path,
    *,
    speech=None,
    chapters=None,
    ocr: bool = False,
    speech_available: bool | None = True,
    chapter_available: bool | None = True,
    count_hotword_tokens: Callable[[str], int] | None = None,
) -> tuple[int, str]:
    buf = io.StringIO()
    with redirect_stdout(buf):
        status = batch_panoscribe.run(
            input_dir,
            output_dir,
            ocr=ocr,
            speech_command=speech,
            chapter_command=chapters,
            speech_available=speech_available,
            chapter_available=chapter_available,
            count_hotword_tokens=count_hotword_tokens,
        )
    return status, buf.getvalue()


class EmptyAndBadInputTest(unittest.TestCase):
    def test_empty_folder_exits_0_with_zero_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "in").mkdir()
            status, out = _run(root / "in", root / "out", speech=_speech_writer(), chapters=_chapter_reader())
            self.assertEqual(status, 0)
            self.assertIn("Created: 0", out)
            self.assertIn("Updated: 0", out)
            self.assertIn("Unchanged: 0", out)
            self.assertIn("Failed: 0", out)

    def test_non_directory_exits_1(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            missing = root / "missing"
            status, out = _run(missing, root / "out", speech=_speech_writer(), chapters=_chapter_reader())
            self.assertEqual(status, 1)


class CreateTranscriptTest(unittest.TestCase):
    def test_missing_transcript_gets_speech_chapters_and_video_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video = _write_video(root / "in" / "Vol1.mp4")
            chapters = [{"title": "Intro to the Von Flue", "start": 0.0, "end": 10.0}]
            speech_calls: list = []
            status, out = _run(
                root / "in",
                root / "out",
                speech=_speech_writer(calls=speech_calls),
                chapters=_chapter_reader(chapters),
            )
            self.assertEqual(status, 0)
            dest = root / "out" / "Vol1.json"
            data = _read_json(dest)
            self.assertEqual(data["video_file"], "Vol1.mp4")
            self.assertEqual(data["chapters"], [{"title": "Intro to the Von Flue", "start": 0.0, "end": 10.0}])
            self.assertEqual(data["language"], "en")
            self.assertEqual(len(data["segments"]), 1)
            self.assertIn("Created:", out)
            self.assertRegex(out, r"Created: 1")
            self.assertEqual(speech_calls[0]["hotwords"], "Von Flue")
            self.assertIs(speech_calls[0]["ocr"], False)

    def test_transcript_path_mirrors_instructional_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_video(root / "in" / "Couch" / "Vol1.mp4")
            status, _ = _run(
                root / "in",
                root / "out",
                speech=_speech_writer(),
                chapters=_chapter_reader([{"title": "A", "start": 0.0, "end": 1.0}]),
            )
            self.assertEqual(status, 0)
            self.assertTrue((root / "out" / "Couch" / "Vol1.json").is_file())

    def test_same_file_name_in_different_folders_keep_separate_transcripts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_video(root / "in" / "A" / "Vol.mp4")
            _write_video(root / "in" / "B" / "Vol.mp4")
            status, out = _run(
                root / "in",
                root / "out",
                speech=_speech_writer(),
                chapters=_chapter_reader([]),
            )
            self.assertEqual(status, 0)
            self.assertTrue((root / "out" / "A" / "Vol.json").is_file())
            self.assertTrue((root / "out" / "B" / "Vol.json").is_file())
            self.assertIn("Created: 2", out)

    def test_empty_container_on_new_transcript_stores_empty_chapter_list(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_video(root / "in" / "Vol1.mp4")
            status, out = _run(
                root / "in",
                root / "out",
                speech=_speech_writer(),
                chapters=_chapter_reader([]),
            )
            self.assertEqual(status, 0)
            data = _read_json(root / "out" / "Vol1.json")
            self.assertEqual(data["chapters"], [])
            self.assertIn("Created: 1", out)


class KeepSpeechTest(unittest.TestCase):
    def test_existing_speech_is_not_requested_again(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_video(root / "in" / "Vol1.mp4")
            dest = root / "out" / "Vol1.json"
            dest.parent.mkdir(parents=True)
            dest.write_text(
                json.dumps(
                    {
                        "video_file": "Vol1.mp4",
                        "chapters": [{"title": "Old", "start": 0.0, "end": 1.0}],
                        "language": "en",
                        "segments": [{"start": 0.0, "end": 1.0, "text": "kept"}],
                    }
                ),
                encoding="utf-8",
            )
            speech_calls: list = []
            status, out = _run(
                root / "in",
                root / "out",
                speech=_speech_writer(calls=speech_calls),
                chapters=_chapter_reader([{"title": "Old", "start": 0.0, "end": 1.0}]),
            )
            self.assertEqual(status, 0)
            self.assertEqual(speech_calls, [])
            self.assertEqual(_read_json(dest)["segments"][0]["text"], "kept")
            self.assertIn("Unchanged: 1", out)

    def test_empty_segments_list_counts_as_finished_speech(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_video(root / "in" / "Vol1.mp4")
            dest = root / "out" / "Vol1.json"
            dest.parent.mkdir(parents=True)
            dest.write_text(
                json.dumps(
                    {
                        "video_file": "Vol1.mp4",
                        "chapters": [],
                        "language": "en",
                        "segments": [],
                    }
                ),
                encoding="utf-8",
            )
            speech_calls: list = []
            status, out = _run(
                root / "in",
                root / "out",
                speech=_speech_writer(calls=speech_calls),
                chapters=_chapter_reader([]),
            )
            self.assertEqual(status, 0)
            self.assertEqual(speech_calls, [])
            self.assertIn("Unchanged: 1", out)

    def test_missing_segments_requests_speech_and_keeps_other_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_video(root / "in" / "Vol1.mp4")
            dest = root / "out" / "Vol1.json"
            dest.parent.mkdir(parents=True)
            dest.write_text(
                json.dumps(
                    {
                        "video_file": "Vol1.mp4",
                        "chapters": [{"title": "Keep", "start": 0.0, "end": 2.0}],
                        "extra": True,
                    }
                ),
                encoding="utf-8",
            )
            status, out = _run(
                root / "in",
                root / "out",
                speech=_speech_writer(),
                chapters=_chapter_reader([{"title": "Keep", "start": 0.0, "end": 2.0}]),
            )
            self.assertEqual(status, 0)
            data = _read_json(dest)
            self.assertEqual(data["chapters"][0]["title"], "Keep")
            self.assertEqual(data["video_file"], "Vol1.mp4")
            self.assertIs(data["extra"], True)
            self.assertEqual(len(data["segments"]), 1)
            self.assertIn("Updated: 1", out)


class ChapterMergeTest(unittest.TestCase):
    def test_missing_chapters_filled_from_container(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_video(root / "in" / "Vol1.mp4")
            dest = root / "out" / "Vol1.json"
            dest.parent.mkdir(parents=True)
            dest.write_text(
                json.dumps(
                    {
                        "video_file": "Vol1.mp4",
                        "language": "en",
                        "segments": [{"start": 0.0, "end": 1.0, "text": "x"}],
                    }
                ),
                encoding="utf-8",
            )
            status, out = _run(
                root / "in",
                root / "out",
                speech=_speech_writer(),
                chapters=_chapter_reader([{"title": "New", "start": 1.23456, "end": 2.0}]),
            )
            self.assertEqual(status, 0)
            data = _read_json(dest)
            self.assertEqual(data["chapters"][0]["title"], "New")
            self.assertEqual(data["chapters"][0]["start"], 1.235)
            self.assertIn("Updated: 1", out)

    def test_empty_container_leaves_existing_chapters(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_video(root / "in" / "Vol1.mp4")
            dest = root / "out" / "Vol1.json"
            dest.parent.mkdir(parents=True)
            existing = [{"title": "Keep me", "start": 0.0, "end": 5.0}]
            dest.write_text(
                json.dumps(
                    {
                        "video_file": "Vol1.mp4",
                        "chapters": existing,
                        "language": "en",
                        "segments": [{"start": 0.0, "end": 1.0, "text": "x"}],
                    }
                ),
                encoding="utf-8",
            )
            status, out = _run(
                root / "in",
                root / "out",
                speech=_speech_writer(),
                chapters=_chapter_reader([]),
            )
            self.assertEqual(status, 0)
            self.assertEqual(_read_json(dest)["chapters"], existing)
            self.assertIn("Unchanged: 1", out)

    def test_differing_container_replaces_chapters(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_video(root / "in" / "Vol1.mp4")
            dest = root / "out" / "Vol1.json"
            dest.parent.mkdir(parents=True)
            dest.write_text(
                json.dumps(
                    {
                        "video_file": "Vol1.mp4",
                        "chapters": [{"title": "Old", "start": 0.0, "end": 1.0}],
                        "language": "en",
                        "segments": [{"start": 0.0, "end": 1.0, "text": "x"}],
                    }
                ),
                encoding="utf-8",
            )
            status, out = _run(
                root / "in",
                root / "out",
                speech=_speech_writer(),
                chapters=_chapter_reader([{"title": "New", "start": 0.0, "end": 2.0}]),
            )
            self.assertEqual(status, 0)
            self.assertEqual(_read_json(dest)["chapters"][0]["title"], "New")
            self.assertIn("Updated: 1", out)

    def test_millisecond_equality_does_not_rewrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_video(root / "in" / "Vol1.mp4")
            dest = root / "out" / "Vol1.json"
            dest.parent.mkdir(parents=True)
            dest.write_text(
                json.dumps(
                    {
                        "video_file": "Vol1.mp4",
                        "chapters": [{"title": "Same", "start": 1.0, "end": 2.0}],
                        "language": "en",
                        "segments": [{"start": 0.0, "end": 1.0, "text": "x"}],
                    }
                ),
                encoding="utf-8",
            )
            status, out = _run(
                root / "in",
                root / "out",
                speech=_speech_writer(),
                chapters=_chapter_reader([{"title": "Same", "start": 1.0004, "end": 2.0004}]),
            )
            self.assertEqual(status, 0)
            self.assertIn("Unchanged: 1", out)

    def test_blank_container_title_becomes_chapter_n(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_video(root / "in" / "Vol1.mp4")
            status, _ = _run(
                root / "in",
                root / "out",
                speech=_speech_writer(),
                chapters=_chapter_reader([{"title": "  ", "start": 0.0, "end": 1.0}]),
            )
            self.assertEqual(status, 0)
            self.assertEqual(_read_json(root / "out" / "Vol1.json")["chapters"][0]["title"], "Chapter 1")

    def test_same_titles_different_order_updates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_video(root / "in" / "Vol1.mp4")
            dest = root / "out" / "Vol1.json"
            dest.parent.mkdir(parents=True)
            dest.write_text(
                json.dumps(
                    {
                        "video_file": "Vol1.mp4",
                        "chapters": [
                            {"title": "A", "start": 0.0, "end": 1.0},
                            {"title": "B", "start": 1.0, "end": 2.0},
                        ],
                        "language": "en",
                        "segments": [{"start": 0.0, "end": 1.0, "text": "x"}],
                    }
                ),
                encoding="utf-8",
            )
            status, out = _run(
                root / "in",
                root / "out",
                speech=_speech_writer(),
                chapters=_chapter_reader(
                    [
                        {"title": "B", "start": 1.0, "end": 2.0},
                        {"title": "A", "start": 0.0, "end": 1.0},
                    ]
                ),
            )
            self.assertEqual(status, 0)
            self.assertEqual(_read_json(dest)["chapters"][0]["title"], "B")
            self.assertIn("Updated: 1", out)


class VideoFileMergeTest(unittest.TestCase):
    def test_missing_video_file_is_filled(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_video(root / "in" / "Vol1.mp4")
            dest = root / "out" / "Vol1.json"
            dest.parent.mkdir(parents=True)
            dest.write_text(
                json.dumps(
                    {
                        "chapters": [],
                        "language": "en",
                        "segments": [{"start": 0.0, "end": 1.0, "text": "x"}],
                    }
                ),
                encoding="utf-8",
            )
            status, out = _run(
                root / "in",
                root / "out",
                speech=_speech_writer(),
                chapters=_chapter_reader([]),
            )
            self.assertEqual(status, 0)
            self.assertEqual(_read_json(dest)["video_file"], "Vol1.mp4")
            self.assertIn("Updated: 1", out)

    def test_empty_video_file_is_filled(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_video(root / "in" / "Vol1.mp4")
            dest = root / "out" / "Vol1.json"
            dest.parent.mkdir(parents=True)
            dest.write_text(
                json.dumps(
                    {
                        "video_file": "",
                        "chapters": [],
                        "language": "en",
                        "segments": [{"start": 0.0, "end": 1.0, "text": "x"}],
                    }
                ),
                encoding="utf-8",
            )
            status, out = _run(
                root / "in",
                root / "out",
                speech=_speech_writer(),
                chapters=_chapter_reader([]),
            )
            self.assertEqual(status, 0)
            self.assertEqual(_read_json(dest)["video_file"], "Vol1.mp4")
            self.assertIn("Updated: 1", out)

    def test_renamed_video_updates_video_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_video(root / "in" / "NewName.mp4")
            dest = root / "out" / "NewName.json"
            dest.parent.mkdir(parents=True)
            dest.write_text(
                json.dumps(
                    {
                        "video_file": "OldName.mp4",
                        "chapters": [],
                        "language": "en",
                        "segments": [{"start": 0.0, "end": 1.0, "text": "x"}],
                    }
                ),
                encoding="utf-8",
            )
            status, out = _run(
                root / "in",
                root / "out",
                speech=_speech_writer(),
                chapters=_chapter_reader([]),
            )
            self.assertEqual(status, 0)
            self.assertEqual(_read_json(dest)["video_file"], "NewName.mp4")
            self.assertIn("Updated: 1", out)


class FailureCasesTest(unittest.TestCase):
    def test_shared_path_writes_nothing_and_names_both_videos(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_video(root / "in" / "Vol.mp4")
            _write_video(root / "in" / "Vol.mkv")
            speech_calls: list = []
            status, out = _run(
                root / "in",
                root / "out",
                speech=_speech_writer(calls=speech_calls),
                chapters=_chapter_reader([]),
            )
            self.assertEqual(status, 1)
            self.assertEqual(speech_calls, [])
            self.assertFalse((root / "out" / "Vol.json").exists())
            self.assertIn("shared path", out.lower())
            self.assertIn("Vol.mp4", out)
            self.assertIn("Vol.mkv", out)
            self.assertIn("Failed: 1", out)

    def test_unreadable_transcript_left_in_place_without_speech(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_video(root / "in" / "Vol1.mp4")
            dest = root / "out" / "Vol1.json"
            dest.parent.mkdir(parents=True)
            dest.write_text("{not-json", encoding="utf-8")
            speech_calls: list = []
            status, out = _run(
                root / "in",
                root / "out",
                speech=_speech_writer(calls=speech_calls),
                chapters=_chapter_reader([]),
            )
            self.assertEqual(status, 1)
            self.assertEqual(speech_calls, [])
            self.assertEqual(dest.read_text(encoding="utf-8"), "{not-json")
            self.assertIn("unreadable", out.lower())

    def test_wrong_shape_segments_left_in_place(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_video(root / "in" / "Vol1.mp4")
            dest = root / "out" / "Vol1.json"
            dest.parent.mkdir(parents=True)
            original = {"segments": "nope", "chapters": [], "video_file": "Vol1.mp4"}
            dest.write_text(json.dumps(original), encoding="utf-8")
            speech_calls: list = []
            status, out = _run(
                root / "in",
                root / "out",
                speech=_speech_writer(calls=speech_calls),
                chapters=_chapter_reader([]),
            )
            self.assertEqual(status, 1)
            self.assertEqual(speech_calls, [])
            self.assertEqual(_read_json(dest), original)
            self.assertIn("wrong shape", out.lower())

    def test_list_root_is_speech_list_and_can_gain_chapters(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_video(root / "in" / "Vol1.mp4")
            dest = root / "out" / "Vol1.json"
            dest.parent.mkdir(parents=True)
            dest.write_text(
                json.dumps([{"start": 0.0, "end": 1.0, "text": "legacy"}]),
                encoding="utf-8",
            )
            status, out = _run(
                root / "in",
                root / "out",
                speech=_speech_writer(),
                chapters=_chapter_reader([{"title": "Added", "start": 0.0, "end": 1.0}]),
            )
            self.assertEqual(status, 0)
            data = _read_json(dest)
            self.assertEqual(data["segments"][0]["text"], "legacy")
            self.assertEqual(data["chapters"][0]["title"], "Added")
            self.assertEqual(data["video_file"], "Vol1.mp4")
            self.assertIn("Updated: 1", out)

    def test_speech_failure_leaves_existing_transcript(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_video(root / "in" / "Vol1.mp4")
            dest = root / "out" / "Vol1.json"
            dest.parent.mkdir(parents=True)
            original = {
                "video_file": "Vol1.mp4",
                "chapters": [{"title": "Keep", "start": 0.0, "end": 1.0}],
                "extra": 1,
            }
            dest.write_text(json.dumps(original), encoding="utf-8")
            status, out = _run(
                root / "in",
                root / "out",
                speech=_speech_writer(fail=True),
                chapters=_chapter_reader([{"title": "Keep", "start": 0.0, "end": 1.0}]),
            )
            self.assertEqual(status, 1)
            self.assertEqual(_read_json(dest), original)
            self.assertIn("speech", out.lower())

    def test_speech_failure_for_missing_transcript_leaves_no_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_video(root / "in" / "Vol1.mp4")
            status, out = _run(
                root / "in",
                root / "out",
                speech=_speech_writer(fail=True),
                chapters=_chapter_reader([]),
            )
            self.assertEqual(status, 1)
            self.assertFalse((root / "out" / "Vol1.json").exists())
            self.assertIn("Failed: 1", out)

    def test_container_failure_saves_speech_and_counts_failed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_video(root / "in" / "Vol1.mp4")
            speech_calls: list = []
            status, out = _run(
                root / "in",
                root / "out",
                speech=_speech_writer(calls=speech_calls),
                chapters=_chapter_reader(fail=True),
            )
            self.assertEqual(status, 1)
            self.assertEqual(speech_calls[0]["hotwords"], None)
            data = _read_json(root / "out" / "Vol1.json")
            self.assertEqual(data["video_file"], "Vol1.mp4")
            self.assertIn("segments", data)
            self.assertNotIn("chapters", data)
            self.assertIn("Failed: 1", out)
            self.assertNotIn("Created: 1", out)
            self.assertIn("chapters", out.lower())

    def test_container_failure_leaves_existing_chapters(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_video(root / "in" / "Vol1.mp4")
            dest = root / "out" / "Vol1.json"
            dest.parent.mkdir(parents=True)
            dest.write_text(
                json.dumps(
                    {
                        "chapters": [{"title": "Keep", "start": 0.0, "end": 1.0}],
                        "language": "en",
                        "segments": [{"start": 0.0, "end": 1.0, "text": "x"}],
                    }
                ),
                encoding="utf-8",
            )
            status, out = _run(
                root / "in",
                root / "out",
                speech=_speech_writer(),
                chapters=_chapter_reader(fail=True),
            )
            self.assertEqual(status, 1)
            data = _read_json(dest)
            self.assertEqual(data["chapters"][0]["title"], "Keep")
            self.assertEqual(data["video_file"], "Vol1.mp4")
            self.assertIn("Failed: 1", out)

    def test_container_failure_on_complete_transcript_does_not_rewrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_video(root / "in" / "Vol1.mp4")
            dest = root / "out" / "Vol1.json"
            dest.parent.mkdir(parents=True)
            payload = {
                "video_file": "Vol1.mp4",
                "chapters": [{"title": "Keep", "start": 0.0, "end": 1.0}],
                "language": "en",
                "segments": [{"start": 0.0, "end": 1.0, "text": "x"}],
            }
            dest.write_text(json.dumps(payload), encoding="utf-8")
            before = dest.read_text(encoding="utf-8")
            mtime = dest.stat().st_mtime_ns
            status, out = _run(
                root / "in",
                root / "out",
                speech=_speech_writer(),
                chapters=_chapter_reader(fail=True),
            )
            self.assertEqual(status, 1)
            self.assertEqual(dest.read_text(encoding="utf-8"), before)
            self.assertEqual(dest.stat().st_mtime_ns, mtime)
            self.assertIn("Failed: 1", out)

    def test_one_failure_continues_later_volumes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_video(root / "in" / "A.mp4")
            _write_video(root / "in" / "B.mp4")
            dest_a = root / "out" / "A.json"
            dest_a.parent.mkdir(parents=True)
            dest_a.write_text("{bad", encoding="utf-8")

            status, out = _run(
                root / "in",
                root / "out",
                speech=_speech_writer(),
                chapters=_chapter_reader([]),
            )
            self.assertEqual(status, 1)
            self.assertTrue((root / "out" / "B.json").is_file())
            self.assertIn("Failed: 1", out)
            self.assertIn("Created: 1", out)

    def test_missing_chapter_program_stops_before_volumes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_video(root / "in" / "Vol1.mp4")
            status, out = _run(
                root / "in",
                root / "out",
                speech=_speech_writer(),
                chapters=_chapter_reader([]),
                chapter_available=False,
            )
            self.assertEqual(status, 1)
            self.assertFalse((root / "out" / "Vol1.json").exists())

    def test_missing_speech_program_stops_when_speech_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_video(root / "in" / "Vol1.mp4")
            status, out = _run(
                root / "in",
                root / "out",
                speech=_speech_writer(),
                chapters=_chapter_reader([]),
                speech_available=False,
            )
            self.assertEqual(status, 1)
            self.assertFalse((root / "out" / "Vol1.json").exists())

    def test_missing_speech_program_allows_chapter_only_repair(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_video(root / "in" / "Vol1.mp4")
            dest = root / "out" / "Vol1.json"
            dest.parent.mkdir(parents=True)
            dest.write_text(
                json.dumps(
                    {
                        "video_file": "Vol1.mp4",
                        "language": "en",
                        "segments": [{"start": 0.0, "end": 1.0, "text": "x"}],
                    }
                ),
                encoding="utf-8",
            )
            status, out = _run(
                root / "in",
                root / "out",
                speech=_speech_writer(),
                chapters=_chapter_reader([{"title": "Added", "start": 0.0, "end": 1.0}]),
                speech_available=False,
            )
            self.assertEqual(status, 0)
            self.assertEqual(_read_json(dest)["chapters"][0]["title"], "Added")
            self.assertIn("Updated: 1", out)


class HotwordTest(unittest.TestCase):
    def test_hotword_examples_from_titles(self):
        cases = [
            (["Intro to the Von Flue"], "Von Flue"),
            (["Chapter 3"], None),
            (["Chapter 3 - Choi Bar"], "Choi Bar"),
            (["MAIN ATTACKS"], None),
            (["Choi Bar Set Up gripping Sequence"], "Choi Bar Set Up gripping Sequence"),
            (["5 UNDERHOOK KNEELING OVERVIEW"], "UNDERHOOK KNEELING"),
            (["Ai-Yotsu", "3/4"], "Ai-Yotsu 3/4"),
            (["(SOP)"], "SOP"),
            (["Von Flue", "VON FLUE"], "Von Flue"),
        ]
        for titles, expected in cases:
            with self.subTest(titles=titles, expected=expected):
                with tempfile.TemporaryDirectory() as tmp:
                    root = Path(tmp)
                    _write_video(root / "in" / "Vol1.mp4")
                    speech_calls: list = []
                    chapters = [
                        {"title": t, "start": float(i), "end": float(i) + 1.0}
                        for i, t in enumerate(titles)
                    ]
                    status, _ = _run(
                        root / "in",
                        root / "out",
                        speech=_speech_writer(calls=speech_calls),
                        chapters=_chapter_reader(chapters),
                        count_hotword_tokens=lambda s: len(s.split()),
                    )
                    self.assertEqual(status, 0)
                    self.assertEqual(speech_calls[0]["hotwords"], expected)

    def test_title_dropped_when_tokens_would_exceed_223(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_video(root / "in" / "Vol1.mp4")
            speech_calls: list = []

            def count_tokens(text: str) -> int:
                # Each kept word costs 100 tokens so a second title trips the cap.
                return max(1, len(text.split()) * 100) if text.strip() else 0

            status, _ = _run(
                root / "in",
                root / "out",
                speech=_speech_writer(calls=speech_calls),
                chapters=_chapter_reader(
                    [
                        {"title": "Alpha", "start": 0.0, "end": 1.0},
                        {"title": "Beta", "start": 1.0, "end": 2.0},
                        {"title": "Gamma", "start": 2.0, "end": 3.0},
                    ]
                ),
                count_hotword_tokens=count_tokens,
            )
            self.assertEqual(status, 0)
            self.assertEqual(speech_calls[0]["hotwords"], "Alpha Beta")

    def test_no_hotwords_when_container_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_video(root / "in" / "Vol1.mp4")
            speech_calls: list = []
            status, _ = _run(
                root / "in",
                root / "out",
                speech=_speech_writer(calls=speech_calls),
                chapters=_chapter_reader([]),
            )
            self.assertEqual(status, 0)
            self.assertIsNone(speech_calls[0]["hotwords"])

    def test_ocr_passed_only_when_speech_requested(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_video(root / "in" / "Vol1.mp4")
            dest = root / "out" / "Vol1.json"
            dest.parent.mkdir(parents=True)
            dest.write_text(
                json.dumps(
                    {
                        "video_file": "Vol1.mp4",
                        "language": "en",
                        "segments": [{"start": 0.0, "end": 1.0, "text": "x"}],
                    }
                ),
                encoding="utf-8",
            )
            speech_calls: list = []
            status, _ = _run(
                root / "in",
                root / "out",
                ocr=True,
                speech=_speech_writer(calls=speech_calls),
                chapters=_chapter_reader([{"title": "X", "start": 0.0, "end": 1.0}]),
            )
            self.assertEqual(status, 0)
            self.assertEqual(speech_calls, [])


class SecondRunStableTest(unittest.TestCase):
    def test_second_run_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_video(root / "in" / "Vol1.mp4")
            chapters = [{"title": "One", "start": 0.0, "end": 1.0}]
            status1, _ = _run(
                root / "in",
                root / "out",
                speech=_speech_writer(),
                chapters=_chapter_reader(chapters),
            )
            self.assertEqual(status1, 0)
            before = (root / "out" / "Vol1.json").read_text(encoding="utf-8")
            mtime = (root / "out" / "Vol1.json").stat().st_mtime_ns
            status2, out = _run(
                root / "in",
                root / "out",
                speech=_speech_writer(),
                chapters=_chapter_reader(chapters),
            )
            self.assertEqual(status2, 0)
            self.assertEqual((root / "out" / "Vol1.json").read_text(encoding="utf-8"), before)
            self.assertEqual((root / "out" / "Vol1.json").stat().st_mtime_ns, mtime)
            self.assertIn("Unchanged: 1", out)
            self.assertIn("Created: 0", out)
            self.assertIn("Updated: 0", out)


class CliOptionsTest(unittest.TestCase):
    def test_force_and_stamp_options_removed(self):
        parser = batch_panoscribe.build_parser()
        option_strings = {
            opt
            for action in parser._actions
            for opt in (action.option_strings or [])
        }
        self.assertNotIn("--force", option_strings)
        self.assertNotIn("--stamp-video-file", option_strings)
        self.assertNotIn("--transcribe", option_strings)
        self.assertNotIn("--no-transcribe", option_strings)
        self.assertIn("--ocr", option_strings)
        self.assertIn("--no-ocr", option_strings)


if __name__ == "__main__":
    unittest.main()
