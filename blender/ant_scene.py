"""Render one still of the Langton's Ant scene (for look checks and benchmarks).

Usage (Blender runs the script; arguments go after "--"):
  blender -b -P blender/ant_scene.py -- --step 12 --theme farm
  blender -b -P blender/ant_scene.py -- --step 5665 --theme ant --scale 100 --repeat 2

The scene itself lives in blender/scene.py (shared with render_video.py).
Kind to the laptop by default: low process priority, 4 render threads, half size.
"""
import argparse, math, sys, time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "pipeline"))
import scene as S
from common import N, ROOT, simulate

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--step", type=int, default=12)
ap.add_argument("--theme", choices=list(S.THEMES), default="farm")
ap.add_argument("--engine", choices=["eevee", "cycles"], default="eevee")
ap.add_argument("--samples", type=int, default=0, help="0 = engine default (eevee 16, cycles 32)")
ap.add_argument("--scale", type=int, default=50, help="resolution %% (100 = 1080x1920)")
ap.add_argument("--threads", type=int, default=4)
ap.add_argument("--yaw", type=float, default=0.0, help="orbit angle in degrees (-18..18 over the video)")
ap.add_argument("--heat-len", type=float, default=0.0, help="fresh-flip trail length in steps (0 = guess)")
ap.add_argument("--repeat", type=int, default=1, help="renders to time (the first includes shader compile)")
ap.add_argument("--out", default="")
ap.add_argument("--save", default="", help="also save the .blend here")
args = ap.parse_args(argv)
S.gentle()

moves, hist = simulate(args.step)
grid = np.zeros((N, N), np.uint8); last = np.full((N, N), -10 ** 9, np.int64)
for s, (px, py) in enumerate(moves):
    grid[py, px] ^= 1; last[py, px] = s
x, y, d, _ = hist[args.step]
touched = last > -10 ** 9
if touched.any():
    ty, tx = np.nonzero(touched)
    bx0, bx1 = min(tx.min(), x), max(tx.max(), x); by0, by1 = min(ty.min(), y), max(ty.max(), y)
else:
    bx0 = bx1 = x; by0 = by1 = y
span = max(bx1 - bx0, by1 - by0) + 1 + (3 if args.step < 30 else 8)
s_px = min(140.0, 900 / span)
cx = (bx0 + bx1 + 1) / 2; cy = (by0 + by1 + 1) / 2
heat_len = args.heat_len or (1.2 if args.step < 30 else 26.0 if args.step > 9977 else 120.0)

sc = S.Scene(args.theme, scale=args.scale, threads=args.threads, engine=args.engine, samples=args.samples)
heat = np.exp(-(args.step - last) / heat_len) * 0.8
ys, xs = np.nonzero((grid == 1) | (touched & (heat > 0.05)))
blk = grid[ys, xs].astype(np.float32)
sc.set_cells(xs, ys, np.ones(len(xs)), heat[ys, xs], blk)
sc.set_tufts(grid, cx, cy, s_px)
sc.set_floor(s_px)
ANGS = [math.pi / 2, 0, -math.pi / 2, math.pi]
sc.set_walker(x + 0.5, y + 0.5, sc.HB if grid[y, x] == 1 else 0.0, ANGS[d], s_px)
sc.set_camera(cx, cy, s_px, args.yaw)

out = args.out or str(ROOT / "renders" / f"{args.theme}_{args.engine}_step{args.step}_{args.scale}.png")
Path(out).parent.mkdir(parents=True, exist_ok=True)
if args.save:
    import bpy
    Path(args.save).parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(Path(args.save).resolve()))
times = []
for _ in range(max(1, args.repeat)):
    t0 = time.time(); sc.render(out, "PNG"); times.append(time.time() - t0)
print(f"BENCH theme={args.theme} engine={args.engine} step={args.step} cells={len(xs)} zoom={s_px:.1f}px "
      f"res={1080 * args.scale // 100}x{1920 * args.scale // 100} threads={args.threads} "
      f"times={' '.join(f'{t:.1f}s' for t in times)} -> {out}", flush=True)
