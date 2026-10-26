"""Experiment #4: Farmer Joe gets a helper. Two farmers, same rule as Experiment 1, taking turns.

A viewer's idea (comment on Experiment 1's Reel): "two farmers ... after like 12000 or something
steps ... both end up on the same square they started on and all of the dirt is grass".

Same way of working as Experiment 3: open on action, one flowing voice track, the animation
follows the word timings, under ~50 s.

Facts checked by simulation (pipeline/farmers.py, Oct 2026):
- RECORD setup (Joe facing up; the helper 3 squares left and 2 up, also facing up), taking turns:
  - the mess peaks at 164 dirt squares (round 1,178);
  - at round 1,181 they stand side by side, back to back; from then on each walks back along the
    OTHER's path (one step behind it), and the field replays every earlier state in reverse;
  - round 2,362: all grass, but the farmers are in other spots, facing down;
  - rounds 2,362-4,724 repeat the first half turned 180 degrees;
  - round 4,724 (9,448 moves in all): all grass, both on their starting squares facing their
    starting way. The state repeats, so it cycles forever.
  - Joe alone from the same start: 342 dirt squares after 4,724 moves, never back.
- Survey: helper within 4 squares, every facing (1,280 setups), up to 30,000 rounds:
  536 come back exactly ("about four in ten"); 4,724 rounds is the longest found.
- Daisy (eats grass / leaves compost) and Joe (harvests / plants) follow the SAME rule: on grass
  turn right and it becomes dirt, on dirt turn left and it grows back (Dean's idea, 22 Oct).
- The survey result is in the description only (cut from the voice for length).
- NOT claimed: why it happens, or that 4,724 is the longest possible (only the longest we found).
"""

EXPERIMENT = 4
THEME = "farm"
# VOICE: Farmer Joe's default (pocket:george)

NARRATION = [
    ("start",  "Experiment number 4. You asked for a helper, so Daisy's in! She eats grass and turns right. "
               "On bare dirt, she leaves compost, turns left, and it grows back. I harvest and plant the same way.",
               "Experiment number four. You asked for a helper, so Daisy's in! She eats grass and turns right. "
               "On bare dirt, she leaves compost, turns left, and it grows back. I harvest and plant the same way."),
    ("mess",   "We take turns. A hundred rounds. A thousand. What a mess!", None),
    ("meet",   "Then, at round 1,181, we meet, and something strange happens. We each walk back along "
               "the other's path, undoing every square.",
               "Then, at round eleven eighty-one, we meet, and something strange happens. We each walk back "
               "along the other's path, undoing every square."),
    ("clean",  "Round 2,362: spotless! But we're in the wrong spots. So it all happens again, upside down.",
               "Round twenty-three sixty-two: spotless! But we're in the wrong spots. So it all happens again, "
               "upside down."),
    ("home",   "Round 4,724: a perfect field, and we're right back where we started. Forever.",
               "Round forty-seven twenty-four: a perfect field, and we're right back where we started. Forever."),
    ("next",   "Thanks for the idea! The farm's getting busy. Next experiment: four crops. See y'all next harvest!", None),
]

TITLE = "Farmer Joe and his sheep make a mess... then clean it up perfectly?!"
DESCRIPTION = """Experiment #4: Farmer Joe gets a helper. A viewer's idea!

Joe and Daisy the sheep follow the same simple rule from Experiment #1. On grass, turn right (Daisy eats it, Joe harvests it). On bare dirt, turn left and it grows back (Daisy leaves compost, Joe plants). They take turns. After 1,181 rounds of chaos they meet, and each one walks back along the other's path, undoing every square. At round 2,362 the field is spotless, then it all happens again upside down, and at round 4,724 Joe and Daisy are both exactly back where they started. Forever.

We simulated 1,280 different starting positions: about four in ten come back like this. 4,724 rounds was the longest we found.

Idea from a viewer, thank you!

Next experiment: four crops.

Narration voice: Kyutai Pocket TTS, voice from the VCTK corpus (CC-BY-4.0).
#maths #science #langtonsant #cellularautomata #farmerjoe"""
