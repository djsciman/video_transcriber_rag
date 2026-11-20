"""Duplex print packet from the Design canvas and class-card sheet."""

from __future__ import annotations

from dataclasses import dataclass

from coach_app.edit import class_cards

MARGIN_IN = 0.5
PRINT_CSS = (
    "@page { margin: 0.5in; }\n"
    "@page canvas { size: letter landscape; margin: 0.5in; }\n"
    "@page class-card { size: letter portrait; margin: 0.5in; }\n"
    ".class-card { break-inside: avoid-page; page-break-inside: avoid; }\n"
)


@dataclass(frozen=True)
class PrintPage:
    kind: str
    orientation: str
    margin_in: float = MARGIN_IN
    keep_together: bool = True
    marks: tuple = ()
    cards: tuple = ()
    class_index: int | None = None
    purpose: str = ""


def packet(session, sheet, store) -> tuple[PrintPage, ...]:
    rows = class_cards(store, sheet)
    canvas = PrintPage(
        kind="canvas",
        orientation="landscape",
        marks=session.marks,
    )
    class_pages = tuple(
        PrintPage(
            kind="class card",
            orientation="portrait",
            cards=row,
            class_index=index,
            purpose=sheet.classes[index].class_record.purpose,
        )
        for index, row in enumerate(rows)
    )
    return (canvas,) + class_pages
