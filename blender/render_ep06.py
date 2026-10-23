"""Render Experiment 6's frames (three barns). Captions, notes and sound come later (pipeline/compose_ep06.py).

Usage: blender -b -P blender/render_ep06.py -- [--scale 100] [--every 1] [--start 0] [--end 0] [--pause 1.0]
Frames: renders/ep06_barns/frames[_draft]/f_00000.jpg, plus screen.json (where the barns, Daisy,
Joe, the bars of tractors and the other experiments' fields are on screen). Frames already on disk
are skipped.

Story (pinned to words, see pipeline/ep06_timeline.py): Daisy trots up to barn 1; Joe opens barn 3
on a goat; the camera rises to the lots behind the barns, where the 1,000 games park one little
tractor per win (stay bar, switch bar); back to the barns, barn 2 opens on the tractor (switching
would have won); 10,000 letters rain down; a wide shot; then the whole farm with every experiment.
Behind the doors: barn 1 a goat, barn 2 the tractor, barn 3 a goat.
"""
import argparse, json, math, sys, time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "pipeline"))
import scene as S
import barns_props as BP
import farm_overview as FO
import crops as CR
from common import FPS, N, ROOT
from ep06_timeline import Timeline

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
import bpy

tl = Timeline(ROOT / "episodes" / "ep06_barns.py")
out = tl.dir / ("frames" if args.scale == 100 and args.every == 1 else "frames_draft"); out.mkdir(parents=True, exist_ok=True)
end = args.end or tl.nf
c = N // 2
def smooth(u): u = min(1.0, max(0.0, u)); return u * u * (3 - 2 * u)
def lerp(a, b, u): return a + (b - a) * u

