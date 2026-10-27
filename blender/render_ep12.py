"""Render Experiment 12's frames (birthday cows). Tags, cards, the tally, pair lines, captions and sound come later
(pipeline/compose_ep12.py), placed with screen.json.

Usage: blender -b -P blender/render_ep12.py -- [--scale 100] [--every 1] [--start 0] [--end 0] [--pause 1.0]
       [--frames 10,200,450]   (just these frames, for preview stills)
Frames: renders/ep12_birthdays/frames[_draft]/f_00000.jpg, plus screen.json (where every cow's tag, Joe and the
cake pile are on screen; at the end, the fields). Frames already on disk are skipped. --end 0 means to the end.

Story (pinned to words, see pipeline/ep12_timeline.py): 23 cows (Experiment 9's cow) graze in a fenced paddock,
Joe in front. On "This" the camera moves in on cows 8 and 13, who look up at each other; back wide for the
tally and the pair lines; in on Joe as cakes pile up beside him; then the pull back over the whole farm:
Experiment 11's four fields and, above them, Experiments 1-10 (farm_overview.build_upto10), today's paddock
on the grass to their left.
"""
import argparse, json, math, sys, time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "pipeline"))
import scene as S
import scenery as SN
from common import FPS, N, ROOT
from ep12_timeline import HERD, PAIR, Timeline
import ep11_timeline as T11
import farm_overview as FO

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--scale", type=int, default=100)
ap.add_argument("--every", type=int, default=1)
ap.add_argument("--start", type=int, default=0)
ap.add_argument("--end", type=int, default=0)
ap.add_argument("--frames", default="", help="only these frames (comma separated), e.g. for preview stills")
ap.add_argument("--pause", type=float, default=1.0,
                help="seconds to rest after each frame, so the laptop runs cooler (0 = flat out)")
args = ap.parse_args(argv)
S.gentle()
import bpy

tl = Timeline(ROOT / "episodes" / "ep12_birthdays.py")
ONLY = {int(x) for x in args.frames.split(",") if x.strip()}
out = tl.dir / ("frames" if args.scale == 100 and args.every == 1 and not ONLY else "frames_draft"); out.mkdir(parents=True, exist_ok=True)
end = (max(ONLY) + 1) if ONLY else (args.end or tl.nf)
c = N // 2

def smooth(u): u = min(1.0, max(0.0, u)); return u * u * (3 - 2 * u)
def lift(s_px):
    """How high a flat image must float over the grass not to flicker into it: the further the camera, the more."""
    return 0.03 if s_px > 12 else max(0.4, 2.2 / s_px)

# ---------------- the herd: a loose block in the paddock (layout only: who stands where says nothing) ----------------
rng = np.random.default_rng(7)
rows = (5, 5, 5, 4, 4)
POS = []
for r_, k in enumerate(rows):
    for i in range(k):
        POS.append((c - (k - 1) * 0.95 + i * 1.9 + rng.uniform(-0.35, 0.35), c - 3.2 + r_ * 1.55 + rng.uniform(-0.25, 0.25)))
POS = np.array(POS[:HERD])
FACE = np.where(rng.random(HERD) < 0.5, 0.0, math.pi) + rng.uniform(-0.6, 0.6, HERD)     # mostly side on
PHASE, NODS = rng.uniform(0, 2 * math.pi, HERD), rng.uniform(0.25, 0.45, HERD)             # grazing
HC = POS.mean(0)
JOE = (POS[:, 0].min() - 0.6, POS[:, 1].max() + 2.4)
PILE = (JOE[0] + 1.6, JOE[1] - 0.3)

sc = S.Scene("farm", scale=args.scale)
sc.set_sky((120, 182, 242))
COW = [sc.add_character("cow") for _ in range(HERD)]
yard = (POS[:, 0].min() - 1.5, POS[:, 1].min() - 1.5, POS[:, 0].max() + 1.5, POS[:, 1].max() + 1.0)
SN.add_fence(sc, yard[0] - 1, yard[1] - 1, yard[2] + 1, yard[3] + 1)
SN.add_trees(sc, HC[0], HC[1], n=10, r0=13, r1=30, keep_clear=(yard[0] - 4, yard[1] - 3, yard[2] + 4, yard[3] + 40))

