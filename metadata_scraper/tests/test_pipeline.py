from datetime import date
from pathlib import Path
from unittest.mock import patch

from bjj_organizer.models import Chapter, Product, Volume
from bjj_organizer.fanatics_search import ProductHit
from bjj_organizer.nfo import tvshow_xml
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
    take_show_url,
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
    split_episodes = _episodes_from_match(
        matched.items,
        matched.mode,
        RuntimeOptions(combine_volumes=False),
        Path("."),
    )
    assert len(split_episodes) == 2
    assert all(episode.split_start_ms is None for episode in split_episodes)
    assert [chapter.title for chapter in split_episodes[0].chapters] == ["Intro", "Goal setting"]


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


def test_volume_plan_expands_to_chapters(tmp_path: Path):
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
        RuntimeOptions(combine_volumes=False),
        scrape_product=scrape,
    )
    assert plan.seasons[0].mode == "volume"
    assert len(plan.seasons[0].episodes) == 6
    names = [e.dest_name for e in plan.seasons[0].episodes]
    assert names[0] == "01.01 - Vol1 Chapter 1.mp4"
    assert names[2] == "01.03 - Vol1 Chapter 3.mp4"
    assert names[3] == "02.01 - Vol2 Chapter 1.mp4"
    assert plan.seasons[0].episodes[0].split_start_ms == 0
    assert plan.seasons[0].episodes[1].split_start_ms == 1000
    assert plan.seasons[0].episodes[2].split_end_ms is None
    assert plan.seasons[0].episodes[0].source == plan.seasons[0].episodes[1].source


def test_segmented_mikey_plan_and_apply(tmp_path: Path):
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

    options = RuntimeOptions(combine_volumes=False)
    plan = build_plan(show, ["https://bjjfanatics.com/products/collar"], options, scrape_product=scrape)
    assert plan.seasons[0].mode == "segmented"
    assert len(plan.seasons[0].episodes) == 3
    assert [e.dest_name for e in plan.seasons[0].episodes] == [
        "01.01 - Introduction.mp4",
        "01.02 - Collar And Sleeve.mp4",
        "02.01 - World One Outside Control.mp4",
    ]
    assert [e.title for e in plan.seasons[0].episodes] == [
        "1.1 Introduction",
        "1.2 Collar And Sleeve",
        "2.1 World One Outside Control",
    ]
    assert all(e.split_start_ms is None for e in plan.seasons[0].episodes)
    apply_plan(plan, options)
    dest_show = tmp_path / plan.dest_name
    season = dest_show / "Season 01"
    videos = sorted(p.name for p in season.glob("*.mp4"))
    assert videos == [
        "01.01 - Introduction.mp4",
        "01.02 - Collar And Sleeve.mp4",
        "02.01 - World One Outside Control.mp4",
    ]
    nfo = (season / "01.01 - Introduction.nfo").read_text(encoding="utf-8")
    assert "<title>1.1 Introduction</title>" in nfo
    assert "<episode>1</episode>" in nfo
    assert "<plot>Volume 1</plot>" in nfo


def test_nested_publish_date_order_and_various(tmp_path: Path):
    root = tmp_path / "Ryan Smith Collection"
    (root / "Get Off My Legs Gringo by Craig Jones").mkdir(parents=True)
    (root / "Mastering No Gi Takedowns by Travis Stevens").mkdir()
    for i in range(1, 3):
        (root / "Get Off My Legs Gringo by Craig Jones" / f"Vol{i}.mp4").write_bytes(b"x")
        (root / "Mastering No Gi Takedowns by Travis Stevens" / f"Vol{i}.mp4").write_bytes(b"x")

    products = {
        "https://example.com/craig": _product("Get Off My Legs Gringo", "Craig Jones", 2, 10, "https://example.com/craig"),
        "https://example.com/travis": _product(
            "Mastering No Gi Takedowns", "Travis Stevens", 2, 2, "https://example.com/travis"
        ),
    }

    def scrape(url: str, user_agent: str | None = None) -> Product:
        return products[url]

    options = RuntimeOptions(skip_chapters=True)
    plan = build_plan(
        root,
        [
            "Get Off My Legs Gringo by Craig Jones=https://example.com/craig",
            "Mastering No Gi Takedowns by Travis Stevens=https://example.com/travis",
        ],
        options,
        scrape_product=scrape,
    )
    assert plan.title == "Ryan Smith Collection by Various"
    assert any("show/bundle URL" in warning for warning in plan.warnings)
    assert plan.show_url == ""
    assert [s.source_name for s in plan.seasons] == [
        "Mastering No Gi Takedowns by Travis Stevens",
        "Get Off My Legs Gringo by Craig Jones",
    ]
    assert [s.number for s in plan.seasons] == [1, 2]
    apply_plan(plan, options)
    renamed = tmp_path / "Ryan Smith Collection by Various"
    assert renamed.is_dir()
    assert (renamed / "Season 01").is_dir()
    assert (renamed / "Season 02").is_dir()
    assert not (renamed / "Get Off My Legs Gringo by Craig Jones").exists()
    videos = sorted(p.name for p in (renamed / "Season 01").glob("*.mp4"))
    assert "S01E01" in videos[0]


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
        RuntimeOptions(combine_volumes=True),
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
        RuntimeOptions(combine_volumes=True),
        scrape_product=scrape,
    )
    assert len(plan.seasons[0].episodes) == 2
    assert plan.seasons[0].episodes[0].split_start_ms is None
    assert len(plan.seasons[0].episodes[0].chapters) == 3
    assert plan.seasons[0].episodes[0].dest_name.endswith("S01E01 - Volume 1.mp4")
    assert len(plan.seasons[0].episodes[0].concat_sources) == 1


