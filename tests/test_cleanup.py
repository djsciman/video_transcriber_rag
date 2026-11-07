"""Clean-up turns completed volume JSON into a raw part-list record."""

from __future__ import annotations

import inspect
import unittest

from coach_app.cleanup import cleanup_volume


class NoChaptersTest(unittest.TestCase):
    def test_no_chapters_is_one_untitled_part_and_copies_video_file(self):
        volume = {
            "video_file": "Vol1.mp4",
            "language": "en",
            "chapters": [],
            "segments": [
                {
                    "start": 1.0,
                    "end": 2.0,
                    "text": "closed guard",
                    "source": "SPEECH",
                    "asr_logprob": -0.2,
                    "ocr_confidence": None,
                    "language": "en",
                },
                {
                    "start": 3.0,
                    "end": 4.5,
                    "text": "hip bump",
                    "source": "SPEECH",
                    "asr_logprob": -0.1,
                    "ocr_confidence": None,
                    "language": "en",
                },
            ],
        }

        record = cleanup_volume(volume)

        self.assertEqual(record["video_file"], "Vol1.mp4")
        self.assertEqual(record["recording_title"], "")
        self.assertEqual(len(record["parts"]), 1)
        part = record["parts"][0]
        self.assertEqual(part["title"], "")
        self.assertEqual(part["start"], 1.0)
        self.assertEqual(part["end"], 4.5)
        self.assertEqual(
            part["speech"],
            [
                {"start": 1.0, "end": 2.0, "text": "closed guard"},
                {"start": 3.0, "end": 4.5, "text": "hip bump"},
            ],
        )


class FillerTokenTest(unittest.TestCase):
    def test_removes_only_uh_um_er_and_keeps_teaching_words(self):
        volume = {
            "video_file": "Vol1.mp4",
            "chapters": [],
            "segments": [
                {
                    "start": 3.1,
                    "end": 6.0,
                    "text": "different uh proponents of jiu jitsu uh utilizing",
                    "source": "SPEECH",
                    "asr_logprob": -0.3,
                    "language": "en",
                },
                {
                    "start": 6.0,
                    "end": 7.0,
                    "text": "umbrella  er  underhook",
                    "source": "SPEECH",
                    "asr_logprob": -0.1,
                    "language": "en",
                },
            ],
        }

        record = cleanup_volume(volume)

        texts = [span["text"] for span in record["parts"][0]["speech"]]
        self.assertEqual(
            texts,
            [
                "different proponents of jiu jitsu utilizing",
                "umbrella underhook",
            ],
        )


class WholeRecordingChapterTest(unittest.TestCase):
    def test_one_whole_recording_chapter_is_untitled_with_recording_title(self):
        volume = {
            "video_file": "Volume 8.mp4",
            "chapters": [
                {
                    "title": "11 Z GUARD, KIMURA, AND NARRATED ROLLING",
                    "start": 0.0,
                    "end": 9581.0,
                }
            ],
            "segments": [
                {
                    "start": 3.0,
                    "end": 8.0,
                    "text": "Zeg guard",
                    "source": "SPEECH",
                    "language": "en",
                },
                {
                    "start": 9000.0,
                    "end": 9010.0,
                    "text": "choy bar",
                    "source": "SPEECH",
                    "language": "en",
                },
            ],
        }

        record = cleanup_volume(volume)

        self.assertEqual(record["video_file"], "Volume 8.mp4")
        self.assertEqual(
            record["recording_title"],
            "11 Z GUARD, KIMURA, AND NARRATED ROLLING",
        )
        self.assertEqual(len(record["parts"]), 1)
        part = record["parts"][0]
        self.assertEqual(part["title"], "")
        self.assertEqual(part["start"], 3.0)
        self.assertEqual(part["end"], 9010.0)
        self.assertEqual(
            [span["text"] for span in part["speech"]],
            ["Zeg guard", "choy bar"],
        )

    def test_one_partial_chapter_is_still_one_untitled_part(self):
        volume = {
            "video_file": "Vol1.mp4",
            "chapters": [
                {"title": "Intro", "start": 0.0, "end": 30.0},
            ],
            "segments": [
                {"start": 1.0, "end": 2.0, "text": "hello", "source": "SPEECH"},
                {"start": 40.0, "end": 41.0, "text": "later", "source": "SPEECH"},
            ],
        }

        record = cleanup_volume(volume)

        self.assertEqual(record["recording_title"], "")
        self.assertEqual(len(record["parts"]), 1)
        self.assertEqual(record["parts"][0]["title"], "")
        self.assertEqual(
            [span["text"] for span in record["parts"][0]["speech"]],
            ["hello", "later"],
        )


