"""Print the duplex advising packet. Drive HTTP, then packet pages and the store.

Headed browser is unavailable in this environment; urllib is the stand-in.
"""

from __future__ import annotations

import inspect
import re
from html.parser import HTMLParser
from urllib.parse import urlencode
from urllib.request import urlopen

from coach_app.app import CoachApp
from coach_app.print_packet import MARGIN_IN, PRINT_CSS, packet
from coach_app.ui_design import design_session
from coach_app.ui_sheet import current_sheet
from tests.test_build import TIGHT_WAIST_PARAGRAPH
from tests.test_ui_design import _design, _install_tight_waist, _named, _open_topic
from tests.test_ui_sheet import _pack, _sheet


class _Page(HTMLParser):
    def __init__(self, markup: str) -> None:
        super().__init__()
        self.markup = markup
        self.title = ""
        self.text_parts: list[str] = []
        self.links: list[tuple[str, str]] = []
        self.pages: list[dict[str, str]] = []
        self._in_title = False
        self._current_href = ""
        self._link_text: list[str] = []
        self._page_kind = ""
        self._page_attrs: dict[str, str] = {}
        self._page_parts: list[str] = []
        self.feed(markup)
        self._flush_page()

    def handle_starttag(self, tag, attrs) -> None:
        attrs = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "a":
            self._current_href = attrs.get("href", "")
            self._link_text = []
        classes = attrs.get("class", "")
        kind = attrs.get("data-kind", "")
        if tag == "article" and (
            kind in {"canvas", "class card"}
            or "print-canvas" in classes.split()
            or "class-card" in classes.split()
        ):
            self._flush_page()
            self._page_kind = kind or (
                "canvas" if "print-canvas" in classes.split() else "class card"
            )
            self._page_attrs = attrs
            self._page_parts = []

    def handle_endtag(self, tag) -> None:
        if tag == "title":
            self._in_title = False
        elif tag == "a":
            self.links.append((self._current_href, "".join(self._link_text).strip()))
            self._current_href = ""
            self._link_text = []
        elif tag == "article" and self._page_kind:
            self._flush_page()

    def handle_data(self, data) -> None:
        if self._in_title:
            self.title += data
        if self._current_href:
            self._link_text.append(data)
        if data.strip():
            self.text_parts.append(data.strip())
            if self._page_kind:
                self._page_parts.append(data.strip())

    def _flush_page(self) -> None:
        if self._page_kind:
            self.pages.append(
                {
                    "kind": self._page_kind,
                    "orientation": self._page_attrs.get("data-orientation", ""),
                    "class_index": self._page_attrs.get("data-class", ""),
                    "text": " ".join(self._page_parts),
                    "attrs": dict(self._page_attrs),
                }
            )
        self._page_kind = ""
        self._page_attrs = {}
        self._page_parts = []

    @property
    def text(self) -> str:
        return " ".join(self.text_parts)


def _get(url: str) -> str:
    with urlopen(url, timeout=5) as response:
        return response.read().decode("utf-8")


def _print_url(app: CoachApp, name: str = "Tight waist", ruleset: str = "gi") -> str:
    return app.url.rstrip("/") + "/print?" + urlencode({"name": name, "ruleset": ruleset})


def _print_href(name: str = "Tight waist", ruleset: str = "gi") -> str:
    return "/print?" + urlencode({"name": name, "ruleset": ruleset})


