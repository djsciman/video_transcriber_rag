"""Coach screen: pick a volume, review proposals, accept or dismiss citations."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path

from coach_app.app import Screen, add_screen, render_shell
from coach_app.cleanup import cleanup_volume
from coach_app.statements import StatementDrafter, propose_statements
from coach_app.store import Citation, CuratedStore, Showing
from coach_app.topics import OTHER_RULESET_CAVEAT, mark_other_ruleset_showing

_STYLE = """
.cite-list { list-style: none; padding: 0; margin: 0; }
.cite-list > li { border-top: 1px solid var(--line); padding: .85rem 0; }
.cite-list > li:first-child { border-top: 0; }
.cite-head { display: flex; flex-wrap: wrap; gap: .4rem .6rem; align-items: center; margin-bottom: .35rem; font-weight: 650; }
.cite-meta { color: var(--muted); font-size: .86rem; margin-bottom: .35rem; }
a.play { color: var(--accent); text-decoration: underline; text-underline-offset: 2px; font-family: ui-monospace, Consolas, monospace; font-size: .85em; }
.steps { margin: .35rem 0 0; padding-left: 1.15rem; max-width: 72ch; }
.steps li { margin: .28rem 0; }
.speech { margin: .35rem 0 0; padding-left: 1.15rem; color: var(--muted); }
.untitled { font-weight: 650; }
textarea { font: inherit; border: 1px solid var(--line); border-radius: 8px; padding: .35rem .55rem; width: 100%; min-height: 4.5rem; }
.actions { display: flex; gap: .45rem; margin-top: .45rem; }
.caveat-box {
  background: #fef9c3;
  border: 1px solid #fde047;
  border-radius: 10px;
  padding: 1rem 1.1rem;
  margin: .45rem 0 0;
  max-width: 72ch;
}
.pill {
  display: inline-block;
  border-radius: 999px;
  padding: .12rem .55rem;
  font-size: .78rem;
  font-weight: 650;
  margin-right: .35rem;
}
.pill-caveat { background: #fef9c3; color: #854d0e; border: 1px solid #ca8a04; }
"""


def render_curate(store: CuratedStore) -> str:
    session = _session(store)
    body = [
        f"<style>{_STYLE}</style>",
        _picker(session),
        _parts(session),
        _proposals(store, session),
        _accepted(store, session),
    ]
    return render_shell(
        title="Curate a volume",
        current="curate",
        body="\n".join(part for part in body if part),
    )


def post_curate(store: CuratedStore, fields: dict[str, list[str]]) -> str:
    action = _field(fields, "action")
    if action == "load":
        _load(store, fields)
    elif action == "accept":
        _accept(store, fields)
    elif action == "dismiss":
        _dismiss(store, fields)
    elif action == "correct":
        _correct_accepted(store, fields)
    elif action == "remove":
        _remove_accepted(store, fields)
    elif action == "mark":
        _mark_aside(store, fields)
    return "/curate"


def _load(store: CuratedStore, fields: dict[str, list[str]]) -> None:
    path = Path(_field(fields, "volume_path"))
    instructor = _field(fields, "instructor")
    instructional = _field(fields, "instructional")
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeError):
        store._curate = {
            "volume_path": str(path),
            "instructor": instructor,
            "instructional": instructional,
            "video_file": "",
            "cleaned": {"video_file": "", "recording_title": "", "parts": []},
            "proposals": [],
        }
        return
    cleaned = cleanup_volume(raw)
    proposals = propose_statements(
        cleaned, StatementDrafter(), instructor=instructor
    )
    store._curate = {
        "volume_path": str(path),
        "instructor": instructor,
        "instructional": instructional,
        "video_file": cleaned.get("video_file") or "",
        "cleaned": cleaned,
        "proposals": list(proposals),
    }


def _accept(store: CuratedStore, fields: dict[str, list[str]]) -> None:
    proposal = _proposal_from(fields)
    if not proposal:
        return
    movement = _field(fields, "movement") or proposal.get("movement")
    bullets = _bullets(_field(fields, "step_bullets"))
    draft = store.correct(
        proposal,
        movement=movement,
        step_bullets=bullets if bullets else proposal.get("step_bullets"),
    )
    instructional = _field(fields, "instructional") or proposal.get(
        "instructional", ""
    )
    video_file = _field(fields, "video_file") or _session(store).get("video_file", "")
    if not instructional or not video_file:
        return
    store.accept(draft, instructional=instructional, video_file=video_file)
    _drop_proposal(store, proposal)


def _dismiss(store: CuratedStore, fields: dict[str, list[str]]) -> None:
    proposal = _proposal_from(fields)
    if proposal:
        _drop_proposal(store, proposal)


def _correct_accepted(store: CuratedStore, fields: dict[str, list[str]]) -> None:
    citation = store.citation(_field(fields, "citation_id"))
    if citation is None:
        return
    movement = _field(fields, "movement") or citation.movement
    bullets = _bullets(_field(fields, "step_bullets"))
    store.correct(
        citation,
        movement=movement,
        step_bullets=bullets if bullets else citation.step_bullets,
    )


def _remove_accepted(store: CuratedStore, fields: dict[str, list[str]]) -> None:
    citation_id = _field(fields, "citation_id")
    if citation_id:
        store.remove(citation_id)


def _mark_aside(store: CuratedStore, fields: dict[str, list[str]]) -> None:
    citation = store.citation(_field(fields, "citation_id"))
    if citation is None:
        return
    try:
        timestamp = float(_field(fields, "timestamp"))
    except ValueError:
        return
    playback_link = _field(fields, "playback_link") or None
    showing = None
    for item in citation.showings:
        if item.timestamp != timestamp:
            continue
        if playback_link is not None and item.playback_link != playback_link:
            continue
        showing = item
        break
    if showing is None:
        return
    mark_other_ruleset_showing(store, citation, showing)


def _picker(session: dict) -> str:
    volume_path = escape(str(session.get("volume_path") or ""), quote=True)
    instructor = escape(str(session.get("instructor") or ""), quote=True)
    instructional = escape(str(session.get("instructional") or ""), quote=True)
    return (
        '<section class="panel" id="pick-volume">\n'
        "<h2>Pick a volume</h2>\n"
        '<form method="post" action="/curate">\n'
        '<input type="hidden" name="action" value="load">\n'
        '<label for="volume_path">Volume JSON</label>\n'
        f'<input id="volume_path" name="volume_path" type="text" value="{volume_path}">\n'
        '<label for="instructor">Instructor</label>\n'
        f'<input id="instructor" name="instructor" type="text" value="{instructor}">\n'
        '<label for="instructional">Instructional</label>\n'
        f'<input id="instructional" name="instructional" type="text" value="{instructional}">\n'
        '<button type="submit">Review volume</button>\n'
        "</form>\n"
        "</section>\n"
    )


def _parts(session: dict) -> str:
    cleaned = session.get("cleaned")
    if not cleaned:
        return ""
    items = []
    for part in cleaned.get("parts") or []:
        title = str(part.get("title") or "").strip()
        if title:
            heading = escape(title)
        else:
            heading = '<span class="untitled">Untitled part</span>'
            note = (
                '<p class="empty">Stays unciteable until movements are marked.</p>'
            )
        speech = "".join(
            f"<li>{escape(span.get('text') or '')}</li>"
            for span in part.get("speech") or []
        )
        block = f"<li><div class=\"cite-head\">{heading}</div>"
        if not title:
            block += note
        if speech:
            block += f'<ul class="speech">{speech}</ul>'
        block += "</li>"
        items.append(block)
    if not items:
        return (
            '<section class="panel" id="parts">\n'
            "<h2>Parts</h2>\n"
            '<p class="empty">No parts in this volume.</p>\n'
            "</section>\n"
        )
    return (
        '<section class="panel" id="parts">\n'
        "<h2>Parts</h2>\n"
        f"<ul>{''.join(items)}</ul>\n"
        "</section>\n"
    )


def _proposals(store: CuratedStore, session: dict) -> str:
    proposals = session.get("proposals") or []
    if not session:
        return ""
    if not proposals:
        return (
            '<section class="panel" id="proposals">\n'
            "<h2>Proposed statements</h2>\n"
            '<p class="empty">No proposed statements.</p>\n'
            "</section>\n"
        )
    instructor = session.get("instructor") or ""
    instructional = session.get("instructional") or ""
    video_file = session.get("video_file") or ""
    cards = []
    for proposal in proposals:
        cards.append(
            _proposal_card(
                store,
                proposal,
                instructor=instructor,
                instructional=instructional,
                video_file=video_file,
            )
        )
    return (
        '<section class="panel" id="proposals">\n'
        "<h2>Proposed statements</h2>\n"
        f'<ul class="cite-list">{"".join(cards)}</ul>\n'
        "</section>\n"
    )


def _proposal_card(
    store: CuratedStore,
    proposal: dict,
    *,
    instructor: str,
    instructional: str,
    video_file: str,
) -> str:
    movement = str(proposal.get("movement") or "")
    chapter = str(proposal.get("chapter") or "")
    bullets = tuple(proposal.get("step_bullets") or ())
    payload = escape(json.dumps(proposal), quote=True)
    play = _playback_lines(
        store,
        volume=video_file,
        details=proposal.get("details") or (),
        movement=movement,
        chapter=chapter,
        instructor=instructor,
        instructional=instructional,
    )
    meta = " · ".join(
        part
        for part in (instructor, instructional, video_file, chapter)
        if part
    )
    return (
        "<li>\n"
        f'<div class="cite-head">{escape(movement)}</div>\n'
        f'<div class="cite-meta">{escape(meta)}</div>\n'
        f"{play}\n"
        f"{_steps(bullets)}\n"
        '<form method="post" action="/curate">\n'
        f'<input type="hidden" name="proposal" value="{payload}">\n'
        f'<input type="hidden" name="instructor" value="{escape(instructor, quote=True)}">\n'
        f'<input type="hidden" name="instructional" value="{escape(instructional, quote=True)}">\n'
        f'<input type="hidden" name="video_file" value="{escape(video_file, quote=True)}">\n'
        '<label>Move name</label>\n'
        f'<input name="movement" type="text" value="{escape(movement, quote=True)}">\n'
        "<label>Step bullets</label>\n"
        f'<textarea name="step_bullets">{escape("\n".join(bullets))}</textarea>\n'
        '<div class="actions">\n'
        '<button type="submit" name="action" value="accept">Accept</button>\n'
        '<button type="submit" name="action" value="dismiss">Dismiss</button>\n'
        "</div>\n"
        "</form>\n"
        "</li>\n"
    )


def _accepted(store: CuratedStore, session: dict) -> str:
    video_file = session.get("video_file") or ""
    citations = [
        citation
        for citation in store.citations()
        if citation.volume == video_file and video_file
    ]
    if not citations:
        return ""
    cards = [_accepted_card(store, citation) for citation in citations]
    return (
        '<section class="panel" id="accepted">\n'
        "<h2>Accepted citations</h2>\n"
        f'<ul class="cite-list">{"".join(cards)}</ul>\n'
        "</section>\n"
    )


def _accepted_card(store: CuratedStore, citation: Citation) -> str:
    bullets = citation.step_bullets
    play = "\n".join(
        _showing_block(store, citation, showing) for showing in citation.showings
    )
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
    return (
        "<li>\n"
        f'<div class="cite-head">{escape(citation.movement)}</div>\n'
        f'<div class="cite-meta">{escape(meta)}</div>\n'
        f"{play}\n"
        f"{_steps(bullets)}\n"
        '<form method="post" action="/curate">\n'
        f'<input type="hidden" name="citation_id" value="{escape(citation.id, quote=True)}">\n'
        '<label>Move name</label>\n'
        f'<input name="movement" type="text" value="{escape(citation.movement, quote=True)}">\n'
        "<label>Step bullets</label>\n"
        f'<textarea name="step_bullets">{escape("\n".join(bullets))}</textarea>\n'
        '<div class="actions">\n'
        '<button type="submit" name="action" value="correct">Save</button>\n'
        '<button type="submit" name="action" value="remove">Remove</button>\n'
        "</div>\n"
        "</form>\n"
        "</li>\n"
    )


def _showing_block(store: CuratedStore, citation: Citation, showing: Showing) -> str:
    play = _playback_lines(
        store,
        volume=citation.volume or "",
        details=({"speech_start": showing.timestamp},),
        movement=citation.movement,
        chapter=citation.chapter or "",
        instructor=citation.instructor or "",
        instructional=citation.instructional or "",
    )
    playback_link = showing.playback_link or ""
    mark = (
        '<form method="post" action="/curate">\n'
        '<input type="hidden" name="action" value="mark">\n'
        f'<input type="hidden" name="citation_id" value="{escape(citation.id, quote=True)}">\n'
        f'<input type="hidden" name="timestamp" value="{escape(str(showing.timestamp), quote=True)}">\n'
        f'<input type="hidden" name="playback_link" value="{escape(playback_link, quote=True)}">\n'
        '<button type="submit">Mark other-ruleset aside</button>\n'
        "</form>\n"
    )
    caveat = getattr(showing, "caveat", "") or ""
    caveat_box = ""
    if caveat:
        caveat_box = (
            '<div class="caveat-box">'
            '<span class="pill pill-caveat">caveat</span> '
            f"{escape(caveat or OTHER_RULESET_CAVEAT)}"
            "</div>\n"
        )
    return f"{play}\n{mark}{caveat_box}"


def _playback_lines(
    store: CuratedStore,
    *,
    volume: str,
    details,
    movement: str,
    chapter: str,
    instructor: str,
    instructional: str,
) -> str:
    lines = []
    for detail in details:
        timestamp = float(detail["speech_start"])
        playback = store.resolve_playback(
            Citation(
                movement=movement,
                instructor=instructor or None,
                instructional=instructional or None,
                volume=volume or None,
                chapter=chapter or None,
            ),
            Showing(timestamp=timestamp),
            video_root=store.video_root() or "",
            transcript_folder=store.transcript_folder() or "",
        )
        status = "available" if playback.available else "missing"
        clock = _fmt_time(playback.speech_start)
        raw = _fmt_raw(playback.speech_start)
        label = f"{clock} ({raw}s) · {volume} · {status}"
        href = playback.path.as_uri() if playback.available else ""
        href_attr = f' href="{escape(href, quote=True)}"' if href else ""
        lines.append(
            f'<div class="cite-meta"><a class="play"{href_attr}>{escape(label)}</a></div>'
        )
    return "\n".join(lines)


def _steps(bullets) -> str:
    items = "".join(f"<li>{escape(str(bullet))}</li>" for bullet in bullets if bullet)
    if not items:
        return ""
    return f'<ol class="steps">{items}</ol>'


def _proposal_from(fields: dict[str, list[str]]) -> dict:
    raw = _field(fields, "proposal")
    if not raw:
        return {}
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _drop_proposal(store: CuratedStore, proposal: dict) -> None:
    session = _session(store)
    key = _key(proposal)
    session["proposals"] = [
        item for item in session.get("proposals") or [] if _key(item) != key
    ]


def _key(proposal: dict) -> tuple:
    return (proposal.get("chapter"), proposal.get("movement"))


def _session(store: CuratedStore) -> dict:
    session = getattr(store, "_curate", None)
    return session if isinstance(session, dict) else {}


def _field(fields: dict[str, list[str]], name: str) -> str:
    values = fields.get(name) or [""]
    return values[0]


def _bullets(text: str) -> tuple[str, ...]:
    return tuple(line.strip() for line in text.splitlines() if line.strip())


def _fmt_time(seconds: float) -> str:
    total = int(seconds)
    return f"{total // 60}:{total % 60:02d}"


def _fmt_raw(seconds: float) -> str:
    if float(seconds).is_integer():
        return str(int(seconds))
    return str(seconds)


add_screen(
    Screen("curate", "/curate", "Curate", get=render_curate, post=post_curate)
)
