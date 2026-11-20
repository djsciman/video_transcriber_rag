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
    assert "segments" not in data
    guard, passing = data["chapters"]
    assert "<290.00>" in guard["transcript_raw"]
    assert "<290.00>" in passing["transcript_raw"]
    assert "straddling the start" in guard["transcript_raw"]
    assert "straddling the start" in passing["transcript_raw"]
    assert "<300.00>" in guard["transcript_raw"]
    assert "<300.00>" in passing["transcript_raw"]
    assert "after chapters" not in guard["transcript_raw"]
    assert "after chapters" not in passing["transcript_raw"]
    assert "transcript_cleaned" not in guard
    assert "techniques" not in guard
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


EMPTY_PARE = json.dumps(
    {
        "transcript_cleaned": "pared guard",
        "concepts": ["Win the underhook before you bump."],
        "suggested_tags": ["underhook"],
        "techniques": [],
    }
)

STAR_TECHNIQUE = {
    "named_move": "2-on-1 sweep*",
    "ruleset": "no-gi",
    "move_type": "sweep",
    "start_occupancy": "bottom",
    "start_position": "butterfly-guard",
    "end_occupancy": "top",
    "end_position": "mount*",
    "technique_steps": "1. Butterfly guard, bottom: take the two-on-one.",
    "main_ideas": "Follow faster than you throw him so you finish on top.",
    "source_time_ranges": ["2248.00-2580.00"],
    "suggested_tags": ["two-on-one opposite arm"],
}


def test_fake_completer_writes_cleaned_and_empty_techniques(tmp_path: Path):
    corpus = tmp_path / "corpus"
    json_path = corpus / SHOW / "Season 01" / "vol.json"
    _write_volume(json_path, _two_chapter_payload())
    prompts: list[str] = []

    def completer(prompt: str) -> str:
        prompts.append(prompt)
        return EMPTY_PARE

    code = prepare_volume(json_path, corpus, completer=completer)

    assert code == 0
    assert len(prompts) == 2
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert "segments" not in data
    guard, passing = data["chapters"]
    assert "<290.00>" in guard["transcript_raw"]
    assert "<290.00>" in passing["transcript_raw"]
    assert "straddling the start" in guard["transcript_raw"]
    assert "straddling the start" in passing["transcript_raw"]
    assert guard["transcript_cleaned"] == "pared guard"
    assert passing["transcript_cleaned"] == "pared guard"
    assert guard["techniques"] == []
    assert passing["techniques"] == []
    assert guard["concepts"] == ["Win the underhook before you bump."]
    assert passing["concepts"] == ["Win the underhook before you bump."]
    assert guard["suggested_tags"] == ["underhook"]
    assert passing["suggested_tags"] == ["underhook"]
    prompt = prompts[0]
    assert "Pare BJJ Instructional Chapter" in prompt
    assert "Chapter concepts" in prompt
    assert "Chapter speech:" in prompt
    assert "<10.00>" in prompt
    assert "<290.00>" in prompt
    assert "<300.00>" in prompt
    assert "instructor:" in prompt
    assert "chapter: Guard" in prompt


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
    assert "concepts" not in guard
    assert "concepts" not in passing
    assert "techniques" not in guard
    assert "techniques" not in passing


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
    assert "concepts" not in guard
    assert "techniques" not in guard


def test_one_completer_call_per_chapter_sends_full_raw(tmp_path: Path):
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
        return json.dumps(
            {
                "transcript_cleaned": f"chapter {len(prompts)}",
                "concepts": [f"idea {len(prompts)}"],
                "suggested_tags": [f"tag {len(prompts)}"],
                "techniques": [],
            }
        )

    code = prepare_volume(json_path, corpus, completer=completer)

    assert code == 0
    assert len(prompts) == 2
    assert "<0.00>" in prompts[0]
    assert "<50.00>" in prompts[0]
    assert "later pass" not in prompts[0]
    assert "later pass" in prompts[1]
    assert "Pare BJJ Instructional Chapter" in prompts[0]
    data = json.loads(json_path.read_text(encoding="utf-8"))
    guard, passing = data["chapters"]
    assert guard["transcript_cleaned"] == "chapter 1"
    assert passing["transcript_cleaned"] == "chapter 2"


