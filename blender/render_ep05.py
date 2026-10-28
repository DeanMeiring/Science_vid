"""Render Experiment 5's frames (four crops). Captions, notes, the mirror flash and sound come later
(pipeline/compose_ep05.py).

Usage: blender -b -P blender/render_ep05.py -- [--scale 100] [--every 1] [--start 0] [--end 0] [--pause 1.0]
Frames: renders/ep05_crops/frames[_draft]/f_00000.jpg, plus screen.json (where Joe and the mirror line
are on screen). Frames already on disk are skipped.

Story (pinned to words, see pipeline/ep05_timeline.py): from above, looking down the mirror line,
Joe plants grass -> dirt -> wheat -> pumpkins one step at a time, makes a quick mess, walks back
onto his first square on "image!", lands on mirror moments at 1,000 and 10,012, then races to
100,044 showing only mirror moments (a growing crop circle). On "circle!" the camera rises to
look straight down.
"""
import argparse, json, math, sys, time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "pipeline"))
import scene as S
from common import FPS, N, ROOT
from ep05_timeline import Timeline
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

tl = Timeline(ROOT / "episodes" / "ep05_crops.py")
out = tl.dir / ("frames" if args.scale == 100 and args.every == 1 else "frames_draft"); out.mkdir(parents=True, exist_ok=True)
end = args.end or tl.nf
c = N // 2; HIST = tl.hist; MIRRORS = set(tl.mirrors.tolist())
ANGS = [math.pi / 2, 0, -math.pi / 2, math.pi]
def smooth(u): u = min(1.0, max(0.0, u)); return u * u * (3 - 2 * u)

sc = S.Scene("farm", scale=args.scale)
sc.set_sky((120, 182, 242))

# ---------------- the whole farm at the end (as in Experiment 4): today's crop circle in the middle,
# Experiments 1-3 growing in around it, and Experiment 4's spotless field with Daisy on it.
# Experiment 4's layout (pipeline/farm_overview.py) is moved by OFF, so its field lands beside today's.
OFF = (90, 20)
OV_RGBA, OV_FID, OV_BOX, OV_BARN = FO.build()
OV_BOX = {k: (b[0] + OFF[0], b[1] + OFF[1], b[2] + OFF[0], b[3] + OFF[1]) for k, b in OV_BOX.items()}
STAG = (np.sin(np.arange(FO.SZ)[:, None] * 12.9898 + np.arange(FO.SZ)[None, :] * 78.233) * 43758.5453) % 1.0
T_PULL = tl.t_next - 0.3
REVEAL = {1: T_PULL + 0.8, 2: T_PULL + 1.4, 3: T_PULL + 2.0}
def overview(tt):
    a = np.zeros((FO.SZ, FO.SZ), np.float32)
    for k, t0 in REVEAL.items():
        m = OV_FID == k; a[m] = np.clip((tt - t0) / 0.5 - STAG[m] * 1.2, 0, 1)
    img = OV_RGBA.copy(); img[..., 3] *= a
    return img
OV_C, OV_S, OV_P, OV_YAW = (OFF[0] + 15.0, OFF[1] + 10.0), 1.75, 62.0, 6.0     # the overview: middle, zoom, pitch, yaw
sc.add_barn(c + OV_BARN[0] + OFF[0], c + OV_BARN[1] + OFF[1], facing=-math.pi / 2)
daisy = sc.add_character("sheep")
ov_set = -1
def to_screen(gx, gy, z=0.0):
    from bpy_extras.object_utils import world_to_camera_view
    from mathutils import Vector
    v = world_to_camera_view(sc.sc, sc.cam, Vector((gx, -gy, z)))
    return [round(v.x * S.W, 1), round((1 - v.y) * S.H, 1)]
screen_path = out / "screen.json"
SCREEN = json.loads(screen_path.read_text()) if screen_path.exists() else {}

