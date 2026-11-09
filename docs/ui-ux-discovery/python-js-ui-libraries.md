# Open-source Python and JavaScript libraries for coach-app UX and visual principles

Research for [Research: Open-Source Third-Party Python and JavaScript Libraries to Realize the UX and Visual Principles](https://github.com/djsciman/video_transcriber_rag/issues/90), a child of the [UI/UX Redesign map](https://github.com/djsciman/video_transcriber_rag/issues/85).

This document names **implementations** and scores them against issue 88 candidate principles and issue 87 visual/interaction needs. It does **not** lock a stack. Live screens stay the spec-70 stdlib HTTP shell until the review child records direction.

Throwaway prototypes on this branch (`research/python-ui-libraries`):

- [`prototypes/ui-ux-redesign/html-over-wire/`](../../prototypes/ui-ux-redesign/html-over-wire/) — Starlette + Jinja2 + htmx (127.0.0.1:8771)
- [`prototypes/ui-ux-redesign/nicegui-studio/`](../../prototypes/ui-ux-redesign/nicegui-studio/) — NiceGUI / Quasar (127.0.0.1:8772)
- [`prototypes/ui-ux-redesign/flask-alpine-inbox/`](../../prototypes/ui-ux-redesign/flask-alpine-inbox/) — Flask + Jinja2 + Alpine.js (127.0.0.1:8773)

Index: [`prototypes/ui-ux-redesign/README.md`](../../prototypes/ui-ux-redesign/README.md)

---

## 1. Executive summary

Issue 87 already named *approaches* (stdlib HTML shell; tokens + APG; layered dashboard; htmx as the strongest JS fit for the HTML/`CuratedStore` POST seam). This ticket names *libraries*, applies an admission filter (not stdlib; OSI-approved; security process; local-first), scores them against issue 88's twelve candidate principles, and proves three compositions on Windows Python 3.12.

**Established facts (cited):** Starlette, Flask, FastAPI, Jinja2, MarkupSafe, Uvicorn, python-multipart, NiceGUI, htmx, Alpine.js, Lit, and Web Awesome core are OSI-licensed and can run on the coach's machine. Each of the first group except Alpine publishes a security policy or GHSA handling. NiceGUI's default bind host is `0.0.0.0` unless native mode; On Air relays UI events through a vendor service. Quart 0.23.1 requires Python ≥3.13. Shoelace is sunset. Motion One's GitHub repo is archived.

**This-ticket analysis (not a lock):** The composition that best preserves the spec-70 test seam (HTTP POST then assert `CuratedStore`), Design map left-click/right-click, print `@page` CSS, 127.0.0.1 bind, and glossary language is **Starlette or Flask + Jinja2 (or htpy) + htmx**, with Alpine.js or Lit as optional progressive enhancement for dialogs and chips. NiceGUI *can* express a spatial studio and a browser print packet, at the cost of bundled Vue/Quasar look, a heavier dependency graph (including FastAPI), and a host default that must be overridden. Streamlit, Dash, and Gradio pass OSI/local-first when cloud share is off; they do not preserve the HTML POST / Design / print packet model. A richer SPA (Preact/Vue/Svelte) was not prototyped because it does not beat progressive enhancement for those four constraints.

No winner is selected. The review child ([Review the UI/UX redesign research and record direction](https://github.com/djsciman/video_transcriber_rag/issues/89)) is the place to grill these candidates.

---

## 2. How this ticket uses issues 87 and 88

This ticket **does not re-derive** visual philosophy or UX heuristics. Grounding files live on sibling research branches and were read with `git show`:

| Source | Path on other branch |
| --- | --- |
| Issue 88 | `research/ux-philosophies-issue-88:docs/ui-ux-discovery/ux-philosophies.md` |
| Issue 87 | `research/ui-tech-visual-issue-87:docs/ui-ux-discovery/tech-visual.md` |
| Issue 88 chrome | `research/ux-philosophies-issue-88:prototypes/ui-ux-redesign/ux-guided.html` |

**From 88, used as the scoring rubric (candidates, not a lock):**

1. Coach language is the system language (`GLOSSARY.md`; coach not user; no vendor/engine).
2. Advisor proposes; coach determines (proposals labeled, reversible, visually distinct from commits).
3. Knowledge in the world (topic, ruleset, store counts, system-chosen, map-ready, sheet mode, missing video, uncategorized count).
4. One activity at a time, whole activity visible (Curate+Place; briefing+system; Design+Convert).
5. Next action is a first-class object.
6. Domain constraints visible (glue, gi/no-gi, uncategorized off lessons, Convert needs named moves).
7. Closure after accept / choose / convert / print.
8. Recognition over recall; accelerators for returning coaches.
9. WCAG POUR as a floor.
10. Forgiving high-cost actions (remove topic / remove citation).
11. Tesler: app holds packing complexity; coach holds decisions.
12. Do not copy a commercial product.

**88 paradigms (one per prototype):** guided next-action; attention inbox + workspace; topic studio with Design map at center.

**From 87, used as implementation needs:** editorial paper/ink; dense productivity; layered dashboard; tokens; focus/hover/busy; empty/error; Design left-click edit / right-click delete; print landscape canvas + portrait class cards 0.5 in; `prefers-reduced-motion`. Tech gist: stdlib HTTP/HTML/`shell.css`/in-page Design JS is **baseline**. Candidates A editorial/stdlib, B tokens+APG, C layered + optional web components. htmx named as strongest JS fit for the HTML/`CuratedStore` POST seam. This ticket supplies implementations, licenses, and security evidence for those sketches.

---

## 3. Methodology, admission filter, sources

### Method

1. Read issue 90, `GLOSSARY.md`, research and prototype skills.
2. Ground against 87/88 via `git show` (those files are not on `implement/spec-70`).
3. Evaluate named libraries against **primary sources**: official docs, LICENSE files, SECURITY.md, GitHub Advisory Database / CVE pages, PyPI metadata, first-party examples.
4. Apply the admission filter. Failures go to section 12 with evidence.
5. Build three throwaway compositions of **non-stdlib Python + JavaScript** under `prototypes/ui-ux-redesign/`. Smoke-run on Windows with `py -3`, bind `127.0.0.1`, in-memory sample data, then stop the servers.
6. Distinguish **established facts** (cited) from **this-ticket analysis**.

Out of scope: editing production `coach_app/`, adding extras to repo-root `pyproject.toml` or `requirements.txt`, locking a stack, re-running visual philosophy research, claiming or editing issue 85.

### Admission filter (every compared library)

1. **Not CPython stdlib.** Stdlib is the baseline column only.
2. **OSI-approved open source** (MIT, BSD, Apache-2.0, MPL-2.0, LGPL, 0BSD, ISC, …). Cite the license URL.
3. **Established security track record:** security policy or private reporting; CVE/GHSA handling if any; maintained releases. OpenSSF Scorecard is a plus; this ticket did **not** scrape Scorecard numbers (honest limit).
4. **Local-first:** can run on the coach's machine without sending curated-store data to a vendor cloud. Optional cloud products (Streamlit Community Cloud, Gradio `share=True`, NiceGUI On Air, Reflex Cloud) fail this clause when enabled; the library may still pass if those modes stay off.

Ranking by GitHub stars is out of scope.

### Primary sources (selected)

**Python hosts / HTML**

- Starlette LICENSE (BSD-3-Clause, Encode OSS Ltd): <https://github.com/Kludex/starlette/blob/main/LICENSE.md>
- Starlette GHSA-82w8-qh3p-5jfq / CVE-2026-54283 (urlencoded `request.form()` limits; patched 1.3.1): <https://github.com/advisories/GHSA-82w8-qh3p-5jfq>
- FastAPI LICENSE (MIT): <https://github.com/fastapi/fastapi/blob/master/LICENSE>
- FastAPI SECURITY.md: <https://github.com/fastapi/fastapi/security>
- FastAPI GHSA-8h2j-cgx8-6xv7 / CVE-2021-32677 (CSRF via JSON in `text/plain`; patched 0.65.2): <https://github.com/advisories/GHSA-8h2j-cgx8-6xv7>
- Flask LICENSE (BSD-3-Clause, Pallets): <https://github.com/pallets/flask/blob/main/LICENSE.txt>
- Pallets security policy: <https://palletsprojects.com/security>
- Flask GHSA-68rp-wp8r-4726 / CVE-2026-27205 (`Vary: Cookie`; patched 3.1.3): <https://github.com/advisories/GHSA-68rp-wp8r-4726>
- Jinja2 GHSA-cpwx-vrp4-4pq7 / CVE-2025-27516 (sandbox `|attr`; patched 3.1.6): <https://github.com/advisories/GHSA-cpwx-vrp4-4pq7>
- MarkupSafe LICENSE (BSD-3-Clause): <https://github.com/pallets/markupsafe/blob/main/LICENSE.txt>
- Uvicorn LICENSE (BSD-3-Clause, Encode OSS Ltd): <https://github.com/Kludex/uvicorn/blob/main/LICENSE.md>
- python-multipart LICENSE (Apache-2.0): <https://github.com/Kludex/python-multipart/blob/main/LICENSE.txt>
- Quart PyPI 0.23.1 (`license_expression` MIT, `requires_python` ≥3.13): <https://pypi.org/pypi/quart/json>
- htpy PyPI 26.5.1 (`license_expression` MIT; MarkupSafe dep; htmx/async): <https://pypi.org/pypi/htpy/json> and <https://htpy.dev>

**Python UI frameworks / shells**

- NiceGUI SECURITY.md: <https://github.com/zauberzeug/nicegui/blob/main/SECURITY.md>
- NiceGUI security practices: <https://nicegui.io/documentation/section_security>
- NiceGUI `ui.run` host / `on_air`: <https://nicegui.io/documentation/section_configuration_deployment>
- NiceGUI GHSA-pq7c-x8g4-rvp6 (patched ≥3.12.0): <https://github.com/zauberzeug/nicegui/security/advisories>
- NiceGUI GHSA-jfrm-rx66-g536 / CVE-2026-45553 (Docutils file insertion; patched 3.12.0)
- NiceGUI GHSA-w8wv-vfpc-hw2w (Windows upload path; patched 3.10.0)
- NiceGUI GHSA-46f2-xhpw-8vh3 and GHSA-955g-h32v-mvrr (patched 3.16.0)
- NiceGUI PyPI MIT classifier: <https://pypi.org/project/nicegui/>
- Reflex LICENSE (Apache-2.0) and intro (compiles to JS / React components): <https://github.com/reflex-dev/reflex/blob/main/LICENSE>, <https://reflex.dev/docs/getting-started/introduction/>
- Streamlit LICENSE (Apache-2.0): <https://github.com/streamlit/streamlit/blob/develop/LICENSE>
- Streamlit Community Cloud (optional vendor deploy): <https://docs.streamlit.io/deploy/streamlit-community-cloud>
- Dash LICENSE (MIT, Plotly): <https://github.com/plotly/dash/blob/dev/LICENSE>
- Gradio LICENSE (Apache-2.0): <https://github.com/gradio-app/gradio/blob/main/LICENSE>
- Flet LICENSE (Apache-2.0): <https://github.com/flet-dev/flet/blob/main/LICENSE>
- pywebview LICENSE (BSD-3-Clause): <https://github.com/r0x0r/pywebview/blob/master/LICENSE>

**JavaScript**

- htmx LICENSE (0BSD): <https://github.com/bigskysoftware/htmx/blob/master/LICENSE>
- htmx SECURITY.md (2.x supported): <https://github.com/bigskysoftware/htmx/blob/master/SECURITY.md>
- Alpine.js LICENSE (MIT): <https://github.com/alpinejs/alpine/blob/main/LICENSE.md>
- Lit LICENSE (BSD-3-Clause): <https://github.com/lit/lit/blob/main/LICENSE>
- Lit SECURITY.md (latest two majors): <https://github.com/lit/lit/blob/main/SECURITY.md>
- Shoelace sunset / migrate to Web Awesome: <https://shoelace.style/>
- Web Awesome LICENSE.md (MIT, Fonticons): <https://github.com/shoelace-style/webawesome/blob/next/LICENSE.md>
- Motion One LICENSE (MIT) and archived 2024-11-12: <https://github.com/motiondivision/motionone>
- d3-force LICENSE (ISC): <https://github.com/d3/d3-force/blob/main/LICENSE>

**OSI identifiers**

- MIT: <https://opensource.org/license/mit>
- BSD-3-Clause: <https://opensource.org/license/bsd-3-clause>
- Apache-2.0: <https://opensource.org/license/apache-2-0>
- 0BSD: <https://opensource.org/license/0bsd>
- ISC: <https://opensource.org/license/isc>

**This-ticket environment (fact):** Windows, `py -3` → Python 3.12.10. Shared throwaway venv at `prototypes/ui-ux-redesign/.venv` (gitignored). Smoke GETs: 8771, 8772, 8773, and `/print` returned HTTP 200, then servers were stopped.

---

## 4. Baseline reminder (stdlib shell)

Issue 87 inspected `implement/spec-70` (`1654281`):

- Entry: `py -3 -m coach_app`
- Server: stdlib `http.server.ThreadingHTTPServer` + `BaseHTTPRequestHandler`
- Bind: default `127.0.0.1:8765`
- One `CuratedStore` from `--location`
- GET full HTML; POST `303` + `Location`; `application/x-www-form-urlencoded`
- CSS: `coach_app/shell.css` inlined
- Design map: in-page JS + SVG in `ui_design.py` (left-click edit, right-click delete)
- Print: `@page` landscape canvas + portrait class cards, 0.5 in
- Tests: HTTP then assert facade (`tests/test_ui_*.py`)
- `pyproject.toml` does not package `coach_app` as a third-party extra; production code uses stdlib plus local modules

Any extra in this ticket is **optional** relative to that baseline. Prototypes must not write production store files and must not land extras in repo-root dependency files.

---

## 5. Track A — non-stdlib Python vs 88 / 87

Scoring keys for this-ticket analysis: **S** strong fit, **M** mixed, **W** weak, **—** not the library's job. License and security columns are established facts.

| Library | Pin / version cited | OSI | Security evidence | Local-first | 88 (1 language, 2 propose/determine, 3 knowledge, 4 one activity, 5 next action, 9 POUR, 10 forgive, 11 Tesler, 12 no clone) | 87 (HTML POST, Design map, print, busy, bind 127.0.0.1) | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **Starlette** | 1.10.0 (prototype 1) | [BSD-3-Clause](https://github.com/Kludex/starlette/blob/main/LICENSE.md) | GHSA-82w8-qh3p-5jfq patched **1.3.1**; 1.10.0 is above that floor | Yes | Host only: S for 2/5/7 if routes stay form-POST HTML; 9 depends on markup; 12 S (no UI kit) | S HTML POST; S print CSS; S bind; Design remains in-page JS | ASGI. Needs Uvicorn + python-multipart for forms. Official examples: <https://www.starlette.io/> |
| **FastAPI** | 0.162.2 arrived as NiceGUI dep | [MIT](https://github.com/fastapi/fastapi/blob/master/LICENSE) | [SECURITY.md](https://github.com/fastapi/fastapi/security); GHSA-8h2j-cgx8-6xv7 patched 0.65.2 | Yes (FastAPI Cloud is optional product) | Same as Starlette for HTML; JSON OpenAPI docs fight principle 1 if exposed to the coach | Same as Starlette if used as HTML host; default docs UI is extra chrome | Built on Starlette. Stronger as an API layer than as a coach HTML shell. |
| **Flask** | 3.1.3 (prototype 3) | [BSD-3-Clause](https://github.com/pallets/flask/blob/main/LICENSE.txt) | [Pallets security](https://palletsprojects.com/security); GHSA-68rp-wp8r-4726 patched **3.1.3** | Yes | Same as Starlette; sync WSGI matches current tests | S HTML POST; S print; S bind (`app.run(host=127.0.0.1)`); debug/reloader must stay off in any coach-facing run ([Pallets: debugger is not a security issue to report](https://palletsprojects.com/security)) | Official: <https://flask.palletsprojects.com/> |
| **Quart** | 0.23.1 | MIT (`license_expression` on PyPI) | Pallets process | Yes | Same as Flask | Same as Flask/ASGI | **`requires_python`: ≥3.13**. Current coach env is 3.12.10. Admitted, not adoptable without a Python bump. |
| **Jinja2** | 3.1.6 | BSD-3-Clause (Pallets) | GHSA-cpwx-vrp4-4pq7 patched **3.1.6** | Yes | S for 1/3 if templates use glossary words; autoescape helps 9 | S HTML generation | Pin ≥3.1.6. Sandbox issue requires attacker-controlled templates. |
| **MarkupSafe** | 3.0.4 | [BSD-3-Clause](https://github.com/pallets/markupsafe/blob/main/LICENSE.txt) | Pallets | Yes | Escaping support for 9 | Required by Jinja2/htpy | |
| **htpy** | 26.5.1 | MIT (PyPI `license_expression`) | No SECURITY.md observed; MarkupSafe for escaping; smaller maintainer surface | Yes | S for typed HTML + htmx partials (first-party claim: “works great with htmx”) | S HTML; not used in the three prototypes | Alternative to Jinja2. <https://htpy.dev> |
| **Uvicorn** | 0.54.0 | [BSD-3-Clause](https://github.com/Kludex/uvicorn/blob/main/LICENSE.md) | Encode/Kludex maintained ASGI server | Yes | — | Bind host/port | Needed by Starlette/NiceGUI |
| **python-multipart** | 0.0.33 | [Apache-2.0](https://github.com/Kludex/python-multipart/blob/main/LICENSE.txt) | Kludex/Starlette form parser | Yes | — | Required for Starlette `request.form()` | |
| **NiceGUI** | 3.19.0 (prototype 2) | MIT | [SECURITY.md](https://github.com/zauberzeug/nicegui/blob/main/SECURITY.md) + private GHSA + nicegui@zauberzeug.com. Pin **≥3.16.0** (GHSA-46f2-xhpw-8vh3, GHSA-955g-h32v-mvrr); also ≥3.12.0 (GHSA-pq7c-x8g4-rvp6, GHSA-jfrm-rx66-g536) and ≥3.10.0 (GHSA-w8wv-vfpc-hw2w Windows path) | Yes **only if** `host=127.0.0.1` and `on_air=False`. Default host is `0.0.0.0`. On Air relays events through on-air.nicegui.io | M: Python UI can speak coach language; Quasar widgets fight 12 unless restyled; busy/propose are Python events not HTML POST | M Design: `ui.splitter`/`ui.tabs`/`ui.html` SVG stand-in proved; real force-graph still custom JS. Print is still the **browser** (`@page` CSS). HTTP tests that POST forms then assert facade do **not** map 1:1 | Bundles Vue + Quasar. Pulls FastAPI/Starlette/Uvicorn. Official: <https://nicegui.io/documentation> |
| **Reflex** | (not installed) | [Apache-2.0](https://github.com/reflex-dev/reflex/blob/main/LICENSE) | GitHub repo + releases; this ticket did not audit every GHSA | Local possible; [Reflex Cloud](https://reflex.dev/docs/hosting/deploy-quick-start/) is a vendor deploy | W–M: compiles frontend to JS/React ([docs](https://reflex.dev/docs/getting-started/introduction/)); wrapping React fights 12 and the HTML POST seam | W for current tests; Design/print would be a React tree | Honest: capable of a studio, expensive lock-in. Not prototyped. |
| **Streamlit** | (not prototyped) | [Apache-2.0](https://github.com/streamlit/streamlit/blob/develop/LICENSE) | Maintained; Community Cloud is optional | Local `streamlit run` is local-first; [Community Cloud](https://docs.streamlit.io/deploy/streamlit-community-cloud) is not | W vs 4/5/11: script-rerun model, not one whole activity + next-action object. Widget language is “user/app” | W Design map / print packet / HTTP facade tests | Data-app chrome. Dropped as a **product UI** candidate (section 12) after honest eval. |
| **Dash** | (not prototyped) | [MIT](https://github.com/plotly/dash/blob/dev/LICENSE) | Plotly-maintained | Local Flask/Werkzeug | W vs 1/12 (Plotly/Dash visual language); callback graph ≠ CuratedStore POST | W print/Design as first-class HTML | Dashboard toolkit. |
| **Gradio** | (not prototyped) | [Apache-2.0](https://github.com/gradio-app/gradio/blob/main/LICENSE) | Hugging Face-maintained | Local yes if `share=False`; `share=True` is a public tunnel | W vs 1/4/12 (ML demo idiom) | W | Dropped as product UI. |
| **pywebview** | (not prototyped) | [BSD-3-Clause](https://github.com/r0x0r/pywebview/blob/master/LICENSE) | Desktop WebView wrapper | Yes (local window) | — shell only | Can wrap any of the HTTP apps; print still the engine; Windows needs WebView2/.NET (NiceGUI native docs note this) | Optional desktop chrome around a local HTTP UI. NiceGUI native mode uses it. |
| **Flet** | (not prototyped) | [Apache-2.0](https://github.com/flet-dev/flet/blob/main/LICENSE) | Flutter-based; GitHub releases | Local desktop/web | W vs 9/print/HTML tests (Flutter controls, not HTML POST) | W Design SVG + `@page` print | Desktop UI, not the HTML/print packet path. |

### Track A analysis (this ticket)

Starlette and Flask are interchangeable HTML hosts for principles 2, 5, 7 and the issue 87 POST seam. FastAPI adds OpenAPI/docs gravity that the coach should never see. Quart is the async Flask twin but needs Python 3.13+. Jinja2 is the proven HTML generator; htpy is an admitted typed alternative aimed at htmx partials. NiceGUI is the honest “Python UI that bundles JS” proof: spatial split and print CSS survive; the HTML test seam and Quasar look do not come for free. Reflex, Streamlit, Dash, Gradio, and Flet are worse fits for Design + briefing + print + facade tests even when they pass OSI/local-first.

---

## 6. Track B — JavaScript vs 88 / 87

| Library | Pin / version cited | OSI | Security evidence | Local-first | 88 | 87 | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| **htmx** | 2.0.11 (prototype 1, jsDelivr throwaway) | [0BSD](https://github.com/bigskysoftware/htmx/blob/master/LICENSE) | [SECURITY.md](https://github.com/bigskysoftware/htmx/blob/master/SECURITY.md): 2.x supported; private GitHub advisory | Yes (file can be vendored) | S 2/5/7 (`hx-post` keeps Accept/Dismiss as form posts); S busy via `hx-indicator`; 9 depends on returned HTML | S HTML/`CuratedStore` POST; S print (full documents still work); Design can stay in-page JS | Issue 87 already named this as strongest JS fit. Official: <https://htmx.org/docs/> |
| **Alpine.js** | 3.14.8 (prototype 3) | [MIT](https://github.com/alpinejs/alpine/blob/main/LICENSE.md) | No SECURITY.md observed at repo root; **no GHSA hits** for `alpinejs` in the GitHub Advisory Database at research time; report via GitHub | Yes | S 3/8 (client filter of chips/queues); S 10 with native `<dialog>`; does not replace server decisions | M: PE on top of Flask POST; dialog is APG-shaped | Official: <https://alpinejs.dev> |
| **Lit** | (not in the three prototypes) | [BSD-3-Clause](https://github.com/lit/lit/blob/main/LICENSE) | [SECURITY.md](https://github.com/lit/lit/blob/main/SECURITY.md): latest two majors; private advisory; 90-day disclosure | Yes | S 9 if components follow APG; M 12 (custom elements, not a product clone) | S for issue 87 candidate C web components; Design map can be a component wrapping existing SVG | Official: <https://lit.dev> |
| **Shoelace** | 2.20.1 still on CDN docs | [MIT](https://github.com/shoelace-style/shoelace/blob/next/LICENSE.md) | Built on Lit; **sunset, no active development** ([shoelace.style](https://shoelace.style/)) | Yes | M 9 (a11y claimed); W 12 (recognizable third-party kit) | Drop for **new** work | Issue 87 already noted sunset toward Web Awesome. |
| **Web Awesome** | core MIT | [MIT](https://github.com/shoelace-style/webawesome/blob/next/LICENSE.md) | Successor to Shoelace; Pro is a **commercial** Font Awesome product | Core: local files. Pro: paid | M 9; W 12 if the kit look ships unmodified | Admitted **core only**. Pro fails OSI-for-the-whole-product | Do not lock. Theme tokens would have to become paper/ink. |
| **Preact / Vue / Svelte** | not prototyped | MIT (typical; not re-fetched per package) | Each has a security process; not the bottleneck | Yes if bundled locally | W vs 11/HTML seam: client state vs facade POST | Beats PE only if Design map needs a reactive graph runtime this ticket did not prove | Issue 90: richer client only if it honestly beats PE. It does not, given print + POST + a11y constraints. |
| **Motion One** | — | [MIT](https://github.com/motiondivision/motionone/blob/main/LICENSE) | Repo **archived 2024-11-12** | n/a | — | Fail admission (abandoned) | Use CSS / Web Animations API + `prefers-reduced-motion` (issue 87). |
| **CSS / WAAPI** | platform | n/a (not a library) | browser | Yes | S 9 with `prefers-reduced-motion` | S busy/focus | Baseline motion. |
| **d3-force** | — | [ISC](https://github.com/d3/d3-force/blob/main/LICENSE) | D3 org; ISC OSI | Yes if vendored | — | Optional physics for Design; issue 87 already has custom SVG | Keep custom SVG unless a later ticket proves force layout needs d3. |
| **Custom SVG + in-page JS** | baseline | n/a | in-repo | Yes | S 6 (named-move vs glue as marks); S 10 (right-click delete with confirm) | S Design left-click / right-click | Remains the Design implementation in prototypes 1 and 3; NiceGUI used an SVG stand-in. |

### Track B analysis (this ticket)

htmx is still the JS that preserves the spec-70 contract. Alpine.js is the light PE layer for inbox filtering and `<dialog>`. Lit is the web-component path if issue 87 candidate C is chosen later. Shoelace is sunset. Web Awesome core is admitted; Pro is not. Motion One is archived. A richer SPA was not justified. d3-force is optional, not required.

---

## 7. Composition recommendations

These are **demonstrations**, not a lock. Each pair is tied to one 88 paradigm and one 87 visual candidate.

### 7.1 HTML-over-the-wire — guided next-action + blue sans shell

- **Python:** Starlette 1.10.0 + Jinja2 3.1.6 + Uvicorn 0.54.0 + python-multipart 0.0.33 + MarkupSafe 3.0.4
- **JS:** htmx 2.0.11
- **Principles shown:** 2 (proposal vs Accept), 3 (chips), 5 (next-action object), 6 (Convert gated on named moves), 7 (feedback after accept/place/convert/print), busy Propose/Convert via `hx-indicator`
- **Official samples:** [Starlette templates](https://www.starlette.io/templates/), [htmx `hx-indicator`](https://htmx.org/attributes/hx-indicator/), [htmx `hx-post`](https://htmx.org/attributes/hx-post/)
- **This ticket:** [`prototypes/ui-ux-redesign/html-over-wire/`](../../prototypes/ui-ux-redesign/html-over-wire/) — http://127.0.0.1:8771/
- **Visual restyle:** shared [`blue_shell.css`](../../prototypes/ui-ux-redesign/blue_shell.css) (navy appbar, ice canvas, Segoe UI / Helvetica / Arial). Distinct from spec-70 cream/serif paper-ink; 88 paradigm is unchanged.

FastAPI could host the same HTML; this prototype used Starlette to keep the extra smaller and to avoid shipping Swagger UI to the coach.

### 7.2 Python UI that bundles JS — topic studio + layered / productivity

- **Python:** NiceGUI 3.19.0 (bundles Vue + Quasar; pulls FastAPI/Starlette/Uvicorn)
- **JS:** not added by this folder; served from the NiceGUI package (`prod_js` defaults true per [config docs](https://nicegui.io/documentation/section_configuration_deployment))
- **Principles shown:** 3 (counts in docks), 4 (Design at center with splitter), 5 (next-action label), 11 (Python holds layout complexity)
- **Honest proof:** `ui.splitter` + `ui.tabs` express a spatial studio. Print is browser `@page` CSS; Quasar chrome is hidden in print. SVG is a **stand-in**, not the spec-70 force-graph. Default `host='0.0.0.0'` was overridden. `on_air=False`.
- **Official samples:** [NiceGUI `ui.splitter`](https://nicegui.io/documentation/splitter), [ui.run host/on_air](https://nicegui.io/documentation/section_configuration_deployment)
- **This ticket:** [`prototypes/ui-ux-redesign/nicegui-studio/`](../../prototypes/ui-ux-redesign/nicegui-studio/) — http://127.0.0.1:8772/

NiceGUI 3.19.0 installed on Windows Python 3.12.10 in this worktree. A 4.x pin was not used (3.19.0 already patches the cited GHSAs through 3.16.0).

### 7.3 Progressive enhancement / APG — attention inbox + productivity tokens

- **Python:** Flask 3.1.3 + Jinja2 3.1.6 + MarkupSafe 3.0.4 + Werkzeug 3.1.9
- **JS:** Alpine.js 3.14.8 (jsDelivr throwaway)
- **Principles shown:** 3 (uncategorized / awaiting / map-ready chips), 8 (filter without leaving the page), 10 (native `<dialog>` confirm for remove-citation)
- **Official samples:** [Flask templates](https://flask.palletsprojects.com/en/stable/quickstart/#rendering-templates), [Alpine `x-data`](https://alpinejs.dev/directives/data), [HTML `dialog`](https://html.spec.whatwg.org/multipage/interactive-elements.html#the-dialog-element)
- **This ticket:** [`prototypes/ui-ux-redesign/flask-alpine-inbox/`](../../prototypes/ui-ux-redesign/flask-alpine-inbox/) — http://127.0.0.1:8773/

Lit + Web Awesome core would be the web-component variant of this composition; Alpine + native dialog was enough to prove PE without a component kit.

---

## 8. Compatibility with CuratedStore, HTTP tests, Design map, print packet, local bind

| Constraint | Stdlib baseline | Starlette/Flask + htmx/Alpine | NiceGUI | Streamlit/Dash/Gradio/Reflex |
| --- | --- | --- | --- | --- |
| One CuratedStore facade | Yes | Yes: keep POST handlers calling the facade | Possible in Python event handlers; **tests that POST HTML forms must be rewritten** as NiceGUI/FastAPI client tests | Poor: widget/callback/session models |
| HTTP tests drive UI then assert facade | Yes today | Yes (303 or htmx fragment + same facade) | Mixed | No without a new harness |
| Design map left-click / right-click | In-page JS | Keep in-page JS (or Lit wrapper) | `ui.html` can host it; prototype used SVG stand-in | Not native |
| Print landscape canvas + portrait cards 0.5 in | CSS `@page` | Same CSS | Same CSS if you inject it; hide Quasar chrome | Framework chrome fights `@page` |
| Bind 127.0.0.1 | Default | Explicit in prototypes | **Must set** `host='127.0.0.1'`; default is `0.0.0.0` | Must audit each runner |
| Coach-only / no vendor cloud | Yes | Yes if JS is vendored in production | Yes if `on_air=False` | Fail if Cloud/share/On Air enabled |
| Windows `py -3` | Yes | Yes (this ticket) | Yes 3.19.0 on 3.12.10 | Not installed here |

Prototypes use `sample_store.py` in-memory data. They **do not** import `coach_app.store` and **do not** write production curated-store files.

---

## 9. Migration / extra-vs-stdlib trade-offs

| Extra | What you gain | What you pay |
| --- | --- | --- |
| Stay stdlib | Zero supply chain; current tests; issue 52/70 “do not name a framework” still holds | Hand-rolled busy indicator, dialogs, fragment updates |
| Starlette or Flask + Jinja2 | Routing, templates, escaping, middleware | One extra family (Encode or Pallets); pin GHSA floors |
| + htmx | Fragment POST, `hx-indicator`, no SPA | Must vendor the file in production; still server-rendered HTML |
| + Alpine or Lit | Client filter, dialog, web components | Second JS pin; Alpine has a thinner published security policy |
| + htpy instead of Jinja2 | Typed HTML, htmx partials in Python | Newer library; thinner security process |
| FastAPI on top of Starlette | OpenAPI, DI | Docs UI and JSON gravity; extra dep; CSRF GHSA is old and patched |
| Quart | Async Flask API | Python ≥3.13 |
| NiceGUI | Python widgets, splitter/tabs, native window option | Vue/Quasar look (principle 12); default 0.0.0.0; On Air footgun; many GHSAs historically (process exists, pin high); HTTP tests change; FastAPI comes along |
| Reflex | Pure-Python React | Compile step, React lock-in, Cloud product |
| pywebview / NiceGUI native | Desktop window | Windows WebView2/.NET; print still the engine |
| Streamlit/Dash/Gradio/Flet | Fast demos | Wrong interaction model for Design + briefing + print |

Production extras, if ever adopted, belong in a **documented optional extra**, not silent repo-root pollution. This ticket added none at repo root.

---

## 10. Risks

| Risk | Evidence | Mitigation (analysis) |
| --- | --- | --- |
| **Lock-in** | NiceGUI/Reflex/Streamlit own the render tree | Prefer HTML-over-the-wire; treat NiceGUI as a studio experiment |
| **Bundled JS** | NiceGUI serves Vue/Quasar; `prod_js` default true | Override tokens; or do not ship Quasar to coaches |
| **Supply chain** | CDN in throwaway prototypes; GHSA floors (Starlette 1.3.1, Flask 3.1.3, Jinja2 3.1.6, NiceGUI 3.16.0) | Vendor JS; pin with hashes; no CDN in production |
| **Windows** | NiceGUI GHSA-w8wv-vfpc-hw2w was a Windows upload path bug; native mode needs WebView2 | Pin ≥3.10.0 (we used 3.19.0); keep uploads off the coach UI if unused |
| **Bind / cloud footguns** | NiceGUI default `0.0.0.0`; On Air; Gradio share; Streamlit Cloud | Force 127.0.0.1; forbid On Air/share in product code |
| **a11y** | POUR is a floor (88.9); kits claim a11y; coach HTML still owns labels | APG dialogs, status chips, no color-only state; test with keyboard |
| **Print** | `@page` is CSS; SPA/Quasar chrome leaks into packets | Dedicated print templates; hide prototype/kit chrome (`display:none` in `@media print`) |
| **Quart Python** | 0.23.1 requires ≥3.13 | Stay on Flask/Starlette while the coach machine is 3.12 |
| **Motion One** | Archived | CSS/WAAPI |
| **Shoelace** | Sunset | Web Awesome core or no kit |
| **htpy security process** | No SECURITY.md observed | MarkupSafe helps; prefer Jinja2 if process weight matters |
| **Alpine security process** | No SECURITY.md; no GHSA hits at research time | Small surface; vendor; watch GHSA |

---

## 11. Preliminary recommendations (candidates, no lock)

For the review child (issue 89), this ticket offers **candidates**:

1. **Default extra if the review wants any extra at all:** Starlette **or** Flask + Jinja2 + vendored htmx. Matches issue 87 S2, issue 88 guided work, HTTP tests, print, Design JS, 127.0.0.1.
2. **PE add-on:** Alpine.js **or** Lit for dialogs, chips, and client filter. Native `<dialog>` before a component kit.
3. **Studio experiment only:** NiceGUI with forced localhost and On Air off. Do not treat Quasar as the product look (principle 12).
4. **HTML generator alternative:** htpy if typed Python HTML + htmx partials beat Jinja2 in a later spike.
5. **Do not adopt as the coach shell:** Streamlit, Dash, Gradio, Flet, Reflex Cloud, NiceGUI On Air, Web Awesome Pro, Shoelace (sunset), Motion One (archived), Quart on Python 3.12.
6. **Design map:** keep custom SVG/in-page JS. Evaluate d3-force only if physics is required.
7. **Motion:** CSS + WAAPI + `prefers-reduced-motion`.
8. **Stay stdlib** remains a valid outcome of issue 89.

No stack is locked. Production `coach_app/` is unchanged.

---

## 12. Considered and dropped

| Item | Why dropped | Evidence |
| --- | --- | --- |
| CPython stdlib as a “library to adopt” | Admission rule 1: stdlib is baseline, not a third-party extra | Issue 87 tech-visual.md; this ticket §4 |
| **Shoelace for new work** | Sunset, no active development; migrate to Web Awesome | <https://shoelace.style/> |
| **Web Awesome Pro** | Commercial Font Awesome product | Product site; core MIT remains admitted |
| **Motion One** | GitHub repo archived 2024-11-12 | <https://github.com/motiondivision/motionone> |
| **Streamlit as product UI** | Script-rerun vs nonlinear Design+briefing; Community Cloud is a vendor path | Apache-2.0 license still passes OSI; fitness fails 88.4/5 and 87 print/Design |
| **Dash as product UI** | Callback dashboard ≠ CuratedStore HTML tests | MIT license; fitness fail |
| **Gradio as product UI** | ML-demo idiom; `share=True` is a public tunnel | Apache-2.0; fitness fail |
| **Reflex as product UI (this round)** | Bundles/compiles React; Cloud product; no prototype (heavy). OSI Apache-2.0 so not a license fail | <https://reflex.dev/docs/getting-started/introduction/> |
| **Flet as product UI** | Flutter controls, not HTML print packet | Apache-2.0 |
| **NiceGUI On Air** | Relays UI events through on-air.nicegui.io | [On Air docs](https://nicegui.io/documentation/section_configuration_deployment#nicegui_on_air) |
| **Quart on current coach Python** | `requires_python >= 3.13`; env is 3.12.10 | PyPI Quart 0.23.1 |
| **Preact/Vue/Svelte as the Design/print runtime** | Does not beat PE for POST + print + a11y in this ticket's proof | Issue 90 richer-client clause |
| **d3-force as required** | Custom SVG already exists; ISC library is optional | Issue 87 Design JS |
| **FastAPI as the coach-facing HTML shell** | Admitted, but OpenAPI/docs UI fights principle 1; Starlette is enough | FastAPI is still the stack under NiceGUI |

Dropped items that **failed the admission filter** (not merely fitness): Shoelace-for-new-work (unmaintained), Motion One (abandoned), Web Awesome Pro (not OSI for the paid kit), NiceGUI On Air / Gradio share / Streamlit Cloud **modes** (not local-first). Streamlit/Dash/Gradio/Flet/Reflex **libraries** pass OSI and can run locally; they are dropped as **coach-app UI** candidates on fitness, not on license.

---

## Appendix A — Prototype runbook (Windows)

From `prototypes/ui-ux-redesign/`:

```
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r html-over-wire\requirements.txt -r nicegui-studio\requirements.txt -r flask-alpine-inbox\requirements.txt
.\.venv\Scripts\python.exe html-over-wire\app.py
.\.venv\Scripts\python.exe nicegui-studio\app.py
.\.venv\Scripts\python.exe flask-alpine-inbox\app.py
```

One composition at a time. Stop with Ctrl+C. Do not leave servers running.

| Composition | URL |
| --- | --- |
| HTML-over-wire | http://127.0.0.1:8771/ |
| NiceGUI studio | http://127.0.0.1:8772/ |
| Flask + Alpine inbox | http://127.0.0.1:8773/ |

Smoke in this worktree: GET `/` on all three and `/print` on 8771 returned HTTP 200 with `PROTOTYPE` and `Coach` in the body; processes were then killed.

## Appendix B — Pins used in throwaway requirements

Do not copy these into repo-root `pyproject.toml`.

- starlette==1.10.0
- jinja2==3.1.6
- uvicorn==0.54.0
- python-multipart==0.0.33
- markupsafe==3.0.4
- nicegui==3.19.0
- flask==3.1.3
- werkzeug==3.1.9
- htmx 2.0.11 (CDN throwaway)
- alpinejs 3.14.8 (CDN throwaway)
