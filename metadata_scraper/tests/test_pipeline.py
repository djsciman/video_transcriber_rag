from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

import organize_instructional
from bjj_organizer.errors import UsageError
from bjj_organizer.models import Chapter, Product, Volume
from bjj_organizer.fanatics_search import ProductHit
from bjj_organizer.match import match_season
from bjj_organizer.pipeline import (
    RuntimeOptions,
    _episodes_from_match,
    _wants_chapter_remux,
    apply_plan,
    build_plan,
    lookup_season_url,
    rename_directory,
    resolve_season_url,
)


def _product(title: str, instructor: str, n_vols: int, day: int, url: str, chapters_each: int = 2) -> Product:
    volumes = []
    for i in range(1, n_vols + 1):
        chapters = tuple(
            Chapter(f"Vol{i} Chapter {c}", (c - 1) * 1000) for c in range(1, chapters_each + 1)
        )
        volumes.append(Volume(name=f"Volume {i}", chapters=chapters))
    return Product(
        title=title,
        instructor=instructor,
        plot=f"Plot for {title}",
        premiered=date(2020, 1, day),
        year=2020,
        tags=["Instructional"],
        unique_ids={"bjjfanatics": str(day)},
        images=[],
        volumes=volumes,
        source_url=url,
    )


def test_untimed_volumes_list_chapters_and_do_not_remux():
    files = [Path("OpenGuardSeatedVolume1.mp4"), Path("OpenGuardSeatedVolume2.mp4")]
    volumes = [
        Volume("Volume 1", (Chapter("Intro", 0), Chapter("Goal setting", 0))),
        Volume("Volume 2", (Chapter("Ankle pick", 0), Chapter("De ashi", 0))),
    ]
    matched = match_season(files, volumes)
    episodes = _episodes_from_match(matched.items, matched.mode, RuntimeOptions(), Path("."))
    assert [episode.title for episode in episodes] == ["Volume 1", "Volume 2"]
    assert [chapter.title for chapter in episodes[0].chapters] == ["Intro", "Goal setting"]
    assert all(episode.split_start_ms is None for episode in episodes)
    assert all(not _wants_chapter_remux(episode, RuntimeOptions()) for episode in episodes)
    combined = _episodes_from_match(
        matched.items,
        matched.mode,
        RuntimeOptions(),
        Path("."),
    )
    assert len(combined) == 2
    assert all(episode.split_start_ms is None for episode in combined)
    assert [chapter.title for chapter in combined[0].chapters] == ["Intro", "Goal setting"]


def test_leaf_plan_and_apply_without_split(tmp_path: Path):
    show = tmp_path / "Battle Tested Half Guard by Bernardo Faria"
    show.mkdir()
    for i in range(1, 5):
        (show / f"BattleTestedHalfGuardDVD{i}.mp4").write_bytes(b"x")

    products = {
        "https://bjjfanatics.com/products/half": _product(
            "Battle Tested Half Guard by Bernardo Faria",
            "Bernardo Faria",
            4,
            5,
            "https://bjjfanatics.com/products/half",
        )
    }

    def scrape(url: str, user_agent: str | None = None) -> Product:
        return products[url]

    options = RuntimeOptions(skip_chapters=True)
    plan = build_plan(show, ["https://bjjfanatics.com/products/half"], options, scrape_product=scrape)
    assert plan.title == "Battle Tested Half Guard by Bernardo Faria"
    assert len(plan.seasons) == 1
    assert plan.seasons[0].dest_name == "Season 01"
    assert len(plan.seasons[0].episodes) == 4
    assert plan.seasons[0].episodes[0].dest_name.startswith(
        "Battle Tested Half Guard by Bernardo Faria - S01E01"
    )
    assert plan.seasons[0].episodes[0].title == "Volume 1"
    apply_plan(plan, options)
    dest = show
    season = dest / "Season 01"
    videos = sorted(p.name for p in season.glob("*.mp4"))
    assert videos[0].startswith("Battle Tested Half Guard by Bernardo Faria - S01E01")
    assert videos[-1].startswith("Battle Tested Half Guard by Bernardo Faria - S01E04")
    assert (dest / "tvshow.nfo").is_file()
    assert (season / "season.nfo").is_file()
    assert list(season.glob("*.nfo"))


