"""Joe and three helpers on one field, Experiment 1's rule (RL), taking turns, for Experiment 9.

A viewer's comment on Experiment 4: "Get 3 helpers". Same rule and moves as pipeline/farmers.py:
  on grass: turn right, dig it into dirt, step forward;
  on dirt:  turn left, it grows back, step forward.
A "round" is one move each. Setups: Joe at (0, 0), the others on random squares within 4 of him,
every farmer facing a random way.

"Walked off" = after the last round he's more than FAR squares out and, over the last 1,040
rounds, he repeats the same 104-move pattern (Experiment 1's highway: 104 moves, 2 squares
diagonally). His "leaving round" is the last round he was within NEAR squares of Joe's start.
"""
import numpy as np

import farmers as FM

FAR, NEAR = 60, 25

def setup(r, n, reach=4):
    """Joe at (0, 0) and n - 1 helpers on other squares within `reach`, random facings."""
    starts = [(0, 0, int(r.integers(0, 4)))]
    while len(starts) < n:
        x, y = int(r.integers(-reach, reach + 1)), int(r.integers(-reach, reach + 1))
        if (x, y) in [s[:2] for s in starts]: continue
        starts.append((x, y, int(r.integers(0, 4))))
    return tuple(starts)

def on_highway(xy, period=104, span=1040):
    """xy: (rounds, 2) one farmer's positions. True if the last `span` rounds repeat every
    `period` rounds, shifted by the same diagonal step of 2 squares each time."""
    a, b = xy[-span:], xy[-span - period:-period]
    shift = a - b
    return bool((shift == shift[0]).all() and (np.abs(shift[0]) == 2).all())

def fate(starts, rounds):
    """What happens to one setup: dict(back=round or None, walked=[farmer index, ...],
    left=[leaving round, ...], dirt=dirt count per round, pos=(rounds + 1, n, 3))."""
    back, h = FM.run(starts, rounds, record=True)
    pos = np.array(h["pos"]); dirt = np.array(h["dirt"])
    out = dict(back=back, walked=[], left=[], dirt=dirt, pos=pos)
    if back: return out
    for i in range(len(starts)):
        xy = pos[:, i, :2]
        if np.abs(xy[-1]).max() > FAR and on_highway(xy):
            near = np.nonzero(np.abs(xy).max(1) <= NEAR)[0]
            out["walked"].append(i); out["left"].append(int(near[-1]))
    return out

def survey(n, sets, rounds=20000, seed=7):
    """`sets` random setups of n farmers. Returns a list of (starts, back, walked, left)."""
    r = np.random.default_rng(seed); out = []
    for _ in range(sets):
        s = setup(r, n); f = fate(s, rounds)
        out.append((s, f["back"], f["walked"], f["left"]))
    return out

# The two runs Experiment 9 shows (both from survey(seed=7)).
# Two helpers: Joe (0, 0) facing right, the cow 4 left 2 down, Daisy 4 left 2 up, both facing left.
# Daisy walks off first, then the cow, then Joe.
TWO_HELPERS = ((0, 0, 1), (-4, 2, 3), (-4, -2, 3))
# Three helpers: Joe facing right, Daisy, the cow and the pig around him; all home at round 1,632.
THREE_HELPERS = ((0, 0, 1), (2, -4, 3), (4, -1, 1), (-3, 2, 3))

if __name__ == "__main__":   # re-check every number the episode uses
    import sys
    from common import gentle
    gentle()
    f = fate(TWO_HELPERS, 20000)
    print("two helpers: back", f["back"], "| walked off (farmer, leaving round):",
          sorted(zip(f["left"], f["walked"])), "| most dirt", f["dirt"].max())
    f = fate(THREE_HELPERS, 20000)
    print("three helpers: back at round", f["back"], "| most dirt", f["dirt"].max(),
          "| furthest anyone goes", int(np.abs(f["pos"][:, :, :2]).max()),
          "| all grass before that at rounds", np.nonzero(f["dirt"][1:-1] == 0)[0].tolist())
    sets = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    for n in (2, 3, 4):
        res = survey(n, sets)
        back = sum(1 for r in res if r[1]); walked = np.array([len(r[2]) for r in res if not r[1]])
        print(f"{n} farmers, {sets} setups, 20,000 rounds: all back home {back} ({back / sets:.1%});"
              f" of the rest, how many walked off: {np.bincount(walked, minlength=n + 1).tolist()}", flush=True)
