"""Experiment #5: four crops (rule LLRR). Every so often the whole field is a perfect mirror image.

Promised at the end of Experiment 4 ("Next experiment: four crops"). Same way of working as
Experiments 3-4: open on action, one flowing voice track, the animation follows the word timings,
under ~50 s.

Facts checked (pipeline/crops.py, Oct 2026):
- Rule: grass L, dirt L, wheat R, pumpkins R; the square Joe leaves moves on to the next crop.
- "Some of these extended Langton's ants produce patterns that become symmetric over and over
  again"; a sufficient condition is turns in pairs (LL, RR) -- proved (the proof uses Truchet
  tiles). Source: Wikipedia, "Langton's ant", citing Gale, Propp, Sutherland & Troubetzkoy,
  "Further Travels with My Ant" (Mathematical Intelligencer, 1995).
- Our simulation: every time Joe is back on his first square facing the way he started, the field
  is a perfect mirror image (4,484 of 4,484 times in 200,000 steps; never when he's back facing
  the other way, 0 of 752). Step 1,000 is one of those moments, so is 10,012 and 100,044.
  By step 100,000 it has happened 2,632 times ("more than 2,600").
- NOT claimed: who proved it or when (Wikipedia doesn't say), or anything about a highway.
"""

EXPERIMENT = 5
THEME = "farm"
# VOICE: Farmer Joe's default (pocket:george)

NARRATION = [
    ("rules",  "Experiment number 5: four crops! On grass, I turn left. On dirt, left again. On wheat, I turn "
               "right. On pumpkins, right again. And every square I leave grows the next crop.",
               "Experiment number five: four crops! On grass, I turn left. On dirt, left again. On wheat, I turn "
               "right. On pumpkins, right again. And every square I leave grows the next crop."),
    ("mess",   "At first, it's just a mess. But every time I'm back on my first square, facing the way I "
               "started... a perfect mirror image!", None),
    ("again",  "A thousand steps: mirror. Ten thousand: mirror again. By a hundred thousand steps, it's "
               "happened more than 2,600 times.",
               "A thousand steps: mirror. Ten thousand: mirror again. By a hundred thousand steps, it's "
               "happened more than two thousand six hundred times."),
    ("proof",  "Mathematicians proved it: when the turns come in pairs, the pattern turns symmetric, over and over.", None),
    ("next",   "My very own crop circle! Next experiment: three barns, one prize. See y'all next harvest!", None),
]

STEPS = 100044                 # the run ends on a mirror moment

TITLE = "Farmer Joe plants four crops... and makes a perfect crop circle?!"
DESCRIPTION = """Experiment #5: four crops on Farmer Joe's farm.

The rule: on grass and dirt, Joe turns left; on wheat and pumpkins, he turns right. Every square he leaves grows the next crop. At first it looks like a mess, but every time Joe is back on his first square, facing the way he started, the whole field is a perfect mirror image. By 100,000 steps it has happened more than 2,600 times.

Mathematicians proved that ants whose turns come in pairs (like left-left-right-right) make patterns that become symmetric over and over again (see Gale, Propp, Sutherland & Troubetzkoy, "Further Travels with My Ant", 1995).

Next experiment: three barns, one prize.

Narration voice: Kyutai Pocket TTS, voice from the VCTK corpus (CC-BY-4.0).
#maths #science #langtonsant #symmetry #farmerjoe"""
