"""Pipeline command: one run over a temp tree with stand-in stages."""

from __future__ import annotations

import io
from pathlib import Path

import run_pipeline


def _show(library: Path, name: str) -> Path:
    path = library / name
    path.mkdir()
    (path / "Volume 1.mp4").write_bytes(b"fake-video")
    return path


def _standins():
    calls = {"match": [], "organize": [], "detect": [], "transcribe": []}

    def match(folder: Path) -> str:
        calls["match"].append(folder)
        return "https://bjjfanatics.com/products/half-guard"

    def organize(folder: Path, url: str | None, *, apply: bool) -> int:
        calls["organize"].append({"folder": folder, "url": url, "apply": apply})
        if apply:
            (folder / "tvshow.nfo").write_text("<tvshow/>", encoding="utf-8")
            season = folder / "Season 01"
            season.mkdir(exist_ok=True)
            dest = season / "S01E01 - Volume 1.mp4"
            src = folder / "Volume 1.mp4"
            if src.exists() and not dest.exists():
                src.replace(dest)
        return 0

    def detect(video: Path, *, force: bool, apply: bool) -> int:
        calls["detect"].append({"video": video, "force": force, "apply": apply})
        return 0

    def transcribe(video: Path, output: Path, *, force: bool) -> int:
        calls["transcribe"].append({"video": video, "output": output, "force": force})
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text('{"segments": []}', encoding="utf-8")
        return 0

    return calls, match, organize, detect, transcribe


def _run(library: Path, corpus: Path, *, apply: bool = False, **kwargs):
    calls, match, organize, detect, transcribe = _standins()
    buf = io.StringIO()
    code = run_pipeline.run(
        library,
        corpus,
        apply=apply,
        match=match,
        organize=organize,
        detect=detect,
        transcribe=transcribe,
        stdout=buf,
        isatty=False,
        **kwargs,
    )
    return code, buf.getvalue(), calls


def test_apply_runs_match_organize_transcribe_not_detect(tmp_path: Path):
    library = tmp_path / "lib"
    library.mkdir()
    show = _show(library, "Half Guard Anthology")
    corpus = tmp_path / "corpus"

    code, out, calls = _run(library, corpus, apply=True)

    assert code == 0
    assert [folder.name for folder in calls["match"]] == [show.name]
    assert [item["folder"].name for item in calls["organize"]] == [show.name]
    assert calls["organize"][0]["apply"] is True
    assert calls["organize"][0]["url"] == "https://bjjfanatics.com/products/half-guard"
    assert calls["detect"] == []
    assert [item["video"].name for item in calls["transcribe"]] == ["S01E01 - Volume 1.mp4"]
    matches = library / "bjjfanatics_matches.csv"
    assert matches.is_file()
    text = matches.read_text(encoding="utf-8")
    assert "https://bjjfanatics.com/products/half-guard" in text
    assert (show / "tvshow.nfo").is_file()
    assert list(corpus.rglob("*.json"))
    assert "RUN" in out
    assert "match" in out.lower()
    assert "organize" in out.lower()
    assert "transcribe" in out.lower()


def test_dry_run_writes_nothing_and_does_not_transcribe(tmp_path: Path):
    library = tmp_path / "lib"
    library.mkdir()
    show = _show(library, "Half Guard Anthology")
    corpus = tmp_path / "corpus"
    before = {p.relative_to(show): p.stat().st_mtime_ns for p in show.rglob("*")}

    code, out, calls = _run(library, corpus, apply=False)

    assert code == 0
    assert calls["match"] == []
    assert calls["transcribe"] == []
    assert calls["detect"] == []
    assert not corpus.exists() or not any(corpus.rglob("*.json"))
    assert (library / "bjjfanatics_matches.csv").exists() is False
    after = {p.relative_to(show): p.stat().st_mtime_ns for p in show.rglob("*")}
    assert after == before
    assert "RUN" in out
    assert "FAIL" not in out


def test_skip_when_artifacts_exist(tmp_path: Path):
    library = tmp_path / "lib"
    library.mkdir()
    show = _show(library, "Half Guard Anthology")
    (show / "tvshow.nfo").write_text("<tvshow/>", encoding="utf-8")
    season = show / "Season 01"
    season.mkdir()
    (show / "Volume 1.mp4").replace(season / "S01E01 - Volume 1.mp4")
    matches = library / "bjjfanatics_matches.csv"
    matches.write_text(
        f"folder_path,product_url\n{show.resolve()},https://bjjfanatics.com/products/half-guard\n",
        encoding="utf-8",
    )
    corpus = tmp_path / "corpus"
    out_json = corpus / show.name / "Season 01" / "S01E01 - Volume 1.json"
    out_json.parent.mkdir(parents=True)
    out_json.write_text('{"segments": []}', encoding="utf-8")

    code, out, calls = _run(library, corpus, apply=True)

    assert code == 0
    assert calls["match"] == []
    assert calls["organize"] == []
    assert calls["transcribe"] == []
    assert "SKIP" in out
    assert "FAIL" not in out


