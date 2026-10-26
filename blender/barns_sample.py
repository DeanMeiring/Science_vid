"""Moving sample for Experiment 6's look: Daisy trots up to barn 1, Joe swings barn 3 open on a goat,
then the camera rises over the barns to the field behind, where the 1,000 games pile up as two bars
of little tractors (one per win): slowly at first, then racing to stay 339, switch 661.

Usage: blender -b -P blender/barns_sample.py -- [--seconds 10] [--scale 50] [--pause 1.0]
Frames: renders/ep06_barns/sample_frames/f_00000.jpg, plus screen.json for the notes
(prototypes/barns_sample_compose.py makes sample.mp4). Frames already on disk are skipped.
"""
import argparse, json, math, sys, time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "pipeline"))
import scene as S
import barns_props as BP
import barns as BG
from common import FPS, N, ROOT

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--seconds", type=float, default=10)
ap.add_argument("--scale", type=int, default=50)
ap.add_argument("--pause", type=float, default=1.0, help="rest after each frame (keeps the laptop cool)")
args = ap.parse_args(argv)
S.gentle()
import bpy

OUT = ROOT / "renders" / "ep06_barns" / "sample_frames"; OUT.mkdir(parents=True, exist_ok=True)
NF = int(args.seconds * FPS); c = N // 2
def smooth(u): u = min(1.0, max(0.0, u)); return u * u * (3 - 2 * u)
def lerp(a, b, u): return a + (b - a) * u

sc = S.Scene("farm", scale=args.scale, character="sheep")
sc.set_sky((120, 182, 242))
joe = sc.add_character("joe")
BX, BY = [c - 4, c, c + 4], c - 3
barns = [BP.add_game_barn(sc, bx, BY) for bx in BX]
BP.add_tractor(sc, BX[0], BY - 1.3, facing=-math.pi / 2)
BP.add_goat(sc, BX[1], BY - 1.2, facing=-math.pi / 2)
BP.add_goat(sc, BX[2], BY - 1.2, facing=-math.pi / 2)

# the games, and where each win's tractor parks: two lots behind the barns, 10 wide, rows going back
g = BG.games(1, 1000)
stay_win = g["pick"] == g["prize"]
LOT = {"stay": c - 4, "switch": c + 4}; ROW0 = BY - 6; COLS = 10
slots, count = [], {"stay": 0, "switch": 0}
for k in range(len(stay_win)):
    side = "stay" if stay_win[k] else "switch"; i = count[side]; count[side] += 1
    slots.append((side, LOT[side] - 2.5 + (i % COLS) * 0.55, ROW0 - (i // COLS) * 0.7))
src = BP.tractor_mesh(sc)
tokens = bpy.data.objects.new("Tokens", S._points_mesh("Tokens", [], {})); sc.sc.collection.objects.link(tokens)
tokens.modifiers.new("Inst", "NODES").node_group = S._instancer_nodes("Tokens", src)

# games played by each frame: none until 5.6 s, a few slowly, then racing to 1,000 by 9.4 s
t = np.arange(NF) / FPS
played = np.where(t < 5.6, 0, np.where(t < 7.0, (t - 5.6) / 1.4 * 6,
                  np.expm1(np.log1p(6) + (np.log1p(1000) - np.log1p(6)) * np.clip((t - 7.0) / 2.4, 0, 1))))
played = np.minimum(played, 1000)

screen_path = OUT / "screen.json"
SCREEN = json.loads(screen_path.read_text()) if screen_path.exists() else {}
def to_screen(gx, gy, z=0.0):
    from bpy_extras.object_utils import world_to_camera_view
    from mathutils import Vector
    v = world_to_camera_view(sc.sc, sc.cam, Vector((gx, -gy, z)))
    return [round(v.x * S.W, 1), round((1 - v.y) * S.H, 1)]

t0 = time.time(); rendered = 0
for f in range(NF):
    tt = f / FPS
    path = OUT / f"f_{f:05d}.jpg"
    if path.exists() and str(f) in SCREEN: continue
    # Daisy trots up to barn 1; Joe opens barn 3
    u = smooth(tt / 1.6); dy = lerp(BY + 6.0, BY + 2.0, u)
    sc.set_walker(BX[0] + 0.5, dy, 0.02, math.pi / 2, 90.0, walk=(tt * 2.2) % 1 if u < 1 else 0.0)
    sc.set_character(joe, BX[2] + 1.2, BY + 2.4, 0.02, math.radians(150 if tt < 1.8 else 175), 90.0)
    BP.open_doors(barns[2], smooth((tt - 1.8) / 0.8))
    # the tractors parked so far (the newest pops in)
    n = int(played[f]); p = played[f]
    if n:
        xy = np.array([(sx, sy) for _, sx, sy in slots[:n]])
        grow = np.clip(p - np.arange(n), 0, 1) if p < 10 else np.ones(n)      # while slow, the newest grows in
        sc_ = 0.42 * np.clip(grow, 0.05, 1)
        old = tokens.data
        tokens.data = S._points_mesh("Tokens", np.stack([xy[:, 0] + 0.5, -(xy[:, 1] + 0.5), np.zeros(n)], -1),
                                     dict(scale=np.stack([sc_] * 3, -1), rot=np.tile([0, 0, math.pi / 2], (n, 1))))
        bpy.data.meshes.remove(old)
    # camera: the game, then rising over the barns to the lots behind
    v = smooth((tt - 4.6) / 1.4)
    cx = c + 0.5; cy = lerp(BY + 1.2, ROW0 - 22.0, v); s = 82.0 * (36.0 / 82.0) ** v; pitch = lerp(30.0, 50.0, v)
    sc.set_tufts(np.zeros((N, N), np.uint8), cx, cy + 3, s); sc.set_floor(s)
    sc.set_camera(cx, cy, s, 0, pitch, tz=lerp(0.9, 0.0, v))
    bpy.context.view_layer.update()
    won = {"stay": int(stay_win[:n].sum()), "switch": int(n - stay_win[:n].sum())}
    tops = {k: to_screen(LOT[k] + 0.5, ROW0 - ((won[k] - 1) // COLS + 1) * 0.7 + 0.2 if won[k] else ROW0 + 0.5, 0.4) for k in LOT}
    SCREEN[str(f)] = dict(played=n, won=won, tops=tops, barns=[to_screen(bx + 0.5, BY + 0.5, 4.0) for bx in BX],
                          daisy=to_screen(BX[0] + 0.5, dy, 1.0), goat=to_screen(BX[2] + 0.5, BY - 0.7, 1.4),
                          joe=to_screen(BX[2] + 1.2, BY + 2.4, 1.4), view=v)
    sc.render(path); rendered += 1
    if args.pause: time.sleep(args.pause)
    if rendered % 10 == 0:
        screen_path.write_text(json.dumps(SCREEN))
        print(f"frame {f}/{NF} games {n}  {(time.time() - t0) / rendered:.2f}s/frame", flush=True)
screen_path.write_text(json.dumps(SCREEN))
print("done", NF, "frames", flush=True)
