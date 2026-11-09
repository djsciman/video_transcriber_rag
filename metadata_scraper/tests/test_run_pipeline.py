"""Pipeline command: one run over a temp tree with stand-in stages."""

from __future__ import annotations

import io
import json
from pathlib import Path

import run_pipeline


def _show(library: Path, name: str) -> Path:
    path = library / name
    path.mkdir()
    (path / "Volume 1.mp4").write_bytes(b"fake-video")
    return path


def _standins():
    calls = {"match": [], "organize": [], "detect": [], "transcribe": [], "prepare": []}

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
        if output.is_file():
            return 0
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text('{"segments": []}', encoding="utf-8")
        return 0

    def prepare(json_path: Path, corpus_root: Path, video_library_root: Path | None = None) -> int:
        calls["prepare"].append(
            {
                "json_path": json_path,
                "corpus_root": corpus_root,
                "video_library_root": video_library_root,
            }
        )
        return 0

    return calls, match, organize, detect, transcribe, prepare


def _run(library: Path, corpus: Path, *, apply: bool = False, **kwargs):
    calls, match, organize, detect, transcribe, prepare = _standins()
    buf = io.StringIO()
    kwargs.setdefault("chapter_count", lambda _video: 0)
    kwargs.setdefault("isatty", False)
    inject_prepare = kwargs.pop("inject_prepare", True)
    code = run_pipeline.run(
        library,
        corpus,
        apply=apply,
        match=match,
        organize=organize,
        detect=detect,
        transcribe=transcribe,
        **({"prepare": prepare} if inject_prepare else {}),
        stdout=buf,
        **kwargs,
    )
    return code, buf.getvalue(), calls


def test_apply_runs_match_organize_detect_transcribe(tmp_path: Path):
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
    assert [item["video"].name for item in calls["detect"]] == ["S01E01 - Volume 1.mp4"]
    assert calls["detect"][0]["apply"] is False
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
    assert "detect" in out.lower()
    assert "transcribe" in out.lower()
    assert "prepare" in out.lower()


def test_dry_run_writes_nothing_and_does_not_transcribe(tmp_path: Path):
    library = tmp_path / "lib"
    library.mkdir()
    show = _show(library, "Half Guard Anthology")
    matches = library / "bjjfanatics_matches.csv"
    matches.write_text(
        f"folder_path,product_url\n{show.resolve()},https://bjjfanatics.com/products/half-guard\n",
        encoding="utf-8",
    )
    corpus = tmp_path / "corpus"
    before = {p.relative_to(show): p.stat().st_mtime_ns for p in show.rglob("*")}
    csv_before = matches.read_text(encoding="utf-8")

    code, out, calls = _run(library, corpus, apply=False)

    assert code == 0
    assert calls["match"] == []
    assert calls["transcribe"] == []
    assert calls["detect"] == []
    assert not corpus.exists() or not any(corpus.rglob("*.json"))
    assert matches.read_text(encoding="utf-8") == csv_before
    after = {p.relative_to(show): p.stat().st_mtime_ns for p in show.rglob("*")}
    assert after == before
    assert "RUN" in out
    assert "detect" in out.lower()
    assert "FAIL" not in out


def test_nfo_without_season_folder_does_not_skip_organize(tmp_path: Path):
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

    code, out, calls = _run(library, corpus, apply=True)

    assert code == 0
    assert calls["organize"]
    assert calls["organize"][0]["apply"] is True
    assert any(line.startswith("RUN") and "organize" in line for line in out.splitlines())
    assert not any(line.startswith("SKIP") and "organize" in line for line in out.splitlines())


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

    code, out, calls = _run(library, corpus, apply=True, chapter_count=lambda _video: 2)

    assert code == 0
    assert calls["match"] == []
    assert calls["organize"] == []
    assert calls["detect"] == []
    assert [item["video"].name for item in calls["transcribe"]] == ["S01E01 - Volume 1.mp4"]
    assert calls["transcribe"][0]["force"] is False
    assert any(line.startswith("SKIP") and "transcribe" in line for line in out.splitlines())
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
    assert calls["detect"]
    assert calls["detect"][0]["apply"] is False
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

    code, out, calls = _run(
        library, corpus, apply=True, force_stage="organize", chapter_count=lambda _video: 2
    )

    assert code == 0
    assert calls["match"] == []
    assert calls["organize"]
    assert calls["detect"] == []
    assert [item["video"].name for item in calls["transcribe"]] == ["S01E01 - Volume 1.mp4"]
    assert calls["transcribe"][0]["force"] is False
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
    calls, match, organize, detect, transcribe, prepare = _standins()

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
        prepare=prepare,
        chapter_count=lambda _video: 0,
        stdout=buf,
        isatty=False,
    )
    out = buf.getvalue()

    assert code == 1
    assert calls["organize"] == []
    assert "FAIL" in out
    assert "organize" in out.lower()
    assert show.name in out