def test_starred_hop_fields_persist_on_technique(tmp_path: Path):
    corpus = tmp_path / "corpus"
    json_path = corpus / SHOW / "Season 01" / "vol.json"
    _write_volume(json_path, _two_chapter_payload())

    def completer(_prompt: str) -> str:
        return json.dumps(
            {
                "transcript_cleaned": "pared",
                "concepts": ["Follow faster than you throw him."],
                "suggested_tags": ["follow faster"],
                "techniques": [{**STAR_TECHNIQUE, "extra": "drop-me"}],
            }
        )

    code = prepare_volume(json_path, corpus, completer=completer)

    assert code == 0
    guard = json.loads(json_path.read_text(encoding="utf-8"))["chapters"][0]
    assert guard["techniques"] == [STAR_TECHNIQUE]


def test_cleaned_chapter_is_not_sent_again(tmp_path: Path):
    corpus = tmp_path / "corpus"
    json_path = corpus / SHOW / "Season 01" / "vol.json"
    _write_volume(json_path, _two_chapter_payload())
    prepare_volume(json_path, corpus)
    data = json.loads(json_path.read_text(encoding="utf-8"))
    data["chapters"][0]["transcript_cleaned"] = "already"
    data["chapters"][0]["concepts"] = ["already boiled"]
    data["chapters"][0]["suggested_tags"] = ["already"]
    _write_volume(json_path, data)
    prompts: list[str] = []

    def completer(prompt: str) -> str:
        prompts.append(prompt)
        return EMPTY_PARE

    code = prepare_volume(json_path, corpus, completer=completer)

    assert code == 0
    assert len(prompts) == 1
    assert "chapter: Pass" in prompts[0]
    guard, passing = json.loads(json_path.read_text(encoding="utf-8"))["chapters"]
    assert guard["transcript_cleaned"] == "already"
    assert passing["transcript_cleaned"] == "pared guard"


def test_empty_raw_skips_completer(tmp_path: Path):
    corpus = tmp_path / "corpus"
    json_path = corpus / SHOW / "Season 01" / "vol.json"
    _write_volume(
        json_path,
        {
            "video_file": VOLUME,
            "chapters": [
                {"title": "Guard", "start": 0.0, "end": 300.0, "transcript_raw": ""},
                {
                    "title": "Pass",
                    "start": 300.0,
                    "end": 600.0,
                    "transcript_raw": "hello",
                },
            ],
            "language": "en",
        },
    )
    prompts: list[str] = []

    def completer(prompt: str) -> str:
        prompts.append(prompt)
        return EMPTY_PARE

    code = prepare_volume(json_path, corpus, completer=completer)

    assert code == 0
    assert len(prompts) == 1
    guard, passing = json.loads(json_path.read_text(encoding="utf-8"))["chapters"]
    assert "transcript_cleaned" not in guard
    assert passing["transcript_cleaned"] == "pared guard"


def test_force_repares_cleaned_chapter(tmp_path: Path):
    corpus = tmp_path / "corpus"
    json_path = corpus / SHOW / "Season 01" / "vol.json"
    _write_volume(json_path, _two_chapter_payload())
    prepare_volume(json_path, corpus, completer=lambda _p: EMPTY_PARE)
    prompts: list[str] = []

    def completer(prompt: str) -> str:
        prompts.append(prompt)
        return json.dumps(
            {
                "transcript_cleaned": "again",
                "concepts": ["again boiled"],
                "suggested_tags": ["again"],
                "techniques": [],
            }
        )

    code = prepare_volume(json_path, corpus, completer=completer, force=True)

    assert code == 0
    assert len(prompts) == 2
    guard = json.loads(json_path.read_text(encoding="utf-8"))["chapters"][0]
    assert guard["transcript_cleaned"] == "again"
    assert guard["concepts"] == ["again boiled"]
    assert guard["suggested_tags"] == ["again"]


