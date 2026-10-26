"""Stills for Experiment 8's look (what grows if you plant it?), from the side by Joe, in the yard
with the farm backdrop (Kenney trees).

Usage: blender -b -P blender/garden_still.py -- --shot mustard|apple|tyre|winter [--scale 50]
  mustard  the mustard grown, chest-high to Joe, a measuring stick beside it
  apple    the apple tree grown (green apples), Joe holding the red apple he planted the seeds of
  tyre     two years on: Joe in his deck chair by the half-buried tyre, weeds round it
  winter   the same, mid time-lapse: snow on the ground, evening sky
"""
import argparse, math, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "pipeline"))
import scene as S
import scenery as SC
import garden_props as GP
from common import N, ROOT

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--shot", default="mustard", choices=["mustard", "apple", "tyre", "winter"])
ap.add_argument("--scale", type=int, default=50)
args = ap.parse_args(argv)
S.gentle()
import bpy

c = N // 2
sc = S.Scene("farm", scale=args.scale)
SC.add_backdrop(sc, c, c - 3, yard=(c - 16, c - 22, c + 14, c + 8), use_kenney="detailed"); SC.add_silo(sc, c - 17, c - 8)
sc.add_barn(c - 13, c - 3, facing=-math.pi / 3)
GP.add_bed(c - 3, c - 1, 8, 3)
grid = np.zeros((N, N), np.uint8); grid[c - 1:c + 2, c - 3:c + 5] = 1           # no grass tufts on the bed
JOE = (c + 0.5, c + 3.0)
if args.shot == "mustard":
    m = GP.add_mustard(c - 1, c); m.scale = (1.0,) * 3
    GP.add_stick(c - 0.1, c + 0.4)
    sc.set_walker(*JOE, 0.0, math.radians(200), 160.0, tool=False)
    cam = (c - 0.3, c + 1.4, 330.0, 8.0, 0.7, -15.0)
elif args.shot == "apple":
    t = GP.add_apple_tree(c + 1, c - 0.5); t["root"].scale = (1.0,) * 3
    sc.set_walker(*JOE, 0.0, math.radians(210), 120.0, tool=False, arms={"right": (-1.7, 0.2), "left": (0.1, 0.05)})
    bpy.context.view_layer.update(); hw = sc.hand_position("right")
    GP.add_apple(hw[0], hw[1], hw[2] + 0.08)
    cam = (c + 1.0, c + 0.6, 175.0, 4.0, 1.7, -12.0)
else:
    GP.add_tyre(c + 1, c)
    GP.add_deckchair(c + 2.8, c + 2.2, rot=math.radians(150))
    sc.set_walker(c + 3.3, c + 2.7, 0.18, math.radians(150), 150.0, tool=False, fall=-0.35)   # lounging back in the chair
    if args.shot == "tyre":
        r = np.random.default_rng(3)
        for k in range(14):                                      # weeds round the tyre, from seeds already in the soil
            a, d = r.uniform(0, 2 * math.pi), r.uniform(0.5, 1.4)
            SC.kenney(["grass_large", "plant_bushSmall", "flower_yellowB", "grass_leafsLarge"][k % 4],
                      c + 1 + d * math.cos(a), c + d * math.sin(a), rot=r.uniform(0, 6.3), scale=r.uniform(1.6, 2.4))
    else:                                                        # winter: snow, an evening sky
        bpy.ops.mesh.primitive_plane_add(size=60, location=(c + 0.5, -(c + 0.5), 0.12)); snow = bpy.context.object
        snow.data.materials.append(S._material("Snow", S.lin((246, 248, 252)), rough=0.8)[0])
        SC.sky_gradient(sc, horizon=(250, 190, 150), top=(70, 90, 160))
    cam = (c + 2.0, c + 1.4, 270.0, 10.0, 0.5, -18.0)
    if args.shot == "winter": grid[:] = 1                     # no grass poking through the snow
sc.set_tufts(grid, cam[0], cam[1], cam[2]); sc.set_floor(cam[2])
sc.set_camera(cam[0], cam[1], cam[2], cam[5], cam[3], cam[4])
out = ROOT / "renders" / "ep08_plant" / f"still_{args.shot}.png"
out.parent.mkdir(parents=True, exist_ok=True)
sc.render(out, "PNG"); print("saved", out, flush=True)
