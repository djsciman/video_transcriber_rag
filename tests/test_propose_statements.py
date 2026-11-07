"""Propose cleaned statements from a cleaned volume. Nothing enters the store."""

import inspect

from coach_app.cleanup import cleanup_volume
from coach_app.statements import StatementDrafter, propose_statements
from coach_app.store import CuratedStore


class RecordingAdvisor:
    """Stand-in collaborator. Records drafts; does not name a vendor."""

    def __init__(self):
        self.calls = []

    def draft(self, *, part, movement, instructor, volume):
        self.calls.append(
            {
                "title": part["title"],
                "movement": movement,
                "instructor": instructor,
            }
        )
        return {
            "movement": movement,
            "instructor": instructor,
            "chapter": part["title"],
            "cleaned_statement": " ".join(span["text"] for span in part["speech"]),
            "step_bullets": tuple(span["text"] for span in part["speech"]),
            "details": tuple(
                {"text": span["text"], "speech_start": span["start"]}
                for span in part["speech"]
            ),
        }


def test_one_movement_chapter_of_at_least_one_minute_yields_one_statement():
    cleaned = cleanup_volume(
        {
            "video_file": "Closed Guard.mp4",
            "chapters": [
                {"title": "Closed Guard", "start": 0.0, "end": 120.0},
                {"title": "Arm Bar", "start": 120.0, "end": 240.0},
            ],
            "segments": [
                {
                    "start": 10.0,
                    "end": 14.0,
                    "text": "from closed guard",
                    "source": "SPEECH",
                },
                {
                    "start": 40.0,
                    "end": 50.0,
                    "text": (
                        "your inside arm shoots the underhook under their inside arm"
                    ),
                    "source": "SPEECH",
                },
                {
                    "start": 130.0,
                    "end": 140.0,
                    "text": "break the grip and finish the arm bar",
                    "source": "SPEECH",
                },
            ],
        }
    )
    advisor = RecordingAdvisor()

    proposals = propose_statements(
        cleaned, advisor, instructor="John Danaher"
    )

    closed = [item for item in proposals if item["chapter"] == "Closed Guard"]
    assert len(closed) == 1
    statement = closed[0]
    assert statement["movement"] == "Closed Guard"
    assert statement["instructor"] == "John Danaher"
    assert statement["chapter"] == "Closed Guard"
    assert advisor.calls[0]["title"] == "Closed Guard"


def test_short_intro_outro_and_named_roll_yield_no_statement():
    cleaned = cleanup_volume(
        {
            "video_file": "Volume 1.mp4",
            "chapters": [
                {"title": "Intro", "start": 0.0, "end": 90.0},
                {"title": "Hip Bump Sweep", "start": 90.0, "end": 140.0},
                {"title": "Outro", "start": 140.0, "end": 220.0},
                {"title": "Narrated Rolling", "start": 220.0, "end": 400.0},
                {"title": "Named Roll", "start": 400.0, "end": 500.0},
            ],
            "segments": [
                {"start": 10.0, "end": 20.0, "text": "welcome", "source": "SPEECH"},
                {
                    "start": 100.0,
                    "end": 110.0,
                    "text": "sit up for the hip bump",
                    "source": "SPEECH",
                },
                {"start": 150.0, "end": 160.0, "text": "thanks for watching", "source": "SPEECH"},
                {"start": 230.0, "end": 240.0, "text": "we roll now", "source": "SPEECH"},
                {"start": 410.0, "end": 420.0, "text": "named rolling", "source": "SPEECH"},
            ],
        }
    )
    advisor = RecordingAdvisor()

    proposals = propose_statements(
        cleaned, advisor, instructor="Ryan Hall"
    )

    assert proposals == []
    assert advisor.calls == []