def test_concepts_keep_strings_and_drop_non_strings(tmp_path: Path):
    corpus = tmp_path / "corpus"
    json_path = corpus / SHOW / "Season 01" / "vol.json"
    _write_volume(json_path, _two_chapter_payload())

    def completer(_prompt: str) -> str:
        return json.dumps(
            {
                "transcript_cleaned": "pared",
                "concepts": [
                    "Win the underhook before you bump.",
                    12,
                    "Keep traveling toward the posted shoulder.",
                    {"no": "dict"},
                ],
                "suggested_tags": ["underhook", 12, "posted shoulder", {"no": "dict"}],
                "techniques": [],
            }
        )

    code = prepare_volume(json_path, corpus, completer=completer)

    assert code == 0
    guard = json.loads(json_path.read_text(encoding="utf-8"))["chapters"][0]
    assert guard["concepts"] == [
        "Win the underhook before you bump.",
        "Keep traveling toward the posted shoulder.",
    ]
    assert guard["suggested_tags"] == ["underhook", "posted shoulder"]


def test_missing_concepts_omits_cleaned(tmp_path: Path):
    corpus = tmp_path / "corpus"
    json_path = corpus / SHOW / "Season 01" / "vol.json"
    _write_volume(json_path, _two_chapter_payload())

    def completer(_prompt: str) -> str:
        return json.dumps({"transcript_cleaned": "pared", "techniques": []})

    code = prepare_volume(json_path, corpus, completer=completer)

    assert code == 1
    guard = json.loads(json_path.read_text(encoding="utf-8"))["chapters"][0]
    assert "transcript_cleaned" not in guard
    assert "concepts" not in guard
    assert "suggested_tags" not in guard


def test_missing_suggested_tags_omits_cleaned(tmp_path: Path):
    corpus = tmp_path / "corpus"
    json_path = corpus / SHOW / "Season 01" / "vol.json"
    _write_volume(json_path, _two_chapter_payload())

    def completer(_prompt: str) -> str:
        return json.dumps(
            {
                "transcript_cleaned": "pared",
                "concepts": ["Win the underhook before you bump."],
                "techniques": [],
            }
        )

    code = prepare_volume(json_path, corpus, completer=completer)

    assert code == 1
    guard = json.loads(json_path.read_text(encoding="utf-8"))["chapters"][0]
    assert "transcript_cleaned" not in guard
    assert "suggested_tags" not in guard


def test_max_llm_calls_stops_after_budget(tmp_path: Path):
    corpus = tmp_path / "corpus"
    json_path = corpus / SHOW / "Season 01" / "vol.json"
    _write_volume(json_path, _two_chapter_payload())
    prompts: list[str] = []

    def completer(prompt: str) -> str:
        prompts.append(prompt)
        return EMPTY_PARE

    code = prepare_volume(json_path, corpus, completer=completer, max_llm_calls=1)

    assert code == 0
    assert len(prompts) == 1
    data = json.loads(json_path.read_text(encoding="utf-8"))
    guard, passing = data["chapters"]
    assert guard["transcript_cleaned"] == "pared guard"
    assert "transcript_cleaned" not in passing
    assert passing["transcript_raw"]


def test_cleaned_without_concepts_is_sent_again(tmp_path: Path):
    corpus = tmp_path / "corpus"
    json_path = corpus / SHOW / "Season 01" / "vol.json"
    _write_volume(json_path, _two_chapter_payload())
    prepare_volume(json_path, corpus)
    data = json.loads(json_path.read_text(encoding="utf-8"))
    data["chapters"][0]["transcript_cleaned"] = "already"
    _write_volume(json_path, data)
    prompts: list[str] = []

    def completer(prompt: str) -> str:
        prompts.append(prompt)
        return EMPTY_PARE

    code = prepare_volume(json_path, corpus, completer=completer)

    assert code == 0
    assert len(prompts) == 2
    guard = json.loads(json_path.read_text(encoding="utf-8"))["chapters"][0]
    assert guard["concepts"] == ["Win the underhook before you bump."]


