"""Render Experiment 3's frames (the lost sheep). Captions, notes and sound come later (pipeline/compose_ep03.py).

Usage: blender -b -P blender/render_ep03.py -- [--scale 100] [--every 1] [--start 0] [--end 0]
Frames: renders/ep03_sheep/frames[_draft]/f_00000.jpg, plus screen.json (where Daisy, the barn and
the nest are on screen, for the handwritten notes). Frames already on disk are skipped.

Story (pinned to words, see pipeline/ep03_timeline.py): Daisy wanders off from the barn painting a
gold trail, comes home on "Yes!" (her whole trail lights up), then a herd of 40 sheep sets off,
then the camera rises to the chickens' nest in the sky as 12 chickens fly a 3D walk, then a wide
shot of both, and back down to Joe by the barn.
"""
import argparse, json, math, sys, time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "pipeline"))
import scene as S
from common import FPS, N, ROOT
from ep03_timeline import Timeline

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

tl = Timeline(ROOT / "episodes" / "ep03_sheep.py")
out = tl.dir / ("frames" if args.scale == 100 and args.every == 1 else "frames_draft"); out.mkdir(parents=True, exist_ok=True)
end = args.end or tl.nf
hx = hy = N // 2
NEST = (hx + 14, hy - 16, 60.0)                # the chickens' home: a nest on a cloud, off beyond the barn

# ---------------- colours ----------------
def hsv2rgb(h, s, v):
    """Vectorised HSV -> sRGB, all arrays."""
    i = np.floor(h * 6).astype(int) % 6; f = h * 6 - np.floor(h * 6)
    p, q, t_ = v * (1 - s), v * (1 - f * s), v * (1 - (1 - f) * s)
    r = np.choose(i, [v, q, p, p, t_, v]); g = np.choose(i, [t_, v, v, q, p, p]); b = np.choose(i, [p, p, t_, v, v, q])
    return np.stack([r, g, b], -1)
def to_lin(c): return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
GOLD = 0.12                                                     # Daisy
PALETTE = np.array([0.07, 0.02, 0.95, 0.88, 0.80, 0.74, 0.66, 0.58, 0.52, 0.98, 0.16])   # no greens

# ---------------- trail canvas: one image, each pixel a square of the field ----------------
SZ = 1024; X0, Y0 = hx - SZ // 2, hy - SZ // 2
last = np.full((SZ, SZ), -1, np.int64)        # step when last walked on
owner = np.full((SZ, SZ), -1, np.int64)       # -1 nobody, 0 Daisy, 1.. herd sheep
daisy_order = np.full((SZ, SZ), -1, np.int64) # Daisy's step there (for the light sweep on "Yes!")
BARN = (hx - 1, hx + 1, hy - 5, hy - 2)       # no trail painted under the barn
def paint(path, k, a, b, order=None):
    seg = path[a:b + 1] + (hx - X0, hy - Y0)
    last[seg[:, 1], seg[:, 0]] = np.arange(a, a + len(seg)); owner[seg[:, 1], seg[:, 0]] = k
    if order is not None: order[seg[:, 1], seg[:, 0]] = np.arange(a, a + len(seg))

def canvas(f, tt, d_step, h_step):
    ys, xs = np.nonzero(owner >= 0)
    gx, gy = xs + X0, ys + Y0
    keep = ~((gx >= BARN[0]) & (gx <= BARN[1]) & (gy >= BARN[2]) & (gy <= BARN[3]))
    ys, xs = ys[keep], xs[keep]
    own = owner[ys, xs]; age = np.where(own == 0, d_step, h_step) - last[ys, xs]
    fade = np.where(own == 0, max(25.0, d_step * 0.12), max(25.0, h_step * 0.12))
    fresh = np.exp(-age / fade)
    hue = np.where(own == 0, GOLD, PALETTE[(own - 1) % len(PALETTE)])
    sat = 0.38 + 0.52 * fresh; val = 0.86 + 0.14 * fresh
    if own.size and tt >= tl.t_yes - 0.05:
        # "Yes!": a wave of light runs along Daisy's whole path, start to finish
        front = tl.ep.DAISY["home_step"] * min(1.0, (tt - tl.t_yes) / 0.9)
        o = daisy_order[ys, xs]
        glow = (own == 0) & (o >= 0) & (o <= front) & (o > front - 600)
        sat = np.where(glow, 0.25, sat); val = np.where(glow, 1.0, val)
        if tt > tl.t_herd: sat = np.where(own == 0, 0.3, sat)    # her trail rests as soft gold
    img = np.zeros((SZ, SZ, 4), np.float32)
    img[ys, xs, :3] = hsv2rgb(hue, sat, val); img[ys, xs, 3] = 1.0
    return img

