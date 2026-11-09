# PROTOTYPE — Flask + Alpine.js attention inbox (issue 90)

Throwaway. Not production. Attention inbox + workspace, productivity tokens, native `dialog`.

## What it proves

- Flask + Jinja2 keep the HTML POST seam (HTTP tests can still POST then assert store state).
- Alpine.js adds client filter and dialog open/close without an SPA JSON rewrite.
- Native `<dialog>` is the APG-shaped confirm for remove-citation (issue 88 principle 10).
- Status chips put uncategorized / awaiting / map-ready in the world (principle 3).

## Run (Windows)

```
py -3 ..\.venv\Scripts\python.exe app.py
```

Open http://127.0.0.1:8773/

Stop with Ctrl+C.

## Third-party Python

| Import | Pin | OSI | Security |
| --- | --- | --- | --- |
| flask | 3.1.3 | BSD-3-Clause | https://palletsprojects.com/security ; pin ≥3.1.3 for GHSA-68rp-wp8r-4726 |
| jinja2 | 3.1.6 | BSD-3-Clause | https://github.com/pallets/jinja/security/advisories |
| markupsafe | 3.0.4 | BSD-3-Clause | Pallets |
| werkzeug | 3.1.9 | BSD-3-Clause | Pallets (Flask WSGI) |

## Third-party JavaScript

| Asset | Pin | OSI | Security |
| --- | --- | --- | --- |
| alpinejs | 3.14.8 (jsDelivr CDN, throwaway) | MIT | No GHSA hits on `alpinejs` in GitHub Advisory Database at research time; report via GitHub. https://github.com/alpinejs/alpine |

## 88 / 87 mapping

- Paradigm: attention inbox + workspace (issue 88 candidate 2)
- Visual: productivity tokens + APG patterns (issue 87 candidate B)