def test_volume_plan_keeps_scrape_chapter_titles(tmp_path: Path):
    show = tmp_path / "Magic Guard Passing by Travis Stevens"
    show.mkdir()
    (show / "MagicGuardPassingbyTravisStevensVol1.mp4").write_bytes(b"x")
    (show / "MagicGuardPassingbyTravisStevensVol2.mp4").write_bytes(b"x")
    product = _product(
        "Magic Guard Passing by Travis Stevens",
        "Travis Stevens",
        2,
        1,
        "https://example.com/magic",
        chapters_each=3,
    )

    def scrape(url: str, user_agent: str | None = None) -> Product:
        return product

    plan = build_plan(
        show,
        ["https://example.com/magic"],
        RuntimeOptions(),
        scrape_product=scrape,
    )
    assert plan.seasons[0].mode == "volume"
    assert len(plan.seasons[0].episodes) == 2
    first = plan.seasons[0].episodes[0]
    assert first.split_start_ms is None
    assert [ch.title for ch in first.chapters] == ["Vol1 Chapter 1", "Vol1 Chapter 2", "Vol1 Chapter 3"]
    assert first.dest_name.endswith("S01E01 - Volume 1.mp4")
    assert len(first.concat_sources) == 1


def test_existing_container_chapters_skip_fanatics_remux(tmp_path: Path, monkeypatch):
    show = tmp_path / "Magic Guard Passing by Travis Stevens"
    show.mkdir()
    source = show / "MagicGuardPassingbyTravisStevensVol1.mp4"
    source.write_bytes(b"x")
    product = _product(
        "Magic Guard Passing by Travis Stevens",
        "Travis Stevens",
        1,
        1,
        "https://example.com/magic",
        chapters_each=3,
    )

    def scrape(url: str, user_agent: str | None = None) -> Product:
        return product

    plan = build_plan(
        show,
        ["https://example.com/magic"],
        RuntimeOptions(),
        scrape_product=scrape,
    )
    remux_calls: list[str] = []
    probed: list[str] = []

    monkeypatch.setattr("bjj_organizer.pipeline._tool", lambda name, explicit=None: name)

    def fake_count(path, ffprobe, command=None):
        probed.append(Path(path).name)
        return 4

    def fake_remux(*args, **kwargs):
        remux_calls.append("remux")
        raise AssertionError("must not remux Fanatics markers over container chapters")

    monkeypatch.setattr("bjj_organizer.pipeline.probe_chapter_count", fake_count)
    monkeypatch.setattr("bjj_organizer.pipeline.remux_with_chapters", fake_remux)

    apply_plan(plan, RuntimeOptions())

    assert remux_calls == []
    assert probed == [source.name]
    season = show / "Season 01"
    dests = list(season.glob("*.mp4"))
    assert len(dests) == 1
    assert dests[0].read_bytes() == b"x"


def test_segmented_plan_groups_chapter_files_into_volumes(tmp_path: Path):
    show = tmp_path / "Mikey Musumeci The Collar and Sleeve System Pt 1"
    show.mkdir()
    names = [
        "4533018132578-01-01- Introduction.mp4",
        "4533018132578-01-02- Collar And Sleeve.mp4",
        "4533018132578-02-01- World One Outside Control.mp4",
    ]
    for name in names:
        (show / name).write_bytes(b"x")
    product = Product(
        title="The Collar and Sleeve System Part 1: Outside Control On The Knees by Mikey Musumeci",
        instructor="Mikey Musumeci",
        plot="Plot",
        premiered=date(2025, 1, 1),
        year=2025,
        tags=["Instructional"],
        unique_ids={"bjjfanatics": "1"},
        images=[],
        volumes=[
            Volume("Volume 1", (Chapter("Introduction", 0), Chapter("Collar And Sleeve", 12_500))),
            Volume("Volume 2", (Chapter("World One Outside Control", 0),)),
        ],
        source_url="https://bjjfanatics.com/products/collar",
    )

    def scrape(url: str, user_agent: str | None = None) -> Product:
        return product

    plan = build_plan(
        show,
        ["https://bjjfanatics.com/products/collar"],
        RuntimeOptions(),
        scrape_product=scrape,
    )
    assert plan.seasons[0].mode == "segmented"
    assert len(plan.seasons[0].episodes) == 2
    assert [e.title for e in plan.seasons[0].episodes] == ["Volume 1", "Volume 2"]
    assert [ch.title for ch in plan.seasons[0].episodes[0].chapters] == [
        "Introduction",
        "Collar And Sleeve",
    ]
    assert all(e.split_start_ms is None for e in plan.seasons[0].episodes)


