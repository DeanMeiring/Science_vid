"""The chicken and the barns, for Experiment 10 (the "chaos game").

A chicken starts anywhere. Each hop: pick one of the barns at random (a die), hop halfway towards it,
leave a footprint. With three barns at the corners of a triangle, the footprints draw the Sierpinski
triangle. With four barns at the corners of a square, they just fill the square.

Barn positions are in field units: the triangle's corners, base 0..1 at the bottom (y up).
"""
import numpy as np

TRI = np.array([[0.0, 0.0], [1.0, 0.0], [0.5, np.sqrt(3) / 2]])
SQUARE = np.array([[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]])

def hops(barns, n, seed=1, start=None, ratio=0.5):
    """n hops. Returns (points (n + 1, 2) with the start first, barn picked for each hop (n,))."""
    r = np.random.default_rng(seed)
    pick = r.integers(0, len(barns), n)
    p = np.empty((n + 1, 2)); p[0] = start if start is not None else (0.45, 0.3)
    for i in range(n):
        p[i + 1] = p[i] + (barns[pick[i]] - p[i]) * ratio
    return p, pick

def to_bary(p):
    """Barycentric coordinates in TRI (a point is inside the triangle if all are >= 0)."""
    a, b, c = TRI
    v0, v1, v2 = b - a, c - a, p - a
    d00, d01, d11 = v0 @ v0, v0 @ v1, v1 @ v1
    d20, d21 = v2 @ v0, v2 @ v1
    den = d00 * d11 - d01 * d01
    v = (d11 * d20 - d01 * d21) / den; w = (d00 * d21 - d01 * d20) / den
    return np.stack([1 - v - w, v, w], -1)

def depth_ok(p, depth):
    """True where a point is NOT in any of the holes down to `depth` levels (the middle triangle,
    then the middle of each corner copy, ...). A point inside the triangle is in level 1's hole
    when all three barycentric coordinates are below 1/2."""
    l = to_bary(p).copy(); ok = np.ones(len(p), bool)
    for _ in range(depth):
        hole = (l < 0.5).all(-1) & (l > 0).all(-1)
        ok &= ~hole
        # zoom into the corner copy the point is in (the coordinate >= 1/2 says which corner)
        k = l.argmax(-1); l = l * 2; l[np.arange(len(l)), k] -= 1
    return ok

if __name__ == "__main__":   # re-check every number the episode uses
    import sys
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 100_000
    p, pick = hops(TRI, n)
    print(f"{n:,} hops, three barns; barn picks: {np.bincount(pick).tolist()}")
    for d in (1, 2, 3, 5, 8):
        # skip the first d hops: from anywhere in the triangle, hop k can't land in a level-k hole
        bad = (~depth_ok(p[d + 1:], d)).sum()
        print(f"  holes down to level {d}: {bad} of {len(p) - d - 1:,} footprints after hop {d} land in one")
    inside = (to_bary(p) >= -1e-12).all(-1)
    print(f"  start outside or inside? start inside: {bool(inside[0])}; all footprints after hop 1 inside: {bool(inside[1:].all())}")
    for k in (1, 5, 10, 20, 50):
        print(f"  allowed after {k} hops: {(3 / 4) ** k:.6%} of the triangle")
    # four barns: the footprints just fill the square
    q, _ = hops(SQUARE, n, seed=2)
    h, _, _ = np.histogram2d(q[10:, 0], q[10:, 1], bins=8, range=[[0, 1], [0, 1]])
    print(f"four barns, {n:,} hops: footprints per 1/64 of the square: min {int(h.min())}, max {int(h.max())}, "
          f"mean {h.mean():.0f} (even = no pattern)")
