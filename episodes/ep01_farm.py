"""Experiment #1: Langton's Ant, as Farmer Joe on a grass field.

Each line: (caption, what the voice says, sim mode while it's spoken, step reached by the end).
Captions keep digits; the voice gets numbers spelled out.
Modes: hold, single (one step at a time), ramp (exponential), linear, land (brake into a
moment), easein.

Facts checked by simulation (Oct 2026, this rule: grass -> turn right, dirt -> turn left):
- the highway starts at step 9,977 and repeats every 104 steps (no shorter period),
  moving 2 squares diagonally per period.
- "nobody has proven it always ends this way": the open question is whether every finite
  starting pattern ends in a highway. (Proven: the path is always unbounded, Cohen-Kong.)
"""

EXPERIMENT = 1
THEME = "farm"
HIGHWAY = 9977

SCRIPT = [
    ("Experiment number 1.", "Experiment number one.", "hold", 0),
    ("Meet Farmer Joe. He's standing on a field of grass.", None, "hold", 0),
    ("On grass, he turns right.", None, "single", 5),
    ("On dirt, he turns left.", None, "single", 10),
    ("Then he digs up the grass, or replants the dirt, and steps forward.", None, "single", 17),
    ("That's it. Two rules. Now let's speed it up.", None, "ramp", 250),
    ("For thousands of steps, Joe just makes a mess.", None, "ramp", 3500),
    ("No pattern. No order. Just chaos.", None, "linear", 9600),
    ("Until step 9,977...", "Until step nine thousand, nine hundred and seventy-seven...", "land", HIGHWAY),
    ("Out of nowhere, Joe starts building a highway.", None, "easein", 12000),
    ("The same 104 steps, over and over, forever.",
     "The same one hundred and four steps, over and over, forever.", "linear", 15000),
    ("Start on any messy field, and nobody has proven it always ends this way.", None, "linear", 16200),
    ("Next experiment: what happens when Joe plants a third crop?", None, "linear", 16800),
]

# rule cards shown while the rules are explained (lines 2-4)
RULES = [("GRASS", "TURN RIGHT"), ("DIRT", "TURN LEFT")]
RULE_LINES = (2, 4)
HIGHWAY_LINE = 8

TITLE = "Farmer Joe follows 2 rules. At step 9,977 something strange happens"
DESCRIPTION = """Experiment #1: Langton's Ant, as Farmer Joe.

On grass Joe turns right, on dirt he turns left, and every square he leaves flips: grass is dug into dirt, dirt grows back to grass. For about 10,000 steps it's pure chaos. Then, at step 9,977, he starts building a "highway": the same 104 steps, over and over, forever.

Nobody has proven that every starting field ends in a highway. It's still an open problem.

Next experiment: what happens when Joe plants a third crop?

Narration voice: Kyutai Pocket TTS, voice from the VCTK corpus (CC-BY-4.0).
#maths #science #langtonsant #emergence"""
