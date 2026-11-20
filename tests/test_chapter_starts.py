"""Chapter start rules that do not open a video."""

import unittest

import find_color_frames


class ShareClearsTest(unittest.TestCase):
    def test_equal_fraction_is_not_a_match_and_above_is(self):
        fraction = 0.75
        self.assertFalse(find_color_frames.share_clears(fraction, fraction))
        self.assertTrue(find_color_frames.share_clears(fraction + 0.001, fraction))


class WalkStartsTest(unittest.TestCase):
    def test_single_hit_keeps_its_share(self):
        rows = [(0.0, False, 0.1), (0.25, True, 0.82), (0.5, False, 0.2)]
        self.assertEqual(
            find_color_frames.walk_starts(rows, gap=30, run_length=1),
            [(0.25, 0.82)],
        )

    def test_non_match_does_not_emit(self):
        rows = [(0.0, False, 0.9), (1.0, False, 0.8)]
        self.assertEqual(find_color_frames.walk_starts(rows, gap=10, run_length=1), [])

    def test_later_hit_inside_gap_does_not_emit(self):
        rows = [(0.0, True, 0.8), (9.75, True, 0.91)]
        self.assertEqual(
            find_color_frames.walk_starts(rows, gap=10, run_length=1),
            [(0.0, 0.8)],
        )

    def test_hit_exactly_one_gap_later_emits(self):
        rows = [(0.0, True, 0.8), (10.0, True, 0.77)]
        self.assertEqual(
            find_color_frames.walk_starts(rows, gap=10, run_length=1),
            [(0.0, 0.8), (10.0, 0.77)],
        )

    def test_automatic_spike_does_not_emit(self):
        rows = [(0.0, True, 0.9), (1.0, False, 0.1)]
        self.assertEqual(find_color_frames.walk_starts(rows, gap=30, run_length=2), [])

    def test_two_adjacent_hits_emit_first_timestamp_and_share(self):
        rows = [(0.0, True, 0.81), (1.0, True, 0.99)]
        self.assertEqual(
            find_color_frames.walk_starts(rows, gap=30, run_length=2),
            [(0.0, 0.81)],
        )

    def test_match_miss_match_does_not_emit(self):
        rows = [(0.0, True, 0.9), (1.0, False, 0.1), (2.0, True, 0.95)]
        self.assertEqual(find_color_frames.walk_starts(rows, gap=30, run_length=2), [])

    def test_run_that_starts_inside_the_gap_does_not_emit(self):
        rows = [
            (0.0, True, 0.8),
            (1.0, True, 0.8),
            (2.0, False, 0.0),
            (29.0, True, 0.7),
            (30.0, True, 0.95),
            (31.0, True, 0.96),
        ]
        self.assertEqual(
            find_color_frames.walk_starts(rows, gap=30, run_length=2),
            [(0.0, 0.8)],
        )


if __name__ == "__main__":
    unittest.main()
