"""Render an episode's frames in Blender (no captions or sound; pipeline/compose.py adds those).

Usage (after pipeline/voice.py has written timing.json):
  blender -b -P blender/render_video.py -- episodes/ep01_farm.py                 full size, every frame
  blender -b -P blender/render_video.py -- episodes/ep01_farm.py --scale 50 --every 3   quick draft

Frames go to renders/<episode>/frames[_draft]/f_00000.jpg. Frames already on disk are
skipped, so a stopped render picks up where it left off. Runs at low priority on 4
threads by default, to keep the laptop usable.
"""
import argparse, math, sys, time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "pipeline"))
import scene as S
from common import FPS, N, ROOT, load_episode, load_timeline, simulate

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("episode")
ap.add_argument("--scale", type=int, default=100)
ap.add_argument("--every", type=int, default=1, help="render every n-th frame (drafts)")
ap.add_argument("--threads", type=int, default=4)
ap.add_argument("--start", type=int, default=0)
ap.add_argument("--end", type=int, default=0)
args = ap.parse_args(argv)
S.gentle()

ep_path = Path(args.episode).resolve(); ep = load_episode(ep_path)
ep_dir = ROOT / "renders" / ep_path.stem
lines, DUR, NF, sched = load_timeline(ep_dir)
out = ep_dir / ("frames" if args.scale == 100 and args.every == 1 else "frames_draft")
out.mkdir(parents=True, exist_ok=True)
end = args.end or NF

TOTAL = int(sched.max())
moves, hist = simulate(TOTAL)
mx = np.minimum.accumulate(moves[:, 0]); Mx = np.maximum.accumulate(moves[:, 0])
my = np.minimum.accumulate(moves[:, 1]); My = np.maximum.accumulate(moves[:, 1])

sc = S.Scene(ep.THEME, scale=args.scale, threads=args.threads)
HB = sc.HB
ANIM = 7                    # frames a block takes to rise / sink
BOX = 900
ANGS = [math.pi / 2, 0, -math.pi / 2, math.pi]   # world heading for dir up/right/down/left (world y = -grid y)

grid = np.zeros((N, N), np.uint8)
last = np.full((N, N), -10 ** 9, np.int64)       # step of each cell's last flip
flip_f = np.full((N, N), -10 ** 9, np.int64)     # frame of each cell's last flip
cx = cy = N / 2 + 0.5; s_cur = 120.0
done = 0; step_f = 0
prev_pos = np.array(hist[0][:2], float); ang_prev = ANGS[0]
t_start = time.time(); rendered = 0
for f in range(end):
    tt = f / FPS
    tgt = sched[f]
    if tgt > done:
        # one step: walk from the old square; many steps: jump
        prev_pos = np.array(hist[done][:2], float) if tgt - done == 1 else np.array(hist[tgt][:2], float)
        ang_prev = ANGS[hist[done][2]] if tgt - done == 1 else ANGS[hist[tgt][2]]
        step_f = f
    while done < tgt:
        px_, py_ = moves[done]; grid[py_, px_] ^= 1; last[py_, px_] = done; flip_f[py_, px_] = f; done += 1
    ax, ay, adir, under = hist[done]
    u = min(1.0, (f - step_f) / 6.0); walk = u; u = 1 - (1 - u) ** 2
    pos = prev_pos * (1 - u) + np.array([ax, ay], float) * u
    da = (ANGS[adir] - ang_prev + math.pi) % (2 * math.pi) - math.pi
    ang = ang_prev + da * min(1.0, u * 1.6)
    if done == 0:
        bx0 = bx1 = ax; by0 = by1 = ay
    else:
        bx0, bx1 = min(mx[done - 1], ax), max(Mx[done - 1], ax); by0, by1 = min(my[done - 1], ay), max(My[done - 1], ay)
    span = max(bx1 - bx0, by1 - by0) + 1 + (3 if done < 30 else 8)
    s_t = min(140.0, BOX / span)
    k = 0.06 if done > 30 else 0.12
    s_cur *= (s_t / s_cur) ** k
    cx += ((bx0 + bx1 + 1) / 2 - cx) * k; cy += ((by0 + by1 + 1) / 2 - cy) * k
    if f < args.start or f % args.every: continue
    path = out / f"f_{f:05d}.jpg"
    if path.exists(): continue
    rate = (sched[min(f + 2, NF - 1)] - sched[max(f - 2, 0)]) / 4 * FPS
    heat_len = max(1.2, rate * 0.06)
    # cells: blocks (rising / sinking) and recently flipped floor squares
    sub = (slice(by0, by1 + 1), slice(bx0, bx1 + 1))
    age_f = f - flip_f[sub]
    hgt = np.where(grid[sub] == 1, np.minimum(1, age_f / ANIM), np.maximum(0, 1 - age_f / ANIM))
    hgt = 1 - (1 - hgt) ** 2
    heat = np.exp(-(done - last[sub]) / heat_len) * 0.8
    ys, xs = np.nonzero((hgt > 0.01) | (heat > 0.05))
    sc.set_cells(xs + bx0, ys + by0, hgt[ys, xs], heat[ys, xs], (hgt[ys, xs] > 0.01).astype(np.float32))
    sc.set_tufts(grid, cx, cy, s_cur)
    sc.set_floor(s_cur)
    az = HB if grid[ay, ax] == 1 and (f - flip_f[ay, ax]) > ANIM else 0.0
    sc.set_walker(pos[0] + 0.5, pos[1] + 0.5, az, ang, s_cur, walk if tgt - sched[max(f - 1, 0)] <= 1 and walk < 1 else 0.0)
    sc.set_camera(cx, cy, s_cur, -18 + 36 * (tt / DUR))   # slow orbit
    sc.render(path)
    rendered += 1
    if rendered % 20 == 0:
        el = time.time() - t_start
        left = len(range(f + 1, end, args.every)) * el / rendered
        print(f"frame {f}/{NF} step {done}  {el / rendered:.1f}s/frame  ~{left / 60:.0f} min left", flush=True)
print(f"done: {rendered} frames in {(time.time() - t_start) / 60:.1f} min -> {out}", flush=True)
