"""Render Experiment 4's frames (Joe and Daisy). Captions, notes and sound come later (pipeline/compose_ep04.py).

Usage: blender -b -P blender/render_ep04.py -- [--scale 100] [--every 1] [--start 0] [--end 0] [--pause 1.0]
Frames: renders/ep04_farmers/frames[_draft]/f_00000.jpg, plus screen.json (where Joe, Daisy and the
other experiments' fields are on screen, for the handwritten notes). Frames already on disk are skipped.

Story (pinned to words, see pipeline/ep04_timeline.py): Joe and Daisy take turns, one slow move at a
time (Daisy nods to eat grass, or leaves a little compost pile on bare dirt; Joe harvests with a
nod, or plants a sprout). Squares keep the colour of whoever cleared them (Joe blue, Daisy gold).
Then racing: the mess, the meeting at round 1,181, the rewind to a spotless field at 2,362, the
upside-down replay, exactly home at 4,724. Then the camera pulls back over the whole farm, where
the earlier experiments' fields grow in around today's (pipeline/farm_overview.py).
"""
import argparse, json, math, sys, time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "pipeline"))
import scene as S
from common import FPS, N, ROOT
from ep04_timeline import Timeline
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

tl = Timeline(ROOT / "episodes" / "ep04_farmers.py")
out = tl.dir / ("frames" if args.scale == 100 and args.every == 1 else "frames_draft"); out.mkdir(parents=True, exist_ok=True)
end = args.end or tl.nf
c = N // 2                                     # today's field: Joe's start is grid (c, c)
MOVES, TOTAL = tl.moves, len(tl.moves)
ACT = 0.35                                     # while slow: the action takes the first 35% of a move, then the step

# ---------------- colours ----------------
def hsv(h, s, v): return FO.hsv2rgb(np.atleast_1d(np.asarray(h, float)), np.atleast_1d(np.asarray(s, float)), np.atleast_1d(np.asarray(v, float)))
def to_lin(x): return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)
HUES = (0.58, 0.12)                            # Joe blue (his overalls), Daisy gold (her colour in Experiment 3)

# ---------------- the farm overview: one image under everything, grown in at the end ----------------
OV_RGBA, OV_FID, OV_BOX, OV_BARN = FO.build()
STAG = (np.sin(np.arange(FO.SZ)[:, None] * 12.9898 + np.arange(FO.SZ)[None, :] * 78.233) * 43758.5453) % 1.0
REVEAL = {1: tl.t_thanks + 0.7, 2: tl.t_thanks + 1.3, 3: tl.t_thanks + 1.9}   # each field grows in over ~1 s
def overview(tt):
    a = np.zeros((FO.SZ, FO.SZ), np.float32)
    for k, t0 in REVEAL.items():
        m = OV_FID == k
        a[m] = np.clip((tt - t0) / 0.5 - STAG[m] * 1.2, 0, 1)
    img = OV_RGBA.copy(); img[..., 3] *= a
    return img

# ---------------- scene ----------------
sc = S.Scene("farm", scale=args.scale)
sc.set_sky((120, 182, 242))
daisy = sc.add_character("sheep")
sc.add_barn(c + OV_BARN[0], c + OV_BARN[1], facing=-math.pi / 2)        # Experiment 3's barn, out on the farm
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
    p.location = (sq[0] + 0.5, -(sq[1] + 0.5), 0.03); p.scale = (size,) * 3

def smooth(u): u = min(1.0, max(0.0, u)); return u * u * (3 - 2 * u)

def to_screen(gx, gy, z=0.0):
    from bpy_extras.object_utils import world_to_camera_view
    from mathutils import Vector
    v = world_to_camera_view(sc.sc, sc.cam, Vector((gx, -gy, z)))
    return [round(v.x * S.W, 1), round((1 - v.y) * S.H, 1), round(v.z, 2)]
screen_path = out / "screen.json"
SCREEN = json.loads(screen_path.read_text()) if screen_path.exists() else {}

