from pathlib import Path

from bjj_organizer.naming import (
    episode_display_title,
    episode_filename,
    parse_video,
    sanitize_filename,
    show_title,
    volume_episode_filename,
)


def test_show_title_adds_by_and_does_not_duplicate():
    assert show_title("Go Further Faster", ["John Danaher"]) == "Go Further Faster by John Danaher"
    assert (
        show_title("Battle Tested Half Guard by Bernardo Faria", ["Bernardo Faria"])
        == "Battle Tested Half Guard by Bernardo Faria"
    )
    assert show_title("Ryan Smith Collection", ["Craig Jones", "Gordon Ryan"]) == (
        "Ryan Smith Collection by Various"
    )


def test_volume_regex_table():
    cases = {
        "BattleTestedHalfGuardDVD1.mp4": 1,
        "KGuardVol1.mp4.mp4": 1,
        "FinishingleglocksbyJacobCouch1.mp4": 1,
        "1 - Arm Bar - Enter the System.mp4": 1,
        "4 Arm Bar - Closed Guard - Go Further Faster.mp4": 4,
        "VOL1PT1 - Stance - Feet to Floor.mp4": 1,
        "GordonRyanVol1NEW.mp4.mp4": 1,
        "MasteringUchiMataTravisStevensVol3new.mp4": 3,
        "OpenGuardVolume2byJohnDanaher1.mp4": 1,
        "OpenGuardVolume2byJohnDanaher8.mp4": 8,
        "Open Guard Volume 2 by John Danaher 3.mp4": 3,
    }
    for name, volume in cases.items():
        parsed = parse_video(Path(name))
        assert parsed.volume_number == volume, name
        assert parsed.extension == ".mp4"
        assert not parsed.is_segmented_name, name
    worm = parse_video(Path("Keenan Cornelius   The Worm Guard DVD 1 [ZofVvwJcx4k].webm"))
    assert worm.volume_number == 1
    assert worm.extension == ".webm"


def test_local_descriptive_titles():
    parsed = parse_video(
        Path("4 Arm Bar - Closed Guard - Go Further Faster.mp4"),
        season_title="Closed Guard",
        show_stem="Go Further Faster",
    )
    assert parsed.local_title == "Arm Bar"

    parsed = parse_video(
        Path("1 - Arm Bar - Enter the System.mp4"),
        season_title="Arm Bar",
        show_stem="Enter the System",
    )
    assert parsed.local_title == "Arm Bar"

    parsed = parse_video(
        Path("VOL1PT1 - Stance - Feet to Floor.mp4"),
        season_title="Season 1",
        show_stem="Feet To Floor",
    )
    assert parsed.part_number == 1
    assert parsed.local_title == "Stance"

    parsed = parse_video(Path("BattleTestedHalfGuardDVD1.mp4"))
    assert parsed.local_title is None


def test_new_and_extra_and_double_ext():
    parsed = parse_video(Path("GordonRyanVol1NEW.mp4.mp4"))
    assert parsed.is_new
    assert parsed.extension == ".mp4"
    parsed = parse_video(Path("HalfButterflyMasterybyBrianGlick4EXECUTIVESUMMARY.mp4.mp4"))
    assert parsed.volume_number == 4
    assert not parsed.is_extra
    assert parsed.extension == ".mp4"
    parsed = parse_video(Path("Keenan Cornelius   The Worm Guard DVD Bonus 1 [ZofVvwJcx4k].webm"))
    assert parsed.is_extra
    assert parsed.extension == ".webm"


def test_already_named_sxxeyy():
    parsed = parse_video(Path("Go Further Faster by John Danaher - S01E04 - Arm Bar.mp4"))
    assert parsed.already_named
    assert parsed.volume_number == 4
    assert parsed.local_title == "Arm Bar"
    assert not parsed.is_segmented_name


def test_fanatics_segment_filename():
    parsed = parse_video(Path("4533018132578-01-01- Introduction.mp4"))
    assert parsed.is_segmented_name
    assert parsed.volume_number == 1
    assert parsed.chapter_number == 1
    assert parsed.local_title == "Introduction"

    parsed = parse_video(
        Path("4533018132578-02-02- Stepping On Hip Family One Variation One_ The Easiest Triangle Set Up.mp4")
    )
    assert parsed.volume_number == 2
    assert parsed.chapter_number == 2
    assert parsed.local_title is not None
    assert parsed.local_title.startswith("Stepping On Hip")


def test_already_named_segment():
    parsed = parse_video(Path("01.02 - Collar And Sleeve - What Is Collar And Sleeve.mp4"))
    assert parsed.is_segmented_name
    assert parsed.already_named
    assert parsed.volume_number == 1
    assert parsed.chapter_number == 2
    assert parsed.local_title == "Collar And Sleeve - What Is Collar And Sleeve"


def test_sanitize_and_episode_filename():
    assert "?" not in sanitize_filename("Foo: Bar? <>")
    name = episode_filename(1, 1, "Introduction", ".mp4")
    assert name == "01.01 - Introduction.mp4"
    name = episode_filename(2, 10, "Too late", ".mp4")
    assert name == "02.10 - Too late.mp4"
    assert episode_display_title(1, 2, "Introduction") == "1.2 Introduction"
    vol_name = volume_episode_filename(
        "The Collar and Sleeve System Part 1 by Mikey Musumeci",
        1,
        1,
        "Volume 1",
        ".mp4",
    )
    assert vol_name == (
        "The Collar and Sleeve System Part One by Mikey Musumeci - S01E01 - Volume 1.mp4"
    )
    assert show_title("The Collar and Sleeve System Pt 1", ["Mikey Musumeci"]) == (
        "The Collar and Sleeve System Part One by Mikey Musumeci"
    )
