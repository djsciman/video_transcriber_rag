from pathlib import Path

from bjj_organizer.models import Chapter
from bjj_organizer.split import build_copy_cmd, build_split_cmd, chapter_ranges, ms_to_seconds, resolve_range


def test_ms_to_seconds():
    assert ms_to_seconds(0) == "0.000"
    assert ms_to_seconds(12_500) == "12.500"
    assert ms_to_seconds(65_000) == "65.000"


def test_chapter_ranges_last_end_is_duration():
    chapters = [
        Chapter("Intro", 0),
        Chapter("Drills", 65_000),
        Chapter("Too late", 999_999_000),
    ]
    ranges = chapter_ranges(chapters, duration_ms=120_000)
    assert [(ch.title, start, end) for ch, start, end in ranges] == [
        ("Intro", 0, 65_000),
        ("Drills", 65_000, 120_000),
    ]


def test_resolve_range_skips_empty_and_past_duration():
    assert resolve_range(0, 1000, 5000) == (0, 1000)
    assert resolve_range(0, None, 5000) == (0, 5000)
    assert resolve_range(5000, 6000, 5000) is None
    assert resolve_range(2000, 2000, 5000) is None


def test_split_cmd_maps_only_av_uses_ss_to_no_map_zero():
    cmd = build_split_cmd(
        "ffmpeg",
        Path("in.mp4"),
        Path("out.mp4"),
        start_ms=0,
        end_ms=12_500,
    )
    assert cmd[0] == "ffmpeg"
    assert "-ss" in cmd
    assert cmd[cmd.index("-ss") + 1] == "0.000"
    assert "-to" in cmd
    assert cmd[cmd.index("-to") + 1] == "12.500"
    assert cmd.count("-i") == 1
    assert "-map" in cmd
    assert "0:v:0?" in cmd
    assert "0:a?" in cmd
    assert "-dn" in cmd
    assert "-sn" in cmd
    assert "-ignore_unknown" in cmd
    assert "-avoid_negative_ts" in cmd
    assert "0" not in cmd[cmd.index("-map") + 1] or cmd[cmd.index("-map") + 1] != "0"
    assert "-map" not in cmd or "0" != cmd[cmd.index("-map") + 1]
    joined = " ".join(cmd)
    assert "-map 0 " not in joined + " "
    assert joined.endswith("out.mp4")


def test_copy_cmd_no_concat():
    cmd = build_copy_cmd("ffmpeg", Path("in.mp4"), Path("out.mkv"))
    assert cmd.count("-i") == 1
    assert "-c" in cmd
    assert "copy" in cmd
