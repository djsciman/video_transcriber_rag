from pathlib import Path

from bjj_organizer.split import build_copy_cmd


def test_copy_cmd_no_concat():
    cmd = build_copy_cmd("ffmpeg", Path("in.mp4"), Path("out.mkv"))
    assert cmd.count("-i") == 1
    assert "-c" in cmd
    assert "copy" in cmd