def test_missing_url_outside_terminal_fails_organize_on_dry_run(tmp_path: Path):
    library = tmp_path / "lib"
    library.mkdir()
    show = _show(library, "New Wave Jiu Jitsu")
    corpus = tmp_path / "corpus"

    code, out, calls = _run(library, corpus, apply=False, isatty=False)

    assert code == 1
    assert calls["organize"] == []
    assert any(line.startswith("FAIL") and "organize" in line for line in out.splitlines())
    assert show.name in out


def test_missing_url_in_terminal_calls_organize_on_dry_run(tmp_path: Path):
    library = tmp_path / "lib"
    library.mkdir()
    show = _show(library, "New Wave Jiu Jitsu")
    corpus = tmp_path / "corpus"

    code, out, calls = _run(library, corpus, apply=False, isatty=True)

    assert code == 0
    assert calls["organize"]
    assert calls["organize"][0]["folder"] == show
    assert calls["organize"][0]["url"] is None
    assert calls["organize"][0]["apply"] is False
    assert any(line.startswith("RUN") and "organize" in line for line in out.splitlines())
    assert "FAIL" not in out


def test_missing_url_in_terminal_calls_organize_on_apply(tmp_path: Path):
    library = tmp_path / "lib"
    library.mkdir()
    show = _show(library, "New Wave Jiu Jitsu")
    corpus = tmp_path / "corpus"
    calls, match, organize, detect, transcribe, prepare = _standins()

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
        prepare=prepare,
        chapter_count=lambda _video: 0,
        stdout=buf,
        isatty=True,
    )
    out = buf.getvalue()

    assert code == 0
    assert calls["organize"]
    assert calls["organize"][0]["folder"] == show
    assert calls["organize"][0]["url"] is None
    assert calls["organize"][0]["apply"] is True
    assert any(line.startswith("RUN") and "organize" in line for line in out.splitlines())


def test_already_organized_dry_run_does_not_call_organize(tmp_path: Path):
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

    code, out, calls = _run(library, corpus, apply=False)

    assert code == 0
    assert calls["organize"] == []
    assert calls["transcribe"] == []
    assert any(line.startswith("SKIP") and "organize" in line for line in out.splitlines())


def test_season_folder_without_nfo_does_not_skip_organize(tmp_path: Path):
    library = tmp_path / "lib"
    library.mkdir()
    show = library / "Half Guard Anthology"
    show.mkdir()
    season = show / "Season 01"
    season.mkdir()
    (season / "S01E01 - Volume 1.mp4").write_bytes(b"fake-video")
    matches = library / "bjjfanatics_matches.csv"
    matches.write_text(
        f"folder_path,product_url\n{show.resolve()},https://bjjfanatics.com/products/half-guard\n",
        encoding="utf-8",
    )
    corpus = tmp_path / "corpus"

    code, out, calls = _run(library, corpus, apply=True)

    assert code == 0
    assert calls["organize"]
    assert not any(line.startswith("SKIP") and "organize" in line for line in out.splitlines())


