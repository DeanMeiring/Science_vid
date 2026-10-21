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
  half-size EEVEE drafts, one render at a time. Ask before long or full-size
  batches. `blender/ant_scene.py` defaults to this.
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
    added, the synthetic box ticked by default.
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
- **Episode 1 posted 21 Oct 2026, 15:45**, public on both, via "Post to
  both": YouTube https://youtube.com/shorts/z1UEqgtLkpM and Instagram
  https://www.instagram.com/reel/Dewi-t-ErwB/. Next: Episode 2, "what
  happens when Joe plants a third crop?" (check the 3-colour rule by
  simulation first), and give the video Joe the profile picture's face
  (eyes, cheeks, moustache).

## Voice
- **Chosen voice (Oct 2026): Kyutai Pocket TTS preset `george`.** Dean's
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
