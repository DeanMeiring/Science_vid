"""Render Experiment 9's frames (Joe and three helpers). Captions, notes and sound come later (pipeline/compose_ep09.py).

Usage: blender -b -P blender/render_ep09.py -- [--scale 100] [--every 1] [--start 0] [--end 0] [--pause 1.0]
Frames: renders/ep09_helpers/frames[_draft]/f_00000.jpg, plus screen.json (where everyone is on screen,
for the handwritten notes). Frames already on disk are skipped. --end 0 means to the end.

Story (pinned to words, see pipeline/ep09_timeline.py): the same look as Experiment 4. Everyone takes
turns, one slow move at a time while Joe explains (the animals nod to eat grass or leave a little
compost pile on bare dirt; Joe harvests with a nod or plants a sprout). Squares keep the colour of
whoever cleared them (Joe blue, Daisy gold, the cow red, the pig pink). Hard cuts between the runs;
the camera fits everyone, so it pulls right back as they walk off, and they turn into glowing dots.
"""
import argparse, json, math, sys, time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "pipeline"))
import scene as S
from common import FPS, N, ROOT
from ep09_timeline import CAST, Timeline
import farm_overview as FO

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--scale", type=int, default=100)
ap.add_argument("--every", type=int, default=1)
ap.add_argument("--start", type=int, default=0)
ap.add_argument("--end", type=int, default=0)
ap.add_argument("--pause", type=float, default=1.0,
                help="seconds to rest after each frame, so the laptop runs cooler (0 = flat out)")
args = ap.parse_args(argv)
S.gentle()
import bpy

tl = Timeline(ROOT / "episodes" / "ep09_helpers.py")
out = tl.dir / ("frames" if args.scale == 100 and args.every == 1 else "frames_draft"); out.mkdir(parents=True, exist_ok=True)
end = args.end or tl.nf
c = N // 2                                     # today's field: Joe's start is grid (c, c)
ACT = 0.35                                     # while slow: the action takes the first 35% of a move, then the step

# ---------------- colours ----------------
def to_lin(x): return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)
HUE = dict(joe=0.58, daisy=0.12, cow=0.0, pig=0.9)   # Joe blue (overalls), Daisy gold, the cow red, the pig pink

# ---------------- scene ----------------
sc = S.Scene("farm", scale=args.scale)
sc.set_sky((120, 182, 242))
HANDLE = {name: sc.add_character(kind) for name, kind in (("daisy", "sheep"), ("cow", "cow"), ("pig", "pig"))}
ANGS = [math.pi / 2, 0, -math.pi / 2, math.pi]

def prop(name, parts):
    """A small object made of spheres: parts = [(loc, radius, scale, rgb)]."""
    root = bpy.data.objects.new(name, None); sc.sc.collection.objects.link(root)
    for loc, r, scl, rgb in parts:
        bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=16, ring_count=8)
        o = bpy.context.object; o.scale = scl; o.parent = root
        o.data.materials.append(S._material(f"{name}{rgb}", S.lin(rgb), rough=0.8)[0]); bpy.ops.object.shade_smooth()
    root.scale = (0, 0, 0)
    return root
COMPOST = prop("Compost", [((0, 0, 0.06), 0.13, (1, 1, 0.6), (92, 62, 38)), ((0.09, 0.05, 0.05), 0.08, (1, 1, 0.7), (110, 76, 46)),
                           ((-0.07, 0.07, 0.04), 0.07, (1, 1, 0.7), (80, 54, 32)), ((0.02, -0.08, 0.04), 0.07, (1, 1, 0.7), (100, 70, 40))])
SPROUT = prop("Sprout", [((0, 0, 0.12), 0.025, (1, 1, 5), (70, 150, 50)), ((0.07, 0, 0.24), 0.07, (1.6, 0.6, 0.3), (110, 200, 70)),
                         ((-0.07, 0, 0.27), 0.065, (1.6, 0.6, 0.3), (110, 200, 70))])
def show_prop(p, sq, size):
    p.location = (sq[0] + c + 0.5, -(sq[1] + c + 0.5), 0.03); p.scale = (size,) * 3

def smooth(u): u = min(1.0, max(0.0, u)); return u * u * (3 - 2 * u)

def place(name, *a, **kw):
    (sc.set_walker if name == "joe" else lambda *a_, **k_: sc.set_character(HANDLE[name], *a_, **k_))(*a, **kw)

