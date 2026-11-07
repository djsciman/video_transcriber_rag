"""Return a briefing memo from the curated store. Stand in the advisor vendor."""

from __future__ import annotations

from dataclasses import dataclass

from coach_app.store import Citation, CuratedStore, Topic
from coach_app.topics import open_topic, other_ruleset_instructionals, same_ruleset_citations


@dataclass(frozen=True)
class Caveat:
    may_transfer: tuple[str, ...]
    depends_on_unshared_tools: tuple[str, ...]


@dataclass(frozen=True)
class DisagreementSide:
    citation: Citation
    partner_job: str


@dataclass(frozen=True)
class BriefingMemo:
    topic_name: str
    topic_ruleset: str
    same_ruleset_citations: tuple[Citation, ...]
    other_ruleset_citations: tuple[Citation, ...] = ()
    other_ruleset_question: str = ""
    caveat: Caveat | None = None
    disagreement: tuple[DisagreementSide, ...] = ()


class BriefingAdvisor:
    """Stand-in that reads movement and cleaned statement. Does not name a vendor."""

    def select(self, topic: Topic, citations: tuple[Citation, ...]) -> tuple[Citation, ...]:
        needle = topic.name.casefold()
        if not needle:
            return ()
        selected = []
        for citation in citations:
            haystack = " ".join(
                (
                    citation.movement or "",
                    citation.cleaned_statement or "",
                    citation.chapter or "",
                    *citation.step_bullets,
                )
            ).casefold()
            if needle in haystack:
                selected.append(citation)
        return tuple(selected)

    def why_paths_differ(self, topic: Topic) -> str:
        other = "no-gi" if topic.ruleset == "gi" else "gi"
        return f"Why do these {topic.ruleset} and {other} paths differ?"

    def caveat(self, topic: Topic, other_citations: tuple[Citation, ...]) -> Caveat:
        other = "no-gi" if topic.ruleset == "gi" else "gi"
        may_transfer = tuple(
            citation.movement for citation in other_citations if citation.movement
        )
        if not may_transfer:
            may_transfer = ("Movement details that do not depend on the other ruleset's tools.",)
        return Caveat(
            may_transfer=may_transfer,
            depends_on_unshared_tools=(
                f"Tools the {topic.ruleset} topic does not share with {other}.",
            ),
        )

    def disagreeing_sides(
        self, topic: Topic, citations: tuple[Citation, ...]
    ) -> tuple[Citation, ...]:
        return ()


def brief_topic(
    store: CuratedStore,
    topic_name: str,
    topic_ruleset: str,
    advisor,
) -> BriefingMemo | None:
    topic = open_topic(store, topic_name, topic_ruleset)
    if topic is None:
        return None
    same = advisor.select(topic, same_ruleset_citations(store, topic))
    other = advisor.select(topic, _welcomed_other_ruleset_citations(store, topic))
    disagreement = _disagreement_sides(advisor.disagreeing_sides(topic, same))
    if other:
        return BriefingMemo(
            topic_name=topic.name,
            topic_ruleset=topic.ruleset,
            same_ruleset_citations=same,
            other_ruleset_citations=other,
            other_ruleset_question=advisor.why_paths_differ(topic),
            caveat=advisor.caveat(topic, other),
            disagreement=disagreement,
        )
    return BriefingMemo(
        topic_name=topic.name,
        topic_ruleset=topic.ruleset,
        same_ruleset_citations=same,
        disagreement=disagreement,
    )


def _welcomed_other_ruleset_citations(
    store: CuratedStore, topic: Topic
) -> tuple[Citation, ...]:
    welcomed = {
        instructional.name
        for instructional in other_ruleset_instructionals(store, topic)
        if _is_welcomed(store, topic, instructional.name)
    }
    if not welcomed:
        return ()
    return tuple(
        citation
        for citation in store.citations()
        if citation.instructional in welcomed
    )


def _is_welcomed(store: CuratedStore, topic: Topic, instructional: str) -> bool:
    choice = store.other_ruleset_choice(topic.name, topic.ruleset, instructional)
    return bool(choice and choice.yes)


def _disagreement_sides(citations: tuple[Citation, ...]) -> tuple[DisagreementSide, ...]:
    if len(citations) < 2:
        return ()
    sides = []
    for index, citation in enumerate(citations):
        others = citations[:index] + citations[index + 1 :]
        partner_job = "; ".join(
            _partner_job_text(other) for other in others if _partner_job_text(other)
        )
        sides.append(DisagreementSide(citation=citation, partner_job=partner_job))
    return tuple(sides)


def _partner_job_text(citation: Citation) -> str:
    if citation.step_bullets:
        return "; ".join(citation.step_bullets)
    return citation.cleaned_statement or citation.movement or ""