def test_extras_folder_is_not_a_season_for_organize_skip(tmp_path: Path):
    library = tmp_path / "lib"
    library.mkdir()
    show = _show(library, "Half Guard Anthology")
    (show / "tvshow.nfo").write_text("<tvshow/>", encoding="utf-8")
    extras = show / "extras"
    extras.mkdir()
    (show / "Volume 1.mp4").replace(extras / "sample.mp4")
    matches = library / "bjjfanatics_matches.csv"
    matches.write_text(
        f"folder_path,product_url\n{show.resolve()},https://bjjfanatics.com/products/half-guard\n",
        encoding="utf-8",
    )
    corpus = tmp_path / "corpus"

    code, out, calls = _run(library, corpus, apply=True)

    assert code == 0
    assert calls["organize"]
    assert not any(line.startswith("SKIP") and "organize" in line for line in out.splitlines())


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
    assert calls["detect"]
    assert all(item["apply"] is False for item in calls["detect"])
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
    assert any(item["apply"] is False for item in calls["detect"])
    assert any(item["apply"] is True for item in calls["detect"])
    assert "embed" in out.lower()


def test_failed_stage_exits_1(tmp_path: Path):
    library = tmp_path / "lib"
    library.mkdir()
    _show(library, "Half Guard Anthology")
    corpus = tmp_path / "corpus"
    calls, match, organize, detect, transcribe, prepare = _standins()

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
        prepare=prepare,
        chapter_count=lambda _video: 0,
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

    calls, match, organize, detect, transcribe, prepare = _standins()

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
        prepare=prepare,
        chapter_count=lambda _video: 0,
        stdout=buf,
        isatty=False,
    )

    assert code == 0
    names = [item["video"].name for item in calls["transcribe"]]
    assert names == ["S01E01 - Volume 1.mp4"]
    assert "01 - Intro.mp4" not in names
    assert [item["video"].name for item in calls["detect"]] == ["S01E01 - Volume 1.mp4"]


def test_apply_stamps_transcript_when_segments_exist(tmp_path: Path):
    library = tmp_path / "lib"
    library.mkdir()
    show = _organized_show(library, "Half Guard Anthology", ["S01E01 - Volume 1.mp4"])
    corpus = tmp_path / "corpus"
    out_json = corpus / show.name / "Season 01" / "S01E01 - Volume 1.json"
    out_json.parent.mkdir(parents=True)
    out_json.write_text('{"segments": []}', encoding="utf-8")

    code, out, calls = _run(library, corpus, apply=True, chapter_count=lambda _video: 2)

    assert code == 0
    assert [item["video"].name for item in calls["transcribe"]] == ["S01E01 - Volume 1.mp4"]
    assert calls["transcribe"][0]["output"] == out_json
    assert calls["transcribe"][0]["force"] is False
    assert any(line.startswith("SKIP") and "transcribe" in line for line in out.splitlines())


def test_dry_run_skips_transcribe_when_segments_exist(tmp_path: Path):
    library = tmp_path / "lib"
    library.mkdir()
    show = _organized_show(library, "Half Guard Anthology", ["S01E01 - Volume 1.mp4"])
    corpus = tmp_path / "corpus"
    out_json = corpus / show.name / "Season 01" / "S01E01 - Volume 1.json"
    out_json.parent.mkdir(parents=True)
    out_json.write_text('{"segments": []}', encoding="utf-8")

    code, out, calls = _run(library, corpus, apply=False, chapter_count=lambda _video: 2)

    assert code == 0
    assert calls["transcribe"] == []
    assert any(line.startswith("SKIP") and "transcribe" in line for line in out.splitlines())


def test_extras_are_not_passed_to_detect_or_transcribe(tmp_path: Path):
    library = tmp_path / "lib"
    library.mkdir()
    show = _organized_show(library, "Half Guard Anthology", ["S01E01 - Volume 1.mp4"])
    extras = show / "Season 01" / "extras"
    extras.mkdir()
    (extras / "sample.mp4").write_bytes(b"trailer")
    (show / "trailers").mkdir()
    (show / "trailers" / "promo.mp4").write_bytes(b"promo")
    corpus = tmp_path / "corpus"

    code, out, calls = _run(library, corpus, apply=True)

    assert code == 0
    detect_names = [item["video"].name for item in calls["detect"]]
    transcribe_names = [item["video"].name for item in calls["transcribe"]]
    assert detect_names == ["S01E01 - Volume 1.mp4"]
    assert transcribe_names == ["S01E01 - Volume 1.mp4"]
    assert "sample.mp4" not in detect_names
    assert "promo.mp4" not in transcribe_names


