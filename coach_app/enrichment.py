"""Consensus-seed load and occupancy rules for the live enrichment catalog."""

from __future__ import annotations

from typing import Any

FAMILY_SIDES = {
    "guard": "bottom",
    "leg-entanglement": "bottom",
    "turtle": "bottom",
    "pin": "top",
    "passing": "top",
    "back": "top",
    "standing": "neutral",
}
START_OCCUPANCY_BY_TYPE = {
    "pass": "top",
    "sweep": "bottom",
    "takedown": "neutral",
    "escape": "bottom",
}


def unify_seed(raw: dict[str, Any]) -> dict[str, Any]:
    """One position identity per shared id; submissions stay end-only."""
    positions: list[dict[str, Any]] = []
    index: dict[str, dict[str, Any]] = {}
    for item in raw.get("starting_positions") or []:
        position = dict(item)
        positions.append(position)
        index[position["id"]] = position
    submissions: list[dict[str, Any]] = []
    for item in raw.get("ending_positions_or_submissions") or []:
        if item.get("kind") == "submission":
            submissions.append(dict(item))
            continue
        if item["id"] in index:
            continue
        position = dict(item)
        position.setdefault("family", "other")
        positions.append(position)
        index[position["id"]] = position
    return {
        "move_types": [dict(item) for item in raw.get("move_types") or []],
        "positions": positions,
        "submissions": submissions,
        "paths": [dict(path) for path in raw.get("paths") or []],
    }


def names_from_cross_refs(item: dict[str, Any]) -> tuple[str, ...]:
    names = []
    for ref in item.get("cross_refs") or ():
        name = ref.get("name") if isinstance(ref, dict) else ref
        if name:
            names.append(str(name))
    return tuple(names)


def aliases_of(item: dict[str, Any]) -> tuple[str, ...]:
    return tuple(item.get("aliases") or ())


def family_of(positions: dict[str, dict[str, Any]], node_id: str) -> str:
    position = positions.get(node_id) or {}
    return str(position.get("family") or "other")


def start_occupancy(move_type: str, start_family: str) -> str:
    locked = START_OCCUPANCY_BY_TYPE.get(move_type)
    if locked:
        return locked
    return FAMILY_SIDES.get(start_family, "")


def end_occupancy(
    move_type: str,
    start_side: str,
    end_kind: str,
    end_family: str,
) -> str:
    if end_kind == "submission" or move_type == "submission":
        return ""
    if move_type in {"sweep", "pass", "back-take"}:
        return "top"
    if move_type == "takedown":
        if end_family == "guard":
            return "bottom"
        if end_family == "standing":
            return "neutral"
        return "top"
    if move_type == "escape":
        if end_family == "standing":
            return "neutral"
        return "bottom"
    if move_type == "transition":
        return start_side
    return start_side


def occupancy_for(
    move_type: str,
    start_family: str,
    end_kind: str,
    end_family: str,
) -> tuple[str, str]:
    start_side = start_occupancy(move_type, start_family)
    return start_side, end_occupancy(move_type, start_side, end_kind, end_family)
