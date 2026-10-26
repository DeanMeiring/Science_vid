"""Joe's crop codes, for Experiment 11: the same walking rule as Experiments 1, 2 and 5 with longer codes.

Each letter is one crop. On a square with crop i, Joe turns right (R) or left (L) as letter i says,
plants crop i + 1 (wrapping round), and steps forward. "RL" is Experiment 1 (Langton's ant).
The four codes the episode shows (Wikipedia, "Langton's ant", and our own runs):
  RLLLLRRRLLL   a square spiral (our find)
  LRRRRRLLR     "fills space in a square around itself" (Wikipedia)
  RRLLLRLLLRRR  "creates a filled triangle shape that grows and moves" (Wikipedia: after about 15,900 steps)
  RRLRLLRLRR    a blob, then a wide highway (our find)
"""
import numpy as np

DX = (0, 1, 0, -1)
DY = (-1, 0, 1, 0)
CODES = ("RLLLLRRRLLL", "LRRRRRLLR", "RRLLLRLLLRRR", "RRLRLLRLRR")

def run(code, steps, n=3001, every=1):
    """Walk `steps` steps from the middle of an n x n field of crop 0. Returns (grid, xy (steps + 1, 2)
    relative to the start, every `every` steps, or fewer if he reached the edge)."""
    k = len(code); turn = [1 if c == "R" else -1 for c in code]
    grid = [[0] * n for _ in range(n)]
    x = y = n // 2; d = 0
    xy = [(0, 0)]
    for s in range(steps):
        row = grid[y]; c = row[x]
        d = (d + turn[c]) % 4
        row[x] = (c + 1) % k
        x += DX[d]; y += DY[d]
        if not (0 < x < n - 1 and 0 < y < n - 1): break
        if (s + 1) % every == 0: xy.append((x - n // 2, y - n // 2))
    return np.array(grid, np.uint8), np.array(xy, np.int64)

def highway(xy, max_period=3000, tail=20000):
    """If the walk ends in a highway (it repeats a block of moves that shifts it the same way each time):
    (onset step, period, shift per period); else None. xy must be every step."""
    a = xy[-min(tail, len(xy) // 4):]
    for P in range(1, max_period):
        d = a[P:] - a[:-P]
        if (d == d[0]).all() and d[0].any():
            dd = xy[P:] - xy[:-P]; ok = (dd == d[0]).all(1)
            bad = np.nonzero(~ok)[0]
            onset = int(bad[-1] + 1) if len(bad) else 0
            return onset, P, tuple(int(v) for v in d[0])
    return None

if __name__ == "__main__":   # re-check every number the episode uses
    import sys
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
    from common import gentle
    gentle()
    for code, steps in (("RL", 20_000), *((c, 1_000_000) for c in CODES)):
        g, xy = run(code, steps)
        hw = highway(xy)
        ys, xs = np.nonzero(g)
        print(f"{code:13s} {len(xy) - 1:>9,} steps: {len(ys):>7,} squares planted, box {np.ptp(xs) + 1} x {np.ptp(ys) + 1}, "
              f"highway: {'none' if hw is None else f'from step {hw[0]:,}, repeats every {hw[1]} steps, moving {hw[2]}'}", flush=True)
