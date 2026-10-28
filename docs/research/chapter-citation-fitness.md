# Whether a chapter is a fit citation

**Answer: mixed.** A spec cannot cite every chapter as stored. Cleanup has to come first for volumes with no chapter, for a chapter that covers a whole volume, for a chapter whose title already names several ideas, for intros, outros, and named rolls, and for any citation that treats the speech at the chapter cut as the start of that idea. A technique-scoped chapter of a few minutes, read from inside the time range rather than from the cut, often does name one teachable idea and the speech matches the title.

This note does not propose a chunking pipeline and does not design retrieval. Primary source: the volume JSON under `C:\Users\dumbo\Documents\GitHub\djsciman_data_projects\video-transcriber\library`. Each volume has top-level keys `chapters`, `language`, and `segments`. A chapter is `title`, `start`, and `end`. A segment is `start`, `end`, `text`, `source`, `asr_logprob`, `ocr_confidence`, and `language`.

## Corpus

The corpus has 32 instructional folders. Two are empty, both John Danaher, so they contribute no volume: `New Wave Jiu Jitsu A New Philosophy Of Submissions Escapes by John Danaher` and `New Wave Jiu Jitsu Mounted Pin Attacks - The 4x4 Mount System by John Danaher`. The other folders hold 140 volumes.

| Measure | Range across the corpus |
| --- | --- |
| Chapters per volume | min 0, p10 0, p25 4.75, median 7, p75 10, p90 13.1, max 27 (mean 7.6) |
| Chapter duration | min 19s, p10 145s, p25 218s, median 302s (about 5 min), p75 433s, p90 666s, max 9730s (mean 407s) |
| Chapter title length | min 5 characters (1 word), p10 14, median 29 (5 words), p90 53, max 141 (20 words) |
| Segments per volume | min 12, p10 49, median 90, p90 195, max 328 (mean 109) |
| Segment duration | min 1.1s, p10 26s, median 29s, p90 33s, max 979s (mean 30s) |
| `asr_logprob` | min −0.717, p10 −0.142, median −0.074, max −0.006. 3 of 15,286 segments are below −0.5. None are below −0.8 |

Where a chapter exists, the ranges tile the volume: no chapter overlaps another, no gap between chapters is larger than a second, and speech sitting outside every chapter is 0.8s in total. No chapter is empty of speech. Every segment has `source` `SPEECH`, `language` `en`, and non-empty `text`. Every volume `language` is `en`. `ocr_confidence` is null on every segment.

That tidy tiling is not the same as a clean cut in the speech. 879 segments cross a chapter boundary, on all 117 volumes that have two or more chapters. The piece of a straddling segment that falls into the later chapter has median 16.5s, p90 29s, max 71s. A citation at `chapter.start` usually opens on the previous idea.

Duration bins for the 1,059 chapters: under 60s, 16; 1–3 min, 153; 3–10 min, 762; 10–20 min, 103; 20 min or longer, 25. The typical stored chapter is one idea-sized block of a few minutes. The unfit cases are a minority of chapters plus a block of volumes that have no chapter at all.

18 volumes have an empty `chapters` array. A citation cannot point at a chapter there:

- Jacob Couch, *Finishing Leg Locks*, all 4 volumes
- Andrew Wiltse, *The Daisy Fresh Knee Slice*, all 4 volumes
- Ryan Hall, *The Hip Bump*, all 4 volumes
- Keenan Cornelius, *Worm Guard (Legacy)*, all 4 volumes
- Adam Wardzinski, *Butterfly Guard Re-Discovered 2*, Volume 1 part 2 (12 segments, about 6 min)
- Adam Wardzinski, *Polish Power Inside Passing*, the only volume (13 segments, about 6 min)

Five volumes have exactly one chapter, and that chapter is the whole recording. Four are John Danaher, *Feet To Floor Volume 1*, titled `Volume 1`, `Volume 2`, `Volume 6`, and `Volume 8` (7,222s to 9,730s). The fifth is Lachlan Giles, *Half Guard Anthology* Volume 8, titled `11 Z GUARD, KIMURA, AND NARRATED ROLLING` (9,581s).

58 segments last 90s or longer, and 6 last 180s or longer. All of them sit in three instructionals: *Half Guard Anthology* by Lachlan Giles (28), *Chokes No Gi* by Lachlan Giles (15), and *Worm Guard (Legacy)* by Keenan Cornelius (15). The longest is one Keenan segment from 64.16s to 1,042.75s.

