"""Local coach-only application opened in a browser on this machine."""

from __future__ import annotations

import argparse
import html
import inspect
from collections.abc import Callable
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import parse_qs, urlencode, urlparse

from coach_app.store import CuratedStore

DEFAULT_LOCATION = Path.cwd() / "curated-store"
_CSS = (Path(__file__).with_name("shell.css")).read_text(encoding="utf-8")


@dataclass(frozen=True)
class Screen:
    name: str
    path: str
    label: str
    get: Callable[[CuratedStore], str] | None = None
    post: Callable[[CuratedStore, dict[str, list[str]]], str] | None = None


SCREENS: list[Screen] = []


def add_screen(screen: Screen) -> Screen:
    SCREENS.append(screen)
    return screen


def nav_items() -> tuple[Screen, ...]:
    return tuple(screen for screen in SCREENS if screen.label)


def screen_for(path: str) -> Screen | None:
    for screen in SCREENS:
        if screen.path == path:
            return screen
    return None


def render_shell(*, title: str, current: str, body: str) -> str:
    links = []
    for screen in nav_items():
        current_attr = ' aria-current="page"' if screen.name == current else ""
        links.append(
            f'<a href="{html.escape(screen.path, quote=True)}"{current_attr}>'
            f"{html.escape(screen.label)}</a>"
        )
    nav = "\n".join(links)
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        f"<title>{html.escape(title)}</title>\n"
        f"<style>{_CSS}</style>\n"
        "</head>\n"
        "<body>\n"
        '<div class="page">\n'
        "<header>\n"
        "<h1>Advising</h1>\n"
        '<p class="meta">Coach-only. Students never use this application.</p>\n'
        "</header>\n"
        f"<nav>{nav}</nav>\n"
        f"<main>{body}</main>\n"
        "</div>\n"
        "</body>\n"
        "</html>\n"
    )


def render_home(store: CuratedStore) -> str:
    topics = store.topics()
    if topics:
        items = "".join(
            _topic_link(topic.name, topic.ruleset) for topic in topics
        )
        topics_body = f"<ul>{items}</ul>"
    else:
        topics_body = '<p class="empty">No topics yet.</p>'
    video_root = store.video_root() or ""
    transcript_folder = store.transcript_folder() or ""
    body = (
        '<section class="panel" id="topics">\n'
        "<h2>Topics</h2>\n"
        f"{topics_body}\n"
        '<form method="post" action="/topics">\n'
        '<label for="topic_name">Topic name</label>\n'
        '<input id="topic_name" name="name" type="text">\n'
        '<div class="choices">\n'
        '<label><input type="radio" name="ruleset" value="gi"> gi</label>\n'
        '<label><input type="radio" name="ruleset" value="no-gi"> no-gi</label>\n'
        "</div>\n"
        '<button type="submit">Open</button>\n'
        "</form>\n"
        "</section>\n"
        '<section class="panel" id="settings">\n'
        "<h2>Playback folders</h2>\n"
        '<form method="post" action="/settings">\n'
        '<label for="video_root">Video root</label>\n'
        f'<input id="video_root" name="video_root" type="text" value="{html.escape(video_root, quote=True)}">\n'
        '<label for="transcript_folder">Transcript folder</label>\n'
        f'<input id="transcript_folder" name="transcript_folder" type="text" value="{html.escape(transcript_folder, quote=True)}">\n'
        '<button type="submit">Save</button>\n'
        "</form>\n"
        "</section>\n"
    )
    return render_shell(title="Coach advising", current="home", body=body)


def save_settings(store: CuratedStore, fields: dict[str, list[str]]) -> str:
    store.set_video_root(_optional(fields.get("video_root", [""])[0]))
    store.set_transcript_folder(_optional(fields.get("transcript_folder", [""])[0]))
    return "/"


def _optional(value: str) -> str | None:
    stripped = value.strip()
    return stripped or None


def _topic_link(name: str, ruleset: str) -> str:
    href = "/topics?" + urlencode({"name": name, "ruleset": ruleset})
    label = f"{html.escape(name)} ({html.escape(ruleset)})"
    return f'<li><a href="{html.escape(href, quote=True)}">{label}</a></li>'


def _call_get(screen: Screen, store: CuratedStore, fields: dict[str, list[str]]) -> str:
    get = screen.get
    if get is None:
        raise RuntimeError("screen has no get")
    if len(inspect.signature(get).parameters) >= 2:
        return get(store, fields)
    return get(store)


add_screen(Screen("home", "/", "Home", get=render_home))
add_screen(Screen("settings", "/settings", "", post=save_settings))
import coach_app.ui_topics
import coach_app.ui_curate  # noqa: E402


class CoachApp:
    """Serve the coach screens against one curated store on localhost."""

    def __init__(self, location, host: str = "127.0.0.1", port: int = 0) -> None:
        self.location = Path(location)
        self.store = CuratedStore.open(self.location)
        self.httpd = _LocalServer((host, port), _make_handler(self))
        self._thread: Thread | None = None

    @property
    def url(self) -> str:
        host, port = self.httpd.server_address
        if isinstance(host, bytes):
            host = host.decode()
        if host in {"0.0.0.0", "::", ""}:
            host = "127.0.0.1"
        return f"http://{host}:{port}"

    def start(self) -> CoachApp:
        self._thread = Thread(target=self.httpd.serve_forever, daemon=True)
        self._thread.start()
        return self

    def stop(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None

    def wait(self) -> None:
        if self._thread is not None:
            self._thread.join()

    def __enter__(self) -> CoachApp:
        return self.start()

    def __exit__(self, *exc) -> None:
        self.stop()


class _LocalServer(ThreadingHTTPServer):
    allow_reuse_address = True


def _make_handler(app: CoachApp):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path or "/"
            screen = screen_for(path)
            if screen is None or screen.get is None:
                self._send(404, "text/plain; charset=utf-8", b"Not found")
                return
            fields = parse_qs(parsed.query, keep_blank_values=True)
            body = _call_get(screen, app.store, fields).encode("utf-8")
            self._send(200, "text/html; charset=utf-8", body)

        def do_POST(self) -> None:
            path = urlparse(self.path).path or "/"
            screen = screen_for(path)
            if screen is None or screen.post is None:
                self._send(404, "text/plain; charset=utf-8", b"Not found")
                return
            length = int(self.headers.get("Content-Length", "0") or "0")
            raw = self.rfile.read(length).decode("utf-8") if length else ""
            fields = parse_qs(raw, keep_blank_values=True)
            location = screen.post(app.store, fields)
            self.send_response(303)
            self.send_header("Location", location)
            self.end_headers()

        def log_message(self, format, *args) -> None:
            return

        def _send(self, status: int, content_type: str, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    return Handler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Open the coach-only advising application in a browser on this machine."
    )
    parser.add_argument(
        "--location",
        default=str(DEFAULT_LOCATION),
        help="Curated store location (default: curated-store next to the process).",
    )
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    app = CoachApp(args.location, host=args.host, port=args.port)
    app.start()
    print(f"Coach advising is open at {app.url} on this machine.")
    try:
        app.wait()
    except KeyboardInterrupt:
        app.stop()
    else:
        app.stop()
    return 0
