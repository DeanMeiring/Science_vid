"""One still of Experiment 4: Joe and his helper on the field, at a given round of the record run.

Usage: blender -b -P blender/farmers_still.py -- --round 1178 --look colours [--scale 50] [--out file.png]
  --look blocks   dirt as raised brown blocks, like Experiment 1
  --look colours  flat painted squares in the colour of whoever dug them (Joe gold, helper blue),
                  squares that just grew back flash fresh green
Also writes <out>.json with where the two farmers are on screen (for notes and arrows).
"""
import argparse, colorsys, json, math, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "pipeline"))
import scene as S
import farmers as FM
from common import N, ROOT

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--round", type=int, default=1178)
ap.add_argument("--look", default="colours", choices=["blocks", "colours"])
ap.add_argument("--scale", type=int, default=50)
ap.add_argument("--out", default="")
args = ap.parse_args(argv)
S.gentle()

HELPER = {"Shirt": (70, 140, 230), "Overalls": (70, 120, 64), "HatBand": (40, 90, 200)}
HUES = (0.11, 0.57)                    # Joe gold, helper sky blue
ANGS = [math.pi / 2, 0, -math.pi / 2, math.pi]

# replay the record run up to the round, remembering who dug each square and when it last changed
c = N // 2
ants = [[x + c, y + c, d] for x, y, d in FM.RECORD]
dirt, owner, changed = set(), {}, {}
for r in range(1, args.round + 1):
    for k, a in enumerate(ants):
        x, y, d = a
        if (x, y) in dirt: d = (d - 1) % 4; dirt.discard((x, y))
        else: d = (d + 1) % 4; dirt.add((x, y)); owner[(x, y)] = k
        changed[(x, y)] = r
        a[:] = [x + FM.DX[d], y + FM.DY[d], d]
R = args.round
regrown = [p for p, r in changed.items() if p not in dirt and R - r < 40]
cells = sorted(dirt)
xs = np.array([p[0] for p in cells] + [p[0] for p in regrown]); ys = np.array([p[1] for p in cells] + [p[1] for p in regrown])
nd = len(cells)
age = np.array([R - changed[p] for p in cells] + [R - changed[p] for p in regrown], float)

sc = S.Scene("farm", scale=args.scale)
helper = sc.add_character("joe", recolour=HELPER)

if args.look == "blocks":
    kind = np.r_[np.ones(nd), np.zeros(len(regrown))]
    hz = np.r_[np.full(nd, sc.HB), np.zeros(len(regrown))]
    heat = np.exp(-age / 30.0) * 0.8
    sc.set_cells(xs, ys, hz, heat, kind)
else:
    def srgb2lin(rgb): return np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    paint = np.zeros((len(xs), 3))
    fresh = np.exp(-age / 60.0)
    for i, p in enumerate(cells):
        paint[i] = colorsys.hsv_to_rgb(HUES[owner[p]], 0.45 + 0.5 * fresh[i], 0.88 + 0.12 * fresh[i])
    for j in range(len(regrown)):                       # just grew back: bright young grass, fading to normal
        f_ = fresh[nd + j]; paint[nd + j] = colorsys.hsv_to_rgb(0.24, 0.55 + 0.2 * f_, 0.7 + 0.3 * f_)
    sc.set_cells(xs, ys, np.full(len(xs), 0.03), np.zeros(len(xs)), np.ones(len(xs)), paint=srgb2lin(paint))

grid = np.zeros((N, N), np.uint8)
if nd: grid[ys[:nd], xs[:nd]] = 1
pts = np.array([[a[0], a[1]] for a in ants] + [[x, y] for x, y in cells])
x0, y0 = pts.min(0); x1, y1 = pts.max(0)
cx, cy = (x0 + x1 + 1) / 2, (y0 + y1 + 1) / 2
s_px = min(110.0, 960 / (max(x1 - x0, (y1 - y0) * 0.85) + 3))
sc.set_tufts(grid, cx, cy, s_px); sc.set_floor(s_px)
z = sc.HB if args.look == "blocks" else 0.03
for k, a in enumerate(ants):
    on = z if (a[0], a[1]) in dirt else 0.02
    if k == 0: sc.set_walker(a[0] + 0.5, a[1] + 0.5, on, ANGS[a[2]], s_px)
    else: sc.set_character(helper, a[0] + 0.5, a[1] + 0.5, on, ANGS[a[2]], s_px)
sc.set_camera(cx, cy, s_px, -10)

out = Path(args.out or ROOT / "renders" / "ep04_farmers" / f"still_{args.look}_{R}.png")
out.parent.mkdir(parents=True, exist_ok=True)
sc.render(out, "PNG")
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector
import bpy
def screen(x, y, zz=0.6):
    v = world_to_camera_view(bpy.context.scene, sc.cam, Vector((x + 0.5, -(y + 0.5), zz)))
    return [round(v.x * 1080), round((1 - v.y) * 1920)]
out.with_suffix(".json").write_text(json.dumps(dict(round=R, dirt=nd, joe=screen(*ants[0][:2]), helper=screen(*ants[1][:2]))))
print("saved", out, f"round {R}: {nd} dirt squares, zoom {s_px:.1f}px", flush=True)