# ---------------- cakes: our own, sponge + icing + a cherry ----------------
def mat(name, rgb, rough=0.6): return S._material(name, S.lin(rgb), rough=rough)[0]
SPONGE, ICING, CHERRY = mat("Sponge", (226, 176, 104)), mat("Icing", (250, 246, 240), 0.4), mat("Cherry", (200, 30, 40), 0.3)
CAKES = []
layers = ((0, 0), (0.5, 0), (1.0, 0), (0.25, 0.42), (0.75, 0.42), (0.5, 0.84))       # (x, height): a little pyramid
for k in range(30):
    lx, lz = layers[k % 6]; row = k // 6
    root = bpy.data.objects.new(f"Cake{k}", None); sc.sc.collection.objects.link(root)
    root.location = (PILE[0] + lx - row * 0.15, -(PILE[1] - row * 0.55), lz + 0.0)
    for loc, kind, m, kw in (((0, 0, 0.1), "cylinder", SPONGE, dict(radius=0.24, depth=0.2, vertices=24)),
                             ((0, 0, 0.215), "cylinder", ICING, dict(radius=0.25, depth=0.05, vertices=24)),
                             ((0, 0, 0.27), "uv_sphere", CHERRY, dict(radius=0.045, segments=10, ring_count=6))):
        getattr(bpy.ops.mesh, f"primitive_{kind}_add")(location=loc, **kw)
        o = bpy.context.object; o.parent = root; o.data.materials.append(m); bpy.ops.object.shade_smooth()
    root.scale = (0, 0, 0); CAKES.append(root)

# ---------------- the whole farm at the end ----------------
class Plane:
    """One image on the field (scene.set_trail_image keeps only one, so swap them in and out)."""
    def __init__(self): self.h = None
    def set(self, img, x0, y0, **kw):
        if self.h: sc.trail_plane, sc.trail_img, sc._trail_size, sc._trail_scale = self.h
        else: sc.trail_plane = None; sc._trail_size = None
        sc.set_trail_image(img, x0, y0, **kw)
        self.h = (sc.trail_plane, sc.trail_img, sc._trail_size, sc._trail_scale)

t11 = T11.Timeline(ROOT / "episodes" / "ep11_codes.py")        # Experiment 11's four fields, as it ended
CROPS = np.array([(0, 0, 0), (120, 80, 48), (222, 178, 70), (236, 120, 30), (200, 60, 50), (240, 230, 210),
                  (150, 90, 160), (70, 120, 200), (250, 190, 210), (40, 70, 45), (180, 210, 90), (110, 200, 200)]) / 255
PAL = np.concatenate([CROPS, np.r_[0, np.ones(11)][:, None]], 1).astype(np.float32)        # as in render_ep11.py
B11 = (c + t11.quad + 90, c)                    # the block's middle: to the right of today's paddock
FIELD11 = []
for name, _, _ in T11.FIELDS:
    lg, b = t11.log[name], t11.box[name]; P = 4; size = max(b[2] - b[0], b[3] - b[1]) + 1 + 2 * P
    g = np.zeros((size, size), np.uint8)
    flat = ((lg["cy"] - b[1] + P) * size + (lg["cx"] - b[0] + P)).astype(np.int64)
    u, first = np.unique(flat[::-1], return_index=True); g.flat[u] = lg["cc"][::-1][first]     # the last crop wins
    ox, oy = t11.origin[name]
    FIELD11.append((PAL[g], B11[0] + ox + b[0] - P, B11[1] + oy + b[1] - P, Plane()))
