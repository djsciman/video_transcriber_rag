# UI technology stack and visual design approaches

Research for [issue 87](https://github.com/djsciman/video_transcriber_rag/issues/87). Parent map: [issue 85](https://github.com/djsciman/video_transcriber_rag/issues/85).

This document evaluates named frontend technologies as **candidates**. It does not lock a stack, a design system, or a visual direction. Standing product rules from issues 52 and 70 still forbid naming a frontend framework, a database engine, or an advisor vendor as the product decision; relaxing that rule is for the review child (issue 89), not this ticket.

The operator of the application is the **coach**. Students never use these screens.

Throwaway prototypes (CDN allowed only there):

- [prototypes/ui-ux-redesign/visual-index.html](../../prototypes/ui-ux-redesign/visual-index.html)
- [prototypes/ui-ux-redesign/visual-editorial.html](../../prototypes/ui-ux-redesign/visual-editorial.html)
- [prototypes/ui-ux-redesign/visual-productivity.html](../../prototypes/ui-ux-redesign/visual-productivity.html)
- [prototypes/ui-ux-redesign/visual-layered.html](../../prototypes/ui-ux-redesign/visual-layered.html)

---

## 1. Existing technical baseline

Inspected on branch `implement/spec-70` (`1654281`) in this worktree. Production `coach_app/` was not modified for this research.

### Runtime and entry

- Entry: `py -3 -m coach_app` (`coach_app/__main__.py` -> `coach_app.app:main`).
- Server: Python stdlib `http.server.ThreadingHTTPServer` + `BaseHTTPRequestHandler` in `coach_app/app.py`.
- Bind: default host `127.0.0.1`, default port `8765`. Local-only.
- Store: one `CuratedStore` opened from `--location` (default `curated-store` next to the process). Persistence is already across runtimes (`CuratedStore.open`).
- Responses: GET returns a full HTML document; POST returns `303` with a `Location`. Forms use `application/x-www-form-urlencoded`.
- CSS: `coach_app/shell.css` is read at import and inlined into every shell (`_CSS = Path(...).read_text(...)`).
- Markup: HTML strings in `render_shell` and per-screen `ui_*.py` modules. Extra per-screen `<style>` blocks are concatenated into the body.

`pyproject.toml` does not package `coach_app` (setuptools include is `bjj_pipeline*` only). The advising package is imported as a local module. At import, `coach_app` uses only the Python standard library plus its own modules (`json`, `pickle`, `html`, `http.server`, `urllib.parse`, `pathlib`, `dataclasses`, `argparse`, `inspect`, `threading`). README states the package does not name a database engine or an application framework.

### Screens (path-based registry)

`SCREENS` in `coach_app/app.py`. Nav labels come from `Screen.label`; empty label hides the item from the top nav.

| Name | Path | Nav label | Module |
| --- | --- | --- | --- |
| home | `/` | Home | `app.py` (`render_home`) |
| settings | `/settings` | (hidden; POST from Home) | `app.py` (`save_settings`) |
| curate | `/curate` | Curate | `ui_curate.py` |
| topic | `/topics` | (hidden; opened from Home) | `ui_topics.py` |
| finder | `/finder` | Finder | `ui_finder.py` |
| place | `/place` | Place | `ui_placement.py` |
| briefing | `/briefing` | (hidden; from topic) | `ui_briefing.py` |
| design | `/design` | Design | `ui_design.py` |
| sheet | `/sheet` | Sheet | `ui_sheet.py` |
| custom | `/custom` | Custom | `ui_library.py` |
| history | `/history` | History | `ui_library.py` |
| print | `/print` | (hidden; from Design/Sheet) | `ui_print.py` |

Home lists topics, opens a topic (name + gi / no-gi), and holds playback folders (video root, transcript folder). Topic resume links Briefing and Design, can remove the topic, and welcomes other-ruleset instructionals.

### Tests

Shell and screen tests drive HTTP, then assert through the facade:

- `tests/test_coach_app_shell.py` — home, settings persistence, catalog seed, no `PROTOTYPE` chrome in product HTML.
- `tests/test_ui_topics.py`, `tests/test_ui_other_ruleset.py`, `tests/test_ui_placement.py`, `tests/test_ui_briefing.py`, `tests/test_ui_design.py`, `tests/test_ui_sheet.py`, `tests/test_ui_library.py`, `tests/test_ui_print.py`.
- Related facade tests without a `test_ui_` prefix: `tests/test_curate.py`, `tests/test_finder.py`.

The test seam is coach-visible HTML + `CuratedStore`. Prototype HTML is not a test harness.

### Animation, visualization, print

- Design map: in-page JavaScript in `ui_design.py` (`_map_script`). SVG force-style layout, pan/zoom, drag, left-click / double-click edit, right-click delete (`contextmenu` -> `delete-{id}` form submit). No third-party graph library.
- Print: browser CSS in `coach_app/print_packet.py` and `ui_print.py`. `@page { margin: 0.5in; }`, `@page canvas { size: letter landscape; margin: 0.5in; }`, `@page class-card { size: letter portrait; margin: 0.5in; }`. Screen CSS hides header/nav on print.

### Visual DNA already in the repo

`coach_app/shell.css` tokens:

```css
:root {
  --bg: #f4f1ea;
  --paper: #fffcf6;
  --ink: #1c1917;
  --muted: #57534e;
  --line: #d6d3d1;
  --accent: #9a3412;
  --shadow: 0 1px 2px rgba(28, 25, 23, 0.06), 0 8px 24px rgba(28, 25, 23, 0.06);
  --serif: "Iowan Old Style", "Palatino Linotype", Palatino, Georgia, serif;
  --sans: "Segoe UI", system-ui, -apple-system, sans-serif;
}
```

Narrow column (`.page { max-width: 52rem }`). Serif `h1`. Paper panels, 8–12px radii, uppercase muted panel titles. Design overrides `.page { max-width: none }` for a full-width canvas. Finder uses a two-column grid. Class cards use a dark cut bar and lesson-type row tints (technique blue, drill yellow, sparring rose, game violet). Existing throwaway prototype `prototypes/enrichment-categories-topic26.html` uses the same paper/ink tokens plus gi / no-gi pills.

Gaps in the live shell (not a value judgment of spec 70, just the visual/tech starting point):

- Almost no `:hover` / `:focus-visible` / `:disabled` / `:active` treatment on buttons and nav.
- No loading indicator for propose-statements, Propose canvas and Draft, Convert, or placement review (full POST round-trip).
- No `prefers-reduced-motion` policy (there is almost no motion).
- Target sizes of compact nav chips and walk buttons may miss [WCAG 2.2 SC 2.5.8](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html) (24×24 CSS px) unless spacing exceptions apply.
- Design drag has no documented non-drag alternative on the canvas itself (WCAG 2.2 SC 2.5.7 Dragging Movements). Forms beside the map do provide single-pointer edit/delete.
- Right-click delete has no keyboard equivalent advertised in the chrome.
- Responsive behavior is wrap-based; Design and Finder become cramped below ~900px; print is specified, screen breakpoints are not.
- Visual regression is not automated; pytest checks strings and store state, not pixels.

---

## 2. Research methodology and sources

### Method

1. Read the live advising package, tests, `GLOSSARY.md`, README, and the existing paper/ink prototype.
2. Evaluate libraries against **this** application's constraints: localhost Python process, one `CuratedStore` facade, HTML-string screens, HTTP-driven tests, stdlib-only import, print packet, in-page Design map, coach-only operator.
3. Prefer primary sources: official library docs, W3C, MDN, first-party design-system sites. Blog roundups were not used as evidence.
4. Score candidates; do not pick a winner. Three throwaway prototypes demonstrate distinct visual **and** implementation approaches.

### Evaluation axes

Compatibility with the curated-store seam; developer experience; maintainability; accessibility; performance; responsiveness (including print); customization; extensibility; ecosystem maturity; documentation; long-term support; implementation complexity; isolation of prototype (and future optional) dependencies from production.

Scores: **H** high / **M** medium / **L** low for this application, not for the industry at large.

### Primary sources

**Platform and a11y**

- [WCAG 2.2](https://www.w3.org/TR/WCAG22/) (W3C Recommendation, 12 December 2024 republication)
- [What's new in WCAG 2.2](https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/)
- [SC 2.5.8 Target Size (Minimum)](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html)
- [WAI-ARIA Overview](https://www.w3.org/WAI/standards-guidelines/aria/) and [WAI-ARIA 1.2](https://www.w3.org/TR/wai-aria-1.2/)
- [ARIA Authoring Practices Guide (APG)](https://www.w3.org/WAI/ARIA/apg/)
- [MDN: prefers-reduced-motion](https://developer.mozilla.org/en-US/docs/Web/CSS/@media/prefers-reduced-motion)
- [MDN: Web Animations API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Animations_API)
- [MDN: View Transition API](https://developer.mozilla.org/en-US/docs/Web/API/View_Transition_API)
- [MDN: CSS custom properties](https://developer.mozilla.org/en-US/docs/Web/CSS/--*)
- [MDN: Using CSS transitions](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_transitions/Using_CSS_transitions)
- [axe-core API](https://www.deque.com/axe/core-documentation/api-documentation/) (Deque)

**HTML-preserving / headless / components**

- [htmx documentation](https://htmx.org/docs/) (v2.0.11 docs at time of research)
- [Alpine.js start here](https://alpinejs.dev/start-here)
- [Lit documentation](https://lit.dev/docs/)
- [Radix Primitives introduction](https://www.radix-ui.com/primitives/docs/overview/introduction)
- [Headless UI](https://headlessui.com/)
- [Shoelace usage](https://shoelace.style/getting-started/usage) (project notes sunset toward [Web Awesome](https://webawesome.com/))
- [Pico CSS docs](https://picocss.com/docs) (project states it is no longer maintained)
- [Open Props](https://open-props.style/)

**Motion, viz, type, icons, test**

- [Motion docs](https://motion.dev/docs) (JavaScript `animate`, not only React)
- [d3-force](https://d3js.org/d3-force)
- [Cytoscape.js](https://js.cytoscape.org/)
- [Lucide (vanilla JS)](https://lucide.dev/guide/packages/lucide)
- [IBM Plex](https://www.ibm.com/plex/)
- [Source Serif (Adobe)](https://github.com/adobe-fonts/source-serif)
- [Playwright visual comparisons](https://playwright.dev/docs/test-snapshots)

**Design-system first parties (characteristics, not skins to copy)**

- [GOV.UK Design System](https://design-system.service.gov.uk/)
- [Carbon accessibility overview](https://www.carbondesignsystem.com/guidelines/accessibility/overview/)
- [Primer](https://primer.style/)

Repo sources: `coach_app/app.py`, `shell.css`, `store.py`, `ui_*.py`, `print_packet.py`, `tests/test_ui_*.py`, `tests/test_coach_app_shell.py`, `prototypes/enrichment-categories-topic26.html`, `GLOSSARY.md`, `README.md`.

---

## 3. Technology comparisons

### 3.1 How any UI stack must sit on the advising package

Non-negotiable for this research:

- Domain writes stay behind `CuratedStore`. Screens must not open a second persistence path.
- Pipeline modules stay on issue 42; they are not a UI concern.
- HTTP tests that POST a form and then assert store records should remain valid, or a parallel seam must be equally coach-visible.
- Optional JS/CSS may be added later only if import of `coach_app` stays stdlib-only **or** the review child explicitly accepts a runtime extra. This ticket does not add production deps.

Implication: a SPA that speaks JSON to a new API would replace the test seam and is a large migration. Progressive HTML (full documents or fragments) keeps the seam.

### 3.2 Component and headless libraries

| Candidate | What it is | Fit notes | Compat | DX | a11y | Isolation | Complexity |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Native HTML + APG patterns | Forms, dialog, menu, tabs from HTML/ARIA | Matches current strings; no new runtime | H | M | H if patterns are followed | H | L–M |
| htmx | HTML attributes issue AJAX; server returns HTML | Fits POST/GET screens; `hx-indicator` for Propose; View Transitions option | H | H for this server | M (author still owns ARIA) | H (one file, or extra) | M |
| Alpine.js | In-page state (`x-data`, `x-show`, `x-transition`) | Good for menus, empty-state toggles, finder filters without a build | H | H | M | H | L |
| Lit | ~5 KB web components, scoped CSS | Could wrap Design map and class cards; still HTML | M | M | M | M (new runtime) | M |
| Shoelace / Web Awesome | Ready-made web components | Fast chrome (dialog, menu, spinner); Shoelace docs say the project is sunset and point to Web Awesome | M | H | M–H | L if CDN; M if vendored | M |
| Radix Primitives | Unstyled accessible widgets | Official install is React (`npm install radix-ui`) | L | H in React | H | L | H |
| Headless UI | Unstyled widgets for React or Vue + Tailwind | Same: requires a JS framework the product currently forbids naming | L | H in that stack | H | L | H |

**Headless vs ready-made.** Headless libraries (Radix, Headless UI) encode APG keyboard and focus behavior and leave paint to the product. They pay off only if the product already has a component runtime. For a Python HTML shell, **copying the APG pattern** (native `<dialog>`, `role="menu"`, combobox) is the headless analog that does not import React. Ready-made web components (Shoelace / Web Awesome) paint faster and risk looking generic unless tokens are overridden.

**htmx** is the closest “named library” to the current architecture: the server still returns HTML, `CuratedStore` stays the writer, and tests can still POST. Official docs: any element can issue any verb; `hx-indicator` / `htmx-request` cover loading; CSS transitions work when element `id`s stay stable across swaps; View Transitions are optional with a fallback.

**Alpine.js** covers the client-only gaps the stdlib shell does not: open/close a Design context menu, announce “proposing…”, filter finder rows, without replacing navigation. It is a script tag, not a build.

**Lit** is a candidate if the review wants a component boundary around Design and class cards while remaining framework-agnostic at the document level.

### 3.3 CSS and styling approaches

| Candidate | Fit | Customization | Maturity / support | Notes |
| --- | --- | --- | --- | --- |
| Current custom properties in `shell.css` | Already shipped | H | H (CSS itself) | Expand tokens; add focus, density, print, reduced-motion |
| Open Props | Token packs (`--size-*`, `--shadow-*`, `--animation-*`, `--motionOK`) | H | H (CSS variables, optional JIT) | Does not impose a look; pairs with either editorial or dense UI |
| Pico CSS | Classless pretty defaults | L | **L — docs: no longer maintained** | Reject as a production basis |
| Utility framework (named only as a candidate) | Fast density | M | H | Would fight HTML-string screens unless compiled; not required |
| Cascade layers + native CSS | Predictable override order | H | H | Good with tokens; no dependency |

Recommendation shape (not a lock): **keep CSS variables as the contract**, whether the values come from a hand-written `shell.css` or from Open Props mapped into the same names (`--ink`, `--paper`, `--accent`). Do not adopt an unmaintained classless sheet as the product skin.

### 3.4 Animation and motion

| Candidate | Role | Reduced-motion | Complexity |
| --- | --- | --- | --- |
| CSS transitions / `@starting-style` | Button press, panel swap, htmx settle | Wrap in `prefers-reduced-motion: reduce { transition: none }` | L |
| Web Animations API | One-off node pops, spinner, toast | Check `matchMedia('(prefers-reduced-motion: reduce)')` | L |
| View Transition API | Home -> topic, Curate proposal swap | Fallback is instant swap (htmx and MDN both document this) | M |
| Motion (JS) `animate()` | Springs, stagger, scroll | Library supports it; still needs a product policy | M |
| Canvas/WebGL motion | Not needed | — | H, reject for this app |

Motion must serve a job: confirm a hit, show that Propose is working, move the coach’s eye to the new Draft. Gratuitous page parallax would fight extended curation and Design sessions.

### 3.5 Icons and typography

**Icons**

- Current: none (text buttons, pills). Fine for a reading-heavy tool.
- [Lucide](https://lucide.dev/guide/packages/lucide): MIT stroke icons, vanilla `createIcons()`, consistent 24px grid that maps to SC 2.5.8 if the hit target is padded.
- System / Unicode: zero dependency, uneven across Windows fonts.
- Octicons (Primer) and Carbon icons: excellent, but they **look like those products**. Avoid as a default if the goal is a distinctive coach tool.

**Type**

- Current stack: Iowan / Palatino / Georgia + Segoe UI. Editorial, already in DNA, no webfont cost.
- [Source Serif 4](https://github.com/adobe-fonts/source-serif) + Source Sans 3: optical sizes for titles vs long cleaned statements; open license; pairs with the paper/ink direction.
- [IBM Plex Sans / Mono](https://www.ibm.com/plex/): designed for dense professional UI; good for a productivity candidate; do not copy Carbon chrome around it.
- Avoid trend display faces and very tight tracking on long statement text.

Webfonts are optional. If used, self-host from the repo (not a production CDN) so localhost stays offline-capable.

### 3.6 Data visualization (mental map)

The live map is custom SVG + a small force/label solver. That is a product asset.

| Candidate | When it earns a place | Cost |
| --- | --- | --- |
| Keep / refine in-page JS | Already encodes mark kinds, pan, drag, right-click delete | Lowest; print SVG can stay in the same model |
| [d3-force](https://d3js.org/d3-force) | If layout quality (collision, link distance) becomes the bottleneck | Small module; still SVG; author keeps hit-testing |
| [Cytoscape.js](https://js.cytoscape.org/) | If the map grows into analysis (compound nodes, many layouts) | Mature, MIT, no deps — heavier than needed for tens of marks |
| Observable Plot / Chart libraries | Wrong shape (charts, not a spatial unit map) | Skip |

Print currently serializes SVG. Any replacement must still emit printable SVG or a static snapshot at Convert / Print time.

WCAG 2.2 SC 2.5.7: dragging a mark must have a single-pointer alternative. The walk/edit forms already do this; a library swap must not drop that.

### 3.7 Responsive layout

Needs:

- **Reading screens** (Home, topic, Curate, Place, Briefing): one column, ~60–72ch measure.
- **Finder**: two panes that stack under ~900px.
- **Design**: canvas full width; tools dock above or in a collapsible rail; not trapped in `max-width: 52rem`.
- **Sheet**: table that can scroll-x on small screens; print uses portrait class cards.
- **Print**: landscape canvas page, portrait class-card pages, 0.5 in margins — already specified; keep `@page` names.

CSS Grid + container queries (optional) beat a layout framework here. No need for a named grid library.

### 3.8 Accessibility tooling

- Authoring: APG patterns, landmarks (`header`, `nav`, `main`), visible `:focus-visible` meeting 3:1 against adjacent pixels ([SC 2.4.13 is AAA](https://www.w3.org/WAI/standards-guidelines/wcag/new-in-22/); still a good target for a dense local tool).
- Automated: [axe-core](https://www.deque.com/axe/core-documentation/api-documentation/) `axe.run` with `wcag22aa` tags, in Playwright or a pytest + browser later. axe does not replace keyboard testing of Design.
- Manual: keyboard-only Design (edit/delete without drag), screen-reader names for marks, color not the only lesson-type cue (pills already duplicate the row tint).

### 3.9 Visual-regression and component docs

- Keep pytest HTTP + store assertions as the **behavior** seam.
- [Playwright `toHaveScreenshot`](https://playwright.dev/docs/test-snapshots) is the first-party candidate for pixels. Official caveat: OS/font/GPU variance; baselines must be taken in one environment. `stylePath` can hide the force graph’s jitter.
- Storybook / Chromatic assume a JS component tree. Low fit until there are components.
- For HTML-string screens, a folder of fixture pages (or the throwaway prototypes) is enough documentation until a stack is locked.

### 3.10 Stack sketches (candidates only)

**S0 — Stay on stdlib HTML/CSS/JS** (prototype: editorial)

Expand `shell.css`, keep form POSTs, keep in-page Design script. Highest compatibility, lowest risk, slowest path to polished menus/loading unless CSS/ARIA is written by hand.

**S1 — Tokens + headless-style patterns, still no production dep** (prototype: productivity)

Same Python shell; APG dialog/menu/tabs; a documented token file; optional Alpine later. Tests unchanged.

**S2 — HTML enhancement library** (htmx ± Alpine)

Same handlers can return fragments; loading indicators for Propose/Convert; View Transitions between topic screens. Adds a JS file (vendored, not CDN) if the review accepts a runtime extra. Store seam unchanged.

**S3 — Web components (Lit or Web Awesome) for chrome only** (prototype: layered)

Design map, dialogs, toasts as components. Python still emits the document. Higher look-and-feel speed, FOUCE and print-shadow-DOM issues to plan for.

**S4 — SPA + JSON API**

Named only to reject for now: would replace the HTTP HTML tests, require a frontend toolchain, and conflict with the current “do not name a framework” product rule until issue 89 says otherwise.

---

## 4. Visual design research

Goal: clean, scannable, comfortable for long curation and Design sessions, distinctive without gimmick, professional without sterile dashboard-clone.

### 4.1 What the current DNA already gets right

Paper ground (`#f4f1ea`) and ink (`#1c1917`) read as a **workbook**, not a marketing site. Serif titles mark “this is a teaching document.” Accent rust (`#9a3412`) is purposeful (links, reasons) rather than a full brand rainbow. Class-card cut bars already feel like printed packets. The Design canvas going full-bleed is the correct exception to the narrow reading column.

Gaps: the shell is visually quiet to the point of unfinished (no focus ring language, no density option, nav chips equal-weight with the page title, Finder and Home share the same cramped column).

### 4.2 Approaches investigated (underlying decisions, not product skins)

**Editorial / typographic (GOV.UK-like discipline, not GOV.UK look).** First-party GOV.UK system emphasizes researched patterns, consistent help placement, and type as the interface. For this app: long cleaned statements, briefing memos, and caveats want a reading measure, strong heading hierarchy, and ink-on-paper contrast — not card grids of equal weight.

**Dense productivity.** Characteristics (not a clone of any commercial IDE): persistent side nav, high information per viewport, sticky context (topic name + ruleset), keyboard. Carbon’s published a11y guidance is useful here: contrast, keyboard, do not rely on color alone — while **not** adopting IBM product chrome.

**Refined dashboard / layered depth.** Primer primitives show how elevation, sticky bars, and quiet borders organize many tools. For Design + Sheet, layering (canvas, then sheet, then a side inspector) beats a single scrolling column. Subtle shadow and one raised surface at a time; no glassmorphism trend.

**Minimalist.** Remove decoration until the next action is obvious. Empty states (“No topics yet.”) already exist; they need a next step, not an illustration.

**Purposeful color.** Lesson types already have tints. Keep a small sequential scale (ink, muted, line, paper, one accent, semantic ok/warn). Gi / no-gi should stay distinct from lesson-type colors (today: gi blue-ish and no-gi violet in the topic-26 prototype). Do not add a sixth accent for decoration.

**Motion.** One 150–250 ms ease for state changes; none for page chrome. Honor `prefers-reduced-motion`.

### 4.3 Extended-use comfort

Curation passes and unit Design are hour-scale. Comfort levers:

- Body size ≥ 16px equivalent, line-height ~1.45–1.6 on statements.
- Avoid pure `#ffffff` walls and pure `#000000` type on long reads (current off-white is better).
- Density toggle (comfortable / compact) would help Finder vs Briefing without two products.
- Sticky topic identity so the coach never loses gi vs no-gi context.
- Do not autoplay motion on the map.

### 4.4 Distinctive without distraction

A coach-only advising application can look like a **typeset studio notebook with a spatial map**, rather than a SaaS analytics console. Distinctive moves that stay quiet:

- Serif for names of topics, systems, and class titles; sans for UI chrome.
- Hairline rules and a single rust accent.
- Map marks already use shape **and** color by type of move — keep both encodings.
- Print packet as a first-class visual: screen class cards should match print cards.

Do not: gradients behind body text, mascot empty states, 202x blob backgrounds, neon dark mode as default.

### 4.5 Three visual directions (prototyped, not ranked)

1. **Paper/ink editorial** — refine what `shell.css` already is. Wide measure, serif titles, quiet nav, print kinship.
2. **Dense productivity** — split panes, tokenized gray scale, IBM Plex, compact tables, inspector pattern.
3. **Layered contemporary** — elevated canvas, docked tools, purposeful motion, web-component chrome.

---

## 5. Recommended design-system characteristics (candidates)

Not a locked system. Any future system for this application should have these properties, which GOV.UK, Carbon, and Primer each document in their own way:

1. **Tokens first.** Color, type, space, radius, shadow, z-index, motion duration as CSS variables. Screens consume tokens, not hex literals (today many `ui_*.py` style blocks hard-code `#fef9c3`, `#1c1917`, etc.).
2. **Semantic color, not rainbow UI.** `ink`, `muted`, `paper`, `line`, `accent`, `ok`, `warn`, `caveat`, plus gi / no-gi. Lesson-type tints stay a closed set.
3. **Two type roles.** Display/serif for topic and class names; UI/sans for controls; optional mono for playback timestamps (already used in Curate).
4. **Density.** Comfortable (Briefing, statements) and compact (Finder walk, Design toolbar). Same components, different spacing tokens.
5. **Focus and target.** Visible focus; 24×24 minimum targets or spacing exception; do not remove outlines.
6. **Landmarks and names.** One `h1`, `nav` with `aria-current="page"` (already present), `main`, labeled regions for map and sheet.
7. **Headless behavior.** Menus, dialogs, tabs follow APG. Styling is separate so editorial and dense skins can share behavior.
8. **Empty, loading, error as first-class.** Copy in the coach’s words (“No topics yet.” / “No first list yet.”) plus the next control.
9. **Print as a surface.** Landscape canvas, portrait class cards, 0.5 in margins, `print-color-adjust: exact` for cut bars (already started).
10. **No third-party look-by-default.** If a component library is adopted, restyle it to the tokens so the app does not look like the library’s demo.

A lightweight token table the review can adopt or rewrite:

| Token | Editorial seed | Productivity seed | Layered seed |
| --- | --- | --- | --- |
| `--bg` | `#f4f1ea` | `#eef0f3` | `#e8eef2` |
| `--paper` | `#fffcf6` | `#ffffff` | `#f7fafb` |
| `--ink` | `#1c1917` | `#12141a` | `#0f1720` |
| `--accent` | `#9a3412` | `#3730a3` | `#0f766e` |
| `--serif` | Iowan / Source Serif | Plex Serif (titles only) | system serif optional |
| `--sans` | Segoe / Source Sans | IBM Plex Sans | system-ui |
| `--radius` | 8–12px | 4–6px | 12–16px |
| `--shadow` | soft paper | hairline + one lift | layered 2–3 elevations |

---

## 6. Recommended interaction and animation practices

Apply regardless of stack. Motion is optional; the state language is not.

### Buttons, hover, focus

- Default, hover, active, disabled, busy. Busy = disable + spinner + accessible name “Proposing statements”.
- `:focus-visible` ring 2px accent on a paper offset (never `outline: none` without a replacement).
- Hover is reinforcement, not the only affordance (keyboard users never see it).

### Loading (the slow advising steps)

| Action | Practice |
| --- | --- |
| Propose statements (Curate) | Immediate busy state on the control; `aria-busy` on the proposal list; keep the volume picker visible |
| Propose canvas and Draft | Disable both Propose and Convert; status text in the prompt panel (“Proposing the Design canvas and Draft…”) |
| Convert canvas to Draft | Same; then scroll/focus the first class card |
| Placement review | Busy on the pass list; do not clear the citation the coach is looking at until the response lands |

htmx `hx-indicator` maps cleanly; stdlib can fake it with a hidden field + CSS if the POST is slow enough to notice. If work is synchronous and fast, still paint a 150 ms minimum busy state so the coach gets confirmation.

### Transitions

- Panel swap: 180 ms fade or 8px slide, only if `prefers-reduced-motion: no-preference`.
- View Transitions (candidate) for Home -> topic resume, with CSS `::view-transition-old/new`.
- Map: node insert scale 0.96 -> 1; no continuous force jitter after settle (print and comfort).

### Scroll

- Reading screens: normal document scroll; no hijack.
- Finder results and placement pass: already `max-height: 70vh; overflow: auto` — keep, add a focusable region name.
- Design canvas: pan inside the stage, not the window. Provide a “reset view” control.

### Navigation feedback

- Keep `aria-current="page"`.
- Stronger current style than a darker border (today’s `nav a[aria-current="page"] { border-color: var(--ink) }` is easy to miss).
- Topic context (name + ruleset pill) sticky on Briefing / Design / Sheet / Print.

### Design map: left-click edit / right-click delete

Live behavior: drag to move; double-click nearby edit; `contextmenu` deletes. Candidates:

- Keep right-click delete **and** add a keyboard path (Delete/Backspace when a mark is selected) plus a visible “Delete” in the inspector.
- Confirm delete (one undo or a dialog) — right-click is too easy on a dense map.
- Do not rely on hover-only tooltips for the gesture legend; put the legend in the toolbar.

SC 2.5.7: inspector buttons satisfy the no-drag alternative if they stay available.

### Empty states

Already in product copy. Visual practice: one sentence + the control that fixes it.

- Home: “No topics yet.” + Open form.
- Design: empty map hint already in CSS `.graph-empty`.
- Finder: uncategorized bucket should look like a **work queue**, not a failure.

### Errors, confirms, notifications

- Form errors: in-page, next to the field, `role="alert"`.
- Destructive (remove topic, delete mark): confirm; do not use browser `alert` as the only path.
- Success: quiet text or a 3s toast; not a modal. Print “opened packet” needs no toast.

### Keyboard

- Tab order follows reading order; map stage is one tab stop with internal arrow handling, or skip-to-inspector.
- Escape closes menus/dialogs.
- Finder walk buttons: arrow keys between siblings (APG toolbar or listbox).

### Responsive and print

- Break around 720px (stack Finder) and 1100px (Design rail beside canvas).
- Print: preserve `@page canvas` landscape and `@page class-card` portrait, 0.5 in margins. Hide prototype chrome (`@media print { .proto-chrome { display: none } }` in throwaways; product already hides header/nav).
- `print-color-adjust: exact` so lesson tints survive.

### Microinteractions worth implementing

- Button active: 1px translateY, 80 ms.
- Accept citation: row flash ok-tint, then collapse.
- Nav current: ink underline grow.
- Propose: spinner in-button, not a full-page replace if fragments are available.

---

## 7. Compatibility and migration considerations

### Stay compatible (any candidate)

- One `CuratedStore` facade; no parallel client cache as source of truth.
- GET/POST screens remain bookmarkable for topics (`/topics?name=&ruleset=`).
- Tests continue to drive HTTP and assert store records.
- `coach_app` import stays stdlib-only until issue 89 says otherwise. Optional JS/CSS files can live beside `shell.css` and be inlined the same way.
- Design map state still round-trips through forms (or htmx posts that hit the same handlers).
- Print CSS remains browser-native.

### Migration ladders (not a schedule)

1. **Tokens + CSS states + APG widgets** inside existing HTML strings. No new dependency. Highest leverage.
2. **Vendor one JS file** (htmx and/or Alpine) inlined like CSS. Handlers may grow fragment responses; full documents still work so old tests pass.
3. **Extract Design map / class cards** as Lit (or similar) components, still fed by server HTML/JSON in a `<script type="application/json">` tag (pattern already used: `#design-state`).
4. Only if 1–3 fail: a named frontend framework and a JSON API — that is a product-rule change for issue 89.

### What would break tests

- Replacing forms with `fetch` JSON and no HTML body.
- Client-only routing with no GET path.
- Shadow DOM that hides button labels from `HTMLParser` in `tests/test_coach_app_shell.py` unless tests move to a real browser.

### Prototype isolation

The three visual files under `prototypes/ui-ux-redesign/` may use CDNs. That is demo-only. Production must not load jsDelivr/unpkg. If a library is later chosen, vendor it in-tree or add an explicit extra — neither is done here.

---

## 8. Risks and trade-offs

| Risk | Why it matters here | Mitigation |
| --- | --- | --- |
| Locking a JS framework | Conflicts with issues 52/70; rewrites tests | Keep S0–S2 available; issue 89 decides |
| Shoelace sunset | Layered prototype uses it via CDN | Treat as stand-in; Web Awesome or Lit if components are wanted |
| Pico unmaintained | Tempting classless skin | Do not use in product |
| CDN in production | Localhost should work offline | Prototypes only |
| Visual regression flakiness | Design force layout jitters | Exclude canvas or freeze seed positions; Playwright `stylePath` |
| Motion vs comfort | Long Design sessions | `prefers-reduced-motion`; no ambient animation |
| Drag-only map | WCAG 2.5.7 | Keep form alternatives |
| Right-click delete | Discoverability + accidents | Legend + confirm + keyboard |
| Webfont licensing / offline | Coach machine may be offline | System stack is valid; self-host if webfonts |
| Shadow DOM vs print | Class cards must print | Render print from light DOM / same CSS as screen cards |
| Token drift | `ui_*.py` hard-coded hex | Central token file |
| Over-building a design system | One coach, one app | Tokens + a dozen patterns, not a public UI kit |
| SPA complexity | Little benefit for form-centric curation | Defer S4 |
| axe-only a11y | Misses map keyboard | Pair with manual scripts |

Trade-off summary: **visual quality is mostly CSS and interaction language**, which S0 can deliver. Libraries buy loading, menus, and motion **faster**, at the cost of a runtime extra and a future support story.

---

## 9. Preliminary technology recommendations (not a lock)

No winner. Issue 89 should compare these with the interaction prototypes (issue 88) and the workflow discovery (issue 86).

### Candidate A — Stdlib HTML/CSS, editorial visual

- **Tech:** Keep `http.server`, HTML strings, expanded `shell.css`, in-page Design JS. APG `<dialog>` and menus by hand.
- **Visual:** Paper/ink, Source Serif or Iowan titles, rust accent, reading measure; Design full-bleed exception.
- **Why it is viable:** Zero runtime risk; tests unchanged; closest to print packet; matches existing DNA.
- **Cost:** Authors write every focus/loading/menu behavior.
- **Prototype:** `prototypes/ui-ux-redesign/visual-editorial.html`

### Candidate B — Design tokens + headless-style patterns, productivity visual

- **Tech:** Still no production dependency. Documented tokens; APG combobox/tabs/dialog in the HTML strings; later optional Alpine. Playwright + axe as **dev** extras, not import-time.
- **Visual:** Dense split panes, IBM Plex, indigo accent, compact Finder/Place, inspector beside Design.
- **Why it is viable:** Biggest UX gain per line of Python; stays inside the current constraint; tokens make a later library restyle cheap.
- **Cost:** Discipline (no hex scatter); some ARIA is easy to get wrong without Radix.
- **Prototype:** `prototypes/ui-ux-redesign/visual-productivity.html`

### Candidate C — Layered dashboard + well-known component/motion library

- **Tech:** Vendored web components (Web Awesome or Lit) and/or Motion `animate()`; htmx optional for Propose indicators. CDN in the throwaway only.
- **Visual:** Elevated canvas, teal accent, purposeful 200 ms motion, docked tools.
- **Why it is viable:** Fastest path to polished dialogs/spinners/toasts; Design feels like a spatial tool.
- **Cost:** Runtime extra; FOUCE; print/shadow DOM; Shoelace-class libraries churn (sunset documented).
- **Prototype:** `prototypes/ui-ux-redesign/visual-layered.html`

### Cross-cutting candidates (compose with A/B/C)

- **htmx** for fragment swaps and `hx-indicator` on Propose/Convert/placement — strongest named-library fit to the HTML seam.
- **Open Props** or a hand-maintained token sheet — styling contract.
- **Lucide** (self-hosted SVG) if icons are wanted; text-only remains valid.
- **Keep custom SVG map**; consider **d3-force** only if layout quality demands it.
- **axe-core + Playwright screenshots** beside pytest, not instead of it.
- **View Transitions API** progressive; CSS fallback.

### Explicitly not recommended as the next product step

- Pico CSS (unmaintained).
- Radix / Headless UI **in product** without first accepting a JS framework (issue 89).
- Cytoscape.js for the current mark count.
- Production CDNs.
- Dark-mode-first trend skins.

### For the review child

Lock **nothing** here. Decide: (1) visual family A/B/C or a hybrid (editorial type + productivity density is a plausible mix); (2) whether a single JS file (htmx/Alpine) is an allowed runtime extra; (3) whether the “do not name a frontend framework” rule stays. Until then, live screens remain the spec-70 stdlib shell.

---

## Appendix: prototype map

| File | Visual | Implementation | CDN |
| --- | --- | --- | --- |
| `visual-editorial.html` | Refined paper/ink | Plain HTML+CSS, stdlib-shaped | None |
| `visual-productivity.html` | Dense productivity | Tokens + APG/headless patterns in one file | None (optional Google Fonts for Plex demo; falls back) |
| `visual-layered.html` | Layered dashboard + motion | Shoelace via CDN + CSS/WAAPI | Prototype-only, documented in-page |
| `visual-index.html` | Index | Links the three | None |

Green dotted outline = proposed coach-final UI. Red dotted outline = prototype chrome. Titles include **PROTOTYPE**.
