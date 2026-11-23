"""Prepare subcommand walks a library, skips finished chapter speech, and honors --force."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from bjj_pipeline import prepare

SHOW = "Arm Bars by John Danaher"
VIDEO = "S01E01 - Volume 1.mp4"
SEGMENTS = [
    {"start": 10.0, "end": 20.0, "text": "in guard"},
    {"start": 290.0, "end": 310.0, "text": "straddling the start"},
]


def _tree(tmp_path: Path, *videos: str) -> tuple[Path, Path, list[Path]]:
    library = tmp_path / "lib"
    season = library / SHOW / "Season 01"
    season.mkdir(parents=True)
    paths = []
    names = videos or (VIDEO,)
    for name in names:
        video = season / name
        video.write_bytes(b"fake-video")
        paths.append(video)
    corpus = tmp_path / "corpus"
    return library, corpus, paths


def _json_for(corpus: Path, video: Path, library: Path) -> Path:
    rel = video.relative_to(library)
    return corpus / rel.with_suffix(".json")


def _eligible_payload() -> dict:
    return {
        "video_file": VIDEO,
        "chapters": [
            {"title": "Guard", "start": 0.0, "end": 300.0},
            {"title": "Pass", "start": 300.0, "end": 600.0},
        ],
        "language": "en",
        "segments": list(SEGMENTS),
    }


def _write_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _completer(calls: list[str] | None = None):
    def completer(prompt: str) -> str:
        if calls is not None:
            calls.append(prompt)
        return json.dumps(
            {
                "transcript_cleaned": "pared",
                "concepts": ["pared idea"],
                "suggested_tags": ["pared"],
                "techniques": [],
            }
        )

    return completer


def _cleanup_completer(calls: list[str] | None = None):
    def completer(prompt: str) -> str:
        if calls is not None:
            calls.append(prompt)
        return json.dumps({"transcript_cleaned": "pared"})

    return completer


def _extract_completer(calls: list[str] | None = None):
    def completer(prompt: str) -> str:
        if calls is not None:
            calls.append(prompt)
        return json.dumps({"concepts": ["pared idea"], "techniques": []})

    return completer


def _run(library: Path, corpus: Path, **kwargs):
    buf = io.StringIO()
    method = kwargs.get("method", prepare.DEFAULT_LLM_METHOD)
    if kwargs.get("llm") and method == "staged":
        kwargs.setdefault("cleaner", _cleanup_completer())
        kwargs.setdefault("extractor", _extract_completer())
    elif kwargs.get("llm"):
        kwargs.setdefault("completer", _completer())
    code = prepare.run(library, corpus, stdout=buf, **kwargs)
    return code, buf.getvalue()


def _prepare_line(out: str, status: str) -> str:
    for line in out.splitlines():
        if line.startswith(status) and "prepare" in line:
            return line
    return ""


def test_help_exits_0(capsys):
    with pytest.raises(SystemExit) as exc:
        prepare.main(["--help"])
    assert exc.value.code == 0
    help_text = capsys.readouterr().out
    assert "--library" in help_text
    assert "--corpus" in help_text
    assert "--force" in help_text
    assert "--llm" in help_text
    assert "--provider" in help_text
    assert "--model" in help_text
    assert "--method" in help_text


def test_missing_library_or_corpus_fails():
    with pytest.raises(SystemExit) as exc:
        prepare.main([])
    assert exc.value.code != 0
    with pytest.raises(SystemExit) as exc:
        prepare.main(["--library", "x"])
    assert exc.value.code != 0
    with pytest.raises(SystemExit) as exc:
        prepare.main(["--corpus", "y"])
    assert exc.value.code != 0


def test_parser_provider_and_model():
    args = prepare.build_parser().parse_args(
        [
            "--library",
            "lib",
            "--corpus",
            "corpus",
            "--llm",
            "--provider",
            "openai",
            "--model",
            "gpt-4.1-mini",
        ]
    )
    assert args.provider == "openai"
    assert args.model == "gpt-4.1-mini"
    defaulted = prepare.build_parser().parse_args(
        ["--library", "lib", "--corpus", "corpus", "--llm"]
    )
    assert defaulted.provider == "xai"
    assert defaulted.model is None
    assert defaulted.method == "staged"
    one_call = prepare.build_parser().parse_args(
        ["--library", "lib", "--corpus", "corpus", "--llm", "--method", "one-call"]
    )
    assert one_call.method == "one-call"
    limited = prepare.build_parser().parse_args(
        [
            "--library",
            "lib",
            "--corpus",
            "corpus",
            "--video",
            "Show\\Season 01\\S01E01.mp4",
        ]
    )
    assert limited.video == Path("Show") / "Season 01" / "S01E01.mp4"


def test_parser_has_force_and_llm_not_apply():
    args = prepare.build_parser().parse_args(
        ["--library", "lib", "--corpus", "corpus", "--force"]
    )
    assert args.force is True
    assert args.llm is False
    llm_on = prepare.build_parser().parse_args(
        ["--library", "lib", "--corpus", "corpus", "--llm"]
    )
    assert llm_on.llm is True
    with pytest.raises(SystemExit):
        prepare.build_parser().parse_args(
            ["--library", "lib", "--corpus", "corpus", "--apply"]
        )
    with pytest.raises(SystemExit):
        prepare.build_parser().parse_args(
            ["--library", "lib", "--corpus", "corpus", "--force-stage", "prepare"]
        )


def test_default_nests_without_calling_the_model(tmp_path: Path):
    library, corpus, videos = _tree(tmp_path)
    json_path = _json_for(corpus, videos[0], library)
    _write_json(json_path, _eligible_payload())
    calls: list[str] = []

    code, out = _run(library, corpus, completer=_completer(calls))

    assert code == 0
    assert calls == []
    assert _prepare_line(out, "RUN")
    data = json.loads(json_path.read_text(encoding="utf-8"))
    guard, passing = data["chapters"]
    assert "<290.00>" in guard["transcript_raw"]
    assert "transcript_cleaned" not in guard
    assert "transcript_cleaned" not in passing
    assert guard["instructor"] == "John Danaher"


def test_finished_transcript_raw_skips_without_llm(tmp_path: Path):
    library, corpus, videos = _tree(tmp_path)
    json_path = _json_for(corpus, videos[0], library)
    payload = _eligible_payload()
    for chapter in payload["chapters"]:
        chapter["transcript_raw"] = "<10.00> already nested"
    _write_json(json_path, payload)
    before = json_path.read_bytes()
    calls: list[str] = []

    code, out = _run(library, corpus, completer=_completer(calls))

    assert code == 0
    assert calls == []
    assert json_path.read_bytes() == before
    assert _prepare_line(out, "SKIP")
    assert not _prepare_line(out, "RUN")


def test_llm_pares_eligible_unfinished(tmp_path: Path):
    library, corpus, videos = _tree(tmp_path)
    json_path = _json_for(corpus, videos[0], library)
    _write_json(json_path, _eligible_payload())
    calls: list[str] = []

    code, out = _run(
        library, corpus, llm=True, method="one-call", completer=_completer(calls)
    )

    assert code == 0
    assert calls
    assert _prepare_line(out, "RUN")
    assert not _prepare_line(out, "SKIP")
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert "segments" not in data
    guard, passing = data["chapters"]
    assert guard["transcript_cleaned"] == "pared"
    assert passing["transcript_cleaned"] == "pared"
    assert guard["concepts"] == ["pared idea"]
    assert passing["concepts"] == ["pared idea"]
    assert guard["suggested_tags"] == ["pared"]
    assert passing["suggested_tags"] == ["pared"]
    assert "<290.00>" in guard["transcript_raw"]
    assert guard["title"] == "Guard"
    assert passing["title"] == "Pass"


def test_finished_transcript_cleaned_skips_with_llm(tmp_path: Path):
    library, corpus, videos = _tree(tmp_path)
    json_path = _json_for(corpus, videos[0], library)
    payload = _eligible_payload()
    for chapter in payload["chapters"]:
        chapter["transcript_raw"] = "<10.00> already nested"
        chapter["transcript_cleaned"] = "already pared"
        chapter["concepts"] = ["already boiled"]
        chapter["suggested_tags"] = ["already"]
    _write_json(json_path, payload)
    before = json_path.read_bytes()
    calls: list[str] = []

    code, out = _run(
        library, corpus, llm=True, method="one-call", completer=_completer(calls)
    )

    assert code == 0
    assert calls == []
    assert json_path.read_bytes() == before
    assert _prepare_line(out, "SKIP")
    assert not _prepare_line(out, "RUN")


def test_transcript_raw_alone_does_not_skip_with_llm(tmp_path: Path):
    library, corpus, videos = _tree(tmp_path)
    json_path = _json_for(corpus, videos[0], library)
    payload = _eligible_payload()
    for chapter in payload["chapters"]:
        chapter["transcript_raw"] = "<10.00> already nested"
    _write_json(json_path, payload)
    calls: list[str] = []

    code, out = _run(
        library, corpus, llm=True, method="one-call", completer=_completer(calls)
    )

    assert code == 0
    assert calls
    assert _prepare_line(out, "RUN")


def test_force_reruns_when_cleaned_keys_exist(tmp_path: Path):
    library, corpus, videos = _tree(tmp_path)
    json_path = _json_for(corpus, videos[0], library)
    payload = _eligible_payload()
    for chapter in payload["chapters"]:
        chapter["transcript_cleaned"] = "already pared"
    _write_json(json_path, payload)
    calls: list[str] = []

    code, out = _run(
        library,
        corpus,
        llm=True,
        method="one-call",
        force=True,
        completer=_completer(calls),
    )

    assert code == 0
    assert calls
    assert _prepare_line(out, "RUN")
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["chapters"][0]["transcript_cleaned"] == "pared"


def test_missing_json_skips_even_with_force(tmp_path: Path):
    library, corpus, _videos = _tree(tmp_path)
    calls: list[str] = []

    code, out = _run(library, corpus, force=True, completer=_completer(calls))

    assert code == 0
    assert calls == []
    assert _prepare_line(out, "SKIP")
    assert not _prepare_line(out, "RUN")
    assert list(corpus.rglob("*.json")) == []


def test_ineligible_skips_even_with_force(tmp_path: Path):
    library, corpus, videos = _tree(tmp_path)
    json_path = _json_for(corpus, videos[0], library)
    _write_json(
        json_path,
        {
            "video_file": VIDEO,
            "chapters": [],
            "segments": list(SEGMENTS),
        },
    )
    before = json_path.read_bytes()
    calls: list[str] = []

    code, out = _run(library, corpus, force=True, completer=_completer(calls))

    assert code == 0
    assert calls == []
    assert json_path.read_bytes() == before
    assert _prepare_line(out, "SKIP")
    assert not _prepare_line(out, "RUN")


def test_missing_segments_skips_even_with_force(tmp_path: Path):
    library, corpus, videos = _tree(tmp_path)
    json_path = _json_for(corpus, videos[0], library)
    payload = _eligible_payload()
    del payload["segments"]
    _write_json(json_path, payload)
    calls: list[str] = []

    code, out = _run(library, corpus, force=True, completer=_completer(calls))

    assert code == 0
    assert calls == []
    assert _prepare_line(out, "SKIP")


def test_model_down_nests_raw_prints_fail_exits_1(tmp_path: Path):
    library, corpus, videos = _tree(tmp_path)
    json_path = _json_for(corpus, videos[0], library)
    _write_json(json_path, _eligible_payload())

    def down(_prompt: str) -> str:
        raise OSError("connection refused")

    code, out = _run(library, corpus, llm=True, method="one-call", completer=down)

    assert code == 1
    fail = _prepare_line(out, "FAIL")
    assert fail
    assert "model half" in fail
    assert not _prepare_line(out, "RUN")
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert "segments" not in data
    guard, passing = data["chapters"]
    assert "<290.00>" in guard["transcript_raw"]
    assert "<290.00>" in passing["transcript_raw"]
    assert "transcript_cleaned" not in guard
    assert "transcript_cleaned" not in passing


def test_model_fail_continues_walk(tmp_path: Path):
    library, corpus, videos = _tree(
        tmp_path, "S01E01 - Volume 1.mp4", "S01E02 - Volume 2.mp4"
    )
    first = _json_for(corpus, videos[0], library)
    second = _json_for(corpus, videos[1], library)
    payload_a = _eligible_payload()
    payload_b = _eligible_payload()
    payload_b["video_file"] = videos[1].name
    _write_json(first, payload_a)
    _write_json(second, payload_b)
    seen = {"n": 0}

    def flaky(prompt: str) -> str:
        seen["n"] += 1
        if seen["n"] == 1:
            raise OSError("down")
        return json.dumps(
            {
                "transcript_cleaned": "pared",
                "concepts": ["pared idea"],
                "suggested_tags": ["pared"],
                "techniques": [],
            }
        )

    code, out = _run(library, corpus, llm=True, method="one-call", completer=flaky)

    assert code == 1
    assert _prepare_line(out, "FAIL")
    assert _prepare_line(out, "RUN")
    first_data = json.loads(first.read_text(encoding="utf-8"))
    second_data = json.loads(second.read_text(encoding="utf-8"))
    assert "transcript_cleaned" not in first_data["chapters"][0]
    assert second_data["chapters"][0]["transcript_cleaned"] == "pared"


def test_extras_and_trailers_are_not_walked(tmp_path: Path):
    library, corpus, videos = _tree(tmp_path)
    json_path = _json_for(corpus, videos[0], library)
    _write_json(json_path, _eligible_payload())
    extras = videos[0].parent / "extras"
    extras.mkdir()
    (extras / "sample.mp4").write_bytes(b"trailer")
    trailers = library / SHOW / "trailers"
    trailers.mkdir()
    (trailers / "promo.mp4").write_bytes(b"promo")
    calls: list[str] = []

    code, out = _run(
        library, corpus, llm=True, method="one-call", completer=_completer(calls)
    )

    assert code == 0
    assert "sample.mp4" not in out
    assert "promo.mp4" not in out
    assert VIDEO in _prepare_line(out, "RUN")
    assert len(calls) == 2


def test_mixed_library_prepares_only_unfinished(tmp_path: Path):
    library, corpus, videos = _tree(
        tmp_path, "S01E01 - Volume 1.mp4", "S01E02 - Volume 2.mp4"
    )
    first = _json_for(corpus, videos[0], library)
    second = _json_for(corpus, videos[1], library)
    done = _eligible_payload()
    for chapter in done["chapters"]:
        chapter["transcript_raw"] = "<10.00> already nested"
        chapter["transcript_cleaned"] = "already"
        chapter["concepts"] = ["already boiled"]
        chapter["suggested_tags"] = ["already"]
    _write_json(first, done)
    unfinished = _eligible_payload()
    unfinished["video_file"] = videos[1].name
    _write_json(second, unfinished)
    calls: list[str] = []

    code, out = _run(
        library, corpus, llm=True, method="one-call", completer=_completer(calls)
    )

    assert code == 0
    assert _prepare_line(out, "SKIP")
    assert _prepare_line(out, "RUN")
    assert json.loads(first.read_text(encoding="utf-8"))["chapters"][0][
        "transcript_cleaned"
    ] == "already"
    assert json.loads(second.read_text(encoding="utf-8"))["chapters"][0][
        "transcript_cleaned"
    ] == "pared"
    assert len(calls) == 2


def test_staged_cli_two_calls_and_skip(tmp_path: Path):
    library, corpus, videos = _tree(tmp_path)
    json_path = _json_for(corpus, videos[0], library)
    _write_json(json_path, _eligible_payload())
    clean_calls: list[str] = []
    extract_calls: list[str] = []

    code, out = _run(
        library,
        corpus,
        llm=True,
        method="staged",
        cleaner=_cleanup_completer(clean_calls),
        extractor=_extract_completer(extract_calls),
    )

    assert code == 0
    assert len(clean_calls) == 2
    assert len(extract_calls) == 2
    assert _prepare_line(out, "RUN")
    data = json.loads(json_path.read_text(encoding="utf-8"))
    assert data["chapters"][0]["transcript_cleaned"] == "pared"
    assert data["chapters"][0]["concepts"] == ["pared idea"]
    assert data["chapters"][0]["suggested_tags"] == ["pared idea"]

    before = json_path.read_bytes()
    code, out = _run(
        library,
        corpus,
        llm=True,
        method="staged",
        cleaner=_cleanup_completer(clean_calls),
        extractor=_extract_completer(extract_calls),
    )
    assert code == 0
    assert json_path.read_bytes() == before
    assert _prepare_line(out, "SKIP")


def test_default_llm_is_staged(tmp_path: Path):
    library, corpus, videos = _tree(tmp_path)
    json_path = _json_for(corpus, videos[0], library)
    _write_json(json_path, _eligible_payload())
    clean_calls: list[str] = []
    extract_calls: list[str] = []

    code, _out = _run(
        library,
        corpus,
        llm=True,
        cleaner=_cleanup_completer(clean_calls),
        extractor=_extract_completer(extract_calls),
    )

    assert code == 0
    assert len(clean_calls) == 2
    assert len(extract_calls) == 2
    assert "Pare chapter speech" in clean_calls[0]
    assert "Extract concepts and techniques" in extract_calls[0]
    assert "Pare BJJ Instructional Chapter" not in clean_calls[0]


def test_video_flag_limits_walk_to_one_file(tmp_path: Path):
    library, corpus, videos = _tree(
        tmp_path, "S01E01 - Volume 1.mp4", "S01E02 - Volume 2.mp4"
    )
    for video in videos:
        _write_json(_json_for(corpus, video, library), _eligible_payload())
    rel = videos[1].relative_to(library)

    code, out = _run(library, corpus, video=rel)

    assert code == 0
    assert "S01E02 - Volume 2.mp4" in out
    assert "S01E01 - Volume 1.mp4" not in out


def test_video_flag_rejects_path_outside_library(tmp_path: Path):
    library, corpus, _videos = _tree(tmp_path)
    outside = tmp_path / "other.mp4"
    outside.write_bytes(b"x")
    code, _out = _run(library, corpus, video=outside)
    assert code == 2
