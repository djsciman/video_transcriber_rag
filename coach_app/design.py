"""Design a unit as an unordered mental map. Catalog organize stays on the finder."""

from __future__ import annotations

from dataclasses import dataclass, replace

from coach_app.placement import citations_for_design_mark

ADD_WALK = ("family", "position", "occupancy", "type", "end", "named move")

FAMILY_OCCUPANCIES = {
    "standing": ("neutral",),
    "guard": ("bottom", "top"),
    "leg-entanglement": ("bottom", "top"),
    "passing": ("top", "bottom"),
    "pin": ("bottom", "top"),
    "turtle": ("bottom", "top"),
    "back": ("bottom", "top"),
    "other": ("bottom", "top", "neutral"),
}

CONTROL_FAMILIES = ("pin", "back", "turtle", "passing")
MOVE_TYPE_ORDER = (
    "takedown",
    "sweep",
    "pass",
    "escape",
    "submission",
    "transition",
    "back-take",
)
MOVE_TYPE_SPEC = {
    "takedown": {"sides": ("neutral",)},
    "sweep": {"sides": ("bottom",)},
    "pass": {"sides": ("top",)},
    "escape": {"sides": ("bottom",), "families": CONTROL_FAMILIES},
    "submission": {"sides": ("top", "bottom", "neutral")},
    "transition": {
        "sides": ("top", "bottom", "neutral"),
        "same_family": True,
        "by_side_families": {
            "bottom": ("guard", "leg-entanglement", "turtle"),
            "top": ("pin", "passing", "back"),
            "neutral": ("standing",),
        },
    },
    "back-take": {"sides": ("top", "bottom")},
}

TIGHT_WAIST_HOME = ("Knee lever", "Tight waist")
TIGHT_WAIST_TRILEMMA = (
    "Far-leg come-up",
    "Roll-through sweep",
    "Back take from tight waist",
)
TIGHT_WAIST_SYSTEM = "Tight waist trilemma"


@dataclass(frozen=True)
class DesignMark:
    kind: str
    target: str
    id: str = ""
    start_id: str = ""
    occupancy: str = ""
    type_of_move: str = ""
    end_id: str = ""


@dataclass(frozen=True)
class AddWalk:
    family: str = ""
    position_id: str = ""
    occupancy: str = ""
    type_of_move: str = ""
    end_id: str = ""


@dataclass(frozen=True)
class DesignSession:
    topic_name: str = ""
    topic_ruleset: str = ""
    marks: tuple[DesignMark, ...] = ()
    walk: AddWalk = AddWalk()
    chosen_citations: tuple[tuple[str, str], ...] = ()
    selected_id: str = ""
    next_id: int = 1


def open_design(*, topic_name: str = "", topic_ruleset: str = "") -> DesignSession:
    return DesignSession(topic_name=topic_name, topic_ruleset=topic_ruleset)


def walk_step(session: DesignSession) -> str:
    walk = session.walk
    if not walk.family:
        return "family"
    if not walk.position_id:
        return "position"
    if not walk.occupancy:
        return "occupancy"
    if not walk.type_of_move:
        return "type"
    if walk.type_of_move != "submission" and not walk.end_id:
        return "end"
    return "named move"


def walk_options(store, session: DesignSession):
    step = walk_step(session)
    walk = session.walk
    if step == "family":
        return tuple(
            sorted(
                {
                    node.family
                    for node in store.enrichment_nodes()
                    if node.kind == "position" and node.family
                }
            )
        )
    if step == "position":
        return tuple(
            node.id
            for node in store.enrichment_nodes()
            if node.kind == "position" and node.family == walk.family
        )
    if step == "occupancy":
        return occupancies_at(store, walk.position_id)
    if step == "type":
        return types_at(store, walk.position_id, walk.occupancy)
    if step == "end":
        return ends_at(store, walk.position_id, walk.occupancy, walk.type_of_move)
    return named_moves_at(
        store,
        walk.position_id,
        walk.occupancy,
        walk.type_of_move,
        walk.end_id,
        ruleset=session.topic_ruleset,
    )


