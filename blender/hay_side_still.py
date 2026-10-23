"""Stills for Experiment 7 seen from the side (Dean, 23 Oct): the straws are counted on the planks,
then raked onto a haystack that grows into a giant hay mountain.

Usage: blender -b -P blender/hay_side_still.py -- --shot first|heap|mountain [--scale 50]
  first     low camera by Joe: one straw in the air, a few on the planks (crossers glow gold)
  heap      10,000 straws: the haystack behind Joe as tall as the barn's door
  mountain  100,000: a hay mountain towering over the barn, camera pulled back
"""
import argparse, json, math, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "pipeline"))
import scene as S
import hay_props as HP
import hay as HY
import scenery as SC
from common import N, ROOT

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--shot", default="first", choices=["first", "heap", "mountain"])
ap.add_argument("--scale", type=int, default=50)
ap.add_argument("--kenney", action="store_true", help="Kenney's trees, bushes and flowers round the yard")
args = ap.parse_args(argv)
S.gentle()
import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

c = N // 2
sc = S.Scene("farm", scale=args.scale)
SC.add_backdrop(sc, c, c - 3, yard=(c - 16, c - 22, c + 14, c + 8), use_kenney=args.kenney)   # hills, trees, fence, clouds, sky
SC.add_silo(sc, c - 17, c - 8)
daisy = sc.add_character("sheep")
HP.add_floor(sc, c - 8, c - 4, 16, 10)                          # the plank floor, out in the yard
sc.add_barn(c - 13, c - 3, facing=-math.pi / 3)                 # the barn to the left, for scale
HP.add_bale(sc, c + 2, c + 2, facing=0.3)
HP.add_bucket(sc, c - 2.5, c + 4); HP.add_pitchfork(sc, c + 3.6, c + 3.4, lean=0.25, facing=0.6)
n = {"first": 6, "heap": 10000, "mountain": 100000}[args.shot]
rad, hgt = HP.heap_size(n)
heap = HP.add_haystack(sc, c + 1, c - 9, rad, hgt) if n > 50 else None
d = HY.drop(1, 100000)
straws = HP.Straws(sc)
k0 = max(0, n - 40)                                              # only the latest straws lie on the planks
x, y, ang, cross = HY.spread(d, k0, n, c - 3, c + 1, 7, 4)
z = np.full(len(x), HP.FLOOR_Z); tilt = np.zeros(len(x)); spin = np.zeros(len(x))
if args.shot == "first":                                         # one more is still flying
    x = np.r_[x, c + 0.9]; y = np.r_[y, c + 2.6]; z = np.r_[z, 1.3]; ang = np.r_[ang, 0.6]; cross = np.r_[cross, False]
    tilt = np.r_[tilt, 0.8]; spin = np.r_[spin, 0.5]
GOLD, PALE = np.array(S.lin((255, 196, 52)))[:3], np.array(S.lin((250, 240, 205)))[:3]
tone = 0.86 + 0.14 * np.random.default_rng(3).random(len(x))[:, None]
straws.set(x, y, z, ang, np.where(cross[:, None], GOLD, PALE) * tone, np.where(cross, 0.9, 0.3), tilt, spin)
sc.set_walker(c + 0.5, c + 2.5, HP.FLOOR_Z, math.radians(200), 100.0)
sc.set_character(daisy, c - 2.0, c + 2.2, HP.FLOOR_Z, math.radians(-30), 100.0)
cam = {"first": (c + 0.4, c + 2.6, 260.0, 12.0, 0.75, -20.0), "heap": (c + 0.5, c - 3.0, 52.0, 16.0, 2.2, -14.0),
       "mountain": (c + 0.5, c + 1.0, 120.0, 6.0, 2.6, -12.0)}[args.shot]     # mountain: eye level behind Joe
grid = np.zeros((N, N), np.uint8); grid[c - 4:c + 6, c - 8:c + 8] = 1         # no grass tufts on the planks
sc.set_tufts(grid, cam[0], cam[1], cam[2]); sc.set_floor(cam[2])
sc.set_camera(cam[0], cam[1], cam[2], cam[5], cam[3], cam[4])
out = ROOT / "renders" / "ep07_pi" / f"side_{args.shot}{'_kenney' if args.kenney else ''}.png"
sc.render(out, "PNG")
print("saved", out, f"straws {n:,}, heap radius {rad:.1f}, height {hgt:.1f}", flush=True)