## Sample

Speech was read in 11 volumes from 11 instructors. In each volume the sample was the first chapter after a leading chapter titled only Intro, Introduction, or Overview; the middle chapter by index; and the longest chapter. When the longest was also the first or the middle, that chapter was read once. Start-of-chapter speech is the segments overlapping the first ~50s. Midpoint speech is the segments overlapping the middle of the time range.

Instructors: Bernardo Faria, Marcelo Garcia, Adam Wardzinski, Lachlan Giles, John Danaher, Craig Jones, Mica Galvao, Jay Rodriguez, Travis Stevens, Kyle Watson, Marcos Tinoco. Whole-volume and no-chapter volumes above were checked at the open and, where noted, at a midpoint. They are not part of the three-chapter sample.

## Chapters that can be cited as stored

These name one teachable idea, and the midpoint speech matches the title. A segment that straddles the cut still contains the previous chapter. That is documented below for Faria and Galvao. It is not every cut. On Danaher’s flower-sweep chapter the previous segment only overlaps the range by 0.1s, and the first full segment inside the range matches the title.

- Adam Wardzinski, *Butterfly Guard Rediscovered 3.0* Volume 4, `Armlock From Lazy Butterfly Guard`, 1,039.7–1,343.3. At 1,044–1,074 he says he will attack the posting arm from lazy butterfly and dig under it. At about 19:25 he is still on that armlock, with a branch into a rolling armbar if the lock fails. The title holds. The same volume’s speech does rename the guard (“classic battle guard”).
- John Danaher, *Closed Guard* Side-Scissor, `Side Scissor Position Working with Lower Head Position: Flower Sweep`, 4,121–4,453. The segment 4,094.46–4,121.1 only overlaps this chapter by a tenth of a second. At 4,125.58 he is still on the side-scissor transition, now “in terms of head position,” which is the first half of the title. At 4,260–4,290 he says the first sweep, with both knees down, is a modification of the flower sweep. The longest chapter in this volume, `The Side Scissor: Elbow Across The Centerline - Converting a Closed Guard to a Side Scissor` (0–1,562, about 26 min), is long but still that conversion at the end: at 1,520–1,553 the grip sequences all finish “into a side scissor.” One idea, taught long, not a grab bag of sweeps. The sweeps are later chapters.
- Craig Jones, *Down Under Leg Attacks* Volume 2, `Finishing from the saddle`, 0–577. He names the saddle and the inside heel hook at 4s, and at about 4:24 he is still on how to finish that heel hook. `Countering the kick off defense`, 1,029–1,121, matches the speech at 1,016: they kick the leg out, and he counters into the heel hook.
- Marcos Tinoco, *Mastering The Lasso Guard* Volume 1, `Lasso to arm drag back take`, 869–1,089. At 959–989 he switches to the sleeve, takes the leg out, and goes around the back for the seatbelt. The title matches. The title `Lasso omoplatta` (2,349–2,649.1) is a spelling miss. At 2,474.43–2,503.15 the foot goes over the shoulder and he lets go of the lasso. At 2,503.34–2,531.54 he finds the far shoulder and locks the hand to the ribs.
- Mica Galvao, *Galvao Style Back Attacks* Volume 2, `Turtle - Back Exposure On Neck Pressure`, 0–700.1. After a recap of earlier chapters, the midpoint (about 5:18) is shoulder pressure behind the neck to expose the back. The title matches. The transcript’s wording on the later chapter is a separate problem, below.
- Bernardo Faria, *Battle Tested Pressure Passing* Volume 1, `Applying Weight and Pressure When Passing`, 90–283. He says the first “technique” is not a technique but how to use weight, and at about 2:44 he places the shoulder on the diaphragm. One principle, and the title matches.

Marcelo Garcia, *Butterfly* Volume 2, is the same shape. `MARCELOTINE` (1,026–1,463) is a proper name; at about 20:09 the speech is the head under the armpit and the wrist against the throat. `THE BLAST` (0–303) and `LEG KICK BUTTERFLY SWEEP` (1,956–2,223) are also proper names. The slices teach a collar-tie entry and a forward-momentum sweep without repeating those names. That is not a contradiction, but a citation that expects the title words in the transcript will not find them.

