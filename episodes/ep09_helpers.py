"""Experiment #9: Farmer Joe gets three helpers (a viewer's comment on Experiment 4: "Get 3 helpers").

Same rule as Experiments 1 and 4, everyone taking turns: on grass turn right and dig it into dirt, on
dirt turn left and it grows back. After Experiment 8 (a joke with no surprise) did worse, back to a real
question with a surprising, checked answer, and a counter racing up. Opens on a hook ("If I...").

Facts checked by simulation (pipeline/helpers.py, 25 Oct 2026). Setups: Joe at (0, 0), helpers on random
squares within 4 of him, random facings, up to 20,000 rounds, 3,000 setups each:
- 1 helper (2 farmers): all home 1,254 of 3,000 (41.8%, "about four in ten", as in Experiment 4).
- 2 helpers (3 farmers): all home 0 of 3,000.
- 3 helpers (4 farmers): all home 24 of 3,000 ("about one in a hundred and twenty-five"); quickest 16
  rounds, longest 1,632.
- Also tried (1,500 setups, within 5): 5 farmers 0 home, 6 farmers 1 home. 1 farmer is Experiment 1:
  never home (Cohen-Kong: one farmer's path is always unbounded).
- TWO_HELPERS run: Daisy walks off on a highway at round 1,158, the cow at 3,215, Joe at 5,751 (each
  then repeats Experiment 1's 104-move highway; "walked off" = more than 60 squares out and on it).
- THREE_HELPERS run: at most 56 dirt squares, nobody goes more than 7 squares out; at round 1,632 the
  field is all grass and all four are on their starting squares, facing their starting way.
- NOT claimed: WHY odd numbers never came home (we don't know), that they never can (only never in
  our tries), or that the walkers keep going forever.
"""

EXPERIMENT = 9
THEME = "farm"

NARRATION = [
    ("hook",  "If I get three helpers, will we all make it back home?", None),
    ("rule",  "Same rule as always. On grass, turn right and dig. On dirt, turn left, and it grows back.", None),
    ("one",   "With one helper, we made it home about four times in ten.", None),
    ("two",   "So I got two. Daisy walked off first. Then the cow. Then me. "
              "Three thousand tries, and not once did we all make it home.", None),
    ("three", "So I got a third. The pig. More helpers, more mess? Round one thousand six hundred and thirty-two. "
              "All grass. Everybody home.", None),
    ("law",   "Twenty-four times in three thousand. One farmer, three, five: never home. Two, four, six: sometimes. "
              "I don't know why. But I'm keeping the pig.", None),
]

TITLE = "Farmer Joe got 3 helpers. Then something weird happened..."
DESCRIPTION = """Experiment #9: Farmer Joe gets three helpers (thanks for the idea in the comments!)

Same rule as Experiment 1, everyone taking turns: on grass, turn right and dig it into dirt; on dirt, turn left and it grows back. Can they all end up back where they started, with the whole field grass again?

We simulated 3,000 random starts for each, up to 20,000 rounds:
- 1 helper: all home 1,254 times (about 4 in 10)
- 2 helpers: 0 times. They walk off one by one, on the same "highway" as Experiment 1
- 3 helpers: 24 times (about 1 in 125)
With 5 farmers: never (in 1,500 tries). With 6: once. Odd numbers never made it home; even numbers sometimes did. We don't know why!

Narration voice: Kyutai Pocket TTS, voice from the VCTK corpus (CC-BY-4.0).

#math #science #langtonsant #farmerjoe"""
