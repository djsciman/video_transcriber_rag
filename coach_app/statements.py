"""Propose cleaned statements from a cleaned raw volume. Does not enter the curated store."""

from __future__ import annotations

import re

_MIN_CHAPTER_SECONDS = 60.0
_SKIP_TITLE = re.compile(
    r"(?i)^\s*(?:intro(?:duction)?|outro|named\s+roll|narrated\s+rolling)\s*$"
)


def propose_statements(cleaned_volume: dict, advisor, *, instructor: str = "", marks=()):
    """Return proposed statements. Writes nothing to the curated store."""
    proposals = []
    for part in _citeable_parts(cleaned_volume, marks):
        for movement in _movements_for(part):
            drafted = advisor.draft(
                part=part,
                movement=movement,
                instructor=instructor,
                volume=cleaned_volume,
            )
            if drafted:
                proposals.append(drafted)
    return proposals


def _citeable_parts(cleaned_volume: dict, marks) -> list[dict]:
    citeable = []
    for part in cleaned_volume.get("parts") or []:
        title = str(part.get("title") or "").strip()
        if not title:
            for mark in marks or ():
                sliced = _part_from_mark(part, mark)
                if _passes_citation_bar(sliced):
                    citeable.append(sliced)
            continue
        if _passes_citation_bar(part):
            citeable.append(part)
    return citeable


def _part_from_mark(part: dict, mark: dict) -> dict:
    start = float(mark["start"])
    end = float(mark["end"])
    return {
        "title": mark["title"],
        "start": start,
        "end": end,
        "speech": [
            span
            for span in part.get("speech") or []
            if start <= span["start"] <= end
        ],
    }


def _passes_citation_bar(part: dict) -> bool:
    title = str(part.get("title") or "").strip()
    if not title or _SKIP_TITLE.match(title):
        return False
    duration = float(part.get("end") or 0) - float(part.get("start") or 0)
    return duration >= _MIN_CHAPTER_SECONDS


_SPLIT_TITLE = re.compile(r"\s*(?:,|\&|/|\band\b)\s*", re.IGNORECASE)


def _movements_for(part: dict) -> tuple[str, ...]:
    title = str(part.get("title") or "").strip()
    if not title:
        return ()
    pieces = [piece.strip() for piece in _SPLIT_TITLE.split(title) if piece.strip()]
    if len(pieces) <= 1:
        return (title,)
    return tuple(piece for piece in pieces if not _SKIP_TITLE.match(piece))


_FALSE_START = re.compile(r"[^,]+,\s*sorry,\s*", re.IGNORECASE)
_WORD = re.compile(r"[A-Za-z']+")


class StatementDrafter:
    """Injectable collaborator that drafts statements from cleaned speech."""

    def draft(self, *, part, movement, instructor, volume):
        context = " ".join(
            span.get("text") or "" for span in part.get("speech") or []
        )
        restored = [
            {
                "start": span["start"],
                "end": span["end"],
                "text": _label_connection(
                    _restore_text(span["text"], volume), context
                ),
            }
            for span in part.get("speech") or []
        ]
        texts = [span["text"] for span in restored if span["text"]]
        return {
            "movement": movement,
            "instructor": instructor,
            "chapter": part["title"],
            "cleaned_statement": " ".join(texts),
            "step_bullets": tuple(texts),
            "details": tuple(
                {"text": span["text"], "speech_start": span["start"]}
                for span in restored
                if span["text"]
            ),
        }


_CONNECTION_LABELS = (
    (
        re.compile(r"their arm toward the (?:entangled )?legs", re.IGNORECASE),
        "their inside arm",
    ),
    (
        re.compile(r"your arm toward the (?:entangled )?legs", re.IGNORECASE),
        "inside arm",
    ),
    (
        re.compile(r"arm toward the (?:entangled )?legs", re.IGNORECASE),
        "inside arm",
    ),
    (
        re.compile(
            r"their arm away from the (?:entangled )?legs", re.IGNORECASE
        ),
        "their outside arm",
    ),
    (
        re.compile(
            r"your arm away from the (?:entangled )?legs", re.IGNORECASE
        ),
        "outside arm",
    ),
    (
        re.compile(r"arm away from the (?:entangled )?legs", re.IGNORECASE),
        "outside arm",
    ),
)


def _label_connection(text: str, context: str) -> str:
    if "half guard" not in context.casefold():
        return text
    labeled = text
    for pattern, replacement in _CONNECTION_LABELS:
        labeled = pattern.sub(replacement, labeled)
    return labeled


def _restore_text(text: str, volume: dict) -> str:
    collapsed = _FALSE_START.sub("", text)
    winners, surfaces = _preferred_forms(volume)

    def replace(match: re.Match) -> str:
        word = match.group(0)
        lemma = _lemma(word)
        winner = winners.get(lemma, lemma)
        if winner == lemma:
            return word
        replacement = surfaces[winner]
        if word[:1].isupper():
            return replacement[:1].upper() + replacement[1:]
        return replacement

    return _WORD.sub(replace, collapsed)


def _preferred_forms(volume: dict) -> tuple[dict[str, str], dict[str, str]]:
    words = _volume_words(volume)
    grouped: dict[str, list[str]] = {}
    for word in words:
        grouped.setdefault(_lemma(word), []).append(word)
    lemmas = list(grouped)
    winners: dict[str, str] = {}
    surfaces: dict[str, str] = {}
    for lemma in lemmas:
        best_lemma = lemma
        best_count = len(grouped[lemma])
        for other in lemmas:
            if other == lemma or not _similar(lemma, other):
                continue
            count = len(grouped[other])
            if count > best_count or (
                count == best_count and len(other) > len(best_lemma)
            ):
                best_lemma = other
                best_count = count
        winners[lemma] = best_lemma
        surface = grouped[best_lemma][0]
        for candidate in grouped[best_lemma]:
            if _lemma(candidate) == best_lemma and not candidate.endswith("s"):
                surface = candidate
                break
        surfaces[best_lemma] = surface
    return winners, surfaces


def _volume_words(volume: dict) -> list[str]:
    words: list[str] = []
    for part in volume.get("parts") or []:
        words.extend(_WORD.findall(str(part.get("title") or "")))
        for span in part.get("speech") or []:
            words.extend(_WORD.findall(str(span.get("text") or "")))
    return words


def _lemma(word: str) -> str:
    folded = word.casefold()
    if len(folded) > 4 and folded.endswith("s"):
        return folded[:-1]
    return folded


def _similar(left: str, right: str) -> bool:
    if min(len(left), len(right)) < 5:
        return False
    return _edit_distance(left, right) <= 2


def _edit_distance(left: str, right: str) -> int:
    if left == right:
        return 0
    if abs(len(left) - len(right)) > 2:
        return 99
    previous = list(range(len(right) + 1))
    for i, lch in enumerate(left, start=1):
        current = [i]
        for j, rch in enumerate(right, start=1):
            insert = current[j - 1] + 1
            delete = previous[j] + 1
            replace = previous[j - 1] + (lch != rch)
            current.append(min(insert, delete, replace))
        previous = current
    return previous[-1]
