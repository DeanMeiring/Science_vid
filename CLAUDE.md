# Working with Dean on Science_vid

## Pull requests
- Every code change goes on its own branch with a pull request. Dean merges
  it himself on GitHub.
- Never merge a PR yourself, and never push straight to `main`.
- Cut each branch from `origin/main` (`git checkout -b claude/<topic>
  origin/main`).

## What this is
- A new YouTube channel: animated maths and science experiments, Shorts
  first (long-form later).
- **Quality over quantity:** Dean wants each Short tailored and neat at the
  start, not mass-produced. Automation and scheduling come later, and
  Dean will decide when.
- It started from videos Dean saw of Langton's Ant: chaos, then a highway
  around step 10,000.
- Sister project: `DeanMeiring/CLIPPER` (his Twitch-clip Shorts app on
  Railway). It's a library of methods to reuse here. Copy what's needed;
  don't import across repos.

## Where we left off (end of 24 Oct 2026, evening)
- **Done for the day after Experiment 8** was posted to YouTube and Instagram (Dean: "end for tonight,
  we work tomorrow again"). TikTok: Dean posts by hand. Next: Experiment 9, Dean's pick ("Get 3 helpers"
  is parked below). PRs #3/#4 still wait for Dean; episode branches 3-8 are stacked, no PRs yet.
- **Done for the day after Experiment 5** (Dean: "finish up for today, will continue tomorrow").
  Next, when Dean asks: Experiment 6, "three barns, one prize" (Monty Hall), as Experiment 5's
  last line promises; check the facts by simulation first. Idea from a comment: "Get 3 helpers".
