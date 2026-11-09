# UI/UX redesign prototypes

Throwaway compositions for the [UI/UX Redesign map](https://github.com/djsciman/video_transcriber_rag/issues/85). Not production. Production screens stay the spec-70 stdlib HTTP shell.

## This branch (`research/python-ui-libraries`, issue 90)

Three **separate** compositions of non-stdlib Python + JavaScript. Not skins. Not `?variant=` on one page.

| Folder | Python + JS | 88 paradigm | 87 visual | Port |
| --- | --- | --- | --- | --- |
| [html-over-wire/](html-over-wire/) | Starlette + Jinja2 + htmx 2.0.11 | Guided next-action | Blue sans productivity | 127.0.0.1:8771 |
| [nicegui-studio/](nicegui-studio/) | NiceGUI 3.19.0 (bundles Vue + Quasar) | Topic studio | Blue sans over Quasar | 127.0.0.1:8772 |
| [flask-alpine-inbox/](flask-alpine-inbox/) | Flask + Jinja2 + Alpine.js 3.14.8 | Attention inbox + workspace | Blue sans + APG dialog | 127.0.0.1:8773 |

Shared visual: [`blue_shell.css`](blue_shell.css) — navy appbar, ice-blue canvas, Segoe UI / Helvetica / Arial, filled blue primaries. Distinct from spec-70 cream/serif paper-ink.

Chrome: **green dotted** = proposed coach-final UI. **red dotted** = prototype-only chrome. Each page has a red banner explaining the key.

Findings: [`docs/ui-ux-discovery/python-js-ui-libraries.md`](../../docs/ui-ux-discovery/python-js-ui-libraries.md)

### One venv (Windows)

From this directory:

```
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r html-over-wire\requirements.txt -r nicegui-studio\requirements.txt -r flask-alpine-inbox\requirements.txt
```

Then run **one** composition at a time:

```
.\.venv\Scripts\python.exe html-over-wire\app.py
.\.venv\Scripts\python.exe nicegui-studio\app.py
.\.venv\Scripts\python.exe flask-alpine-inbox\app.py
```

Stop with Ctrl+C. Do not leave servers running. State is in-memory; nothing is written to a production curated-store folder.

## Sibling prototypes (other branches)

These files are **not** on this branch. Fetch them from the research branches that landed them:

- Issue 88 (UX philosophies): `research/ux-philosophies-issue-88` — `prototypes/ui-ux-redesign/ux-index.html`, `ux-guided.html`, `ux-inbox.html`, `ux-studio.html`
- Issue 87 (tech + visual): `research/ui-tech-visual-issue-87` — `prototypes/ui-ux-redesign/visual-index.html`, `visual-editorial.html`, `visual-productivity.html`, `visual-layered.html`

```
git show research/ux-philosophies-issue-88:prototypes/ui-ux-redesign/ux-guided.html
git show research/ui-tech-visual-issue-87:prototypes/ui-ux-redesign/visual-editorial.html
```