# ---------------- scene ----------------
sc = S.Scene("farm", scale=args.scale, character="sheep")
sc.add_barn(hx, hy - 2, facing=-math.pi / 2)
sc.add_nest(*NEST)
sc.set_sky((120, 182, 242))
joe = sc.add_character("joe")
JOE = (hx + 2.2, hy - 1.2)
ANGS = [math.pi / 2, 0, -math.pi / 2, math.pi]
def smooth(u): u = min(1.0, max(0.0, u)); return u * u * (3 - 2 * u)

def to_screen(gx, gy, z=0.0):
    from bpy_extras.object_utils import world_to_camera_view
    from mathutils import Vector
    v = world_to_camera_view(sc.sc, sc.cam, Vector((gx, -gy, z)))
    return [round(v.x * S.W, 1), round((1 - v.y) * S.H, 1), round(v.z, 2)]
screen_path = out / "screen.json"
SCREEN = json.loads(screen_path.read_text()) if screen_path.exists() else {}

# camera state (smoothed)
cam = dict(cx=hx + 0.5, cy=hy - 0.5, s=95.0, pitch=54.0, tz=0.0)
d_done = h_done = 0
t_start = time.time(); rendered = 0
for f in range(end):
    tt = f / FPS
    d_step, h_step, c_step = int(tl.daisy_step[f]), int(tl.herd_step[f]), int(tl.flock_step[f])
    if d_step > d_done: paint(tl.daisy, 0, d_done, d_step, daisy_order); d_done = d_step
    if h_step > h_done:
        for k, p in enumerate(tl.herd):
            stop = tl.herd_home[k] if tl.herd_home[k] is not None else 10 ** 9      # home: she stops
            a, b = min(h_done, stop), min(h_step, stop)
            if b > a: paint(p, k + 1, a, b)
        h_done = h_step
    # ---- where the camera wants to be
    ys, xs = np.nonzero(owner >= 0)
    gx0, gx1 = (xs.min() + X0, xs.max() + X0) if xs.size else (hx, hx)
    gy0, gy1 = (ys.min() + Y0, ys.max() + Y0) if ys.size else (hy, hy)
    gx0, gx1 = min(gx0, hx - 3), max(gx1, hx + 4); gy0, gy1 = min(gy0, hy - 7), max(gy1, hy + 1)
    fit = lambda w, h: min(110.0, 900 / (max(w, h * 0.85) + 8))
    beads = []
    if tt >= tl.t_fly:
        for k, p in enumerate(tl.flock):
            stop = tl.flock_home[k] if tl.flock_home[k] is not None else 10 ** 9
            beads.append(np.unique(p[:min(c_step, stop) + 1], axis=0))
    if tt < tl.t_chicken:                                      # Daisy, then the herd, on the field
        tgt = dict(cx=(gx0 + gx1 + 1) / 2, cy=(gy0 + gy1 + 1) / 2, s=fit(gx1 - gx0, gy1 - gy0), pitch=54.0, tz=0.0)
        if tt < 4.0: tgt["s"] = max(tgt["s"], 80.0)           # stay close while Joe introduces her
    elif tt < tl.t_quote:                                      # up to the nest in the sky
        allb = np.vstack(beads) if beads else np.zeros((1, 3))
        bx0, by0, bz0 = allb.min(0); bx1, by1, bz1 = allb.max(0)
        ext = max(bx1 - bx0, by1 - by0, (bz1 - bz0) * 1.3) + 14
        tgt = dict(cx=NEST[0] + 0.5 + (bx0 + bx1) / 2, cy=NEST[1] + 0.5 + (by0 + by1) / 2, s=min(45.0, 1000 / ext),
                   pitch=10.0, tz=NEST[2] + (bz0 + bz1) / 2)
    elif tt < tl.t_next:                                       # wide: the field and the sky together
        # pull back from the chickens: their tangle in the sky and the herd's field below, together
        allb = np.vstack(beads) if beads else np.zeros((1, 3))
        bx0, by0, bz0 = allb.min(0); bx1, by1, bz1 = allb.max(0)
        ext = max(bx1 - bx0, by1 - by0, (bz1 - bz0) * 1.3) + 14
        tgt = dict(cx=NEST[0] + 0.5 + (bx0 + bx1) / 2, cy=NEST[1] + 0.5 + (by0 + by1) / 2 + 20,
                   s=min(45.0, 1000 / ext) * 0.8, pitch=20.0, tz=NEST[2] * 0.55)
    else:                                                      # back down to Joe by the barn
        tgt = dict(cx=JOE[0] - 0.6, cy=JOE[1] - 0.4, s=125.0, pitch=42.0, tz=0.5)   # Joe by his barn
    k_ = 0.12 if tt < 1.0 else 0.06
    cam["s"] *= (tgt["s"] / cam["s"]) ** k_
    for key in ("cx", "cy", "pitch", "tz"): cam[key] += (tgt[key] - cam[key]) * k_
    if f < args.start or f % args.every: continue
    path = out / f"f_{f:05d}.jpg"
    if path.exists() and str(f) in SCREEN: continue
    # ---- the picture
    sc.set_trail_image(canvas(f, tt, d_step, h_step), X0, Y0)
    grid = np.zeros((N, N), np.uint8)
    sc.set_tufts(grid, cam["cx"], cam["cy"], cam["s"] if cam["pitch"] > 45 else 1.0)
    sc.set_floor(cam["s"] if cam["pitch"] > 45 else 5.0)
    # Daisy: walking until she's home, then into the barn
    if d_step < tl.ep.DAISY["home_step"] or tt < tl.t_yes + 0.5:
        x, y = tl.daisy[d_step] + (hx, hy); nxt = tl.daisy[min(d_step + 1, len(tl.daisy) - 1)] - tl.daisy[d_step]
        hd = math.atan2(-nxt[1], nxt[0]) if nxt.any() else math.pi / 2
        walk = (tt * FPS / 14) % 1 if d_step <= 14 else 0.0
        sc.set_walker(x + 0.5, y + 0.5, 0.03, hd, cam["s"], walk)
    else:
        sc.set_walker(hx + 0.5, hy - 3.5, -3.0, 0.0, cam["s"])            # inside the barn
    sc.set_character(joe, JOE[0], JOE[1], 0.0, math.radians(200), max(cam["s"], 17.0))
    # the herd still out walking, as dots
    if tl.t_herd <= tt:
        dots = [p[h_step] + (hx, hy) for k, p in enumerate(tl.herd) if tl.herd_home[k] is None or tl.herd_home[k] > h_step]
        dots = np.array(dots) if dots else np.zeros((0, 2))
    else:
        dots = np.zeros((0, 2))
    # the chickens: beads where they've flown, white dots where they are now
    if beads and tt < tl.t_next:
        pts, cols, heads = [], [], []
        for k, b in enumerate(beads):
            p = tl.flock[k]; now = p[min(c_step, tl.flock_home[k] or 10 ** 9)]
            pts.append(b + (NEST[0], NEST[1], NEST[2])); hue = PALETTE[k % len(PALETTE)]
            cols.append(np.tile(to_lin(hsv2rgb(np.array([hue]), np.array([0.75]), np.array([1.0])))[0], (len(b), 1)))
            if not (tl.flock_home[k] is not None and tl.flock_home[k] <= c_step): heads.append(now + (NEST[0], NEST[1], NEST[2]))
        pts = np.vstack(pts); sc.set_beads(pts[:, :3], np.vstack(cols), float(min(0.3, max(0.12, 4.0 / cam["s"]))))
        if heads:
            hh = np.array(heads); dots = np.vstack([np.column_stack([dots, np.full(len(dots), 0.3)]) if len(dots) else np.zeros((0, 3)),
                                                    hh[:, :3].astype(float)])
    else:
        sc.set_beads(np.zeros((0, 3)), np.zeros((0, 3)))
    if len(dots) and dots.shape[1] == 2: dots = np.column_stack([dots, np.full(len(dots), 0.3)])
    sc.set_dots(dots[:, 0] if len(dots) else [], dots[:, 1] if len(dots) else [], cam["s"], zs=dots[:, 2] if len(dots) else [])
    # the nest glows each time a chicken gets home
    recent = [h for h in tl.flock_home if h is not None and 0 <= c_step - h < 60 and tt >= tl.t_fly]
    sc.nest_glow.data.energy = 400.0 if recent else 0.0
    yaw = -12 + 24 * tt / tl.duration + (25 * smooth((tt - tl.t_chicken) / 3) * (1 - smooth((tt - tl.t_next) / 2)))
    sc.set_camera(cam["cx"], cam["cy"], cam["s"], yaw, cam["pitch"], cam["tz"])
    import bpy; bpy.context.view_layer.update()
    dx, dy = (tl.daisy[d_step] + (hx, hy)) if d_step < tl.ep.DAISY["home_step"] else (hx, hy)
    SCREEN[str(f)] = dict(daisy=to_screen(dx + 0.5, dy + 0.5, 0.4), barn=to_screen(hx + 0.5, hy - 2.0, 1.6),
                          home=to_screen(hx + 0.5, hy + 0.5, 0.0), nest=to_screen(NEST[0] + 0.5, NEST[1] + 0.5, NEST[2]),
                          joe=to_screen(JOE[0], JOE[1], 1.2))
    sc.render(path)
    if args.pause: time.sleep(args.pause)            # breathing room for the chip (and the fan)
    rendered += 1
    if rendered % 10 == 0: screen_path.write_text(json.dumps(SCREEN))
    if rendered % 30 == 0:
        el = time.time() - t_start
        print(f"frame {f}/{tl.nf}  {el / rendered:.2f}s/frame  ~{len(range(f + 1, end, args.every)) * el / rendered / 60:.0f} min left", flush=True)
screen_path.write_text(json.dumps(SCREEN))
print(f"done: {rendered} frames in {(time.time() - t_start) / 60:.1f} min -> {out}", flush=True)