def test_multi_idea_chapter_title_yields_one_statement_per_movement():
    cleaned = cleanup_volume(
        {
            "video_file": "Volume 2.mp4",
            "chapters": [
                {"title": "Kimura and Guillotine", "start": 0.0, "end": 180.0},
                {"title": "Closed Guard", "start": 180.0, "end": 300.0},
            ],
            "segments": [
                {
                    "start": 10.0,
                    "end": 20.0,
                    "text": "catch the kimura from here",
                    "source": "SPEECH",
                },
                {
                    "start": 80.0,
                    "end": 90.0,
                    "text": "now the guillotine finish",
                    "source": "SPEECH",
                },
                {
                    "start": 200.0,
                    "end": 210.0,
                    "text": "from closed guard",
                    "source": "SPEECH",
                },
            ],
        }
    )
    advisor = RecordingAdvisor()

    proposals = propose_statements(
        cleaned, advisor, instructor="Lachlan Giles"
    )

    kimura_chapter = [
        item for item in proposals if item["chapter"] == "Kimura and Guillotine"
    ]
    assert [item["movement"] for item in kimura_chapter] == ["Kimura", "Guillotine"]
    assert advisor.calls[0]["movement"] == "Kimura"
    assert advisor.calls[1]["movement"] == "Guillotine"


def test_restores_terms_collapses_false_starts_keeps_cues_and_house_spellings():
    cleaned = cleanup_volume(
        {
            "video_file": "Closed Guard.mp4",
            "chapters": [
                {"title": "Closed Guard", "start": 0.0, "end": 120.0},
                {"title": "Arm Bar", "start": 120.0, "end": 240.0},
            ],
            "segments": [
                {
                    "start": 10.0,
                    "end": 14.0,
                    "text": "set the overclass",
                    "source": "SPEECH",
                },
                {
                    "start": 20.0,
                    "end": 25.0,
                    "text": "the overclasp grips here",
                    "source": "SPEECH",
                },
                {
                    "start": 30.0,
                    "end": 35.0,
                    "text": "underclasps, sorry, overclasps just like so",
                    "source": "SPEECH",
                },
                {
                    "start": 130.0,
                    "end": 140.0,
                    "text": "finish with the choy bar",
                    "source": "SPEECH",
                },
                {
                    "start": 150.0,
                    "end": 160.0,
                    "text": "choy bar again",
                    "source": "SPEECH",
                },
            ],
        }
    )

    proposals = propose_statements(
        cleaned, StatementDrafter(), instructor="John Danaher"
    )

    closed = next(item for item in proposals if item["chapter"] == "Closed Guard")
    closed_text = closed["cleaned_statement"]
    assert "overclasp" in closed_text
    assert "overclass" not in closed_text
    assert "underclasps" not in closed_text
    assert "just like so" in closed_text

    arm = next(item for item in proposals if item["chapter"] == "Arm Bar")
    assert "choy bar" in arm["cleaned_statement"]
    assert "choi" not in arm["cleaned_statement"].casefold()


def test_spoken_details_gather_across_showings_with_timestamps_shown_only_omitted():
    cleaned = cleanup_volume(
        {
            "video_file": "Half Guard.mp4",
            "chapters": [
                {"title": "Knee Cut", "start": 0.0, "end": 180.0},
                {"title": "Frame", "start": 180.0, "end": 300.0},
            ],
            "segments": [
                {
                    "start": 12.5,
                    "end": 20.0,
                    "text": "frame the far hip",
                    "source": "SPEECH",
                },
                {
                    "start": 40.0,
                    "end": 48.0,
                    "text": "just like so",
                    "source": "SPEECH",
                },
                {
                    "start": 90.0,
                    "end": 100.0,
                    "text": "cut the knee to mount",
                    "source": "SPEECH",
                },
                {
                    "start": 200.0,
                    "end": 210.0,
                    "text": "build the frame",
                    "source": "SPEECH",
                },
            ],
        }
    )

    proposal = next(
        item
        for item in propose_statements(
            cleaned, StatementDrafter(), instructor="John Danaher"
        )
        if item["chapter"] == "Knee Cut"
    )

    starts = [detail["speech_start"] for detail in proposal["details"]]
    texts = [detail["text"] for detail in proposal["details"]]
    assert 12.5 in starts
    assert 90.0 in starts
    assert "frame the far hip" in texts
    assert "cut the knee to mount" in texts
    assert "hip shift" not in proposal["cleaned_statement"]
    for detail in proposal["details"]:
        assert "speech_start" in detail


