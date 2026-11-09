"""PROTOTYPE (issue 90) — HTML-over-the-wire.

Starlette + Jinja2 + htmx. Guided next-action. Blue sans-serif shell.
In-memory sample only. Bind 127.0.0.1:8771. Does not write the curated store.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import HTMLResponse, RedirectResponse
from starlette.routing import Route
from starlette.templating import Jinja2Templates

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sample_store import counts, fresh, next_action  # noqa: E402

HERE = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(HERE / "templates"))
BLUE_CSS = (ROOT / "blue_shell.css").read_text(encoding="utf-8")
STATE = fresh()
HOST = "127.0.0.1"
PORT = 8771


def ctx(request: Request, extra: dict | None = None) -> dict:
    payload = {
        "request": request,
        "state": STATE,
        "counts": counts(STATE),
        "next": next_action(STATE),
        "prototype_name": "HTML-over-the-wire",
        "port": PORT,
        "blue_css": BLUE_CSS,
    }
    if extra:
        payload.update(extra)
    return payload


async def home(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "work.html", ctx(request))


async def propose(request: Request) -> HTMLResponse:
    await asyncio.sleep(1.2)
    STATE["last_feedback"] = (
        "Advisor proposed a cleaned statement. It is labeled and reversible."
    )
    if request.headers.get("hx-request"):
        return templates.TemplateResponse(request, "fragments/stage.html", ctx(request))
    return RedirectResponse("/", status_code=303)


async def accept(request: Request) -> RedirectResponse:
    form = await request.form()
    pid = str(form.get("proposal_id") or "")
    for proposal in STATE["proposals"]:
        if proposal["id"] == pid and proposal["status"] == "awaiting":
            proposal["status"] = "accepted"
            STATE["citations_accepted"] += 1
            STATE["uncategorized"].append(
                {
                    "id": f"new-{pid}",
                    "text": proposal["text"],
                    "instructor": "Sample instructor",
                    "playback_missing": False,
                }
            )
            STATE["last_feedback"] = (
                f"Coach accepted. Curated store now holds {STATE['citations_accepted']} citations. "
                "The citation is uncategorized until Place."
            )
            break
    return RedirectResponse("/", status_code=303)


async def dismiss(request: Request) -> RedirectResponse:
    form = await request.form()
    pid = str(form.get("proposal_id") or "")
    for proposal in STATE["proposals"]:
        if proposal["id"] == pid:
            proposal["status"] = "dismissed"
            STATE["last_feedback"] = "Coach dismissed the proposal. Reversible by proposing again."
            break
    return RedirectResponse("/", status_code=303)


async def place(request: Request) -> RedirectResponse:
    form = await request.form()
    cid = str(form.get("citation_id") or "")
    remaining = []
    for item in STATE["uncategorized"]:
        if item["id"] == cid:
            STATE["placed"].append({**item, "named_move": "Hip bump sweep"})
            STATE["last_feedback"] = (
                f"Coach placed a citation on named move Hip bump sweep. "
                f"{len(STATE['uncategorized']) - 1} uncategorized remain."
            )
        else:
            remaining.append(item)
    STATE["uncategorized"] = remaining
    return RedirectResponse("/", status_code=303)


async def choose_system(request: Request) -> RedirectResponse:
    STATE["system_chosen"] = True
    STATE["system_words"] = "Hip bump or kimura when the partner posts"
    STATE["last_feedback"] = "Coach determined the system. Design is now anchored."
    return RedirectResponse("/", status_code=303)


async def add_named_move(request: Request) -> RedirectResponse:
    STATE["map_marks"].append(
        {"id": f"m{len(STATE['map_marks']) + 1}", "kind": "named_move", "label": "Hip bump sweep"}
    )
    STATE["last_feedback"] = "Named move added on Design. Convert can pack."
    return RedirectResponse("/", status_code=303)


async def convert(request: Request) -> HTMLResponse:
    await asyncio.sleep(0.8)
    named = [m for m in STATE["map_marks"] if m.get("kind") == "named_move"]
    if not named:
        STATE["last_feedback"] = "Convert blocked: Design needs a named move."
        if request.headers.get("hx-request"):
            return templates.TemplateResponse(request, "fragments/stage.html", ctx(request))
        return RedirectResponse("/", status_code=303)
    STATE["sheet_mode"] = "draft"
    STATE["draft_classes"] = [
        {"title": "Class 1", "kind": "technique", "move": "Hip bump sweep"}
    ]
    STATE["last_feedback"] = "Coach converted Design to Draft. Sheet mode is Draft (dashed cards)."
    if request.headers.get("hx-request"):
        return templates.TemplateResponse(request, "fragments/stage.html", ctx(request))
    return RedirectResponse("/", status_code=303)


async def print_packet(request: Request) -> HTMLResponse:
    STATE["last_feedback"] = "Print packet ready: landscape canvas, portrait class cards, 0.5 in."
    return templates.TemplateResponse(request, "print.html", ctx(request))


async def reset(request: Request) -> RedirectResponse:
    STATE.clear()
    STATE.update(fresh())
    return RedirectResponse("/", status_code=303)


app = Starlette(
    debug=True,
    routes=[
        Route("/", home),
        Route("/propose", propose, methods=["POST"]),
        Route("/accept", accept, methods=["POST"]),
        Route("/dismiss", dismiss, methods=["POST"]),
        Route("/place", place, methods=["POST"]),
        Route("/choose-system", choose_system, methods=["POST"]),
        Route("/add-named-move", add_named_move, methods=["POST"]),
        Route("/convert", convert, methods=["POST"]),
        Route("/print", print_packet),
        Route("/reset", reset, methods=["POST"]),
    ],
)


if __name__ == "__main__":
    import uvicorn

    print(f"PROTOTYPE html-over-wire on http://{HOST}:{PORT} (sample data, no store writes)")
    uvicorn.run(app, host=HOST, port=PORT, log_level="warning")