def test_nested_collection_is_leftover_bundle(tmp_path: Path):
    root = tmp_path / "Ryan Smith Collection"
    (root / "Get Off My Legs Gringo by Craig Jones").mkdir(parents=True)
    (root / "Mastering No Gi Takedowns by Travis Stevens").mkdir()
    for i in range(1, 3):
        (root / "Get Off My Legs Gringo by Craig Jones" / f"Vol{i}.mp4").write_bytes(b"x")
        (root / "Mastering No Gi Takedowns by Travis Stevens" / f"Vol{i}.mp4").write_bytes(b"x")

    def scrape(url: str, user_agent: str | None = None) -> Product:
        raise AssertionError("leftover bundles must not scrape")

    with pytest.raises(UsageError, match="leftover bundle"):
        build_plan(
            root,
            ["https://example.com/craig"],
            RuntimeOptions(skip_chapters=True),
            scrape_product=scrape,
        )


def test_rename_directory_retries_access_denied(tmp_path: Path):
    source = tmp_path / "Leg Locks"
    dest = tmp_path / "Leg Locks by John Danaher"
    source.mkdir()
    original = Path.rename
    calls = {"n": 0}

    def side_effect(self, target):
        calls["n"] += 1
        if calls["n"] < 3:
            err = PermissionError(13, "Access is denied")
            err.winerror = 5
            raise err
        return original(self, target)

    with patch.object(Path, "rename", side_effect), patch("bjj_organizer.pipeline.time.sleep"):
        assert rename_directory(source, dest, attempts=5)
    assert dest.is_dir()
    assert not source.exists()


def test_rename_directory_warns_instead_of_raising(tmp_path: Path, capsys):
    source = tmp_path / "Leg Locks"
    dest = tmp_path / "Leg Locks by John Danaher"
    source.mkdir()

    def always_fail(self, target):
        err = PermissionError(13, "Access is denied")
        err.winerror = 5
        raise err

    with patch.object(Path, "rename", always_fail), patch("bjj_organizer.pipeline.time.sleep"):
        assert rename_directory(source, dest, attempts=2) is False
    err = capsys.readouterr().err
    assert "could not rename folder" in err
    assert source.is_dir()


def test_leaf_inside_series_warns(tmp_path: Path):
    series = tmp_path / "Enter the System by John Danaher"
    (series / "Leg Locks").mkdir(parents=True)
    (series / "Arm Bar").mkdir()
    (series / "Leg Locks" / "Vol1.mp4").write_bytes(b"x")
    (series / "Arm Bar" / "Vol1.mp4").write_bytes(b"x")
    product = _product("Leg Locks", "John Danaher", 1, 1, "https://example.com/legs", chapters_each=1)

    def scrape(url: str, user_agent: str | None = None) -> Product:
        return product

    plan = build_plan(
        series / "Leg Locks",
        ["https://example.com/legs"],
        RuntimeOptions(skip_chapters=True),
        scrape_product=scrape,
    )
    assert any("season of Enter the System" in w for w in plan.warnings)


