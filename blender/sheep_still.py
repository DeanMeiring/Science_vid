"""One still of Experiment 3: Daisy the sheep out on a random walk, her trail behind her, the barn at home.

Usage: blender -b -P blender/sheep_still.py -- --steps 800 --seed 7 [--scale 100] [--out file.png]
Used for look checks and the style samples.
"""
import argparse, math, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "pipeline"))
import scene as S
from common import N, ROOT

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--steps", type=int, default=800)
ap.add_argument("--seed", type=int, default=7)
ap.add_argument("--scale", type=int, default=100)
ap.add_argument("--out", default="")
args = ap.parse_args(argv)
S.gentle()

# the walk: every step, one of the four directions at random
rng = np.random.default_rng(args.seed)
DXY = np.array([(0, -1), (1, 0), (0, 1), (-1, 0)])
d = rng.integers(0, 4, args.steps)
path = np.vstack([[0, 0], np.cumsum(DXY[d], 0)]) + N // 2
hx = hy = N // 2
visits = {}
for i, (x, y) in enumerate(path): visits[(x, y)] = i
xs = np.array([k[0] for k in visits]); ys = np.array([k[1] for k in visits]); last = np.array(list(visits.values()))

sc = S.Scene("farm", scale=args.scale, character="sheep")
heat = np.exp(-(args.steps - last) / 25.0) * 0.8                     # her newest steps look freshest
sc.set_cells(xs, ys, np.full(len(xs), 0.02), heat, np.ones(len(xs)))  # trampled path, nearly flat
grid = np.zeros((N, N), np.uint8); grid[ys, xs] = 1
x, y = path[-1]
cx = (min(xs.min(), hx) + max(xs.max(), hx) + 1) / 2; cy = (min(ys.min(), hy - 5) + max(ys.max(), hy) + 1) / 2
span = max(xs.max() - xs.min(), ys.max() - ys.min()) + 10
s_px = min(140.0, 900 / span)
sc.set_tufts(grid, cx, cy, s_px)
sc.set_floor(s_px)
sc.add_barn(hx, hy - 2, facing=-math.pi / 2)                          # door looking at home
ANGS = [math.pi / 2, 0, -math.pi / 2, math.pi]
sc.set_walker(x + 0.5, y + 0.5, 0.02, ANGS[d[-1]], s_px)
sc.set_camera(cx, cy, s_px, -10)
out = args.out or str(ROOT / "renders" / "ep03_sheep" / f"still_seed{args.seed}_{args.steps}.png")
Path(out).parent.mkdir(parents=True, exist_ok=True)
sc.render(out, "PNG")
print("saved", out, f"zoom {s_px:.1f}px  distance from home {abs(x - hx) + abs(y - hy)} squares", flush=True)