def test_print_action_uses_packet_pages_landscape_then_whole_portrait_cards(tmp_path):
    with CoachApp(tmp_path) as app:
        _pack(app)
        store = app.store
        session = design_session(store, "Tight waist", "gi")
        sheet = current_sheet(store, "Tight waist", "gi")
        pages = packet(session, sheet, store)
        markup = _get(_print_url(app))
        printed = _Page(markup)

    assert MARGIN_IN == 0.5
    assert pages[0].kind == "canvas"
    assert pages[0].orientation == "landscape"
    assert pages[0].margin_in == 0.5
    assert pages[0].keep_together
    assert [page.kind for page in pages[1:]] == ["class card"] * len(sheet.classes)
    assert [page.orientation for page in pages[1:]] == ["portrait"] * len(sheet.classes)
    assert all(page.keep_together for page in pages[1:])
    assert all(page.margin_in == 0.5 for page in pages)
    assert [item["kind"] for item in printed.pages] == [page.kind for page in pages]
    assert printed.pages[0]["orientation"] == "landscape"
    assert all(item["orientation"] == "portrait" for item in printed.pages[1:])
    assert "print-canvas" in markup
    canvas_at = markup.find('<article class="print-canvas"')
    card_at = markup.find('<article class="class-card"')
    assert 0 <= canvas_at < card_at
    css = (PRINT_CSS + markup).casefold()
    assert "0.5in" in css
    assert "landscape" in css
    assert "portrait" in css
    assert "avoid" in css
    assert str(MARGIN_IN) in markup or "0.5in" in markup
    assert PRINT_CSS in markup
    for index, page in enumerate(pages[1:]):
        block = printed.pages[index + 1]
        assert block["kind"] == "class card"
        assert block["class_index"] == str(page.class_index)
        for card in page.cards:
            assert card.target in block["text"]
            assert card.kind in block["text"]
        assert "unit paragraph" not in block["text"].casefold()
        assert "success watch" not in block["text"].casefold()
        assert TIGHT_WAIST_PARAGRAPH not in block["text"]


def test_print_html_hides_unit_paragraph_and_success_watch(tmp_path):
    with CoachApp(tmp_path) as app:
        _pack(app)
        markup = _get(_print_url(app))
        printed = _Page(markup)
        cards_html = " ".join(item["text"] for item in printed.pages if item["kind"] == "class card")

    assert TIGHT_WAIST_PARAGRAPH not in markup
    assert "success watch" not in markup.casefold()
    assert "unit-prompt" not in markup
    assert 'id="prompt-text"' not in markup
    assert "none / some / most / all" not in markup.casefold()
    assert "success watch" not in cards_html.casefold()
    assert "Playback" not in markup
    assert "PROTOTYPE" not in markup
    assert "Load sample" not in markup
    assert "window.print" in markup


def test_design_and_sheet_link_to_the_print_packet(tmp_path):
    href = _print_href()
    with CoachApp(tmp_path) as app:
        packed = _pack(app)
        design = _Page(_get(_design(app)))
        sheet = _Page(_get(_sheet(app, mode="read")))

    assert any(link[0] == href and "print" in link[1].casefold() for link in packed.links)
    assert any(link[0] == href and "print" in link[1].casefold() for link in design.links)
    assert any(link[0] == href and "print" in link[1].casefold() for link in sheet.links)


def test_print_screen_calls_packet_and_skips_named_pdf_libraries():
    import coach_app.app as app_mod
    import coach_app.ui_print as ui_print

    source = inspect.getsource(ui_print)
    folded = source.casefold()
    app_source = inspect.getsource(app_mod)

    assert "packet" in source
    assert "PRINT_CSS" in source
    assert "MARGIN_IN" in source
    assert "current_sheet" in source
    assert "design_session" in source
    assert "import coach_app.ui_print" in app_source
    assert app_source.count("import coach_app.ui_print") == 1
    assert any(screen.path == "/print" for screen in app_mod.SCREENS)
    assert "reportlab" not in folded
    assert "weasyprint" not in folded
    assert "pdfkit" not in folded
    assert "fpdf" not in folded
    assert "pypdf" not in folded
    assert "pikepdf" not in folded
    assert "playwright" not in folded
    assert "selenium" not in folded
    assert "prototypes" not in folded
    assert "ui_library" not in folded
    assert re.search(r"from\s+\S*pdf", folded) is None
