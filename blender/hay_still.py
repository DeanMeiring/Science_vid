"""Stills for Experiment 7's look (pi from a bale of hay).

Usage: blender -b -P blender/hay_still.py -- --shot close|many|carpet [--scale 50] [--out file.png]
  close    Joe by the bale, the first straws on the planks (one still falling); crossers glow gold
  many     2,000 straws around Joe
  carpet   all 100,000: a golden carpet over the whole floor
Also writes <out>.json with screen positions for the notes.
"""
import argparse, json, math, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "pipeline"))
import scene as S
import hay_props as HP
import hay as HY
from common import N, ROOT

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--shot", default="close", choices=["close", "many", "carpet"])
ap.add_argument("--scale", type=int, default=50)
ap.add_argument("--out", default="")
args = ap.parse_args(argv)
S.gentle()
import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

c = N // 2
sc = S.Scene("farm", scale=args.scale)
sc.set_sky((120, 182, 242))
FX0, FY0, FW, FH = c - 40, c - 30, 80, 60                      # the floor: 80 squares x 60 planks
HP.add_floor(sc, FX0, FY0, FW, FH)
JX, JY = c + 0.5, c + 2.5                                       # Joe, with the bale beside him
HP.add_bale(sc, c + 2, c + 2, facing=0.3)
straws = HP.Straws(sc)
d = HY.drop(1, 100000)
GOLD, PALE = np.array(S.lin((255, 196, 52)))[:3], np.array(S.lin((250, 240, 205)))[:3]
def screen(gx, gy, z=0.0):
    v = world_to_camera_view(bpy.context.scene, sc.cam, Vector((gx, -gy, z)))
    return [round(v.x * 1080), round((1 - v.y) * 1920)]

n, area = {"close": (7, (c - 3, c - 2, 6, 4)), "many": (2000, (c - 8, c - 6, 16, 12)), "carpet": (100000, (FX0, FY0, FW, FH))}[args.shot]
x, y, ang, cross = HY.spread(d, 0, n, *area)
z = np.full(n, HP.FLOOR_Z + 0.017)
tilt = spin = None
if args.shot == "close":                                         # the last one is still falling
    z[-1] = 1.1; tilt = np.zeros(n); tilt[-1] = 0.7; spin = np.zeros(n); spin[-1] = 0.4
rgb = np.where(cross[:, None], GOLD, PALE); glow = np.where(cross, 0.8, 0.15)
straws.set(x, y, z, ang, rgb, glow, tilt, spin)
s_px, pitch, cy = {"close": (150.0, 52.0, c + 0.6), "many": (48.0, 50.0, c), "carpet": (11.0, 58.0, c - 2)}[args.shot]
sc.set_walker(JX, JY, HP.FLOOR_Z, math.radians(110), s_px)
sc.set_tufts(np.ones((N, N), np.uint8), c, cy, s_px); sc.set_floor(s_px)
sc.set_camera(c + 0.5, cy, s_px, -8, pitch)
bpy.context.view_layer.update()
info = dict(n=n, cross=int(cross.sum()), joe=screen(JX, JY, 1.2),
            straws=[screen(x[i], y[i], z[i]) for i in range(min(n, 7))], cross_list=cross[:7].tolist())
out = Path(args.out or ROOT / "renders" / "ep07_pi" / f"still_{args.shot}.png")
out.parent.mkdir(parents=True, exist_ok=True)
sc.render(out, "PNG")
out.with_suffix(".json").write_text(json.dumps(info))
print("saved", out, {k: v for k, v in info.items() if k in ("n", "cross")}, flush=True)
