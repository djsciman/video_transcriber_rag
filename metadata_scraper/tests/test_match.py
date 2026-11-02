from pathlib import Path

import pytest

from bjj_organizer.errors import MatchError
from bjj_organizer.match import detect_media_mode, flatten_chapters, match_season, match_volumes, parse_videos
from bjj_organizer.models import Chapter, Volume
from bjj_organizer.naming import parse_video


def _vols(n: int, chapters_each: int = 1) -> list[Volume]:
    volumes = []
    for i in range(1, n + 1):
        chapters = tuple(Chapter(f"V{i}C{c}", (c - 1) * 1000) for c in range(1, chapters_each + 1))
        volumes.append(Volume(name=f"Volume {i}", chapters=chapters))
    return volumes


def test_equal_count_pairs_by_order():
    files = [Path(f"TitleVol{i}.mp4") for i in (1, 2, 3, 4)]
    pairs, extras, _ = match_volumes(files, _vols(4))
    assert [p[0].volume_number for p in pairs] == [1, 2, 3, 4]
    assert extras == []


def test_new_preferred_over_duplicate():
    files = [Path("GordonRyanVol1.mp4"), Path("GordonRyanVol1NEW.mp4")]
    pairs, extras, warnings = match_volumes(files, _vols(1))
    assert pairs[0][0].path.name == "GordonRyanVol1NEW.mp4"
    assert extras[0].name == "GordonRyanVol1.mp4"
    assert warnings


def test_product_title_volume_uses_trailing_disc():
    files = [Path(f"OpenGuardVolume2byJohnDanaher{i}.mp4") for i in range(1, 9)]
    for index, path in enumerate(files, start=1):
        parsed = parse_video(path)
        assert parsed.volume_number == index
        assert parsed.part_number is None
        assert parsed.local_title is None
        assert not parsed.is_segmented_name
    pairs, extras, warnings = match_volumes(files, _vols(8, chapters_each=3))
    assert [pair[0].volume_number for pair in pairs] == list(range(1, 9))
    assert [pair[0].path.name for pair in pairs] == [path.name for path in files]
    assert extras == []
    assert warnings == []


def test_executive_summary_disc_counts_as_a_volume():
    files = [
        Path("HalfButterflyMasterybyBrianGlick1NEW.mp4.mp4"),
        Path("HalfButterflyMasterybyBrianGlick2.mp4.mp4"),
        Path("HalfButterflyMasterybyBrianGlick3.mp4.mp4"),
        Path("HalfButterflyMasterybyBrianGlick4EXECUTIVESUMMARY.mp4.mp4"),
    ]
    result = match_season(files, _vols(4, chapters_each=3))
    assert result.mode == "volume"
    assert result.extras == []
    assert [item.parsed.path.name for item in result.items[::3]] == [path.name for path in files]


def test_too_few_files_aborts():
    files = [Path("TitleVol1.mp4"), Path("TitleVol2.mp4")]
    with pytest.raises(MatchError, match="Fewer local videos"):
        match_volumes(files, _vols(4))


def test_leftover_becomes_extra():
    files = [Path(f"TitleVol{i}.mp4") for i in range(1, 6)]
    pairs, extras, warnings = match_volumes(files, _vols(4))
    assert len(pairs) == 4
    assert extras[0].name == "TitleVol5.mp4"
    assert warnings


def test_unparsed_equal_count_pairs_by_name():
    files = [Path("aaa.mp4"), Path("bbb.mp4")]
    pairs, extras, warnings = match_volumes(files, _vols(2))
    assert [p[0].path.name for p in pairs] == ["aaa.mp4", "bbb.mp4"]
    assert extras == []
    assert any("sorted name" in w for w in warnings)


def test_flatten_chapters():
    volumes = _vols(2, chapters_each=3)
    flat = flatten_chapters(volumes)
    assert [(v, c) for v, c, _, _ in flat] == [(1, 1), (1, 2), (1, 3), (2, 1), (2, 2), (2, 3)]


def test_mode_segmented_when_fanatics_names():
    files = [
        Path("4533018132578-01-01- Introduction.mp4"),
        Path("4533018132578-01-02- Next.mp4"),
        Path("4533018132578-02-01- Other.mp4"),
    ]
    parsed = parse_videos(files)
    volumes = _vols(2, chapters_each=2)
    volumes[1] = Volume("Volume 2", (Chapter("Other", 0),))
    assert detect_media_mode(parsed, volumes) == "segmented"


def test_mode_volume_when_file_count_matches_volumes():
    files = [Path(f"TitleVol{i}.mp4") for i in (1, 2, 3, 4)]
    parsed = parse_videos(files)
    assert detect_media_mode(parsed, _vols(4, chapters_each=5)) == "volume"


def test_mode_segmented_when_file_count_equals_chapters():
    files = [Path(f"clip{i:02d}.mp4") for i in range(1, 7)]
    parsed = parse_videos(files)
    assert detect_media_mode(parsed, _vols(2, chapters_each=3)) == "segmented"


def test_mode_one_chapter_per_volume_is_segmented():
    files = [Path(f"TitleVol{i}.mp4") for i in (1, 2, 3, 4)]
    parsed = parse_videos(files)
    assert detect_media_mode(parsed, _vols(4, chapters_each=1)) == "segmented"


