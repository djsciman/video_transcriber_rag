"""PROTOTYPE (issue 90) — Flask + Jinja2 + Alpine.js inbox.

Attention inbox + workspace. Productivity tokens + APG dialog.
In-memory sample only. Bind 127.0.0.1:8773. Does not write the curated store.
"""

from __future__ import annotations

import sys
from pathlib import Path

from flask import Flask, redirect, render_template, request, url_for

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sample_store import counts, fresh, next_action  # noqa: E402

HOST = "127.0.0.1"
PORT = 8773
STATE = fresh()
BLUE_CSS = (ROOT / "blue_shell.css").read_text(encoding="utf-8")

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True


def page(queue: str = "uncategorized"):
    return render_template(
        "inbox.html",
        state=STATE,
        counts=counts(STATE),
        next=next_action(STATE),
        queue=queue,
        port=PORT,
        blue_css=BLUE_CSS,
    )


@app.get("/")
def home():
    return page(request.args.get("queue") or "uncategorized")


@app.post("/accept")
def accept():
    pid = request.form.get("proposal_id") or ""
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
                f"Coach accepted. {STATE['citations_accepted']} citations in the curated store. "
                "The new citation joined Uncategorized."
            )
            break
    return redirect(url_for("home", queue="awaiting"))


@app.post("/place")
def place():
    cid = request.form.get("citation_id") or ""
    remaining = []
    for item in STATE["uncategorized"]:
        if item["id"] == cid:
            STATE["placed"].append({**item, "named_move": "Hip bump sweep"})
            STATE["last_feedback"] = "Coach placed the citation on named move Hip bump sweep."
        else:
            remaining.append(item)
    STATE["uncategorized"] = remaining
    return redirect(url_for("home", queue="uncategorized"))


@app.post("/choose-system")
def choose_system():
    STATE["system_chosen"] = True
    STATE["system_words"] = "Hip bump or kimura when the partner posts"
    if STATE["map_marks"]:
        STATE["last_feedback"] = "Coach determined the system. Topic is map-ready."
    else:
        STATE["map_marks"].append({"id": "m1", "kind": "named_move", "label": "Hip bump sweep"})
        STATE["last_feedback"] = "Coach determined the system and the sample map is ready."
    return redirect(url_for("home", queue="map-ready"))


@app.post("/remove-citation")
def remove_citation():
    cid = request.form.get("citation_id") or ""
    STATE["uncategorized"] = [c for c in STATE["uncategorized"] if c["id"] != cid]
    STATE["last_feedback"] = "Coach removed a citation after confirming. High-cost action was gated."
    return redirect(url_for("home", queue="uncategorized"))


@app.post("/reset")
def reset():
    STATE.clear()
    STATE.update(fresh())
    return redirect(url_for("home"))


if __name__ == "__main__":
    print(f"PROTOTYPE flask-alpine-inbox on http://{HOST}:{PORT} (sample data, no store writes)")
    app.run(host=HOST, port=PORT, debug=False, use_reloader=False)
