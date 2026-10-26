"""Moving sample for Experiment 4's look (style C, Daisy as the helper): Joe and Daisy take turns,
one slow move at a time, then racing through the mess, the meeting at round 1,181 and the rewind,
to the spotless field at round 2,362. Joe's squares are blue (his overalls), Daisy's gold.

Usage: blender -b -P blender/farmers_sample.py -- [--seconds 10] [--scale 50] [--pause 1.0]
Frames: renders/ep04_farmers/sample_frames/f_00000.jpg, plus screen.json for the notes
(prototypes/farmers_sample_compose.py makes sample.mp4). Frames already on disk are skipped.
"""
import argparse, colorsys, json, math, sys, time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "pipeline"))
import scene as S
import farmers as FM
from common import FPS, N, ROOT

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--seconds", type=float, default=10)
ap.add_argument("--scale", type=int, default=50)
ap.add_argument("--pause", type=float, default=1.0, help="rest after each frame (keeps the laptop cool)")
args = ap.parse_args(argv)
S.gentle()

OUT = ROOT / "renders" / "ep04_farmers" / "sample_frames"; OUT.mkdir(parents=True, exist_ok=True)
NF = int(args.seconds * FPS)
HUES = (0.58, 0.12)                    # Joe blue, Daisy gold
ANGS = [math.pi / 2, 0, -math.pi / 2, math.pi]
c = N // 2

# every move of the run, in order: (farmer, square, dug?, position before, position after)
moves = []
ants = [[x + c, y + c, d] for x, y, d in FM.RECORD]; dirt = set()
for r in range(2362):
    for k, a in enumerate(ants):
        x, y, d = a; dug = (x, y) not in dirt
        d = (d + 1) % 4 if dug else (d - 1) % 4
        dirt.add((x, y)) if dug else dirt.discard((x, y))
        before = (x, y, a[2]); a[:] = [x + FM.DX[d], y + FM.DY[d], d]
        moves.append((k, (x, y), dug, before, tuple(a)))
assert not dirt, "the field should be spotless at round 2,362"
TOTAL = len(moves)

