# Accessibility numeric targets for a local HTML coach app

Research for [Research: Accessibility numeric targets for a local HTML coach app](https://github.com/djsciman/video_transcriber_rag/issues/138), a child of [Three-job coach UI implementation spec](https://github.com/djsciman/video_transcriber_rag/issues/134).

This document names **candidate** testable numbers from W3C primary sources. It does **not** lock targets. The grilling child [Grilling: Lock accessibility numeric targets](https://github.com/djsciman/video_transcriber_rag/issues/144) is the place to lock.

Live screens stay the spec-70 stdlib HTTP shell. This ticket does not rewrite `coach_app/` UI.

---

## 1. Executive summary

The coach-only advising shell is a local HTML app bound to `127.0.0.1`, used by one person (the coach), with dense productivity screens and a Design force graph. Issue 89 already locked quiet CSS motion (Web Animations API where needed) and honor `prefers-reduced-motion`. Those locks are direction, not numbers.

**This-ticket analysis (not a lock):** WCAG 2.2 Level **AA** is the candidate floor that fits a dense local HTML app. Level AAA as a whole-site policy is not recommended by W3C. Selected AAA numbers can still be candidates where they do not fight density (focus-indicator size; optional 7:1 body text).

| Area | AA floor (candidate) | AAA / stricter option (candidate) | Dense / Design caveat |
| --- | --- | --- | --- |
| Text contrast | 4.5:1 body; 3:1 large text (18 pt / 14 pt bold) | 7:1 body; 4.5:1 large | Do not round 4.499:1 up. |
| Non-text / UI / graph marks | 3:1 against adjacent color | — | Graph lines and node fills required for understanding. |
| Pointer target | 24×24 CSS px, or 24 px-diameter spacing circles that do not intersect | 44×44 CSS px | Dense lists: 24 px + spacing. Graph pins: essential-exception candidate if position is the information; equivalent 24 px chrome still required. |
| Keyboard | All functions via keyboard interface; no trap; visible focus; focused component not entirely hidden | 2 CSS px-thick perimeter focus with 3:1 change of contrast | Tab between composites; arrows inside Design / find lists. Drag is not a keyboard substitute. |
| Motion | Auto-running motion >5 s needs pause/stop/hide; ≤3 flashes / s | Disable non-essential motion animation from interaction | Honor `prefers-reduced-motion: reduce`: stop force ticks; CSS/WAAPI duration 0 or skip. |

No winner is selected.

---

## 2. App context this ticket is scoring against

Established on closed [Review: UI/UX Research Findings, Prototype Evaluation, and Design Decisions](https://github.com/djsciman/video_transcriber_rag/issues/89) (resolution comment [7242517105](https://github.com/djsciman/video_transcriber_rag/issues/89#issuecomment-7242517105)):

- Home is three jobs: Accept, Curate, Build a unit. Dense productivity visual direction.
- Quiet CSS motion; honor `prefers-reduced-motion` (Q23).
- Bind `127.0.0.1`. Coach is the only user of the application. Students are out of scope.
- HTML-over-the-wire extra allowed; Alpine/Lit only for find-list filter and confirm. Design is in-page JS.

Established on closed [Prototype: How the coach designs a unit on the mental map](https://github.com/djsciman/video_transcriber_rag/issues/28): full-width force graph; left-click edits; right-click deletes; add walk family → position → occupancy → type → end → named move.

Local bind and single-user do **not** cancel WCAG success criteria. WCAG 2.2 applies to web content on any device, including desktops ([WCAG 2.2 Abstract](https://www.w3.org/TR/WCAG22/)). What changes is policy: this is not a public site, so a formal conformance claim is optional; the later spec still needs testable numbers so tokens, motion, and Design JS can be checked.

---

## 3. Method and sources

1. Read issue 138, parent map 134, issue 89 resolution, and issue 28 Design lock.
2. Take numbers only from owners: [WCAG 2.2 Recommendation 12 December 2024](https://www.w3.org/TR/WCAG22/), Understanding WCAG 2.2 pages, Techniques, [WAI-ARIA Authoring Practices Guide (APG)](https://www.w3.org/WAI/ARIA/apg/), [CSS Media Queries Level 5](https://www.w3.org/TR/mediaqueries-5/#prefers-reduced-motion).
3. Map each number onto dense productivity chrome versus the Design force graph.
4. Mark analysis that is not in those specs as **this-ticket analysis**.

Out of scope: implementing fixes, locking numbers, rewriting live screens, editing the parent map.

---

## 4. Contrast

### 4.1 Text — SC 1.4.3 Contrast (Minimum), Level AA

Normative ([WCAG 2.2 §1.4.3](https://www.w3.org/TR/WCAG22/#contrast-minimum); [Understanding 1.4.3](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html)):

- Text and images of text: contrast ratio **at least 4.5:1**.
- Large-scale text: **at least 3:1**.
- Exceptions: inactive UI, pure decoration, invisible text, text in a picture with significant other visual content, logotypes.

**Large-scale** (glossary): at least **18 point** or **14 point bold** (or CJK equivalent). Understanding 1.4.3: `1pt = 1.333px`, so 14 pt ≈ **18.5 CSS px** and 18 pt ≈ **24 CSS px**.

**Ratio formula** (glossary *contrast ratio*): `(L1 + 0.05) / (L2 + 0.05)` where L1 is the lighter relative luminance and L2 the darker. Range 1:1 to 21:1.

**Do not round.** Understanding 1.4.3: 4.499:1 does not meet 4.5:1. Same rule for 3:1 on 1.4.11 (2.999:1 fails).

Placeholder text, hover text, and focused text all count.

### 4.2 Text — SC 1.4.6 Contrast (Enhanced), Level AAA

Normative ([WCAG 2.2 §1.4.6](https://www.w3.org/TR/WCAG22/#contrast-enhanced)): **7:1** normal text; **4.5:1** large text.

Understanding 1.4.3 rationale: 4.5:1 compensates roughly for 20/40 acuity; 7:1 for about 20/80. People past that typically use assistive technology with its own contrast tools.

**Candidate for grilling:** AA 4.5:1 as the spec floor (fits dense tokens). AAA 7:1 as an optional body-text stretch, not a whole-app AAA claim. W3C: “It is not recommended that Level AAA conformance be required as a general policy for entire sites” ([Understanding Conformance](https://www.w3.org/WAI/WCAG22/Understanding/conformance.html)).

### 4.3 Non-text — SC 1.4.11 Non-text Contrast, Level AA

Normative ([WCAG 2.2 §1.4.11](https://www.w3.org/TR/WCAG22/#non-text-contrast); [Understanding 1.4.11](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html)):

Visual presentation of the following has contrast ratio **at least 3:1** against adjacent color(s):

- **User interface components:** visual information required to identify the component and its states (except inactive, or unmodified user-agent appearance).
- **Graphical objects:** parts of graphics required to understand the content (except essential presentation).

Focus indicators are in scope of 1.4.11 when the author styles them: the indicator in the focused state must contrast 3:1 with adjacent colors. Hover treatments that are not required to identify the hover state are not in scope of 1.4.11.

**Design graph (this-ticket mapping):** node fills, node outlines, and edges that carry occupancy / type / named-move meaning are graphical objects required for understanding → **3:1 vs adjacent canvas**. If labels sit on the node, those labels are text → 1.4.3. A legend or list that repeats the same information can reduce how much of the drawing must itself meet 3:1, but only if that alternative is actually present.

### 4.4 User preference media: `prefers-contrast`

[CSS Media Queries 5 §12.3](https://www.w3.org/TR/mediaqueries-5/#prefers-contrast): `prefers-contrast` values `no-preference | less | more | custom`. Unqualified `@media (prefers-contrast)` is **incorrect** for applying high-contrast styles, because it also matches people who asked for *less* contrast.

**Candidate:** tokens stay at the WCAG ratios above; optionally add a `prefers-contrast: more` bump. Do not treat Windows forced-colors as a substitute for authored 4.5:1 / 3:1.

---

## 5. Target size

### 5.1 Minimum — SC 2.5.8 Target Size (Minimum), Level AA (new in 2.2)

Normative ([WCAG 2.2 §2.5.8](https://www.w3.org/TR/WCAG22/#target-size-minimum); [Understanding 2.5.8](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html)):

The target for pointer inputs is at least **24 by 24 CSS pixels**, except:

- **Spacing:** undersized targets (< 24×24) are placed so a **24 CSS px diameter circle** centered on each target’s bounding box does not intersect another target or another undersized target’s circle.
- **Equivalent:** a different control on the same page meets the criterion.
- **Inline:** the target is in a sentence, or size is constrained by line-height of non-target text.
- **User agent control:** size is the UA default, unmodified.
- **Essential:** a particular presentation is essential or legally required.

Pass means a **solid 24×24 CSS px square, axis-aligned, completely inside the target**. A 24 px-diameter circle that does not fill that square is *undersized* and must use the spacing exception.

CSS pixels are the CSS reference pixel (visual angle about 0.0213°), not hardware pixels. Zoom does not change CSS px size of an element, so authors cannot claim “it is big enough after the coach zooms.”

Working Group rationale in Understanding 2.5.8: 24 px was chosen for **all pointer modalities** (mouse, trackpad, stylus, touch), not touch-only. 44 px was judged too large as an AA floor.

### 5.2 Enhanced — SC 2.5.5 Target Size (Enhanced), Level AAA

Normative ([WCAG 2.2 §2.5.5](https://www.w3.org/TR/WCAG22/#target-size-enhanced); [Understanding 2.5.5](https://www.w3.org/WAI/WCAG22/Understanding/target-size-enhanced.html)): **44 by 44 CSS pixels**, with equivalent / inline / UA / essential exceptions (no spacing exception).

Understanding 2.5.5 encourages larger than 44 px when the control is frequent, hard to undo, or near a screen edge.

### 5.3 Mapping to dense productivity and Design

**Chrome (job homes, find lists, Save / Save and Accept, next-step, Settings):** candidate AA **24×24 CSS px** for every custom control. Icon-only toolbars that stay under 24 px can pass via the spacing exception if 24 px circles do not collide — Understanding still *encourages* meeting the size, not only the spacing.

**44×44 AAA** fights the locked dense productivity direction on Accept find lists and Named-moves catalog rows. **This-ticket analysis:** treat 44 px as a candidate for high-cost actions only (remove topic, Convert, print), not as the global floor.

**Design force graph:** Understanding 2.5.8 Essential exception explicitly names **digital maps** (pins must sit at the true location) and **interactive data visualizations that are necessarily dense**. A named-move mark whose (x, y) *is* the occupancy on the mental map is a candidate for that exception. The exception is not a free pass:

- Equivalent 24 px controls on the same page (add walk, selected-mark inspector, keyboard move) still have to pass 2.5.8.
- Overlapping marks: overlapping area is not counted toward either target unless both perform the same action ([target definition](https://www.w3.org/TR/WCAG22/#dfn-target)).
- Right-click delete is pointer-specific; a visible equivalent (Delete on the selected mark, or a 24 px delete control) is required for 2.1.1 and helps 2.5.8 Equivalent.

---

## 6. Keyboard

There is no single “keyboard px” number. The testable claims are presence, order, visibility, and (at AAA) focus-indicator geometry.

### 6.1 Operable — SC 2.1.1 Keyboard, Level A

Normative ([WCAG 2.2 §2.1.1](https://www.w3.org/TR/WCAG22/#keyboard); [Understanding 2.1.1](https://www.w3.org/WAI/WCAG22/Understanding/keyboard.html)):

All functionality is operable through a **keyboard interface** without requiring specific timings for individual keystrokes, except where the underlying function requires **path-dependent** input (not just endpoints).

MouseKeys does **not** satisfy this SC. Dragging an object to a location when the path is irrelevant is **not** path-dependent (Understanding example: drawing programs size/position/rotate from the keyboard; drag-and-drop also supports cut/paste or form controls).

**Design mapping:** placing a mark, choosing occupancy, editing, and deleting are endpoint operations → keyboard required. Freehand sketching of a path would be the exception; this app does not do that.

### 6.2 No trap — SC 2.1.2 No Keyboard Trap, Level A (non-interference)

Normative ([WCAG 2.2 §2.1.2](https://www.w3.org/TR/WCAG22/#no-keyboard-trap); [Understanding 2.1.2](https://www.w3.org/WAI/WCAG22/Understanding/no-keyboard-trap.html)):

If focus can move to a component via a keyboard interface, it can move away using only a keyboard interface. If that needs more than unmodified arrow/Tab or other standard exit methods, the user is told the method.

Modal inner Accept / Curate flows (issue 89 dual job signal) may trap focus **inside the dialog** if Esc / Cancel / OK return focus to the trigger. A canvas that swallows Tab with no documented exit fails.

This SC is in **Conformance Requirement 5: Non-Interference**: even non-relied-upon content must not trap ([Understanding Conformance](https://www.w3.org/WAI/WCAG22/Understanding/conformance.html)).

### 6.3 Focus visible — SC 2.4.7, Level AA

Normative ([WCAG 2.2 §2.4.7](https://www.w3.org/TR/WCAG22/#focus-visible); [Understanding 2.4.7](https://www.w3.org/WAI/WCAG22/Understanding/focus-visible.html)):

Any keyboard-operable UI has a mode of operation where the keyboard **focus indicator is visible**. It must not be time-limited.

No thickness is specified at AA. Author-styled indicators also have to meet 1.4.11 (3:1 adjacent contrast). Do not `outline: none` without a replacement ([failure F78](https://www.w3.org/WAI/WCAG22/Techniques/failures/F78)).

### 6.4 Focus not obscured — SC 2.4.11, Level AA (new in 2.2)

Normative ([WCAG 2.2 §2.4.11](https://www.w3.org/TR/WCAG22/#focus-not-obscured-minimum); [Understanding 2.4.11](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html)):

When a component receives keyboard focus, it is **not entirely hidden** due to author-created content. Partial covering is allowed at AA. AAA 2.4.12 requires no covering at all.

Sticky job-signal chrome, next-step rails, and cookie-like banners are the usual failures. CSS `scroll-padding` is a documented technique ([C43](https://www.w3.org/WAI/WCAG22/Techniques/css/C43)).

### 6.5 Focus appearance — SC 2.4.13, Level AAA (new in 2.2)

Normative ([WCAG 2.2 §2.4.13](https://www.w3.org/TR/WCAG22/#focus-appearance); [Understanding 2.4.13](https://www.w3.org/WAI/WCAG22/Understanding/focus-appearance.html)):

When the keyboard focus indicator is visible, an area of it:

1. is at least as large as a **2 CSS pixel thick perimeter** of the unfocused component (or sub-component), and
2. has contrast ratio **at least 3:1** between the **same pixels** in focused vs unfocused states.

A solid 2 px outline is the simplest pass. Inset 2 px lines that do not sit on the outer edge fail size; they need to be thicker. Change-of-contrast (2.4.13) is not the same measurement as adjacent contrast (1.4.11); both can apply.

**Candidate:** adopt 2.4.13 numbers as the **author-supplied focus token** even if the spec does not claim whole-app AAA. Dense screens need a strong indicator more than they need AAA target size.

### 6.6 APG keyboard conventions (informative, not numeric)

[APG: Developing a Keyboard Interface](https://www.w3.org/WAI/ARIA/apg/practices/keyboard-interface/):

- **Tab / Shift+Tab** move between UI components; **arrow keys** move inside composites (radio groups, tablists, menus, grids, trees).
- Only one radio/tab/option from a composite sits in the tab sequence.
- Visual focus indicator always visible; **selected** state visually distinct from **focus**.
- Do not use `tabindex` to reorder the tab sequence; DOM order is the sequence.
- After closing a dialog or deleting a list item, restore focus to the trigger or the next item — do not drop to `body`.

**This-ticket mapping:**

| Surface | APG composite candidate |
| --- | --- |
| Accept find list | Grid or listbox: Tab onto the list, arrows between rows, Enter opens the row. |
| Named-moves catalog | Tree view: Right expands, Left collapses (APG tree convention). |
| Inner Accept / Curate | Modal dialog: focus in, Esc out, return to invoker ([Dialog Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/)). |
| Design canvas | One tab stop for the graph; arrows move among marks; Enter edits; Delete removes; separate 24 px add-walk chrome in the tab sequence. |

### 6.7 Dragging — SC 2.5.7 Dragging Movements, Level AA (new in 2.2)

Normative ([WCAG 2.2 §2.5.7](https://www.w3.org/TR/WCAG22/#dragging-movements); [Understanding 2.5.7](https://www.w3.org/WAI/WCAG22/Understanding/dragging-movements.html)):

Functionality that uses a dragging movement can also be achieved by a **single pointer without dragging**, unless dragging is essential or is UA-provided (native scrollbars).

Keyboard access (2.1.1) does **not** automatically pass 2.5.7. The alternative must be click/tap (or a text field). Examples: click a track instead of dragging a thumb; select then arrow-button; click-corner then click-opposite-corner.

**Design mapping:** if the coach repositions a mark by dragging, provide a non-drag pointer path (select mark + nudge buttons, or click-to-place). Path-based “must follow the edge” gestures would also fail 2.5.1 Pointer Gestures.

---

## 7. Reduced motion and related time limits

### 7.1 CSS `prefers-reduced-motion` (the feature issue 89 named)

[CSS Media Queries Level 5 §12.1](https://www.w3.org/TR/mediaqueries-5/#prefers-reduced-motion) (Working Draft 19 February 2026; this is the CSSWG owner of the feature):

| Name | `prefers-reduced-motion` |
| --- | --- |
| For | `@media` |
| Value | `no-preference` \| `reduce` |
| Type | discrete |

- **`no-preference`:** user has made no preference known. Evaluates **false** in a boolean context.
- **`reduce`:** user prefers an interface that removes or replaces motion-based animation that triggers vestibular discomfort or attention distraction.

User agents must re-evaluate media queries when the environment changes.

Issue 89 lock is “honor `prefers-reduced-motion`.” The spec-level test is: when the OS/UA reports `reduce`, non-essential motion is gone.

### 7.2 Technique C39 (sufficient for 2.3.3)

[C39: Using the CSS prefers-reduced-motion query to prevent motion](https://www.w3.org/WAI/WCAG22/Techniques/css/C39):

```css
@media (prefers-reduced-motion: reduce) {
  /* disable motion */
}

@media (prefers-reduced-motion: no-preference) {
  /* motion only when the user did not ask to reduce */
}
```

Test: enable the system reduced-motion setting; for each interactive motion, either the animation is essential **or** it is suppressed.

JavaScript equivalent is documented as [SCR40](https://www.w3.org/WAI/WCAG22/Techniques/client-side-script/SCR40) (`matchMedia('(prefers-reduced-motion: reduce)')`) — the owner for WAAPI / force-sim ticks.

### 7.3 Animation from interactions — SC 2.3.3, Level AAA

Normative ([WCAG 2.2 §2.3.3](https://www.w3.org/TR/WCAG22/#animation-from-interactions); [Understanding 2.3.3](https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html)):

**Motion animation** triggered by interaction can be disabled, unless essential.

Glossary *motion animation*: steps between conditions that create the illusion of movement or a smooth transition. Instant appear is not animation. Color, blur, or opacity that do **not** change perceived size, shape, or position are excluded (errata notes blurring).

Understanding: scrolling new content into view is essential; parallax and decorative transitions are not. Honor OS reduce-motion is one listed solution.

**Candidate:** treat 2.3.3 as in-scope for the spec even though it is AAA, because issue 89 already locked honor `prefers-reduced-motion`. Quiet CSS / WAAPI motion is the no-preference path; `reduce` is duration 0 / skip / instant cut.

### 7.4 Pause, Stop, Hide — SC 2.2.2, Level A (non-interference)

Normative ([WCAG 2.2 §2.2.2](https://www.w3.org/TR/WCAG22/#pause-stop-hide); [Understanding 2.2.2](https://www.w3.org/WAI/WCAG22/Understanding/pause-stop-hide.html)):

For moving, blinking, scrolling, or auto-updating information:

- **Moving / blinking / scrolling** that (1) starts automatically, (2) lasts **more than five seconds**, and (3) is presented in parallel with other content: mechanism to **pause, stop, or hide**, unless essential.
- **Auto-updating** that starts automatically and is in parallel: pause/stop/hide **or** control frequency, unless essential.

**Five seconds** is the numeric threshold. Hover-to-pause that resumes when focus leaves is **not** a pause mechanism.

**Design mapping:** a force simulation that keeps ticking after load, beside the add-walk chrome, is auto-running motion in parallel with other content. Candidates that pass 2.2.2:

- Simulation settles in ≤5 s, then static; or
- Explicit Pause / Freeze on the canvas; or
- Under `prefers-reduced-motion: reduce`, skip simulation and place marks with a static layout (also 2.3.3 / C39).

A preload spinner that is the only content on the page is excepted (Understanding 2.2.2).

### 7.5 Three flashes — SC 2.3.1, Level A (non-interference)

Normative ([WCAG 2.2 §2.3.1](https://www.w3.org/TR/WCAG22/#three-flashes-or-below-threshold); [Understanding 2.3.1](https://www.w3.org/WAI/WCAG22/Understanding/three-flashes-or-below-threshold.html)):

Pages do not contain anything that flashes **more than three times in any one-second period**, or the flash is below the general / red flash thresholds.

Simplest pass: **≤3 flashes per second** ([G19](https://www.w3.org/WAI/WCAG22/Techniques/general/G19)). Quiet CSS motion should stay well under this. Do not blink Save / next-step affordances at 3 Hz or faster.

Area threshold (if someone later adds video or GIF): combined concurrent flashes occupy no more than 0.006 steradians in a 10° field; Understanding approximates **341 × 256 CSS px** (87,296 CSS px) as 10° at typical distance.

---

## 8. Other numeric AA criteria that will show up in tokens / layout

These are not in the ticket’s four named buckets, but they are testable numbers the later spec will hit if it claims WCAG 2.2 AA.

### 8.1 Resize text — SC 1.4.4, Level AA

[Understanding 1.4.4](https://www.w3.org/WAI/WCAG22/Understanding/resize-text.html): text (except captions and images of text) can be resized without AT up to **200 percent** without loss of content or functionality. 200% means twice width and height. Do not block user-agent zoom (`user-scalable=no` / `maximum-scale=1` fails related ACT rule [b4f0c3](https://www.w3.org/WAI/standards-guidelines/act/rules/b4f0c3/)).

### 8.2 Reflow — SC 1.4.10, Level AA

[Understanding 1.4.10](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html): content without two-dimensional scrolling at **320 CSS px** width (vertical-scroll pages) or **256 CSS px** height (horizontal-scroll pages). 320 px ≡ 1280 px viewport at **400%** zoom.

**Exception:** parts that need two-dimensional layout for usage or meaning: images required for understanding (maps, diagrams), video, data tables, **interfaces that must keep toolbars in view while manipulating content**. Understanding’s photo-editor example matches Design: a fixed canvas plus persistent toolbars may two-axis-scroll the canvas; the add-walk / inspector chrome around it still reflows.

**This-ticket analysis:** do not promise a 320 px phone layout as a product goal (coach machine, dense productivity). Do promise that browser zoom to 400% on a 1280-wide window does not clip Accept lists or trap the coach in two-axis scroll for ordinary HTML chrome. The graph itself is excepted as a diagram.

### 8.3 Text spacing — SC 1.4.12, Level AA

[Understanding 1.4.12](https://www.w3.org/WAI/WCAG22/Understanding/text-spacing.html): no loss of content or functionality when the user sets **all** of:

- line height ≥ **1.5×** font size
- paragraph spacing after ≥ **2×** font size
- letter spacing ≥ **0.12×** font size
- word spacing ≥ **0.16×** font size

Authors are **not** required to ship those values. They must not clip or overlap when a user stylesheet / bookmarklet applies them. Canvas text is treated as images of text and is out of this SC.

---

## 9. What “local, coach-only, dense” does and does not change

| Fact | Effect on candidates |
| --- | --- |
| Bind `127.0.0.1`; not a public site | Formal WCAG claim optional. Numbers stay useful as spec tests. |
| One coach | Still keyboard, contrast, vestibular, tremor, low vision. Do not drop 2.1.1 because “the coach has a mouse.” |
| Dense productivity (issue 89 Q5) | Prefer **24 px** AA targets over **44 px** AAA as the global floor. |
| Design force graph (issue 28) | Essential-exception **candidate** for 2.5.8 node size; **not** an exception for 2.1.1, 2.5.7, 1.4.11, or reduced motion. |
| Quiet CSS + WAAPI (issue 89 Q23) | Motion budget is already “little.” Numeric tests: `prefers-reduced-motion: reduce` ⇒ no position/size animation; auto-run force sim ≤5 s or pausable; flash ≤3 / s. |
| Find lists + inner dialogs | APG grid/listbox + modal dialog; 2.4.11 so sticky job chrome does not fully cover the focused row. |

---

## 10. Candidate package for grilling (not a lock)

Grill these as yes/no. Wording is a recommendation, not a decision.

1. **Conformance grain:** spec cites WCAG 2.2 **Level AA** as the accessibility floor, plus the issue-89 reduced-motion lock, **without** claiming whole-app AAA.
2. **Text contrast:** **4.5:1** (normal), **3:1** (large ≥18 pt / 14 pt bold). Measure authored CSS colors; do not round.
3. **Non-text contrast:** **3:1** for component boundaries/states and for Design marks/edges required for understanding.
4. **Targets:** custom chrome **24×24 CSS px** (or 24 px spacing exception). **44×44** only if grilling wants it for irreversible actions.
5. **Design nodes:** allow 2.5.8 **Essential** for densely placed marks whose position is the information, **if** the same page has equivalent 24 px / keyboard / non-drag controls for add, select, move, edit, delete.
6. **Keyboard:** every job action (including graph place/edit/delete and Convert) has a keyboard path; Tab between composites; arrows inside; no trap; focus visible; focused control not entirely hidden by sticky chrome.
7. **Focus token (AAA numbers used at AA ambition):** author-supplied indicator ≥ **2 CSS px** perimeter area and **3:1** change-of-contrast (2.4.13) **and** 3:1 adjacent (1.4.11).
8. **Reduced motion:** on `(prefers-reduced-motion: reduce)`, CSS transitions/animations that change position or size are disabled (C39); WAAPI and the force simulation read `matchMedia` (SCR40) and skip or freeze. On `no-preference`, keep quiet motion.
9. **Auto-run motion:** force layout that would run >**5 s** beside other chrome is pausable/stoppable (2.2.2) or finishes ≤5 s.
10. **Flash:** nothing flashes more than **3 times per second** (2.3.1).
11. **Zoom / spacing (if AA is the floor):** text resize **200%**; reflow chrome at **320 CSS px** with Design canvas excepted; user text-spacing override (1.5 / 2.0 / 0.12 / 0.16) does not clip.

---

## 11. Sources

Primary (owners of the numbers):

- [Web Content Accessibility Guidelines (WCAG) 2.2](https://www.w3.org/TR/WCAG22/), W3C Recommendation 12 December 2024.
- Understanding: [1.4.3](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html), [1.4.4](https://www.w3.org/WAI/WCAG22/Understanding/resize-text.html), [1.4.10](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html), [1.4.11](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html), [1.4.12](https://www.w3.org/WAI/WCAG22/Understanding/text-spacing.html), [2.1.1](https://www.w3.org/WAI/WCAG22/Understanding/keyboard.html), [2.1.2](https://www.w3.org/WAI/WCAG22/Understanding/no-keyboard-trap.html), [2.2.2](https://www.w3.org/WAI/WCAG22/Understanding/pause-stop-hide.html), [2.3.1](https://www.w3.org/WAI/WCAG22/Understanding/three-flashes-or-below-threshold.html), [2.3.3](https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html), [2.4.7](https://www.w3.org/WAI/WCAG22/Understanding/focus-visible.html), [2.4.11](https://www.w3.org/WAI/WCAG22/Understanding/focus-not-obscured-minimum.html), [2.4.13](https://www.w3.org/WAI/WCAG22/Understanding/focus-appearance.html), [2.5.5](https://www.w3.org/WAI/WCAG22/Understanding/target-size-enhanced.html), [2.5.7](https://www.w3.org/WAI/WCAG22/Understanding/dragging-movements.html), [2.5.8](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html), [Conformance](https://www.w3.org/WAI/WCAG22/Understanding/conformance.html).
- Techniques: [C39](https://www.w3.org/WAI/WCAG22/Techniques/css/C39), [SCR40](https://www.w3.org/WAI/WCAG22/Techniques/client-side-script/SCR40), [C43](https://www.w3.org/WAI/WCAG22/Techniques/css/C43), [G19](https://www.w3.org/WAI/WCAG22/Techniques/general/G19).
- [CSS Media Queries Level 5 §12.1 prefers-reduced-motion](https://www.w3.org/TR/mediaqueries-5/#prefers-reduced-motion).
- [WAI-ARIA APG: Developing a Keyboard Interface](https://www.w3.org/WAI/ARIA/apg/practices/keyboard-interface/), [Dialog (Modal) Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/).

Repo direction (not numeric owners):

- Issue 89 resolution: https://github.com/djsciman/video_transcriber_rag/issues/89#issuecomment-7242517105
- Issue 28 Design interaction (force graph, left-click edit, right-click delete).
- Issue 138 question; parent map 134 destination (a11y numeric targets on the written spec).
