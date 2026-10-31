# Sources and license notes

Assembled 2026-10-31 for issue [#25](https://github.com/djsciman/video_transcriber_rag/issues/25).

## Sources used

| Id | Source | License | Role |
| --- | --- | --- | --- |
| `bjj-data` | [bjj-data](https://github.com/grapple-flows/bjj-data) `taxonomy.json` v0.1.0 | [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/) | Primary open vocabulary of position and submission labels and aliases. Local copy: `reference/bjj-data-taxonomy-v0.1.0.json`. Attribution: Data from bjj-data by Grapple Flows (https://grappleflows.com). |
| `wikipedia` | [List of Brazilian jiu-jitsu techniques](https://en.wikipedia.org/wiki/List_of_Brazilian_jiu-jitsu_techniques) | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) | Technique type categories and common named moves. |
| `wikibooks` | [Brazilian Jiu Jitsu: Positional and Technical Guide](https://en.wikibooks.org/wiki/Brazilian_Jiu_Jitsu:_Positional_and_Technical_Guide) | [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/) | Position family outline (pins, guards, submissions). |
| `grapplepedia` | [Grapplepedia](https://jiujitsuauthority.com/grapplepedia/) | All rights reserved (consulted only) | Cross-check of ~35 core positions and move-type groupings. Names rewritten as consensus labels; no wholesale copy. |

## License notes that affect reuse

1. **bjj-data (CC BY 4.0).** Keep attribution when redistributing the reference file or derived vocabulary labels from it.
2. **Wikipedia / Wikibooks (CC BY-SA 4.0).** Share-alike applies to adapted text from those pages. This seed uses short common technique names as consensus labels rather than copying article prose.
3. **Grapplepedia.** Consulted for coverage consensus only. Its site license is not an open reuse grant. Do not treat `seed.json` as a Grapplepedia dump.
4. **BJJGraph** ([bjjgraph.org](https://bjjgraph.org/)) is source-available noncommercial and was **not** copied into this seed.
5. The seed holds **finder-node labels only**. It does not include lesson fields, instructional content, or video.

## Counts in `seed.json`

- 7 move types
- 36 starting positions
- 55 ending positions or submissions
- 100 paths (start → move type → end)
- 139 named-move leaves (`gi` / `no-gi` / `both`)
