"""Record the topic system as coach words and set earlier systems aside."""

from __future__ import annotations

from dataclasses import dataclass, replace

from coach_app.store import CuratedStore, SetAside, Topic


@dataclass(frozen=True)
class SystemConflict:
    earlier_topic_name: str
    system: str
    side: object


class SystemAdvisor:
    """Stand-in that flags an earlier system a student cannot follow with a side."""

    def cannot_follow_together(self, earlier_system: str, side) -> bool:
        return True


def choose_system(store: CuratedStore, topic: Topic, words: str) -> Topic:
    current = store.topic(topic.name, topic.ruleset) or topic
    return store.put_topic(replace(current, system=words))


def set_aside(store: CuratedStore, this_topic: Topic, earlier_topic: Topic) -> SetAside:
    return store.put_set_aside(
        SetAside(
            topic_name=this_topic.name,
            topic_ruleset=this_topic.ruleset,
            earlier_topic_name=earlier_topic.name,
            earlier_topic_ruleset=earlier_topic.ruleset,
        )
    )


def end_set_aside(store: CuratedStore, this_topic: Topic, earlier_topic: Topic) -> None:
    store._set_asides.pop(
        (
            this_topic.name,
            this_topic.ruleset,
            earlier_topic.name,
            earlier_topic.ruleset,
        ),
        None,
    )


def system_conflicts(store: CuratedStore, topic: Topic, sides, advisor):
    hidden = {
        (record.earlier_topic_name, record.earlier_topic_ruleset)
        for record in store.set_asides(topic.name, topic.ruleset)
    }
    notes = []
    for earlier in store.topics():
        if earlier.ruleset != topic.ruleset or earlier.name == topic.name:
            continue
        live = store.topic(earlier.name, earlier.ruleset)
        if live is None or not live.system:
            continue
        if (live.name, live.ruleset) in hidden:
            continue
        for side in sides:
            if advisor.cannot_follow_together(live.system, side):
                notes.append(
                    SystemConflict(
                        earlier_topic_name=live.name,
                        system=live.system,
                        side=side,
                    )
                )
    return tuple(notes)