E4 = (B11[0], B11[1] - t11.quad - 60 - 235)          # Experiment 4's field (the farm sits above the block, as in Experiment 11)
OV = Plane()
OV_RGBA, OV_FID, OV_BOX, OV_BARN = FO.build_upto10()
STAG = (np.sin(np.arange(FO.SZ)[:, None] * 12.9898 + np.arange(FO.SZ)[None, :] * 78.233) * 43758.5453) % 1.0
REVEAL = {10: 0.5, 9: 0.6, 8: 0.7, 7: 0.8, 5: 0.9, 6: 1.0, 1: 1.1, 2: 1.2, 3: 1.3}     # seconds after the pull starts
def overview(tt):
    a = np.zeros((FO.SZ, FO.SZ), np.float32)
    for k, t0 in REVEAL.items():
        mm = OV_FID == k; a[mm] = np.clip((tt - tl.t_pull - t0) / 0.4 - STAG[mm] * 1.0, 0, 1)
    img = OV_RGBA.copy(); img[..., 3] *= a
    return img
sc.add_barn(E4[0] + OV_BARN[0], E4[1] + OV_BARN[1], facing=-math.pi / 2)        # Experiment 3's barn
BOXES = {k: (b[0] + E4[0], b[1] + E4[1], b[2] + E4[0], b[3] + E4[1]) for k, b in OV_BOX.items()}
BOXES[11] = (B11[0] - t11.quad, B11[1] - t11.quad, B11[0] + t11.quad, B11[1] + t11.quad)
BOXES[12] = tuple(int(v) for v in yard)
allb = np.array(list(BOXES.values()))
OV_C = ((allb[:, 0].min() + allb[:, 2].max()) / 2, (allb[:, 1].min() + allb[:, 3].max()) / 2)
OV_S = 0.85 * min(1000 / (allb[:, 2].max() - allb[:, 0].min() + 60), 1500 / (allb[:, 3].max() - allb[:, 1].min() + 100))

def to_screen(gx, gy, z=0.0):
    from bpy_extras.object_utils import world_to_camera_view
    from mathutils import Vector
    v = world_to_camera_view(sc.sc, sc.cam, Vector((gx, -gy, z)))
    return [round(v.x * S.W, 1), round((1 - v.y) * S.H, 1), round(v.z, 2)]
screen_path = out / "screen.json"
SCREEN = json.loads(screen_path.read_text()) if screen_path.exists() else {}

# ---------------- camera shots ----------------
ext = max(np.ptp(POS[:, 0]), np.ptp(POS[:, 1]) * 0.85)
WIDE = dict(cx=HC[0] - 0.7, cy=HC[1] + 1.3, s=1000 / (ext + 3.5), pitch=50.0)
pa, pb = POS[PAIR[0]], POS[PAIR[1]]
PAIRSHOT = dict(cx=(pa[0] + pb[0]) / 2 + 0.5, cy=(pa[1] + pb[1]) / 2 + 0.5,
                s=min(150.0, 960 / (max(abs(pa[0] - pb[0]), abs(pa[1] - pb[1]) * 0.85) + 3.5)), pitch=50.0)
JOESHOT = dict(cx=(JOE[0] + PILE[0]) / 2 + 0.9, cy=JOE[1] - 0.6, s=175.0, pitch=42.0)
SHOTS = dict(wide=WIDE, pair=PAIRSHOT, joe=JOESHOT)

