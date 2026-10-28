"""Render Experiment 11's frames (Joe's crop codes). Captions, notes and sound come later (pipeline/compose_ep11.py).

Usage: blender -b -P blender/render_ep11.py -- [--scale 100] [--every 1] [--start 0] [--end 0] [--pause 1.0]
Frames: renders/ep11_codes/frames[_draft]/f_00000.jpg, plus screen.json (where Joe, each field and the other
experiments are on screen, and the crop under Joe, for the notes). Frames already on disk are skipped.
--end 0 means to the end.

Story (pinned to words, see pipeline/ep11_timeline.py): four codes, each on its own field in a 2 x 2 block.
Every field is one image lying on the grass (a pixel per square, a colour per crop), so hundreds of thousands
of squares cost nothing. Joe walks one square at a time while slow; the camera fits what he's planted, so it
pulls back as the pattern grows (he becomes a glowing dot). Hard cuts between codes; then the whole block,
then the whole farm.
"""
import argparse, json, math, sys, time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "pipeline"))
import scene as S
from common import FPS, N, ROOT
from ep11_timeline import FIELDS, Timeline
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

tl = Timeline(ROOT / "episodes" / "ep11_codes.py")
out = tl.dir / ("frames" if args.scale == 100 and args.every == 1 else "frames_draft"); out.mkdir(parents=True, exist_ok=True)
end = args.end or tl.nf
c = N // 2
PAD = 4
ANGS = [math.pi / 2, 0, -math.pi / 2, math.pi]
# one colour per crop (0 is grass: see-through): dirt, wheat, pumpkins, tomatoes, cotton, lavender,
# blueberries, blossom, kale, lime, mint
CROPS = np.array([(0, 0, 0), (120, 80, 48), (222, 178, 70), (236, 120, 30), (200, 60, 50), (240, 230, 210),
                  (150, 90, 160), (70, 120, 200), (250, 190, 210), (40, 70, 45), (180, 210, 90), (110, 200, 200)]) / 255
PAL = np.concatenate([CROPS, np.r_[0, np.ones(11)][:, None]], 1).astype(np.float32)

def lift(s_px):
    """How high a flat image must float over the grass not to flicker into it: the further the camera, the more."""
    return 0.03 if s_px > 12 else max(0.4, 2.2 / s_px)

def smooth(u): u = min(1.0, max(0.0, u)); return u * u * (3 - 2 * u)

class Plane:
    """One trail image on the field (scene.set_trail_image keeps only one, so swap them in and out)."""
    def __init__(self): self.h = None
    def set(self, img, x0, y0, **kw):
        if self.h: sc.trail_plane, sc.trail_img, sc._trail_size, sc._trail_scale = self.h
        else: sc.trail_plane = None; sc._trail_size = None
        sc.set_trail_image(img, x0, y0, **kw)
        self.h = (sc.trail_plane, sc.trail_img, sc._trail_size, sc._trail_scale)