# moves done at each frame: one at a time at first, then racing; constant speed through the rewind
key = [(0.0, 0), (3.5, 14), (5.5, 500), (7.0, TOTAL // 2), (9.2, TOTAL), (args.seconds, TOTAL)]
t = np.arange(NF) / FPS
sched = np.zeros(NF)
for (ta, ma), (tb, mb) in zip(key, key[1:]):
    m = (t >= ta) & (t < tb); u = (t[m] - ta) / (tb - ta)
    sched[m] = ma + (mb - ma) * u if (mb <= 20 or mb == TOTAL) else np.expm1(np.log1p(ma) + (np.log1p(mb) - np.log1p(ma)) * u)
sched[t >= key[-2][0]] = TOTAL

sc = S.Scene("farm", scale=args.scale)
daisy = sc.add_character("sheep")
dirt, owner, changed, changed_f = set(), {}, {}, {}
FLASH = 10                                         # frames a square glows after growing back
pos = [list(m) for m in ([moves[0][3], moves[1][3]])]
done = 0; cx = cy = None; s_cur = 110.0
screen_path = OUT / "screen.json"
SCREEN = json.loads(screen_path.read_text()) if screen_path.exists() else {}
def to_screen(gx, gy, z=0.0):
    from bpy_extras.object_utils import world_to_camera_view
    from mathutils import Vector
    v = world_to_camera_view(sc.sc, sc.cam, Vector((gx, -gy, z)))
    return [round(v.x * S.W, 1), round((1 - v.y) * S.H, 1), round(v.z, 2)]
def srgb2lin(rgb): return np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)

t0 = time.time(); rendered = 0
for f in range(NF):
    target = sched[f]; M = int(target)
    while done < M:                                            # apply the moves up to this frame
        k, sq, dug, _, after = moves[done]
        if dug: dirt.add(sq); owner[sq] = k
        else: dirt.discard(sq)
        changed[sq] = done; changed_f[sq] = f; pos[k] = list(after); done += 1
    speed = (sched[f] - sched[f - 1]) if f else 0.0
    fade = max(30.0, speed * 10)
    regrown = [p for p, f_ in changed_f.items() if p not in dirt and f - f_ < FLASH and done - changed[p] < 12]   # only while slow
    cells = list(dirt)
    # camera: fit the mess and both farmers, smoothly
    allp = np.array([p[:2] for p in pos] + [list(p) for p in cells], float)
    x0, y0 = allp.min(0); x1, y1 = allp.max(0)
    s_t = min(110.0, 960 / (max(x1 - x0, (y1 - y0) * 0.85) + 6))
    tx, ty = (x0 + x1 + 1) / 2, (y0 + y1 + 1) / 2
    if cx is None: cx, cy = tx, ty
    kk = 0.07
    s_cur *= (s_t / s_cur) ** kk; cx += (tx - cx) * kk; cy += (ty - cy) * kk
    SCREEN.setdefault(str(f), {})
    path = OUT / f"f_{f:05d}.jpg"
    if path.exists() and SCREEN[str(f)].get("joe"): continue
    xs = np.array([p[0] for p in cells] + [p[0] for p in regrown], int)
    ys = np.array([p[1] for p in cells] + [p[1] for p in regrown], int)
    age = np.array([done - changed[p] for p in cells], float)
    fr = np.r_[np.exp(-age / fade), [1 - (f - changed_f[p]) / FLASH for p in regrown]]; paint = np.zeros((len(xs), 3))
    for i, p in enumerate(cells):
        paint[i] = colorsys.hsv_to_rgb(HUES[owner[p]], 0.45 + 0.5 * fr[i], 0.88 + 0.12 * fr[i])
    for j in range(len(regrown)):
        f_ = fr[len(cells) + j]; paint[len(cells) + j] = colorsys.hsv_to_rgb(0.24, 0.55 + 0.2 * f_, 0.7 + 0.3 * f_)
    sc.set_cells(xs, ys, np.full(len(xs), 0.03), np.zeros(len(xs)), np.ones(len(xs)), paint=srgb2lin(paint))
    grid = np.zeros((N, N), np.uint8)
    if cells: grid[np.array([p[1] for p in cells]), np.array([p[0] for p in cells])] = 1
    sc.set_tufts(grid, cx, cy, s_cur); sc.set_floor(s_cur)
    # the farmers; while slow, the one moving walks smoothly between squares
    frac = target - M if speed < 1 and M < TOTAL else 0.0
    where = []
    for k in range(2):
        x, y, d = pos[k]; walk = 0.0
        if frac and moves[M][0] == k:
            _, _, _, b, a = moves[M]
            e = frac * frac * (3 - 2 * frac)
            x, y, d = b[0] + (a[0] - b[0]) * e, b[1] + (a[1] - b[1]) * e, a[2]; walk = frac
        z = 0.03 if (int(round(x)), int(round(y))) in dirt else 0.02
        if k == 0: sc.set_walker(x + 0.5, y + 0.5, z, ANGS[d], s_cur, walk=walk)
        else: sc.set_character(daisy, x + 0.5, y + 0.5, z, ANGS[d], s_cur, walk=walk)
        where.append((x + 0.5, y + 0.5))
    sc.set_camera(cx, cy, s_cur, -10 + 8 * f / NF)
    SCREEN[str(f)] = dict(round=done // 2, dirt=len(dirt), moves=done,
                          joe=to_screen(*where[0], 1.0), daisy=to_screen(*where[1], 0.8))
    sc.render(path); rendered += 1
    if args.pause: time.sleep(args.pause)
    if rendered % 10 == 0:
        screen_path.write_text(json.dumps(SCREEN))
        print(f"frame {f}/{NF} round {done // 2}  {(time.time() - t0) / rendered:.2f}s/frame", flush=True)
screen_path.write_text(json.dumps(SCREEN))
print("done", NF, "frames", flush=True)