# ---------------- state, advanced every frame (also the skipped ones, so it's always right) ----------------
dirt, owner, changed, changed_f = set(), {}, {}, {}
pos = [list(MOVES[0][3]), list(MOVES[1][3])]
done = 0
cam = dict(cx=-1.0, cy=-1.0, s=110.0, pitch=54.0)
OV_C, OV_S, OV_P = (15.0, 10.0), 1.75, 62.0                 # the overview: middle, zoom, pitch
t_start = time.time(); rendered = 0; ov_set = -1
for f in range(end):
    tt = f / FPS
    target = float(tl.sched[f]); M = int(target); slow = tl.rate[f] < FPS * 0.5     # a move lasts 2+ frames
    while done < M:
        k, sq, dug, _, after = MOVES[done]
        if dug: dirt.add(sq); owner[sq] = k
        else: dirt.discard(sq)
        changed[sq] = done; changed_f[sq] = f; pos[k] = list(after); done += 1
    # the move in progress (only drawn while slow): action first, then the step
    frac = target - M if (slow and M < TOTAL) else 0.0
    cur = MOVES[M] if frac else None
    show_dirt = set(dirt)
    if cur and frac >= ACT:
        (show_dirt.add if cur[2] else show_dirt.discard)(cur[1])
    # ---- camera target
    if tt < tl.t_thanks:
        allp = np.array([p[:2] for p in pos] + [list(p) for p in dirt], float)
        x0, y0 = allp.min(0); x1, y1 = allp.max(0)
        tgt = dict(cx=(x0 + x1 + 1) / 2, cy=(y0 + y1 + 1) / 2, s=min(120.0, 960 / (max(x1 - x0, (y1 - y0) * 0.85) + 6)), pitch=54.0)
        if tt < tl.t_slow_end: tgt["s"] = max(tgt["s"], 105.0)          # close while Joe explains
        if tl.t_home <= tt: tgt.update(s=95.0)                           # back home: close on the two of them
        k_ = 0.12 if tt < 1.0 else 0.07
    else:                                                                 # pull back over the whole farm
        u = smooth((tt - tl.t_thanks - 0.2) / 2.6)
        tgt = dict(cx=OV_C[0] * u - 1.0 * (1 - u), cy=OV_C[1] * u - 1.0 * (1 - u), s=95.0 * (OV_S / 95.0) ** u, pitch=54 + (OV_P - 54) * u)
        k_ = 0.25
    cam["s"] *= (tgt["s"] / cam["s"]) ** k_
    for key in ("cx", "cy", "pitch"): cam[key] += (tgt[key] - cam[key]) * k_
    if f < args.start or f % args.every: continue
    path = out / f"f_{f:05d}.jpg"
    if path.exists() and str(f) in SCREEN: continue
    # ---- today's field: dirt in the colour of whoever cleared it; fresh squares vivid
    fade = max(30.0, tl.rate[f] / FPS * 10)
    cells = sorted(show_dirt)
    regrown = [p for p, f_ in changed_f.items() if p not in show_dirt and f - f_ < 10 and done - changed[p] < 12] if slow else []
    if cur and frac >= ACT and not cur[2]: regrown.append(cur[1])
    xs = np.array([p[0] + c for p in cells + regrown], int); ys = np.array([p[1] + c for p in cells + regrown], int)
    paint = np.zeros((len(xs), 3))
    for i, p in enumerate(cells):
        who = owner.get(p, cur[0] if cur else 0) if not (cur and p == cur[1]) else cur[0]
        age = 0 if (cur and p == cur[1]) else done - changed.get(p, done)
        fr = math.exp(-age / fade)
        paint[i] = hsv(HUES[who], 0.45 + 0.5 * fr, 0.88 + 0.12 * fr)[0]
    for j, p in enumerate(regrown):
        fr = 1.0 if (cur and p == cur[1]) else max(0.0, 1 - (f - changed_f.get(p, f)) / 10)
        paint[len(cells) + j] = hsv(0.24, 0.55 + 0.2 * fr, 0.7 + 0.3 * fr)[0]
    sc.set_cells(xs, ys, np.full(len(xs), 0.03), np.zeros(len(xs)), np.ones(len(xs)), paint=to_lin(paint))
    grid = np.zeros((N, N), np.uint8)
    if cells: grid[np.array([p[1] for p in cells]) + c, np.array([p[0] for p in cells]) + c] = 1
    sc.set_tufts(grid, cam["cx"] + c, cam["cy"] + c, cam["s"]); sc.set_floor(cam["s"])
    # ---- the other experiments (only once the zoom out starts)
    if tt >= tl.t_thanks:
        key = round(min(tt, REVEAL[3] + 1.8), 2)
        if key != ov_set: sc.set_trail_image(overview(tt), c - FO.SZ // 2, c - FO.SZ // 2, glow=0.15, z=0.4); ov_set = key   # lifted: from far away the floor shows through a plane at z=0.02
    # ---- Joe and Daisy: while slow, the one moving acts on his square, then steps
    show_prop(COMPOST, (0, 0), 0); show_prop(SPROUT, (0, 0), 0)
    act = None
    for k in range(2):
        x, y, d = pos[k]; walk = fall = 0.0
        if cur and cur[0] == k:
            _, sq, dug, b, a = cur
            if frac < ACT:                                 # turn on the spot, and do the job
                u = frac / ACT
                d0, d1 = ANGS[b[2]], ANGS[a[2]]; dd = (d1 - d0 + math.pi) % (2 * math.pi) - math.pi
                x, y, ang = b[0], b[1], d0 + dd * smooth(u * 1.6)
                if dug: fall = 0.28 * math.sin(math.pi * u)                         # a nod: eating / harvesting
                act = dict(who=k, dug=dug)
            else:                                          # step to the next square
                e = smooth((frac - ACT) / (1 - ACT))
                x, y, ang = b[0] + (a[0] - b[0]) * e, b[1] + (a[1] - b[1]) * e, ANGS[a[2]]; walk = (frac - ACT) / (1 - ACT)
            if not dug:                                    # compost (Daisy) or a sprout (Joe), then the grass grows
                size = smooth(frac / ACT) * (1 - smooth((frac - 0.55) / 0.4))
                show_prop(SPROUT if k == 0 else COMPOST, sq, size * (1.0 if k == 0 else 1.2))
        else:
            ang = ANGS[d]
        z = 0.03 if (round(x), round(y)) in show_dirt else 0.02
        if k == 0: sc.set_walker(x + c + 0.5, y + c + 0.5, z, ang, cam["s"], walk=walk, fall=fall)
        else: sc.set_character(daisy, x + c + 0.5, y + c + 0.5, z, ang, cam["s"], walk=walk, fall=fall)
        pos_draw = (x + c + 0.5, y + c + 0.5)
        if k == 0: joe_at = pos_draw
        else: daisy_at = pos_draw
    yaw = -10 + 16 * min(tt, tl.t_thanks) / tl.t_thanks
    sc.set_camera(cam["cx"] + c + 0.5, cam["cy"] + c + 0.5, cam["s"], yaw, cam["pitch"])
    bpy.context.view_layer.update()
    rec = dict(round=done // 2, moves=done, dirt=len(show_dirt), joe=to_screen(*joe_at, 1.0), daisy=to_screen(*daisy_at, 0.8), act=act)
    if tt >= tl.t_thanks:
        rec["fields"] = {str(k): to_screen((b[0] + b[2]) / 2 + c + 0.5, b[1] + c - 4, 0.0) for k, b in OV_BOX.items()}
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
