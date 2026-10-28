"""Experiment #7: pi from a bale of hay (Buffon's needle). Joe drops straws on his barn floor.

Promised at the end of Experiment 6 ("Next experiment: I'll find pi with a bale of hay!"). Dean wanted
this one to feel different from the grid episodes: Joe doing a farm job, with more 3D design.
The "Next experiment" line is left out until Dean picks Experiment 8 (add it to the "end" beat and
re-voice).

Facts checked (Oct 2026):
- Wikipedia, "Buffon's needle problem": first posed in the 18th century by Georges-Louis Leclerc,
  Comte de Buffon; a needle as long as the gap between lines (l = t) crosses a line with
  probability 2/pi, so pi ~= 2 x needles / crossings.
- Our simulation (pipeline/hay.py, seed 1): 63.6% of 100,000 straws cross (2/pi = 63.66%);
  10 straws -> 2.50, 100 -> 2.99, 1,000 -> 3.03, 10,000 -> 3.13, 100,000 -> 3.143.
- It only gets CLOSER to pi with more straws (slowly); never claimed to be exact.
- "Before tractors": the first tractors (steam) came in the 19th century, after Buffon (18th).
- Hay is dried grass (true); "the sun did" the drying (field-dried hay); jokes, but not wrong.
"""

EXPERIMENT = 7
THEME = "farm"
# VOICE: Farmer Joe's default (pocket:george)

# Dean (23 Oct): open on a hook ("If you...", better for retention), not "Experiment number 7" (that's
# on screen). Deadpan Joe, straight into the action: two or three throws, then "Now: faster" and
# it escalates: Joe spam-throws (100), a wheelbarrow dumps (1,000), a tractor dumps (10,000), a combine
# harvester (100,000; our own design, no brand colours). Every load lands on the planks first (that's
# where it's counted), then hops onto the heap, which grows into a mountain. The maths and the numbers stay as checked.
NARRATION = [
    ("throw",  "If you throw hay at a floor, you can find pi. Watch. This straw lands across a crack: gold. "
               "This one doesn't: not gold. My boards are exactly one straw wide.",
               "If you throw hay at a floor, you can find pie. Watch. This straw lands across a crack: gold. "
               "This one doesn't: not gold. My boards are exactly one straw wide."),
    ("fast",   "Now: faster. Two times all the straws, divided by the gold ones, gets closer and closer to pi.",
               "Now: faster. Two times all the straws, divided by the gold ones, gets closer and closer to pie."),
    ("count",  "Ten straws: 2.5. A hundred: 2.99. A thousand: 3.03. Ten thousand: 3.13. A hundred thousand... 3.14!",
               "Ten straws: two point five. A hundred: two point nine nine. A thousand: three point oh three. "
               "Ten thousand: three point one three. A hundred thousand... three point one four!"),
    ("end",    "Not the pie you eat, Daisy. I did not plan the mountain. A guy named Buffon worked this out in the 1700s. "
               "Before tractors. See y'all next harvest!",
               "Not the pie you eat, Daisy. I did not plan the mountain. A guy named Buffon worked this out in the "
               "seventeen hundreds. Before tractors. See y'all next harvest!"),
]

STRAWS = dict(seed=1, n=100000)

TITLE = "Farmer Joe finds pi... with a bale of hay?!"
DESCRIPTION = """Experiment #7: pi from a bale of hay.

Farmer Joe's floorboards are exactly one straw wide. He drops straws at random and counts how many land across a crack. Two times the number of straws, divided by the number that cross, gets closer and closer to pi: 10 straws give 2.5, 100 give 2.99, 1,000 give 3.03, and 100,000 straws give 3.14!

This is Buffon's needle, first posed in the 18th century by Georges-Louis Leclerc, Comte de Buffon: a straw as long as the gap between the cracks crosses one with probability 2/pi.

Narration voice: Kyutai Pocket TTS, voice from the VCTK corpus (CC-BY-4.0).
#maths #pi #probability #buffonsneedle #farmerjoe"""
