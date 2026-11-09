"""PROTOTYPE (issue 90) — NiceGUI topic studio.

Python UI framework that bundles Vue + Quasar. Layered / productivity chrome.
Proves whether a Design-like spatial split and a print-packet story survive.
In-memory sample only. Bind 127.0.0.1:8772. Does not write the curated store.
"""

from __future__ import annotations

import sys
from pathlib import Path

from nicegui import ui

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sample_store import counts, fresh, next_action  # noqa: E402

HOST = "127.0.0.1"
PORT = 8772
STATE = fresh()

PRINT_CSS = """
@page { margin: 0.5in; }
@page canvas { size: letter landscape; margin: 0.5in; }
@page class-card { size: letter portrait; margin: 0.5in; }
@media print {
  .proto-chrome { display: none !important; }
}
@media (prefers-reduced-motion: reduce) {
  * { animation: none !important; transition: none !important; }
}
"""


def refresh(world, next_box, map_box, sheet_box, feedback, state_pre) -> None:
    c = counts(STATE)
    nxt = next_action(STATE)
    world.clear()
    with world:
        for label, value in [
            ("Topic", STATE["topic_name"]),
            ("Ruleset", STATE["ruleset"]),
            ("Citations", c["citations_accepted"]),
            ("Uncategorized", c["uncategorized"]),
            ("System", "chosen" if c["system_chosen"] else "empty"),
            ("Map-ready", "yes" if c["map_ready"] else "no"),
            ("Sheet", c["sheet_mode"]),
            ("Missing video", c["missing_video"]),
        ]:
            ui.badge(f"{label}: {value}").props("outline")
    next_box.clear()
    with next_box:
        ui.label("NEXT ACTION").classes("text-xs tracking-widest text-orange-800")
        ui.label(nxt["label"]).classes("text-lg font-medium")
        ui.label(nxt["why"]).classes("text-sm text-stone-600")
    map_box.clear()
    with map_box:
        if STATE["map_marks"]:
            marks = "".join(
                f'<circle cx="{80 + i * 70}" cy="80" r="18" fill="#dbeafe" stroke="#1d4ed8" />'
                f'<text x="{80 + i * 70}" y="84" text-anchor="middle" font-size="10">{m["label"][:8]}</text>'
                for i, m in enumerate(STATE["map_marks"])
            )
            ui.html(
                f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 480 160" width="100%" height="160">'
                f'<rect width="480" height="160" fill="#fffcf6" stroke="#d6d3d1"/>{marks}</svg>',
                sanitize=False,
            )
        else:
            ui.label("Empty map. Convert stays blocked until a named move exists.").classes("text-stone-500")
    sheet_box.clear()
    with sheet_box:
        if STATE["draft_classes"]:
            for card in STATE["draft_classes"]:
                with ui.card().classes("w-full border-dashed"):
                    ui.label(f"{card['title']} · {card['kind']}").classes("font-medium")
                    ui.label(card["move"])
        else:
            ui.label("No Draft yet.")
    feedback.set_text(STATE["last_feedback"])
    state_pre.set_text(str(c))


def choose_system() -> None:
    STATE["system_chosen"] = True
    STATE["system_words"] = "Hip bump or kimura when the partner posts"
    STATE["last_feedback"] = "Coach determined the system. The studio map is now anchored."
    refresh(*PANELS)


def add_named_move() -> None:
    STATE["map_marks"].append(
        {"id": f"m{len(STATE['map_marks']) + 1}", "kind": "named_move", "label": "Hip bump sweep"}
    )
    STATE["last_feedback"] = "Named move on Design. Left-click would edit; right-click would delete."
    refresh(*PANELS)


def convert() -> None:
    named = [m for m in STATE["map_marks"] if m.get("kind") == "named_move"]
    if not named:
        STATE["last_feedback"] = "Convert blocked: Design needs a named move."
        refresh(*PANELS)
        return
    STATE["sheet_mode"] = "draft"
    STATE["draft_classes"] = [{"title": "Class 1", "kind": "technique", "move": "Hip bump sweep"}]
    STATE["last_feedback"] = "Coach converted. Packing stayed in the application. Sheet mode is Draft."
    refresh(*PANELS)


def place_first() -> None:
    if not STATE["uncategorized"]:
        STATE["last_feedback"] = "No uncategorized citations."
        refresh(*PANELS)
        return
    item = STATE["uncategorized"].pop(0)
    STATE["placed"].append({**item, "named_move": "Hip bump sweep"})
    STATE["last_feedback"] = (
        f"Coach placed a citation. {len(STATE['uncategorized'])} uncategorized remain."
    )
    refresh(*PANELS)


