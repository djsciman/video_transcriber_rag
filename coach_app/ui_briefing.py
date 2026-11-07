"""Briefing memo for an open topic, before the coach determines the system."""

from __future__ import annotations

import html
from urllib.parse import urlencode

from coach_app.app import Screen, add_screen, render_shell
from coach_app.briefing import BriefingAdvisor, BriefingMemo, brief_topic
from coach_app.store import Citation, CuratedStore, Showing

_STYLE = """
.memo-top {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
  border-bottom: 1px solid var(--line);
  padding-bottom: 1rem;
  margin-bottom: 1rem;
}
.memo-top h2 {
  font-family: var(--serif);
  font-size: 1.45rem;
  text-transform: none;
  letter-spacing: 0;
  color: var(--ink);
  margin: 0;
}
.memo-note { color: var(--muted); font-size: 0.86rem; text-align: right; }
.cite-list { list-style: none; padding: 0; margin: 0; }
.cite-list > li { border-top: 1px solid var(--line); padding: 0.85rem 0; }
.cite-list > li:first-child { border-top: 0; }
.cite-head {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem 0.6rem;
  align-items: center;
  margin-bottom: 0.35rem;
  font-weight: 650;
}
.cite-meta { color: var(--muted); font-size: 0.86rem; margin-bottom: 0.35rem; }
a.play {
  color: var(--accent);
  text-decoration: underline;
  text-underline-offset: 2px;
  font-family: ui-monospace, Consolas, monospace;
  font-size: 0.85em;
}
.steps { margin: 0.35rem 0 0; padding-left: 1.15rem; max-width: 72ch; }
.steps li { margin: 0.28rem 0; }
.pill {
  display: inline-block;
  border-radius: 999px;
  padding: 0.12rem 0.55rem;
  font-size: 0.78rem;
  font-weight: 650;
  margin-right: 0.35rem;
}
.pill-gi { background: #ecfccb; color: #3f6212; border: 1px solid #84cc16; }
.pill-nogi { background: #e0f2fe; color: #075985; border: 1px solid #38bdf8; }
.pill-other { background: #eff6ff; color: #1d4ed8; border: 1px solid #93c5fd; }
.pill-caveat { background: #fef9c3; color: #854d0e; border: 1px solid #ca8a04; }
.other-card {
  border: 1px solid #93c5fd;
  border-radius: 10px;
  padding: 1rem;
  background: #eff6ff;
  margin-bottom: 0.75rem;
}
.caveat-box {
  background: #fef9c3;
  border: 1px solid #fde047;
  border-radius: 10px;
  padding: 1rem 1.1rem;
  margin: 0.45rem 0 0;
  max-width: 72ch;
}
.caveat-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
  margin-top: 0.5rem;
}
.question { font-size: 1.05rem; max-width: 68ch; margin: 0.35rem 0 0.75rem; }
.sides {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.75rem;
}
.side {
  border: 1px solid #fecdd3;
  border-radius: 10px;
  padding: 1rem 1.1rem;
  background: #fff1f2;
}
"""


def briefing_location(name: str, ruleset: str) -> str:
    return "/briefing?" + urlencode({"name": name, "ruleset": ruleset})


def render_briefing(store: CuratedStore, fields: dict[str, list[str]]) -> str:
    name = _first(fields, "name")
    ruleset = _first(fields, "ruleset")
    topic = store.topic(name, ruleset)
    if topic is None:
        body = (
            '<section class="panel">\n'
            '<p class="empty">That topic is not open.</p>\n'
            "</section>\n"
        )
        return render_shell(title="Briefing", current="home", body=body)
    memo = brief_topic(store, topic.name, topic.ruleset, _advisor(store))
    if memo is None:
        body = (
            '<section class="panel">\n'
            '<p class="empty">That topic is not open.</p>\n'
            "</section>\n"
        )
        return render_shell(title="Briefing", current="home", body=body)
    body = f"<style>{_STYLE}</style>\n" + _memo(store, memo)
    return render_shell(
        title=f"{memo.topic_name} ({memo.topic_ruleset})",
        current="home",
        body=body,
    )


def _advisor(store: CuratedStore):
    return getattr(store, "_briefing_advisor", None) or BriefingAdvisor()


def _memo(store: CuratedStore, memo: BriefingMemo) -> str:
    pill_class = "pill-gi" if memo.topic_ruleset == "gi" else "pill-nogi"
    pill_label = f"{html.escape(memo.topic_ruleset)} topic"
    same = "".join(_citation_item(store, citation) for citation in memo.same_ruleset_citations)
    parts = [
        '<article class="panel memo" id="briefing-memo">\n',
        '<div class="memo-top">\n',
        "<div>\n",
        f"<h2>{html.escape(memo.topic_name)} ({html.escape(memo.topic_ruleset)})</h2>\n",
        f'<div style="margin-top:.35rem"><span class="pill {pill_class}">{pill_label}</span></div>\n',
        "</div>\n",
        '<div class="memo-note">Before the coach determines the system</div>\n',
        "</div>\n",
        '<section id="same-ruleset">\n',
        "<h3>Same-ruleset citations</h3>\n",
        f'<ul class="cite-list">{same}</ul>\n' if same else '<p class="empty">No same-ruleset citations.</p>\n',
        "</section>\n",
        _other_section(store, memo),
        _disagreement_section(store, memo),
        "</article>\n",
    ]
    return "".join(parts)


