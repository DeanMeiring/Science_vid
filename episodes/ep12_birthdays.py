"""Experiment #12: birthday cows (the birthday paradox).

Script revised 27 Oct 2026 after Codex's review (docs/ep12_review.md): Codex's shorter proposal, which
Dean approved with "check the handoff and then build". The first take of the old, longer script
(42.2 s) was a listening sample only.

Model (said once in the video): every birthday is independent and equally likely, 365 days, no leap day.

Facts checked (pipeline/birthdays.py, seed 12 fixed before looking, 100,000 herds per size, 27 Oct 2026):
- Exact chance that any two share a birthday: 22 cows 47.57%, 23 cows 50.73%. 23 is the smallest herd
  above 50%. Said as "just under half" / "just over half"; the cards show the exact 47.6% / 50.7%.
- Simulated (each herd size has its own stream from the seed; SE = one standard error, 95% = +/- 1.96 SE):
  22 cows 47,798 / 100,000 = 47.80% (95% 47.49-48.11%); 23 cows 50,617 / 100,000 = 50.62% (95% 50.31-50.93%).
- The 23-cow tally on screen is that run's running count, early dip and all: 4/10, 47/100, 506/1,000,
  5,118/10,000, 50,617/100,000. Said: "fifty thousand, six hundred and seventeen... fifty point six percent".
  On screen the simulated 50.6% and the exact 50.7% have separate labels.
- Herd 1 of the 23-cow run is the herd on screen (in run order, not picked): cows 8 and 13 (1-based)
  share 30 Aug; there is no other pair. The match is already there among the first 13 cows, so the video
  never shows the 23rd cow "making" it: 23 is where over half of random herds have SOME match, not the
  first size a match can happen. Herds 2-5: no match.
- 23 cows make 23 x 22 / 2 = 253 possible pairs: the number of chances, not independent events.
- One particular cow is a different question: it first passes 50% with 253 OTHER cows (254 in all;
  50.05%). Description only.
- Cakes: one per herd with a match = 50,617 (on screen).
- NOT claimed: anything about real herds' birthdays. (One made-up season, 80% of births in 90 days, gives
  85.0% for 23 cows, but that one example doesn't prove a general rule: not in the description.)
"""

EXPERIMENT = 12
THEME = "farm"
ALIGN_SPELL_NUMBERS = True       # pipeline/align.py: match "23" / "253" / "50.6%" to Whisper's digits

NARRATION = [
    ("hook",   "How many cows before two probably share a birthday? Guess.", None),
    ("model",  "In my simulation, birthdays are independent, with all 365 days equally likely.",
               "In my simulation, birthdays are independent, with all three hundred and sixty-five days equally likely."),
    ("maths",  "22 cows: just under half of herds have a match. 23: just over half.",
               "Twenty-two cows: just under half of herds have a match. Twenty-three: just over half."),
    ("pair",   "This pair shares August 30th. But let's test 100,000 herds.",
               "This pair shares August thirtieth. But let's test a hundred thousand herds."),
    ("tally",  "50,617 had a match. 50.6%.",
               "Fifty thousand, six hundred and seventeen had a match. Fifty point six percent."),
    ("why",    "Why? 23 cows make 253 possible pairs. Any pair can match.",
               "Why? Twenty-three cows make two hundred and fifty-three possible pairs. Any pair can match."),
    ("gag",    "A cake for every matching herd? I'm out of flour.", None),
]

TITLE = "How many cows before two share a birthday?"
DESCRIPTION = """Experiment #12: Farmer Joe's birthday cows (the birthday paradox).

With just 23 cows, it's more likely than not that two share a birthday. The exact chance is 50.7%; in our simulation of 100,000 herds, 50,617 (50.6%) had a match. With 22 cows it's 47.6%.

Why so few? 23 cows make 253 possible pairs, and any pair can match. That's a different question from "does another cow share MY cow's birthday?" For that, you'd need 253 other cows (254 in all) to pass 50%.

The model: every birthday is independent and equally likely, over 365 days (leap day left out). This is an ideal model, not measured cow-birthday data; real farms may have seasonal births.

Narration voice: Kyutai Pocket TTS, voice from the VCTK corpus (CC-BY-4.0).

#math #science #birthdayparadox #probability #farmerjoe"""