def test_segmented_combine_groups_by_volume(tmp_path: Path):
    show = tmp_path / "Mikey Musumeci The Collar and Sleeve System Pt 1"
    show.mkdir()
    names = [
        "4533018132578-01-01- Introduction.mp4",
        "4533018132578-01-02- Collar And Sleeve.mp4",
        "4533018132578-02-01- World One Outside Control.mp4",
    ]
    for name in names:
        (show / name).write_bytes(b"x")
    product = Product(
        title="The Collar and Sleeve System Part 1 by Mikey Musumeci",
        instructor="Mikey Musumeci",
        plot="Plot",
        premiered=date(2025, 1, 1),
        year=2025,
        tags=["Instructional"],
        unique_ids={"bjjfanatics": "1"},
        images=[],
        volumes=[
            Volume("Volume 1", (Chapter("Introduction", 0), Chapter("Collar And Sleeve", 12_500))),
            Volume("Volume 2", (Chapter("World One Outside Control", 0),)),
        ],
        source_url="https://bjjfanatics.com/products/collar",
    )

    def scrape(url: str, user_agent: str | None = None) -> Product:
        return product

    plan = build_plan(
        show,
        ["https://bjjfanatics.com/products/collar"],
        RuntimeOptions(),
        scrape_product=scrape,
    )
    assert plan.combine_volumes
    assert len(plan.seasons[0].episodes) == 2
    first, second = plan.seasons[0].episodes
    assert first.title == "Volume 1"
    assert [p.name for p in first.concat_sources] == [
        "4533018132578-01-01- Introduction.mp4",
        "4533018132578-01-02- Collar And Sleeve.mp4",
    ]
    assert [ch.title for ch in first.chapters] == ["Introduction", "Collar And Sleeve"]
    assert first.dest_name.endswith("S01E01 - Volume 1.mp4")
    assert second.dest_name.endswith("S01E02 - Volume 2.mp4")
    assert len(second.concat_sources) == 1


def test_volume_combine_keeps_one_episode_per_volume(tmp_path: Path):
    show = tmp_path / "Magic Guard Passing by Travis Stevens"
    show.mkdir()
    (show / "MagicGuardPassingbyTravisStevensVol1.mp4").write_bytes(b"x")
    (show / "MagicGuardPassingbyTravisStevensVol2.mp4").write_bytes(b"x")
    product = _product(
        "Magic Guard Passing by Travis Stevens",
        "Travis Stevens",
        2,
        1,
        "https://example.com/magic",
        chapters_each=3,
    )

    def scrape(url: str, user_agent: str | None = None) -> Product:
        return product

    plan = build_plan(
        show,
        ["https://example.com/magic"],
        RuntimeOptions(),
        scrape_product=scrape,
    )
    assert len(plan.seasons[0].episodes) == 2
    assert plan.seasons[0].episodes[0].split_start_ms is None
    assert len(plan.seasons[0].episodes[0].chapters) == 3
    assert plan.seasons[0].episodes[0].dest_name.endswith("S01E01 - Volume 1.mp4")
    assert len(plan.seasons[0].episodes[0].concat_sources) == 1


def test_resolve_url_one_season_accepts_bare_url():
    url = resolve_season_url(
        "Season 1",
        "Season 01",
        keyed={},
        bare_urls=["https://example.com/half"],
        nested=True,
        season_count=1,
        show_folder="Half Guard Anthology by Lachlan Giles",
    )
    assert url == "https://example.com/half"


