from pathlib import Path

from bjj_organizer.chapters import build_ffmetadata, build_ffmpeg_cmd
from bjj_organizer.models import Chapter
from bjj_organizer.scrape.bjj_fanatics import parse_timestamp_ms


def test_timestamp_formats():
    assert parse_timestamp_ms("0") == 0
    assert parse_timestamp_ms("1:05") == 65_000
    assert parse_timestamp_ms("1:01:11") == ((1 * 3600) + 60 + 11) * 1000
    assert parse_timestamp_ms("0 - 11:55") == 0
    assert parse_timestamp_ms("0- 2:44") == 0
    assert parse_timestamp_ms("0-2:44") == 0
    assert parse_timestamp_ms("11:55 - 25:41") == (11 * 60 + 55) * 1000
    assert parse_timestamp_ms("nope") is None


def test_ffmetadata_end_clamped_to_duration():
    chapters = [
        Chapter("Intro", 0),
        Chapter("Drills", 65_000),
        Chapter("Too late", 999_999_000),
    ]
    text = build_ffmetadata(chapters, duration_ms=120_000)
    assert "title=Intro" in text
    assert "START=0" in text
    assert "END=65000" in text
    assert "title=Drills" in text
    assert "END=120000" in text
    assert "Too late" not in text


def test_ffmetadata_skips_untitled_timeline():
    chapters = [Chapter("Intro", 0), Chapter("Goal setting", 0), Chapter("Distance", 0)]
    assert build_ffmetadata(chapters, duration_ms=120_000) == ""


def test_ffmpeg_cmd_maps_only_av_and_drops_data():
    cmd = build_ffmpeg_cmd(
        "ffmpeg",
        Path("in.mp4"),
        Path("chapters.ffmeta"),
        Path("out.mp4"),
        mov_faststart=True,
    )
    assert cmd.count("-map") == 2
    assert "0:v:0?" in cmd
    assert "0:a?" in cmd
    assert "-dn" in cmd
    assert "-sn" in cmd
    assert "-ignore_unknown" in cmd
    assert cmd[cmd.index("-map_chapters") + 1] == "1"
