"""Two farmers following Experiment 1's rule (RL) on the same field, for Experiment 4.

A viewer's idea (comment on Experiment 1's Reel): two farmers end up back where they started,
and all the dirt is grass again. Each farmer, on his turn:
  on grass: turn right, dig it into dirt, step forward;
  on dirt:  turn left, it grows back, step forward.
They take turns (Joe, then the helper) unless together=True (both look at the field, then both act).
A "round" is one move each.

Directions: 0 up, 1 right, 2 down, 3 left (grid y grows downwards, as in the renders).
"""
import numpy as np

DX = (0, 1, 0, -1)
DY = (-1, 0, 1, 0)

def run(starts, rounds, together=False, record=False):
    """Run the farmers from `starts` [(x, y, d), ...] on an all-grass field.
    Returns (round it's back exactly where it started or None, history). Back exactly means all
    grass, every farmer on his starting square facing his starting way.
    With record=True, history holds per round: dirt count, and each farmer's (x, y, d)."""
    ants = [list(a) for a in starts]
    start = [tuple(a) for a in starts]
    dirt = set()
    hist = dict(dirt=[0], pos=[[tuple(a) for a in ants]]) if record else None
    for r in range(1, rounds + 1):
        if together:
            seen = [(a[0], a[1]) in dirt for a in ants]
            for a, on_dirt in zip(ants, seen):
                a[2] = (a[2] - 1) % 4 if on_dirt else (a[2] + 1) % 4
            for a in ants: dirt ^= {(a[0], a[1])}   # two on one square flip it twice
            for a in ants: a[0] += DX[a[2]]; a[1] += DY[a[2]]
        else:
            for a in ants:
                x, y, d = a
                if (x, y) in dirt: d = (d - 1) % 4; dirt.discard((x, y))
                else: d = (d + 1) % 4; dirt.add((x, y))
                a[0], a[1], a[2] = x + DX[d], y + DY[d], d
        if record:
            hist["dirt"].append(len(dirt)); hist["pos"].append([tuple(a) for a in ants])
        if not dirt and [tuple(a) for a in ants] == start:
            return r, hist
    return None, hist

def survey(reach=4, rounds=30000, together=False):
    """Joe at (0, 0); the helper anywhere within `reach` squares; every pair of facings.
    Returns {setup: round it comes back, or None}."""
    out = {}
    for hx in range(-reach, reach + 1):
        for hy in range(-reach, reach + 1):
            if hx == 0 and hy == 0: continue
            for d0 in range(4):
                for d1 in range(4):
                    s = ((0, 0, d0), (hx, hy, d1))
                    out[s] = run(s, rounds, together)[0]
    return out

# The setup Experiment 4 shows: the longest return found in the survey (4,724 rounds).
# Joe at (0, 0) facing up, the helper 3 squares left and 2 up, also facing up.
RECORD = ((0, 0, 0), (-3, -2, 0))

if __name__ == "__main__":   # re-check every number the episode uses
    import sys
    back, hist = run(RECORD, 10000, record=True)
    dirt = np.array(hist["dirt"]); peak = int(dirt.argmax())
    xy = np.array([[p[:2] for p in rnd] for rnd in hist["pos"]])
    print(f"record setup: back exactly at round {back} ({2 * back} moves)")
    print(f"  most dirt: {dirt.max()} squares at round {peak}; furthest anyone goes: {int(np.abs(xy).max())} squares")
    print(f"  dirt at rounds 100/1000/2000/3000/4000/4700: {[int(dirt[r]) for r in (100, 1000, 2000, 3000, 4000, 4700)]}")
    print(f"  one full cycle repeats: {run(RECORD, 2 * back)[0] == back}")
    alone, _ = run(RECORD[:1], 2 * back)
    print(f"  Joe alone from the same start: back by {2 * back} moves? {alone is not None}")
    if "--survey" in sys.argv:
        for together in (False, True):
            s = survey(together=together); hits = [v for v in s.values() if v]
            print(f"survey ({'together' if together else 'taking turns'}): {len(hits)} of {len(s)} come back;"
                  f" quickest {min(hits)}, longest {max(hits)} rounds;"
                  f" setups at the longest: {sum(v == max(hits) for v in hits)}")
