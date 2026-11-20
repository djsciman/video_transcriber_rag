"""compare-llm copies sample volumes and pares them with each chat vendor."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pytest

from bjj_pipeline import compare_llm

SHOW = "Arm Bars by John Danaher"
REL = f"{SHOW}/Season 01/S01E01 - Volume 1.json"
REL_TWO = f"{SHOW}/Season 01/S01E02 - Volume 2.json"


def _nested_payload(*, cleaned: bool = False) -> dict:
    chapters = []
    for title in ("Guard", "Pass"):
        chapter = {
            "title": title,
            "start": 0.0 if title == "Guard" else 300.0,
            "end": 300.0 if title == "Guard" else 600.0,
            "transcript_raw": f"<10.00> {title} speech",
        }
        if cleaned:
            chapter["transcript_cleaned"] = "old cleaned"
            chapter["concepts"] = ["old idea"]
            chapter["suggested_tags"] = ["old"]
            chapter["techniques"] = []
        chapters.append(chapter)
    return {
        "video_file": "S01E01 - Volume 1.mp4",
        "chapters": chapters,
        "language": "en",
    }


def _write_volume(corpus: Path, payload: dict, rel: str = REL) -> Path:
    path = corpus / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _completer(label: str):
    def completer(_prompt: str) -> str:
        return json.dumps(
            {
                "transcript_cleaned": f"{label} cleaned",
                "concepts": [f"{label} idea"],
                "suggested_tags": [label],
                "techniques": [],
            }
        )

    return completer


def test_help_exits_0(capsys):
    with pytest.raises(SystemExit) as exc:
        compare_llm.main(["--help"])
    assert exc.value.code == 0
    help_text = capsys.readouterr().out
    assert "--corpus" in help_text
    assert "--out" in help_text
    assert "--volume" in help_text
    assert "--volumes-file" in help_text
    assert "--providers" in help_text
    assert "--max-chapters" in help_text
    assert "--dry-run" in help_text
    assert "--from-existing" in help_text
    assert "--methods" in help_text
    assert "--provider" in help_text
    assert "--model" in help_text


def test_dry_run_does_not_copy_or_call(tmp_path: Path, monkeypatch):
    corpus = tmp_path / "corpus"
    out = tmp_path / "out"
    _write_volume(corpus, _nested_payload(cleaned=True))
    monkeypatch.setenv("XAI_API_KEY", "x")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    calls: list[str] = []

    buf = io.StringIO()
    code = compare_llm.run(
        corpus,
        out,
        volumes=[REL],
        dry_run=True,
        completers={"xai": _completer("xai")},
        stdout=buf,
    )

    assert code == 0
    assert calls == []
    assert not out.exists() or list(out.rglob("*.json")) == []
    text = buf.getvalue()
    assert "DRY" in text
    assert REL.replace("\\", "/") in text.replace("\\", "/")
    assert "XAI_API_KEY" in text
    assert "set" in text
    assert "OPENAI_API_KEY" in text
    assert "missing" in text
    source = json.loads((corpus / REL).read_text(encoding="utf-8"))
    assert source["chapters"][0]["transcript_cleaned"] == "old cleaned"


def test_compare_copies_strips_and_leaves_source(tmp_path: Path):
    corpus = tmp_path / "corpus"
    out = tmp_path / "out"
    source = _write_volume(corpus, _nested_payload(cleaned=True))
    before = source.read_bytes()
    buf = io.StringIO()

    code = compare_llm.run(
        corpus,
        out,
        volumes=[REL],
        providers=("xai", "openai"),
        completers={"xai": _completer("xai"), "openai": _completer("openai")},
        stdout=buf,
    )

    assert code == 0
    assert source.read_bytes() == before
    xai = json.loads((out / "xai" / REL).read_text(encoding="utf-8"))
    openai = json.loads((out / "openai" / REL).read_text(encoding="utf-8"))
    assert xai["chapters"][0]["transcript_cleaned"] == "xai cleaned"
    assert openai["chapters"][0]["transcript_cleaned"] == "openai cleaned"
    assert xai["chapters"][0]["concepts"] == ["xai idea"]
    assert openai["chapters"][0]["concepts"] == ["openai idea"]
    report = json.loads((out / "report.json").read_text(encoding="utf-8"))
    chapter = report["volumes"][0]["chapters"][0]
    assert chapter["title"] == "Guard"
    assert chapter["by_provider"]["xai"]["concepts"] == ["xai idea"]
    assert chapter["by_provider"]["openai"]["concepts"] == ["openai idea"]
    markdown = (out / "report.md").read_text(encoding="utf-8")
    assert "Guard" in markdown
    assert "xai idea" in markdown
    assert "openai idea" in markdown
    metrics = json.loads((out / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["providers"]["xai"]["cleaned_chapters"] == 2
    assert metrics["providers"]["openai"]["cleaned_chapters"] == 2
    assert (out / "metrics.md").is_file()
    assert "median raw-token coverage" in (out / "metrics.md").read_text(encoding="utf-8")


def test_max_chapters_is_per_provider(tmp_path: Path):
    corpus = tmp_path / "corpus"
    out = tmp_path / "out"
    _write_volume(corpus, _nested_payload())
    counts = {"xai": 0, "openai": 0}

    def counting(label: str):
        def completer(_prompt: str) -> str:
            counts[label] += 1
            return json.dumps(
                {
                    "transcript_cleaned": f"{label} cleaned",
                    "concepts": [label],
                    "suggested_tags": [label],
                    "techniques": [],
                }
            )

        return completer

    code = compare_llm.run(
        corpus,
        out,
        volumes=[REL],
        providers=("xai", "openai"),
        max_chapters=1,
        completers={"xai": counting("xai"), "openai": counting("openai")},
        stdout=io.StringIO(),
    )

    assert code == 0
    assert counts == {"xai": 1, "openai": 1}
    xai = json.loads((out / "xai" / REL).read_text(encoding="utf-8"))
    assert "transcript_cleaned" in xai["chapters"][0]
    assert "transcript_cleaned" not in xai["chapters"][1]


def test_max_chapters_applies_per_volume(tmp_path: Path):
    corpus = tmp_path / "corpus"
    out = tmp_path / "out"
    _write_volume(corpus, _nested_payload(), REL)
    _write_volume(corpus, _nested_payload(), REL_TWO)
    counts = {"openai": 0}

    def counting(_prompt: str) -> str:
        counts["openai"] += 1
        return json.dumps(
            {
                "transcript_cleaned": "openai cleaned",
                "concepts": ["openai"],
                "suggested_tags": ["openai"],
                "techniques": [],
            }
        )

    code = compare_llm.run(
        corpus,
        out,
        volumes=[REL, REL_TWO],
        providers=("openai",),
        max_chapters=1,
        completers={"openai": counting},
        stdout=io.StringIO(),
    )

    assert code == 0
    assert counts == {"openai": 2}
    first = json.loads((out / "openai" / REL).read_text(encoding="utf-8"))
    second = json.loads((out / "openai" / REL_TWO).read_text(encoding="utf-8"))
    assert "transcript_cleaned" in first["chapters"][0]
    assert "transcript_cleaned" not in first["chapters"][1]
    assert "transcript_cleaned" in second["chapters"][0]
    assert "transcript_cleaned" not in second["chapters"][1]


def test_volumes_file_loads_paths(tmp_path: Path):
    listing = tmp_path / "sample.txt"
    listing.write_text(
        f"# comment\n{REL}\n\n",
        encoding="utf-8",
    )
    rels = compare_llm.load_volume_list(volumes_file=listing)
    assert rels == [REL]


def test_model_error_is_printed(tmp_path: Path):
    corpus = tmp_path / "corpus"
    out = tmp_path / "out"
    _write_volume(corpus, _nested_payload())

    def down(_prompt: str) -> str:
        raise RuntimeError("HTTP 400 temperature is deprecated")

    buf = io.StringIO()
    code = compare_llm.run(
        corpus,
        out,
        volumes=[REL],
        providers=("anthropic",),
        completers={"anthropic": down},
        stdout=buf,
    )
    assert code == 1
    assert "HTTP 400" in buf.getvalue()
    assert "temperature" in buf.getvalue()


def test_from_existing_rebuilds_metrics_without_calls(tmp_path: Path):
    out = tmp_path / "out"
    rel = REL.replace("\\", "/")
    payload = {
        "video_file": "S01E01 - Volume 1.mp4",
        "chapters": [
            {
                "title": "Guard",
                "start": 0.0,
                "end": 300.0,
                "transcript_raw": "<10.00> keep the elbow tight",
                "transcript_cleaned": "keep the elbow tight",
                "concepts": ["Keep the elbow tight."],
                "suggested_tags": ["elbow"],
                "techniques": [],
            }
        ],
    }
    dest = out / "xai" / rel
    dest.parent.mkdir(parents=True)
    dest.write_text(json.dumps(payload), encoding="utf-8")
    openai = dict(payload)
    openai["chapters"] = [dict(payload["chapters"][0], transcript_cleaned="finish the choke")]
    other = out / "openai" / rel
    other.parent.mkdir(parents=True)
    other.write_text(json.dumps(openai), encoding="utf-8")
    buf = io.StringIO()
    code = compare_llm.refresh_from_existing(
        out, providers=("xai", "openai"), stdout=buf
    )
    assert code == 0
    metrics = json.loads((out / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["disagreements"][0]["title"] == "Guard"
    assert "xai/openai" in metrics["disagreements"][0]["pair_f1"] or "openai/xai" in metrics["disagreements"][0]["pair_f1"]


def test_methods_bakeoff_two_trees_one_source(tmp_path: Path):
    corpus = tmp_path / "corpus"
    out = tmp_path / "out"
    source = _write_volume(corpus, _nested_payload(cleaned=True))
    before = source.read_bytes()

    def one_call(_prompt: str) -> str:
        return json.dumps(
            {
                "transcript_cleaned": "one cleaned",
                "concepts": ["one idea"],
                "suggested_tags": ["one"],
                "techniques": [{"named_move": "Hip bump", "main_ideas": "Win the underhook."}],
            }
        )

    def cleaner(_prompt: str) -> str:
        return json.dumps({"transcript_cleaned": "staged cleaned"})

    def extractor(_prompt: str) -> str:
        return json.dumps(
            {
                "concepts": ["staged idea"],
                "techniques": [
                    {"named_move": "Hip bump sweep", "main_ideas": "Get hips under."}
                ],
            }
        )

    buf = io.StringIO()
    code = compare_llm.run(
        corpus,
        out,
        volumes=[REL],
        methods=("one-call", "staged"),
        provider="xai",
        model="grok-4.3",
        method_completers={
            "one-call": {"completer": one_call},
            "staged": {"cleaner": cleaner, "extractor": extractor},
        },
        stdout=buf,
    )

    assert code == 0
    assert source.read_bytes() == before
    one = json.loads((out / "one-call" / REL).read_text(encoding="utf-8"))
    staged = json.loads((out / "staged" / REL).read_text(encoding="utf-8"))
    assert one["chapters"][0]["transcript_cleaned"] == "one cleaned"
    assert staged["chapters"][0]["transcript_cleaned"] == "staged cleaned"
    assert one["chapters"][0]["concepts"] == ["one idea"]
    assert staged["chapters"][0]["concepts"] == ["staged idea"]
    report = json.loads((out / "report.json").read_text(encoding="utf-8"))
    chapter = report["volumes"][0]["chapters"][0]
    assert chapter["by_method"]["one-call"]["cleaned_chars"] == len("one cleaned")
    assert chapter["by_method"]["staged"]["cleaned_chars"] == len("staged cleaned")
    assert chapter["by_method"]["one-call"]["concepts"] == ["one idea"]
    assert chapter["by_method"]["staged"]["concepts"] == ["staged idea"]
    assert chapter["by_method"]["one-call"]["named_moves"] == ["Hip bump"]
    assert chapter["by_method"]["staged"]["named_moves"] == ["Hip bump sweep"]
    assert chapter["by_method"]["one-call"]["technique_count"] == 1
    assert chapter["by_method"]["staged"]["technique_count"] == 1
    markdown = (out / "report.md").read_text(encoding="utf-8")
    assert "LLM method comparison" in markdown
    assert "one idea" in markdown
    assert "staged idea" in markdown
    assert "technique_count" in markdown
    metrics = json.loads((out / "metrics.json").read_text(encoding="utf-8"))
    assert "one-call" in metrics["providers"]
    assert "staged" in metrics["providers"]
    assert not (out / "xai").exists()


def test_duplicate_titles_keep_separate_report_rows(tmp_path: Path):
    corpus = tmp_path / "corpus"
    out = tmp_path / "out"
    payload = {
        "video_file": "S01E01 - Volume 1.mp4",
        "chapters": [
            {
                "title": "Overview",
                "start": 0.0,
                "end": 300.0,
                "transcript_raw": "<10.00> first overview",
            },
            {
                "title": "Overview",
                "start": 300.0,
                "end": 600.0,
                "transcript_raw": "<310.00> second overview",
            },
        ],
        "language": "en",
    }
    _write_volume(corpus, payload)
    counts = {"xai": 0, "openai": 0}

    def labeled(name: str):
        def completer(_prompt: str) -> str:
            counts[name] += 1
            return json.dumps(
                {
                    "transcript_cleaned": f"{name} {counts[name]}",
                    "concepts": [f"{name} idea {counts[name]}"],
                    "suggested_tags": [name],
                    "techniques": [],
                }
            )

        return completer

    code = compare_llm.run(
        corpus,
        out,
        volumes=[REL],
        providers=("xai", "openai"),
        completers={"xai": labeled("xai"), "openai": labeled("openai")},
        stdout=io.StringIO(),
    )
    assert code == 0
    chapters = json.loads((out / "report.json").read_text(encoding="utf-8"))[
        "volumes"
    ][0]["chapters"]
    assert len(chapters) == 2
    assert chapters[0]["title"] == "Overview"
    assert chapters[1]["title"] == "Overview"
    assert chapters[0]["by_provider"]["xai"]["concepts"] == ["xai idea 1"]
    assert chapters[1]["by_provider"]["xai"]["concepts"] == ["xai idea 2"]
    assert chapters[0]["by_provider"]["openai"]["concepts"] == ["openai idea 1"]
    assert chapters[1]["by_provider"]["openai"]["concepts"] == ["openai idea 2"]
    metrics = json.loads((out / "metrics.json").read_text(encoding="utf-8"))
    titles = [row["title"] for row in metrics["disagreements"]]
    assert titles.count("Overview") == 2


def test_methods_max_chapters_matches_chapter_count(tmp_path: Path):
    corpus = tmp_path / "corpus"
    out = tmp_path / "out"
    _write_volume(corpus, _nested_payload())
    counts = {"one": 0, "clean": 0, "extract": 0}

    def one_call(_prompt: str) -> str:
        counts["one"] += 1
        return json.dumps(
            {
                "transcript_cleaned": "one cleaned",
                "concepts": ["one"],
                "suggested_tags": ["one"],
                "techniques": [],
            }
        )

    def cleaner(_prompt: str) -> str:
        counts["clean"] += 1
        return json.dumps({"transcript_cleaned": "staged cleaned"})

    def extractor(_prompt: str) -> str:
        counts["extract"] += 1
        return json.dumps({"concepts": ["staged"], "techniques": []})

    buf = io.StringIO()
    code = compare_llm.run(
        corpus,
        out,
        volumes=[REL],
        methods=("one-call", "staged"),
        provider="xai",
        model="grok-4.3",
        max_chapters=1,
        method_completers={
            "one-call": {"completer": one_call},
            "staged": {"cleaner": cleaner, "extractor": extractor},
        },
        stdout=buf,
    )
    assert code == 0
    assert counts == {"one": 1, "clean": 1, "extract": 1}
    assert "1 per method" in buf.getvalue()
    one = json.loads((out / "one-call" / REL).read_text(encoding="utf-8"))
    staged = json.loads((out / "staged" / REL).read_text(encoding="utf-8"))
    assert "transcript_cleaned" in one["chapters"][0]
    assert "transcript_cleaned" not in one["chapters"][1]
    assert "transcript_cleaned" in staged["chapters"][0]
    assert "concepts" in staged["chapters"][0]
    assert "transcript_cleaned" not in staged["chapters"][1]


def test_methods_rejects_non_default_providers(tmp_path: Path, capsys):
    code = compare_llm.main(
        [
            "--corpus",
            str(tmp_path / "corpus"),
            "--out",
            str(tmp_path / "out"),
            "--methods",
            "one-call,staged",
            "--providers",
            "openai",
            "--volume",
            REL,
        ]
    )
    assert code == 2
    err = capsys.readouterr().err
    assert "--methods" in err
    assert "--providers" in err


def test_missing_volume_fails(tmp_path: Path):
    buf = io.StringIO()
    code = compare_llm.run(
        tmp_path / "corpus",
        tmp_path / "out",
        volumes=["missing.json"],
        stdout=buf,
    )
    assert code == 1
    assert "missing.json" in buf.getvalue()
