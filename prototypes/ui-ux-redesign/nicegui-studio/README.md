# PROTOTYPE — NiceGUI topic studio (issue 90)

Throwaway. Not production. Topic studio via NiceGUI's bundled Vue + Quasar, restyled with a blue sans-serif shell (`ui.colors` + `../blue_shell.css`).

## What it proves

- A spatial split (Design map vs docks) is expressible in NiceGUI (`ui.splitter`, `ui.tabs`).
- Print is still the **browser**: `@page` CSS can be injected. Quasar chrome is extra to hide.
- Default `ui.run(host=...)` is `'0.0.0.0'` unless native mode; this prototype **forces** `127.0.0.1`.
- `on_air` is off. Enabling it would relay UI events through NiceGUI On Air (not local-first).
- Bundled Quasar look fights issue 88 principle 12 (do not copy a commercial product) unless tokens are overridden.

Honest limit: this is not a force-graph. SVG is a stand-in. A production Design map would still be custom JS inside `ui.html`, or a custom Vue component.

## Run (Windows)

```
py -3 ..\.venv\Scripts\python.exe app.py
```

Open http://127.0.0.1:8772/

Stop with Ctrl+C. Do not leave the process running.

## Third-party Python

| Import | Pin | OSI | Security |
| --- | --- | --- | --- |
| nicegui | 3.19.0 | MIT | https://github.com/zauberzeug/nicegui/blob/main/SECURITY.md ; private GitHub advisory + nicegui@zauberzeug.com. Pin ≥3.12.0 for GHSA-pq7c-x8g4-rvp6 and GHSA-jfrm-rx66-g536; ≥3.10.0 for GHSA-w8wv-vfpc-hw2w (Windows upload path). |

NiceGUI pulls Starlette/FastAPI/Uvicorn/Vue/Quasar as its own stack. Those are bundled-frontend consequences, not extra product decisions.

## Bundled JavaScript (not added by this folder)

Vue + Quasar, served from the NiceGUI package. See https://nicegui.io/documentation/section_configuration_deployment (`prod_js` defaults true).

## 88 / 87 mapping

- Paradigm: topic studio (issue 88 candidate 3)
- Visual: layered dashboard / productivity (issue 87 candidate C)
