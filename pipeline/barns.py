"""Three barns, one prize (the Monty Hall problem), for Experiment 6.

Each game: the tractor is behind a random barn; Daisy picks a random barn; Joe, who knows where the
tractor is, opens a different barn with a goat behind it (at random when he has two to choose
from); staying keeps Daisy's pick, switching takes the barn that's left.
Barns are numbered 0, 1, 2.
"""
import numpy as np

def games(seed, n):
    """n games: dict of arrays prize, pick, opened, other (the barn you'd switch to)."""
    r = np.random.default_rng(seed)
    prize = r.integers(0, 3, n); pick = r.integers(0, 3, n)
    alt = (pick + 1 + r.integers(0, 2, n)) % 3                # one of the two barns Daisy didn't pick
    opened = np.where(pick == prize, alt, 3 - pick - prize)   # never the prize, never her pick
    other = 3 - pick - opened
    assert ((opened != pick) & (opened != prize)).all()
    return dict(prize=prize, pick=pick, opened=opened, other=other)

def blind_host(seed, n):
    """Joe doesn't know and opens one of the other barns at random: of the games where it happens
    to be a goat, how often do staying and switching win?"""
    r = np.random.default_rng(seed)
    prize = r.integers(0, 3, n); pick = r.integers(0, 3, n)
    opened = (pick + 1 + r.integers(0, 2, n)) % 3; goat = opened != prize
    return float(np.mean(pick[goat] == prize[goat])), float(np.mean((3 - pick - opened)[goat] == prize[goat]))

if __name__ == "__main__":   # re-check every number the episode uses
    g = games(1, 1_000_000)
    print(f"1,000,000 games: stay wins {np.mean(g['pick'] == g['prize']):.4f}, switch wins {np.mean(g['other'] == g['prize']):.4f}")
    g = games(1, 1000)
    print(f"the 1,000 games shown: stay {int((g['pick'] == g['prize']).sum())}, switch {int((g['other'] == g['prize']).sum())}")
    print("host who doesn't know (goat shown by luck): stay %.3f, switch %.3f" % blind_host(2, 1_000_000))