def test_complete_chat_posts_openai_body(monkeypatch):
    from bjj_pipeline.prepare import (
        DEFAULT_LLM_MODEL,
        DEFAULT_REASONING_EFFORT,
        complete_chat,
    )

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
        recorded["authorization"] = req.headers.get("Authorization")
        return FakeResponse()

    monkeypatch.setenv("BJJ_LLM_BASE_URL", "http://example.test/v1")
    monkeypatch.setenv("BJJ_LLM_MODEL", "grok-test")
    monkeypatch.setenv("XAI_API_KEY", "secret-key")
    text = complete_chat("pare this", urlopen=fake_urlopen)

    assert text == "pared json"
    assert recorded["url"] == "http://example.test/v1/chat/completions"
    assert recorded["body"]["model"] == "grok-test"
    assert recorded["body"]["messages"][0]["role"] == "system"
    assert "Pare BJJ Instructional Chapter" in recorded["body"]["messages"][0]["content"]
    assert recorded["body"]["messages"][1] == {"role": "user", "content": "pare this"}
    assert recorded["body"]["temperature"] == 0
    assert recorded["body"]["reasoning_effort"] == "low"
    assert recorded["body"]["response_format"] == {"type": "json_object"}
    assert "options" not in recorded["body"]
    assert recorded["authorization"] == "Bearer secret-key"
    assert DEFAULT_REASONING_EFFORT == "low"

    monkeypatch.delenv("BJJ_LLM_BASE_URL")
    monkeypatch.delenv("BJJ_LLM_MODEL")
    complete_chat("again", urlopen=fake_urlopen)
    assert recorded["url"] == "https://api.x.ai/v1/chat/completions"
    assert recorded["body"]["model"] == DEFAULT_LLM_MODEL
    assert DEFAULT_LLM_MODEL == "grok-4.3"


def _fake_chat_urlopen(recorded: dict, content: str = "pared json", anthropic: bool = False):
    class FakeResponse:
        def read(self):
            if anthropic:
                payload = {"content": [{"type": "text", "text": content}]}
            else:
                payload = {"choices": [{"message": {"content": content}}]}
            return json.dumps(payload).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    def fake_urlopen(req, timeout=None):
        recorded["url"] = req.full_url
        recorded["body"] = json.loads(req.data.decode("utf-8"))
        recorded["timeout"] = timeout
        recorded["headers"] = {k.lower(): v for k, v in req.header_items()}
        return FakeResponse()

    return fake_urlopen


