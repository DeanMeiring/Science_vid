"""Experiment #8: what grows if you plant it? (Dean's gag, 23 Oct; "Get 3 helpers" is parked for later.)

Deadpan Joe plants things and waits (time-lapses): a mustard seed, an apple seed, a mustard seed and an
apple seed together, and a rusty wheelbarrow tyre. The "law" is a real one: biogenesis, life only comes
from life. Opens on a hook ("If you...").

Facts checked (Oct 2026):
- Black mustard (Brassica nigra) is an annual, "up to 1.2 metres (4 ft) tall" (Wikipedia, "Brassica nigra").
  So: four feet in one season, not a tree.
- Apples grown from seed don't copy their parents: "seedling apples do not 'breed true'" (Wikipedia, "Apple").
- Mustard (cabbage family, Brassicaceae) and apple (rose family, Rosaceae) aren't in the same family;
  hybrids are "normally from within the same genus", and between families "extremely rare" (Wikipedia,
  "Hybrid (biology)"; its examples are animals). So: you won't get a mustard-apple.
- Biogenesis: living things come from living things, the opposite of spontaneous generation; Pasteur's
  swan-neck flask experiments (1859) (Wikipedia, "Biogenesis", "Swan neck flask").
- A tyre left in the ground grows nothing itself; weeds come up round it from seeds already in the soil.
- NOT claimed: how many years an apple seedling takes to fruit (not in the source).
"""

EXPERIMENT = 8
THEME = "farm"
# VOICE: Farmer Joe's default (pocket:george)

NARRATION = [
    ("mustard", "If you plant a mustard seed, you get mustard. Four feet of it. In one season.", None),
    ("apple",   "If you plant an apple seed, you get an apple tree. Just not the same apple. Apple seeds don't copy their parents.", None),
    ("both",    "Plant them together, and you will not get a mustard-apple. They're not even in the same family.", None),
    ("tyre",    "And if you plant a rusty wheelbarrow tyre, and wait two years... nothing. Well. Weeds. Those were seeds already.",
                "And if you plant a rusty wheelbarrow tire, and wait two years... nothing. Well. Weeds. Those were seeds already."),
    ("law",     "Scientists call it biogenesis: life only comes from life. Louis Pasteur showed it in 1859, with a flask of soup. "
                "I'm still waiting for my wheelbarrow. See y'all next harvest!",
                "Scientists call it biogenesis: life only comes from life. Louis Pasteur showed it in eighteen fifty-nine, "
                "with a flask of soup. I'm still waiting for my wheelbarrow. See y'all next harvest!"),
]

TITLE = "Farmer Joe planted a wheelbarrow tyre. Two years later..."
DESCRIPTION = """Experiment #8: what grows if you plant it?

Plant a mustard seed and you get mustard: up to four feet of it in one season. Plant an apple seed and you get an apple tree, just not the same apple (apples grown from seed don't copy their parents; that's why orchards graft). Plant them together and you won't get a mustard-apple: they're not even in the same plant family. And plant a rusty wheelbarrow tyre... nothing grows. Just weeds, from seeds already in the soil.

That's biogenesis: life only comes from life. Louis Pasteur showed it with his swan-neck flask experiments in 1859.

Narration voice: Kyutai Pocket TTS, voice from the VCTK corpus (CC-BY-4.0).
#science #biology #plants #farmerjoe"""
