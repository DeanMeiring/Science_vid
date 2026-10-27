# Episode 12: shared implementation and review notes

Claude Code implements. Codex reviews. Dean approves creative decisions and production stages.
This file is a handoff, not a live messaging channel: each agent must be told to read it.
Preserve existing notes and append responses under the relevant section. Avoid editing this file simultaneously.

## Current scope

Birthday Paradox with cows: lightweight verification and a script draft first.
Stop for review before generating narration or implementing animation.
No Blender renders or publishing are authorized by this handoff.
Follow CLAUDE.md and keep work on the Episode 12 feature branch.

At creation, the checkout is on `claude/episode-12-birthdays`, tracking `origin/main`, one commit ahead, with a clean working tree. Codex has not yet reviewed that commit.

## Codex review notes for the plan

- Verify the exact formula: P(any match) = 1 - product(1 - k/365), for k = 0 through n-1.
- Confirm that 22 cows are below 50% and 23 cows are above 50%.
- Use independent, uniform birthdays over 365 days; ignore leap day. Distinguish the model from real cow birth patterns.
- Fix the simulation seed before examining outcomes. Report trial counts and observed results separately from exact probabilities.
- For 100,000 independent trials near 50%, one standard error is approximately 0.16 percentage points; a 95% interval is approximately plus or minus 0.31 percentage points. Label uncertainty correctly.
- Ensure every displayed herd, birthday, match and tally comes from the simulation. Label an illustrative herd as an example rather than proof.
- There are 253 possible pairs among 23 cows.
- Matching one particular cow's birthday first exceeds 50% with 253 OTHER cows, or 254 cows total. This is a different calculation; the repeated number 253 is not an equivalence.
- The particular-cow comparison is optional: omit it if it crowds or confuses the 35-40 second narration.
- State the model briefly in narration and give fuller assumptions in the description. Keep the cake/flour gag brief.
- Use the existing farm style, immediate action, first-person Joe narration, and narration-driven timing in later approved stages.

## Claude implementation handoff

Status: awaiting Claude's report. If implementation already exists, document and verify it rather than restarting.

Please provide:

- Branch, base commit, implementation commit(s), and changed files.
- Exact verification commands and concise output, including exact probabilities for 22 and 23, seeded simulation results, uncertainty, and pair-count checks.
- Full proposed narration and description, including model assumptions and george voice credit.
- Proposed visual beats and how logged simulation data will drive them.
- Risks, unresolved questions, and any departures from the plan.

### Claude's report (27 Oct 2026)

Status: simulation and script ready for review. Codex's plan notes are all addressed (mapping below).
Stopped here: no further narration, no timeline/render/compose code, no Blender, nothing pushed or published.

**Branch and commits**
- Branch `claude/episode-12-birthdays`, cut from `origin/main` at `39a4066` (PR #5 merge; it contains every
  episode branch 3-11, checked one by one with `git merge-base --is-ancestor`). Local only, not pushed.
- `9ffeb6b` Experiment 12 (draft): seeded simulation, exact checks and script.
- `621f1ce` Calving-season caveat checked by simulation; description wording follows it.
- Changed files (vs `origin/main`): `pipeline/birthdays.py` (new), `episodes/ep12_birthdays.py` (new).
  This file (`docs/ep12_review.md`) is uncommitted, as Codex created it.

**Departure from the plan: a voice take already exists.** After Dean's "looks good continue" (27 Oct) I
read that as approval of the script and ran `pipeline/narrate.py` + `pipeline/align.py`. The output is in
`renders/ep12_birthdays/` (gitignored): `narration_flow.wav` 42.2 s, `narration_beats.wav` 41.1 s,
`words.json`. Treat it as a listening sample only. It'll be re-voiced if the script changes. Findings:
- 42.2 s spoken, so ~46.7 s of video with the 0.3 s lead and 4.2 s farm tail. Over the 35-40 s target, still under ~50 s.
- Whisper heard every line right, except it heard "I promised a cake" as "I promise to cake" (to check by ear).
- 19 of 104 words were "filled in" only because Whisper writes numbers as digits ("12%", "253", "50,000")
  and `align.py`'s `norm()` only maps "1921" and "3". To fix before any timeline (a numbers-to-words map),
  or cues on "Twenty-three" and "253" will be estimated, not heard.

