"""Experiment #6: three barns, one prize (the Monty Hall problem). Daisy plays; Joe is the host.

Promised at the end of Experiment 5 ("Next experiment: three barns, one prize"). Same way of
working: open on action, one flowing voice track, the animation follows the word timings, < 50 s.
Experiment 7 isn't decided yet (Dean wants to think about it first), so the "Next experiment" line
is left out for now: add it to the "end" beat and re-voice once Dean has picked.

Facts checked (Oct 2026):
- Our simulation, 1,000,000 games: staying wins 33.4%, switching 66.6%. The run shown (
  pipeline/barns.games(1, 1000)): staying wins 339, switching 661. See pipeline/barns.py.
- The host must KNOW where the prize is and always open a goat barn. If he opened one at random and
  it happened to be a goat, switching would be 50/50 (our sim: 49.9%). So Joe says he knows.
- Wikipedia, "Monty Hall problem": switching wins 2/3; "an overwhelming majority of people assume
  that each door has an equal probability and conclude that switching does not matter"; Marilyn
  vos Savant's answer in Parade (1990) drew "approximately 10,000 readers, including nearly 1,000
  with PhDs", most saying she was wrong; Paul Erdos "remained unconvinced until he was shown a
  computer simulation".
"""

EXPERIMENT = 6
THEME = "farm"
# VOICE: Farmer Joe's default (pocket:george)

NARRATION = [
    ("setup",  "Experiment number 6: three barns! One has my shiny tractor. The other two... goats. Daisy picks barn one.",
               "Experiment number six: three barns! One has my shiny tractor. The other two... goats. Daisy picks barn one."),
    ("reveal", "I know where the tractor is, so I open a barn with a goat. Should Daisy switch? Most people say it "
               "doesn't matter. Fifty-fifty.", None),
    ("play",   "Let's play a thousand times. Staying won 339. Switching won 661! Switch, and you win two times out of three.",
               "Let's play a thousand times. Staying won three hundred thirty-nine. Switching won six hundred sixty-one! "
               "Switch, and you win two times out of three."),
    ("why",    "Her first pick is right only one time in three. The other two times, I just showed her where it is.", None),
    ("end",    "In 1990, about ten thousand people wrote in to say this was wrong. Even the great Paul Erdős wasn't "
               "convinced, until he saw a computer simulation. See y'all next harvest!",
               "In nineteen ninety, about ten thousand people wrote in to say this was wrong. Even the great Paul Erdos "
               "wasn't convinced, until he saw a computer simulation. See y'all next harvest!"),
]

GAMES = dict(seed=1, n=1000)

TITLE = "Daisy picks a barn. Should she switch?"
DESCRIPTION = """Experiment #6: three barns, one prize (the Monty Hall problem).

One barn hides Farmer Joe's tractor, the other two hide goats. Daisy picks a barn. Joe knows where the tractor is, so he opens a barn with a goat, and asks: do you want to switch? Most people say it doesn't matter. But in 1,000 games, staying won 339 times and switching won 661. Switching wins two times out of three: Daisy's first pick is right only one time in three, and the other two times Joe has just shown her where the tractor is.

When Marilyn vos Savant gave this answer in Parade magazine in 1990, about 10,000 readers wrote in, most of them saying she was wrong. Even the mathematician Paul Erdős wasn't convinced until he saw a computer simulation.

Narration voice: Kyutai Pocket TTS, voice from the VCTK corpus (CC-BY-4.0).
#maths #probability #montyhall #farmerjoe"""
