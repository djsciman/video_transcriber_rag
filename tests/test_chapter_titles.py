"""Opening branding titles that do not open a video."""

import unittest

import generate_chapters


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


if __name__ == "__main__":
    unittest.main()