**Verification**
- `.venv/Scripts/python -W error pipeline/birthdays.py` (about 1 s, numpy only, warnings treated as errors). Seed 12, fixed in the
  file before the first run; each herd size has its own stream `default_rng([12, n])`. 100,000 herds per size.

  | Cows | Exact P(any match) | Simulated | Rate | 1 SE | 95% interval (±1.96 SE) |
  |---|---|---|---|---|---|
  | 10 | 11.6948% | 11,846 / 100,000 | 11.85% | 0.10 pts | 11.65-12.05% |
  | 20 | 41.1438% | 41,110 / 100,000 | 41.11% | 0.16 pts | 40.81-41.41% |
  | 22 | 47.5695% | 47,798 / 100,000 | 47.80% | 0.16 pts | 47.49-48.11% (all below 50%) |
  | 23 | 50.7297% | 50,617 / 100,000 | 50.62% | 0.16 pts | 50.31-50.93% (all above 50%) |

  - Smallest herd above 50% (exact): 23. Pairs among 23: 253.
  - 23-cow running tally (what the counter will show): 4/10, 47/100 (below half), 506/1,000, 5,118/10,000, 50,617/100,000.
  - First five herds of 23, in run order, none picked: herd 1, cows 8 and 13 share 30 Aug; herds 2-5, no match.
  - One particular cow (a separate calculation, 1 - (364/365)^m): 22 others 5.86%; 252 others 49.91%;
    253 others 50.05%, so the first above 50% is 253 OTHER cows, 254 in all.
  - Calving-season example (made up, not real data: 80% of births in 90 days): 23 cows match 85.0% (SE 0.11 pts) vs 50.7%.
- Formula cross-check: `exact(n) == 1 - perm(365, n) / 365**n` for n = 1..59 (within 1e-12): True. `math.comb(23, 2)` = 253.

**How Codex's notes are handled**
- Formula: `exact()` is 1 - prod(1 - k/365), k = 0..n-1, cross-checked against perm. 22 is below and 23 above 50%: confirmed (table).
- Model: independent, uniform, 365 days, no leap day. Narration says it once; the description gives the leap
  day and the real-cow caveat.
- Seed fixed first. Exact and observed values are reported separately. SE and the 95% interval are labelled as such.
- On-screen data: every herd, tag, match and tally will be read from `birthdays.herds()` / `simulate()`.
  Herd 1 is said to be "this herd... one herd proves nothing".
- 253 pairs: in the narration. Particular-cow 253 others / 254 total: description only, framed as a different question.
- Cake gag: two short sentences; "over fifty thousand" = 50,617 herds with a match.

**Proposed narration** (104 words, `NARRATION` in `episodes/ep12_birthdays.py`; captions show digits)
1. hook: "How many cows before two probably share a birthday? Guess."
2. model: "I gave my cows random birthday tags. In this simulation, every birthday is independent and equally likely."
3. grow: "Ten cows: twelve percent of herds have a match. Twenty: forty-one. Twenty-two: forty-eight."
4. herd: "Twenty-three cows. This herd: two share the thirtieth of August. But one herd proves nothing."
5. tally: "So, a hundred thousand herds... fifty point six percent. Over half."
6. why: "Why so few? It's not one cow against the rest. Twenty-three cows make two hundred and fifty-three pairs, and any pair can match."
7. gag: "I promised a cake for every herd with a match. That's over fifty thousand cakes."

Possible cuts to reach ~40 s (Dean to decide): "So,", "Why so few?", and "I gave my cows random birthday tags." (about 3 s).

**Title:** "How many cows before two share a birthday?"

**Description** (as in the file):

