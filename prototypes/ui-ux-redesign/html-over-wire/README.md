# PROTOTYPE — HTML-over-the-wire (issue 90)

Throwaway. Not production. Guided next-action + editorial paper/ink.

## What it proves

Starlette (Python host) + Jinja2 (HTML generation) + htmx (fragment POST + `hx-indicator`) can host:

- Next action as a first-class object
- Advisor proposal vs coach Accept/Dismiss
- Knowledge in the world chips
- Busy Propose / Convert without replacing the HTML/`CuratedStore` POST seam
- Print `@page` landscape canvas + portrait class cards, 0.5 in

## Run (Windows)

From this folder, after creating the shared venv (see parent README):

```
py -3 ..\.venv\Scripts\python.exe app.py
```

Or from a venv that already has `requirements.txt` installed:

```
py -3 app.py
```

Open http://127.0.0.1:8771/ — bind is localhost only.

Stop with Ctrl+C. In-memory only; reset does not touch production store files.

## Third-party Python

| Import | Pin | OSI | Security |
| --- | --- | --- | --- |
| starlette | 1.10.0 | BSD-3-Clause | https://github.com/Kludex/starlette/security/advisories ; pin ≥1.3.1 for GHSA-82w8-qh3p-5jfq |
| jinja2 | 3.1.6 | BSD-3-Clause | https://github.com/pallets/jinja/security/advisories ; pin ≥3.1.6 for GHSA-cpwx-vrp4-4pq7 |
| uvicorn | 0.54.0 | BSD-3-Clause | https://github.com/Kludex/uvicorn (Encode/Kludex security process) |
| python-multipart | 0.0.33 | Apache-2.0 | needed for Starlette `request.form()` |
| markupsafe | 3.0.4 | BSD-3-Clause | Jinja escaping; Pallets security |

## Third-party JavaScript

| Asset | Pin | OSI | Security |
| --- | --- | --- | --- |
| htmx.org | 2.0.11 (jsDelivr, SRI in template) | 0BSD | https://github.com/bigskysoftware/htmx/blob/master/SECURITY.md |

CDN is throwaway-only. Production would vendor the file.

## 88 / 87 mapping

- Paradigm: guided next-action (issue 88 candidate 1)
- Visual: editorial paper/ink (issue 87 candidate A)
- Closest to issue 87 stack sketch S2, now with a real Python extra