def test_step_bullets_use_inside_outside_and_name_body_parts():
    cleaned = cleanup_volume(
        {
            "video_file": "Half Guard Passing.mp4",
            "chapters": [
                {"title": "Underhook", "start": 0.0, "end": 120.0},
                {"title": "Knee Cut", "start": 120.0, "end": 240.0},
            ],
            "segments": [
                {
                    "start": 10.0,
                    "end": 25.0,
                    "text": (
                        "in half guard your arm toward the entangled legs "
                        "shoots the underhook under their arm toward the legs"
                    ),
                    "source": "SPEECH",
                },
                {
                    "start": 40.0,
                    "end": 55.0,
                    "text": (
                        "your arm away from the entangled legs blocks their "
                        "arm away from the legs from the crossface"
                    ),
                    "source": "SPEECH",
                },
                {
                    "start": 130.0,
                    "end": 140.0,
                    "text": "cut the knee",
                    "source": "SPEECH",
                },
            ],
        }
    )

    proposal = next(
        item
        for item in propose_statements(
            cleaned, StatementDrafter(), instructor="John Danaher"
        )
        if item["chapter"] == "Underhook"
    )

    bullets = proposal["step_bullets"]
    assert any(
        "inside arm" in bullet
        and "shoots" in bullet
        and "their inside arm" in bullet
        for bullet in bullets
    )
    assert any(
        "outside arm" in bullet
        and "blocks" in bullet
        and "their outside arm" in bullet
        for bullet in bullets
    )


def test_untitled_part_proposes_nothing_until_marks_pass_the_bar():
    cleaned = cleanup_volume(
        {
            "video_file": "Volume 8.mp4",
            "chapters": [
                {
                    "title": "11 Z GUARD, KIMURA, AND NARRATED ROLLING",
                    "start": 0.0,
                    "end": 9581.0,
                }
            ],
            "segments": [
                {"start": 3.0, "end": 8.0, "text": "Zeg guard", "source": "SPEECH"},
                {
                    "start": 70.0,
                    "end": 80.0,
                    "text": "stay in Z-guard",
                    "source": "SPEECH",
                },
                {
                    "start": 200.0,
                    "end": 210.0,
                    "text": "choy bar finish",
                    "source": "SPEECH",
                },
            ],
        }
    )
    advisor = RecordingAdvisor()

    assert propose_statements(cleaned, advisor, instructor="Lachlan Giles") == []
    assert advisor.calls == []

    marks = [
        {"title": "Z-guard", "start": 0.0, "end": 120.0},
        {"title": "Intro", "start": 120.0, "end": 200.0},
        {"title": "Kimura", "start": 200.0, "end": 230.0},
    ]
    proposals = propose_statements(
        cleaned, advisor, instructor="Lachlan Giles", marks=marks
    )

    assert [item["movement"] for item in proposals] == ["Z-guard"]
    assert proposals[0]["chapter"] == "Z-guard"
    assert advisor.calls == [
        {
            "title": "Z-guard",
            "movement": "Z-guard",
            "instructor": "Lachlan Giles",
        }
    ]


def test_rejecting_or_ignoring_a_proposal_stores_nothing():
    cleaned = cleanup_volume(
        {
            "video_file": "Closed Guard.mp4",
            "chapters": [
                {"title": "Closed Guard", "start": 0.0, "end": 120.0},
                {"title": "Arm Bar", "start": 120.0, "end": 240.0},
            ],
            "segments": [
                {
                    "start": 10.0,
                    "end": 14.0,
                    "text": "from closed guard",
                    "source": "SPEECH",
                },
            ],
        }
    )
    store = CuratedStore()

    proposals = propose_statements(
        cleaned, RecordingAdvisor(), instructor="John Danaher"
    )

    assert proposals
    assert "store" not in inspect.signature(propose_statements).parameters
    assert store.citations() == ()
    assert store.volumes() == ()
    assert store.instructionals() == ()
