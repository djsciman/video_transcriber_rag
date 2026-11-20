"""Transcribe identity keeps extra chapter-speech keys through a later write."""

from __future__ import annotations

import json
from pathlib import Path

from bjj_pipeline import batch_panoscribe


def test_chapters_equal_ignores_extra_keys():
    stored = [
        {
            "title": "Guard",
            "start": 0.0,
            "end": 300.0,
            "transcript_raw": "<10.00> in guard",
            "instructor": "John Danaher",
        }
    ]
    container = [{"title": "Guard", "start": 0.0, "end": 300.0}]
    assert batch_panoscribe.chapters_equal(stored, container)


def test_matching_container_chapters_keep_extra_keys_on_speech_rewrite(tmp_path: Path):
    video = tmp_path / "Vol1.mp4"
    video.write_bytes(b"fake-video")
    dest = tmp_path / "Vol1.json"
    dest.write_text(
        json.dumps(
            {
                "video_file": "Vol1.mp4",
                "chapters": [
                    {
                        "title": "Guard",
                        "start": 0.0,
                        "end": 300.0,
                        "instructor": "John Danaher",
                        "instructional": "Arm Bars",
                        "volume": "Vol1.mp4",
                        "previous_chapter": "",
                        "next_chapter": "Pass",
                        "transcript_raw": "<10.00> in guard",
                    },
                    {
                        "title": "Pass",
                        "start": 300.0,
                        "end": 600.0,
                        "instructor": "John Danaher",
                        "instructional": "Arm Bars",
                        "volume": "Vol1.mp4",
                        "previous_chapter": "Guard",
                        "next_chapter": "",
                        "transcript_raw": "<290.00> straddling the start",
                    },
                ],
                "language": "en",
                "segments": [{"start": 0.0, "end": 1.0, "text": "old"}],
            }
        ),
        encoding="utf-8",
    )

    def speech(_video: Path, aside: Path, _hotwords: str | None, _ocr: bool) -> None:
        aside.write_text(
            json.dumps(
                {
                    "language": "en",
                    "segments": [{"start": 0.0, "end": 1.0, "text": "new speech"}],
                }
            ),
            encoding="utf-8",
        )

    def chapters(_video: Path) -> list:
        return [
            {"title": "Guard", "start": 0.0, "end": 300.0},
            {"title": "Pass", "start": 300.0, "end": 600.0},
        ]

    result = batch_panoscribe.process_volume(
        video,
        dest,
        ocr=False,
        force=True,
        speech_command=speech,
        chapter_command=chapters,
        count_hotword_tokens=lambda _text: 1,
    )

    assert result == "updated"
    data = json.loads(dest.read_text(encoding="utf-8"))
    assert data["segments"] == [{"start": 0.0, "end": 1.0, "text": "new speech"}]
    guard, passing = data["chapters"]
    assert guard["transcript_raw"] == "<10.00> in guard"
    assert passing["transcript_raw"] == "<290.00> straddling the start"
    assert guard["instructor"] == "John Danaher"
    assert guard["next_chapter"] == "Pass"
    assert passing["previous_chapter"] == "Guard"
    assert passing["next_chapter"] == ""