def pick(store, session: DesignSession, value) -> DesignSession:
    chosen = _option_id(value)
    if not chosen:
        return session
    step = walk_step(session)
    allowed = walk_options(store, session)
    resolved = _match_option(store, step, chosen, allowed)
    if resolved is None:
        return session
    if step == "family":
        return replace(session, walk=replace(session.walk, family=resolved))
    if step == "position":
        return replace(session, walk=replace(session.walk, position_id=resolved))
    if step == "occupancy":
        marked = _place_occupancy(session, resolved)
        return replace(
            marked,
            walk=replace(marked.walk, occupancy=resolved),
            marks=_prune_incompatible(store, marked.marks, marked.walk),
        )
    if step == "type":
        marked = _place_type(session, resolved)
        return replace(marked, walk=replace(marked.walk, type_of_move=resolved))
    if step == "end":
        return replace(session, walk=replace(session.walk, end_id=resolved))
    return add_named_move(store, session, resolved)


def occupancies_at(store, position_id) -> tuple[str, ...]:
    position = _catalog_node(store, position_id, "position")
    family = position.family if position else "other"
    return FAMILY_OCCUPANCIES.get(family, ("bottom", "top"))


def types_at(store, position_id, occupancy) -> tuple[str, ...]:
    position = _catalog_node(store, position_id, "position")
    family = position.family if position else ""
    allowed = tuple(
        move_type
        for move_type in MOVE_TYPE_ORDER
        if move_allowed(move_type, occupancy, family)
    )
    catalog = tuple(
        node.id for node in store.enrichment_nodes() if node.kind == "type of move"
    )
    if not catalog:
        return allowed
    catalog_ids = set(catalog)
    catalog_names = {
        node.name.casefold(): node.id
        for node in store.enrichment_nodes()
        if node.kind == "type of move"
    }
    return tuple(
        move_type
        for move_type in allowed
        if move_type in catalog_ids
        or move_type.replace("-", " ") in catalog_names
        or move_type in catalog_names
    )


def ends_at(store, position_id, occupancy, type_of_move) -> tuple[str, ...]:
    start = _catalog_node(store, position_id, "position")
    start_family = start.family if start else ""
    seen: list[str] = []
    for move in _named_moves(
        store,
        start_id=position_id,
        occupancy=occupancy,
        type_of_move=type_of_move,
    ):
        end = store.enrichment_node(move.end_id)
        if end is None:
            continue
        if type_of_move == "submission" or end.kind == "submission":
            continue
        if type_of_move == "transition" and end.family != start_family:
            continue
        if move.end_id not in seen:
            seen.append(move.end_id)
    return tuple(seen)


def named_moves_at(
    store,
    start_id,
    occupancy="",
    type_of_move="",
    end_id="",
    *,
    ruleset: str = "",
) -> tuple[str, ...]:
    return tuple(
        node.id
        for node in _named_moves(
            store,
            start_id=start_id,
            occupancy=occupancy,
            type_of_move=type_of_move,
            end_id=end_id,
            ruleset=ruleset,
        )
    )


def move_allowed(move_type: str, occupancy: str, family: str) -> bool:
    spec = MOVE_TYPE_SPEC.get(move_type)
    if spec is None:
        return False
    if occupancy and occupancy not in spec["sides"]:
        return False
    families = spec.get("families")
    if families and family not in families:
        return False
    by_side = spec.get("by_side_families")
    if by_side and occupancy:
        if family not in by_side.get(occupancy, ()):
            return False
    return True