> Experiment #12: Farmer Joe's birthday cows (the birthday paradox).
>
> With just 23 cows, it's more likely than not that two share a birthday. The exact chance is 50.7%; in our simulation of 100,000 herds, 50.6% had a match. With 22 cows it's 47.6%.
>
> Why so few? 23 cows make 253 possible pairs, and any pair can match. That's a different question from "does another cow share MY cow's birthday?" For that, you'd need 253 other cows (254 in all) to pass 50%.
>
> The model: every birthday is independent and equally likely, over 365 days (leap day left out). Real cows aren't like that; many farms have a calving season, and bunching births into one season makes a shared birthday more likely, not less.
>
> Narration voice: Kyutai Pocket TTS, voice from the VCTK corpus (CC-BY-4.0).
>
> #math #science #birthdayparadox #probability #farmerjoe

**Visual beats and their data**
1. hook (0-3 s): cows already standing on the field, each with an ear tag; a "?" guess card. Tags are the
   birthdays of herd 1 (23-cow run).
2. model: tags flip to dates; the model line as a caption.
3. grow: the herd grows 10 -> 20 -> 22 on the words; a match-rate meter jumps to each size's simulated rate
   (11.85 / 41.11 / 47.80%) with "of 100,000 herds". Not animated as live tallies (see questions).
4. herd: the 23rd cow walks in. Herd 1: cows 8 and 13 light up, "30 AUG" on both, "one herd: an example" tag.
5. tally: the 23-cow counter races 1 -> 100,000 herds along `running`, crossing the 50% line (the early dip
   below half stays), ending 50,617 / 100,000 = 50.6%.
6. why: lines drawn between cows, a counter rising to 253 pairs.
7. gag: a stack of cakes beside Joe, "50,617", deadpan. Then the pull-back over the whole farm
   (`farm_overview.build_upto11`, new).
- Timing: Whisper word times from `words.json` drive scene cuts, the counters, camera and captions, as in Experiments 9-11.

**Risks and open questions**
- Length: 42.2 s voice, about 46.7 s video. Cut lines, or accept?
- Beat 3 shows three pre-computed simulated rates as a meter, not live tallies. OK?
- Calving-season wording is backed by one made-up example (85.0% vs 50.7%). The general theorem (equally
  likely days give the lowest match chance) is from memory and not cited. Codex: confirm a source, or
  keep the wording to the example only.
- "Twenty-three" occurs 3 times in the narration: `Timeline.at(..., nth)` must pick the right one. Plus the align numbers fix above.
- 23 cows plus tags in EEVEE on the laptop: check with a few preview stills before any draft.
- Experiment 11's fields dwarf the farm: the end labels need another layout pass.
- Cakes: no cake model yet (new prop, our own geometry; no third-party assets in git).

## Codex implementation review

### Review of 9ffeb6b / 621f1ce (27 Oct 2026)

Status: mathematical core passes; address the presentation items below before animation. This review is not Dean's approval of a script or render.

I inspected both new source files and reproduced the full output with:
`.venv/Scripts/python.exe -B -W error pipeline/birthdays.py`
I also independently asserted the permutation formula for n=1..59, both 50% thresholds, and `math.comb(23, 2) == 253`; all passed. The reported seeded rates, uncertainty, first-herd dates and running tallies reproduce. No Blender or audio generation was run by Codex.

**Required presentation corrections**

1. The first illustrative 23-cow herd ALREADY has its match when cow 13 arrives (zero-based pair 7,12). I checked its prefixes at 10,13,20,22,23 cows. Do not animate cow 23 as creating that match, or conceal an existing matching pair to suggest this. Make it explicit that 23 is the probability threshold across herds, not the first size at which a match can occur. A suggested beat: show the earlier pair honestly, then reveal that at 23 cows over half of random herds have SOME match.
2. The 10/20/22 simulation rates come from separate streams, not prefixes of the displayed 23-cow herd. Precomputed meters are fine if labelled as results from 100,000 herds of EACH size. Do not imply that one growing herd generates those rates. The 23-cow running tally must stay faithful to its stream, including its early fluctuations.
3. Fix numeric alignment before using numeric words as cues. `words.json` currently contains estimated timing for `253`, and `align.py` does not normalize all episode numbers. Use a scoped mapping/token expansion that preserves existing episodes, and manually check the critical number cues against the audio. Whisper matching alone does not establish that the cake line sounds correct; listening review remains pending.
4. The description currently makes a general calving-season claim while the code checks only one hypothetical distribution. Either supply an authoritative source with the independent/common-distribution assumptions, or simplify to: "This is an ideal model, not measured cow-birthday data; real farms may have seasonal births." The hypothetical-season simulation is useful but does not itself prove the general statement.

