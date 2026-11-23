"""Opening branding titles that do not open a video."""

import unittest
from pathlib import Path

import generate_chapters
from bjj_pipeline.organizer.naming import parse_video, sole_chapter_title


class OpeningChapterTitleTest(unittest.TestCase):
    def test_stance_garbled_intro_plate_at_zero_is_introduction(self):
        self.assertEqual(
            generate_chapters.opening_chapter_title(
                "INTRODUICTIONNTO FEEETTTOFFOORR WOLUME1",
                0.0,
            ),
            "Introduction",
        )

    def test_triangles_volume_plate_at_zero_is_introduction(self):
        self.assertEqual(
            generate_chapters.opening_chapter_title("TRIANGLES", 0.0),
            "Introduction",
        )

    def test_criteria_card_keeps_its_ocr(self):
        title = (
            "THE CRITERIA FOR TAKEDOWN SELECTION FOR JIU-JITSU"
        )
        self.assertEqual(
            generate_chapters.opening_chapter_title(title, 695.0),
            title,
        )

    def test_anchor_at_opening_window_keeps_ocr(self):
        title = "(1) Create The Critical One In / One Out Scenario"
        self.assertEqual(
            generate_chapters.opening_chapter_title(
                title,
                generate_chapters.OPENING_SECONDS,
            ),
            title,
        )


class SoleChapterTitleTest(unittest.TestCase):
    def test_introduction_becomes_episode_title(self):
        parsed = parse_video(
            Path("Passing the Guard - S01E04 - Toreando Pass.mp4")
        )
        self.assertEqual(
            sole_chapter_title(parsed, "Introduction"),
            "Toreando Pass",
        )

    def test_real_title_is_kept_on_volume_episode(self):
        parsed = parse_video(
            Path("Half Guard Anthology - S01E08 - Volume 8.mp4")
        )
        self.assertEqual(
            sole_chapter_title(
                parsed,
                "11 Z GUARD, KIMURA, AND NARRATED ROLLING",
            ),
            "11 Z GUARD, KIMURA, AND NARRATED ROLLING",
        )

    def test_volume_episode_introduction_becomes_volume_name(self):
        parsed = parse_video(
            Path(
                "The Collar and Sleeve System Part One by Mikey Musumeci"
                " - S01E01 - Volume 1.mp4"
            )
        )
        self.assertEqual(sole_chapter_title(parsed, "Introduction"), "Volume 1")

    def test_ocr_kept_when_filename_has_no_episode_title(self):
        parsed = parse_video(Path("TheHipBumpbyRyanHall3.mp4"))
        self.assertEqual(sole_chapter_title(parsed, "STRUCTURE"), "STRUCTURE")


if __name__ == "__main__":
    unittest.main()