def test_force_reruns_all_selected_stages(tmp_path: Path):
    library = tmp_path / "lib"
    library.mkdir()
    show = _show(library, "Half Guard Anthology")
    (show / "tvshow.nfo").write_text("<tvshow/>", encoding="utf-8")
    matches = library / "bjjfanatics_matches.csv"
    matches.write_text(
        f"folder_path,product_url\n{show.resolve()},https://bjjfanatics.com/products/stale\n",
        encoding="utf-8",
    )
    corpus = tmp_path / "corpus"
    out_json = corpus / show.name / "Volume 1.json"
    out_json.parent.mkdir(parents=True)
    out_json.write_text('{"segments": []}', encoding="utf-8")

    code, out, calls = _run(library, corpus, apply=True, force=True)

    assert code == 0
    assert calls["match"]
    assert calls["organize"]
    assert calls["transcribe"]
    assert calls["detect"] == []
    assert "RUN" in out


def test_force_stage_reruns_only_that_unit(tmp_path: Path):
    library = tmp_path / "lib"
    library.mkdir()
    show = library / "Half Guard Anthology"
    show.mkdir()
    season = show / "Season 01"
    season.mkdir()
    (season / "S01E01 - Volume 1.mp4").write_bytes(b"fake-video")
    (show / "tvshow.nfo").write_text("<tvshow/>", encoding="utf-8")
    matches = library / "bjjfanatics_matches.csv"
    matches.write_text(
        f"folder_path,product_url\n{show.resolve()},https://bjjfanatics.com/products/half-guard\n",
        encoding="utf-8",
    )
    corpus = tmp_path / "corpus"
    out_json = corpus / show.name / "Season 01" / "S01E01 - Volume 1.json"
    out_json.parent.mkdir(parents=True)
    out_json.write_text('{"segments": []}', encoding="utf-8")

    code, out, calls = _run(library, corpus, apply=True, force_stage="organize")

    assert code == 0
    assert calls["match"] == []
    assert calls["organize"]
    assert calls["transcribe"] == []
    assert "organize" in out.lower()


def test_csv_url_is_passed_to_organize_without_prompt(tmp_path: Path):
    library = tmp_path / "lib"
    library.mkdir()
    show = _show(library, "Half Guard Anthology")
    url = "https://bjjfanatics.com/products/the-half-guard-anthology"
    matches = library / "bjjfanatics_matches.csv"
    matches.write_text(
        f"folder_path,product_url\n{show.resolve()},{url}\n",
        encoding="utf-8",
    )
    corpus = tmp_path / "corpus"

    code, out, calls = _run(library, corpus, apply=True)

    assert code == 0
    assert calls["match"] == []
    assert calls["organize"][0]["url"] == url
    assert calls["organize"][0]["apply"] is True


def test_missing_url_outside_terminal_fails_organize(tmp_path: Path):
    library = tmp_path / "lib"
    library.mkdir()
    show = _show(library, "New Wave Jiu Jitsu")
    corpus = tmp_path / "corpus"
    calls, match, organize, detect, transcribe = _standins()

    def no_url(folder: Path) -> str:
        calls["match"].append(folder)
        return ""

    buf = io.StringIO()
    code = run_pipeline.run(
        library,
        corpus,
        apply=True,
        match=no_url,
        organize=organize,
        detect=detect,
        transcribe=transcribe,
        stdout=buf,
        isatty=False,
    )
    out = buf.getvalue()

    assert code == 1
    assert calls["organize"] == []
    assert "FAIL" in out
    assert "organize" in out.lower()
    assert show.name in out


def test_already_nfo_dry_run_does_not_call_organize(tmp_path: Path):
    library = tmp_path / "lib"
    library.mkdir()
    show = _show(library, "Half Guard Anthology")
    (show / "tvshow.nfo").write_text("<tvshow/>", encoding="utf-8")
    matches = library / "bjjfanatics_matches.csv"
    matches.write_text(
        f"folder_path,product_url\n{show.resolve()},https://bjjfanatics.com/products/half-guard\n",
        encoding="utf-8",
    )
    corpus = tmp_path / "corpus"

    code, out, calls = _run(library, corpus, apply=False)

    assert code == 0
    assert calls["organize"] == []
    assert calls["transcribe"] == []
    assert "SKIP" in out


