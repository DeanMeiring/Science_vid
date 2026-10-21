"""Render an episode's frames in Blender (no captions or sound; pipeline/compose.py adds those).

Usage (after pipeline/voice.py has written timing.json):
  blender -b -P blender/render_video.py -- episodes/ep01_farm.py                 full size, every frame
  blender -b -P blender/render_video.py -- episodes/ep01_farm.py --scale 50 --every 3   quick draft

The episode's RULE (default "RL") sets the colours: each square the walker leaves moves on
to the next one (grass -> dirt -> wheat -> grass for "RLR"). A line with mode "trip" pauses
the sim while the camera flies in, Joe falls on his face, his hat rolls off, and he gets up
and puts it back on.

Frames go to renders/<episode>/frames[_draft]/f_00000.jpg. Frames already on disk are
skipped, so a stopped render picks up where it left off. Runs at low priority on 4
threads by default, to keep the laptop usable.
"""
import argparse, json, math, sys, time
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
RULE = getattr(ep, "RULE", "RL"); K = len(RULE)
moves, hist = simulate(TOTAL, RULE)
mx = np.minimum.accumulate(moves[:, 0]); Mx = np.maximum.accumulate(moves[:, 0])
my = np.minimum.accumulate(moves[:, 1]); My = np.maximum.accumulate(moves[:, 1])

sc = S.Scene(ep.THEME, scale=args.scale, threads=args.threads)
HGT = np.array(sc.heights[:K])   # block height per colour
ANIM = 7                    # frames a block takes to rise / sink
BOX = 900
ANGS = [math.pi / 2, 0, -math.pi / 2, math.pi]   # world heading for dir up/right/down/left (world y = -grid y)

# ---------------- the trip (a "trip" line): times are seconds from the start of the line ----------------
HAT_C = 0.67 * 1.6        # hat centre above his feet when it's on his head