def test_parser_omitting_apply_is_dry_run():
    args = run_pipeline.build_parser().parse_args(
        ["--library", r"D:\instructionals", "--corpus", r"D:\corpus"]
    )
    assert args.apply is False
    assert args.embed is False
    assert args.force is False
    assert args.force_stage is None


def _organized_show(library: Path, name: str, videos: list[str]) -> Path:
    show = library / name
    season = show / "Season 01"
    season.mkdir(parents=True)
    (show / "tvshow.nfo").write_text("<tvshow/>", encoding="utf-8")
    for filename in videos:
        (season / filename).write_bytes(b"fake-video")
    matches = library / "bjjfanatics_matches.csv"
    matches.write_text(
        f"folder_path,product_url\n{show.resolve()},https://bjjfanatics.com/products/half-guard\n",
        encoding="utf-8",
    )
    return show


def test_detect_skips_when_container_has_chapters(tmp_path: Path):
    library = tmp_path / "lib"
    library.mkdir()
    show = _organized_show(library, "Half Guard Anthology", ["S01E01 - Volume 1.mp4"])
    corpus = tmp_path / "corpus"
    probed: list[str] = []

    def chapter_count(video: Path) -> int:
        probed.append(video.name)
        return 4

    code, out, calls = _run(library, corpus, apply=True, chapter_count=chapter_count)

    assert code == 0
    assert probed == ["S01E01 - Volume 1.mp4"]
    assert calls["detect"] == []
    assert "SKIP" in out
    assert "detect" in out.lower()
    assert show.name in out


def test_detect_skips_when_sidecar_exists(tmp_path: Path):
    library = tmp_path / "lib"
    library.mkdir()
    _organized_show(library, "Half Guard Anthology", ["S01E01 - Volume 1.mp4"])
    video = library / "Half Guard Anthology" / "Season 01" / "S01E01 - Volume 1.mp4"
    sidecar = video.with_name(f"{video.stem}_chapters.csv")
    sidecar.write_text("Chapter,StartTimestamp,EndTimestamp\n", encoding="utf-8")
    corpus = tmp_path / "corpus"

    code, out, calls = _run(library, corpus, apply=True)

    assert code == 0
    assert calls["detect"] == []
    assert "SKIP" in out
    assert "detect" in out.lower()
    assert sidecar.read_text(encoding="utf-8") == "Chapter,StartTimestamp,EndTimestamp\n"


def test_force_reruns_detect_when_sidecar_exists(tmp_path: Path):
    library = tmp_path / "lib"
    library.mkdir()
    _organized_show(library, "Half Guard Anthology", ["S01E01 - Volume 1.mp4"])
    video = library / "Half Guard Anthology" / "Season 01" / "S01E01 - Volume 1.mp4"
    (video.with_name(f"{video.stem}_chapters.csv")).write_text("old\n", encoding="utf-8")
    corpus = tmp_path / "corpus"

    code, out, calls = _run(library, corpus, apply=True, force=True)

    assert code == 0
    assert [item["video"].name for item in calls["detect"]] == ["S01E01 - Volume 1.mp4"]
    assert calls["detect"][0]["force"] is True
    assert calls["detect"][0]["apply"] is False
    assert "RUN" in out


def test_force_does_not_detect_when_container_has_chapters(tmp_path: Path):
    library = tmp_path / "lib"
    library.mkdir()
    _organized_show(library, "Half Guard Anthology", ["S01E01 - Volume 1.mp4"])
    corpus = tmp_path / "corpus"

    code, out, calls = _run(
        library, corpus, apply=True, force=True, chapter_count=lambda _video: 3
    )

    assert code == 0
    assert calls["detect"] == []
    assert "SKIP" in out
    assert "detect" in out.lower()


def test_uncombined_chapter_file_season_warns_and_skips_detect(tmp_path: Path):
    library = tmp_path / "lib"
    library.mkdir()
    _organized_show(
        library,
        "Collar Sleeve",
        ["01.01 - Intro.mp4", "01.02 - Collar And Sleeve.mp4", "01.03 - Finish.mp4"],
    )
    corpus = tmp_path / "corpus"

    code, out, calls = _run(library, corpus, apply=True)

    assert code == 0
    assert calls["detect"] == []
    assert "WARN" in out
    assert "uncombined" in out.lower()
    assert "SKIP" in out
    assert "detect" in out.lower()