def test_complete_chat_openai_omits_reasoning_effort(monkeypatch):
    from bjj_pipeline.prepare import complete_chat

    recorded: dict = {}
    monkeypatch.delenv("BJJ_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("BJJ_LLM_MODEL", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
    text = complete_chat(
        "pare this",
        provider="openai",
        urlopen=_fake_chat_urlopen(recorded),
    )

    assert text == "pared json"
    assert recorded["url"] == "https://api.openai.com/v1/chat/completions"
    assert recorded["body"]["model"] == "gpt-5.4-mini"
    assert "reasoning_effort" not in recorded["body"]
    assert recorded["body"]["response_format"] == {"type": "json_object"}
    assert recorded["headers"]["authorization"] == "Bearer sk-openai"


def test_complete_chat_anthropic_posts_messages_body(monkeypatch):
    from bjj_pipeline.prepare import complete_chat

    recorded: dict = {}
    monkeypatch.delenv("BJJ_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("BJJ_LLM_MODEL", raising=False)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant")
    text = complete_chat(
        "pare this",
        provider="claude",
        urlopen=_fake_chat_urlopen(recorded, anthropic=True),
    )

    assert text == "pared json"
    assert recorded["url"] == "https://api.anthropic.com/v1/messages"
    assert recorded["body"]["model"] == "claude-haiku-5-5"
    assert recorded["body"]["max_tokens"] == 16384
    assert "temperature" not in recorded["body"]
    assert recorded["body"]["messages"] == [{"role": "user", "content": "pare this"}]
    assert "Pare BJJ Instructional Chapter" in recorded["body"]["system"]
    assert "reasoning_effort" not in recorded["body"]
    assert recorded["body"]["thinking"] == {"type": "disabled"}
    assert recorded["headers"]["x-api-key"] == "sk-ant"
    assert recorded["headers"]["anthropic-version"] == "2023-06-01"


def test_complete_chat_anthropic_reads_text_after_thinking_block(monkeypatch):
    from bjj_pipeline.prepare import complete_chat

    class FakeResponse:
        def read(self):
            return json.dumps(
                {
                    "stop_reason": "end_turn",
                    "content": [
                        {"type": "thinking", "thinking": "", "signature": "sig"},
                        {"type": "text", "text": "pared json"},
                    ],
                }
            ).encode("utf-8")

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant")
    text = complete_chat(
        "pare this",
        provider="anthropic",
        urlopen=lambda req, timeout=None: FakeResponse(),
    )
    assert text == "pared json"


def test_complete_chat_provider_from_env_and_model_override(monkeypatch):
    from bjj_pipeline.prepare import complete_chat

    recorded: dict = {}
    monkeypatch.setenv("BJJ_LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
    monkeypatch.delenv("BJJ_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("BJJ_LLM_MODEL", raising=False)
    complete_chat(
        "pare this",
        model="gpt-4.1-mini",
        urlopen=_fake_chat_urlopen(recorded),
    )

    assert recorded["url"] == "https://api.openai.com/v1/chat/completions"
    assert recorded["body"]["model"] == "gpt-4.1-mini"
    assert "reasoning_effort" not in recorded["body"]


def test_complete_chat_http_error_includes_status_and_body():
    from bjj_pipeline.prepare import complete_chat
    import urllib.error

    class FakeError(urllib.error.HTTPError):
        def __init__(self):
            super().__init__(
                "https://api.anthropic.com/v1/messages",
                400,
                "Bad Request",
                hdrs=None,
                fp=None,
            )

        def read(self):
            return b'{"error":{"message":"`temperature` is deprecated for this model."}}'

    def boom(req, timeout=None):
        raise FakeError()

    try:
        complete_chat("pare this", provider="anthropic", urlopen=boom)
    except RuntimeError as exc:
        text = str(exc)
        assert "HTTP 400" in text
        assert "temperature" in text
    else:
        raise AssertionError("expected RuntimeError")


def test_complete_chat_rejects_unknown_provider():
    from bjj_pipeline.prepare import complete_chat

    try:
        complete_chat("pare this", provider="gemini")
    except ValueError as exc:
        assert "gemini" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_complete_chat_custom_spec_and_medium_effort(monkeypatch):
    from bjj_pipeline.prepare import complete_chat

    recorded: dict = {}
    monkeypatch.delenv("BJJ_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("BJJ_LLM_MODEL", raising=False)
    monkeypatch.setenv("XAI_API_KEY", "secret-key")
    text = complete_chat(
        "pare this",
        spec="Cleanup only.",
        reasoning_effort="medium",
        urlopen=_fake_chat_urlopen(recorded),
    )

    assert text == "pared json"
    assert recorded["body"]["model"] == "grok-4.3"
    assert recorded["body"]["messages"][0] == {
        "role": "system",
        "content": "Cleanup only.",
    }
    assert recorded["body"]["messages"][1] == {"role": "user", "content": "pare this"}
    assert recorded["body"]["reasoning_effort"] == "medium"


def test_complete_chat_omits_spec_uses_combined_and_low(monkeypatch):
    from bjj_pipeline.prepare import complete_chat

    recorded: dict = {}
    monkeypatch.delenv("BJJ_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("BJJ_LLM_MODEL", raising=False)
    complete_chat("pare this", urlopen=_fake_chat_urlopen(recorded))
    assert "Pare BJJ Instructional Chapter" in recorded["body"]["messages"][0]["content"]
    assert recorded["body"]["reasoning_effort"] == "low"


def test_make_completer_cleanup_low_extract_medium_same_model(monkeypatch):
    from bjj_pipeline.prepare import make_completer

    bodies: list[dict] = []

    def fake_urlopen(req, timeout=None):
        bodies.append(json.loads(req.data.decode("utf-8")))

        class FakeResponse:
            def read(self):
                return json.dumps(
                    {"choices": [{"message": {"content": "{}"}}]}
                ).encode("utf-8")

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        return FakeResponse()

    monkeypatch.setattr("bjj_pipeline.prepare.urllib.request.urlopen", fake_urlopen)
    monkeypatch.delenv("BJJ_LLM_MODEL", raising=False)
    cleaner = make_completer(
        "xai", "grok-4.3", spec="CLEAN", reasoning_effort="low"
    )
    extractor = make_completer(
        "xai", "grok-4.3", spec="EXTRACT", reasoning_effort="medium"
    )
    openai_clean = make_completer(
        "openai", "gpt-4.1-mini", spec="CLEAN", reasoning_effort="low"
    )
    openai_extract = make_completer(
        "openai", "gpt-4.1-mini", spec="EXTRACT", reasoning_effort="medium"
    )
    cleaner("hi")
    extractor("hi")
    openai_clean("hi")
    openai_extract("hi")
    assert bodies[0]["model"] == "grok-4.3"
    assert bodies[1]["model"] == "grok-4.3"
    assert bodies[0]["reasoning_effort"] == "low"
    assert bodies[1]["reasoning_effort"] == "medium"
    assert bodies[0]["messages"][0]["content"] == "CLEAN"
    assert bodies[1]["messages"][0]["content"] == "EXTRACT"
    assert bodies[2]["model"] == "gpt-4.1-mini"
    assert bodies[3]["model"] == "gpt-4.1-mini"
    assert "reasoning_effort" not in bodies[2]
    assert "reasoning_effort" not in bodies[3]


def test_complete_chat_medium_effort_omitted_on_openai(monkeypatch):
    from bjj_pipeline.prepare import complete_chat

    recorded: dict = {}
    monkeypatch.delenv("BJJ_LLM_BASE_URL", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
    complete_chat(
        "pare this",
        provider="openai",
        spec="Extract only.",
        reasoning_effort="medium",
        urlopen=_fake_chat_urlopen(recorded),
    )
    assert recorded["url"] == "https://api.openai.com/v1/chat/completions"
    assert recorded["body"]["model"] == "gpt-5.4-mini"
    assert recorded["body"]["messages"][0]["content"] == "Extract only."
    assert "reasoning_effort" not in recorded["body"]


def test_staged_specs_size_and_content():
    from bjj_pipeline.prepare import _cleanup_spec, _extract_spec

    cleanup = _cleanup_spec()
    extract = _extract_spec()
    assert len(cleanup) < 8000
    assert len(extract) < 16000
    assert "Chair sit escape" not in cleanup
    assert "Chair sit escape" not in extract
    assert "steps" in cleanup.lower()
    assert "do not" in cleanup.lower()
    assert "drill" in extract.lower()
    assert "1234.00-1560.00" in extract
    assert "Never infer" in extract
    assert "suggested_tags" not in extract.split("## Output")[-1] or "No `suggested_tags`" in extract


CLEANUP_JSON = json.dumps({"transcript_cleaned": "pared guard"})
EXTRACT_JSON = json.dumps(
    {
        "concepts": ["Win the underhook before you bump."],
        "techniques": [],
    }
)


def test_staged_cleanup_then_extract(tmp_path: Path):
    corpus = tmp_path / "corpus"
    json_path = corpus / SHOW / "Season 01" / "vol.json"
    _write_volume(json_path, _two_chapter_payload())
    clean_prompts: list[str] = []
    extract_prompts: list[str] = []

    def cleaner(prompt: str) -> str:
        clean_prompts.append(prompt)
        return CLEANUP_JSON

    def extractor(prompt: str) -> str:
        extract_prompts.append(prompt)
        return EXTRACT_JSON

    code = prepare_volume(
        json_path, corpus, cleaner=cleaner, extractor=extractor
    )

    assert code == 0
    assert len(clean_prompts) == 2
    assert len(extract_prompts) == 2
    assert "Pare chapter speech" in clean_prompts[0]
    assert "<10.00>" in clean_prompts[0]
    assert "Extract concepts and techniques" in extract_prompts[0]
    assert "pared guard" in extract_prompts[0]
    assert "um so like" not in extract_prompts[0]
    data = json.loads(json_path.read_text(encoding="utf-8"))
    guard = data["chapters"][0]
    assert guard["transcript_cleaned"] == "pared guard"
    assert guard["concepts"] == ["Win the underhook before you bump."]
    assert guard["suggested_tags"] == ["Win the underhook before you bump"]
    assert guard["techniques"] == []


def test_staged_extract_not_called_when_cleanup_fails(tmp_path: Path):
    corpus = tmp_path / "corpus"
    json_path = corpus / SHOW / "Season 01" / "vol.json"
    _write_volume(json_path, _two_chapter_payload())
    extracts = []

    def cleaner(_prompt: str) -> str:
        raise OSError("cleanup down")

    def extractor(prompt: str) -> str:
        extracts.append(prompt)
        return EXTRACT_JSON

    code = prepare_volume(
        json_path, corpus, cleaner=cleaner, extractor=extractor
    )

    assert code == 1
    assert extracts == []
    guard = json.loads(json_path.read_text(encoding="utf-8"))["chapters"][0]
    assert "transcript_cleaned" not in guard
    assert "concepts" not in guard


def test_staged_cleaned_without_concepts_calls_extract_only(tmp_path: Path):
    corpus = tmp_path / "corpus"
    json_path = corpus / SHOW / "Season 01" / "vol.json"
    payload = _two_chapter_payload()
    payload["chapters"][0]["transcript_raw"] = "<10.00> um keep the elbow"
    payload["chapters"][0]["transcript_cleaned"] = "Keep the elbow tight."
    payload["chapters"][1]["transcript_raw"] = "<300.00> pass speech"
    payload["chapters"][1]["transcript_cleaned"] = "Pass cleaned."
    payload["chapters"][1]["concepts"] = ["already"]
    del payload["segments"]
    _write_volume(json_path, payload)
    clean_prompts: list[str] = []
    extract_prompts: list[str] = []

    def cleaner(prompt: str) -> str:
        clean_prompts.append(prompt)
        return CLEANUP_JSON

    def extractor(prompt: str) -> str:
        extract_prompts.append(prompt)
        return EXTRACT_JSON

    code = prepare_volume(
        json_path, corpus, cleaner=cleaner, extractor=extractor
    )

    assert code == 0
    assert clean_prompts == []
    assert len(extract_prompts) == 1
    assert "Keep the elbow tight." in extract_prompts[0]
    assert "um keep the elbow" not in extract_prompts[0]
    guard, passing = json.loads(json_path.read_text(encoding="utf-8"))["chapters"]
    assert guard["concepts"] == ["Win the underhook before you bump."]
    assert passing["concepts"] == ["already"]


def test_staged_failed_extract_keeps_cleaned(tmp_path: Path):
    corpus = tmp_path / "corpus"
    json_path = corpus / SHOW / "Season 01" / "vol.json"
    _write_volume(json_path, _two_chapter_payload())

    def extractor(_prompt: str) -> str:
        return "not json"

    code = prepare_volume(
        json_path,
        corpus,
        cleaner=lambda _p: CLEANUP_JSON,
        extractor=extractor,
    )

    assert code == 1
    guard = json.loads(json_path.read_text(encoding="utf-8"))["chapters"][0]
    assert guard["transcript_cleaned"] == "pared guard"
    assert "concepts" not in guard
    assert "techniques" not in guard


def test_staged_extract_ignores_model_tags_and_empty_concepts(tmp_path: Path):
    corpus = tmp_path / "corpus"
    json_path = corpus / SHOW / "Season 01" / "vol.json"
    _write_volume(json_path, _two_chapter_payload())

    def extractor(_prompt: str) -> str:
        return json.dumps(
            {
                "concepts": [],
                "suggested_tags": ["ignore-me"],
                "techniques": [
                    {
                        **STAR_TECHNIQUE,
                        "main_ideas": "Follow faster than you throw him.",
                        "suggested_tags": ["model-tag"],
                    }
                ],
            }
        )

    code = prepare_volume(
        json_path,
        corpus,
        cleaner=lambda _p: CLEANUP_JSON,
        extractor=extractor,
    )

    assert code == 0
    guard = json.loads(json_path.read_text(encoding="utf-8"))["chapters"][0]
    assert guard["concepts"] == []
    assert guard["suggested_tags"] == []
    assert guard["techniques"][0]["suggested_tags"] == [
        "Follow faster than you throw him"
    ]
    assert "ignore-me" not in guard["suggested_tags"]
    assert "model-tag" not in guard["techniques"][0]["suggested_tags"]


def test_staged_empty_raw_skips_both(tmp_path: Path):
    corpus = tmp_path / "corpus"
    json_path = corpus / SHOW / "Season 01" / "vol.json"
    _write_volume(
        json_path,
        {
            "video_file": VOLUME,
            "chapters": [
                {"title": "Guard", "start": 0.0, "end": 300.0, "transcript_raw": ""},
                {
                    "title": "Pass",
                    "start": 300.0,
                    "end": 600.0,
                    "transcript_raw": "hello",
                },
            ],
            "language": "en",
        },
    )
    calls = {"clean": 0, "extract": 0}

    def cleaner(_prompt: str) -> str:
        calls["clean"] += 1
        return CLEANUP_JSON

    def extractor(_prompt: str) -> str:
        calls["extract"] += 1
        return EXTRACT_JSON

    code = prepare_volume(
        json_path, corpus, cleaner=cleaner, extractor=extractor
    )
    assert code == 0
    assert calls == {"clean": 1, "extract": 1}
    guard = json.loads(json_path.read_text(encoding="utf-8"))["chapters"][0]
    assert "transcript_cleaned" not in guard


def test_staged_force_resends_both(tmp_path: Path):
    corpus = tmp_path / "corpus"
    json_path = corpus / SHOW / "Season 01" / "vol.json"
    _write_volume(json_path, _two_chapter_payload())
    prepare_volume(
        json_path,
        corpus,
        cleaner=lambda _p: CLEANUP_JSON,
        extractor=lambda _p: EXTRACT_JSON,
    )
    calls = {"clean": 0, "extract": 0}

    def cleaner(_prompt: str) -> str:
        calls["clean"] += 1
        return json.dumps({"transcript_cleaned": "again"})

    def extractor(_prompt: str) -> str:
        calls["extract"] += 1
        return json.dumps({"concepts": ["again boiled"], "techniques": []})

    code = prepare_volume(
        json_path, corpus, cleaner=cleaner, extractor=extractor, force=True
    )
    assert code == 0
    assert calls == {"clean": 2, "extract": 2}
    guard = json.loads(json_path.read_text(encoding="utf-8"))["chapters"][0]
    assert guard["transcript_cleaned"] == "again"
    assert guard["concepts"] == ["again boiled"]


def test_completer_rejected_with_cleaner():
    try:
        prepare_volume(
            Path("unused.json"),
            Path("unused"),
            completer=lambda _p: EMPTY_PARE,
            cleaner=lambda _p: CLEANUP_JSON,
        )
    except ValueError as exc:
        assert "completer" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_one_call_still_uses_combined_spec(tmp_path: Path):
    corpus = tmp_path / "corpus"
    json_path = corpus / SHOW / "Season 01" / "vol.json"
    _write_volume(json_path, _two_chapter_payload())
    prompts: list[str] = []

    def completer(prompt: str) -> str:
        prompts.append(prompt)
        return EMPTY_PARE

    prepare_volume(json_path, corpus, completer=completer)
    assert len(prompts) == 2
    assert "Pare BJJ Instructional Chapter" in prompts[0]
    assert "Chapter concepts" in prompts[0]
