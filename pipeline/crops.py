"""Four crops (rule LLRR) for Experiment 5, and the check behind its claim.

Joe on grass turns left, on dirt left, on wheat right, on pumpkins right; the square he leaves
moves on to the next crop (grass -> dirt -> wheat -> pumpkins -> grass).

The claim: the field becomes a perfect mirror image over and over again.
- Source: Wikipedia, "Langton's ant" (extension to multiple colours, citing Gale, Propp,
  Sutherland & Troubetzkoy, "Further Travels with My Ant", Mathematical Intelligencer 1995):
  "Some of these extended Langton's ants produce patterns that become symmetric over and over
  again"; a sufficient condition is that the name, as a cyclic list, is made of pairs of equal
  letters (LL, RR), which LLRR is. "LLRR: Grows symmetrically."
- Our simulation says exactly when: every time Joe is back on his first square facing the way he
  started (up), the field is a mirror image across the line just below that square (top half =
  bottom half); never when he's back facing down.

Directions: 0 up, 1 right, 2 down, 3 left (grid y grows downwards, as in the renders).
"""
import numpy as np

DX = (0, 1, 0, -1)
DY = (-1, 0, 1, 0)
TURN = (-1, -1, 1, 1)          # L L R R
CROPS = ("grass", "dirt", "wheat", "pumpkins")

def run(steps, size=1601):
    """Joe's walk: returns (grid after `steps` (values 0-3), positions (steps+1, 3) of x, y, d with
    the start at (size//2, size//2) facing up)."""
    g = [[0] * size for _ in range(size)]
    x = y = size // 2; d = 0
    hist = np.zeros((steps + 1, 3), np.int64); hist[0] = (x, y, d); hs = hist.tolist()
    for s in range(1, steps + 1):
        c = g[y][x]; d = (d + TURN[c]) % 4; g[y][x] = (c + 1) % 4
        x += DX[d]; y += DY[d]; hs[s] = (x, y, d)
    return np.array(g, np.int8), np.array(hs, np.int64)

def mirrored(g, c):
    """Is the field its own mirror image across the line between rows c and c+1?"""
    ys, xs = np.nonzero(g)
    if not len(ys): return True
    r = max(c - ys.min(), ys.max() - c - 1) + 1
    band = g[c - r + 1:c + r + 1]                     # rows c-r+1 .. c+r, symmetric about c + 1/2
    return bool((band == band[::-1]).all()) and ys.min() >= c - r + 1 and ys.max() <= c + r

def check(steps):
    """Back on the first square: how often, which way he faces, and whether the field is mirrored."""
    size = 1601; c = size // 2
    g = [[0] * size for _ in range(size)]
    x = y = c; d = 0
    out = {"up": [0, 0], "down": [0, 0], "left/right": [0, 0]}   # [times, mirrored]
    for s in range(1, steps + 1):
        cc = g[y][x]; d = (d + TURN[cc]) % 4; g[y][x] = (cc + 1) % 4
        x += DX[d]; y += DY[d]
        if x == c and y == c:
            k = "up" if d == 0 else "down" if d == 2 else "left/right"
            out[k][0] += 1
            out[k][1] += mirrored(np.array(g[c - 200:c + 201], np.int8), 200)
    return out

if __name__ == "__main__":
    import sys
    steps = int(sys.argv[1]) if len(sys.argv) > 1 else 100000
    print(f"back on the first square in {steps:,} steps -> [times, field mirrored]:", check(steps))
