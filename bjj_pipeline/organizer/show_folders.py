"""Short show-folder names on disk. NFO titles and episode filenames stay long."""

from __future__ import annotations

import re

from .naming import sanitize_filename, series_stem, show_title

# GFF product titles include a redundant "BJJ Fundamentals" subtitle. Dest names drop it.
_GFF_FUNDAMENTALS_RE = re.compile(r"\s*[:\-]?\s*BJJ Fundamentals(?=\s|$|,)", re.IGNORECASE)
_MULTI_SPACE_RE = re.compile(r"[ \t]{2,}")
_DOUBLE_HYPHEN_RE = re.compile(r"\s+-\s+-\s+")


def strip_gff_fundamentals(text: str) -> str:
    """Drop redundant 'BJJ Fundamentals' from GFF titles and dest stems."""
    if "bjj fundamentals" not in text.lower():
        return text
    out = _GFF_FUNDAMENTALS_RE.sub("", text)
    out = _MULTI_SPACE_RE.sub(" ", out)
    out = _DOUBLE_HYPHEN_RE.sub(" - ", out)
    return out

# Long library-root folder -> short dest. Keep Season 01. Do not change episode files.
SHOW_FOLDER_NAMES: dict[str, str] = {
    "Arm Bars Enter The System by John Danaher": "Danaher - ETS Arm Bars",
    "Back Attacks Enter The System by John Danaher": "Danaher - ETS Back Attacks",
    "Battle Tested Pressure Passing by Bernardo Faria": "Faria - BT Pressure Passing",
    "Buzzsaw Passing: Gi by Andrew Wiltse": "Wiltse - Buzzsaw GI Passing",
    "Butterfly by Marcelo Garcia": "Garcia - Butterfly",
    "Butterfly Guard Re-Discovered 2 by Adam Wardzinski": "Wardzinski - Bfly Rediscovered 2",
    "Butterfly Guard Re-Discovered by Adam Wardzinski": "Wardzinski - Bfly Rediscovered",
    "Butterfly Guard Rediscovered 3.0 by Adam Wardzinski": "Wardzinski - Bfly Rediscovered 3",
    "Chokes No Gi by Lachlan Giles": "Giles - Chokes NG",
    "Closed Guard - Go Further Faster by John Danaher": "Danaher - GFF Closed Guard",
    "Down Under Leg Attacks by Craig Jones": "Jones - Down Under Legs",
    "Enter the System by John Danaher - Leglocks": "Danaher - ETS Leglocks",
    "Feet To Floor Volume 1 Fundamental Standing Skills by John Danaher": "Danaher - FTF 1",
    "Feet To Floor Volume 2 by John Danaher": "Danaher - FTF 2",
    "Feet To Floor Volume 3 by John Danaher": "Danaher - FTF 3",
    "Finishing Leg Locks by Jacob Couch": "Couch - Finishing Leg Locks",
    "Foot Sweeps, Ankle Picks and Tripods Engineering by Adam Wardzinski": "Wardzinski - Foot Sweeps",
    "Galvao Style Back Attacks by Mica Galvao": "Mica Galvao - Back Attacks",
    "Get Off My Legs Gringo by Craig Jones": "Jones - Get Off My Legs",
    "Guard Retention - Go Further Faster by John Danaher": "Danaher - GFF Guard Retention",
    "Half Guard Anthology by Lachlan Giles": "Giles - HG Anthology",
    "Half Guard - Go Further Faster by John Danaher": "Danaher - GFF Half Guard",
    "Half Guard Passing and Dynamic Pins - Go Further Faster by John Danaher": (
        "Danaher - GFF HG Pass Pins"
    ),
    "High Percentage Gi Passes by Gordon Ryan": "Ryan - HiPerc Gi Passes",
    "Jay Rods Judo by Jay Rodriguez": "Rodriguez - Jay Rods Judo",
    "Kimura Enter The System by John Danaher": "Danaher - ETS Kimura",
    "Magic Guard Passing by Travis Stevens": "Stevens - Magic Guard Passing",
    "Make Z Guard Great Again by Craig Jones": "Jones - Make Z Guard",
    "Master The Move Arm Drags by John Danaher": "Danaher - MTM Arm Drags",
    "Master The Move The Side Crucifix by John Danaher": "Danaher - MTM Side Crucifix",
    "Mastering No Gi Takedowns by Travis Stevens": "Stevens - NG Takedowns",
    "Mastering The Knee Weave System by Kyle Watson": "Watson - Knee Weave",
    "Mastering The Lasso Guard by Marcos Tinoco": "Tinoco - Lasso Guard",
    "New Wave Jiu Jitsu A New Philosophy Of Submissions Escapes by John Danaher": (
        "Danaher - NW Sub Escapes"
    ),
    "New Wave Jiu Jitsu Mounted Pin Attacks - The 4x4 Mount System by John Danaher": (
        "Danaher - NW 4x4 Mount"
    ),
    "New Wave Jiu Jitsu Open Guard The two Foundations Of Guard Play by John Danaher": (
        "Danaher - NW OG Foundations"
    ),
    "New Wave Jiu Jitsu Open Guard vol 2 Sweeps and Reversals by John Danaher": (
        "Danaher - NW OG 2 Sweeps"
    ),
    "New Wave Jiu Jitsu Side Attacks - Building a Devastating Side Control System by John Danaher": (
        "Danaher - NW Side Attacks"
    ),
    "No Gi Open Guard Volume 1 K Guard by Lachlan Giles": "Giles - NG OG 1 K Guard",
    "No Gi Open Guard Volume 2 De La Riva & Waiter by Lachlan Giles": "Giles - NG OG 2 DLR",
    "No Gi Open Guard Volume 3 RDLR & Leg Entanglements by Lachlan Giles": "Giles - NG OG 3 RDLR",
    "No-Gi Judo Throws by Shintaro Higashi": "Higashi - NG Judo Throws",
    "Octopus Guard 2.0 by Craig Jones": "Jones - Octopus Guard 2",
    "Open Guard - Go Further Faster by John Danaher": "Danaher - GFF Open Guard",
    "Passing Modern Guard by Andre Galvao": "Andre Galvao - Passing Modern Guard",
    "Passing the Guard - Go Further Faster by John Danaher": "Danaher - GFF Passing",
    "Pin Escapes & Turtle Escapes - Go Further Faster by John Danaher": (
        "Danaher - GFF Pin Turtle Esc"
    ),
    "Polish Power Backtakes By Adam Wardzinski": "Wardzinski - PP Backtakes",
    "Polish Power Full Mount By Adam Wardzinski": "Wardzinski - PP Mount",
    "Polish Power Inside Passing By Adam Wardzinski": "Wardzinski - PP Inside Passing",
    "Polish Power Passing By Adam Wardzinski": "Wardzinski - PP Passing",
    "Polish Power Side Control By Adam Wardzinski": "Wardzinski - PP Side Control",
    "Power Ride A New Philosophy on Pinning by Craig Jones": "Jones - Power Ride",
    "Precision Back Takes by Lucas Lepri": "Lepri - Precision Back Takes",
    "Scientific Gripping Systems For Jiu Jitsu by Travis Stevens": "Stevens - Scientific Gripping",
    "Side Control Setups & Submissions by Bernardo Faria": "Faria - Side Control",
    "Special K Guard by Neil Melanson": "Melanson - Special K",
    "Spider Guard Mastery by Michael Langhi": "Langhi - Spider Guard",
    "Standing2Ground Positional Dominance & Scrimmage Wrestling by John Danaher": (
        "Danaher - S2G Positional"
    ),
    "Standing2Ground Takedowns & Standing Skills For Jiu Jitsu by John Danaher": (
        "Danaher - S2G Takedowns"
    ),
    "Standing2Ground Upper Body Takedowns by John Danaher": "Danaher - S2G Upper Body",
    "Strangles & Turtle Breakdowns - Go Further Faster by John Danaher": (
        "Danaher - GFF Strangles Turtle"
    ),
    "Submission Escapes by Tom DeBlass": "DeBlass - Submission Escapes",
    "Systematically Attacking From Half Guard by Gordon Ryan": "Ryan - SysAtk Half Guard",
    "Systematically Attacking From Open Guard Seated Position by Gordon Ryan": (
        "Ryan - SysAtk Seated OG"
    ),
    "Systematically Attacking The Guard by Gordon Ryan": "Ryan - SysAtk The Guard",
    "The Battle Tested Half Guard by Bernardo Faria": "Faria - BT Half Guard",
    "The Collar and Sleeve System Part One by Mikey Musumeci": "Musumeci - Collar Sleeve 1",
    "The Daisy Fresh Knee Slice by Andrew Wiltse": "Wiltse - Daisy Fresh Knee Slice",
    "The Fastest Way To Increase your Submission Percentage by John Danaher": (
        "Danaher - Fastest Sub Pct"
    ),
    "The Front Headlock System by John Danaher": "Danaher - ETS Front Headlock",
    "The Hip Bump by Ryan Hall": "Hall - Hip Bump",
    "The No Gi Butterfly Guard Rediscovered by Adam Wardzinski": "Wardzinski - NG Bfly Rediscovered",
    "The Pendejo Guard by Craig Jones": "Jones - Pendejo Guard",
    "The Polish Power System Bundle By Adam Wardzinski": "Wardzinski - PP Bundle",
    "The Triangle Machine by Craig Jones": "Jones - Triangle Machine",
    "The Z Guard Encyclopedia by Craig Jones": "Jones - Z Guard Encyc",
    "Triangles Enter The System by John Danaher": "Danaher - ETS Triangles",
    "Uchi Mata by Travis Stevens": "Stevens - Uchi Mata",
    "Under Pressure Half Butterfly Guard Mastery by Brian Glick": "Glick - HG Butterfly",
    "Worm Guard (Legacy) by Keenan Cornelius": "Cornelius - Worm Guard",
}