def rot(e):
    """Blender XYZ Euler -> matrix."""
    cx_, sx = math.cos(e[0]), math.sin(e[0]); cy_, sy = math.cos(e[1]), math.sin(e[1]); cz, sz = math.cos(e[2]), math.sin(e[2])
    Rx = np.array([[1, 0, 0], [0, cx_, -sx], [0, sx, cx_]]); Ry = np.array([[cy_, 0, sy], [0, 1, 0], [-sy, 0, cy_]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx

def hat_at(centre, e):
    """Hat pose whose centre is at `centre` (his frame, x forward) turned by Euler e."""
    return tuple(np.asarray(centre) - rot(e) @ np.array([0, 0, HAT_C])), tuple(e)

def smooth(u): u = min(1.0, max(0.0, u)); return u * u * (3 - 2 * u)

TRIP = getattr(ep, "TRIP_LINE", None)
if TRIP is not None:
    tl_line = lines[TRIP]
    hat_word = next((a for w, a, _ in tl_line["words"] if w.lower().startswith("hat")), tl_line["t1"] - 1.2)
    T_GET = max(1.7, hat_word - tl_line["t0"] - 0.95)       # he starts getting up a moment before "Hat's"
GROUND_HAT = ((1.55, 0.32, 0.07), (0.5, 0.0, 0.9))           # where the hat ends up: ahead of him, tipped over
FALL_E = (0.0, math.radians(84), 0.0)

def trip_pose(tl):
    """(fall 0..1, hat pose or None) at tl seconds into the trip line."""
    if tl < 0: return 0.0, None
    if tl < 0.30: fall = (tl / 0.30) ** 2                                   # down he goes
    elif tl < 0.42: fall = 1 - 0.06 * math.sin(math.pi * (tl - 0.30) / 0.12)   # little bounce
    elif tl < T_GET: fall = 1.0
    else: fall = 1 - smooth((tl - T_GET) / 0.5)                            # gets up
    on_head = hat_at((math.sin(FALL_E[1] * fall) * HAT_C, 0, math.cos(FALL_E[1] * fall) * HAT_C), (0, FALL_E[1] * fall, 0))
    if tl < 0.15: return fall, None
    if tl < 0.60:                                                        # flies off and lands ahead of him
        u = (tl - 0.15) / 0.45
        c0 = np.array([math.sin(FALL_E[1] * 0.3) * HAT_C, 0, math.cos(FALL_E[1] * 0.3) * HAT_C])
        c1 = np.array(GROUND_HAT[0]); c = c0 * (1 - u) + c1 * u; c[2] += 0.6 * math.sin(math.pi * u)
        e = np.array(GROUND_HAT[1]) * u; e[2] += 3.0 * u
        return fall, hat_at(c, e)
    if tl < T_GET + 0.5: return fall, hat_at(GROUND_HAT[0], GROUND_HAT[1])
    if tl < T_GET + 0.85:                                                  # plops it back on
        u = smooth((tl - T_GET - 0.5) / 0.35)
        c = np.array(GROUND_HAT[0]) * (1 - u) + np.array([0, 0, HAT_C]) * u; c[2] += 0.5 * math.sin(math.pi * u)
        return fall, hat_at(c, np.array(GROUND_HAT[1]) * (1 - u))
    return fall, None

# ---------------- the comparison (COMPARE_LINE): an earlier episode's field on the same farm ----------------
CMP = getattr(ep, "COMPARE_LINE", None)
if CMP is not None:
    cw = ep.COMPARE_WITH
    o_moves, _ = simulate(cw["steps"], cw["rule"])
    og = np.zeros((N, N), np.uint8)
    for px_, py_ in o_moves: og[py_, px_] = (og[py_, px_] + 1) % len(cw["rule"])
    oys, oxs = np.nonzero(og > 0); okind = og[oys, oxs]
    # today's whole field (at its last step), and the old one just beyond it (higher up the screen)
    fx0, fx1, fy0, fy1 = int(mx[-1]), int(Mx[-1]), int(my[-1]), int(My[-1])
    GAP = 45                       # room between the fields for the nearer one's label
    ox = (fx0 + fx1) / 2 - (oxs.min() + oxs.max()) / 2
    oy = fy0 - GAP - oys.max() - 1
    oxs = (oxs + round(ox)).astype(np.int64); oys = (oys + round(oy)).astype(np.int64)
    ostag = (np.sin(oxs * 12.9898 + oys * 78.233) * 43758.5453) % 1.0      # blocks rise one after another
    cmp_t0 = lines[CMP]["t0"]
    labels_path = out / "labels.json"
    LABELS = json.loads(labels_path.read_text()) if labels_path.exists() else {}

def to_screen(gx, gy):
    """Grid point -> pixel (x, y) on the full-size frame."""
    from bpy_extras.object_utils import world_to_camera_view
    from mathutils import Vector
    v = world_to_camera_view(sc.sc, sc.cam, Vector((gx, -gy, 0.0)))
    return [round(v.x * S.W, 1), round((1 - v.y) * S.H, 1)]

grid = np.zeros((N, N), np.uint8)
prev = np.zeros((N, N), np.uint8)                # colour before the last change (blocks morph from it)
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
        px_, py_ = moves[done]; prev[py_, px_] = grid[py_, px_]; grid[py_, px_] = (grid[py_, px_] + 1) % K
        last[py_, px_] = done; flip_f[py_, px_] = f; done += 1
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
    tx_, ty_ = (bx0 + bx1 + 1) / 2, (by0 + by1 + 1) / 2
    tl = tt - tl_line["t0"] if TRIP is not None else -1
    if TRIP is not None and 0 <= tl < tl_line["t1"] - tl_line["t0"] - 0.35:
        # the trip: fly in close to Joe (he falls forward, so aim a little ahead of his feet)
        hd = ANGS[adir]
        tx_, ty_ = pos[0] + 0.5 + 0.45 * math.cos(hd), pos[1] + 0.5 - 0.45 * math.sin(hd)
        s_t, k = 340.0, 0.14
    if CMP is not None and tt >= cmp_t0 - 0.3:
        # zoom out to both fields, with room above each for its label
        ux0, ux1 = min(bx0, oxs.min()), max(bx1, oxs.max()); uy0, uy1 = min(by0, oys.min()), max(by1, oys.max())
        tx_, ty_ = (ux0 + ux1 + 1) / 2, (uy0 + uy1 + 1) / 2 - 0.06 * (uy1 - uy0)
        # fit the width, and the height into the band between the labels and the captions
        # (the tilted camera squashes depth to about 0.85 on screen)
        s_t, k = min(140.0, BOX / (ux1 - ux0 + 14), 1150 / ((uy1 - uy0 + 14) * 0.85)), 0.07
    s_cur *= (s_t / s_cur) ** k
    cx += (tx_ - cx) * k; cy += (ty_ - cy) * k
    if f < args.start or f % args.every: continue
    path = out / f"f_{f:05d}.jpg"
    if path.exists(): continue
    rate = (sched[min(f + 2, NF - 1)] - sched[max(f - 2, 0)]) / 4 * FPS
    heat_len = max(1.2, rate * 0.06)
    # cells: blocks morph from their old height to the new one; a block sinking back to grass keeps
    # its old colour on the way down; recently changed grass squares show as fresh tiles
    sub = (slice(by0, by1 + 1), slice(bx0, bx1 + 1))
    cur, old = grid[sub], prev[sub]
    a = np.minimum(1.0, (f - flip_f[sub]) / ANIM); a = 1 - (1 - a) ** 2
    hz = HGT[old] * (1 - a) + HGT[cur] * a
    kind = np.where(cur > 0, cur, np.where(a < 1, old, 0))
    heat = np.exp(-(done - last[sub]) / heat_len) * 0.8
    ys, xs = np.nonzero((hz > 0.004) | (heat > 0.05) | (cur > 0))
    xs, ys, hz, heat, kind = xs + bx0, ys + by0, hz[ys, xs], heat[ys, xs], kind[ys, xs]
    if CMP is not None and tt >= cmp_t0:
        # the earlier field rises out of the grass, block by block
        r = np.clip((tt - cmp_t0 - 0.9 * ostag) / 0.5, 0, 1); r = r * r * (3 - 2 * r)
        on = r > 0
        xs = np.concatenate([xs, oxs[on]]); ys = np.concatenate([ys, oys[on]])
        hz = np.concatenate([hz, HGT[okind[on]] * r[on]]); heat = np.concatenate([heat, np.zeros(on.sum())])
        kind = np.concatenate([kind, okind[on]])
    sc.set_cells(xs, ys, hz, heat, kind)
    sc.set_tufts(grid, cx, cy, s_cur, hz=HGT[grid])
    sc.set_floor(s_cur)
    az = HGT[grid[ay, ax]] if (f - flip_f[ay, ax]) > ANIM else HGT[prev[ay, ax]]
    fall, hat = trip_pose(tl) if TRIP is not None else (0.0, None)
    sc.set_walker(pos[0] + 0.5, pos[1] + 0.5, az, ang, s_cur,
                  walk if tgt - sched[max(f - 1, 0)] <= 1 and walk < 1 else 0.0, fall=fall, hat=hat)
    yaw = -18 + 36 * (tt / DUR)   # slow orbit
    if TRIP is not None and tl >= 0:
        # swing round to see Joe's face (three-quarter front), then drift back as we zoom out
        dur = tl_line["t1"] - tl_line["t0"]
        w = smooth(tl / 0.8) * (1 - smooth((tl - dur + 0.35) / 1.2))
        front = math.degrees(math.atan2(-math.cos(ang), -math.sin(ang))) + 55
        yaw += ((front - yaw + 180) % 360 - 180) * w
    sc.set_camera(cx, cy, s_cur, yaw)
    if CMP is not None and tt >= cmp_t0 - 0.5:
        # where the labels go: just above each field (pixels on the full-size frame)
        import bpy; bpy.context.view_layer.update()
        LABELS[str(f)] = [to_screen((oxs.min() + oxs.max() + 1) / 2, oys.min() - 3),
                          to_screen((fx0 + fx1 + 1) / 2, fy0 - 3)]
        if rendered % 10 == 0: labels_path.write_text(json.dumps(LABELS))
    sc.render(path)
    rendered += 1
    if rendered % 20 == 0:
        el = time.time() - t_start
        left = len(range(f + 1, end, args.every)) * el / rendered
        print(f"frame {f}/{NF} step {done}  {el / rendered:.1f}s/frame  ~{left / 60:.0f} min left", flush=True)
if CMP is not None: labels_path.write_text(json.dumps(LABELS))
print(f"done: {rendered} frames in {(time.time() - t_start) / 60:.1f} min -> {out}", flush=True)