def add_named_move(store, session: DesignSession, named_move_id) -> DesignSession:
    node = _catalog_node(store, named_move_id, "named move")
    if node is None:
        return session
    occupancy = node.start_occupancy or session.walk.occupancy
    start_id = node.start_id or session.walk.position_id
    walk = session.walk
    if not walk.family:
        start = _catalog_node(store, start_id, "position")
        walk = replace(
            walk,
            family=start.family if start else walk.family,
            position_id=start_id,
            occupancy=occupancy,
            type_of_move=node.type_of_move,
            end_id=node.end_id,
        )
    marks = tuple(mark for mark in session.marks if not _is_pending_type(mark))
    if occupancy and not any(mark.kind == "occupancy" for mark in marks):
        marks, next_id = _append_mark(
            replace(session, marks=marks),
            DesignMark(
                kind="occupancy",
                target=occupancy,
                start_id=start_id,
                occupancy=occupancy,
            ),
        )
        session = replace(session, marks=marks, next_id=next_id)
        marks = session.marks
    if any(mark.kind == "named move" and mark.target == node.id for mark in marks):
        return replace(session, marks=marks, walk=AddWalk())
    marks, next_id = _append_mark(
        replace(session, marks=marks),
        DesignMark(
            kind="named move",
            target=node.id,
            start_id=start_id,
            occupancy=occupancy,
            type_of_move=node.type_of_move,
            end_id=node.end_id,
        ),
    )
    return replace(session, marks=marks, next_id=next_id, walk=AddWalk())


def add_system(store, session: DesignSession, system_id) -> DesignSession:
    node = _catalog_node(store, system_id, "system")
    if node is None or len(node.aliases) < 2:
        return session
    updated = session
    for member_id in node.aliases:
        updated = add_named_move(store, updated, member_id)
    if any(mark.kind == "system" and mark.target == node.id for mark in updated.marks):
        return updated
    marks, next_id = _append_mark(
        updated,
        DesignMark(kind="system", target=node.id),
    )
    return replace(updated, marks=marks, next_id=next_id)


def sample_tight_waist(store) -> DesignSession:
    session = open_design(topic_name="Tight waist", topic_ruleset="gi")
    by_name = {
        node.name: node
        for node in store.enrichment_nodes()
        if node.kind == "named move"
    }
    for name in TIGHT_WAIST_HOME + TIGHT_WAIST_TRILEMMA:
        node = by_name.get(name)
        if node is not None:
            session = add_named_move(store, session, node.id)
    system = next(
        (
            node
            for node in store.enrichment_nodes()
            if node.kind == "system" and node.name == TIGHT_WAIST_SYSTEM
        ),
        None,
    )
    if system is not None:
        session = add_system(store, session, system.id)
    return session


def edit_mark(session: DesignSession, mark_id) -> DesignSession:
    mark = _mark(session, mark_id)
    if mark is None:
        return session
    return replace(session, selected_id=mark.id)


def delete_mark(session: DesignSession, mark_id) -> DesignSession:
    mark = _mark(session, mark_id)
    if mark is None:
        return session
    remaining = tuple(item for item in session.marks if item.id != mark.id)
    selected = "" if session.selected_id == mark.id else session.selected_id
    if mark.kind == "named move":
        remaining = _drop_systems_missing_members(remaining)
        chosen = tuple(
            pair for pair in session.chosen_citations if pair[0] != mark.target
        )
        return replace(
            session, marks=remaining, selected_id=selected, chosen_citations=chosen
        )
    return replace(session, marks=remaining, selected_id=selected)


def citations_on_mark(store, session: DesignSession, mark_id=None):
    target = mark_id if mark_id is not None else session.selected_id
    mark = _mark(session, target)
    if mark is None or mark.kind != "named move":
        return ()
    return citations_for_design_mark(store, mark.target)


def choose_citation(store, session: DesignSession, mark_id, citation_id) -> DesignSession:
    offered = {item.id for item in citations_on_mark(store, session, mark_id)}
    if citation_id not in offered:
        return session
    mark = _mark(session, mark_id)
    if mark is None:
        return session
    pair = (mark.target, citation_id)
    if pair in session.chosen_citations:
        chosen = tuple(item for item in session.chosen_citations if item != pair)
    else:
        chosen = session.chosen_citations + (pair,)
    return replace(session, chosen_citations=chosen)


def _named_moves(
    store,
    *,
    start_id,
    occupancy="",
    type_of_move="",
    end_id="",
    ruleset="",
):
    start = _catalog_node(store, start_id, "position")
    start_key = start.id if start else str(start_id or "")
    wanted_type = _resolve_type(store, type_of_move) if type_of_move else ""
    wanted_end = ""
    if end_id:
        end = store.enrichment_node(end_id) or _catalog_node(store, end_id, "position")
        wanted_end = end.id if end else str(end_id)
    for node in store.enrichment_nodes():
        if node.kind != "named move":
            continue
        if node.start_id != start_key:
            continue
        if occupancy and node.start_occupancy != occupancy:
            continue
        if wanted_type and node.type_of_move != wanted_type:
            continue
        if wanted_end and node.end_id != wanted_end:
            continue
        if ruleset and node.ruleset and node.ruleset not in {ruleset, "both"}:
            continue
        yield node


