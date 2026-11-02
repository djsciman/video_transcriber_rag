from datetime import date
from pathlib import Path

import split_bundles

from bjj_organizer.errors import ScrapeError
from bjj_organizer.models import Product, ProductImage
from bjj_organizer.split_bundles import apply_bundles, discover_bundles, has_problems, plan_bundles


def _product(
    title: str,
    handle: str,
    product_id: str,
    *,
    plot: str = "A real plot.",
    instructor: str = "John Danaher",
    premiered: date = date(2019, 9, 6),
) -> Product:
    return Product(
        title=title,
        instructor=instructor,
        plot=plot,
        premiered=premiered,
        year=premiered.year,
        tags=["Instructional", "Guard"],
        unique_ids={"bjjfanatics": product_id, "bjjfanatics-handle": handle},
        images=[],
        volumes=[],
        source_url=f"https://bjjfanatics.com/products/{handle}",
    )


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _tvshow(*seasons: tuple[int, str], director: str = "John Danaher") -> str:
    named = "\n".join(
        f'  <namedseason number="{number}">{label}</namedseason>' for number, label in seasons
    )
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        "<tvshow>\n"
        "  <title>Bundle Show</title>\n"
        f"  <director>{director}</director>\n"
        f"{named}\n"
        '  <uniqueid type="bjjfanatics" default="true">111</uniqueid>\n'
        "</tvshow>\n"
    )


def _season_nfo(number: int, handle: str, product_id: str) -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        "<season>\n"
        f"  <title>Season {number}</title>\n"
        f"  <seasonnumber>{number}</seasonnumber>\n"
        f'  <uniqueid type="bjjfanatics" default="true">{product_id}</uniqueid>\n'
        f'  <uniqueid type="bjjfanatics-handle">{handle}</uniqueid>\n'
        "</season>\n"
    )


def _episode_nfo(show: str, season: int, episode: int, plot: str = "keep this plot") -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        "<episodedetails>\n"
        "  <title>Introduction</title>\n"
        f"  <showtitle>{show}</showtitle>\n"
        f"  <season>{season}</season>\n"
        f"  <episode>{episode}</episode>\n"
        f"  <plot>{plot}</plot>\n"
        "  <aired>2019-09-06</aired>\n"
        "  <director>John Danaher</director>\n"
        "</episodedetails>\n"
    )


def _bundle(root: Path) -> Path:
    show = root / "Go Further Faster By John Danaher"
    _write(
        show / "tvshow.nfo",
        _tvshow((2, "Half Guard"), (3, "Closed Guard")),
    )
    _write(show / "poster.jpg", "bundle-poster")
    season = show / "Season 02"
    _write(season / "season.nfo", _season_nfo(2, "half-guard", "396"))
    _write(season / "poster.jpg", "half-poster")
    video = "Go Further Faster by John Danaher - S02E03 - Introduction.mp4"
    _write(season / video, "video-bytes")
    _write(
        season / "Go Further Faster by John Danaher - S02E03 - Introduction.nfo",
        _episode_nfo("Go Further Faster by John Danaher", 2, 3),
    )
    other = show / "Season 03"
    _write(other / "season.nfo", _season_nfo(3, "closed-guard", "397"))
    _write(other / "poster.jpg", "closed-poster")
    other_video = "Go Further Faster by John Danaher - S03E01 - Overview.mp4"
    _write(other / other_video, "other-video")
    _write(
        other / "Go Further Faster by John Danaher - S03E01 - Overview.nfo",
        _episode_nfo("Go Further Faster by John Danaher", 3, 1, "closed plot"),
    )
    return show


