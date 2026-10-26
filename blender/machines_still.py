"""A still of Experiment 7's machines side by side in the yard (a look check): the wheelbarrow tipping,
the tractor with its trailer tipping, and the combine harvester.

Usage: blender -b -P blender/machines_still.py -- [--scale 50]
"""
import argparse, math, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "pipeline"))
import scene as S
import hay_props as HP
import barns_props as BP
import machines_props as MP
import scenery as SC
from common import N, ROOT

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser(); ap.add_argument("--scale", type=int, default=50); args = ap.parse_args(argv)
S.gentle()
import bpy
c = N // 2
sc = S.Scene("farm", scale=args.scale)
SC.add_backdrop(sc, c, c - 3, yard=(c - 16, c - 22, c + 14, c + 8), use_kenney=True)
HP.add_floor(sc, c - 8, c - 4, 16, 10)
wb = MP.add_wheelbarrow(c - 5, c + 2, facing=math.radians(-60)); wb["tray"].rotation_euler.y = -0.6
BP.add_tractor(sc, c - 0.5, c - 1, facing=math.radians(-10))
tr = MP.add_trailer(c - 3.3, c - 0.5, facing=math.radians(-10)); tr["bed"].rotation_euler.y = 0.5
cb = MP.add_combine(c + 6, c - 1, facing=math.radians(200))
sc.set_walker(c - 6.5, c + 3.5, HP.FLOOR_Z, math.radians(20), 120.0, tool=False, arms={"right": (-1.2, 0.1), "left": (-1.2, 0.1)})
grid = np.zeros((N, N), np.uint8); grid[c - 4:c + 6, c - 8:c + 8] = 1
sc.set_tufts(grid, c, c + 1, 60.0); sc.set_floor(60.0)
sc.set_camera(c + 0.5, c + 1.0, 62.0, -10, 22.0, 1.2)
out = ROOT / "renders" / "ep07_pi" / "machines.png"
sc.render(out, "PNG"); print("saved", out, flush=True)
