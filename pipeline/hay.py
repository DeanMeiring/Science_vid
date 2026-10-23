"""Pi from a bale of hay (Buffon's needle), for Experiment 7.

Joe's barn floor is made of boards one straw-length wide (the cracks run along x, at y = 0, 1, 2...).
He drops straws at random: a random middle point on the floor and a random direction. A straw
crosses a crack when its two ends lie on different boards. With the straw as long as a board is
wide, the chance of crossing is 2/pi (Buffon, 18th century), so  pi ~= 2 x straws / crossings.

Lengths are in boards (a straw is 1 long).
"""
import numpy as np

def drop(seed, n, width=12.0, boards=8):
    """n straws on a floor `width` boards long and `boards` boards wide. Returns dict with each straw's
    middle (x, y), angle, ends, and whether it crosses a crack."""
    r = np.random.default_rng(seed)
    x = r.uniform(0.5, width - 0.5, n); y = r.uniform(0, boards, n); ang = r.uniform(0, np.pi, n)
    dx, dy = 0.5 * np.cos(ang), 0.5 * np.sin(ang)
    y0, y1 = y - dy, y + dy
    cross = np.floor(y0) != np.floor(y1)
    return dict(x=x, y=y, ang=ang, ends=np.stack([x - dx, y0, x + dx, y1], -1), cross=cross)

def estimate(cross):
    """Running estimate of pi after each straw (nan until the first crossing)."""
    h = np.cumsum(cross); n = np.arange(1, len(cross) + 1)
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(h > 0, 2 * n / h, np.nan)

if __name__ == "__main__":   # re-check every number the episode uses
    import sys
    seed = int(sys.argv[1]) if len(sys.argv) > 1 else 1
    d = drop(seed, 100_000); est = estimate(d["cross"])
    print(f"crossing rate over 100,000 straws: {d['cross'].mean():.4f} (2/pi = {2 / np.pi:.4f})")
    for n in (10, 100, 1000, 10000, 100000):
        print(f"  {n:>7,} straws: {int(d['cross'][:n].sum()):>6,} cross -> pi ~ {est[n - 1]:.4f}")

def spread(d, k0, k1, x0, y0, width, rows, seed=7):
    """Where to draw straws k0..k1 on a bigger floor: each keeps its angle and its place across its
    plank (the fraction of y), which is all that decides whether it crosses a crack, so the count
    is exactly the simulation's. Only which plank and how far along it are re-drawn, inside the
    area x0..x0+width, planks y0..y0+rows. Returns x, y, ang, cross."""
    r = np.random.default_rng(seed + k0)
    n = k1 - k0; fy = d["y"][k0:k1] % 1.0
    x = x0 + 0.5 + r.uniform(0, width - 1, n); y = y0 + r.integers(0, rows, n) + fy
    return x, y, d["ang"][k0:k1], d["cross"][k0:k1]
