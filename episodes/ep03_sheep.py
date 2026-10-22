"""Experiment #3: Farmer Joe's sheep wanders off (a random walk). Will she find her way home?

New way of working (Dean's feedback after Episode 2: slow start, choppy voice):
- open on action: Daisy is already wandering in the first second;
- the narration is voiced as ONE flowing track (pipeline/narrate.py), not line by line;
- the animation will follow the voice (word timings), not the other way round;
- under ~50 s (also Instagram's API upload limit).

NARRATION is a list of beats: (cue, caption text, spoken text or None). The cue names what the
picture does during that beat, for the animation later.

Facts checked (Oct 2026):
- George Polya proved in 1921 that a random walk on a flat (2D) grid returns to its start
  with probability 1 ("almost surely"); in 3D the chance is only about 34%.
  Source: Wikipedia, "Random walk" (citing MathWorld, "Polya's Random Walk Constants").
  Our simulation agrees: 2,000 walkers x 200,000 steps: 2D 80% home and still rising,
  3D 36% and flat.
- "A drunk man will find his way home, but a drunk bird may get lost forever": mathematician
  Shizuo Kakutani (Wikipedia, "Random walk", via Durrett, Probability: Theory and Examples).
- NOT claimed: how long it takes on average (not checked).
"""

EXPERIMENT = 3
THEME = "farm"
# VOICE: Farmer Joe's default (pocket:george)

NARRATION = [
    ("wander",  "Experiment number 3. My sheep Daisy wandered off again. Every step, she picks a "
                "random direction. No plan at all.",
                "Experiment number three. My sheep Daisy wandered off again. Every step, she picks a "
                "random direction. No plan at all."),
    ("far",     "A hundred steps. A thousand. She's way out past the barn. Is she ever coming home?", None),
    ("home",    "Yes! In 1921, a mathematician named George Pólya proved it. On a flat field, a random "
                "walker always gets home. Eventually.",
                "Yes! In nineteen twenty-one, a mathematician named George Polya proved it. On a flat field, "
                "a random walker always gets home. Eventually."),
    ("chicken", "But my chicken can fly. Up, down, every direction. And in three dimensions, only about one "
                "in three ever make it back.", None),
    ("quote",   "As one mathematician put it: a drunk man will find his way home, but a drunk bird may get "
                "lost forever.", None),
    ("next",    "Next experiment: four crops. See y'all next harvest!", None),
]

# The walks shown (picked by simulation, Oct 2026; counters on screen are these runs' real results):
# - Daisy, seed 583: never home until step 6,470 (lands on "Yes!"); 68 squares out at step 1,000,
#   110 at her furthest.
# - the herd: 40 sheep, seed 102, 20,000 steps each: 33 of 40 get home in that time.
# - the chickens: 12 in 3D, seed 204, 4,000 steps each: exactly 4 of 12 get home (one in three).
DAISY = dict(seed=583, home_step=6470)
HERD = dict(seed=102, sheep=40, steps=20000)
FLOCK = dict(seed=204, chickens=12, steps=4000)

TITLE = "Farmer Joe's sheep wandered off. Will she ever come home?"
DESCRIPTION = """Experiment #3: a random walk on Farmer Joe's farm.

Every step, Daisy the sheep picks a random direction. Will she ever find her way home? In 1921 George Pólya proved that on a flat field a random walker always gets home eventually. But in three dimensions (like Joe's flying chicken) only about 34% ever make it back.

"A drunk man will find his way home, but a drunk bird may get lost forever." (Shizuo Kakutani)

Next experiment: four crops.

Narration voice: Kyutai Pocket TTS, voice from the VCTK corpus (CC-BY-4.0).
#maths #science #randomwalk #probability #farmerjoe"""
