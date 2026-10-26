"""Render Experiment 10's frames (the chicken and the barns). Captions, notes and sound come later (pipeline/compose_ep10.py).

Usage: blender -b -P blender/render_ep10.py -- [--scale 100] [--every 1] [--start 0] [--end 0] [--pause 1.0]
Frames: renders/ep10_chicken/frames[_draft]/f_00000.jpg, plus screen.json (where Joe, the chicken, the barns,
the middle hole and the other experiments are on screen, for the name plates and notes). Frames already on
disk are skipped. --end 0 means to the end.

Story (pinned to words, see pipeline/ep10_timeline.py): three barns at the corners of a big triangle; the
chicken hops halfway to a barn picked at random (the barn bounces), one hop at a time while Joe explains,
then faster and faster; every footprint stays, gold, painted as one fine image (8 pixels per square), so a
million of them cost nothing. The camera starts close on her and pulls back to the whole triangle. Then a
cut to four barns in a square next door, which just fills in. Then the whole farm.
"""
import argparse, json, math, sys, time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "pipeline"))
import scene as S
from common import FPS, N, ROOT
from ep10_timeline import SQ, Timeline
import chaos as CH
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

tl = Timeline(ROOT / "episodes" / "ep10_chicken.py")
out = tl.dir / ("frames" if args.scale == 100 and args.every == 1 else "frames_draft"); out.mkdir(parents=True, exist_ok=True)
end = args.end or tl.nf
c = N // 2
L = 24.0                                   # the triangle's side, in squares
RES = 8                                    # footprint pixels per square
PAD = 3                                    # squares of canvas round each field
ORIGIN = {"tri": (c, c), "square": (c + 40, c)}   # where each field's (0, 0) corner sits on the grid
BARNS = {"tri": CH.TRI, "square": SQ}
GOLD, BRIGHT = (0.98, 0.78, 0.28, 1.0), (1.0, 0.96, 0.62, 1.0)

def grid(run, p):
    """Sim units (y up) -> grid squares (y down)."""
    ox, oy = ORIGIN[run]
    return ox + p[..., 0] * L, oy - p[..., 1] * L

def smooth(u): u = min(1.0, max(0.0, u)); return u * u * (3 - 2 * u)

# ---------------- footprints: for each pixel, the first hop that lands on it ----------------
S_IMG = int((L + 2 * PAD) * RES)
FIRST, PIX = {}, {}
for run, (p, _) in tl.pts.items():
    gx, gy = grid(run, p)
    px = ((gx - (ORIGIN[run][0] - PAD)) * RES).astype(np.int64); py = ((gy - (ORIGIN[run][1] - L - PAD)) * RES).astype(np.int64)
    ok = (px >= 0) & (px < S_IMG) & (py >= 0) & (py < S_IMG)
    first = np.full((S_IMG, S_IMG), np.iinfo(np.int64).max, np.int64)
    np.minimum.at(first, (py[ok], px[ok]), np.arange(len(p))[ok])
    FIRST[run], PIX[run] = first, (px, py)
def footprints(run, h):
    """Every footprint up to hop h (the start isn't one), gold; the newest brighter and bigger."""
    img = np.zeros((S_IMG, S_IMG, 4), np.float32)
    f = FIRST[run]; img[(f >= 1) & (f <= h)] = GOLD
    r = 2 if h < 150 else 1 if h < 1500 else 0           # the first ones big enough to see, shrinking as they pile up
    if r:
        px, py = PIX[run]
        for dx in range(-r, r + 1):
            for dy in range(-r, r + 1):
                if dx * dx + dy * dy <= r * r + 1:
                    img[np.clip(py[1:h + 1] + dy, 0, S_IMG - 1), np.clip(px[1:h + 1] + dx, 0, S_IMG - 1)] = GOLD
    if h >= 1:
        px, py = PIX[run]; x, y = px[h], py[h]
        img[max(0, y - 2):y + 3, max(0, x - 2):x + 3] = BRIGHT
    return img

class Plane:
    """One trail image on the field (scene.set_trail_image keeps only one, so swap them in and out)."""
    def __init__(self): self.h = None
    def set(self, img, x0, y0, **kw):
        if self.h: sc.trail_plane, sc.trail_img, sc._trail_size, sc._trail_scale = self.h
        else: sc.trail_plane = None; sc._trail_size = None
        sc.set_trail_image(img, x0, y0, **kw)
        self.h = (sc.trail_plane, sc.trail_img, sc._trail_size, sc._trail_scale)