g = np.zeros((N, N), np.int8); changed = np.full((N, N), -10 ** 9, np.int64); done = 0
cam = dict(cx=c + 0.5, cy=c + 1.0, s=110.0, pitch=72.0, yaw=90.0)
t_start = time.time(); rendered = 0
for f in range(end):
    tt = f / FPS
    T = int(tl.shown[f])
    while done < T:                                  # each step: the square Joe leaves grows the next crop
        x, y, _ = HIST[done]; g[y, x] = (g[y, x] + 1) % 4; changed[y, x] = done; done += 1
    ys, xs = np.nonzero(g)
    x0 = min(xs.min() if len(xs) else c, c - 2); x1 = max(xs.max() + 1 if len(xs) else c + 1, c + 3)
    y0 = min(ys.min() if len(ys) else c, c - 2); y1 = max(ys.max() + 1 if len(ys) else c + 1, c + 3)
    # the camera looks down the mirror line (between rows c and c+1): screen left/right = the two halves
    tgt_pitch = 72.0 + 16.0 * smooth((tt - tl.t_circle) / 1.6)          # "crop circle!": rise to look straight down
    room = 0.62 if tgt_pitch < 80 else 0.55
    s_t = min(110.0, 960 / (max(y1 - y0, (x1 - x0) * room) + 6))
    if tt < tl.t_rules_end: s_t = max(s_t, 100.0)                      # close while Joe explains
    tx = (x0 + x1) / 2 + 0.12 * (x1 - x0) * (1 - smooth((tt - tl.t_circle) / 1.6))
    k_ = 0.12 if tt < 1.0 else 0.07
    ty, tyaw = c + 1.0, 90.0
    if tt >= T_PULL:                                 # swing round and pull back over the whole farm
        u = smooth((tt - T_PULL) / 2.8)
        tx, ty = tx + (c + OV_C[0] - tx) * u, ty + (c + OV_C[1] - ty) * u
        s_t = s_t * (OV_S / s_t) ** u; tgt_pitch += (OV_P - tgt_pitch) * u; tyaw += (OV_YAW - tyaw) * u; k_ = 0.25
    cam["s"] *= (s_t / cam["s"]) ** k_
    for key, v in (("cx", tx), ("cy", ty), ("pitch", tgt_pitch), ("yaw", tyaw)): cam[key] += (v - cam[key]) * k_
    if f < args.start or f % args.every: continue
    path = out / f"f_{f:05d}.jpg"
    if path.exists() and str(f) in SCREEN: continue
    kind = g[ys, xs].astype(int)
    slow = tl.rate[f] < FPS * 0.5
    heat = np.exp(-(done - changed[ys, xs]) / 3.0) * 0.8 if slow else np.zeros(len(xs))   # a just-planted square glows
    sc.set_cells(xs, ys, np.array(sc.heights)[kind], heat, kind)
    sc.set_tufts(g, cam["cx"], cam["cy"], cam["s"]); sc.set_pumpkins(g, cam["cx"], cam["cy"], cam["s"]); sc.set_floor(cam["s"])
    if tt >= T_PULL:
        key = round(min(tt, REVEAL[3] + 1.8), 2)
        if key != ov_set:                            # lifted: from far away the floor shows through a plane at z=0.02
            sc.set_trail_image(overview(tt), c - FO.SZ // 2 + OFF[0], c - FO.SZ // 2 + OFF[1], glow=0.15, z=0.4); ov_set = key
    sc.set_character(daisy, c + OFF[0] + 0.5, c + OFF[1] + 0.5, 0.02, math.pi / 2, cam["s"])   # Experiment 4's spot
    # Joe: while slow he walks smoothly into the next square
    x, y, d = HIST[T]; walk = 0.0
    if slow and T < len(HIST) - 1:
        frac = tl.sched[f] - T; nx, ny, nd = HIST[T + 1]
        e = frac * frac * (3 - 2 * frac); x, y, d = x + (nx - x) * e, y + (ny - y) * e, nd; walk = frac
    on = g[int(round(y)), int(round(x))]
    sc.set_walker(x + 0.5, y + 0.5, sc.heights[on] if on else 0.02, ANGS[d], cam["s"], walk=walk)
    sc.set_camera(cam["cx"], cam["cy"], cam["s"], cam["yaw"], cam["pitch"])
    bpy.context.view_layer.update()
    SCREEN[str(f)] = dict(step=T, mirror=bool(T in MIRRORS), snap=bool(tl.snap[f]), joe=to_screen(x + 0.5, y + 0.5, 0.9),
                          axis=[to_screen(x0 - 1, c + 1.0, 0.3), to_screen(x1 + 1, c + 1.0, 0.3)])
    if tt >= T_PULL:
        boxes = {**OV_BOX, 5: (x0 - c, y0 - c, x1 - c, y1 - c)}
        SCREEN[str(f)]["fields"] = {str(k): to_screen((b[0] + b[2]) / 2 + c + 0.5, b[1] + c - 4, 0.0) for k, b in boxes.items()}
    sc.render(path)
    if args.pause: time.sleep(args.pause)            # breathing room for the chip (and the fan)
    rendered += 1
    if rendered % 10 == 0: screen_path.write_text(json.dumps(SCREEN))
    if rendered % 30 == 0:
        el = time.time() - t_start
        print(f"frame {f}/{tl.nf}  {el / rendered:.2f}s/frame  ~{len(range(f + 1, end, args.every)) * el / rendered / 60:.0f} min left", flush=True)
screen_path.write_text(json.dumps(SCREEN))
print(f"done: {rendered} frames in {(time.time() - t_start) / 60:.1f} min -> {out}", flush=True)