## Too broad

The title, or the speech inside the range, names more than one teachable idea.

- Faria, Volume 1, `4 Options To Finish Over Under Pass`, 1,168–1,553. At 1,202 he says he will show “all ways you have to establish the position.” The midpoint is only one of those finishes (hand on the pants, then side control).
- Wardzinski, Volume 4, `Lazy Butterfly Guard Attacks - Lazy Butterfly Guard Cross Choke And Cross Choke Sweep`, 0–376.1. The title names a choke and a sweep. At 159–189 the speech is the choke (“raising up the sharp palm”).
- Same volume, `Omoplata Options`, 1,343.3–1,842.1. At 1,352–1,379: “attack with the omoplatas for both sides. So we're going to break down both of them now.”
- Kyle Watson, *Mastering The Knee Weave System* Volume 3, `Entries from Half Guard (Bottom) - Dogfight-Knee Tap, Handshake Sweep & Backstep Counter`, 719–1,357. At 1,029 he finishes “a basic knee tap” from dogfight. At 1,059 he starts a second move: “we call this the handshake sweep.”
- Lachlan Giles, *Chokes No Gi* Volume 1, `Overview of positions and submissions`, 65–176. At 94–157 he lists front headlock, guard, inverted north-south, north-south, top half, and mount, then the guillotine, arm-in guillotine, anaconda, “daas,” Japanese necktie, and north-south choke.
- Travis Stevens, *Magic Guard Passing* Volume 1. `guard passing strategy while opponent is supine` (0–715) is a ladder of controls from feet to knees to hips, not one pass. `strategy for inside the situp guard` (715–1,541) opens with “a lot of different things that can happen and a lot of different reactions.” The titles match those bundles. They are too broad for one idea.
- Giles, *Half Guard Anthology* Volume 8, the only chapter, `11 Z GUARD, KIMURA, AND NARRATED ROLLING`, 0–9,580.7. At 3s he is on “Zeg guard.” At 4,778.6s he is on a “choy bar,” underneath the shoulder, trying to get a leg over the head. The title lists three topics, and the speech has already changed subject halfway through.
- Danaher, *Feet To Floor Volume 1*, `Volume 1` on the Stance volume, 0–9,011.4. The title does not name an idea. At 8.8s he lists the contents as “stance, gripping, motion, kazushi, and position.” At about 74:31 the speech is Jigotai versus an upright posture, a different skill from the opening.

## Too thin

Sixteen chapters are under 60s. The shortest is Marcos Tinoco, Volume 1, `introduction`, 0–19. The segment that contains it runs 0.11–32.03, so the intro and the next chapter (`lasso sweep concepts`, 19–122) share one utterance. Other stored shorts include Adam Wardzinski, *Foot Sweeps* Volume 1, `Intro`, 0–39; Jay Rodriguez, Volume 1, `Intro`, 0–47; Kyle Watson, Volume 4, `Outro`, 1,131–1,189.

Lachlan Giles, *Chokes No Gi* Volume 1, `Arm length and technique preference`, 2,461–2,506 (45s). The sentence that reaches arm length starts at 2,442.59, inside the previous chapter. By 2,502.80, still inside this chapter, he has left the topic: “So I just want to quickly go over why I think the inverted north-south is one of the best positions.” A timestamp in this chapter does not isolate one idea.

Bernardo Faria, Volume 4, stores named rolls as chapters of about a minute, which is not a taught technique: `Bruno Jacare Dias - Third Roll` (314–367), `Liam - Second Roll` (2,735–2,784), `Kyle Misuraca - Second Roll` (3,056–3,113), `Kyle Misuraca - Fifth Roll` (3,301–3,357.5).

## Title against the speech at the cut

The mismatch at the cut is systematic, not a one-off bad title. Median leak into the next chapter is 16.5s.

