from pathlib import Path

from bjj_organizer.concat import build_concat_cmd, chapters_from_durations, concat_list_line
from bjj_organizer.models import Chapter


def test_chapters_from_durations():
    chapters = chapters_from_durations(["Intro", "Drills"], [10_000, 20_000])
    assert chapters == [Chapter("Intro", 0), Chapter("Drills", 10_000)]


def test_concat_cmd_uses_concat_demuxer_and_copy():
    cmd = build_concat_cmd("ffmpeg", Path("list.txt"), Path("out.mp4"))
    assert cmd[:6] == ["ffmpeg", "-y", "-f", "concat", "-safe", "0"]
    assert "-c" in cmd
    assert "copy" in cmd
    assert "-dn" in cmd
    joined = " ".join(cmd)
    assert "-map 0 " not in joined + " "
    assert joined.endswith("out.mp4")


def test_concat_list_line_uses_posix_and_quotes(tmp_path: Path):
    path = tmp_path / "clip 1.mp4"
    line = concat_list_line(path)
    assert line.startswith("file '")
    assert line.endswith("'")
    assert "\\" not in line.replace(r"'\''", "")
