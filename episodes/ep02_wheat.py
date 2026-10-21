"""Experiment #2: Farmer Joe plants a third crop (Langton's ant with 3 colours, rule RLR).

Joe narrates himself from this episode on, in his own voice (pipeline/tts.py FARMER_JOE).

Each line: (caption, what the voice says, sim mode while it's spoken, step reached by the end).
Modes as in Episode 1, plus "trip": the sim pauses, the camera flies in, Joe trips over his
own crops, his hat rolls off, he gets up and puts it back on. In the conclusion (COMPARE_LINE)
Episode 1's field (same rule, re-simulated to its last step) rises next to today's on one farm.

Facts checked (Oct 2026):
- Rule RLR (grass right, dirt left, wheat right; each square cycles grass -> dirt -> wheat
  -> grass): our simulation ran 2,000,000 steps and never built a highway (it grew to
  about 275 x 275 squares). Same code reproduces Episode 1 exactly (9,977 / 104).
- "Nobody knows if this one ever builds a highway": Wikipedia, Langton's ant: "RLR: Grows
  chaotically. It is not known whether this ant ever produces a highway." (extension by
  Turk and Propp; Gale, Propp, Sutherland, Troubetzkoy, "Further Travels with My Ant",
  Mathematical Intelligencer 1995).
- Episode 1 (2 crops, RL) built a highway, at step 9,977 (now only in the description).
"""

EXPERIMENT = 2
THEME = "farm"
RULE = "RLR"                     # turn on grass, dirt, wheat
CROPS = ["GRASS", "DIRT", "WHEAT"]

SCRIPT = [
    ("Howdy! Farmer Joe here. Look at my little hat.", None, "hold", 0),
    ("Today I'm planting a third crop: wheat!", None, "single", 3),     # he starts farming straight away
    ("On grass, I turn right.", None, "single", 6),
    ("On dirt, I turn left.", None, "single", 9),
    ("And on wheat, I turn right again.", None, "single", 12),
    ("Every square I leave grows to the next crop. Grass, dirt, wheat, then back to grass.",
     None, "single", 21),
    ("Alright. Let's speed it up!", None, "ramp", 400),
    ("10,000 steps, and it's just a mess.", "Ten thousand steps, and it's just a mess.", "ramp", 10000),
    ("100,000 steps. Still no highway.", "A hundred thousand steps. Still no highway.", "ramp", 100000),
    ("A million steps. Still nothing!", "A million steps. Still nothing!", "linear", 1000000),
    ("Whoa! ...I'm okay. Hat's okay too.",
     [("Whoa!", 1.3), ("I'm okay.", 1.4), ("Hat's okay too.", 0.0)], "trip", 1000000),
    ("Here's the thing: nobody knows if this one ever builds a highway.", None, "linear", 1060000),
    ("Two crops gave me a highway. Three crops... just a mess.",
     "Two crops gave me a highway. Three crops... just a mess.", "linear", 1110000),
    ("Do y'all think I'll ever get out of this mess? Tell me in the comments!", None, "linear", 1160000),
    ("Next experiment: four crops. See y'all next harvest!", None, "linear", 1200000),
]

# rule cards shown while the rules are explained (lines 2-5)
RULES = [("GRASS", "TURN RIGHT"), ("DIRT", "TURN LEFT"), ("WHEAT", "TURN RIGHT")]
RULE_LINES = (2, 5)
HIGHWAY = None                    # no highway this time (as far as anyone knows)
TRIP_LINE = 10                    # near the end, at a million steps
# conclusion: the camera zooms out and Episode 1's field rises out of the grass on the same farm,
# just beyond today's, each with a label above it
COMPARE_LINE = 12
COMPARE_WITH = dict(rule="RL", steps=16800, title="EXPERIMENT #1", sub="2 CROPS · HIGHWAY")
COMPARE_LABEL = dict(title="EXPERIMENT #2", sub="3 CROPS · STILL A MESS")

TITLE = "Farmer Joe plants a third crop. A million steps later..."
DESCRIPTION = """Experiment #2: Langton's Ant with 3 colours, as Farmer Joe's farm.

On grass Joe turns right, on dirt he turns left, on wheat he turns right again, and every square he leaves grows to the next crop: grass, dirt, wheat, then grass again.

With two crops he built a highway at step 9,977. With three (the rule "RLR") he's still lost in the mess after a million steps, and nobody knows if this one EVER builds a highway. It's an open question.

Do you think he'll ever get out? Next experiment: four crops.

Narration voice: Kokoro TTS (Apache-2.0).
#maths #science #langtonsant #emergence #farmerjoe"""
