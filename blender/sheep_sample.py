"""Sample clip for Experiment 3's look: a herd of sheep random-walking from the barn, each painting
its own coloured trail (bright where it just walked, deeper behind), the camera pulling back.

Usage: blender -b -P blender/sheep_sample.py -- [--sheep 12] [--steps 4000] [--seconds 10] [--scale 50]
Frames: renders/ep03_sheep/sample_frames/; then pipeline makes sample.mp4 (see the end of this file).
"""
import argparse, colorsys, json, math, sys, time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "pipeline"))
import scene as S
from common import FPS, N, ROOT

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--sheep", type=int, default=12)
ap.add_argument("--steps", type=int, default=4000)
ap.add_argument("--seconds", type=float, default=10)
ap.add_argument("--scale", type=int, default=50)
ap.add_argument("--seed", type=int, default=3)
ap.add_argument("--still", type=int, default=0, help="only render the last frame, at this scale")
args = ap.parse_args(argv)
S.gentle()

OUT = ROOT / "renders" / "ep03_sheep" / "sample_frames"; OUT.mkdir(parents=True, exist_ok=True)
NF = int(args.seconds * FPS)
hx = hy = N // 2
DXY = np.array([(0, -1), (1, 0), (0, 1), (-1, 0)])
rng = np.random.default_rng(args.seed)
paths = [np.vstack([[0, 0], np.cumsum(DXY[rng.integers(0, 4, args.steps)], 0)]) + (hx, hy) for _ in range(args.sheep)]
dirs = [None] * args.sheep
# steps reached at each frame: slow and readable at first, then racing (same for every sheep)
u = np.arange(NF) / (NF - 1)
sched = np.floor(args.steps * np.expm1(3.2 * u) / np.expm1(3.2)).astype(int)
# each sheep's colour: hues that pop on green grass (no greens); Daisy (sheep 0) is gold.
# Fresh steps are vivid, older ones soften to pastel (never dark and muddy).
PALETTE = [0.12, 0.07, 0.02, 0.95, 0.88, 0.80, 0.74, 0.66, 0.58, 0.52, 0.16, 0.98]
HUES = [PALETTE[i % len(PALETTE)] for i in range(args.sheep)]
def colour(k, age, fade):
    fresh = np.exp(-np.atleast_1d(age) / fade)
    sat = 0.38 + 0.52 * fresh; val = 0.86 + 0.14 * fresh
    rgb = np.array([colorsys.hsv_to_rgb(HUES[k], s_, v_) for s_, v_ in zip(sat, val)])
    return np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)    # sRGB -> linear

sc = S.Scene("farm", scale=args.still or args.scale, character="sheep")
sc.add_barn(hx, hy - 2, facing=-math.pi / 2)
barn_x, barn_y = (hx - 1, hx + 1), (hy - 5, hy - 2)              # don't paint trail under the barn
last = np.full((N, N), -1, np.int64); owner = np.full((N, N), -1, np.int64)
done = 0; cx, cy, s_cur = hx + 0.5, hy + 0.5, 110.0
ANGS = [math.pi / 2, 0, -math.pi / 2, math.pi]
t0 = time.time(); daisy_log = []
for f in range(NF):
    T = int(sched[f])
    for k, p in enumerate(paths):                                  # paint each sheep's new steps
        seg = p[done:T + 1]
        last[seg[:, 1], seg[:, 0]] = np.arange(done, done + len(seg)); owner[seg[:, 1], seg[:, 0]] = k
    done = T
    ys, xs = np.nonzero(owner >= 0)
    keep = ~((xs >= barn_x[0]) & (xs <= barn_x[1]) & (ys >= barn_y[0]) & (ys <= barn_y[1]))
    xs, ys = xs[keep], ys[keep]
    fade = max(20.0, T * 0.12)
    paint = np.zeros((len(xs), 3))
    for k in range(args.sheep):
        m = owner[ys, xs] == k
        if m.any(): paint[m] = colour(k, T - last[ys[m], xs[m]], fade)
    # camera: fit every trail and the barn, smoothly
    bx0, bx1 = min(xs.min(), hx - 2), max(xs.max(), hx + 2); by0, by1 = min(ys.min(), hy - 6), max(ys.max(), hy + 1)
    s_t = min(110.0, 900 / (max(bx1 - bx0, (by1 - by0) * 0.85) + 8))
    k_ = 0.08
    s_cur *= (s_t / s_cur) ** k_; cx += ((bx0 + bx1 + 1) / 2 - cx) * k_; cy += ((by0 + by1 + 1) / 2 - cy) * k_
    dx, dy = paths[0][T]; daisy_log.append([int(T), int(abs(dx - hx) + abs(dy - hy))])
    if args.still and f < NF - 1: continue
    path = OUT / f"f_{f:05d}.jpg"
    if path.exists() and not args.still: continue
    sc.set_cells(xs, ys, np.full(len(xs), 0.03), np.zeros(len(xs)), np.ones(len(xs)), paint=paint)
    grid = np.zeros((N, N), np.uint8); grid[ys, xs] = 1
    sc.set_tufts(grid, cx, cy, s_cur); sc.set_floor(s_cur)
    step_d = paths[0][min(T + 1, args.steps)] - paths[0][T]
    hd = math.atan2(-step_d[1], step_d[0]) if step_d.any() else 0.0
    sc.set_walker(dx + 0.5, dy + 0.5, 0.03, hd, s_cur)
    others = np.array([p[T] for p in paths[1:]])
    sc.set_dots(others[:, 0], others[:, 1], s_cur)
    sc.set_camera(cx, cy, s_cur, -12 + 10 * f / NF)
    if args.still:
        sc.render(OUT.parent / "sample_still.png", "PNG"); print("saved still", flush=True); break
    sc.render(path)
    if f % 30 == 0: print(f"frame {f}/{NF} step {T}  {(time.time() - t0) / (f + 1):.2f}s/frame", flush=True)
(OUT.parent / "sample_daisy.json").write_text(json.dumps(daisy_log))
print("done", NF, "frames", flush=True)