cam = dict(WIDE)
t_start = time.time(); rendered = 0; ov_key = -1
for f in range(end):
    tt = f / FPS; shot = tl.shot(f)
    if shot == "pull":
        u = smooth((tt - tl.t_pull) / 2.8)
        tgt = dict(cx=JOESHOT["cx"] + (OV_C[0] - JOESHOT["cx"]) * u, cy=JOESHOT["cy"] + (OV_C[1] - JOESHOT["cy"]) * u,
                   s=JOESHOT["s"] * (OV_S / JOESHOT["s"]) ** u, pitch=42 + 20 * u); k_ = 0.3
    else:
        tgt = SHOTS[shot]; k_ = 0.1
    cam["s"] *= (tgt["s"] / cam["s"]) ** k_
    for key in ("cx", "cy", "pitch"): cam[key] += (tgt[key] - cam[key]) * k_
    if ONLY and f not in ONLY: continue
    if f < args.start or f % args.every: continue
    path = out / f"f_{f:05d}.jpg"
    if path.exists() and str(f) in SCREEN: continue
    # ---- the cows graze (a slow nod each); on "This", cows 8 and 13 look up and turn to each other
    look = smooth((tt - tl.t_pair) / 0.6) * (1 - smooth((tt - tl.t_test - 0.3) / 0.6))
    ANG = FACE.copy()
    for i, h in enumerate(COW):
        ang = FACE[i]; nod = 0.16 * max(0.0, math.sin(tt * NODS[i] * 2 * math.pi + PHASE[i])) ** 2
        if i in PAIR:
            j = PAIR[1] if i == PAIR[0] else PAIR[0]
            to = math.atan2(-(POS[j, 1] - POS[i, 1]), POS[j, 0] - POS[i, 0])
            ang = ang + ((to - ang + math.pi) % (2 * math.pi) - math.pi) * look; nod *= 1 - look
        ANG[i] = ang; sc.set_character(h, POS[i, 0] + 0.5, POS[i, 1] + 0.5, 0.02, ang, cam["s"], fall=nod)
    # ---- Joe faces the camera; a shrug on "flour."
    shrug = smooth((tt - tl.t_flour) / 0.3) * (1 - smooth((tt - tl.t_pull - 0.6) / 0.4))
    sc.set_walker(JOE[0] + 0.5, JOE[1] + 0.5, 0.02, -math.pi / 2 + 0.35, cam["s"], tool=False,
                  arms={"right": (-0.4 * shrug, 0.9 * shrug), "left": (-0.4 * shrug, 0.9 * shrug)})
    n_cake = tl.cakes[f] * len(CAKES)
    for k, cake in enumerate(CAKES):
        g = smooth((n_cake - k) * 1.5); cake.scale = (g, g, g)
    # ---- grass, and the farm on the pull back
    sc.set_tufts(np.zeros((N, N), np.uint8), cam["cx"], cam["cy"], cam["s"]); sc.set_floor(cam["s"])
    if shot == "pull":
        key = round(min(tt - tl.t_pull, 2.0), 2)
        if key != ov_key:
            a = smooth((tt - tl.t_pull - 0.2) / 0.6)
            for img, x0, y0, pl in FIELD11:
                im = img.copy(); im[..., 3] *= a; pl.set(im, x0, y0, z=0.03, glow=0.22)
            OV.set(overview(tt), E4[0] - FO.SZ // 2, E4[1] - FO.SZ // 2, glow=0.15, z=0.4); ov_key = key
        for *_, pl in FIELD11: pl.h[0].location.z = lift(cam["s"])
        OV.h[0].location.z = lift(cam["s"])
    yaw = -7 + 12 * tt / tl.duration
    sc.set_camera(cam["cx"], cam["cy"], cam["s"], yaw, cam["pitch"])
    bpy.context.view_layer.update()
    h_, m_ = tl.herd_at(f)
    heads = [to_screen(POS[i, 0] + 0.5 + 0.55 * math.cos(ANG[i]), POS[i, 1] + 0.5 - 0.55 * math.sin(ANG[i]), 1.45) for i in range(HERD)]
    rec = dict(shot=shot, herd=h_, matches=m_, s=round(cam["s"], 1), tags=heads,
               mid=[to_screen(POS[i, 0] + 0.5, POS[i, 1] + 0.5, 0.75) for i in range(HERD)],
               joe=to_screen(JOE[0] + 0.5, JOE[1] + 0.5, 1.9), pile=to_screen(PILE[0] + 0.5, PILE[1] + 0.5, 1.3))
    if shot == "pull":
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