def test_organized_one_season_show_name_url(tmp_path: Path):
    show = tmp_path / "Half Guard Anthology by Lachlan Giles"
    season = show / "Season 01"
    season.mkdir(parents=True)
    (season / "season.nfo").write_text("<season><title>Season 1</title></season>", encoding="utf-8")
    (season / "01.01 - Overview.mp4").write_bytes(b"x")
    (season / "01.02 - Entries.mp4").write_bytes(b"x")
    (season / "02.01 - Recovery.mp4").write_bytes(b"x")
    product = Product(
        title="The Half Guard Anthology by Lachlan Giles",
        instructor="Lachlan Giles",
        plot="Plot",
        premiered=date(2019, 1, 1),
        year=2019,
        tags=["Instructional"],
        unique_ids={"bjjfanatics": "1"},
        images=[],
        volumes=[
            Volume("Volume 1", (Chapter("Overview", 0), Chapter("Entries", 1000))),
            Volume("Volume 2", (Chapter("Recovery", 0),)),
        ],
        source_url="https://bjjfanatics.com/products/half",
    )

    def scrape(url: str, user_agent: str | None = None) -> Product:
        return product

    plan = build_plan(
        show,
        ["https://bjjfanatics.com/products/half"],
        RuntimeOptions(),
        scrape_product=scrape,
    )
    assert plan.seasons[0].source_name == "The Half Guard Anthology by Lachlan Giles"
    assert len(plan.seasons[0].episodes) == 2
    assert len(plan.seasons[0].episodes[0].concat_sources) == 2


def test_nested_bundle_is_left_out_of_organize(tmp_path: Path):
    root = tmp_path / "Go Further Faster By John Danaher"
    (root / "Closed Guard").mkdir(parents=True)
    (root / "Open Guard").mkdir()
    (root / "Closed Guard" / "1 Overview.mp4").write_bytes(b"x")
    (root / "Open Guard" / "1 Finding.mp4").write_bytes(b"x")

    def scrape(url: str, user_agent: str | None = None) -> Product:
        raise AssertionError("leftover bundles must not scrape")

    with pytest.raises(UsageError, match="leftover bundle"):
        build_plan(
            root,
            ["https://bjjfanatics.com/products/closed-guard"],
            RuntimeOptions(skip_chapters=True),
            scrape_product=scrape,
        )


def test_csv_product_url_is_auto_accepted_without_tty(tmp_path: Path, monkeypatch):
    csv_url = "https://bjjfanatics.com/products/the-half-guard-anthology"
    monkeypatch.setattr("bjj_organizer.pipeline.lookup_candidates", lambda *args, **kwargs: [])
    monkeypatch.setattr("bjj_organizer.pipeline.csv_hint_url", lambda folder: csv_url)

    class _Stdin:
        def isatty(self) -> bool:
            return False

        def readline(self) -> str:
            raise AssertionError("CSV URL must not prompt")

    url = lookup_season_url(
        tmp_path,
        "Half Guard Anthology",
        1,
        RuntimeOptions(stdin=_Stdin(), stderr=__import__("io").StringIO()),
    )
    assert url == csv_url


def test_season_lookup_drops_bundle_url(tmp_path: Path, monkeypatch):
    hits = [
        ProductHit("Go Further Faster Bundle by John Danaher", "https://example.com/bundle", 0.95),
        ProductHit("Closed Guard", "https://example.com/closed", 0.80),
    ]
    monkeypatch.setattr("bjj_organizer.pipeline.lookup_candidates", lambda *args, **kwargs: list(hits))
    monkeypatch.setattr("bjj_organizer.pipeline.csv_hint_url", lambda folder: "https://example.com/bundle")

    class _Stdin:
        def isatty(self) -> bool:
            return True

        def readline(self) -> str:
            return "y\n"

    url = lookup_season_url(
        tmp_path,
        "Closed Guard",
        2,
        RuntimeOptions(stdin=_Stdin(), stderr=__import__("io").StringIO()),
        exclude_urls={"https://example.com/bundle"},
    )
    assert url == "https://example.com/closed"


def test_organized_one_season_bare_url(tmp_path: Path):
    show = tmp_path / "Half Guard Anthology by Lachlan Giles"
    season = show / "Season 01"
    season.mkdir(parents=True)
    (season / "01.01 - Overview.mp4").write_bytes(b"x")
    product = _product("The Half Guard Anthology", "Lachlan Giles", 1, 1, "https://example.com/half", chapters_each=1)

    def scrape(url: str, user_agent: str | None = None) -> Product:
        assert url == "https://example.com/half"
        return product

    plan = build_plan(
        show,
        ["https://example.com/half"],
        RuntimeOptions(skip_chapters=True),
        scrape_product=scrape,
    )
    assert len(plan.seasons) == 1


