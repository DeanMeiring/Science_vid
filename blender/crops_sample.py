"""Moving sample for Experiment 5's look (style C): Joe plants four crops one step at a time, then
races to step 10,012. From above, looking down the mirror line.

While fast, every frame shows a mirror moment (Joe back on his first square facing up), so what's
on screen is always a true mirror image and the field grows like a crop circle; the step counter
still counts every step.

Usage: blender -b -P blender/crops_sample.py -- [--seconds 10] [--scale 50] [--pause 1.0]
Frames: renders/ep05_crops/sample_frames/f_00000.jpg, plus screen.json for the notes
(prototypes/crops_sample_compose.py makes sample.mp4). Frames already on disk are skipped.
"""
import argparse, json, math, sys, time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "pipeline"))
import scene as S
import crops as CR
from common import FPS, N, ROOT

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--seconds", type=float, default=10)
ap.add_argument("--scale", type=int, default=50)
ap.add_argument("--pause", type=float, default=1.0, help="rest after each frame (keeps the laptop cool)")
args = ap.parse_args(argv)
S.gentle()

OUT = ROOT / "renders" / "ep05_crops" / "sample_frames"; OUT.mkdir(parents=True, exist_ok=True)
NF = int(args.seconds * FPS); END = 10012; c = N // 2
_, hist = CR.run(END, size=N)
MIRROR = np.nonzero((hist[:, 0] == c) & (hist[:, 1] == c) & (hist[:, 2] == 0))[0][1:]   # steps of the mirror moments
# steps reached at each frame: one at a time, then racing (exponential), then holding on step 10,012
t = np.arange(NF) / FPS
sched = np.where(t < 3.5, t / 3.5 * 14, np.expm1(np.log1p(14) + (np.log1p(END) - np.log1p(14)) * np.clip((t - 3.5) / 5.5, 0, 1)))
sched = np.minimum(sched, END)
rate = np.gradient(sched)
snap = rate > 3                                      # fast: show the latest mirror moment instead
shown = np.where(snap, MIRROR[np.maximum(np.searchsorted(MIRROR, np.floor(sched), "right") - 1, 0)], np.floor(sched)).astype(int)
shown[t >= 9.0] = END

sc = S.Scene("farm", scale=args.scale)
ANGS = [math.pi / 2, 0, -math.pi / 2, math.pi]
g = np.zeros((N, N), np.int8); changed = np.full((N, N), -10 ** 9, np.int64); done = 0
cx, s_cur = None, 110.0
screen_path = OUT / "screen.json"
SCREEN = json.loads(screen_path.read_text()) if screen_path.exists() else {}
def to_screen(gx, gy, z=0.0):
    from bpy_extras.object_utils import world_to_camera_view
    from mathutils import Vector
    v = world_to_camera_view(sc.sc, sc.cam, Vector((gx, -gy, z)))
    return [round(v.x * S.W, 1), round((1 - v.y) * S.H, 1)]

t0 = time.time(); rendered = 0
for f in range(NF):
    T = int(shown[f])
    while done < T:                                  # step: the square Joe leaves grows the next crop
        x, y, _ = hist[done]; g[y, x] = (g[y, x] + 1) % 4; changed[y, x] = done; done += 1
    ys, xs = np.nonzero(g)
    x0, x1 = min(xs.min() if len(xs) else c, c - 2), max(xs.max() + 1 if len(xs) else c + 1, c + 3)
    y0, y1 = min(ys.min() if len(ys) else c, c - 2), max(ys.max() + 1 if len(ys) else c + 1, c + 3)
    tx = (x0 + x1) / 2 + 2.5 * min(1.0, (x1 - x0) / 20)
    s_t = min(110.0, 1000 / (max(y1 - y0, (x1 - x0) * 0.6) + 1))
    if cx is None: cx = tx
    k_ = 0.08; cx += (tx - cx) * k_; s_cur *= (s_t / s_cur) ** k_
    path = OUT / f"f_{f:05d}.jpg"
    if path.exists() and str(f) in SCREEN: continue
    kind = g[ys, xs].astype(int)
    fade = max(6.0, rate[f] * 3)
    heat = np.exp(-(done - changed[ys, xs]) / fade) * 0.8 * (not snap[f])    # just changed: glows (while slow)
    sc.set_cells(xs, ys, np.array(sc.heights)[kind], heat, kind)
    sc.set_tufts(g, cx, c + 1.0, s_cur); sc.set_pumpkins(g, cx, c + 1.0, s_cur); sc.set_floor(s_cur)
    # Joe: while slow he walks smoothly into the next square
    x, y, d = hist[T]; walk = 0.0
    if not snap[f] and T < END:
        frac = sched[f] - T; nx, ny, nd = hist[T + 1]
        e = frac * frac * (3 - 2 * frac); x, y, d = x + (nx - x) * e, y + (ny - y) * e, nd; walk = frac
    on = g[int(round(y)), int(round(x))]
    sc.set_walker(x + 0.5, y + 0.5, sc.heights[on] if on else 0.02, ANGS[d], s_cur, walk=walk)
    sc.set_camera(cx, c + 1.0, s_cur, 90, 78)
    import bpy; bpy.context.view_layer.update()
    mirror = bool(T in set(MIRROR[MIRROR <= T][-1:].tolist())) and T > 0
    SCREEN[str(f)] = dict(step=T, mirrors=int((MIRROR <= T).sum()), mirror=mirror, fast=bool(snap[f]),
                          speed=float(rate[f] * FPS), joe=to_screen(x + 0.5, y + 0.5, 0.9),
                          axis=[to_screen(x0 - 1, c + 1.0, 0.3), to_screen(x1 + 1, c + 1.0, 0.3)])
    sc.render(path); rendered += 1
    if args.pause: time.sleep(args.pause)
    if rendered % 10 == 0:
        screen_path.write_text(json.dumps(SCREEN))
        print(f"frame {f}/{NF} step {T}  {(time.time() - t0) / rendered:.2f}s/frame", flush=True)
screen_path.write_text(json.dumps(SCREEN))
print("done", NF, "frames", flush=True)