# ---------------- the barns and the lots ----------------
sc = S.Scene("farm", scale=args.scale, character="sheep")              # Daisy is the main walker
sc.set_sky((120, 182, 242))
joe = sc.add_character("joe")
BX, BY = [c - 3.6, c, c + 3.6], c - 3
barns = [BP.add_game_barn(sc, bx, BY) for bx in BX]
BP.add_goat(sc, BX[0], BY - 1.2, facing=-math.pi / 2)
BP.add_tractor(sc, BX[1], BY - 1.3, facing=-math.pi / 2)
BP.add_goat(sc, BX[2], BY - 1.2, facing=-math.pi / 2)
LOT = {"stay": c - 4, "switch": c + 4}; ROW0 = BY - 6; COLS = 10
slots, count = [], {"stay": 0, "switch": 0}
for k in range(len(tl.stay_win)):
    side = "stay" if tl.stay_win[k] else "switch"; i = count[side]; count[side] += 1
    slots.append((LOT[side] - 2.5 + (i % COLS) * 0.55, ROW0 - (i // COLS) * 0.7))
SLOTS = np.array(slots)
src = BP.tractor_mesh(sc)
tokens = bpy.data.objects.new("Tokens", S._points_mesh("Tokens", [], {})); sc.sc.collection.objects.link(tokens)
tokens.modifiers.new("Inst", "NODES").node_group = S._instancer_nodes("Tokens", src)
JOE = (BX[2] + 1.1, BY + 2.4)
DAISY_FROM, DAISY_AT = (BX[0] + 0.5, BY + 7.5), (BX[0] + 0.5, BY + 2.0)

# ---------------- 10,000 letters (a few hundred envelopes) rain down on "1990" ----------------
rng = np.random.default_rng(6); NL = 260
L_XY = np.stack([rng.uniform(c - 7, c + 8, NL), rng.uniform(BY - 1, BY + 6, NL)], -1)
L_T0 = tl.t_1990 + rng.uniform(0, 2.4, NL); L_SPIN = rng.uniform(-6, 6, (NL, 3)); L_Z0 = rng.uniform(7, 10, NL)
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0)); env = bpy.context.object
env.scale = (0.32, 0.22, 0.012); bpy.ops.object.transform_apply(scale=True)
env.data.materials.append(S._material("Envelope", S.lin((250, 248, 240)), rough=0.6)[0]); env.hide_render = True; env.hide_viewport = True
letters = bpy.data.objects.new("Letters", S._points_mesh("Letters", [], {})); sc.sc.collection.objects.link(letters)
letters.modifiers.new("Inst", "NODES").node_group = S._instancer_nodes("Letters", env)
def set_letters(tt):
    dt = tt - L_T0; on = dt > 0
    if not on.any(): pts, rot = np.zeros((0, 3)), np.zeros((0, 3))
    else:
        z = np.maximum(L_Z0 - 4.9 * dt ** 2, 0.02 + (np.arange(NL) % 4) * 0.015)
        landed = z <= 0.09
        rot = np.where(landed[:, None], np.stack([np.zeros(NL), np.zeros(NL), L_SPIN[:, 2]], -1), L_SPIN * dt[:, None])
        pts = np.stack([L_XY[:, 0] + 0.5, -(L_XY[:, 1] + 0.5), z], -1)[on]; rot = rot[on]
    old = letters.data
    letters.data = S._points_mesh("Letters", pts, dict(scale=np.ones((len(pts), 3)), rot=rot))
    bpy.data.meshes.remove(old)

# ---------------- the whole farm at the end ----------------
# The layout of Experiments 1-4 (pipeline/farm_overview.py, centred on Experiment 4's field) with
# Experiment 5's crop circle where it was in Experiment 5 (90 left, 20 up from Experiment 4's field);
# today's barns land 110 right, 40 down from Experiment 4's field (clear of the others).
E4 = (c - 110, c - 40)                                        # Experiment 4's field, in today's grid
OV_RGBA, OV_FID, OV_BOX, OV_BARN = FO.build()
g5, _ = CR.run(100044, size=N)
ys5, xs5 = np.nonzero(g5); k5 = g5[ys5, xs5]
COL5 = np.array([(0, 0, 0), (120, 80, 48), (222, 178, 70), (236, 120, 30)]) / 255
px5, py5 = xs5 - c - 90 + FO.SZ // 2, ys5 - c - 20 + FO.SZ // 2
OV_RGBA[py5, px5, :3] = COL5[k5]; OV_RGBA[py5, px5, 3] = 1; OV_FID[py5, px5] = 5
OV_BOX[5] = (int(xs5.min() - c - 90), int(ys5.min() - c - 20), int(xs5.max() - c - 90), int(ys5.max() - c - 20))
STAG = (np.sin(np.arange(FO.SZ)[:, None] * 12.9898 + np.arange(FO.SZ)[None, :] * 78.233) * 43758.5453) % 1.0
T_PULL = tl.t_next - 0.3
REVEAL = {5: T_PULL + 0.6, 1: T_PULL + 1.1, 2: T_PULL + 1.6, 3: T_PULL + 2.1}
def overview(tt):
    a = np.zeros((FO.SZ, FO.SZ), np.float32)
    for k, t0 in REVEAL.items():
        m = OV_FID == k; a[m] = np.clip((tt - t0) / 0.5 - STAG[m] * 1.2, 0, 1)
    img = OV_RGBA.copy(); img[..., 3] *= a
    return img
sc.add_barn(E4[0] + OV_BARN[0], E4[1] + OV_BARN[1], facing=-math.pi / 2)        # Experiment 3's barn
BOXES = {k: (b[0] + E4[0] - c, b[1] + E4[1] - c, b[2] + E4[0] - c, b[3] + E4[1] - c) for k, b in OV_BOX.items()}
BOXES[6] = (BX[0] - c - 1, ROW0 - c - 47, BX[2] - c + 2, BY - c + 3)
allb = np.array(list(BOXES.values()))
OV_C = ((allb[:, 0].min() + allb[:, 2].max()) / 2 + c, (allb[:, 1].min() + allb[:, 3].max()) / 2 + c)
OV_S = 1000 / (allb[:, 2].max() - allb[:, 0].min() + 40)

def to_screen(gx, gy, z=0.0):
    from bpy_extras.object_utils import world_to_camera_view
    from mathutils import Vector
    v = world_to_camera_view(sc.sc, sc.cam, Vector((gx, -gy, z)))
    return [round(v.x * S.W, 1), round((1 - v.y) * S.H, 1)]
screen_path = out / "screen.json"
SCREEN = json.loads(screen_path.read_text()) if screen_path.exists() else {}

# ---------------- camera shots (target x, y, zoom, pitch, height, yaw) ----------------
GAME = (c + 0.5, BY + 2.2, 90.0, 26.0, 0.8, 0.0)
def lots_shot(n_rows):
    length = max(6.0, n_rows * 0.7)
    return (c + 0.5, ROW0 - length / 2 + 1, min(70.0, 1150 / (length + 10)), 50.0, 0.0, 0.0)
WIDE = (c + 0.5, (BY + ROW0 - 47) / 2 + 2, 24.0, 45.0, 0.0, 0.0)
OVER = (OV_C[0], OV_C[1], OV_S, 62.0, 0.0, 6.0)
cam = list(GAME); ov_set = -1
t_start = time.time(); rendered = 0
for f in range(end):
    tt = f / FPS
    w = tl.won(f); n = w["played"]
    rows = (max(w["stay"], w["switch"]) + COLS - 1) // COLS
    if tt < tl.t_fifty: tgt = GAME
    elif tt < tl.t_her: tgt = lots_shot(rows)
    elif tt < tl.t_even: tgt = (GAME[0], GAME[1] - 0.8, 82.0, 30.0, 1.4, 0.0) if tt >= tl.t_1990 else GAME
    elif tt < T_PULL: tgt = WIDE
    else: tgt = OVER
    k_ = 0.25 if tt >= T_PULL else (0.12 if tt < 1.0 else 0.08)
    cam[2] *= (tgt[2] / cam[2]) ** k_
    for i in (0, 1, 3, 4, 5): cam[i] += (tgt[i] - cam[i]) * k_
    if f < args.start or f % args.every: continue
    path = out / f"f_{f:05d}.jpg"
    if path.exists() and str(f) in SCREEN: continue
    # Daisy trots up to barn 1; Joe stands by barn 3
    u = smooth((tt - 0.1) / (tl.t_pick - 0.4)); dy = lerp(DAISY_FROM[1], DAISY_AT[1], u)
    sc.set_walker(DAISY_AT[0], dy, 0.02, math.pi / 2, cam[2], walk=(tt * 2.2) % 1 if u < 1 else 0.0)
    sc.set_character(joe, JOE[0], JOE[1], 0.02, math.radians(150 if tt < tl.t_goat - 0.8 else 175), cam[2])
    BP.open_doors(barns[2], smooth((tt - tl.t_goat + 0.4) / 0.7))
    BP.open_doors(barns[1], smooth((tt - tl.t_showed + 0.2) / 0.7))
    # the little tractors parked so far (while slow, the newest grows in)
    p = tl.played[f]
    if tl.t_her - 0.3 <= tt < tl.t_even:             # back at the barns: the bars behind them would clutter the shot
        old = tokens.data; tokens.data = S._points_mesh("Tokens", [], {}); bpy.data.meshes.remove(old)
    elif n:
        grow = np.clip(p - np.arange(n), 0, 1) if p < 8 else np.ones(n)
        s_ = 0.42 * np.clip(grow, 0.05, 1); xy = SLOTS[:n]
        old = tokens.data
        tokens.data = S._points_mesh("Tokens", np.stack([xy[:, 0] + 0.5, -(xy[:, 1] + 0.5), np.zeros(n)], -1),
                                     dict(scale=np.stack([s_] * 3, -1), rot=np.tile([0, 0, math.pi / 2], (n, 1))))
        bpy.data.meshes.remove(old)
    set_letters(tt)
    sc.set_tufts(np.zeros((N, N), np.uint8), cam[0], cam[1] + 3, cam[2]); sc.set_floor(cam[2])
    if tt >= T_PULL:
        key = round(min(tt, max(REVEAL.values()) + 1.8), 2)
        if key != ov_set:                            # lifted: from far away the floor shows through a plane at z=0.02
            sc.set_trail_image(overview(tt), E4[0] - FO.SZ // 2, E4[1] - FO.SZ // 2, glow=0.15, z=0.4); ov_set = key
    sc.set_camera(cam[0], cam[1], cam[2], cam[5], cam[3], cam[4])
    bpy.context.view_layer.update()
    tops = {k: to_screen(LOT[k] + 0.5, ROW0 - ((w[k] - 1) // COLS + 1) * 0.7 + 0.2 if w[k] else ROW0 + 0.5, 0.4) for k in LOT}
    rec = dict(barns=[to_screen(bx + 0.5, BY + 0.5, 4.0) for bx in BX], daisy=to_screen(DAISY_AT[0], dy, 1.0),
               joe=to_screen(JOE[0], JOE[1], 1.4), tops=tops, **w)
    if tt >= T_PULL:
        rec["fields"] = {str(k): to_screen((b[0] + b[2]) / 2 + c + 0.5, b[1] + c - 4, 0.0) for k, b in BOXES.items()}
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
