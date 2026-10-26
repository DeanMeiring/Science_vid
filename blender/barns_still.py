"""Stills for Experiment 6's look (three barns).

Usage: blender -b -P blender/barns_still.py -- --shot game|results [--scale 50] [--out file.png]
  game     three barns in a row, Daisy in front of barn 1, Joe by barn 3 with its doors open on a goat
  results  the 1,000 games as two "bar charts" of little tractors (one per win): stay 339, switch 661
Also writes <out>.json with screen positions for the notes.
"""
import argparse, json, math, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "pipeline"))
import scene as S
import barns_props as BP
import barns as BG
from common import N, ROOT

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--shot", default="game", choices=["game", "results"])
ap.add_argument("--scale", type=int, default=50)
ap.add_argument("--out", default="")
args = ap.parse_args(argv)
S.gentle()
import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

c = N // 2
sc = S.Scene("farm", scale=args.scale, character="sheep")             # Daisy is the main walker
sc.set_sky((120, 182, 242))
joe = sc.add_character("joe")
BX = [c - 4, c, c + 4]                                                 # the barns' door squares, left to right
BY = c - 3
def screen(gx, gy, z=0.0):
    v = world_to_camera_view(bpy.context.scene, sc.cam, Vector((gx, -gy, z)))
    return [round(v.x * 1080), round((1 - v.y) * 1920)]
info = {}

if args.shot == "game":
    barns = [BP.add_game_barn(sc, bx, BY) for bx in BX]
    BP.open_doors(barns[2], 1.0)
    BP.add_goat(sc, BX[2], BY - 1.2, facing=-math.pi / 2)              # inside barn 3, facing out
    BP.add_goat(sc, BX[1], BY - 1.2, facing=-math.pi / 2)              # (behind the shut doors)
    BP.add_tractor(sc, BX[0], BY - 1.3, facing=-math.pi / 2)           # behind barn 1's shut doors
    sc.set_walker(BX[0] + 0.5, BY + 2.0, 0.02, math.pi / 2, 90.0)      # Daisy in front of barn 1, facing it
    sc.set_character(joe, BX[2] + 1.2, BY + 2.4, 0.02, math.radians(150), 90.0)
    cx, cy, s_px, pitch = c + 0.5, BY + 1.2, 82.0, 30.0
    sc.set_tufts(np.zeros((N, N), np.uint8), cx, cy + 3, s_px); sc.set_floor(s_px)
    sc.set_camera(cx, cy, s_px, 0, pitch, tz=0.9)
    bpy.context.view_layer.update()
    info = dict(barns=[screen(bx + 0.5, BY + 0.5, 4.0) for bx in BX], daisy=screen(BX[0] + 0.5, BY + 2.0, 1.0),
                joe=screen(BX[2] + 1.2, BY + 2.4, 1.4), goat=screen(BX[2] + 0.5, BY - 0.7, 1.4))
else:
    g = BG.games(1, 1000)
    wins = {"stay": int((g["pick"] == g["prize"]).sum()), "switch": int((g["other"] == g["prize"]).sum())}
    src = BP.tractor_mesh(sc)
    pts, cols = [], 10
    lots = {"stay": c - 4, "switch": c + 4}                            # each lot: 10 wide, one row per 10 wins
    for name, x0 in lots.items():
        for k in range(wins[name]):
            pts.append((x0 - 2.5 + (k % cols) * 0.55, c + 2 - (k // cols) * 0.7))
    pts = np.array(pts)
    ob = bpy.data.objects.new("Tokens", S._points_mesh("Tokens", np.stack([pts[:, 0] + 0.5, -(pts[:, 1] + 0.5), np.zeros(len(pts))], -1),
                              dict(scale=np.full((len(pts), 3), 0.42), rot=np.tile([0, 0, math.pi / 2], (len(pts), 1)))))
    sc.sc.collection.objects.link(ob); ob.modifiers.new("Inst", "NODES").node_group = S._instancer_nodes("Tokens", src)
    sc.set_walker(c + 0.5, c + 4.5, 0.02, math.pi / 2, 60.0)            # Daisy and Joe watching in front
    sc.set_character(joe, c - 1.0, c + 4.8, 0.02, math.pi / 2, 60.0)
    cx, cy, s_px, pitch = c + 0.5, c - 18.0, 36.0, 48.0
    sc.set_tufts(np.zeros((N, N), np.uint8), cx, cy, s_px); sc.set_floor(s_px)
    sc.set_camera(cx, cy, s_px, 0, pitch)
    bpy.context.view_layer.update()
    rows = {k: (v + cols - 1) // cols for k, v in wins.items()}
    info = dict(wins=wins, top={k: screen(x0 + 0.5, c + 2 - rows[k] * 0.7 - 0.6, 0.5) for k, x0 in lots.items()},
                base={k: screen(x0 + 0.5, c + 3.2, 0.0) for k, x0 in lots.items()})

out = Path(args.out or ROOT / "renders" / "ep06_barns" / f"still_{args.shot}.png")
out.parent.mkdir(parents=True, exist_ok=True)
sc.render(out, "PNG")
out.with_suffix(".json").write_text(json.dumps(info))
print("saved", out, info, flush=True)