def test_organize_parser_has_no_combine_or_split_flags():
    parser = organize_instructional.build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--folder", "Show", "--no-combine-volumes"])
    with pytest.raises(SystemExit):
        parser.parse_args(["--folder", "Show", "--combine-volumes"])
    args = parser.parse_args(["--folder", "Show", "--url", "https://example.com/product"])
    assert not hasattr(args, "combine_volumes")
    assert args.urls == ["https://example.com/product"]


def test_default_plan_concatenates_chapter_files_into_volumes(tmp_path: Path):
    show = tmp_path / "Mikey Musumeci The Collar and Sleeve System Pt 1"
    show.mkdir()
    names = [
        "4533018132578-01-01- Introduction.mp4",
        "4533018132578-01-02- Collar And Sleeve.mp4",
        "4533018132578-02-01- World One Outside Control.mp4",
    ]
    for name in names:
        (show / name).write_bytes(b"x")
    product = Product(
        title="The Collar and Sleeve System Part 1 by Mikey Musumeci",
        instructor="Mikey Musumeci",
        plot="Plot",
        premiered=date(2025, 1, 1),
        year=2025,
        tags=["Instructional"],
        unique_ids={"bjjfanatics": "1"},
        images=[],
        volumes=[
            Volume("Volume 1", (Chapter("Introduction", 0), Chapter("Collar And Sleeve", 12_500))),
            Volume("Volume 2", (Chapter("World One Outside Control", 0),)),
        ],
        source_url="https://bjjfanatics.com/products/collar",
    )

    def scrape(url: str, user_agent: str | None = None) -> Product:
        return product

    plan = build_plan(
        show,
        ["https://bjjfanatics.com/products/collar"],
        RuntimeOptions(),
        scrape_product=scrape,
    )
    assert len(plan.seasons[0].episodes) == 2
    first, second = plan.seasons[0].episodes
    assert first.title == "Volume 1"
    assert [p.name for p in first.concat_sources] == [
        "4533018132578-01-01- Introduction.mp4",
        "4533018132578-01-02- Collar And Sleeve.mp4",
    ]
    assert [ch.title for ch in first.chapters] == ["Introduction", "Collar And Sleeve"]
    assert first.split_start_ms is None
    assert second.split_start_ms is None
    assert first.dest_name.endswith("S01E01 - Volume 1.mp4")
    assert second.dest_name.endswith("S01E02 - Volume 2.mp4")


def test_leftover_bundle_folder_is_not_organized(tmp_path: Path):
    root = tmp_path / "Go Further Faster By John Danaher"
    (root / "Closed Guard").mkdir(parents=True)
    (root / "Open Guard").mkdir()
    (root / "Closed Guard" / "1 Overview.mp4").write_bytes(b"x")
    (root / "Open Guard" / "1 Finding.mp4").write_bytes(b"x")

    def scrape(url: str, user_agent: str | None = None) -> Product:
        raise AssertionError("leftover bundles must not scrape")

    with pytest.raises(UsageError, match="leftover bundle"):
        build_plan(
            root,
            ["https://bjjfanatics.com/products/closed-guard"],
            RuntimeOptions(skip_chapters=True),
            scrape_product=scrape,
        )


def test_one_product_url_per_instructional_folder(tmp_path: Path):
    show = tmp_path / "Closed Guard"
    show.mkdir()
    (show / "Vol1.mp4").write_bytes(b"x")

    def scrape(url: str, user_agent: str | None = None) -> Product:
        raise AssertionError("too many URLs must fail before scrape")

    with pytest.raises(UsageError, match="at most one"):
        build_plan(
            show,
            [
                "https://example.com/closed",
                "https://example.com/other",
            ],
            RuntimeOptions(skip_chapters=True),
            scrape_product=scrape,
        )
    with pytest.raises(UsageError, match="SeasonFolder"):
        build_plan(
            show,
            ["Closed Guard=https://example.com/closed"],
            RuntimeOptions(skip_chapters=True),
            scrape_product=scrape,
        )