def to_screen(gx, gy, z=0.0):
    from bpy_extras.object_utils import world_to_camera_view
    from mathutils import Vector
    v = world_to_camera_view(sc.sc, sc.cam, Vector((gx, -gy, z)))
    return [round(v.x * S.W, 1), round((1 - v.y) * S.H, 1), round(v.z, 2)]
screen_path = out / "screen.json"
SCREEN = json.loads(screen_path.read_text()) if screen_path.exists() else {}

# ---------------- state per run, advanced every frame (also the skipped ones, so it's always right) ----------------
class Run:
    def __init__(self, name):
        self.name, self.moves, self.cast = name, tl.moves[name], CAST[name]
        self.dirt, self.owner, self.changed, self.changed_f = set(), {}, {}, {}
        self.pos = [list(self.moves[k][3]) for k in range(len(self.cast))]
        self.done = 0
    def advance(self, M, f):
        while self.done < M:
            k, sq, dug, _, after = self.moves[self.done]
            if dug: self.dirt.add(sq); self.owner[sq] = k
            else: self.dirt.discard(sq)
            self.changed[sq] = self.done; self.changed_f[sq] = f; self.pos[k] = list(after); self.done += 1
RUNS = {name: Run(name) for name in CAST}

cam = dict(cx=0.0, cy=0.0, s=90.0, pitch=54.0)
t_start = time.time(); rendered = 0; last_scene = -1
for f in range(end):
    tt = f / FPS
    si = int(tl.scene[f]); run = RUNS[tl.scenes[si][0]]; n = len(run.cast)
    target = float(tl.sched[f]); M = int(target); slow = tl.rate[f] < FPS * 0.5     # a move lasts 2+ frames
    run.advance(M, f)
    frac = target - M if (slow and M < len(run.moves)) else 0.0
    cur = run.moves[M] if frac else None
    show_dirt = set(run.dirt)
    if cur and frac >= ACT:
        (show_dirt.add if cur[2] else show_dirt.discard)(cur[1])
    # ---- camera: fit everyone and the mess; close on the four at home, then on the pig
    allp = np.array([p[:2] for p in run.pos] + [list(p) for p in run.dirt], float)
    x0, y0 = allp.min(0); x1, y1 = allp.max(0)
    tgt = dict(cx=(x0 + x1 + 1) / 2, cy=(y0 + y1 + 1) / 2, s=min(110.0, 960 / (max(x1 - x0, (y1 - y0) * 0.85) + (6 if si == 2 else 3))), pitch=54.0)
    if si == 3 and tt >= tl.t_home: tgt["s"] = min(tgt["s"] * 1.15, 110.0)
    if si == 3 and tt >= tl.t_but:
        px, py = run.pos[3][:2]; tgt.update(cx=px + 0.5, cy=py + 0.5, s=150.0)
    if si != last_scene:                                   # a hard cut: start framed
        cam.update(tgt); last_scene = si
    k_ = 0.12 if si == 3 and tt >= tl.t_but else 0.08
    cam["s"] *= (tgt["s"] / cam["s"]) ** k_
    for key in ("cx", "cy", "pitch"): cam[key] += (tgt[key] - cam[key]) * k_
    if f < args.start or f % args.every: continue
    path = out / f"f_{f:05d}.jpg"
    if path.exists() and str(f) in SCREEN: continue
    # ---- the field: dirt in the colour of whoever cleared it; fresh squares vivid
    fade = max(30.0, tl.rate[f] / FPS * 10 * n / 2)
    cells = sorted(show_dirt)
    regrown = [p for p, f_ in run.changed_f.items() if p not in show_dirt and f - f_ < 10 and run.done - run.changed[p] < 12] if slow else []
    if cur and frac >= ACT and not cur[2]: regrown.append(cur[1])
    xs = np.array([p[0] + c for p in cells + regrown], int); ys = np.array([p[1] + c for p in cells + regrown], int)
    who = np.array([cur[0] if (cur and p == cur[1]) else run.owner.get(p, 0) for p in cells], int)
    age = np.array([0 if (cur and p == cur[1]) else run.done - run.changed.get(p, run.done) for p in cells], float)
    fr = np.exp(-age / fade)
    hues = np.array([HUE[run.cast[k]] for k in who]) if len(cells) else np.zeros(0)
    paint = np.zeros((len(xs), 3))
    if len(cells): paint[:len(cells)] = FO.hsv2rgb(hues, 0.45 + 0.5 * fr, 0.88 + 0.12 * fr)
    for j, p in enumerate(regrown):
        g = 1.0 if (cur and p == cur[1]) else max(0.0, 1 - (f - run.changed_f.get(p, f)) / 10)
        paint[len(cells) + j] = FO.hsv2rgb(np.array([0.24]), np.array([0.55 + 0.2 * g]), np.array([0.7 + 0.3 * g]))[0]
    sc.set_cells(xs, ys, np.full(len(xs), 0.03), np.zeros(len(xs)), np.ones(len(xs)), paint=to_lin(paint))
    grid = np.zeros((N, N), np.uint8)
    if cells:
        gy_, gx_ = np.array([p[1] for p in cells]) + c, np.array([p[0] for p in cells]) + c
        ok = (gx_ >= 0) & (gx_ < N) & (gy_ >= 0) & (gy_ < N); grid[gy_[ok], gx_[ok]] = 1
    sc.set_tufts(grid, cam["cx"] + c, cam["cy"] + c, cam["s"]); sc.set_floor(cam["s"])
    # ---- everyone in this run: while slow, the one moving acts on his square, then steps; the rest off stage
    show_prop(COMPOST, (0, 0), 0); show_prop(SPROUT, (0, 0), 0)
    at = {}; act = None
    for name in ("joe", "daisy", "cow", "pig"):
        if name not in run.cast:
            place(name, -500.0, -500.0, -50.0, 0.0, cam["s"]); continue
        k = run.cast.index(name); x, y, d = run.pos[k]; walk = fall = 0.0
        if cur and cur[0] == k:
            _, sq, dug, b, a = cur
            if frac < ACT:                                 # turn on the spot, and do the job
                u = frac / ACT
                d0, d1 = ANGS[b[2]], ANGS[a[2]]; dd = (d1 - d0 + math.pi) % (2 * math.pi) - math.pi
                x, y, ang = b[0], b[1], d0 + dd * smooth(u * 1.6)
                if dug: fall = 0.28 * math.sin(math.pi * u)                         # a nod: eating / harvesting
                act = dict(who=name, dug=dug)
            else:                                          # step to the next square
                e = smooth((frac - ACT) / (1 - ACT))
                x, y, ang = b[0] + (a[0] - b[0]) * e, b[1] + (a[1] - b[1]) * e, ANGS[a[2]]; walk = (frac - ACT) / (1 - ACT)
            if not dug:                                    # compost (the animals) or a sprout (Joe), then the grass grows
                size = smooth(frac / ACT) * (1 - smooth((frac - 0.55) / 0.4))
                show_prop(SPROUT if name == "joe" else COMPOST, sq, size * (1.0 if name == "joe" else 1.2))
        else:
            ang = ANGS[d]
        z = 0.03 if (round(x), round(y)) in show_dirt else 0.02
        place(name, x + c + 0.5, y + c + 0.5, z, ang, cam["s"], walk=walk, fall=fall)
        at[name] = (x + c + 0.5, y + c + 0.5)
    yaw = -10 + 16 * tt / tl.duration
    sc.set_camera(cam["cx"] + c + 0.5, cam["cy"] + c + 0.5, cam["s"], yaw, cam["pitch"])
    bpy.context.view_layer.update()
    rec = dict(run=run.name, scene=si, round=run.done // n, moves=run.done, dirt=len(show_dirt), act=act, s=round(cam["s"], 1),
               who={name: to_screen(*p, 1.0 if name == "joe" else 0.8) for name, p in at.items()})
    SCREEN[str(f)] = rec
    sc.render(path)
    if args.pause: time.sleep(args.pause)            # breathing room for the chip (and the fan)
    rendered += 1
    if rendered % 10 == 0: screen_path.write_text(json.dumps(SCREEN))
    if rendered % 30 == 0:
        el = time.time() - t_start
        print(f"frame {f}/{tl.nf}  {el / rendered:.2f}s/frame  ~{len(range(f + 1, end, args.every)) * el / rendered / 60:.0f} min left", flush=True)
screen_path.write_text(json.dumps(SCREEN))
print(f"done: {rendered} frames in {(time.time() - t_start) / 60:.1f} min -> {out}", flush=True)