def test_force_stage_detect_runs_on_uncombined_season(tmp_path: Path):
    library = tmp_path / "lib"
    library.mkdir()
    _organized_show(
        library,
        "Collar Sleeve",
        ["01.01 - Intro.mp4", "01.02 - Collar And Sleeve.mp4"],
    )
    corpus = tmp_path / "corpus"

    code, out, calls = _run(library, corpus, apply=True, force_stage="detect")

    assert code == 0
    names = [item["video"].name for item in calls["detect"]]
    assert names == ["01.01 - Intro.mp4", "01.02 - Collar And Sleeve.mp4"]
    assert all(item["apply"] is False for item in calls["detect"])
    assert all(item["force"] is True for item in calls["detect"])
    assert calls["organize"] == []
    assert "RUN" in out


def test_detect_is_one_invocation_per_volume(tmp_path: Path):
    library = tmp_path / "lib"
    library.mkdir()
    _organized_show(
        library,
        "Half Guard Anthology",
        ["S01E01 - Volume 1.mp4", "S01E02 - Volume 2.mp4"],
    )
    corpus = tmp_path / "corpus"

    code, out, calls = _run(library, corpus, apply=True)

    assert code == 0
    names = [item["video"].name for item in calls["detect"]]
    assert names == ["S01E01 - Volume 1.mp4", "S01E02 - Volume 2.mp4"]
    assert all(item["apply"] is False for item in calls["detect"])


def test_parser_force_stage_includes_detect():
    args = run_pipeline.build_parser().parse_args(
        [
            "--library",
            r"D:\instructionals",
            "--corpus",
            r"D:\corpus",
            "--force-stage",
            "detect",
        ]
    )
    assert args.force_stage == "detect"
    assert run_pipeline.DEFAULT_STAGES == (
        "match",
        "organize",
        "detect",
        "transcribe",
        "prepare",
    )
    assert run_pipeline.STAGE_CHOICES == (
        "match",
        "organize",
        "detect",
        "transcribe",
        "prepare",
        "embed",
    )


def _eligible_payload() -> dict:
    return {
        "video_file": "S01E01 - Volume 1.mp4",
        "chapters": [
            {"title": "Guard", "start": 0.0, "end": 300.0},
            {"title": "Pass", "start": 300.0, "end": 600.0},
        ],
        "language": "en",
        "segments": [
            {"start": 10.0, "end": 20.0, "text": "in guard"},
            {"start": 290.0, "end": 310.0, "text": "straddling the start"},
        ],
    }


