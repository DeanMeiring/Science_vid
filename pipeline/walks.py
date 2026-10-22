"""Random walks for Experiment 3, generated the same way everywhere (picking seeds, rendering, checking).

Every step is one of the 4 directions on a flat grid (6 in 3D), chosen at random.
Paths start at the origin; add the home position yourself.
"""
import numpy as np

D2 = np.array([(0, -1), (1, 0), (0, 1), (-1, 0)])                                   # up, right, down, left
D3 = np.array([(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)])

def daisy(seed, steps):
    """One sheep: positions after 0..steps steps."""
    r = np.random.default_rng(seed)
    return np.vstack([[0, 0], np.cumsum(D2[r.integers(0, 4, steps)], 0)])

def herd(seed, sheep, steps):
    """Many sheep from one generator: list of (steps+1, 2) paths."""
    r = np.random.default_rng(seed)
    return [np.vstack([[0, 0], np.cumsum(D2[r.integers(0, 4, steps)], 0)]) for _ in range(sheep)]

def flock(seed, chickens, steps):
    """Chickens flying in 3D: list of (steps+1, 3) paths."""
    r = np.random.default_rng(seed)
    return [np.vstack([[0, 0, 0], np.cumsum(D3[r.integers(0, 6, steps)], 0)]) for _ in range(chickens)]

def first_home(path):
    """Step at which a walk first gets back to the start, or None."""
    h = np.nonzero((path[1:] == 0).all(1))[0]
    return int(h[0]) + 1 if len(h) else None

if __name__ == "__main__":   # re-check the walks the episode uses
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from common import load_episode
    ep = load_episode(Path(__file__).resolve().parent.parent / "episodes" / "ep03_sheep.py")
    d = daisy(ep.DAISY["seed"], 20000); dist = np.abs(d).sum(1)
    print("Daisy: first home at step", first_home(d), "| furthest", dist[:first_home(d)].max(), "| at step 1000:", dist[1000])
    h = herd(ep.HERD["seed"], ep.HERD["sheep"], ep.HERD["steps"])
    print("herd: home", sum(first_home(p) is not None for p in h), "of", len(h))
    f = flock(ep.FLOCK["seed"], ep.FLOCK["chickens"], ep.FLOCK["steps"])
    print("flock: home", sum(first_home(p) is not None for p in f), "of", len(f))