def reset() -> None:
    STATE.clear()
    STATE.update(fresh())
    refresh(*PANELS)


@ui.page("/")
def studio() -> None:
    ui.add_css(PRINT_CSS)
    ui.add_head_html(
        """
<style>
  .proto-chrome { border: 2px dotted #b91c1c; background: #fef2f2; padding: 0.55rem 0.75rem; margin-bottom: 0.6rem; }
  .coach-final { border: 2px dotted #15803d; background: #fffcf6; padding: 0.9rem 1rem; }
</style>
"""
    )
    with ui.column().classes("w-full p-3"):
        with ui.element("div").classes("proto-chrome"):
            ui.html(
                "<strong>PROTOTYPE</strong> — Issue 90 composition 2 of 3: NiceGUI (bundles Vue + Quasar). "
                "Topic studio. Layered / productivity. Sample data. Nothing is written to the curated store.<br>"
                "<strong>Color key:</strong> red dotted = prototype-only chrome. "
                "green dotted = proposed coach-final UI. Bind 127.0.0.1:8772. "
                '<a href="http://127.0.0.1:8771/">HTML-over-wire</a> · '
                '<a href="http://127.0.0.1:8773/">Flask + Alpine inbox</a>.',
                sanitize=False,
            )
        with ui.element("div").classes("coach-final"):
            ui.label("Topic studio").classes("text-2xl")
            ui.label(
                f"Coach-only. Open topic {STATE['topic_name']} ({STATE['ruleset']}). "
                "Design map at the center. Briefing, store, sheet, and print are docks."
            ).classes("text-stone-600")

            world = ui.row().classes("gap-2 flex-wrap q-mb-sm")
            next_box = ui.card().classes("w-full bg-orange-50")

            with ui.splitter(value=62).classes("w-full h-96") as splitter:
                with splitter.before:
                    ui.label("DESIGN MAP").classes("text-xs tracking-widest")
                    map_box = ui.column().classes("w-full")
                    with ui.row():
                        ui.button("Add named move", on_click=add_named_move)
                        ui.button("Convert to Draft", on_click=convert).props("color=primary")
                with splitter.after:
                    ui.label("DOCKS").classes("text-xs tracking-widest")
                    with ui.tabs() as tabs:
                        briefing = ui.tab("Briefing")
                        store = ui.tab("Store")
                        sheet = ui.tab("Sheet")
                        packet = ui.tab("Print")
                    with ui.tab_panels(tabs, value=briefing).classes("w-full"):
                        with ui.tab_panel(briefing):
                            ui.label("Advisor proposes system words. Coach determines.")
                            ui.button("Choose system", on_click=choose_system)
                            ui.label().bind_text_from(STATE, "system_words")
                        with ui.tab_panel(store):
                            ui.label("Uncategorized citations are not offered on a lesson.")
                            ui.button("Place one citation", on_click=place_first)
                        with ui.tab_panel(sheet):
                            sheet_box = ui.column()
                        with ui.tab_panel(packet):
                            ui.label(
                                "Print uses the browser. Landscape canvas + portrait class cards, 0.5 in. "
                                "Quasar layout chrome is hidden via @media print."
                            )
                            ui.button("Open print view", on_click=lambda: ui.navigate.to("/print"))

            feedback = ui.label().classes("q-mt-md")
            with ui.element("div").classes("proto-chrome q-mt-md"):
                ui.label("Prototype-only state dump and reset.")
                ui.button("Reset sample", on_click=reset)
                state_pre = ui.label().classes("font-mono text-xs")

            global PANELS
            PANELS = (world, next_box, map_box, sheet_box, feedback, state_pre)
            refresh(*PANELS)


@ui.page("/print")
def print_page() -> None:
    ui.add_css(PRINT_CSS)
    ui.label(f"Design canvas — {STATE['topic_name']} ({STATE['ruleset']})").classes("text-2xl")
    ui.label(f"System: {STATE['system_words'] or 'empty'}")
    for card in STATE["draft_classes"]:
        with ui.card():
            ui.label(f"{card['title']} · {card['kind']}")
            ui.label(card["move"])
    ui.label("Use the browser print dialog. This page is the packet story.")


PANELS: tuple = ()

if __name__ in {"__main__", "__mp_main__"}:
    print(f"PROTOTYPE nicegui-studio on http://{HOST}:{PORT} (sample data, no store writes)")
    ui.run(
        host=HOST,
        port=PORT,
        reload=False,
        show=False,
        title="PROTOTYPE topic studio",
        dark=False,
        on_air=False,
    )