def _other_section(store: CuratedStore, memo: BriefingMemo) -> str:
    if not memo.other_ruleset_citations:
        return ""
    cards = "".join(
        _other_card(store, citation) for citation in memo.other_ruleset_citations
    )
    caveat = _caveat_box(memo)
    return (
        '<section id="other-ruleset-briefing">\n'
        "<h3>Other-ruleset material</h3>\n"
        f'<p class="question">{html.escape(memo.other_ruleset_question)}</p>\n'
        f"{cards}"
        f"{caveat}"
        "</section>\n"
    )


def _other_card(store: CuratedStore, citation: Citation) -> str:
    return (
        '<div class="other-card">\n'
        f'<div class="cite-head">{html.escape(citation.movement)} '
        '<span class="pill pill-other">other-ruleset</span></div>\n'
        f"{_citation_meta(citation)}\n"
        f"{_playback(store, citation)}\n"
        f"{_steps(citation.step_bullets)}\n"
        "</div>\n"
    )


def _caveat_box(memo: BriefingMemo) -> str:
    if memo.caveat is None:
        return ""
    may = "".join(
        f"<li>{html.escape(item)}</li>" for item in memo.caveat.may_transfer if item
    )
    depends = "".join(
        f"<li>{html.escape(item)}</li>"
        for item in memo.caveat.depends_on_unshared_tools
        if item
    )
    return (
        '<div class="caveat-box">'
        '<span class="pill pill-caveat">caveat</span> '
        "<strong>What may transfer / what depends on unshared tools</strong>"
        '<div class="caveat-grid">'
        f"<div><em>May transfer</em><ul>{may}</ul></div>"
        f"<div><em>Depends on tools this topic does not share</em><ul>{depends}</ul></div>"
        "</div></div>\n"
    )


def _disagreement_section(store: CuratedStore, memo: BriefingMemo) -> str:
    if not memo.disagreement:
        return ""
    sides = "".join(
        _side(store, side.citation) for side in memo.disagreement
    )
    return (
        '<section id="disagreement">\n'
        "<h3>Same-ruleset disagreement</h3>\n"
        f'<div class="sides">{sides}</div>\n'
        "</section>\n"
    )


def _side(store: CuratedStore, citation: Citation) -> str:
    instructor = html.escape(citation.instructor or "")
    return (
        '<div class="side">\n'
        f"<strong>{instructor}</strong>\n"
        f'<div class="cite-head">{html.escape(citation.movement)}</div>\n'
        f"{_citation_meta(citation)}\n"
        f"{_playback(store, citation)}\n"
        f"{_steps(citation.step_bullets)}\n"
        "</div>\n"
    )


def _citation_item(store: CuratedStore, citation: Citation) -> str:
    return (
        "<li>\n"
        f'<div class="cite-head">{html.escape(citation.movement)}</div>\n'
        f"{_citation_meta(citation)}\n"
        f"{_playback(store, citation)}\n"
        f"{_steps(citation.step_bullets)}\n"
        "</li>\n"
    )


def _citation_meta(citation: Citation) -> str:
    meta = " · ".join(
        part
        for part in (
            citation.instructor or "",
            citation.instructional or "",
            citation.volume or "",
            citation.chapter or "",
        )
        if part
    )
    return f'<div class="cite-meta">{html.escape(meta)}</div>'


def _playback(store: CuratedStore, citation: Citation) -> str:
    lines = []
    for showing in citation.showings:
        lines.append(_play_line(store, citation, showing))
    return "\n".join(lines)


def _play_line(store: CuratedStore, citation: Citation, showing: Showing) -> str:
    playback = store.resolve_playback(
        citation,
        showing,
        video_root=store.video_root() or "",
        transcript_folder=store.transcript_folder() or "",
    )
    status = "available" if playback.available else "missing"
    handle = showing.playback_link or ""
    volume = citation.volume or ""
    clock = _fmt_time(playback.speech_start)
    label = handle or f"{volume}@{playback.speech_start}"
    visible = f"{clock} · {label} · {status}"
    href = playback.path.as_uri() if playback.available else ""
    href_attr = f' href="{html.escape(href, quote=True)}"' if href else ""
    return (
        f'<div class="cite-meta"><a class="play"{href_attr}>'
        f"{html.escape(visible)}</a></div>"
    )


def _steps(bullets) -> str:
    items = "".join(
        f"<li>{html.escape(str(bullet))}</li>" for bullet in bullets if bullet
    )
    if not items:
        return ""
    return f'<ol class="steps">{items}</ol>'


def _fmt_time(seconds: float) -> str:
    total = int(seconds)
    return f"{total // 60}:{total % 60:02d}"


def _first(fields: dict[str, list[str]], key: str) -> str:
    values = fields.get(key) or [""]
    return values[0] if values else ""


add_screen(Screen("briefing", "/briefing", "", get=render_briefing))