def test_resolve_url_one_season_accepts_show_name_key():
    url = resolve_season_url(
        "Season 1",
        "Season 01",
        keyed={"Half Guard Anthology by Lachlan Giles": "https://example.com/half"},
        bare_urls=[],
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
        ["Half Guard Anthology by Lachlan Giles=https://bjjfanatics.com/products/half"],
        RuntimeOptions(combine_volumes=True),
        scrape_product=scrape,
    )
    assert plan.seasons[0].source_name == "The Half Guard Anthology by Lachlan Giles"
    assert len(plan.seasons[0].episodes) == 2
    assert len(plan.seasons[0].episodes[0].concat_sources) == 2


def test_take_show_url_keeps_season_keys():
    show_url, seasons = take_show_url(
        "Go Further Faster By John Danaher",
        {
            "Go Further Faster By John Danaher": "https://example.com/bundle",
            "Closed Guard": "https://example.com/closed",
        },
        [],
    )
    assert show_url == "https://example.com/bundle"
    assert seasons == {"Closed Guard": "https://example.com/closed"}


def test_nested_bundle_supplies_show_metadata(tmp_path: Path):
    root = tmp_path / "Go Further Faster By John Danaher"
    (root / "Closed Guard").mkdir(parents=True)
    (root / "Open Guard").mkdir()
    (root / "Closed Guard" / "1 Overview.mp4").write_bytes(b"x")
    (root / "Open Guard" / "1 Finding.mp4").write_bytes(b"x")
    bundle_url = "https://bjjfanatics.com/products/go-further-faster-bundle-by-john-danher"
    closed_url = "https://bjjfanatics.com/products/closed-guard"
    open_url = "https://bjjfanatics.com/products/open-guard"
    bundle = _product(
        "Go Further Faster Bundle by John Danaher",
        "John Danaher",
        1,
        3,
        bundle_url,
        chapters_each=1,
    )
    bundle.plot = "Bundle plot about the whole series"
    bundle.volumes = [Volume("Volume 01: Pin Escapes", (Chapter("Should Not Match", 0),))]
    bundle.unique_ids = {
        "bjjfanatics": "999",
        "bjjfanatics-handle": "go-further-faster-bundle-by-john-danher",
    }
    closed = _product("Closed Guard", "John Danaher", 1, 1, closed_url, chapters_each=1)
    opened = _product("Open Guard", "John Danaher", 1, 2, open_url, chapters_each=1)
    products = {bundle_url: bundle, closed_url: closed, open_url: opened}

    def scrape(url: str, user_agent: str | None = None) -> Product:
        return products[url]

    plan = build_plan(
        root,
        [
            bundle_url,
            f"Closed Guard={closed_url}",
            f"Open Guard={open_url}",
        ],
        RuntimeOptions(skip_chapters=True),
        scrape_product=scrape,
    )
    assert plan.show_url == bundle_url
    assert plan.plot.startswith("Bundle plot")
    assert "Should Not Match" not in plan.plot
    assert plan.premiered == date(2020, 1, 3)
    assert plan.unique_id == "999"
    assert plan.title == "Go Further Faster by John Danaher"
    assert [season.product.source_url for season in plan.seasons] == [closed_url, open_url]
    assert all(episode.title != "Should Not Match" for season in plan.seasons for episode in season.episodes)
    blob = __import__("xml.etree.ElementTree", fromlist=["tostring"]).tostring(
        tvshow_xml(plan), encoding="unicode"
    )
    assert ">999</uniqueid>" in blob
    assert "go-further-faster-bundle-by-john-danher" in blob


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
