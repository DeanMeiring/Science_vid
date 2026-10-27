"""Experiment #12: birthday cows (the birthday paradox). DRAFT for review: not voiced yet.

Model (said once in the video): every birthday is independent and equally likely, 365 days, no leap day.

Facts checked (pipeline/birthdays.py, seed 12 fixed before looking, 100,000 herds per size, 27 Oct 2026):
- Exact chance that any two share a birthday: 10 cows 11.69%, 20 cows 41.14%, 22 cows 47.57%,
  23 cows 50.73%. 23 is the smallest herd above 50%.
- Simulated (each size its own stream from the seed; SE = one standard error, 95% = +/- 1.96 SE):
  10 cows 11,846 / 100,000 = 11.85% (SE 0.10%); 20 cows 41.11% (SE 0.16%);
  22 cows 47,798 = 47.80% (95% 47.49-48.11%, all below half);
  23 cows 50,617 = 50.62% (95% 50.31-50.93%, all above half).
- Spoken numbers are the SIMULATED rates, rounded: twelve, forty-one, forty-eight, fifty point six.
- The 23-cow tally on screen is this run's running count: 4/10, 47/100 (below half!), 506/1,000,
  5,118/10,000, 50,617/100,000.
- Herd 1 of the 23-cow run (shown first, not picked): cows 8 and 13 share 30 Aug. Herds 2-5: no match.
  The narration says one herd proves nothing.
- 23 cows make 23 x 22 / 2 = 253 pairs.
- One particular cow is a different question: it first passes 50% with 253 OTHER cows (254 in all;
  50.05%; with 22 others only 5.86%). Description only: left out of the narration so the two 253s aren't confused.
- The cakes: one per herd with a match = 50,617, said as "over fifty thousand".
- Calving-season caveat (description): one made-up example season, 80% of births in 90 days: 23 cows
  match 85.0% of the time (SE 0.11%), vs 50.7% for equally likely days. The general result (equally likely
  days give the LOWEST chance) is from memory: source to confirm before we cite it; not cited now.
- NOT claimed: anything about real herds' birthday spread.
"""

EXPERIMENT = 12
THEME = "farm"

NARRATION = [
    ("hook",   "How many cows before two probably share a birthday? Guess.", None),
    ("model",  "I gave my cows random birthday tags. In this simulation, every birthday is independent and equally likely.",
               None),
    ("grow",   "Ten cows: twelve percent of herds have a match. Twenty: forty-one. Twenty-two: forty-eight.", None),
    ("herd",   "Twenty-three cows. This herd: two share the thirtieth of August. But one herd proves nothing.", None),
    ("tally",  "So, a hundred thousand herds... 50.6 percent. Over half.",
               "So, a hundred thousand herds... fifty point six percent. Over half."),
    ("why",    "Why so few? It's not one cow against the rest. Twenty-three cows make 253 pairs, and any pair can match.",
               "Why so few? It's not one cow against the rest. Twenty-three cows make two hundred and fifty-three pairs, "
               "and any pair can match."),
    ("gag",    "I promised a cake for every herd with a match. That's over fifty thousand cakes.", None),
]

TITLE = "How many cows before two share a birthday?"
DESCRIPTION = """Experiment #12: Farmer Joe's birthday cows (the birthday paradox).

With just 23 cows, it's more likely than not that two share a birthday. The exact chance is 50.7%; in our simulation of 100,000 herds, 50.6% had a match. With 22 cows it's 47.6%.

Why so few? 23 cows make 253 possible pairs, and any pair can match. That's a different question from "does another cow share MY cow's birthday?" For that, you'd need 253 other cows (254 in all) to pass 50%.

The model: every birthday is independent and equally likely, over 365 days (leap day left out). Real cows aren't like that; many farms have a calving season, and bunching births into one season makes a shared birthday more likely, not less.

Narration voice: Kyutai Pocket TTS, voice from the VCTK corpus (CC-BY-4.0).

#math #science #birthdayparadox #probability #farmerjoe"""