def _write_corpus_json(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def _prepare_line(out: str, status: str) -> bool:
    return any(
        line.startswith(status) and "prepare" in line for line in out.splitlines()
    )


def test_parser_force_stage_includes_prepare():
    args = run_pipeline.build_parser().parse_args(
        [
            "--library",
            r"D:\instructionals",
            "--corpus",
            r"D:\corpus",
            "--force-stage",
            "prepare",
        ]
    )
    assert args.force_stage == "prepare"


def test_embed_does_not_imply_prepare(tmp_path: Path):
    library = tmp_path / "lib"
    library.mkdir()
    _organized_show(library, "Half Guard Anthology", ["S01E01 - Volume 1.mp4"])
    corpus = tmp_path / "corpus"

    code, out, calls = _run(
        library, corpus, apply=True, stages=("match",), embed=True
    )

    assert code == 0
    assert calls["prepare"] == []
    assert "prepare" not in out.lower()
    assert "embed" in out.lower()


def test_dry_run_prints_run_for_prepare_and_does_not_call_it(tmp_path: Path):
    library = tmp_path / "lib"
    library.mkdir()
    show = _organized_show(
        library, "Arm Bars by John Danaher", ["S01E01 - Volume 1.mp4"]
    )
    corpus = tmp_path / "corpus"
    out_json = (
        corpus / show.name / "Season 01" / "S01E01 - Volume 1.json"
    )
    _write_corpus_json(out_json, _eligible_payload())
    before = out_json.read_bytes()

    code, out, calls = _run(
        library, corpus, apply=False, chapter_count=lambda _video: 2
    )

    assert code == 0
    assert calls["prepare"] == []
    assert out_json.read_bytes() == before
    assert _prepare_line(out, "RUN")
    assert not _prepare_line(out, "FAIL")


def test_dry_run_runs_prepare_when_only_transcript_raw_present(tmp_path: Path):
    library = tmp_path / "lib"
    library.mkdir()
    show = _organized_show(
        library, "Arm Bars by John Danaher", ["S01E01 - Volume 1.mp4"]
    )
    corpus = tmp_path / "corpus"
    out_json = (
        corpus / show.name / "Season 01" / "S01E01 - Volume 1.json"
    )
    payload = _eligible_payload()
    for chapter in payload["chapters"]:
        chapter["transcript_raw"] = "<10.00> already nested"
    _write_corpus_json(out_json, payload)
    before = out_json.read_bytes()

    code, out, calls = _run(
        library, corpus, apply=False, chapter_count=lambda _video: 2
    )

    assert code == 0
    assert calls["prepare"] == []
    assert out_json.read_bytes() == before
    assert _prepare_line(out, "RUN")
    assert not _prepare_line(out, "SKIP")


def test_dry_run_skips_prepare_when_transcript_cleaned_present(tmp_path: Path):
    library = tmp_path / "lib"
    library.mkdir()
    show = _organized_show(
        library, "Arm Bars by John Danaher", ["S01E01 - Volume 1.mp4"]
    )
    corpus = tmp_path / "corpus"
    out_json = (
        corpus / show.name / "Season 01" / "S01E01 - Volume 1.json"
    )
    payload = _eligible_payload()
    for chapter in payload["chapters"]:
        chapter["transcript_cleaned"] = "pared"
    _write_corpus_json(out_json, payload)
    before = out_json.read_bytes()

    code, out, calls = _run(
        library, corpus, apply=False, chapter_count=lambda _video: 2
    )

    assert code == 0
    assert calls["prepare"] == []
    assert out_json.read_bytes() == before
    assert _prepare_line(out, "SKIP")
    assert not _prepare_line(out, "RUN")


def test_apply_calls_prepare_on_eligible_volume(tmp_path: Path):
    library = tmp_path / "lib"
    library.mkdir()
    show = _organized_show(
        library, "Arm Bars by John Danaher", ["S01E01 - Volume 1.mp4"]
    )
    corpus = tmp_path / "corpus"
    out_json = (
        corpus / show.name / "Season 01" / "S01E01 - Volume 1.json"
    )
    _write_corpus_json(out_json, _eligible_payload())

    code, out, calls = _run(
        library, corpus, apply=True, chapter_count=lambda _video: 2
    )

    assert code == 0
    assert [item["json_path"] for item in calls["prepare"]] == [out_json]
    assert calls["prepare"][0]["corpus_root"] == corpus
    assert calls["prepare"][0]["video_library_root"] == library
    assert _prepare_line(out, "RUN")


def test_apply_nests_and_pares_via_default_prepare(tmp_path: Path, monkeypatch):
    library = tmp_path / "lib"
    library.mkdir()
    show = _organized_show(
        library, "Arm Bars by John Danaher", ["S01E01 - Volume 1.mp4"]
    )
    corpus = tmp_path / "corpus"
    out_json = (
        corpus / show.name / "Season 01" / "S01E01 - Volume 1.json"
    )
    _write_corpus_json(out_json, _eligible_payload())
    calls_model: list[str] = []

    def fake_complete(prompt: str) -> str:
        calls_model.append(prompt)
        return json.dumps({"transcript_cleaned": "pared", "suggested_tags": []})

    monkeypatch.setattr("bjj_pipeline.prepare.complete_chat", fake_complete)

    code, out, calls = _run(
        library,
        corpus,
        apply=True,
        chapter_count=lambda _video: 2,
        inject_prepare=False,
        stages=("prepare",),
    )

    assert code == 0
    assert calls["prepare"] == []
    assert len(calls_model) == 2
    data = json.loads(out_json.read_text(encoding="utf-8"))
    guard, passing = data["chapters"]
    assert "<290.00>" in guard["transcript_raw"]
    assert "<290.00>" in passing["transcript_raw"]
    assert guard["transcript_cleaned"] == "pared"
    assert passing["transcript_cleaned"] == "pared"
    assert guard["suggested_tags"] == []
    assert guard["previous_chapter"] == ""
    assert guard["next_chapter"] == "Pass"
    assert passing["previous_chapter"] == "Guard"
    assert passing["next_chapter"] == ""
    assert guard["instructor"] == "John Danaher"
    assert guard["instructional"] == show.name
    assert guard["volume"] == "S01E01 - Volume 1.mp4"
    assert data["segments"][1]["text"] == "straddling the start"
    assert _prepare_line(out, "RUN")


def test_second_apply_skips_prepare_when_transcript_cleaned_present(tmp_path: Path):
    library = tmp_path / "lib"
    library.mkdir()
    show = _organized_show(
        library, "Arm Bars by John Danaher", ["S01E01 - Volume 1.mp4"]
    )
    corpus = tmp_path / "corpus"
    out_json = (
        corpus / show.name / "Season 01" / "S01E01 - Volume 1.json"
    )
    payload = _eligible_payload()
    for chapter in payload["chapters"]:
        chapter["transcript_cleaned"] = "pared"
    _write_corpus_json(out_json, payload)

    code, out, calls = _run(
        library, corpus, apply=True, chapter_count=lambda _video: 2
    )

    assert code == 0
    assert calls["prepare"] == []
    assert _prepare_line(out, "SKIP")
    assert not _prepare_line(out, "RUN")


def test_transcript_raw_alone_does_not_skip_prepare(tmp_path: Path):
    library = tmp_path / "lib"
    library.mkdir()
    show = _organized_show(
        library, "Arm Bars by John Danaher", ["S01E01 - Volume 1.mp4"]
    )
    corpus = tmp_path / "corpus"
    out_json = (
        corpus / show.name / "Season 01" / "S01E01 - Volume 1.json"
    )
    payload = _eligible_payload()
    for chapter in payload["chapters"]:
        chapter["transcript_raw"] = "<10.00> already nested"
    _write_corpus_json(out_json, payload)

    code, out, calls = _run(
        library, corpus, apply=True, chapter_count=lambda _video: 2
    )

    assert code == 0
    assert calls["prepare"]
    assert _prepare_line(out, "RUN")


def test_force_stage_prepare_reruns_when_transcript_cleaned_present(tmp_path: Path):
    library = tmp_path / "lib"
    library.mkdir()
    show = _organized_show(
        library, "Arm Bars by John Danaher", ["S01E01 - Volume 1.mp4"]
    )
    corpus = tmp_path / "corpus"
    out_json = (
        corpus / show.name / "Season 01" / "S01E01 - Volume 1.json"
    )
    payload = _eligible_payload()
    for chapter in payload["chapters"]:
        chapter["transcript_cleaned"] = "pared"
    _write_corpus_json(out_json, payload)

    code, out, calls = _run(
        library,
        corpus,
        apply=True,
        force_stage="prepare",
        chapter_count=lambda _video: 2,
    )

    assert code == 0
    assert calls["match"] == []
    assert calls["organize"] == []
    assert [item["json_path"] for item in calls["prepare"]] == [out_json]
    assert _prepare_line(out, "RUN")


def test_force_includes_prepare(tmp_path: Path):
    library = tmp_path / "lib"
    library.mkdir()
    show = _organized_show(
        library, "Arm Bars by John Danaher", ["S01E01 - Volume 1.mp4"]
    )
    corpus = tmp_path / "corpus"
    out_json = (
        corpus / show.name / "Season 01" / "S01E01 - Volume 1.json"
    )
    payload = _eligible_payload()
    for chapter in payload["chapters"]:
        chapter["transcript_cleaned"] = "pared"
    _write_corpus_json(out_json, payload)

    code, out, calls = _run(
        library, corpus, apply=True, force=True, chapter_count=lambda _video: 2
    )

    assert code == 0
    assert calls["prepare"]
    assert _prepare_line(out, "RUN")


def test_completer_down_nests_raw_prints_fail_then_retry_fills_cleaned(
    tmp_path: Path, monkeypatch
):
    library = tmp_path / "lib"
    library.mkdir()
    show = _organized_show(
        library, "Arm Bars by John Danaher", ["S01E01 - Volume 1.mp4"]
    )
    corpus = tmp_path / "corpus"
    out_json = (
        corpus / show.name / "Season 01" / "S01E01 - Volume 1.json"
    )
    _write_corpus_json(out_json, _eligible_payload())

    def down(_prompt: str) -> str:
        raise OSError("connection refused")

    monkeypatch.setattr("bjj_pipeline.prepare.complete_chat", down)
    code, out, _calls = _run(
        library,
        corpus,
        apply=True,
        chapter_count=lambda _video: 2,
        inject_prepare=False,
        stages=("prepare",),
    )

    assert code == 1
    assert _prepare_line(out, "FAIL")
    data = json.loads(out_json.read_text(encoding="utf-8"))
    guard, passing = data["chapters"]
    assert "<290.00>" in guard["transcript_raw"]
    assert "<290.00>" in passing["transcript_raw"]
    assert "transcript_cleaned" not in guard
    assert "suggested_tags" not in guard

    def up(_prompt: str) -> str:
        return json.dumps({"transcript_cleaned": "pared later", "suggested_tags": []})

    monkeypatch.setattr("bjj_pipeline.prepare.complete_chat", up)
    code, out, _calls = _run(
        library,
        corpus,
        apply=True,
        chapter_count=lambda _video: 2,
        inject_prepare=False,
        stages=("prepare",),
    )

    assert code == 0
    assert _prepare_line(out, "RUN")
    data = json.loads(out_json.read_text(encoding="utf-8"))
    guard, passing = data["chapters"]
    assert guard["transcript_cleaned"] == "pared later"
    assert passing["transcript_cleaned"] == "pared later"
    assert guard["suggested_tags"] == []


def test_prepare_skips_whole_recording_chapter(tmp_path: Path):
    library = tmp_path / "lib"
    library.mkdir()
    show = _organized_show(
        library, "Arm Bars by John Danaher", ["S01E01 - Volume 1.mp4"]
    )
    corpus = tmp_path / "corpus"
    out_json = (
        corpus / show.name / "Season 01" / "S01E01 - Volume 1.json"
    )
    _write_corpus_json(
        out_json,
        {
            "video_file": "S01E01 - Volume 1.mp4",
            "chapters": [{"title": "Volume 1", "start": 0.0, "end": 1000.0}],
            "language": "en",
            "segments": [
                {"start": 10.0, "end": 20.0, "text": "in guard"},
                {"start": 900.0, "end": 910.0, "text": "after"},
            ],
        },
    )

    code, out, calls = _run(
        library, corpus, apply=True, chapter_count=lambda _video: 2
    )

    assert code == 0
    assert calls["prepare"] == []
    assert _prepare_line(out, "SKIP")


def test_prepare_fail_exits_1(tmp_path: Path):
    library = tmp_path / "lib"
    library.mkdir()
    show = _organized_show(
        library, "Arm Bars by John Danaher", ["S01E01 - Volume 1.mp4"]
    )
    corpus = tmp_path / "corpus"
    out_json = (
        corpus / show.name / "Season 01" / "S01E01 - Volume 1.json"
    )
    _write_corpus_json(out_json, _eligible_payload())
    calls, match, organize, detect, transcribe, prepare = _standins()

    def boom(json_path: Path, corpus_root: Path, video_library_root: Path | None = None) -> int:
        calls["prepare"].append(
            {
                "json_path": json_path,
                "corpus_root": corpus_root,
                "video_library_root": video_library_root,
            }
        )
        return 1

    buf = io.StringIO()
    code = run_pipeline.run(
        library,
        corpus,
        apply=True,
        match=match,
        organize=organize,
        detect=detect,
        transcribe=transcribe,
        prepare=boom,
        chapter_count=lambda _video: 2,
        stdout=buf,
        isatty=False,
    )

    assert code == 1
    assert _prepare_line(buf.getvalue(), "FAIL")
