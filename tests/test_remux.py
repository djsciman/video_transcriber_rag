"""Shared remux verify modes and chapter-probe reader, with stubbed ffmpeg."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

from bjj_pipeline.organizer.errors import FfmpegError
from bjj_pipeline.organizer.models import Chapter
from bjj_pipeline.remux import (
    VERIFY_COUNT,
    VERIFY_STRICT,
    RemuxError,
    build_ffmpeg_cmd,
    chapter_count,
    chapter_titles,
    read_container_chapters,
    remux_chapters,
)

INTRO = {
    "id": 0,
    "time_base": "1/1000",
    "start": 0,
    "start_time": "0.000000",
    "end": 10000,
    "end_time": "10.000000",
    "tags": {"title": "Intro"},
}


def _ok(args, stdout=""):
    return subprocess.CompletedProcess(args, 0, stdout, "")


def _fail(args, stderr="boom"):
    return subprocess.CompletedProcess(args, 1, "", stderr)


def _media(*, duration="10.000000", chapters=None, data_tag="text", extra_data=False, codec="h264"):
    streams = [
        {
            "codec_type": "video",
            "codec_name": codec,
            "width": 1920,
            "height": 1080,
            "nb_frames": "100",
        },
        {
            "codec_type": "audio",
            "codec_name": "aac",
            "sample_rate": "48000",
            "channels": 2,
            "nb_frames": "200",
        },
    ]
    if data_tag is not None:
        streams.append({"codec_type": "data", "codec_tag_string": data_tag})
    if extra_data:
        streams.append({"codec_type": "data", "codec_tag_string": "bin"})
    return {
        "format": {"duration": duration},
        "streams": streams,
        "chapters": chapters if chapters is not None else [INTRO],
    }


def _stub(_tmp: Path, *, after: dict, ffmpeg_ok: bool = True):
    calls: list[list[str]] = []

    def command(args: list[str]):
        calls.append(args)
        if Path(args[0]).name.lower().startswith("ffmpeg") or args[0] == "ffmpeg":
            if not ffmpeg_ok:
                return _fail(args)
            Path(args[-1]).write_bytes(b"remuxed")
            return _ok(args)
        return _ok(args, json.dumps(after))

    return command, calls


def test_count_verify_accepts_chapter_without_text_stream(tmp_path: Path):
    source = tmp_path / "vol.mp4"
    dest = tmp_path / "out.mp4"
    source.write_bytes(b"src")
    command, _calls = _stub(tmp_path, after={"chapters": [INTRO]})
    remux_chapters(
        source,
        dest,
        ";FFMETADATA1\n",
        ffmpeg="ffmpeg",
        ffprobe="ffprobe",
        verify=VERIFY_COUNT,
        command=command,
    )
    assert dest.read_bytes() == b"remuxed"


def test_count_verify_rejects_zero_chapters(tmp_path: Path):
    source = tmp_path / "vol.mp4"
    dest = tmp_path / "out.mp4"
    source.write_bytes(b"src")
    command, _calls = _stub(tmp_path, after={"chapters": []})
    with pytest.raises(RemuxError, match="no chapters"):
        remux_chapters(
            source,
            dest,
            ";FFMETADATA1\n",
            ffmpeg="ffmpeg",
            ffprobe="ffprobe",
            verify=VERIFY_COUNT,
            command=command,
        )
    assert not dest.exists()
    assert source.read_bytes() == b"src"


def test_strict_verify_accepts_mp4_text_stream(tmp_path: Path):
    video = tmp_path / "vol.mp4"
    video.write_bytes(b"src")
    after = _media()
    command, _calls = _stub(tmp_path, after=after)
    remux_chapters(
        video,
        video,
        ";FFMETADATA1\n",
        ffmpeg="ffmpeg",
        ffprobe="ffprobe",
        verify=VERIFY_STRICT,
        expected_chapters=[("Intro", 0, 10000)],
        before=after,
        duration=10.0,
        command=command,
    )
    assert video.read_bytes() == b"remuxed"


def test_strict_verify_rejects_webm_data_stream(tmp_path: Path):
    video = tmp_path / "vol.webm"
    video.write_bytes(b"src")
    after = _media()
    command, _calls = _stub(tmp_path, after=after)
    with pytest.raises(RemuxError, match="data stream"):
        remux_chapters(
            video,
            video,
            ";FFMETADATA1\n",
            ffmpeg="ffmpeg",
            ffprobe="ffprobe",
            verify=VERIFY_STRICT,
            expected_chapters=[("Intro", 0, 10000)],
            before=after,
            duration=10.0,
            command=command,
        )
    assert video.read_bytes() == b"src"


def test_strict_verify_rejects_signature_change(tmp_path: Path):
    video = tmp_path / "vol.mp4"
    video.write_bytes(b"src")
    before = _media()
    after = _media(codec="hevc")
    command, _calls = _stub(tmp_path, after=after)
    with pytest.raises(RemuxError, match="video or audio"):
        remux_chapters(
            video,
            video,
            ";FFMETADATA1\n",
            ffmpeg="ffmpeg",
            ffprobe="ffprobe",
            verify=VERIFY_STRICT,
            expected_chapters=[("Intro", 0, 10000)],
            before=before,
            duration=10.0,
            command=command,
        )
    assert video.read_bytes() == b"src"


def test_webm_count_flags_omit_mp4_faststart():
    cmd = build_ffmpeg_cmd(
        "ffmpeg",
        Path("in.webm"),
        Path("chapters.ffmeta"),
        Path("out.webm"),
        mov_faststart=True,
        verify=VERIFY_COUNT,
    )
    joined = " ".join(cmd)
    assert "-movflags" not in cmd
    assert "faststart" not in joined
    assert "-sn" not in cmd
    assert "-dn" in cmd


def test_strict_webm_flags_omit_mp4_faststart():
    cmd = build_ffmpeg_cmd(
        "ffmpeg",
        Path("in.webm"),
        Path("chapters.ffmeta"),
        Path("out.webm"),
        verify=VERIFY_STRICT,
    )
    joined = " ".join(cmd)
    assert "-movflags" not in cmd
    assert "faststart" not in joined
    assert "-sn" not in cmd
    assert "-dn" not in cmd


def test_read_container_chapters_injected_command():
    payload = {
        "chapters": [
            {
                "id": 0,
                "time_base": "1/1000",
                "start": 0,
                "start_time": "0.000000",
                "end": 1000,
                "end_time": "1.000000",
                "tags": {"title": "The \u201dguard\u201d"},
            }
        ]
    }

    def command(args: list[str]):
        assert args[0] == "ffprobe"
        assert "-show_chapters" in args
        return _ok(args, json.dumps(payload, ensure_ascii=False))

    path = Path("unused.mp4")
    chapters = read_container_chapters(path, command=command)
    assert chapter_count(path, "ffprobe", command=command) == 1
    assert chapter_titles(path, "ffprobe", command=command) == ["The \u201dguard\u201d"]
    assert chapters == [{"title": "The \u201dguard\u201d", "start": 0.0, "end": 1.0}]


def test_organize_remux_defaults_to_count_verify(tmp_path: Path):
    from bjj_pipeline.organizer.chapters import remux_with_chapters

    source = tmp_path / "vol.mp4"
    dest = tmp_path / "out.mp4"
    source.write_bytes(b"src")
    after = {"chapters": [INTRO]}

    def command(args: list[str]):
        if args[0] == "ffmpeg":
            Path(args[-1]).write_bytes(b"remuxed")
            return _ok(args)
        if "format=duration" in args:
            return _ok(args, "10.000\n")
        return _ok(args, json.dumps(after))

    remux_with_chapters(
        source,
        dest,
        [Chapter("Intro", 0), Chapter("Drills", 5_000)],
        "ffmpeg",
        "ffprobe",
        mov_faststart=True,
        command=command,
    )
    assert dest.read_bytes() == b"remuxed"


def test_apply_chapters_uses_strict_verify(tmp_path: Path):
    from bjj_pipeline import generate_chapters

    video = tmp_path / "Vol1.mp4"
    video.write_bytes(b"src")
    video.with_name("Vol1_chapters.csv").write_text(
        "Chapter,StartTimestamp,EndTimestamp\nChapter 1,00:00:00.000,00:00:10.000\n",
        encoding="utf-8",
    )
    video.with_name("Vol1_chapternames.csv").write_text(
        "Volume,Chapter\nVol1,Intro\n",
        encoding="utf-8",
    )
    after = _media()
    command, calls = _stub(tmp_path, after=after)
    generate_chapters.apply_chapters(video, command=command)
    assert video.read_bytes() == b"remuxed"
    ffmpeg_cmd = next(c for c in calls if Path(c[0]).name.lower().startswith("ffmpeg"))
    joined = " ".join(ffmpeg_cmd)
    assert "faststart" not in joined
    assert "-dn" not in ffmpeg_cmd


def test_organize_remux_count_failure_leaves_source(tmp_path: Path):
    from bjj_pipeline.organizer.chapters import remux_with_chapters

    source = tmp_path / "vol.mp4"
    dest = tmp_path / "out.mp4"
    source.write_bytes(b"src")

    def command(args: list[str]):
        if args[0] == "ffmpeg":
            Path(args[-1]).write_bytes(b"remuxed")
            return _ok(args)
        if "format=duration" in args:
            return _ok(args, "10.000\n")
        return _ok(args, json.dumps({"chapters": []}))

    with pytest.raises(FfmpegError, match="no chapters"):
        remux_with_chapters(
            source,
            dest,
            [Chapter("Intro", 0), Chapter("Drills", 5_000)],
            "ffmpeg",
            "ffprobe",
            mov_faststart=True,
            command=command,
        )
    assert source.read_bytes() == b"src"
    assert not dest.exists()
