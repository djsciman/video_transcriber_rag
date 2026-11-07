"""Duplex print packet from the current Design canvas and class-card sheet."""

from __future__ import annotations

import inspect

from coach_app.build import BuildAdvisor, convert
from coach_app.design import add_named_move, sample_tight_waist
from coach_app.edit import add_lesson, class_cards, open_sheet, set_purpose
from coach_app.print_packet import MARGIN_IN, PRINT_CSS, packet
from coach_app.store import Lesson
from tests.test_design import _named, _tight_waist_catalog


def _sheet(store, draft, mode="read"):
    return open_sheet(store, draft, mode)


def test_packet_is_landscape_canvas_then_whole_portrait_class_cards():
    store = _tight_waist_catalog()
    session = sample_tight_waist(store)
    draft = convert(store, session, BuildAdvisor()).draft
    sheet = _sheet(store, draft)
    pages = packet(session, sheet, store)
    cards = class_cards(store, sheet)

    assert MARGIN_IN == 0.5
    assert pages[0].kind == "canvas"
    assert pages[0].orientation == "landscape"
    assert pages[0].margin_in == 0.5
    assert pages[0].marks == session.marks
    assert pages[0].cards == ()
    assert len(pages) == 1 + len(sheet.classes)
    assert [page.kind for page in pages[1:]] == ["class card"] * len(sheet.classes)
    assert [page.orientation for page in pages[1:]] == ["portrait"] * len(sheet.classes)
    assert [page.margin_in for page in pages[1:]] == [0.5] * len(sheet.classes)
    assert [page.class_index for page in pages[1:]] == list(range(len(sheet.classes)))
    assert [page.cards for page in pages[1:]] == list(cards)
    assert all(page.keep_together for page in pages)
    assert all(len(page.cards) == len(sheet.classes[page.class_index].lessons) for page in pages[1:])
    css = PRINT_CSS.casefold()
    assert "0.5in" in css
    assert "landscape" in css
    assert "portrait" in css
    assert "avoid" in css


def test_packet_uses_the_current_canvas_and_class_card_sheet():
    store = _tight_waist_catalog()
    session = sample_tight_waist(store)
    draft = convert(store, session, BuildAdvisor()).draft
    sheet = _sheet(store, draft, "edit")
    knee = _named(store, "Knee lever")
    old_school = _named(store, "Old school sweep")

    written = set_purpose(store, sheet, 0, "Win the underhook.")
    opened = add_lesson(
        store,
        written,
        Lesson(kind="sparring", target=knee.id, scenario="Half guard bottom."),
    )
    current_session = add_named_move(store, session, old_school.id)
    pages = packet(current_session, opened, store)
    cards = class_cards(store, opened)

    assert pages[0].marks == current_session.marks
    assert pages[0].marks != session.marks
    assert old_school.id in {
        mark.target for mark in pages[0].marks if mark.kind == "named move"
    }
    assert len(pages) == 1 + len(opened.classes)
    assert len(opened.classes) == len(draft.classes) + 1
    assert pages[1].purpose == "Win the underhook."
    assert pages[1].cards == cards[0]
    assert pages[-1].cards == cards[-1]
    assert pages[-1].cards[0].kind == "sparring"
    assert pages[-1].cards[0].what_to_run == ("Half guard bottom.",)


def test_print_plan_does_not_open_a_browser_or_use_prototype_html():
    source = inspect.getsource(inspect.getmodule(packet))
    folded = source.casefold()

    assert list(inspect.signature(packet).parameters) == [
        "session",
        "sheet",
        "store",
    ]
    assert "browser" not in folded
    assert "webbrowser" not in folded
    assert "playwright" not in folded
    assert "prototypes" not in folded
    assert "<html" not in folded
    assert "openai" not in folded
    assert "anthropic" not in folded
    assert "sqlite" not in folded
