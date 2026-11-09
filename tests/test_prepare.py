"""Prepare nests raw chapter speech onto a transcribed volume JSON."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

from bjj_pipeline.prepare import prepare_volume

SHOW = "Arm Bars Enter The System by John Danaher"
VOLUME = "Arm Bars Enter The System by John Danaher - S01E01 - Volume 1.mp4"
SEGMENTS = [
    {"start": 10.0, "end": 20.0, "text": "in guard"},
    {"start": 290.0, "end": 310.0, "text": "straddling the start"},
    {"start": 300.0, "end": 320.0, "text": "at the pass"},
    {"start": 400.0, "end": 410.0, "text": "in pass"},
    {"start": 900.0, "end": 910.0, "text": "after chapters"},
]


def _write_volume(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _two_chapter_payload() -> dict:
    return {
        "video_file": VOLUME,
        "chapters": [
            {"title": "Guard", "start": 0.0, "end": 300.0},
            {"title": "Pass", "start": 300.0, "end": 600.0},
        ],
        "language": "en",
        "segments": list(SEGMENTS),
    }


def test_prepare_overwrites_in_place_and_copies_overlapping_span(tmp_path: Path):
    corpus = tmp_path / "corpus"
    json_path = corpus / SHOW / "Season 01" / "vol.json"
    _write_volume(json_path, _two_chapter_payload())

    prepare_volume(json_path, corpus)

    assert list(corpus.rglob("*.json")) == [json_path]
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["segments"] == SEGMENTS
    guard, passing = data["chapters"]
    assert "<290.00>" in guard["transcript_raw"]
    assert "<290.00>" in passing["transcript_raw"]
    assert "straddling the start" in guard["transcript_raw"]
    assert "straddling the start" in passing["transcript_raw"]
    assert "<300.00>" in guard["transcript_raw"]
    assert "<300.00>" in passing["transcript_raw"]
    assert "after chapters" not in guard["transcript_raw"]
    assert "after chapters" not in passing["transcript_raw"]
    assert data["segments"][4]["text"] == "after chapters"
    assert "transcript_cleaned" not in guard
    assert "suggested_tags" not in guard


def test_empty_previous_on_first_and_empty_next_on_last(tmp_path: Path):
    corpus = tmp_path / "corpus"
    json_path = corpus / SHOW / "Season 01" / "vol.json"
    _write_volume(json_path, _two_chapter_payload())

    prepare_volume(json_path, corpus)

    data = json.loads(json_path.read_text(encoding="utf-8"))
    guard, passing = data["chapters"]
    assert guard["previous_chapter"] == ""
    assert guard["next_chapter"] == "Pass"
    assert passing["previous_chapter"] == "Guard"
    assert passing["next_chapter"] == ""


def test_credits_from_show_folder_and_video_file(tmp_path: Path):
    corpus = tmp_path / "corpus"
    json_path = corpus / SHOW / "Season 01" / "vol.json"
    _write_volume(json_path, _two_chapter_payload())

    prepare_volume(json_path, corpus)

    data = json.loads(json_path.read_text(encoding="utf-8"))
    for chapter in data["chapters"]:
        assert chapter["instructor"] == "John Danaher"
        assert chapter["instructional"] == SHOW
        assert chapter["volume"] == VOLUME


def test_instructor_from_nfo_director_when_library_show_exists(tmp_path: Path):
    corpus = tmp_path / "corpus"
    library = tmp_path / "library"
    show = "Arm Bars Enter The System by Wrong Name"
    json_path = corpus / show / "Season 01" / "vol.json"
    payload = _two_chapter_payload()
    payload["video_file"] = "Arm Bars.mp4"
    _write_volume(json_path, payload)
    nfo = library / show / "tvshow.nfo"
    nfo.parent.mkdir(parents=True)
    nfo.write_text(
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        "<tvshow>\n"
        "  <director>John Danaher</director>\n"
        "  <actor><name>Someone Else</name></actor>\n"
        "</tvshow>\n",
        encoding="utf-8",
    )

    prepare_volume(json_path, corpus, library)

    chapter = json.loads(json_path.read_text(encoding="utf-8"))["chapters"][0]
    assert chapter["instructor"] == "John Danaher"
    assert chapter["instructional"] == show
    assert chapter["volume"] == "Arm Bars.mp4"


def test_instructor_from_nfo_actor_when_director_missing(tmp_path: Path):
    corpus = tmp_path / "corpus"
    library = tmp_path / "library"
    show = "Half Guard Anthology"
    json_path = corpus / show / "vol.json"
    payload = _two_chapter_payload()
    payload["video_file"] = "Half Guard.mp4"
    _write_volume(json_path, payload)
    nfo = library / show / "tvshow.nfo"
    nfo.parent.mkdir(parents=True)
    nfo.write_text(
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        "<tvshow>\n"
        "  <actor><name>Lachlan Giles</name></actor>\n"
        "</tvshow>\n",
        encoding="utf-8",
    )

    prepare_volume(json_path, corpus, library)

    chapter = json.loads(json_path.read_text(encoding="utf-8"))["chapters"][0]
    assert chapter["instructor"] == "Lachlan Giles"
    assert chapter["instructional"] == show


def test_instructor_empty_without_nfo_or_by_suffix(tmp_path: Path):
    corpus = tmp_path / "corpus"
    show = "Uncredited Instructional"
    json_path = corpus / show / "vol.json"
    _write_volume(json_path, _two_chapter_payload())

    prepare_volume(json_path, corpus)

    chapter = json.loads(json_path.read_text(encoding="utf-8"))["chapters"][0]
    assert chapter["instructor"] == ""
    assert chapter["instructional"] == show


def test_empty_chapters_leave_file_unchanged(tmp_path: Path):
    corpus = tmp_path / "corpus"
    json_path = corpus / SHOW / "Season 01" / "vol.json"
    payload = _two_chapter_payload()
    payload["chapters"] = []
    _write_volume(json_path, payload)
    before = json_path.read_bytes()

    prepare_volume(json_path, corpus)

    assert json_path.read_bytes() == before


def test_missing_chapters_leave_file_unchanged(tmp_path: Path):
    corpus = tmp_path / "corpus"
    json_path = corpus / SHOW / "Season 01" / "vol.json"
    payload = _two_chapter_payload()
    del payload["chapters"]
    _write_volume(json_path, payload)
    before = json_path.read_bytes()

    prepare_volume(json_path, corpus)

    assert json_path.read_bytes() == before


def test_one_chapter_covering_whole_recording_leave_file_unchanged(tmp_path: Path):
    corpus = tmp_path / "corpus"
    json_path = corpus / SHOW / "Season 01" / "vol.json"
    payload = {
        "video_file": VOLUME,
        "chapters": [{"title": "Volume 1", "start": 0.0, "end": 1000.0}],
        "language": "en",
        "segments": list(SEGMENTS),
    }
    _write_volume(json_path, payload)
    before = json_path.read_bytes()

    prepare_volume(json_path, corpus)

    assert json_path.read_bytes() == before


def test_one_partial_chapter_leave_file_unchanged(tmp_path: Path):
    corpus = tmp_path / "corpus"
    json_path = corpus / SHOW / "Season 01" / "vol.json"
    payload = {
        "video_file": VOLUME,
        "chapters": [{"title": "Intro", "start": 0.0, "end": 30.0}],
        "language": "en",
        "segments": list(SEGMENTS),
    }
    _write_volume(json_path, payload)
    before = json_path.read_bytes()

    prepare_volume(json_path, corpus)

    assert json_path.read_bytes() == before


def test_two_chapters_one_untitled_leave_file_unchanged(tmp_path: Path):
    corpus = tmp_path / "corpus"
    json_path = corpus / SHOW / "Season 01" / "vol.json"
    payload = _two_chapter_payload()
    payload["chapters"][1]["title"] = "  "
    _write_volume(json_path, payload)
    before = json_path.read_bytes()

    prepare_volume(json_path, corpus)

    assert json_path.read_bytes() == before


def test_prepare_accepts_injected_completer():
    params = inspect.signature(prepare_volume).parameters
    assert list(params)[:4] == [
        "json_path",
        "corpus_root",
        "video_library_root",
        "completer",
    ]


VALID_HOP = {
    "start_position": "closed-guard",
    "start_occupancy": "bottom",
    "move_type": "submission",
    "end": "armbar",
    "end_occupancy": "",
    "named_move": "Armbar from closed guard",
    "ruleset": "both",
}

PARE_JSON = json.dumps(
    {
        "transcript_cleaned": "pared guard",
        "suggested_tags": [
            {**VALID_HOP, "system": "not-a-field"},
            {**VALID_HOP, "named_move": "not-a-real-move"},
            {**VALID_HOP, "start_occupancy": "side"},
            {**VALID_HOP, "end_occupancy": "top"},
        ],
    }
)


def _named_moves_from_prompt(prompt: str) -> list[str]:
    start = prompt.index("NAMED_MOVES:\n") + len("NAMED_MOVES:\n")
    end = prompt.index("\nEND_NAMED_MOVES")
    block = prompt[start:end].strip()
    names = []
    for line in block.splitlines():
        names.append(line[2:] if line.startswith("- ") else line)
    return names


def test_fake_completer_writes_cleaned_keys_and_keeps_overlap(tmp_path: Path):
    corpus = tmp_path / "corpus"
    json_path = corpus / SHOW / "Season 01" / "vol.json"
    _write_volume(json_path, _two_chapter_payload())
    prompts: list[str] = []

    def completer(prompt: str) -> str:
        prompts.append(prompt)
        return PARE_JSON

    code = prepare_volume(json_path, corpus, completer=completer)

    assert code == 0
    assert len(prompts) == 2
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["segments"] == SEGMENTS
    guard, passing = data["chapters"]
    assert "<290.00>" in guard["transcript_raw"]
    assert "<290.00>" in passing["transcript_raw"]
    assert "straddling the start" in guard["transcript_raw"]
    assert "straddling the start" in passing["transcript_raw"]
    assert guard["transcript_cleaned"] == "pared guard"
    assert passing["transcript_cleaned"] == "pared guard"
    assert guard["suggested_tags"] == [VALID_HOP]
    assert passing["suggested_tags"] == [VALID_HOP]
    assert "system" not in guard["suggested_tags"][0]
    prompt = prompts[0]
    assert "- takedown (Takedown)" in prompt
    assert "- closed-guard (Closed guard)" in prompt
    assert "- armbar (Armbar)" in prompt
    assert "Keep chapter titles and names already used in this volume's speech" in prompt
    assert "Occupancy: top, bottom, neutral" in prompt or "Occupancy:" in prompt


def test_completer_down_keeps_raw_omits_cleaned(tmp_path: Path):
    corpus = tmp_path / "corpus"
    json_path = corpus / SHOW / "Season 01" / "vol.json"
    _write_volume(json_path, _two_chapter_payload())

    def down(_prompt: str) -> str:
        raise OSError("connection refused")

    code = prepare_volume(json_path, corpus, completer=down)

    assert code == 1
    data = json.loads(json_path.read_text(encoding="utf-8"))
    guard, passing = data["chapters"]
    assert "<290.00>" in guard["transcript_raw"]
    assert "<290.00>" in passing["transcript_raw"]
    assert "transcript_cleaned" not in guard
    assert "transcript_cleaned" not in passing
    assert "suggested_tags" not in guard
    assert "suggested_tags" not in passing


def test_unusable_completion_omits_cleaned_keys(tmp_path: Path):
    corpus = tmp_path / "corpus"
    json_path = corpus / SHOW / "Season 01" / "vol.json"
    _write_volume(json_path, _two_chapter_payload())

    def junk(_prompt: str) -> str:
        return "not json"

    code = prepare_volume(json_path, corpus, completer=junk)

    assert code == 1
    guard = json.loads(json_path.read_text(encoding="utf-8"))["chapters"][0]
    assert "transcript_raw" in guard
    assert "transcript_cleaned" not in guard
    assert "suggested_tags" not in guard


def test_windowed_chapter_stitches_text_and_dedupes_hops(tmp_path: Path):
    corpus = tmp_path / "corpus"
    json_path = corpus / SHOW / "Season 01" / "vol.json"
    spans = [
        {"start": float(index * 10), "end": float(index * 10 + 5), "text": f"span {index}"}
        for index in range(6)
    ]
    payload = {
        "video_file": VOLUME,
        "chapters": [
            {"title": "Guard", "start": 0.0, "end": 100.0},
            {"title": "Pass", "start": 100.0, "end": 200.0},
        ],
        "language": "en",
        "segments": spans
        + [{"start": 120.0, "end": 130.0, "text": "later pass"}],
    }
    _write_volume(json_path, payload)
    prompts: list[str] = []

    def completer(prompt: str) -> str:
        prompts.append(prompt)
        n = len(prompts)
        return json.dumps(
            {
                "transcript_cleaned": f"window {n}",
                "suggested_tags": [VALID_HOP, VALID_HOP],
            }
        )

    code = prepare_volume(json_path, corpus, completer=completer)

    assert code == 0
    assert len(prompts) == 3
    assert "<30.00>" in prompts[0]
    assert "<30.00>" in prompts[1]
    assert "<40.00>" not in prompts[0]
    assert "<0.00>" not in prompts[1]
    assert "Chapter speech:" in prompts[0]
    assert "Context (do not repeat):" not in prompts[0]
    assert "Context (do not repeat):" in prompts[1]
    assert "Pare only this speech:" in prompts[1]
    data = json.loads(json_path.read_text(encoding="utf-8"))
    guard, passing = data["chapters"]
    assert guard["transcript_cleaned"] == "window 1 window 2"
    assert passing["transcript_cleaned"] == "window 3"
    assert guard["suggested_tags"] == [VALID_HOP]


def test_specific_title_sends_short_named_move_list(tmp_path: Path):
    corpus = tmp_path / "corpus"
    json_path = corpus / SHOW / "Season 01" / "vol.json"
    payload = _two_chapter_payload()
    payload["chapters"][0]["title"] = "Hip bump sweep"
    payload["chapters"][1]["title"] = "Hip bump sweep"
    _write_volume(json_path, payload)
    prompts: list[str] = []

    def completer(prompt: str) -> str:
        prompts.append(prompt)
        return json.dumps({"transcript_cleaned": "pared", "suggested_tags": []})

    prepare_volume(json_path, corpus, completer=completer)

    names = _named_moves_from_prompt(prompts[0])
    assert "Hip bump sweep" in names
    assert "Rear naked choke" not in names
    assert len(names) >= 5


def test_vague_title_sends_full_named_move_list(tmp_path: Path):
    corpus = tmp_path / "corpus"
    json_path = corpus / SHOW / "Season 01" / "vol.json"
    payload = _two_chapter_payload()
    payload["chapters"][0]["title"] = "Volume 1"
    payload["chapters"][1]["title"] = "Volume 2"
    _write_volume(json_path, payload)
    prompts: list[str] = []

    def completer(prompt: str) -> str:
        prompts.append(prompt)
        return json.dumps({"transcript_cleaned": "pared", "suggested_tags": []})

    prepare_volume(json_path, corpus, completer=completer)

    names = _named_moves_from_prompt(prompts[0])
    seed = json.loads(
        (
            Path(__file__).resolve().parents[1]
            / "docs"
            / "enrichment-seed"
            / "seed.json"
        ).read_text(encoding="utf-8")
    )
    full = []
    seen: set[str] = set()
    for path in seed["paths"]:
        for leaf in path["leaves"]:
            name = leaf["name"]
            if name not in seen:
                seen.add(name)
                full.append(name)
    assert names == full
    assert "Rear naked choke" in names
    assert "Hip bump sweep" in names


def test_complete_chat_posts_openai_body(monkeypatch):
    from bjj_pipeline.prepare import DEFAULT_LLM_MODEL, complete_chat

    recorded: dict = {}

    class FakeResponse:
        def read(self):
            return json.dumps(
                {"choices": [{"message": {"content": "pared json"}}]}
            ).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_urlopen(req, timeout=None):
        recorded["url"] = req.full_url
        recorded["body"] = json.loads(req.data.decode("utf-8"))
        recorded["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setenv("BJJ_LLM_BASE_URL", "http://example.test/v1")
    monkeypatch.setenv("BJJ_LLM_MODEL", "qwen-test")
    text = complete_chat("pare this", urlopen=fake_urlopen)

    assert text == "pared json"
    assert recorded["url"] == "http://example.test/v1/chat/completions"
    assert recorded["body"]["model"] == "qwen-test"
    assert recorded["body"]["messages"] == [{"role": "user", "content": "pare this"}]
    assert recorded["body"]["temperature"] == 0
    assert recorded["body"]["reasoning_effort"] == "none"
    assert recorded["body"]["response_format"] == {"type": "json_object"}
    assert recorded["body"]["options"] == {"num_ctx": 2048}

    monkeypatch.delenv("BJJ_LLM_BASE_URL")
    monkeypatch.delenv("BJJ_LLM_MODEL")
    complete_chat("again", urlopen=fake_urlopen)
    assert recorded["url"] == "http://localhost:11434/v1/chat/completions"
    assert recorded["body"]["model"] == DEFAULT_LLM_MODEL
    assert DEFAULT_LLM_MODEL == "qwen3.5:4b"