class Field:
    def __init__(self, name):
        self.name, self.lg, b = name, tl.log[name], tl.box[name]
        self.b = b; self.size = max(b[2] - b[0], b[3] - b[1]) + 1 + 2 * PAD
        ox, oy = tl.origin[name]; self.ox, self.oy = c + ox, c + oy          # the start square on the grid
        self.grid = np.zeros((self.size, self.size), np.uint8); self.done = 0; self.shown = -1
        self.flat = ((self.lg["cy"] - b[1] + PAD) * self.size + (self.lg["cx"] - b[0] + PAD)).astype(np.int64)
        lo = np.minimum.accumulate; hi = np.maximum.accumulate
        self.minx, self.maxx = lo(self.lg["cx"]), hi(self.lg["cx"]); self.miny, self.maxy = lo(self.lg["cy"]), hi(self.lg["cy"])
        self.plane = Plane()
    def advance(self, M):
        if M <= self.done: return
        idx = self.flat[self.done:M][::-1]; val = self.lg["cc"][self.done:M][::-1]
        u, first = np.unique(idx, return_index=True)                # the last crop planted on each square wins
        self.grid.flat[u] = val[first]; self.done = M
    def draw(self):
        if self.shown == self.done: return
        self.plane.set(PAL[self.grid], self.ox + self.b[0] - PAD, self.oy + self.b[1] - PAD, z=0.03, glow=0.22)
        self.shown = self.done
    def joe(self, M, frac):
        """Joe on the grid (x, y), facing, and how far through his step he is."""
        lg = self.lg
        x0, y0 = (lg["px"][M - 1], lg["py"][M - 1]) if M else (0, 0)
        d0 = lg["pd"][M - 1] if M else 0
        if frac and M < len(lg["px"]):
            x1, y1, d1 = lg["px"][M], lg["py"][M], lg["pd"][M]
            if frac < 0.35:                                   # turn on the spot
                dd = (ANGS[d1] - ANGS[d0] + math.pi) % (2 * math.pi) - math.pi
                return self.ox + x0 + 0.5, self.oy + y0 + 0.5, ANGS[d0] + dd * smooth(frac / 0.35), 0.0
            e = smooth((frac - 0.35) / 0.65)
            return self.ox + x0 + (x1 - x0) * e + 0.5, self.oy + y0 + (y1 - y0) * e + 0.5, ANGS[d1], (frac - 0.35) / 0.65
        return self.ox + x0 + 0.5, self.oy + y0 + 0.5, ANGS[d0], 0.0
    def fit(self, M):
        """Camera target that fits everything planted so far (and Joe)."""
        i = max(0, M - 1)
        x0, x1 = min(self.minx[i], 0), max(self.maxx[i], 0); y0, y1 = min(self.miny[i], 0), max(self.maxy[i], 0)
        return self.ox + (x0 + x1 + 1) / 2, self.oy + (y0 + y1 + 1) / 2, max(x1 - x0, (y1 - y0) * 0.85)

# ---------------- scene ----------------
sc = S.Scene("farm", scale=args.scale)
sc.set_sky((120, 182, 242))
FLD = {name: Field(name) for name, _, _ in FIELDS}
for fl in FLD.values(): fl.draw()

# ---------------- the whole farm at the end: every experiment so far above today's 2 x 2 block ----------------
E4 = (c, c - tl.quad - 60 - 235)                    # Experiment 4's field on this grid
OV = Plane()
OV_RGBA, OV_FID, OV_BOX, OV_BARN = FO.build_upto10()
STAG = (np.sin(np.arange(FO.SZ)[:, None] * 12.9898 + np.arange(FO.SZ)[None, :] * 78.233) * 43758.5453) % 1.0
REVEAL = {10: tl.t_pull + 0.3, 9: tl.t_pull + 0.5, 8: tl.t_pull + 0.7, 7: tl.t_pull + 0.9, 5: tl.t_pull + 1.1,
          6: tl.t_pull + 1.3, 1: tl.t_pull + 1.5, 2: tl.t_pull + 1.7, 3: tl.t_pull + 1.9}
def overview(tt):
    a = np.zeros((FO.SZ, FO.SZ), np.float32)
    for k, t0 in REVEAL.items():
        mm = OV_FID == k; a[mm] = np.clip((tt - t0) / 0.4 - STAG[mm] * 1.0, 0, 1)
    img = OV_RGBA.copy(); img[..., 3] *= a
    return img
sc.add_barn(E4[0] + OV_BARN[0], E4[1] + OV_BARN[1], facing=-math.pi / 2)        # Experiment 3's barn
BOXES = {k: (b[0] + E4[0], b[1] + E4[1], b[2] + E4[0], b[3] + E4[1]) for k, b in OV_BOX.items()}
BOXES[11] = (c - tl.quad, c - tl.quad, c + tl.quad, c + tl.quad)
allb = np.array(list(BOXES.values()))
OV_C = ((allb[:, 0].min() + allb[:, 2].max()) / 2, (allb[:, 1].min() + allb[:, 3].max()) / 2)
OV_S = min(1000 / (allb[:, 2].max() - allb[:, 0].min() + 60), 1500 / (allb[:, 3].max() - allb[:, 1].min() + 100))
BLOCK = (c, c + 20, 1000 / (2 * tl.quad + 60))

def to_screen(gx, gy, z=0.0):
    from bpy_extras.object_utils import world_to_camera_view
    from mathutils import Vector
    v = world_to_camera_view(sc.sc, sc.cam, Vector((gx, -gy, z)))
    return [round(v.x * S.W, 1), round((1 - v.y) * S.H, 1), round(v.z, 2)]
screen_path = out / "screen.json"
SCREEN = json.loads(screen_path.read_text()) if screen_path.exists() else {}

