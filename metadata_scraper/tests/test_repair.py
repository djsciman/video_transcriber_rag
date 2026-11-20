from datetime import date
from pathlib import Path

from bjj_organizer.models import Chapter, Product, Volume
from bjj_organizer.pipeline import RuntimeOptions, apply_plan, build_plan
from bjj_organizer.repair import assess, format_report, parse_repair_answer


def _product(title: str, instructor: str, url: str, volumes: list[Volume]) -> Product:
    return Product(
        title=title,
        instructor=instructor,
        plot=f"Plot for {title}",
        premiered=date(2020, 1, 2),
        year=2020,
        tags=["Instructional"],
        unique_ids={"bjjfanatics": "1"},
        images=[],
        volumes=volumes,
        source_url=url,
    )


def _scrape(product: Product):
    def scrape(url: str, user_agent: str | None = None) -> Product:
        return product

    return scrape


def test_parse_repair_answer_accepts_all_and_letters():
    assert parse_repair_answer("all", ["B", "C", "D"]) == {"B", "C", "D"}
    assert parse_repair_answer("A, C", ["A", "C", "D"]) == {"A", "C"}
    assert parse_repair_answer("a,c", ["A", "C"]) == {"A", "C"}
    assert parse_repair_answer("", ["B"]) is None
    assert parse_repair_answer("Z", ["B", "C"]) is None


def test_raw_chapter_files_checklist_is_unchecked_and_offers_fixes(tmp_path: Path):
    show = tmp_path / "Polish Power Backtakes"
    show.mkdir()
    (show / "4533018132578-01-01- Turtle.mp4").write_bytes(b"x")
    (show / "4533018132578-01-02- Clock.mp4").write_bytes(b"x")
    url = "https://example.com/back"
    product = _product(
        "Polish Power Back Takes",
        "Adam Wardzinski",
        url,
        [Volume("Volume 1", (Chapter("Turtle", 0), Chapter("Clock", 1000)))],
    )
    plan = build_plan(show, [url], RuntimeOptions(), scrape_product=_scrape(product))
    report = assess(plan, RuntimeOptions())
    text = format_report(report)
    assert "[ ] tvshow.nfo" in text
    assert "[ ] Season ## folder" in text
    assert "[ ] season.nfo" in text
    assert "[ ] episode NFOs" in text
    assert "C" in report.needed_letters()
    assert "D" in report.needed_letters()
    assert "F" in report.needed_letters()


def test_finished_show_row_is_checked_and_has_no_fix(tmp_path: Path):
    show = tmp_path / "Battle Tested Half Guard by Bernardo Faria"
    show.mkdir()
    (show / "BattleTestedHalfGuardDVD1.mp4").write_bytes(b"x")
    url = "https://example.com/half"
    product = _product(
        "Battle Tested Half Guard by Bernardo Faria",
        "Bernardo Faria",
        url,
        [Volume("Volume 1", (Chapter("Intro", 0),))],
    )
    options = RuntimeOptions(skip_chapters=True)
    plan = build_plan(show, [url], options, scrape_product=_scrape(product))
    apply_plan(plan, options)
    report = assess(plan, options)
    text = format_report(report)
    assert "[x] tvshow.nfo" in text
    assert "[x] season.nfo" in text
    assert "[x] episode NFOs (1 of 1)" in text
    assert "B" not in report.needed_letters()
    assert "F" not in report.needed_letters()


def test_half_finished_combine_stays_unchecked(tmp_path: Path):
    show = tmp_path / "Open Guard"
    show.mkdir()
    (show / "4533018132578-01-01- Introduction.mp4").write_bytes(b"x")
    (show / "4533018132578-01-02- Armbar.mp4").write_bytes(b"x")
    url = "https://example.com/open"
    product = _product(
        "Open Guard",
        "John Danaher",
        url,
        [Volume("Volume 1", (Chapter("Introduction", 0), Chapter("Armbar", 1000)))],
    )
    options = RuntimeOptions()
    plan = build_plan(show, [url], options, scrape_product=_scrape(product))
    dest_dir = show / plan.seasons[0].dest_name
    dest_dir.mkdir()
    (dest_dir / plan.seasons[0].episodes[0].dest_name).write_bytes(b"x")
    report = assess(plan, options)
    text = format_report(report)
    assert "[ ] chapter clips combined into volumes" in text
    assert "clips still separate" in text
    assert "D" in report.needed_letters()


def test_match_error_records_the_season_without_episodes(tmp_path: Path):
    show = tmp_path / "Bad Season"
    show.mkdir()
    (show / "clip.mp4").write_bytes(b"x")
    bad_url = "https://example.com/bad"
    product = _product(
        "Bad Season",
        "Ada",
        bad_url,
        [Volume(f"Volume {i}", (Chapter("A", 0), Chapter("B", 1000))) for i in range(1, 5)],
    )
    plan = build_plan(show, [bad_url], RuntimeOptions(), scrape_product=_scrape(product))
    assert len(plan.seasons) == 1
    assert plan.seasons[0].match_error
    assert not plan.seasons[0].episodes


def test_clips_already_inside_an_episode_are_leftovers(tmp_path: Path, monkeypatch):
    show = tmp_path / "Bundle"
    episode = show / "Season 02" / "Show - S02E03 - Volume 3.mp4"
    episode.parent.mkdir(parents=True)
    episode.write_bytes(b"x")
    clips = show / "No Gi"
    clips.mkdir()
    (clips / "6644438007906-20-01- Dive Under.mp4").write_bytes(b"x")
    (clips / "6644438007906-20-02- Tip Over.mp4").write_bytes(b"x")
    url = "https://example.com/nogi"
    product = _product(
        "No Gi",
        "Ada",
        url,
        [Volume(f"Volume {i}", tuple(Chapter(f"C{i}-{n}", 0) for n in range(8))) for i in range(1, 4)],
    )

    def fake_titles(path, ffprobe):
        return ["Dive Under", "Tip Over"]

    monkeypatch.setattr("bjj_organizer.pipeline.probe_chapter_titles", fake_titles)
    plan = build_plan(show, [url], RuntimeOptions(), scrape_product=_scrape(product))
    season = plan.seasons[0]
    assert season.keep_dest
    assert season.dest_name == "Season 02"
    assert season.episodes[0].dest_name == episode.name
    assert len(season.extras) == 2
    assert not season.match_error


def test_repair_step_c_moves_videos_without_episode_nfo(tmp_path: Path):
    show = tmp_path / "Half Butterfly"
    show.mkdir()
    (show / "HalfButterflyMasterybyBrianGlick1.mp4").write_bytes(b"x")
    (show / "HalfButterflyMasterybyBrianGlick2.mp4").write_bytes(b"x")
    url = "https://example.com/hb"
    product = _product(
        "Half Butterfly",
        "Brian Glick",
        url,
        [
            Volume("Volume 1", (Chapter("Intro", 0),)),
            Volume("Volume 2", (Chapter("Sweep", 0),)),
        ],
    )
    options = RuntimeOptions(repair=True, repair_steps={"C"})
    plan = build_plan(show, [url], options, scrape_product=_scrape(product))
    apply_plan(plan, options)
    season = show / "Season 01"
    assert (season / "season.nfo").is_file()
    assert (season / "HalfButterflyMasterybyBrianGlick1.mp4").is_file()
    assert (season / "HalfButterflyMasterybyBrianGlick2.mp4").is_file()
    assert not (show / "tvshow.nfo").is_file()
    assert list(season.glob("*.nfo")) == [season / "season.nfo"]
    assert not list(season.glob("*S01E*"))
