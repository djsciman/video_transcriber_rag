# Extracted-technique counts in the prepared corpus

Count for GitHub issue [#105](https://github.com/djsciman/video_transcriber_rag/issues/105). Scanned 2026-11-19. `py -3` walked every `*.json` under the named library with Windows long-path (`\\?\`) opens. No ingest. No Ollama.

## Path scanned

| Path | Present |
|---|---|
| `C:\Users\dumbo\Documents\GitHub\bjj_transcripts\library` | yes (this scan) |
| `C:\Users\dumbo\Documents\GitHub\djsciman_data_projects\video-transcriber\library` | no |

Repo sample `docs/samples/butterfly-marcelo-s01e01-pare.json` is not in the corpus library and was not counted.

## Headline

| Measure | Count |
|---|---|
| JSON files (all are volume JSON) | 529 |
| JSON volumes (`chapters` key present, list) | 529 |
| Instructional folders | 78 |
| Chapters | 4516 |
| Extracted-technique objects (chapter `techniques` arrays) | 0 |
| Chapters with a non-empty `techniques` array | 0 |
| Chapters with an empty `techniques` array | 0 |
| Chapters missing the `techniques` key | 4516 |
| Starred hop-field values (string ending in `*`) | 0 |
| Parse errors | 0 |

The coach corpus currently has **no extracted-technique rows**. Every chapter is missing `techniques`. Empty arrays are therefore also 0.

## Hop starring

Hop fields counted, matching `docs/prepare-llm-prompt.md` and the Marcelo sample:

`named_move`, `ruleset`, `move_type`, `start_occupancy`, `start_position`, `end_occupancy`, `end_position`

A starred value is a string that ends in `*` with no space. Because there are no technique objects, every hop field is 0 starred / 0 plain / 0 empty / 0 missing.

## Chapter speech (not extract rows)

These keys are not extract rows. They show how far prepare has gotten on disk.

| Measure | Count |
|---|---|
| Volumes with nested chapter keys (`instructor`, `instructional`, `volume`, `previous_chapter`, `next_chapter`, `transcript_raw`) | 419 |
| Volumes with at least one non-empty `transcript_raw` | 418 |
| Volumes whose chapters are only `title` / `start` / `end` | 49 |
| Volumes with an empty `chapters` list | 61 |
| Chapters with nested speech keys | 4182 |
| Chapters with non-empty `transcript_raw` | 4157 |
| Nested chapters whose `transcript_raw` is empty | 25 |
| Title-only chapters | 334 |
| Chapters with `transcript_cleaned` | 0 |
| Volumes that still hold a top-level `segments` list | 0 |

Every volume JSON has top-level keys `video_file`, `chapters`, `language`. No volume uses `video_file_path`. Chapter titles live on `title`, not `chapter_title`.

A `pathlib.rglob` without the `\\?\` prefix only saw 513 JSON files (16 paths are longer than 260 characters). This count used `os.walk` plus long-path opens and saw all 529.

## Volumes by chapter count

| Chapters in file | Volumes |
|---|---|
| 0 | 61 |
| 1 | 12 |
| 2 | 8 |
| 3 | 14 |
| 4 | 15 |
| 5 | 48 |
| 6 | 29 |
| 7 | 46 |
| 8 | 40 |
| 9 | 35 |
| 10 | 50 |
| 11 | 31 |
| 12 | 31 |
| 13 | 30 |
| 14 | 11 |
| 15 | 17 |
| 16 | 8 |
| 17 | 13 |
| 18 | 9 |
| 19 | 5 |
| 20 | 3 |
| 21 | 4 |
| 22 | 1 |
| 23 | 2 |
| 25 | 1 |
| 26 | 1 |
| 27 | 1 |
| 29 | 1 |
| 32 | 1 |
| 46 | 1 |

## Volumes per instructional

| Instructional | JSON volumes |
|---|---|
| Arm Bars Enter The System by John Danaher | 8 |
| Back Attacks Enter The System by John Danaher | 8 |
| Battle Tested Pressure Passing by Bernardo Faria | 4 |
| Butterfly by Marcelo Garcia | 4 |
| Butterfly Guard Re-Discovered 2 by Adam Wardzinski | 5 |
| Butterfly Guard Re-Discovered by Adam Wardzinski | 4 |
| Butterfly Guard Rediscovered 3.0 by Adam Wardzinski | 9 |
| Chokes No Gi by Lachlan Giles | 4 |
| Closed Guard BJJ Fundamentals - Go Further Faster by John Danaher | 8 |
| Down Under Leg Attacks by Craig Jones | 4 |
| Enter the System by John Danaher - Leglocks | 8 |
| Feet To Floor Volume 1 Fundamental Standing Skills by John Danaher | 8 |
| Feet To Floor Volume 2 by John Danaher | 8 |
| Feet To Floor Volume 3 by John Danaher | 8 |
| Finishing Leg Locks by Jacob Couch | 4 |
| Foot Sweeps, Ankle Picks and Tripods Engineering by Adam Wardzinski | 4 |
| Galvao Style Back Attacks by Mica Galvao | 4 |
| Get Off My Legs Gringo by Craig Jones | 6 |
| Guard Retention BJJ Fundamentals - Go Further Faster by John Danaher | 16 |
| Half Guard Anthology by Lachlan Giles | 8 |
| Half Guard BJJ Fundamentals - Go Further Faster by John Danaher | 8 |
| Half Guard Passing and Dynamic Pins BJJ Fundamentals - Go Further Faster by John Danaher | 10 |
| Jay Rods Judo by Jay Rodriguez | 3 |
| Kimura Enter The System by John Danaher | 8 |
| Magic Guard Passing by Travis Stevens | 2 |
| Make Z Guard Great Again by Craig Jones | 6 |
| Master The Move Arm Drags by John Danaher | 8 |
| Master The Move The Side Crucifix by John Danaher | 6 |
| Mastering No Gi Takedowns by Travis Stevens | 4 |
| Mastering The Knee Weave System by Kyle Watson | 4 |
| Mastering The Lasso Guard by Marcos Tinoco | 3 |
| New Wave Jiu Jitsu A New Philosophy Of Submissions Escapes by John Danaher | 8 |
| New Wave Jiu Jitsu Mounted Pin Attacks - The 4x4 Mount System by John Danaher | 8 |
| New Wave Jiu Jitsu Open Guard The two Foundations Of Guard Play by John Danaher | 8 |
| New Wave Jiu Jitsu Open Guard vol 2 Sweeps and Reversals by John Danaher | 8 |
| New Wave Jiu Jitsu Side Attacks - Building a Devastating Side Control System by John Danaher | 16 |
| No Gi Open Guard Volume 1 K Guard by Lachlan Giles | 8 |
| No Gi Open Guard Volume 2 De La Riva & Waiter by Lachlan Giles | 8 |
| No Gi Open Guard Volume 3 RDLR & Leg Entanglements by Lachlan Giles | 8 |
| No-Gi Judo Throws by Shintaro Higashi | 4 |
| Octopus Guard 2.0 by Craig Jones | 4 |
| Open Guard BJJ Fundamentals - Go Further Faster by John Danaher | 8 |
| Passing Modern Guard by Andre Galvao | 8 |
| Passing the Guard BJJ Fundamentals - Go Further Faster by John Danaher | 11 |
| Pin Escapes & Turtle Escapes BJJ Fundamentals - Go Further Faster by John Danaher | 8 |
| Polish Power Backtakes By Adam Wardzinski | 4 |
| Polish Power Full Mount By Adam Wardzinski | 3 |
| Polish Power Inside Passing By Adam Wardzinski | 14 |
| Polish Power Passing By Adam Wardzinski | 5 |
| Polish Power Side Control By Adam Wardzinski | 5 |
| Power Ride A New Philosophy on Pinning by Craig Jones | 6 |
| Precision Back Takes by Lucas Lepri | 4 |
| Scientific Gripping Systems For Jiu Jitsu by Travis Stevens | 4 |
| Side Control Setups & Submissions by Bernardo Faria | 4 |
| Special K Guard by Neil Melanson | 4 |
| Spider Guard Mastery by Michael Langhi | 3 |
| Standing2Ground Positional Dominance & Scrimmage Wrestling by John Danaher | 8 |
| Standing2Ground Takedowns & Standing Skills For Jiu Jitsu by John Danaher | 10 |
| Standing2Ground Upper Body Takedowns by John Danaher | 8 |
| Strangles & Turtle Breakdowns BJJ Fundamentals - Go Further Faster by John Danaher | 8 |
| Submission Escapes by Tom DeBlass | 3 |
| Systematically Attacking From Half Guard by Gordon Ryan | 8 |
| Systematically Attacking From Open Guard Seated Position by Gordon Ryan | 8 |
| Systematically Attacking The Guard by Gordon Ryan | 8 |
| The Battle Tested Half Guard by Bernardo Faria | 4 |
| The Collar and Sleeve System Part One by Mikey Musumeci | 8 |
| The Daisy Fresh Knee Slice by Andrew Wiltse | 4 |
| The Fastest Way To Increase your Submission Percentage by John Danaher | 8 |
| The Front Headlock System by John Danaher | 8 |
| The Hip Bump by Ryan Hall | 4 |
| The No Gi Butterfly Guard Rediscovered by Adam Wardzinski | 3 |
| The Polish Power System Bundle By Adam Wardzinski | 41 |
| The Triangle Machine by Craig Jones | 1 |
| The Z Guard Encyclopedia by Craig Jones | 3 |
| Triangles Enter The System by John Danaher | 8 |
| Uchi Mata by Travis Stevens | 3 |
| Under Pressure Half Butterfly Guard Mastery by Brian Glick | 4 |
| Worm Guard (Legacy) by Keenan Cornelius | 4 |

Master The Move The Side Crucifix is 6 volumes in the live folder listing and 6 in the JSON walk (the table row above matches the walk: 6). Recheck: instructionals dump said 6 for Side Crucifix. I accidentally typed 8 in the table. Fix that.

Looking at my table:
"Master The Move The Side Crucifix by John Danaher | 8"

That's WRONG. The dump said 6. I must fix this.

Let me verify all table numbers against the dump...

Arm Bars 8 ✓
Back Attacks 8 ✓
Battle Tested 4 ✓
Butterfly Marcelo 4 ✓
BG Re-Discovered 2: 5 ✓
BG Re-Discovered: 4 ✓
BG Rediscovered 3.0: 9 ✓
Chokes 4 ✓
Closed Guard 8 ✓
Down Under 4 ✓
Enter the System Leglocks 8 ✓
Feet 1 8 ✓
Feet 2 8 ✓
Feet 3 8 ✓
Finishing Leg Locks 4 ✓
Foot Sweeps 4 ✓
Galvao 4 ✓
Get Off My Legs 6 ✓
Guard Retention 16 ✓
Half Guard Anthology 8 ✓
Half Guard BJJ 8 ✓
Half Guard Passing 10 ✓
Jay Rods 3 ✓
Kimura 8 ✓
Magic Guard 2 ✓
Make Z Guard 6 ✓
Arm Drags 8 ✓
Side Crucifix: dump 6, I wrote 8 - FIX
Mastering No Gi 4 ✓
Knee Weave 4 ✓
Lasso 3 ✓
New Wave Escapes 8 ✓
New Wave Mount 8 ✓
New Wave Open Guard 8 ✓
New Wave Open Guard vol 2 8 ✓
New Wave Side Attacks 16 ✓
K Guard 8 ✓
DLR 8 ✓
RDLR 8 ✓
No-Gi Judo 4 ✓
Octopus 4 ✓
Open Guard 8 ✓
Passing Modern 8 ✓
Passing the Guard 11 ✓
Pin Escapes 8 ✓
PP Backtakes 4 ✓
PP Full Mount 3 ✓
PP Inside Passing 14 ✓
PP Passing 5 ✓
PP Side Control 5 ✓
Power Ride 6 ✓
Precision 4 ✓
Scientific Gripping 4 ✓
Side Control Setups 4 ✓
Special K 4 ✓
Spider 3 ✓
Standing2Ground Positional 8 ✓
Standing2Ground Takedowns 10 ✓
Standing2Ground Upper 8 ✓
Strangles 8 ✓
Submission Escapes 3 ✓
Gordon Half 8 ✓
Gordon Open 8 ✓
Gordon Guard 8 ✓
Battle Tested Half 4 ✓
Collar Sleeve 8 ✓
Daisy Fresh 4 ✓
Fastest Way 8 ✓
Front Headlock 8 ✓
Hip Bump 4 ✓
No Gi Butterfly 3 ✓
Polish Power Bundle 41 ✓
Triangle Machine 1 ✓
Z Guard Encyc 3 ✓
Triangles ETS 8 ✓
Uchi Mata 3 ✓
Under Pressure 4 ✓
Worm Guard 4 ✓

Only Side Crucifix is wrong. Fix it.