# ---------------- scene ----------------
sc = S.Scene("farm", scale=args.scale, character="chicken")
sc.set_sky((120, 182, 242))
joe = sc.add_character("joe")
BARN_OBJ = {}
for run, barns in BARNS.items():
    cx, cy = grid(run, barns.mean(0)); objs = []
    for b in barns:
        gx, gy = grid(run, b)
        face = math.atan2(-(cy - gy), cx - gx)            # world angle (y flipped) towards the middle
        objs.append(sc.add_barn(gx - 1.2 * math.cos(face) - 0.5, gy + 1.2 * math.sin(face) - 0.5, facing=face))
    BARN_OBJ[run] = objs
PLANE = {run: Plane() for run in BARNS}
for run in BARNS: PLANE[run].set(footprints(run, 0), ORIGIN[run][0] - PAD, ORIGIN[run][1] - L - PAD, z=0.03, gap=0.0, glow=0.3, cell=1 / RES)
JOE_AT = {run: (grid(run, BARNS[run][0])[0] + 3.0, grid(run, BARNS[run][0])[1] + 2.5) for run in BARNS}
WIDE = {run: (grid(run, BARNS[run].mean(0))[0], grid(run, BARNS[run].mean(0))[1] + (1.5 if run == "tri" else -1.5), 26.0) for run in BARNS}
MID = np.array([[0.5, 0.0], [0.75, np.sqrt(3) / 4], [0.25, np.sqrt(3) / 4]])     # the middle hole's corners

# ---------------- the whole farm at the end: every experiment so far; today's fields at about +240, +80 ----------------
E4 = (c - 240, c - 80)                              # Experiment 4's field on this grid
OV = Plane()
OV_RGBA, OV_FID, OV_BOX, OV_BARN = FO.build_upto9()
STAG = (np.sin(np.arange(FO.SZ)[:, None] * 12.9898 + np.arange(FO.SZ)[None, :] * 78.233) * 43758.5453) % 1.0
REVEAL = {9: tl.t_pull + 0.3, 8: tl.t_pull + 0.5, 7: tl.t_pull + 0.7, 5: tl.t_pull + 0.9, 6: tl.t_pull + 1.1,
          1: tl.t_pull + 1.3, 2: tl.t_pull + 1.5, 3: tl.t_pull + 1.8}
def overview(tt):
    a = np.zeros((FO.SZ, FO.SZ), np.float32)
    for k, t0 in REVEAL.items():
        mm = OV_FID == k; a[mm] = np.clip((tt - t0) / 0.4 - STAG[mm] * 1.0, 0, 1)
    img = OV_RGBA.copy(); img[..., 3] *= a
    return img
sc.add_barn(E4[0] + OV_BARN[0], E4[1] + OV_BARN[1], facing=-math.pi / 2)        # Experiment 3's barn
BOXES = {k: (b[0] + E4[0], b[1] + E4[1], b[2] + E4[0], b[3] + E4[1]) for k, b in OV_BOX.items()}
BOXES[10] = (c - 2, c - L - 2, c + 40 + L + 2, c + 2)
allb = np.array(list(BOXES.values()))
OV_C = ((allb[:, 0].min() + allb[:, 2].max()) / 2, (allb[:, 1].min() + allb[:, 3].max()) / 2)
OV_S = 1000 / (allb[:, 2].max() - allb[:, 0].min() + 90)

def to_screen(gx, gy, z=0.0):
    from bpy_extras.object_utils import world_to_camera_view
    from mathutils import Vector
    v = world_to_camera_view(sc.sc, sc.cam, Vector((gx, -gy, z)))
    return [round(v.x * S.W, 1), round((1 - v.y) * S.H, 1), round(v.z, 2)]
screen_path = out / "screen.json"
SCREEN = json.loads(screen_path.read_text()) if screen_path.exists() else {}

