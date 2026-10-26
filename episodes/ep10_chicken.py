"""Experiment #10: the chicken and the barns (the "chaos game"; picked by Dean on 26 Oct from the ideas list).

A chicken hops halfway towards a barn picked at random, over and over, leaving a footprint each time.
With three barns, the footprints draw the Sierpinski triangle. With four (a square), no pattern.
Same recipe as Experiments 4 and 9: a clear question, a counter racing up, a surprising, checked answer.

Facts checked (pipeline/chaos.py, 26 Oct 2026; Wikipedia "Sierpinski triangle" and "Chaos game"):
- Three barns, halfway each hop, starting inside the triangle: the footprints converge on the Sierpinski
  triangle ("Using a regular triangle and the factor 1/2 will result in the Sierpinski triangle").
  By hand a rough outline appears after about a hundred points (Wikipedia); our renders show it.
- 1,000,000 hops (seed 1): 0 footprints after the first hop in the middle hole, and 0 in any hole down to
  8 levels (after that many hops). From anywhere inside, one hop lands in a corner half-size copy, so the
  middle is never hit (except its edges).
- The holes keep going: after n hops only (3/4)^n of the triangle is left (Wikipedia: the area tends to zero).
- Described by Waclaw Sierpinski in 1915 (Wikipedia).
- Four barns at the corners of a square, halfway: "the fractal is not visible and the interior of the square
  fills evenly" (Wikipedia, "Chaos game"); our 1,000,000 hops: every 1/64 of the square gets 15,404-15,940
  footprints (mean 15,625).
- NOT claimed: who named the chaos game (Wikipedia doesn't say), or anything about the chicken's speed.
"""

EXPERIMENT = 10
THEME = "farm"

NARRATION = [
    ("hook",  "If my chicken hops halfway to a random barn, over and over, what does she draw?", None),
    ("rule",  "Three barns. Pick one at random, hop halfway there, leave a footprint. And again.", None),
    ("count", "Ten hops: a mess. A hundred: hmm. A thousand. Ten thousand.", None),
    ("tri",   "Triangles, inside triangles, inside triangles. The Sierpinski triangle, from nineteen fifteen. "
              "My chicken drew it by accident.",
              "Triangles, inside triangles, inside triangles. The Sher-pinski triangle, from nineteen fifteen. "
              "My chicken drew it by accident."),
    ("hole",  "And in a million hops, she never once landed in the middle. Not once.", None),
    ("four",  "Four barns? No pattern at all. She just fills the square. Same chicken, same rule, one more barn. "
              "Go figure.", None),
]

TITLE = "Farmer Joe's chicken hopped at random. Then a pattern appeared..."
DESCRIPTION = """Experiment #10: the chicken and the barns.

Three barns. Each hop, the chicken picks a barn at random and hops halfway towards it, leaving a footprint. It looks like a random mess... until the footprints draw triangles inside triangles: the Sierpinski triangle (described by Waclaw Sierpinski in 1915). This is called the "chaos game".

We simulated a million hops: after the first hop, she never once lands in the middle hole, or in any of the smaller holes. With four barns in a square, there's no pattern at all: the square just fills evenly.

Narration voice: Kyutai Pocket TTS, voice from the VCTK corpus (CC-BY-4.0).

#math #science #fractal #farmerjoe"""