def _place_occupancy(session: DesignSession, occupancy: str) -> DesignSession:
    marks = tuple(mark for mark in session.marks if mark.kind != "occupancy")
    session = replace(session, marks=marks)
    marks, next_id = _append_mark(
        session,
        DesignMark(
            kind="occupancy",
            target=occupancy,
            start_id=session.walk.position_id,
            occupancy=occupancy,
        ),
    )
    return replace(session, marks=marks, next_id=next_id)


def _place_type(session: DesignSession, type_of_move: str) -> DesignSession:
    marks = tuple(mark for mark in session.marks if not _is_pending_type(mark))
    session = replace(session, marks=marks)
    marks, next_id = _append_mark(
        session,
        DesignMark(
            kind="type",
            target=type_of_move,
            start_id=session.walk.position_id,
            occupancy=session.walk.occupancy,
            type_of_move=type_of_move,
        ),
    )
    return replace(session, marks=marks, next_id=next_id)


def _prune_incompatible(store, marks, walk: AddWalk):
    kept = []
    for mark in marks:
        if mark.kind == "named move":
            node = store.enrichment_node(mark.target)
            if node is None:
                continue
            if walk.position_id and node.start_id != walk.position_id:
                continue
            if walk.occupancy and node.start_occupancy != walk.occupancy:
                continue
        kept.append(mark)
    return _drop_systems_missing_members(tuple(kept))


def _drop_systems_missing_members(marks: tuple[DesignMark, ...]) -> tuple[DesignMark, ...]:
    on_map = {mark.target for mark in marks if mark.kind == "named move"}
    kept = []
    for mark in marks:
        if mark.kind != "system":
            kept.append(mark)
            continue
        if len(on_map) >= 2:
            kept.append(mark)
    return tuple(kept)


def _append_mark(session: DesignSession, mark: DesignMark):
    stored = mark if mark.id else replace(mark, id=str(session.next_id))
    return session.marks + (stored,), session.next_id + 1


def _is_pending_type(mark: DesignMark) -> bool:
    return mark.kind == "type"


def _mark(session: DesignSession, mark_id) -> DesignMark | None:
    wanted = str(mark_id or "")
    for mark in session.marks:
        if mark.id == wanted:
            return mark
    return None


def _option_id(value) -> str:
    if value is None:
        return ""
    if hasattr(value, "id"):
        return str(value.id)
    return str(value).strip()


def _match_option(store, step: str, chosen: str, allowed) -> str | None:
    allowed = tuple(allowed)
    if chosen in allowed:
        return chosen
    folded = chosen.casefold()
    for option in allowed:
        if str(option).casefold() == folded:
            return option
    if step in {"position", "end", "named move"}:
        node = store.enrichment_node(chosen)
        if node is not None and node.id in allowed:
            return node.id
        for node in store.enrichment_nodes():
            if node.name.casefold() == folded and node.id in allowed:
                return node.id
    if step == "type":
        resolved = _resolve_type(store, chosen)
        if resolved in allowed:
            return resolved
    return None


def _resolve_type(store, value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    node = store.enrichment_node(raw)
    if node is not None and node.kind == "type of move":
        return node.id
    folded = raw.casefold().replace(" ", "-")
    for node in store.enrichment_nodes():
        if node.kind != "type of move":
            continue
        if node.id.casefold() == folded or node.name.casefold().replace(" ", "-") == folded:
            return node.id
    return folded


def _catalog_node(store, value, kind: str):
    if not value:
        return None
    node = store.enrichment_node(str(value))
    if node is not None and node.kind == kind:
        return node
    folded = str(value).casefold()
    for item in store.enrichment_nodes():
        if item.kind == kind and (
            item.id.casefold() == folded or item.name.casefold() == folded
        ):
            return item
    return None