def _resolver(handle: str) -> Product:
    catalog = {
        "half-guard": _product(
            "Half Guard: Fundamentals by John Danaher",
            "half-guard",
            "396",
            plot="Half guard plot.",
        ),
        "closed-guard": _product(
            "Closed Guard by John Danaher",
            "closed-guard",
            "397",
            plot="Closed guard plot.",
        ),
    }
    if handle not in catalog:
        raise ScrapeError(f"missing {handle}")
    return catalog[handle]


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_split_two_seasons_rewrites_names_nfo_and_artwork(tmp_path: Path):
    show = _bundle(tmp_path)
    bundles = plan_bundles([show], offline=False, resolve_product=_resolver)
    apply_bundles(bundles)

    half = tmp_path / "Half Guard Fundamentals by John Danaher"
    closed = tmp_path / "Closed Guard by John Danaher"
    half_video = half / "Season 01" / (
        "Half Guard Fundamentals by John Danaher - S01E03 - Introduction.mp4"
    )
    assert half_video.read_text(encoding="utf-8") == "video-bytes"
    episode = _text(half_video.with_suffix(".nfo"))
    assert "<showtitle>Half Guard: Fundamentals by John Danaher</showtitle>" in episode
    assert "<season>1</season>" in episode
    assert "<episode>3</episode>" in episode
    assert "<plot>keep this plot</plot>" in episode
    assert "<aired>2019-09-06</aired>" in episode

    show_nfo = _text(half / "tvshow.nfo")
    assert "<title>Half Guard: Fundamentals by John Danaher</title>" in show_nfo
    assert "<plot>Half guard plot.</plot>" in show_nfo
    assert ">396</uniqueid>" in show_nfo
    assert "half-guard" in show_nfo
    assert 'namedseason number="1"' in show_nfo
    assert "<lockdata>false</lockdata>" in show_nfo
    season_nfo = _text(half / "Season 01" / "season.nfo")
    assert "<title>Half Guard: Fundamentals by John Danaher</title>" in season_nfo
    assert "<seasonnumber>1</seasonnumber>" in season_nfo
    assert ">396</uniqueid>" in season_nfo

    assert (half / "poster.jpg").read_text(encoding="utf-8") == "half-poster"
    assert (half / "folder.jpg").read_text(encoding="utf-8") == "half-poster"
    assert (half / "fanart.jpg").read_text(encoding="utf-8") == "half-poster"
    assert (half / "Season 01" / "poster.jpg").read_text(encoding="utf-8") == "half-poster"

    closed_video = closed / "Season 01" / (
        "Closed Guard by John Danaher - S01E01 - Overview.mp4"
    )
    assert closed_video.is_file()
    assert "<season>1</season>" in _text(closed_video.with_suffix(".nfo"))
    assert not show.exists()
    assert not has_problems(bundles)