- Faria, `4 Options To Finish Over Under Pass`, starts at 1,168. The segment 1,143.17–1,174.58 is still the previous pass: “Just hip-scape. And I'm gonna follow him… I'm just gonna get rid of his legs and go to the side control.”
- Galvao, `Double Unders To The Back`, starts at 1,857.2. The segment 1,855.30–1,887.57 overlaps that chapter by about 30s. It begins “And then you have the back control over there,” the end of the previous pass, and only then announces the next one.
- Watson, the half-guard chapter above, starts at 719. The segment 708.53–746.19 overlaps it by about 27s and opens on the previous topic (“those are three entries… Now we're switching gears”).

## Transcript failures that make a citation unsafe

`asr_logprob` does not mark the bad lines. The renames below sit around −0.06 to −0.25, the same band as the median of −0.074. The worst score in the corpus is −0.717 on Wardzinski’s “and make the shock pack.” (2,617.97–2,619.82), inside `Regrip Triangle From Lazy Butterfly Guard` (2,253.1–2,622.4). Two seconds, and the surrounding segments are a readable triangle. A filter on logprob would miss the failures that matter and would flag almost nothing (3 segments under −0.5).

Word errors that would make a quoted citation name the wrong technique:

- Wardzinski, cross-choke chapter, 188.78–219.17, logprob −0.151: “from here, lazy buffalo guard. The gear is untied.” The chapter is lazy butterfly, gi lapel. Same chapter, he chokes with “the sharp palm.”
- Galvao, `Double Unders To The Back`, 1,855.30–1,917.47, logprob −0.151 to −0.169: “passes leading to the backstakes,” “we did a toronto,” “an old guy pass,” “the double runner position.” The title says double-unders to the back. The transcript does not.
- Craig Jones, `Countering the kick off defense`, 1,016.21–1,085.07: “another leg palm,” “Kick my glicep,” “kick the bison,” then “secure the heel hook.” The idea survives. The body words do not.
- Jay Rodriguez, `Russian Double From Rear Bodylock`, 1,573.34–1,634.96: “i can't get my oprah gone break,” “Koda gets standing with your body lock,” “issues with my Koda inserted hooks.” Nearby speech is a readable rear body lock and double. A quote of those sentences is not safe.
- Tinoco, the intro segment 0.11–32.03, logprob −0.253: “I'm Marcelo Garcia of Black Belt” and “leg loss is one of my main strong game,” then the next sentence says “lasso.” The instructor is Marcos Tinoco. “Leg loss” for lasso would attach the citation to the wrong topic.
- Giles, overview and arm-length chapters: “daas,” “dash choke,” “dars check,” and “arming guillotine” for the D’Arce and the arm-in guillotine.

The Keenan failure is structural. The first *Worm Guard (Legacy)* volume (the stored name contains `The Worm Guard DVD 1`) has no chapters. One segment runs 64.16–1,042.75 (978.6s) at logprob −0.124, beginning “I can push a little bit, but he can move his arm and resist.” A timestamp inside that sixteen minutes points at one text blob, not at a sentence. The other three Worm Guard volumes also have speech and no chapters. The same is true of the Hall, Wiltse, and Couch instructionals. Hall Volume 1 opens, with no chapter to hang it on, “this is Craig. We're here to talk to you guys about the hip pump sweep” (8.82–34.32). Wiltse Volume 1 opens on the knee slice (8.24–37.07). Couch Volume 1 opens on “the Daisy Fresh leg lock systems” (8.82–38.61). The speech is instructional. There is no stored chapter to cite.

The two short Wardzinski volumes with no chapters (about 6 minutes, 12 and 13 segments) are too small to be the rest of those instructionals. They are still volumes in the corpus, and they still have nothing to cite.

## Decision

Cite as stored only the narrow case: a chapter whose title names one move or one principle, longer than a minute and not a whole volume, with the timestamp taken from inside the range after the straddling segment. That pattern showed up for Wardzinski’s armlock, Danaher’s flower sweep and side-scissor conversion, Jones’s saddle finish, Tinoco’s arm-drag back take, Galvao’s neck-pressure back exposure, and Faria’s pressure principle. Even those are unsafe if the citation quotes a garbled sentence as the technique name. Logprob will not catch that.

Cleanup has to come before a citation is trustworthy for everything else, and that everything else is common:

- 18 volumes with no chapter, including four entire instructionals (Couch, Wiltse, Hall, Cornelius)
- 5 whole-volume chapters, four of them titled only `Volume N`
- chapters that list several techniques, overviews, or “options”
- intros, outros, and named rolls under about a minute
- any citation parked on the chapter boundary, because every multi-chapter volume has speech that belongs to two chapters
- a timestamp inside a multi-minute segment, which in this corpus is a Giles or Keenan problem

Until that split is made, the spec should not treat a stored chapter as a fit citation.