- **Experiment 8: "what grows if you plant it?"** (Dean's gag, 23 Oct): Joe plants a mustard seed, an
  apple seed, both together, and a rusty wheelbarrow tyre; the real "law" is biogenesis (life only from
  life; Pasteur 1859). Branch `claude/episode-8-plant`; `episodes/ep08_plant.py` (facts and sources in
  its docstring), voiced in george (32.9 s). Dean asked for "nonsense that sounds legit"; kept every line
  true instead (mustard is an annual, 4 ft, not a tree; seed-grown apples don't breed true; weeds grow
  round the tyre from seeds already in the soil).
  **Half-size draft made 23 Oct** (`renders/ep08_plant/ep08_plant_draft.mp4`, 34.6 s): `pipeline/ep08_timeline.py`,
  `blender/render_ep08.py` (five scenes cut on words, time-lapse skies, two winters of snow, moustache
  grows, weeds, flask on a table, then the whole farm via `farm_overview.build_upto7()`),
  `pipeline/compose_ep08.py` (notes, thought bubble crossed out, BIOGENESIS card, labels, sound).
  End labels spread out with arrows (`NUDGE`). Dean: "looks good". **Full render done 24 Oct**
  (`renders/ep08_plant/ep08_plant.mp4`, 34.6 s, 17 MB). **Posted to YouTube 24 Oct** (Dean asked by message, away from the laptop): https://youtube.com/shorts/WGJwOUZqe9M.
  Instagram failed 3 times with ProcessingFailedError (the stale-login error again); after Dean reconnected
  Instagram in the studio it posted 24 Oct 19:37: https://www.instagram.com/reel/De4rysbAF8p/
  Lesson: low memory (~12 of 15.5 GB in use) got the background render stopped twice; finishing it
  in foreground chunks of ~9 min (`--start A --end B`) worked, since only background jobs get stopped.
  Lesson: `--start 0 --end 0` renders the WHOLE video (0 = to the end); for check frames use
  `--every N --start A --end B` with the 1 s pause (a mistake here sent the fans roaring).
- **Parked: "Get 3 helpers"** (Dean picked it first, then parked it on 23 Oct; a viewer's comment on Experiment 4):
  Joe and three helpers on one field, the same rule as Experiment 1. Find the story by simulation
  first; open on an "If you..." hook; reuse the backdrop, Kenney models and Joe's arms. Simulated
  (23 Oct): all back home: 2 farmers ~4 in 10, 3 farmers 0 of 1,500, 4 farmers ~1 in 200; with 4,
  usually one or two walk off on a highway, all four in ~1 in 7. Story idea: "more helpers, more mess",
  helpers leaving one by one; helpers = Daisy + a cow + a pig (not decided).
- **Experiment 7: pi from a bale of hay** (started 23 Oct, Dean: "yes start experiment 7").
  Branch `claude/episode-7-pi` (stacked on `claude/episode-6-barns`). `pipeline/hay.py` is the sim
  (straws one board wide dropped at random; crossing rate 63.6% vs 2/pi 63.66%); seed 1:
  10 -> 2.50, 100 -> 2.99, 1,000 -> 3.03, 10,000 -> 3.13, 100,000 -> 3.143. `episodes/ep07_pi.py`,
  voiced in george (32.2 s; "pi" spoken as "pie"). **No "Next experiment" line yet: Dean picks
  Experiment 8.** Source: Wikipedia, "Buffon's needle problem" (18th century, Comte de Buffon, 2l/(pi t)).
- **Experiment 7 rendered 23 Oct** (`renders/ep07_pi/ep07_pi.mp4`, 37.4 s, 24 MB). Dean's direction:
  side view close to Joe, more detail, a backdrop (`blender/scenery.py`: hills, Kenney trees, fence,
  silo, clouds, sky gradient), deadpan Joe, opening on a hook ("If you throw hay at a floor, you can
  find pi."), escalation hand -> blur -> wheelbarrow -> tractor -> combine (`blender/machines_props.py`,
  our own combine: no John Deere colours). Every straw is the simulation's; counted on the planks,
  then hops onto the heap (Dean asked why it didn't go onto the pile: it must land on the planks to
  count). 2nd throw shows a pale straw from the first ten (counts at 10/100/... unchanged). Joe now
  has shoulder joints (`set_walker(arms=..., tool=False)`, `hand_position`). Captions show the π symbol.
  **Posted 23 Oct 13:56** to both: YouTube https://youtube.com/shorts/wxQgNbzltts and Instagram
  https://www.instagram.com/reel/De1gJe5j6hO/
- **YouTube "not shown in feed" (23 Oct):** none of the 7 Shorts are shown in the Shorts feed. Checked via
  the API: all public, processed, not made for kids, no rejection, viewable logged out (so not the
  "unaudited API project uploads are locked private" rule). Dean checked: phone-verified, feature
  eligibility on, audience not made for kids, no warnings. Suggested test: upload the next one to
  YouTube from the phone (studio Download button) and compare "Shown in feed".
- **Third-party 3D assets:** Kenney (CC0, nature + survival kits) in `assets/thirdparty/kenney`,
  loaded by `scenery.kenney()`, teal recoloured to farm greens. Quaternius: free commercial use but
  their licence forbids redistributing the files; downloads need a click on their site. Everything in
  `assets/thirdparty/` is gitignored, never committed.
- **TikTok:** Dean posts by hand from his phone. The studio has "Download video" and "Copy title +
  description" buttons for that. (TikTok's API needs an app audit before posts can be public, and an
  https login redirect.)
- **Experiment 6: three barns, one prize (Monty Hall)** (started 23 Oct; Dean: "build, but wait
  on which experiment comes next, I want to think about it"). Branch `claude/episode-6-barns`
  (stacked on `claude/episode-5-crops`). `pipeline/barns.py` is the sim; `episodes/ep06_barns.py`
  the script (Daisy picks, Joe hosts and KNOWS; prize = Joe's tractor, two goats), voiced in george
  (41.2 s, Dean: "voice is good"). Ends teasing Experiment 7, which Dean picked on 23 Oct:
  **pi from a bale of hay** (Buffon's needle: straws as long as the floorboard gap cross a crack
  with probability 2/pi). Dean wants Experiment 7 to feel different: Joe doing a farm job, with
  more 3D Blender design. Other ideas offered then: the fastest slide (brachistochrone), golden-angle
  sunflower, bees' hexagons, stacking apples (Kepler). Checked: 1M games switch 66.6%; the 1,000 shown: stay 339, switch 661;
  blind host = 50/50; Parade 1990 (~10,000 letters), Erdős and the simulation (Wikipedia).
  **Rendered 23 Oct** (`renders/ep06_barns/ep06_barns.mp4`, 42.9 s, 26 MB; full render 48 min).
  New 3D props in `blender/barns_props.py`: barns whose doors swing open, a goat, Joe's tractor
  (also instanced as little tractor "wins"). Behind the doors: goat, tractor, goat. Letters rain
  down on "1990". Ends on the whole farm with all six experiments labelled. **Posted 2026-10-23 10:20** to both:
  YouTube https://youtube.com/shorts/hW9eZ_L_Smg and Instagram https://www.instagram.com/reel/De1Hdj2nVY7/
- **Experiment 5 posted 22 Oct 2026, 22:52** to both from the studio: YouTube
  https://youtube.com/shorts/TKMkmPbBdc8 and Instagram https://www.instagram.com/reel/Dez4ouTlgJu/
- Branches `claude/episode-3`, `claude/episode-4-farmers`, `claude/episode-5-crops` are pushed,
  stacked on PR #4; no PRs for them yet.
- **Experiment 5: four crops** (started 22 Oct evening, Dean: "start making next video"). Branch
  `claude/episode-5-crops` (stacked on `claude/episode-4-farmers`). `pipeline/crops.py` is the sim
  and the check; `episodes/ep05_crops.py` the script (grass L, dirt L, wheat R, pumpkins R),
  voiced in george (38.3 s), waiting for Dean to listen. Checked: every time Joe is back on his
  first square facing the way he started, the field is a perfect mirror image (4,484 of 4,484
  in 200k steps; never facing down, 0 of 752); 2,632 times by step 100,000. Source for "proved":
  Wikipedia "Langton's ant" (pairs of equal turns -> symmetric over and over; Gale et al. 1995).
  Ends teasing "three barns, one prize" (Monty Hall).
  **Rendered 22 Oct** (`renders/ep05_crops/ep05_crops.mp4`, 40.0 s, 21.7 MB; full render 42 min).
  Dean picked style C: from above, looking down the mirror line, a glowing line + "MIRROR!" on
  each mirror moment; while racing only mirror moments are shown, so every frame is a true
  mirror image. Pumpkins added to the farm theme (`scene.set_pumpkins`). Dean then asked for the
  whole-farm zoom out at the end (as in Experiment 4): only the last 175 frames were re-rendered.
  Experiment 4's spot shows Daisy. Posted 22 Oct 22:52 (links above).
  Lesson: word lookups match every occurrence ("next crop" before "Next experiment"); pass nth.
- **Posted:** Experiments 1 and 2 on YouTube and Instagram. Dean posted
  Experiment 2's Reel from his phone (the API failed because it's over
  ~50 s): https://www.instagram.com/reel/DexWGACAEWc/
- **Experiment 3 posted 22 Oct 2026, 10:25** to both from the studio
  (38 s, so Instagram's API took it): YouTube
  https://youtube.com/shorts/EUE8YBSfB6I and Instagram
  https://www.instagram.com/reel/DeyjHWhgJIm/
- **Stats log** (track the trend; check with Dean before acting on it):

  | Date | Instagram | YouTube |
  |---|---|---|
  | 22 Oct 08:00 | Ep1 17 likes, Ep2 20; 3 followers | Ep1 3 views, Ep2 3 views; 1 subscriber |
  | 22 Oct 12:30 | Ep1 20 likes, Ep2 38 likes (2 comments), Ep3 0 (just out); 4 followers | Ep1 3, Ep2 3, Ep3 0 views; 1 subscriber |
| 22 Oct 13:34 | Ep3 "a lot of views" (Dean) | Ep1 3, Ep2 4, Ep3 2 views; channel 29 views / 0.4 h watch time (28 days); 1 subscriber |
| 22 Oct 20:05 | likes Ep1 23, Ep2 45, Ep3 132, Ep4 78 (6 h old); 7 followers | Ep1 3, Ep2 4, Ep3 2, Ep4 2 views; 1 subscriber |
| 22 Oct 22:54 | likes Ep1 25, Ep2 51, Ep3 144, Ep4 149, Ep5 0 (just out); 9 followers | Ep1 4, Ep2 4, Ep3 3, Ep4 2, Ep5 0 views; 1 subscriber |

  YouTube is barely showing the Shorts while Instagram grows. Asked Dean to
  check in YouTube Studio that each video shows as a Short, its traffic
  sources (Shorts feed?), and any warning icons. If they're all fine, it's
  probably new-channel slowness; a steady rhythm (every 2-3 days) helps.
  22 Oct, later: Experiment 3 (the sheep) is getting a lot of views on Instagram;
  YouTube still ~0. Dean's call: keep posting consistently on both.
  Checked in YouTube Studio (22 Oct): all three show as Shorts, no warnings or
  notifications. So it's new-channel slowness, not a problem with the uploads.
- New comments (22 Oct evening): Ep4 "Get 3 helpers" (idea: three farmers?); Ep3 "Shouldn't they
  all head back home at infinity?" (on a flat field yes, almost surely; in 3D no, ~34% ever do).
- Viewer comments so far: "two farmers end up back where they started"
  (idea for an episode, check by simulation) and an "infinite monkeys" joke
  tagging a friend on Experiment 2.
- **GitHub:** PR #3 (`claude/voice-cartoon` → `main`, all the pipeline
  work) is open and waits for Dean to merge it (Claude Code blocks Claude
  from merging). `claude/episode-2` is stacked on top of it; its PR is #4.
- **Next: Experiment 3, the lost sheep** (facts checked, below). Dean said
  "not yet": start when he asks. Plan:
  1. script under ~50 s that opens on action;
  2. voice it in george, as whole flowing paragraphs, and let Dean hear the
     voice-over on its own first;
  3. then style samples for the "more amateur, personal" look;
  4. then animate to follow the voice (Whisper word timings), and render.
- **Ideas queue:** four crops / crop circle (LLRR), Monty Hall barns,
  golden-angle sunflowers. A viewer comment on Experiment 1's Reel: "two
  farmers … after ~12,000 steps both end up where they started and all the
  dirt is grass". Check by simulation; a possible episode crediting them.
- **Experiment 4: two farmers** (the viewer's idea; Dean said "go for it", 22 Oct). Branch
  `claude/episode-4-farmers` (stacked on `claude/episode-3`). `pipeline/farmers.py` is the sim;
  `episodes/ep04_farmers.py` the script, voiced in george (40.7 s, `renders/ep04_farmers/
  narration_flow.wav`), waiting for Dean to listen. Checked: in the record setup the mess peaks
  at 164 squares, at round 1,181 the farmers meet and each walks back along the other's path,
  the field is spotless at 2,362 (wrong spots), it repeats upside down, and at 4,724 rounds
  (9,448 moves) both are exactly home, forever. Survey: 536 of 1,280 setups come back; 4,724 is
  the longest *found* (don't call it the longest possible). Experiment 3 teased "four crops"
  next; this episode's last line keeps that promise for Experiment 5. Credit the commenter
  (handle needed from Dean) in the description.
- **Experiment 4 rendered 22 Oct** (`renders/ep04_farmers/ep04_farmers.mp4`, 42.7 s; full
  render 47 min). Dean's changes after the sample: no graph (round + SPEED counters instead),
  Daisy the sheep as the helper (eats grass / leaves compost; Joe harvests / plants), and a
  final zoom out over one farm with every experiment so far, labelled (`pipeline/farm_overview.py`).
  Lesson: a flat image at z=0.02 vanishes into the floor from far away (lift it, z=0.4).
  Lesson: Claude Code stops background jobs when the laptop runs low on memory; frames on disk
  are kept, so a render resumes where it stopped.
- **Experiment 4 posted to YouTube 22 Oct 2026, 16:02** (https://youtube.com/shorts/DhlirSjSuRo).
  Instagram: posted 16:44 (https://www.instagram.com/reel/DezOaEAAG8r/) after it first failed
  with "ProcessingFailedError" at the upload step, for every video (even Experiment 3's, which
  had posted that morning), while the login still worked for reads (posting quota 2/100).
  **Fix: Dean disconnected and reconnected Instagram in the studio.** So that error can mean a
  stale login, not the video; reconnect first. This also casts doubt on the "~50 s limit"
  above (Experiment 2's failure may have been the same thing).
- Instagram insights (views, reach) need the `instagram_manage_insights`
  permission; not requested yet.

## Format Dean asked for
- **The narrator explains while it runs:** zoomed in on the grid while
  the rules are explained ("put an ant on a grid of white squares… on white
  it turns right, on black it turns left… then it flips the colour and steps
  forward"), then the camera zooms out as it speeds up, while the narration
  explains the rest.
- **Satisfying visuals.**
- **"Experiment #N" series that evolves:** each episode changes one thing
  from the last and ends on the next question ("Next experiment: what
  happens with three colours?"). See `docs/ideas.md`.
- **3D:** Dean asked for "a bit more 3D", and he liked the result a lot
  (`prototypes/ant_3d.py`, frames in `docs/img/ant_3d_frames.jpg`):
  - tilted camera (pitch 54°) with a slow orbit (yaw -18° → +18°)
  - black squares are raised blocks (height 0.42) that rise and sink over
    7 frames when flipped
  - soft shadows
  - recently flipped squares glow pink, and that trail shortens with speed
  - a small 3D ant that walks smoothly between squares while slow
  - "STEP n" and "SPEED ×n" counters; slow motion into step 9,977, then a
    flash and boom
  - word-by-word captions (current word yellow), rule cards that light up
    for the rule in use
- The 2D version (`prototypes/ant_2d.py`) was the step before. It has the
  same structure.

## How the prototype works (keep this design)
- **Narration-driven:** `SCRIPT` is a list of (caption, mode, target step).
  Each line's mode decides what the sim does while it's spoken: `hold`,
  `single` (one step at a time), `ramp` (exponential), `linear`, `land`
  (brake into a moment), `easein`.
- **Timing:** for now word timing is estimated from word length at ~2.7
  words/s. With a real voice, use Whisper word timings instead, the way
  CLIPPER's `longform_beats.script_timings` does.
- **Camera:** it fits the bounding box of every square touched so far,
  smoothed, so it starts zoomed in and pulls back by itself.
- **Sound:** generated in numpy: a tick per step while slow, a hum whose
  pitch rises with speed, a riser into the highway moment and a boom.
- **Render:** Pillow at 2x then downscaled (no anti-aliased polygon lib), RGB
  frames piped into ffmpeg. The 3D render took ~7 min for 47 s on 4 cloud
  cores.
- **Lesson:** text layers are cached, cropped to their box. Clear the cache
  *before* inserting, not after: clearing after inserting crashed once on
  the lookup.
- **Lesson:** Pillow's `GaussianBlur` needs a plain float, not a numpy
  float.

## Facts checked by simulation (Langton's Ant, RL)
- The highway starts at step **9,977** and repeats every **104 steps**,
  moving 2 cells diagonally per period.
- The claim "nobody has proven it always builds a highway" refers to the
  open question for every finite starting pattern. What *is* proven is that
  the path is always unbounded (Cohen–Kong).
- Dean described the rule as "left on white, right on black". That's the
  mirror image: same behaviour, the highway goes the other way.
- Script rule: every claim in a script must be checked by running the sim
  (or a solid source) before it goes in. No made-up facts.

## Laptop: VS Code + Blender
- **Windows 11**, Intel Core Ultra 7 265U (a 15 W laptop chip, 14 threads),
  Intel built-in graphics, ~15 GB RAM.
- **Be gentle on the laptop** (Dean asked): low priority, 4 render threads,
  half-size EEVEE drafts, one render at a time (never a second Blender or a
  compose alongside a render). Ask before long or full-size batches.
  Renders rest 1 s after each frame (`--pause`, default 1.0) because the
  265U's graphics and CPU share one small cooler, and EEVEE kept the fan
  roaring (Dean, 22 Oct 2026). `blender/ant_scene.py` defaults to this.
- Blender 4.5 LTS is the portable zip in
  `%LOCALAPPDATA%\Programs\Blender\blender-4.5.10-windows-x64\blender.exe`
  (the installer needs admin rights). ffmpeg 9 is installed via winget.
- `blender/ant_scene.py` renders one still: `blender -b -P blender/ant_scene.py
  -- --step 12 --theme farm`. One block mesh is instanced on a point per
  square (geometry nodes). Captions and counters stay in Pillow, laid over
  the frames.
- Benchmark (Oct 2026, 1080x1920, all threads):
  - EEVEE: ~2 s/frame after a ~2 s warm-up, so ~45-50 min per 47 s Short.
  - Cycles CPU, 48 samples: ~35 s/frame, so ~13 h per Short. Not worth it.
- **Farm theme** (Dean's idea, being tried): a small farmer on a grass
  field. On grass he turns right and digs it into dirt; on dirt he turns
  left and it grows back. Ant theme kept as `--theme ant`.
- Keep the Pillow renderer working as the fallback (and for automation
  later on Railway, where there's no GPU).
- CLIPPER is cloned next to this repo at `C:\ANALYSIS\ANALYSIS\CLIPPER`
  (Dean OK'd it) to copy code from.

## Episode pipeline and studio (Oct 2026)
- `episodes/epNN_*.py` holds the script: (caption, spoken text, mode,
  target step), rule cards, title, description.
- The steps: `pipeline/voice.py` (narration + `timing.json`) →
  `blender/render_video.py` (frames) → `pipeline/compose.py` (captions,
  sound, mp4 + thumbnail). Commands are in the README.
- Real line lengths from the voice set the timing. Caption words are
  spread by word length; Whisper alignment is still to do.
- `studio/app.py` (localhost:8765) is where Dean watches and posts.
  - YouTube: CLIPPER's OAuth + resumable upload, category 28, `#Shorts`
    added. The synthetic box is **off** by default (Dean asked, Oct 2026);
    it can still be ticked on the page.
  - Instagram: Facebook Login + resumable upload to rupload.facebook.com,
    because the laptop has no public URL.
  - Posting is always a click by Dean, with a confirm. Never post
    automatically.
- First episode: farm theme. The farmer is **Farmer Joe** (Dean's name,
  Oct 2026); he may become the mascot of the whole channel, with every
  experiment given a farm twist (not decided yet; the Instagram account is
  already named after him). His trail is fresh grass that flashes yellow-green (picked as a
  default, not by Dean yet).
- Accounts connected in the studio (Oct 2026):
  - Instagram: **@farmerjoe1111**, a Creator account linked to the Farmer
    Joe Facebook Page. `INSTAGRAM_USERNAME` in `.env` pins it.
  - YouTube: the **Farmer Joe** channel (`@farmer-joe-1111`, id
    UCW4elsuFZaMRHhMRq6hKGZA). It showed as "Caught On Code" at first: that
    was the same channel under its old name.
- **Instagram upload limit (found 21 Oct 2026):** through the API, Reels up
  to ~50 s upload; 55 s and longer fail with "ProcessingFailedError /
  Request processing failed" (size isn't the cause: 23 MB at 63 s fails,
  27 MB at 45 s works). Undocumented, measured by test uploads with
  `publish_reel(..., publish=False)`, which never posts. Longer videos: post
  from the phone app, or keep episodes under ~50 s.
- **Episode 2 posted to YouTube 21 Oct 2026, 21:45**
  (https://youtube.com/shorts/OyYem3ntT3Y). Instagram failed (too long).
- **Episode 1 posted 21 Oct 2026, 15:45**, public on both, via "Post to
  both": YouTube https://youtube.com/shorts/z1UEqgtLkpM and Instagram
  https://www.instagram.com/reel/Dewi-t-ErwB/. Next: Episode 2, "what
  happens when Joe plants a third crop?" (check the 3-colour rule by
  simulation first), and give the video Joe the profile picture's face
  (eyes, cheeks, moustache).

- **Episode 2 (Oct 2026):** Joe narrates himself (first person), plants
  wheat (rule RLR, no highway in 2M simulated steps; Wikipedia says it's
  unknown whether RLR ever builds one), trips near the end (`trip` mode),
  and the conclusion zooms out over one farm with Episode 1's field rising
  beyond today's, each labelled. Dean liked the trip gag and the bald head
  under the hat.
- **Series plan (Dean, Oct 2026):** Joe runs a *different* experiment each
  episode on his farm (not 8 ant episodes). Order: Experiment 3 lost sheep
  (random walk), then four crops / crop circle (LLRR, check symmetry first),
  Monty Hall barns, golden-angle sunflowers. Episode 2's last line teases
  the sheep.
- **Experiment 3 facts (checked):** Pólya (1921): a random walk on a flat
  grid returns home with probability 1; in 3D only about 34% (Wikipedia,
  "Random walk", citing MathWorld). Kakutani: "A drunk man will find his
  way home, but a drunk bird may get lost forever" (via Durrett,
  *Probability: Theory and Examples*). Our sim, 2,000 walkers × 200,000
  steps: 2D 80% home and still rising; 3D 36% and flat. Not checked yet:
  anything about *how long* it takes on average (don't claim it).
- **Pacing (Dean, after Episode 2):** it "takes too long to start and speed
  up" and "the voice over did not flow". From Experiment 3: open on action in
  the first 1-2 s, rules in 1-2 quick lines, speeding up by ~6-8 s; voice
  whole paragraphs in one go (no per-line gaps or MIN_DUR padding) and
  drive sim cues and captions from Whisper word timings; aim for < 50 s.
- **Experiment 3 voice (22 Oct):** Dean picked take A (`narration_flow.wav`,
  the whole script voiced in one go, 36.8 s) and the name Daisy. His rule:
  "don't generate it too long", with Joe describing what's happening while
  the experiment starts, then speeding up more and more to the end.
- **From Experiment 3, Dean wants to try a more amateur, personal feel.**
  The polished look is "very good", but he wants it less slick. Try a few
  different setups and show samples before committing.

## Voice
- **Farmer Joe's voice: Pocket TTS `george` again (from Experiment 3).**
  Episode 2 used a Kokoro blend (michael 55% + santa 45%); Dean didn't like
  it after hearing it in the finished video ("rather go back to the
  original used in experiment one"). Episode 2 stays as posted, pinned with
  `VOICE` in its episode file. Remember the CC-BY credit line for george in
  every description. Keep voices natural: pitch-shifted "cartoon" voices
  sounded weird to him.
- **Episode 1's voice: Kyutai Pocket TTS preset `george`.** Dean's
  friend wasn't available, and Dean has no good mic, so he picked from 8
  free voices (`voice/samples.py`, Kokoro + Pocket presets).
  - `george` is VCTK speaker p315, licensed CC-BY-4.0: commercial use is
    OK, but credit it in every video description, e.g. "Narration voice:
    Kyutai Pocket TTS, voice from the VCTK corpus (CC-BY-4.0)".
  - Use `model.get_state_for_audio_prompt("george")`. On Windows, run
    Python in UTF-8 mode (`-X utf8`), or pocket_tts crashes reading its
    config.
  - `HF_TOKEN` is in `.env` (gitignored). Packages are in `.venv`.
  - Avoid the Pocket presets from the `expresso/` and `ears/` folders: they
    are non-commercial.
- If a friend's cloned voice is used later: only with his OK. Record his
  consent with the sample, like CLIPPER's `/voices` page (`consent` in
  `voice.json`). Samples live in `voices/` (gitignored, never committed).
- Reuse CLIPPER's `clipper/voice_clone.py`:
  - Kyutai Pocket TTS, CPU, ~0.6 GB RAM, CC-BY-4.0.
  - Needs `HF_TOKEN` from an account that accepted the terms at
    huggingface.co/kyutai/pocket-tts.
  - `spoken_text` spells numbers out ("9,977" → "nine thousand nine
    hundred seventy-seven"). Captions keep digits.
  - The misread check (Whisper transcript vs script) also comes from
    there.
- On YouTube, a cloned voice of someone else needs the altered/synthetic
  content label (`status.containsSyntheticMedia`, as CLIPPER sets it for
  friends' voices). For the stock `george` voice, check YouTube's current
  rule before the first upload.

## Pieces in CLIPPER worth copying (paths in that repo)
- `clipper/voice_clone.py`: voice cloning and number spelling.
- `clipper/longform_beats.py`: aligning Whisper word timings to a script.
- `clipper/captions.py`: ASS captions, if we switch from drawn captions.
- `clipper/youtube_upload.py`: upload, `publish_at` scheduling,
  thumbnails, the synthetic-media flag.
- `clipper/ball_evolution.py` / `ball_sounds.py`: numpy sound design,
  recipe variety, `pick_seed` (simulating without drawing to pick good
  runs).
- `webapp/main.py` Ball Evolution autopilot: for later, if Dean wants
  automatic posting (Railway cron waker, `EXTRA_YOUTUBE_ACCOUNTS`).

## YouTube risks (Dean was told)
- YouTube's July 2025 "inauthentic / repetitive content" rules and the
  1 Oct 2026 Shorts change punish template-looking, mass-produced videos.
- What keeps this safe:
  - each video is a genuinely different experiment
  - real explanation in the narration
  - true, checked facts
  - Dean reviews each one
- Everything visual is our own maths render, and the fonts are OFL, so
  there's no copyright risk there.

## Other preferences (same as CLIPPER)
- No paid signups or subscriptions. Check for free options first.
- For big visual changes, show a mockup or sample render first.
- Don't say a claim is proven without checking it.
