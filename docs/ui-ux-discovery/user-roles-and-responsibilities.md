# Roles and responsibilities

Language is [`GLOSSARY.md`](../../GLOSSARY.md). This file does not redefine those terms.

## Roles

| Actor | Uses the application? | Responsibility | Status |
| --- | --- | --- | --- |
| **Coach** | Yes. The only person who uses the application. | Decides what a student trains and how. Curates citations, determines the system, designs the unit, packs classes, teaches from the sheet, prints the packet. | **Required** — glossary Coach; issue 52 stories 1-2; issue 70 stories 1-3 |
| **Student** | Never. | Performs the topic under resistance in class. Does not query the application. | **Required** — glossary Student; issue 52 story 1; issue 70 story 1 |
| **Instructor** | Never. | Teaches on an instructional. Speech becomes cleaned statements the coach accepts. | **Required** — glossary Instructor |
| **Advisor** | Not a person. Part of the application. | Reads the curated store. Proposes cleaned statements, placement, briefing, Design/Draft packing. Leaves the system to the coach. Does not advise from raw JSON or the video file. | **Required** — glossary Advisor; issue 52 implementation decisions |

Avoid: user (except the ticket phrase "user journey"), instructor-as-coach, athlete, chatbot, bot, model.

**Inferred:** there is one coach on one machine. Multi-coach and multi-machine sync are out of scope (issue 70).

## Coach responsibilities the interface must support

The coach **must** do these acts. The advisor may propose; the coach accepts, corrects, dismisses, or replaces.

### Explicit coach control (**Required**)

- Accept or dismiss each proposed cleaned statement. Dismiss stores nothing.
- Correct move name and step bullets before and after accept.
- Remove an accepted citation that cannot be repaired.
- Mark an other-ruleset aside on a showing.
- Welcome each matching instructional of the other ruleset with yes or no.
- Open a topic by submitting a kept name and gi or no-gi; remove a topic.
- Determine the system as the coach's words. Instructionals seed it; the coach's experience is part of it; an instructor's method may be the whole system when it fits.
- Set aside an earlier same-ruleset system and put it back.
- Organize the live enrichment catalog (add, rename, move, delete).
- Accept, correct, or skip each placement proposal. Skip leaves the citation uncategorized.
- Write coach-authored citations (movement name + step bullets, no playback).
- Place marks on the Design map, choose already-linked citations on a mark, write coach notes on a mark.
- Write the unit paragraph (Propose prompt or hand-build descriptor).
- Choose Propose vs Convert vs refuse (empty map cannot Convert).
- Edit the sheet: add/remove/drag, purpose lines, partner-job / scenario / condition text.
- Place other-ruleset citations into a lesson explicitly; welcomed series do not pack themselves.
- Create, edit, delete Custom lessons; copy a unit from history.
- Teach from Read mode; print the duplex packet.
- Set video root and transcript folder.
- Watch corpus video via playback when the file exists.

### Advisor proposes; coach still decides (**Required**)

| Automation | Coach decision |
| --- | --- |
| Clean-up nests speech under chapters | None at this step; the coach then reviews proposals. Untitled parts stay unciteable until movements are marked. |
| Propose cleaned statements | Correct / accept / dismiss |
| Placement pass | Accept / correct named-move / skip |
| Briefing memo (same-ruleset citations, other-ruleset caveat, disagreement) | Watch, compare, then determine the system |
| Propose packing (paragraph -> canvas + Draft) | Keep, then Edit |
| Convert packing (hand-built canvas -> Draft) | Keep, then Edit |
| Partner-job stubs on first Draft | Coach writes or keeps the stub |

### Advisor must not do (**Required**)

- Advise from raw volumes or the video file.
- Re-scrape enrichment or overwrite catalog edits with a second seed import.
- Pack other-ruleset citations into a lesson without the coach placing them.
- Split classes on the briefing.
- Pack classes on Design.
- Pick a winner across rulesets.
- Rename an open topic.
- Mix unrelated topics into a weekly calendar.
- Store disagreement as a topic record, or store the clean-up part list.
- Store Read-mode checkboxes or the success-watch clipboard.

## Other actors (not application users)

- **Pipeline operator** is the same coach off-application: corpus-prep (issue 42) produces completed volume JSON. The advising UI consumes those files. **Required** as an external dependency, not as an in-app role.
- **Stand-in advisor** in tests and `coach_app` does not name a vendor. **Required** (issues 52, 70 testing decisions).

## Capabilities by actor (summary)

See [requirements-inventory.md](requirements-inventory.md) for the full functional list. The coach has every write capability. The advisor has read + propose. The student has none.
