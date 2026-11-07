"""Open a topic and welcome other-ruleset instructionals through the store."""

from __future__ import annotations

from dataclasses import dataclass, replace

from coach_app.store import (
    Citation,
    CuratedStore,
    OtherRulesetChoice,
    Showing,
    Topic,
)

OTHER_RULESET_CAVEAT = (
    "What may transfer, and what depends on tools the topic's ruleset does not share."
)


@dataclass(frozen=True)
class OtherRulesetShowing(Showing):
    caveat: str = OTHER_RULESET_CAVEAT


@dataclass(frozen=True)
class WelcomedOtherRuleset(OtherRulesetChoice):
    caveat: str = OTHER_RULESET_CAVEAT


def open_topic(store: CuratedStore, name: str, ruleset: str) -> Topic | None:
    kept = name.rstrip(" ")
    if not kept or ruleset not in {"gi", "no-gi"}:
        return None
    existing = store.topic(kept, ruleset)
    if existing is not None:
        return existing
    return store.put_topic(Topic(name=kept, ruleset=ruleset))


def remove_topic(store: CuratedStore, name: str, ruleset: str) -> None:
    kept = name.rstrip(" ")
    store._topics.pop((kept, ruleset), None)
    for key in list(store._other_ruleset):
        if key[0] == kept and key[1] == ruleset:
            store._other_ruleset.pop(key, None)
    for key in list(store._set_asides):
        if key[0] == kept and key[1] == ruleset:
            store._set_asides.pop(key, None)


def same_ruleset_citations(store: CuratedStore, topic: Topic) -> tuple[Citation, ...]:
    selected = []
    for citation in store.citations():
        if not citation.instructional:
            continue
        instructional = store.instructional(citation.instructional)
        if instructional and instructional.ruleset == topic.ruleset:
            selected.append(citation)
    return tuple(selected)


def mark_other_ruleset_showing(
    store: CuratedStore,
    citation: Citation,
    showing: Showing,
    caveat: str = OTHER_RULESET_CAVEAT,
) -> OtherRulesetShowing:
    marked = OtherRulesetShowing(
        timestamp=showing.timestamp,
        playback_link=showing.playback_link,
        caveat=caveat,
    )
    showings = tuple(
        marked if _same_showing(item, showing) else item
        for item in citation.showings
    )
    store.put_citation(replace(citation, showings=showings))
    return marked


def other_ruleset_instructionals(
    store: CuratedStore, topic: Topic
) -> tuple:
    other = "no-gi" if topic.ruleset == "gi" else "gi"
    cited = {
        citation.instructional
        for citation in store.citations()
        if citation.instructional
    }
    return tuple(
        instructional
        for instructional in store.instructionals()
        if instructional.ruleset == other and instructional.name in cited
    )


def welcome_other_ruleset(
    store: CuratedStore,
    topic: Topic,
    instructional,
    yes: bool,
) -> OtherRulesetChoice:
    name = instructional if isinstance(instructional, str) else instructional.name
    if yes:
        choice: OtherRulesetChoice = WelcomedOtherRuleset(
            topic_name=topic.name,
            topic_ruleset=topic.ruleset,
            instructional=name,
            yes=True,
            caveat=OTHER_RULESET_CAVEAT,
        )
    else:
        choice = OtherRulesetChoice(
            topic_name=topic.name,
            topic_ruleset=topic.ruleset,
            instructional=name,
            yes=False,
        )
    return store.put_other_ruleset_choice(choice)


def _same_showing(left: Showing, right: Showing) -> bool:
    return left.timestamp == right.timestamp and left.playback_link == right.playback_link