class RealChaptersTest(unittest.TestCase):
    def test_two_titled_chapters_nest_speech_under_those_parts(self):
        volume = {
            "video_file": "Closed Guard.mp4",
            "language": "en",
            "chapters": [
                {"title": "Closed Guard", "start": 0.0, "end": 120.0},
                {"title": "Arm Bar", "start": 120.0, "end": 240.0},
            ],
            "segments": [
                {
                    "start": 10.0,
                    "end": 14.0,
                    "text": "closed guard",
                    "source": "SPEECH",
                    "asr_logprob": -0.1,
                    "ocr_confidence": None,
                    "language": "en",
                },
                {
                    "start": 120.0,
                    "end": 125.0,
                    "text": "armbar",
                    "source": "SPEECH",
                    "asr_logprob": -0.2,
                    "ocr_confidence": None,
                    "language": "en",
                },
                {
                    "start": 200.0,
                    "end": 205.0,
                    "text": "finish the armbar",
                    "source": "SPEECH",
                    "asr_logprob": -0.15,
                    "language": "en",
                },
            ],
        }

        record = cleanup_volume(volume)

        self.assertEqual(record["video_file"], "Closed Guard.mp4")
        self.assertEqual(record["recording_title"], "")
        self.assertEqual(
            record["parts"],
            [
                {
                    "title": "Closed Guard",
                    "start": 0.0,
                    "end": 120.0,
                    "speech": [
                        {"start": 10.0, "end": 14.0, "text": "closed guard"},
                    ],
                },
                {
                    "title": "Arm Bar",
                    "start": 120.0,
                    "end": 240.0,
                    "speech": [
                        {"start": 120.0, "end": 125.0, "text": "armbar"},
                        {"start": 200.0, "end": 205.0, "text": "finish the armbar"},
                    ],
                },
            ],
        )

    def test_overlapping_chapters_use_later_starting_and_do_not_slide(self):
        volume = {
            "video_file": "Vol1.mp4",
            "chapters": [
                {"title": "Closed Guard", "start": 0.0, "end": 30.0},
                {"title": "Arm Bar", "start": 20.0, "end": 50.0},
            ],
            "segments": [
                {
                    "start": 10.0,
                    "end": 25.0,
                    "text": "starts in closed guard",
                    "source": "SPEECH",
                },
                {
                    "start": 22.0,
                    "end": 28.0,
                    "text": "both chapters contain this start",
                    "source": "SPEECH",
                },
                {
                    "start": 40.0,
                    "end": 45.0,
                    "text": "only arm bar",
                    "source": "SPEECH",
                },
                {
                    "start": 60.0,
                    "end": 62.0,
                    "text": "after both chapters",
                    "source": "SPEECH",
                },
            ],
        }

        record = cleanup_volume(volume)

        self.assertEqual(
            [(part["title"], [span["text"] for span in part["speech"]]) for part in record["parts"]],
            [
                ("Closed Guard", ["starts in closed guard"]),
                ("Arm Bar", ["both chapters contain this start", "only arm bar"]),
                ("", ["after both chapters"]),
            ],
        )
        untitled = record["parts"][-1]
        self.assertEqual(untitled["title"], "")
        self.assertEqual(untitled["start"], 60.0)
        self.assertEqual(untitled["end"], 62.0)
        self.assertNotIn("language", untitled["speech"][0])
        self.assertNotIn("source", untitled["speech"][0])
        self.assertNotIn("asr_logprob", untitled["speech"][0])
        self.assertNotIn("ocr_confidence", untitled["speech"][0])

    def test_gap_between_chapters_stays_untitled_not_slid_into_neighbor(self):
        volume = {
            "video_file": "Vol1.mp4",
            "chapters": [
                {"title": "Closed Guard", "start": 0.0, "end": 10.0},
                {"title": "Arm Bar", "start": 20.0, "end": 30.0},
            ],
            "segments": [
                {"start": 5.0, "end": 8.0, "text": "in closed guard", "source": "SPEECH"},
                {"start": 12.0, "end": 16.0, "text": "between chapters", "source": "SPEECH"},
                {"start": 22.0, "end": 24.0, "text": "in arm bar", "source": "SPEECH"},
            ],
        }

        record = cleanup_volume(volume)

        self.assertEqual(
            [(part["title"], [span["text"] for span in part["speech"]]) for part in record["parts"]],
            [
                ("Closed Guard", ["in closed guard"]),
                ("", ["between chapters"]),
                ("Arm Bar", ["in arm bar"]),
            ],
        )


class CuratedStoreIsolationTest(unittest.TestCase):
    def test_raw_record_is_not_written_to_the_curated_store(self):
        volume = {
            "video_file": "Vol1.mp4",
            "chapters": [
                {"title": "Closed Guard", "start": 0.0, "end": 10.0},
                {"title": "Arm Bar", "start": 10.0, "end": 20.0},
            ],
            "segments": [
                {"start": 1.0, "end": 2.0, "text": "guard", "source": "SPEECH"},
            ],
        }
        record = cleanup_volume(volume)

        self.assertIn("parts", record)
        self.assertNotIn("store", inspect.signature(cleanup_volume).parameters)
