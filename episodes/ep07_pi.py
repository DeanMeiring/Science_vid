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

# Dean (23 Oct): "Captain Obvious" Joe -- the same voice, but deadpan, short sentences, over-explaining the
# obvious. The maths and the numbers stay exactly as checked.
NARRATION = [
    ("setup",  "Experiment number 7. I'm finding pi. With hay. This is hay. It's dried grass. I did not dry it. "
               "The sun did. Between the boards: cracks. That's where cracks go. Each board is one straw wide. "
               "I checked. Twice.",
               "Experiment number seven. I'm finding pie. With hay. This is hay. It's dried grass. I did not dry it. "
               "The sun did. Between the boards: cracks. That's where cracks go. Each board is one straw wide. "
               "I checked. Twice."),
    ("throw",  "I throw a straw. It lands across a crack. Gold. I throw another. It doesn't. Not gold. Still a straw.", None),
    ("trick",  "Now the trick: two times all the straws, divided by the gold ones, gets closer and closer to pi. "
               "Not the pie you eat. Daisy. Daisy, no.",
               "Now the trick: two times all the straws, divided by the gold ones, gets closer and closer to pie. "
               "Not the pie you eat. Daisy. Daisy, no."),
    ("count",  "Ten straws: 2.5. Wrong. A hundred: 2.99. Closer. A thousand: 3.03. A hundred thousand straws... 3.14!",
               "Ten straws: two point five. Wrong. A hundred: two point nine nine. Closer. A thousand: three point oh three. "
               "A hundred thousand straws... three point one four!"),
    ("end",    "I did not plan the mountain. A guy named Buffon worked this out in the 1700s. Before tractors. "
               "See y'all next harvest!",
               "I did not plan the mountain. A guy named Buffon worked this out in the seventeen hundreds. "
               "Before tractors. See y'all next harvest!"),
]

STRAWS = dict(seed=1, n=100000)

TITLE = "Farmer Joe finds pi... with a bale of hay?!"
DESCRIPTION = """Experiment #7: pi from a bale of hay.

Farmer Joe's floorboards are exactly one straw wide. He drops straws at random and counts how many land across a crack. Two times the number of straws, divided by the number that cross, gets closer and closer to pi: 10 straws give 2.5, 100 give 2.99, 1,000 give 3.03, and 100,000 straws give 3.14!

This is Buffon's needle, first posed in the 18th century by Georges-Louis Leclerc, Comte de Buffon: a straw as long as the gap between the cracks crosses one with probability 2/pi.

Narration voice: Kyutai Pocket TTS, voice from the VCTK corpus (CC-BY-4.0).
#maths #pi #probability #buffonsneedle #farmerjoe"""