LONG_FOLDER_FROM_SHORT: dict[str, str] = {short: long for long, short in SHOW_FOLDER_NAMES.items()}

_PHRASES: tuple[tuple[str, str], ...] = (
    ("bjj fundamentals - go further faster", "GFF"),
    ("go further faster", "GFF"),
    ("enter the system", "ETS"),
    ("new wave jiu jitsu", "NW"),
    ("feet to floor", "FTF"),
    ("standing2ground", "S2G"),
    ("master the move", "MTM"),
    ("polish power", "PP"),
    ("systematically attacking", "SysAtk"),
    ("no gi open guard", "NG OG"),
    ("no-gi", "NG"),
    ("no gi", "NG"),
)


def instructor_folder_token(instructors: list[str]) -> str:
    unique: list[str] = []
    seen: set[str] = set()
    for name in instructors:
        text = name.strip()
        key = text.lower()
        if text and key not in seen:
            seen.add(key)
            unique.append(text)
    if len(unique) != 1:
        return "Various" if unique else ""
    parts = unique[0].split()
    last = parts[-1]
    if last.lower() == "galvao" and len(parts) > 1:
        return unique[0]
    return last


def abbreviate_instructional_stem(stem: str) -> str:
    text = " ".join(stem.split())
    lowered = text.lower()
    for needle, token in _PHRASES:
        index = lowered.find(needle)
        if index < 0:
            continue
        text = text[:index] + token + text[index + len(needle) :]
        lowered = text.lower()
    text = text.strip(" -")
    if text.lower().startswith("the "):
        text = text[4:]
    return sanitize_filename(text)


def dest_show_folder(folder_name: str, instructors: list[str] | None = None) -> str:
    """Short folder name for a show. Identity if already short."""
    if folder_name in SHOW_FOLDER_NAMES:
        return SHOW_FOLDER_NAMES[folder_name]
    stripped = strip_gff_fundamentals(folder_name)
    if stripped != folder_name and stripped in SHOW_FOLDER_NAMES:
        return SHOW_FOLDER_NAMES[stripped]
    if folder_name in LONG_FOLDER_FROM_SHORT:
        return folder_name
    stem = series_stem(folder_name)
    short = abbreviate_instructional_stem(stem)
    token = instructor_folder_token(instructors or [])
    if token and token.lower() not in short.lower():
        short = f"{token} - {short}"
    return sanitize_filename(short) or folder_name


def show_display_title(folder_name: str, instructors: list[str], nfo_title: str = "") -> str:
    """NFO / episode-filename title. Prefer existing NFO, then the long folder name."""
    if nfo_title.strip():
        return strip_gff_fundamentals(nfo_title.strip())
    long_name = LONG_FOLDER_FROM_SHORT.get(folder_name, folder_name)
    return strip_gff_fundamentals(show_title(long_name, instructors))
