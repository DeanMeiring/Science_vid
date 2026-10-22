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

## Where we left off (end of 21 Oct 2026)
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

  YouTube is barely showing the Shorts while Instagram grows. Asked Dean to
  check in YouTube Studio that each video shows as a Short, its traffic
  sources (Shorts feed?), and any warning icons. If they're all fine, it's
  probably new-channel slowness; a steady rhythm (every 2-3 days) helps.
  22 Oct, later: Experiment 3 (the sheep) is getting a lot of views on Instagram;
  YouTube still ~0. Dean's call: keep posting consistently on both.
  Checked in YouTube Studio (22 Oct): all three show as Shorts, no warnings or
  notifications. So it's new-channel slowness, not a problem with the uploads.
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