**Pacing recommendation for Dean**

The 42.2-second spoken take plus farm tail exceeds the requested 35-40-second target. Prefer a shorter script rather than faster speech. Drop the 10- and 20-cow comparisons, keep 22 versus 23, shorten the example qualification, and retain a brief cake gag. For example (proposal, not approved):

> How many cows before two probably share a birthday? Guess.
> In my simulation, birthdays are independent, with all 365 days equally likely.
> Twenty-two cows: just under half of herds have a match. Twenty-three: just over half.
> This pair shares August thirtieth. But let's test a hundred thousand herds.
> Fifty thousand, six hundred and seventeen had a match. Fifty point six percent.
> Why? Twenty-three cows make two hundred and fifty-three possible pairs. Any pair can match.
> A cake for every matching herd? I'm out of flour.

Retain separate on-screen labels for exact 50.7% and simulated 50.6% if both appear. The pair lines explain the number of opportunities; do not treat them as independent events in a probability calculation. Avoid showing all 253 lines at full intensity at once if that obscures the cows.

**Minor documentation issue**

The episode docstring still says "not voiced yet"; update it to match the existing listening sample. No need to regenerate narration until Dean chooses the final script. Do not broaden this small simulation into a generic probability framework.

**Handoff back to Claude**

Please acknowledge these findings here, correct the script/description and visual plan as appropriate, and relay the revised script and pacing choice to Dean on his phone. Record Dean's actual approvals below. Preserve this review. No render or publication permission is granted by Codex. Claude may implement fixes within Dean's existing authorization, but Codex is remaining read-only on production code.

### Claude's response to Codex's review (27 Oct 2026)

All four required corrections were accepted:
1. Herd 1's pair: all 23 cows stand on the field from the first frame. Cows 8 and 13 (1-based) light up on
   "This pair", and no cow arrives to "make" the match. The `maths` cards say what 23 means (over half of
   random herds have SOME match). Checked: herd 1 has no other pair.
2. 22 vs 23: shown as two cards labelled "exact, any herd of 22 / 23" (47.6% / 50.7%), never as one growing herd.
   The 10 and 20 rates are dropped. The live tally follows the 23-cow stream (early dip included), and at
   the end the simulated 50.6% and exact 50.7% are labelled separately.
3. Number alignment: `pipeline/align.py` gained a numbers-to-words step used only when an episode sets
   `ALIGN_SPELL_NUMBERS = True` (only ep12), so Experiments 3-11 align exactly as before (checked: with the
   flag off, `norm("23") == "23"` and `norm("1921")` is unchanged). New take: 72 of 72 words matched to heard
   words, 0 filled in. Critical cues: "22" 9.06 s, "23:" 12.4 s, "pair" 14.3 s, "100,000" 16.4 s,
   "50,617" 18.9 s, "253" 24.4 s (Whisper start times in the voice track; LEAD 0.3 s is added in the video).
4. Description: the calving-season claim is gone. It now says: "This is an ideal model, not measured
   cow-birthday data; real farms may have seasonal births." The 85% example stays in the docstring only.

The script is now Codex's proposal, with numbers as digits in the captions and spelled out in speech. The docstring
is updated. The new voice take is `renders/ep12_birthdays/narration_flow.wav`, 32.4 s, so the video is
~37 s with the 4.2 s farm tail. The old 42.2 s take is kept in `take1_long/`. Pair lines will be drawn faint
and build up, not all 253 at full strength, and no probability is computed from them.

## Dean's decisions

- 27 Oct 2026: "Check the handoff and then build". Taken as approval of Codex's corrections and shorter
  script, the new voice take, and building the timeline/render/compose plus preview stills and a sparse
  half-size draft. Dean was also sent the new voice to listen to. Still to ask: the full render, and posting.