def test_default_library_is_the_working_directory(tmp_path: Path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    code = split_bundles.main(["--offline"])
    captured = capsys.readouterr()
    assert code == 0
    assert "No bundle shows" in captured.out


def test_one_season_show_is_ignored(tmp_path: Path):
    show = tmp_path / "Magic Guard Passing by Travis Stevens"
    _write(show / "Season 01" / "poster.jpg", "poster")
    found, note = discover_bundles(tmp_path, None)
    assert found == []
    assert note == ""
    single, single_note = discover_bundles(tmp_path, show)
    assert single == []
    assert "not a bundle show" in single_note


def test_leftover_folder_keeps_the_bundle(tmp_path: Path):
    show = _bundle(tmp_path)
    _write(show / "The Daisy Fresh Knee Slice by Andrew Wiltse" / "clip.mp4", "clip")
    bundles = plan_bundles([show], offline=False, resolve_product=_resolver)
    apply_bundles(bundles)
    assert show.is_dir()
    assert (show / "The Daisy Fresh Knee Slice by Andrew Wiltse" / "clip.mp4").is_file()
    assert not (show / "tvshow.nfo").exists()
    assert not (show / "Season 02").exists()
    assert bundles[0].leftovers == ["The Daisy Fresh Knee Slice by Andrew Wiltse"]


def test_existing_destination_skips_that_season(tmp_path: Path):
    show = _bundle(tmp_path)
    taken = tmp_path / "Closed Guard by John Danaher"
    _write(taken / "Season 01" / "already.mp4", "keep")
    bundles = plan_bundles([show], offline=False, resolve_product=_resolver)
    closed = next(season for season in bundles[0].seasons if season.number == 3)
    assert closed.skipped
    assert "already exists" in closed.skip_reason
    apply_bundles(bundles)
    assert (show / "Season 03").is_dir()
    assert (taken / "Season 01" / "already.mp4").read_text(encoding="utf-8") == "keep"
    assert not (show / "Season 02").exists()
    assert show.is_dir()
    assert has_problems(bundles)


def test_offline_uses_named_season_and_director(tmp_path: Path):
    show = _bundle(tmp_path)
    bundles = plan_bundles([show], offline=True, resolve_product=_resolver)
    titles = {season.number: season.title for season in bundles[0].seasons}
    assert titles[2] == "Half Guard by John Danaher"
    assert titles[3] == "Closed Guard by John Danaher"
    apply_bundles(bundles)
    dest = tmp_path / "Half Guard by John Danaher"
    assert (dest / "Season 01").is_dir()
    assert "<title>Half Guard by John Danaher</title>" in _text(dest / "tvshow.nfo")
    assert ">396</uniqueid>" in _text(dest / "tvshow.nfo")


def test_video_without_episode_token_is_moved_and_reported(tmp_path: Path):
    show = tmp_path / "Bundle"
    _write(show / "tvshow.nfo", _tvshow((1, "Arm Drags"), (2, "Knee Cut")))
    first = show / "Season 01"
    _write(first / "season.nfo", _season_nfo(1, "arm-drags", "10"))
    _write(first / "poster.jpg", "p1")
    _write(first / "loose-clip.mp4", "loose")
    _write(first / "loose-clip.nfo", _episode_nfo("Bundle", 4, 9, "loose plot"))
    second = show / "Season 02"
    _write(second / "season.nfo", _season_nfo(2, "knee-cut", "11"))
    _write(second / "poster.jpg", "p2")
    _write(second / "Bundle - S02E01 - Knee Cut.mp4", "knee")
    _write(second / "Bundle - S02E01 - Knee Cut.nfo", _episode_nfo("Bundle", 2, 1))

    def resolve(handle: str) -> Product:
        if handle == "arm-drags":
            return _product("Arm Drags by John Danaher", handle, "10", plot="Arm plot.")
        return _product("Knee Cut by John Danaher", handle, "11", plot="Knee plot.")

    bundles = plan_bundles([show], offline=False, resolve_product=resolve)
    loose = next(item for item in bundles[0].seasons[0].files if item.source_name == "loose-clip.mp4")
    assert "no SxxEyy token" in loose.warning
    apply_bundles(bundles)
    moved = tmp_path / "Arm Drags by John Danaher" / "Season 01" / "loose-clip.mp4"
    assert moved.read_text(encoding="utf-8") == "loose"
    nfo = _text(moved.with_suffix(".nfo"))
    assert "<showtitle>Arm Drags by John Danaher</showtitle>" in nfo
    assert "<season>1</season>" in nfo
    assert "<episode>9</episode>" in nfo
    assert "<plot>loose plot</plot>" in nfo
    assert has_problems(bundles)


def test_fetch_failure_skips_one_season_and_continues(tmp_path: Path):
    show = _bundle(tmp_path)

    def resolve(handle: str) -> Product:
        if handle == "half-guard":
            raise ScrapeError("HTTP 404 fetching half-guard")
        return _resolver(handle)

    bundles = plan_bundles([show], offline=False, resolve_product=resolve)
    failed = next(season for season in bundles[0].seasons if season.number == 2)
    assert failed.skipped and failed.fetch_failed
    apply_bundles(bundles)
    assert (show / "Season 02").is_dir()
    assert (tmp_path / "Closed Guard by John Danaher" / "Season 01").is_dir()
    assert show.is_dir()
    assert has_problems(bundles)


def test_downloads_poster_when_the_season_has_none(tmp_path: Path, monkeypatch):
    show = tmp_path / "Bundle"
    _write(show / "tvshow.nfo", _tvshow((1, "Arm Drags"), (2, "Knee Cut")))
    for number, handle, product_id in ((1, "arm-drags", "10"), (2, "knee-cut", "11")):
        season = show / f"Season {number:02d}"
        _write(season / "season.nfo", _season_nfo(number, handle, product_id))
        _write(season / f"Bundle - S0{number}E01 - Clip.mp4", "video")
        _write(
            season / f"Bundle - S0{number}E01 - Clip.nfo",
            _episode_nfo("Bundle", number, 1),
        )

    def resolve(handle: str) -> Product:
        product = _product(f"{handle} by John Danaher", handle, "10" if handle == "arm-drags" else "11")
        product.images = [
            ProductImage(url=f"https://example.test/{handle}.jpg", width=10, height=10, alt="", position=1)
        ]
        return product

    def fake_download(url: str, dest: Path, user_agent: str = "") -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(b"downloaded-poster")
        return dest

    monkeypatch.setattr("bjj_organizer.split_bundles.download_image", fake_download)
    bundles = plan_bundles([show], offline=False, resolve_product=resolve)
    assert any("downloaded on apply" in warning for warning in bundles[0].seasons[0].warnings)
    apply_bundles(bundles)
    dest = tmp_path / "arm-drags by John Danaher"
    assert (dest / "poster.jpg").read_bytes() == b"downloaded-poster"
    assert (dest / "Season 01" / "poster.jpg").read_bytes() == b"downloaded-poster"


def test_resume_moves_into_matching_show_without_replacing_nfo(tmp_path: Path):
    show = _bundle(tmp_path)
    dest = tmp_path / "Closed Guard by John Danaher"
    _write(
        dest / "tvshow.nfo",
        """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<tvshow>
  <title>Closed Guard by John Danaher</title>
  <plot>keep-show</plot>
  <uniqueid type="bjjfanatics" default="true">397</uniqueid>
</tvshow>
""",
    )
    _write(dest / "Season 01" / "season.nfo", "<season><title>keep-season</title></season>")
    _write(dest / "Season 01" / "poster.jpg", "dest-poster")
    bundles = plan_bundles([show], offline=False, resolve_product=_resolver)
    closed = next(season for season in bundles[0].seasons if season.number == 3)
    assert not closed.skipped
    apply_bundles(bundles)
    video = dest / "Season 01" / "Closed Guard by John Danaher - S01E01 - Overview.mp4"
    assert video.read_text(encoding="utf-8") == "other-video"
    assert "keep-show" in _text(dest / "tvshow.nfo")
    assert "keep-season" in _text(dest / "Season 01" / "season.nfo")
    assert (dest / "Season 01" / "poster.jpg").read_text(encoding="utf-8") == "dest-poster"
    episode = _text(video.with_suffix(".nfo"))
    assert "<showtitle>Closed Guard by John Danaher</showtitle>" in episode
    assert "<season>1</season>" in episode
    assert not (show / "Season 03").exists()


def test_episode_names_shorten_to_fit_windows_path(tmp_path: Path, monkeypatch):
    import bjj_organizer.split_bundles as splitter

    show = _bundle(tmp_path)
    dest_season = tmp_path / "Half Guard Fundamentals by John Danaher" / "Season 01"
    short = "S01E03 - Introduction.mp4"
    monkeypatch.setattr(splitter, "PATH_LIMIT", len(str(dest_season / short)))
    bundles = plan_bundles([show], offline=False, resolve_product=_resolver)
    half = next(season for season in bundles[0].seasons if season.number == 2)
    video = next(item for item in half.files if item.source_name.endswith(".mp4"))
    assert video.dest_name == short
    assert any("shortened" in warning for warning in half.warnings)
    apply_bundles(bundles)
    assert (dest_season / short).read_text(encoding="utf-8") == "video-bytes"
    assert not has_problems(bundles)