cam = dict(cx=0.0, cy=0.0, s=100.0, pitch=54.0)
t_start = time.time(); rendered = 0; last_scene = -1; ov_set = -1
for f in range(end):
    tt = f / FPS
    si = int(tl.scene[f]); name = tl.scenes[si][0]; fl = FLD[name]
    target = float(tl.sched[f]); M = int(target); slow = tl.rate[f] < FPS * 0.5
    fl.advance(M)
    frac = target - M if (slow and M < len(fl.lg["cx"])) else 0.0
    jx, jy, ang, walk = fl.joe(M, frac)
    # ---- camera: fit the field so far (close while slow); the block on "Same"; the farm after "carrots"
    fx, fy, ext = fl.fit(M)
    tgt = dict(cx=fx, cy=fy, s=min(100.0, 960 / (ext + 6)), pitch=54.0); k_ = 0.12 if slow else 0.3   # keep up while racing
    if tt >= tl.t_same:
        u = smooth((tt - tl.t_same) / 1.6)
        tgt = dict(cx=fx + (BLOCK[0] - fx) * u, cy=fy + (BLOCK[1] - fy) * u, s=tgt["s"] * (BLOCK[2] / tgt["s"]) ** u, pitch=54.0); k_ = 0.3
    if tt >= tl.t_pull:
        u = smooth((tt - tl.t_pull) / 2.6)
        tgt = dict(cx=BLOCK[0] + (OV_C[0] - BLOCK[0]) * u, cy=BLOCK[1] + (OV_C[1] - BLOCK[1]) * u,
                   s=BLOCK[2] * (OV_S / BLOCK[2]) ** u, pitch=54 + 8 * u); k_ = 0.3
    if si != last_scene: cam.update(tgt); last_scene = si             # a hard cut: start framed
    cam["s"] *= (tgt["s"] / cam["s"]) ** k_
    for key in ("cx", "cy", "pitch"): cam[key] += (tgt[key] - cam[key]) * k_
    if f < args.start or f % args.every: continue
    path = out / f"f_{f:05d}.jpg"
    if path.exists() and str(f) in SCREEN: continue
    for other in FLD.values():          # fields we've cut away from show their finished pattern
        if other is not fl and other.done == 0 and tl.scenes.index(next(s_ for s_ in tl.scenes if s_[0] == other.name)) < si:
            other.advance(len(other.lg["cx"]))
        other.draw()
        other.plane.h[0].location.z = lift(cam["s"])
    if tt >= tl.t_pull:
        key = round(min(tt, max(REVEAL.values()) + 1.5), 2)
        if key != ov_set:                            # lifted: from far away the floor shows through a plane at z=0.02
            OV.set(overview(tt), E4[0] - FO.SZ // 2, E4[1] - FO.SZ // 2, glow=0.15, z=0.4); ov_set = key
        OV.h[0].location.z = lift(cam["s"])
    tg = np.zeros((N, N), np.uint8)
    if cam["s"] > 30:                                # close: no grass tufts on the squares he's planted
        ys_, xs_ = np.nonzero(fl.grid); gx_ = xs_ + fl.ox + fl.b[0] - PAD; gy_ = ys_ + fl.oy + fl.b[1] - PAD
        ok = (gx_ >= 0) & (gx_ < N) & (gy_ >= 0) & (gy_ < N); tg[gy_[ok], gx_[ok]] = 1
    sc.set_tufts(tg, cam["cx"], cam["cy"], cam["s"]); sc.set_floor(cam["s"])
    sc.set_walker(jx, jy, 0.04, ang, cam["s"], walk=walk)
    yaw = -8 + 10 * tt / tl.duration
    sc.set_camera(cam["cx"], cam["cy"], cam["s"], yaw, cam["pitch"])
    bpy.context.view_layer.update()
    under = int(fl.grid[int(jy - fl.oy) - fl.b[1] + PAD, int(jx - fl.ox) - fl.b[0] + PAD]) if not frac or frac < 0.35 else None
    rec = dict(field=name, steps=M, s=round(cam["s"], 1), joe=to_screen(jx, jy, 1.0), crop=under, slow=bool(slow))
    if tt >= tl.t_same - 0.2:
        rec["codes"] = {n_: to_screen(f_.ox + (f_.b[0] + f_.b[2]) / 2 + 0.5, f_.oy + f_.b[1] - 6, 0.0) for n_, f_ in FLD.items()}
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