cam = dict(cx=0.0, cy=0.0, s=50.0, pitch=54.0)
t_start = time.time(); rendered = 0; last_scene = -1; ov_set = -1; shown = {run: -1 for run in BARNS}
for f in range(end):
    tt = f / FPS
    si = int(tl.scene[f]); run = tl.scenes[si][0]
    p, pick = tl.pts[run]
    target = float(tl.sched[f]); h = int(target); slow = tl.rate[f] < FPS * 0.5
    frac = target - h if (slow and h < len(pick)) else 0.0
    # the chicken: on her latest footprint, or mid-hop while slow (crouch, then an arc halfway to the barn)
    gx0, gy0 = grid(run, p[h]); ang = 0.0; z = 0.03; walk = 0.0; bounce = None
    if frac:
        gx1, gy1 = grid(run, p[h + 1]); ang = math.atan2(-(gy1 - gy0), gx1 - gx0)
        dist = math.hypot(gx1 - gx0, gy1 - gy0); bounce = (int(pick[h]), frac)
        if frac < 0.25: chick = (gx0, gy0)
        else:
            u = smooth((frac - 0.25) / 0.6)
            chick = (gx0 + (gx1 - gx0) * u, gy0 + (gy1 - gy0) * u); z = 0.03 + 0.22 * dist * math.sin(math.pi * u); walk = u
    else:
        chick = (gx0, gy0)
        if h >= 1: g_ = grid(run, p[h - 1]); ang = math.atan2(-(gy0 - g_[1]), gx0 - g_[0])
    # ---- camera: close on her while slow, then the whole field; then the whole farm
    wx, wy, ws = WIDE[run]
    tgt = dict(cx=wx, cy=wy, s=ws * (1.12 if run == "tri" and tt < tl.t_ten else 1.0), pitch=54.0)   # a touch closer while slow
    k_ = 0.06
    if tt >= tl.t_pull:
        u = smooth((tt - tl.t_pull) / 2.6)
        tgt = dict(cx=wx + (OV_C[0] - wx) * u, cy=wy + (OV_C[1] - wy) * u, s=ws * (OV_S / ws) ** u, pitch=54 + 8 * u); k_ = 0.25
    if si != last_scene:
        if last_scene >= 0: cam.update(tgt)                      # a hard cut: start framed
        else: cam.update(dict(cx=tgt["cx"], cy=tgt["cy"], s=tgt["s"], pitch=54.0))
        last_scene = si
    cam["s"] *= (tgt["s"] / cam["s"]) ** k_
    for key in ("cx", "cy", "pitch"): cam[key] += (tgt[key] - cam[key]) * k_
    if f < args.start or f % args.every: continue
    path = out / f"f_{f:05d}.jpg"
    if path.exists() and str(f) in SCREEN: continue
    # ---- footprints (each field keeps its own; the triangle stays full once we've cut away)
    for r_ in BARNS:
        hh = h if r_ == run else (len(tl.pts[r_][1]) if r_ == "tri" and run == "square" else 0)
        if hh != shown[r_]:
            PLANE[r_].set(footprints(r_, hh), ORIGIN[r_][0] - PAD, ORIGIN[r_][1] - L - PAD, z=0.03, glow=0.3, cell=1 / RES); shown[r_] = hh
    if tt >= tl.t_pull:
        key = round(min(tt, max(REVEAL.values()) + 1.5), 2)
        if key != ov_set:                            # lifted: from far away the floor shows through a plane at z=0.02
            OV.set(overview(tt), E4[0] - FO.SZ // 2, E4[1] - FO.SZ // 2, glow=0.15, z=0.4); ov_set = key
    # ---- barns: the picked one bounces while slow; the square's barns only once we're there
    for r_, objs in BARN_OBJ.items():
        for i, o in enumerate(objs):
            b = 1.0
            if r_ == run and bounce and bounce[0] == i: b = 1 + 0.18 * math.sin(math.pi * min(1.0, bounce[1] / 0.5))
            o.scale = (1.8 * b,) * 3
    sc.set_tufts(np.zeros((N, N), np.uint8), cam["cx"], cam["cy"], cam["s"]); sc.set_floor(cam["s"])
    sc.set_walker(chick[0], chick[1], z, ang, cam["s"], walk=walk)
    jx, jy = JOE_AT[run]
    sc.set_character(joe, jx, jy, 0.02, math.atan2(-(chick[1] - jy), chick[0] - jx), cam["s"])
    yaw = -8 + 10 * tt / tl.duration
    sc.set_camera(cam["cx"], cam["cy"], cam["s"], yaw, cam["pitch"])
    bpy.context.view_layer.update()
    rec = dict(run=run, hops=h, s=round(cam["s"], 1), chicken=to_screen(chick[0], chick[1], z + 0.8), joe=to_screen(jx, jy, 1.0),
               barns=[to_screen(*grid(run, b), 1.5) for b in BARNS[run]], picked=bounce[0] if bounce else None)
    if run == "tri": rec["mid"] = [to_screen(*grid("tri", m_), 0.05) for m_ in MID]
    if tt >= tl.t_pull:
        rec["fields"] = {str(k): to_screen((b[0] + b[2]) / 2 + 0.5, b[1] - 4, 0.0) for k, b in BOXES.items()}
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
