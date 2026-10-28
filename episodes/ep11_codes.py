"""Experiment #11: Joe's crop codes (Dean's idea, 26 Oct: "move in different patterns like LLRRLL").

Same walking rule as Experiments 1, 2 and 5, longer codes: each letter is one crop; on a square with crop i
Joe turns right (R) or left (L) as letter i says, plants crop i + 1 (wrapping round), and steps forward.
A showcase of four codes that do completely different things; next experiment should be something else
(not the walking rule again).

Facts checked (pipeline/codes.py, 26 Oct 2026; Wikipedia "Langton's ant"):
- RL (Experiment 1): our detector finds the highway from step 9,976, every 104 steps (the known 9,977;
  one step apart from how steps are counted).
- RLLLLRRRLLL (11 letters): a messy start, then a clean square spiral (rings) by ~100,000 steps, still a
  spiral at 1,000,000 (our runs; not in Wikipedia: "our find", don't say it's famous).
- LRRRRRLLR: "fills space in a square around itself" (Wikipedia); our runs: a growing square to 1,000,000.
- RRLLLRLLLRRR: "creates a filled triangle shape that grows and moves after about 15,900 iterations"
  (Wikipedia); our runs: the mess walks off dragging a growing triangle (clear by 30,000).
- RRLRLLRLRR: a mess, then from step 232,645 a highway repeating every 936 steps, 2 squares diagonally
  each time (our run; "our find").
- Gajardo et al. (2000): "a construction that calculates any boolean circuit" using the trajectory of a
  single ant (Wikipedia). Said as: "this walk can work like a computer circuit".
- NOT claimed: that nobody can predict a code without running it (no source), that any pattern lasts
  forever, or that the highway is "nine times wider".
"""

EXPERIMENT = 11
THEME = "farm"

NARRATION = [
    ("hook",     "If I change the letters in my crop code, the whole field goes crazy.", None),
    ("rule",     "Each crop tells me which way to turn. R, turn right. L, turn left. Then I plant the next crop.", None),
    ("spiral",   "This code has eleven letters. Chaos... then a perfect square spiral.", None),
    ("square",   "This one just keeps filling a square.", None),
    ("triangle", "This one makes a mess, then walks off, dragging a giant triangle behind it.", None),
    ("highway",  "And this one makes a mess for 232,000 steps... then builds a highway.",
                 "And this one makes a mess for two hundred and thirty-two thousand steps... then builds a highway."),
    ("end",      "Same farmer, same rule, different letters. In 2000, mathematicians showed this walk can work like a "
                 "computer circuit. I just wanted carrots.",
                 "Same farmer, same rule, different letters. In two thousand, mathematicians showed this walk can work "
                 "like a computer circuit. I just wanted carrots."),
]

TITLE = "Farmer Joe changed one code. The field went crazy..."
DESCRIPTION = """Experiment #11: Farmer Joe's crop codes.

Same rule as Experiment 1: each crop tells Joe which way to turn (R = right, L = left), then he plants the next crop and steps forward. Only the code changes:
- RLLLLRRRLLL: chaos, then a perfect square spiral
- LRRRRRLLR: keeps filling a square
- RRLLLRLLLRRR: a mess that walks off dragging a giant triangle
- RRLRLLRLRR: 232,000 steps of mess, then a highway

These are "Langton's ant" rules with more colours (Greg Turk and Jim Propp's extension). In 2000, Gajardo et al. showed a single ant's path can calculate any boolean circuit.

Narration voice: Kyutai Pocket TTS, voice from the VCTK corpus (CC-BY-4.0).

#math #science #langtonsant #farmerjoe"""