def test_missing_nfo_dry_run_may_call_organize_without_writes(tmp_path: Path):
    library = tmp_path / "lib"
    library.mkdir()
    show = _show(library, "Half Guard Anthology")
    url = "https://bjjfanatics.com/products/half-guard"
    matches = library / "bjjfanatics_matches.csv"
    matches.write_text(
        f"folder_path,product_url\n{show.resolve()},{url}\n",
        encoding="utf-8",
    )
    corpus = tmp_path / "corpus"
    before = list(show.rglob("*"))

    code, out, calls = _run(library, corpus, apply=False)

    assert code == 0
    assert calls["organize"]
    assert calls["organize"][0]["apply"] is False
    assert calls["organize"][0]["url"] == url
    assert calls["transcribe"] == []
    assert not (show / "tvshow.nfo").exists()
    assert list(show.rglob("*")) == before


def test_apply_does_not_embed_without_flag(tmp_path: Path):
    library = tmp_path / "lib"
    library.mkdir()
    _show(library, "Half Guard Anthology")
    corpus = tmp_path / "corpus"

    code, out, calls = _run(library, corpus, apply=True)

    assert code == 0
    assert calls["detect"] == []
    assert "embed" not in out.lower()


def test_embed_flag_is_separate_from_apply(tmp_path: Path):
    library = tmp_path / "lib"
    library.mkdir()
    show = _show(library, "Half Guard Anthology")
    (show / "tvshow.nfo").write_text("<tvshow/>", encoding="utf-8")
    matches = library / "bjjfanatics_matches.csv"
    matches.write_text(
        f"folder_path,product_url\n{show.resolve()},https://bjjfanatics.com/products/half-guard\n",
        encoding="utf-8",
    )
    corpus = tmp_path / "corpus"
    out_json = corpus / show.name / "Volume 1.json"
    out_json.parent.mkdir(parents=True)
    out_json.write_text('{"segments": []}', encoding="utf-8")

    code, out, calls = _run(library, corpus, apply=True, embed=True)

    assert code == 0
    assert calls["detect"]
    assert calls["detect"][0]["apply"] is True
    assert "embed" in out.lower()


def test_failed_stage_exits_1(tmp_path: Path):
    library = tmp_path / "lib"
    library.mkdir()
    _show(library, "Half Guard Anthology")
    corpus = tmp_path / "corpus"
    calls, match, organize, detect, transcribe = _standins()

    def boom(folder: Path, url: str | None, *, apply: bool) -> int:
        calls["organize"].append({"folder": folder, "url": url, "apply": apply})
        return 1

    buf = io.StringIO()
    code = run_pipeline.run(
        library,
        corpus,
        apply=True,
        match=match,
        organize=boom,
        detect=detect,
        transcribe=transcribe,
        stdout=buf,
        isatty=False,
    )

    assert code == 1
    assert "FAIL" in buf.getvalue()


def test_transcribe_walks_post_organize_volumes_not_pre_concat_clips(tmp_path: Path):
    library = tmp_path / "lib"
    library.mkdir()
    show = library / "Half Guard Anthology"
    show.mkdir()
    (show / "01 - Intro.mp4").write_bytes(b"clip")
    corpus = tmp_path / "corpus"

    calls, match, organize, detect, transcribe = _standins()

    def organize_to_volume(folder: Path, url: str | None, *, apply: bool) -> int:
        calls["organize"].append({"folder": folder, "url": url, "apply": apply})
        (folder / "01 - Intro.mp4").unlink()
        season = folder / "Season 01"
        season.mkdir()
        (season / "S01E01 - Volume 1.mp4").write_bytes(b"volume")
        (folder / "tvshow.nfo").write_text("<tvshow/>", encoding="utf-8")
        return 0

    buf = io.StringIO()
    code = run_pipeline.run(
        library,
        corpus,
        apply=True,
        match=match,
        organize=organize_to_volume,
        detect=detect,
        transcribe=transcribe,
        stdout=buf,
        isatty=False,
    )

    assert code == 0
    names = [item["video"].name for item in calls["transcribe"]]
    assert names == ["S01E01 - Volume 1.mp4"]
    assert "01 - Intro.mp4" not in names


def test_parser_omitting_apply_is_dry_run():
    args = run_pipeline.build_parser().parse_args(
        ["--library", r"D:\instructionals", "--corpus", r"D:\corpus"]
    )
    assert args.apply is False
    assert args.embed is False
    assert args.force is False
    assert args.force_stage is None