def test_match_season_segmented_preserves_vol_ch_order():
    files = [
        Path("4533018132578-02-01- World One.mp4"),
        Path("4533018132578-01-02- Collar.mp4"),
        Path("4533018132578-01-01- Introduction.mp4"),
    ]
    volumes = [
        Volume("Volume 1", (Chapter("Introduction", 0), Chapter("Collar And Sleeve", 1000))),
        Volume("Volume 2", (Chapter("World One Outside Control", 0),)),
    ]
    result = match_season(files, volumes)
    assert result.mode == "segmented"
    assert [(i.volume_number, i.chapter_number) for i in result.items] == [(1, 1), (1, 2), (2, 1)]
    assert result.items[0].chapter_title == "Introduction"
    assert result.items[0].parsed.path.name.endswith("Introduction.mp4")


def test_bundle_disc_numbers_align_to_product_volumes():
    files = [
        Path("6617708494946-09-01- Dlr Overview.mp4"),
        Path("6617708494946-09-02- Gi Vs No Gi.mp4"),
        Path("6617708494946-10-01- Waiter Overview.mp4"),
    ]
    volumes = [
        Volume("Volume 1", (Chapter("DLR overview", 0), Chapter("Gi vs no gi", 0))),
        Volume("Volume 2", (Chapter("Waiter overview", 0),)),
    ]
    result = match_season(files, volumes)
    assert result.mode == "segmented"
    assert [(item.volume_number, item.chapter_number) for item in result.items] == [
        (1, 1),
        (1, 2),
        (2, 1),
    ]
    assert result.items[0].parsed.path.name.startswith("6617708494946-09-01")
    assert result.items[2].parsed.path.name.startswith("6617708494946-10-01")
    assert any("bundle sequence" in warning for warning in result.warnings)


def test_bundle_shift_when_disc_number_collides_with_later_volume():
    files = [
        Path("6644438007906-02-01- Side.mp4"),
        Path("6644438007906-02-02- Underhook.mp4"),
        Path("6644438007906-03-01- Shoulder.mp4"),
    ]
    volumes = [
        Volume("Volume 1", (Chapter("Side", 0), Chapter("Underhook", 0))),
        Volume("Volume 2", (Chapter("Shoulder", 0),)),
    ]
    result = match_season(files, volumes)
    assert [(item.volume_number, item.chapter_number) for item in result.items] == [
        (1, 1),
        (1, 2),
        (2, 1),
    ]
    assert result.items[0].parsed.path.name.endswith("Side.mp4")
    assert any("bundle sequence" in warning for warning in result.warnings)


def test_near_complete_segment_match_skips_missing_chapter():
    files = [Path(f"6644438007906-02-{index:02d}- Chapter {index}.mp4") for index in range(1, 10)]
    volumes = [Volume("Volume 1", tuple(Chapter(f"Chapter {index}", 0) for index in range(1, 11)))]
    result = match_season(files, volumes)
    assert [item.chapter_number for item in result.items] == list(range(1, 10))
    assert any("1.10 Chapter 10" in warning for warning in result.warnings)


def test_in_range_segment_numbers_are_not_shifted():
    files = [Path("6617708494946-01-01- Introduction.mp4")]
    result = match_season(files, [Volume("Volume 1", (Chapter("Introduction", 0),))])
    assert result.items[0].volume_number == 1
    assert result.items[0].chapter_number == 1
    assert not any("bundle sequence" in warning for warning in result.warnings)


def test_match_season_volume_expands_chapters():
    files = [Path("TitleVol1.mp4"), Path("TitleVol2.mp4")]
    volumes = _vols(2, chapters_each=3)
    result = match_season(files, volumes)
    assert result.mode == "volume"
    assert len(result.items) == 6
    assert [(i.volume_number, i.chapter_number) for i in result.items] == [
        (1, 1),
        (1, 2),
        (1, 3),
        (2, 1),
        (2, 2),
        (2, 3),
    ]
    assert result.items[0].split_start_ms == 0
    assert result.items[0].split_end_ms == 1000
    assert result.items[2].split_end_ms is None
    assert result.items[0].parsed.path == result.items[1].parsed.path


def test_untimed_chapter_list_keeps_one_file_per_volume():
    files = [Path(f"OpenGuardSeatedVolume{i}.mp4") for i in range(1, 3)]
    volumes = [
        Volume("Volume 1", (Chapter("Intro", 0), Chapter("Goal setting", 0))),
        Volume("Volume 2", (Chapter("Ankle pick", 0), Chapter("De ashi", 0))),
    ]
    result = match_season(files, volumes)
    assert result.mode == "volume"
    assert len(result.items) == 2
    assert [item.chapter_title for item in result.items] == ["Volume 1", "Volume 2"]
    assert [item.split_start_ms for item in result.items] == [None, None]
    assert [chapter.title for chapter in result.items[0].toc] == ["Intro", "Goal setting"]
    assert any("without timestamps" in warning for warning in result.warnings)


def test_match_season_skip_chapters_keeps_volumes_whole():
    files = [Path("TitleVol1.mp4"), Path("TitleVol2.mp4")]
    result = match_season(files, _vols(2, chapters_each=4), skip_chapters=True)
    assert result.mode == "volume"
    assert len(result.items) == 2
    assert [i.chapter_number for i in result.items] == [1, 1]
    assert result.items[0].split_start_ms is None


def test_match_season_too_few_segments_aborts():
    files = [Path("4533018132578-01-01- Introduction.mp4")]
    with pytest.raises(MatchError, match="Fewer local videos than scraped chapters"):
        match_season(files, _vols(1, chapters_each=3))


def test_parse_video_imported_for_sanity():
    assert parse_video(Path("TitleVol1.mp4")).volume_number == 1
