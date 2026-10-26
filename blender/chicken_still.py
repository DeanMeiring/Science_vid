"""Sample stills for Experiment 10's look (the chicken, three barns, footprints).

Usage: blender -b -P blender/chicken_still.py -- [--scale 50]
Writes renders/ep10_chicken/look/look_{a,b,c,d}.jpg: 10 hops up close, 1,000 hops, 100,000 hops, four barns.
"""
import argparse, math, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "pipeline"))
import scene as S
from common import N, ROOT
import chaos as CH

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser(); ap.add_argument("--scale", type=int, default=50); args = ap.parse_args(argv)
S.gentle()
import bpy

out = ROOT / "renders" / "ep10_chicken" / "look"; out.mkdir(parents=True, exist_ok=True)
c = N // 2
L = 24.0                                   # the triangle's side, in squares
RES = 8                                    # footprint pixels per square
PAD = 3                                    # squares of canvas round the triangle

def grid(p):
    """Sim units (y up) -> grid squares (y down), Joe's field centre c."""
    return c + p[..., 0] * L, c - p[..., 1] * L

def footprints(p, n_recent=0):
    """One image: every footprint so far, gold; the latest few brighter."""
    S_ = int((L + 2 * PAD) * RES)
    gx, gy = grid(p)
    px = ((gx - (c - PAD)) * RES).astype(int); py = ((gy - (c - L - PAD)) * RES).astype(int)
    ok = (px >= 0) & (px < S_) & (py >= 0) & (py < S_)
    img = np.zeros((S_, S_, 4), np.float32)
    img[py[ok], px[ok]] = (0.98, 0.78, 0.28, 1.0)
    if n_recent:
        k = slice(-n_recent, None)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                xx, yy = np.clip(px[k] + dx, 0, S_ - 1), np.clip(py[k] + dy, 0, S_ - 1)
                img[yy, xx] = (1.0, 0.95, 0.6, 1.0)
    return img, c - PAD, c - L - PAD

sc = S.Scene("farm", scale=args.scale, character="chicken")
sc.set_sky((120, 182, 242))
joe = sc.add_character("joe")
centroid = CH.TRI.mean(0)
def place_barns(barns):
    objs = []
    cx, cy = grid(centroid)
    for b in barns:
        gx, gy = grid(b)
        face = math.atan2(-(cy - gy), cx - gx)            # world angle (y flipped) towards the middle
        bx, by = gx - 1.2 * math.cos(face), gy + 1.2 * math.sin(face)
        objs.append(sc.add_barn(bx - 0.5, by - 0.5, facing=face))
    return objs
barns = place_barns(CH.TRI)
sc.set_tufts(np.zeros((N, N), np.uint8), c + L / 2, c - L / 3, 40.0)

def shot(name, p, chicken_at, s_px, cx, cy, recent=0, joe_at=None):
    img, x0, y0 = footprints(p, recent)
    sc.set_trail_image(img, x0, y0, z=0.03, gap=0.0, glow=0.3, cell=1 / RES)
    gx, gy = grid(np.array(chicken_at))
    sc.set_walker(gx, gy, 0.03, math.radians(30), s_px)
    jx, jy = joe_at if joe_at else (grid(CH.TRI[0])[0] + 3.0, grid(CH.TRI[0])[1] + 2.5)
    sc.set_character(joe, jx, jy, 0.02, math.radians(40), s_px)
    sc.set_floor(s_px)
    sc.set_camera(cx, cy, s_px, -8, 54)
    bpy.context.view_layer.update()
    sc.render(out / f"look_{name}.jpg"); print("wrote", name, flush=True)

p, _ = CH.hops(CH.TRI, 100_000)
cx, cy = grid(centroid)
gx, gy = grid(p[10])
shot("a", p[:11], p[10], 70.0, (gx + cx) / 2, (gy + cy) / 2, recent=11)
shot("b", p[:1001], p[1000], 26.0, cx, cy + 1.5, recent=1)
shot("c", p, p[-1], 26.0, cx, cy + 1.5, recent=1)
# four barns: a square, same size
for o in barns:
    for ch in [o] + list(o.children_recursive): ch.hide_render = True
q, _ = CH.hops(CH.SQUARE * np.array([1.0, 0.866]), 100_000, seed=2)
place_barns(CH.SQUARE * np.array([1.0, 0.866]))
shot("d", q, q[-1], 26.0, cx, cy - 1.5, recent=1)
