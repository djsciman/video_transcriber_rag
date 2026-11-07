"""Accept, correct, and remove citations. Playback resolves at open time."""

from __future__ import annotations

import inspect

from coach_app.cleanup import cleanup_volume
from coach_app.statements import StatementDrafter, propose_statements
from coach_app.store import CuratedStore, Instructional, Volume


LOCKED_NO_GI = (
    "Finishing Leg Locks",
    "Master The Move Arm Drags",
    "Master The Move The Side Crucifix",
    "Jay Rods Judo",
)
LOCKED_GI = (
    "Half Guard Passing and Dynamic Pins",
    "Mastering The Knee Weave System",
)


class CatalogAdvisor:
    """Stand-in that reads accepted citations. Does not name a vendor."""

    def from_store(self, store: CuratedStore):
        return store.citations()


def _closed_guard_volume():
    return {
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
                "start": 40.0,
                "end": 48.0,
                "text": "just like so",
                "source": "SPEECH",
            },
            {
                "start": 130.0,
                "end": 140.0,
                "text": "finish with the choy bar",
                "source": "SPEECH",
            },
        ],
    }


def _knee_cut_volume():
    return {
        "video_file": "Half Guard Passing and Dynamic Pins - Volume 1.mp4",
        "chapters": [
            {"title": "The knee cut", "start": 0.0, "end": 180.0},
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


def _proposal_for(raw, *, instructor="John Danaher", chapter=None):
    cleaned = cleanup_volume(raw)
    proposals = propose_statements(
        cleaned, StatementDrafter(), instructor=instructor
    )
    if chapter is None:
        return cleaned, proposals[0]
    return cleaned, next(item for item in proposals if item["chapter"] == chapter)


def test_accept_writes_instructional_volume_and_citation():
    store = CuratedStore()
    cleaned, proposal = _proposal_for(
        _knee_cut_volume(), chapter="The knee cut"
    )

    citation = store.accept(
        proposal,
        instructional="Half Guard Passing and Dynamic Pins",
        video_file=cleaned["video_file"],
    )

    assert store.instructionals() == (
        Instructional(
            instructor="John Danaher",
            name="Half Guard Passing and Dynamic Pins",
            ruleset="gi",
        ),
    )
    assert store.volumes() == (
        Volume(
            instructional="Half Guard Passing and Dynamic Pins",
            video_file_name="Half Guard Passing and Dynamic Pins - Volume 1.mp4",
        ),
    )
    assert store.citations() == (citation,)
    assert citation.movement == "The knee cut"
    assert citation.instructor == "John Danaher"
    assert citation.instructional == "Half Guard Passing and Dynamic Pins"
    assert citation.volume == "Half Guard Passing and Dynamic Pins - Volume 1.mp4"
    assert citation.chapter == "The knee cut"
    assert "frame the far hip" in (citation.cleaned_statement or "")
    assert citation.step_bullets
    assert citation.showings
    assert citation.showings[0].timestamp == 12.5
    assert citation.id
    assert store.citation(citation.id) == citation


def test_not_accepting_writes_nothing():
    store = CuratedStore()
    cleaned, proposal = _proposal_for(_closed_guard_volume(), chapter="Closed Guard")

    store.correct(proposal, movement="Overclasp")

    assert proposal
    assert cleaned["video_file"] == "Closed Guard.mp4"
    assert store.instructionals() == ()
    assert store.volumes() == ()
    assert store.citations() == ()
    assert CatalogAdvisor().from_store(store) == ()


def test_correct_before_accept_changes_the_stored_statement():
    store = CuratedStore()
    cleaned, proposal = _proposal_for(_knee_cut_volume(), chapter="The knee cut")

    draft = store.correct(
        proposal,
        movement="Knee slice",
        step_bullets=("Frame the far hip.", "Cut the knee to mount."),
    )
    assert store.citations() == ()

    citation = store.accept(
        draft,
        instructional="Half Guard Passing and Dynamic Pins",
        video_file=cleaned["video_file"],
    )

    assert citation.movement == "Knee slice"
    assert citation.step_bullets == (
        "Frame the far hip.",
        "Cut the knee to mount.",
    )
    assert citation.cleaned_statement == "Frame the far hip. Cut the knee to mount."
    assert store.citations() == (citation,)


def test_correct_after_accept_replaces_statement_with_no_earlier_version():
    store = CuratedStore()
    cleaned, proposal = _proposal_for(_knee_cut_volume(), chapter="The knee cut")
    citation = store.accept(
        proposal,
        instructional="Half Guard Passing and Dynamic Pins",
        video_file=cleaned["video_file"],
    )
    original_id = citation.id
    original_showings = citation.showings
    original_instructor = citation.instructor
    original_instructional = citation.instructional
    original_volume = citation.volume
    original_chapter = citation.chapter

    updated = store.correct(
        citation,
        movement="Knee slice",
        step_bullets=(
            "Inside arm shoots the underhook under their inside arm.",
            "Outside arm blocks their outside arm from the crossface.",
        ),
    )

    assert updated.id == original_id
    assert store.citations() == (updated,)
    assert store.citation(original_id) == updated
    assert updated.movement == "Knee slice"
    assert updated.step_bullets[0].startswith("Inside arm")
    assert updated.instructor == original_instructor
    assert updated.instructional == original_instructional
    assert updated.volume == original_volume
    assert updated.chapter == original_chapter
    assert updated.showings == original_showings


def test_word_edit_leaves_provenance_and_playback_links():
    store = CuratedStore()
    cleaned, proposal = _proposal_for(_knee_cut_volume(), chapter="The knee cut")
    citation = store.accept(
        proposal,
        instructional="Half Guard Passing and Dynamic Pins",
        video_file=cleaned["video_file"],
    )
    links = tuple(showing.playback_link for showing in citation.showings)

    updated = store.correct(
        citation,
        step_bullets=("Frame the far hip and cut the knee.",),
    )

    assert updated.movement == citation.movement
    assert updated.instructor == citation.instructor
    assert updated.instructional == citation.instructional
    assert updated.volume == citation.volume
    assert updated.chapter == citation.chapter
    assert updated.showings == citation.showings
    assert tuple(showing.playback_link for showing in updated.showings) == links
    assert all(showing.playback_link for showing in updated.showings)


def test_movement_name_follows_a_move_name_edit():
    store = CuratedStore()
    cleaned, proposal = _proposal_for(_knee_cut_volume(), chapter="The knee cut")
    citation = store.accept(
        proposal,
        instructional="Half Guard Passing and Dynamic Pins",
        video_file=cleaned["video_file"],
    )

    updated = store.correct(citation, movement="Knee slice pass")

    assert updated.movement == "Knee slice pass"
    assert store.citation(citation.id).movement == "Knee slice pass"


def test_remove_drops_an_accepted_citation():
    store = CuratedStore()
    cleaned, proposal = _proposal_for(_knee_cut_volume(), chapter="The knee cut")
    citation = store.accept(
        proposal,
        instructional="Half Guard Passing and Dynamic Pins",
        video_file=cleaned["video_file"],
    )

    store.remove(citation)

    assert store.citations() == ()
    assert store.citation(citation.id) is None


def test_locked_instructionals_store_gi_or_no_gi_as_a_whole():
    store = CuratedStore()
    cleaned, proposal = _proposal_for(_closed_guard_volume(), chapter="Closed Guard")
    instructors = {
        "Finishing Leg Locks": "Jacob Couch",
        "Master The Move Arm Drags": "John Danaher",
        "Master The Move The Side Crucifix": "John Danaher",
        "Jay Rods Judo": "Jay Rodriguez",
        "Half Guard Passing and Dynamic Pins": "John Danaher",
        "Mastering The Knee Weave System": "John Danaher",
    }

    for name in LOCKED_NO_GI + LOCKED_GI:
        draft = dict(proposal)
        draft["instructor"] = instructors[name]
        store.accept(
            draft,
            instructional=name,
            video_file=f"{name} - Volume 1.mp4",
        )

    by_name = {item.name: item for item in store.instructionals()}
    for name in LOCKED_NO_GI:
        assert by_name[name].ruleset == "no-gi"
        assert by_name[name].instructor == instructors[name]
    for name in LOCKED_GI:
        assert by_name[name].ruleset == "gi"
        assert by_name[name].instructor == instructors[name]
    assert store.instructional("Master The Move by John Danaher") is None


def test_empty_danaher_folders_stay_out_until_volumes_arrive(tmp_path):
    store = CuratedStore()
    empty = tmp_path / "Standing2Ground Upper Body Takedowns by John Danaher"
    empty.mkdir()
    (empty / "notes.txt").write_text("no volumes yet", encoding="utf-8")

    assert store.instructionals() == ()
    assert store.volumes() == ()
    assert store.citations() == ()
    assert store.instructional(empty.name) is None

    cleaned, proposal = _proposal_for(_closed_guard_volume(), chapter="Closed Guard")
    store.accept(
        proposal,
        instructional="Master The Move Arm Drags",
        video_file=cleaned["video_file"],
    )

    assert [item.name for item in store.instructionals()] == [
        "Master The Move Arm Drags"
    ]
    assert store.instructional(empty.name) is None


def test_accepted_overclasp_is_usable_and_unnamed_hip_shift_stays_off():
    store = CuratedStore()
    cleaned, proposal = _proposal_for(_closed_guard_volume(), chapter="Closed Guard")
    assert "overclasp" in proposal["cleaned_statement"]
    assert "hip shift" not in proposal["cleaned_statement"]

    store.accept(
        proposal,
        instructional="Half Guard Passing and Dynamic Pins",
        video_file=cleaned["video_file"],
    )

    used = CatalogAdvisor().from_store(store)
    assert used
    text = " ".join(item.cleaned_statement or "" for item in used)
    assert "overclasp" in text
    assert "overclass" not in text
    assert "hip shift" not in text


def test_playback_resolves_video_path_and_speech_start(tmp_path):
    store = CuratedStore()
    cleaned, proposal = _proposal_for(_knee_cut_volume(), chapter="The knee cut")
    folder = tmp_path / "Half Guard Passing and Dynamic Pins"
    folder.mkdir()
    video = folder / cleaned["video_file"]
    video.write_bytes(b"")
    (folder / (video.stem + ".nfo")).write_text("ignore me", encoding="utf-8")
    (folder / (video.stem + ".json")).write_text("{}", encoding="utf-8")

    citation = store.accept(
        proposal,
        instructional="Half Guard Passing and Dynamic Pins",
        video_file=cleaned["video_file"],
    )
    playback = store.resolve_playback(
        citation,
        citation.showings[0],
        video_root=tmp_path,
        transcript_folder="Half Guard Passing and Dynamic Pins",
    )

    assert playback.path == video
    assert playback.speech_start == 12.5
    assert playback.available is True
    source = inspect.getsource(store.resolve_playback)
    assert "ffmpeg" not in source.casefold()
    assert "whisper" not in source.casefold()
    assert "vlc" not in source.casefold()
    assert "browser" not in source.casefold()


def test_missing_video_still_admits_the_citation(tmp_path):
    store = CuratedStore()
    cleaned, proposal = _proposal_for(_knee_cut_volume(), chapter="The knee cut")
    folder = tmp_path / "Half Guard Passing and Dynamic Pins"
    folder.mkdir()
    (folder / "Half Guard Passing and Dynamic Pins - Volume 1.nfo").write_text(
        "artwork only", encoding="utf-8"
    )

    citation = store.accept(
        proposal,
        instructional="Half Guard Passing and Dynamic Pins",
        video_file=cleaned["video_file"],
    )

    assert store.citation(citation.id) == citation
    playback = store.resolve_playback(
        citation,
        citation.showings[0],
        video_root=tmp_path,
        transcript_folder="Half Guard Passing and Dynamic Pins",
    )
    assert playback.speech_start == 12.5
    assert playback.available is False
    assert playback.path.name == cleaned["video_file"]
    assert store.citations() == (citation,)
