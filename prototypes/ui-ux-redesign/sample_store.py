"""In-memory sample curated-store stand-in for throwaway UI prototypes.

Does not import production coach_app.store. Does not write files.
Copy this module's state; never persist to the live curated-store folder.
"""

from copy import deepcopy

SAMPLE = {
    "topic_name": "Hip bump sweep",
    "ruleset": "gi",
    "system_words": "",
    "system_chosen": False,
    "sheet_mode": None,
    "citations_accepted": 9,
    "missing_video": 1,
    "map_marks": [],
    "draft_classes": [],
    "last_feedback": "Open. Sample data only. Nothing is saved to disk.",
    "proposals": [
        {
            "id": "p1",
            "kind": "cleaned_statement",
            "text": "Sit up into the hip bump, post the far hand, and sweep when the partner posts.",
            "volume": "Volume 1",
            "status": "awaiting",
        }
    ],
    "uncategorized": [
        {
            "id": "c1",
            "text": "Frame the near hip before the sit-up so the partner cannot flatten you.",
            "instructor": "Sample instructor",
            "playback_missing": False,
        },
        {
            "id": "c2",
            "text": "When the partner bases the far hand, switch to the kimura from the hip bump.",
            "instructor": "Sample instructor",
            "playback_missing": True,
        },
        {
            "id": "c3",
            "text": "Keep the hook as you bump so the partner cannot step over.",
            "instructor": "Sample instructor",
            "playback_missing": False,
        },
    ],
    "placed": [],
}


def fresh():
    return deepcopy(SAMPLE)


def counts(state):
    awaiting = sum(1 for p in state["proposals"] if p["status"] == "awaiting")
    uncategorized = len(state["uncategorized"])
    map_ready = bool(state["system_chosen"] and state["map_marks"])
    named_moves = [m for m in state["map_marks"] if m.get("kind") == "named_move"]
    return {
        "awaiting": awaiting,
        "uncategorized": uncategorized,
        "placed": len(state["placed"]),
        "citations_accepted": state["citations_accepted"],
        "missing_video": state["missing_video"],
        "system_chosen": state["system_chosen"],
        "map_ready": map_ready,
        "named_move_count": len(named_moves),
        "sheet_mode": state["sheet_mode"] or "none",
        "can_convert": bool(named_moves),
    }


def next_action(state):
    c = counts(state)
    if c["awaiting"]:
        return {
            "id": "accept",
            "label": "Review the advisor proposal",
            "why": "A cleaned statement is waiting. The advisor proposes; the coach determines.",
        }
    if c["uncategorized"]:
        return {
            "id": "place",
            "label": "Place uncategorized citations",
            "why": "Uncategorized citations are not offered on a lesson.",
        }
    if not state["system_chosen"]:
        return {
            "id": "briefing",
            "label": "Choose the system on the briefing",
            "why": "Design stays unanchored until the coach determines the system.",
        }
    if not c["named_move_count"]:
        return {
            "id": "design",
            "label": "Add a named move on Design",
            "why": "Convert needs named moves before a Draft can pack.",
        }
    if state["sheet_mode"] is None:
        return {
            "id": "convert",
            "label": "Convert Design to Draft",
            "why": "The map has named moves. Convert is the next commit.",
        }
    return {
        "id": "print",
        "label": "Print the packet",
        "why": "Draft exists. Print landscape canvas and portrait class cards.",
    }
