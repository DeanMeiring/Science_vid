"""Live demo of Experiment 7 (Dean, 23 Oct): from the side, close to Joe, with the farm backdrop.
Joe throws straws in different ways -- an underarm toss, an overhead fling, a spin-throw, a forkful
with the pitchfork, two-handed showers -- each straw flies in an arc, tumbles, lands on the planks
and flashes gold if it lies across a crack. Then it speeds up: counted straws go onto the heap
behind, which grows, and Joe backs away from it (glancing over his shoulder).

Usage: blender -b -P blender/hay_demo.py -- [--seconds 15] [--scale 50] [--pause 1.0]
Frames: renders/ep07_pi/demo_frames/f_00000.jpg + screen.json (prototypes/hay_demo_compose.py).
"""
import argparse, json, math, sys, time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "pipeline"))
import scene as S
import hay_props as HP
import scenery as SC
import hay as HY
from common import FPS, N, ROOT

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--seconds", type=float, default=15)
ap.add_argument("--scale", type=int, default=50)
ap.add_argument("--pause", type=float, default=1.0)
args = ap.parse_args(argv)
S.gentle()
import bpy

OUT = ROOT / "renders" / "ep07_pi" / "demo_frames"; OUT.mkdir(parents=True, exist_ok=True)
NF = int(args.seconds * FPS); c = N // 2
def smooth(u): u = min(1.0, max(0.0, u)); return u * u * (3 - 2 * u)
def lerp(a, b, u): return a + (b - a) * u

# ---------------- the yard ----------------
sc = S.Scene("farm", scale=args.scale)
SC.add_backdrop(sc, c, c - 3, yard=(c - 16, c - 22, c + 14, c + 8)); SC.add_silo(sc, c - 17, c - 8)
daisy = sc.add_character("sheep")
HP.add_floor(sc, c - 8, c - 4, 16, 10)
sc.add_barn(c - 13, c - 3, facing=-math.pi / 3)
HP.add_bale(sc, c + 2, c + 2, facing=0.3)
HP.add_bucket(sc, c - 2.5, c + 4)
fork_root = bpy.data.objects.new("ForkRig", None); sc.sc.collection.objects.link(fork_root)
HP.add_pitchfork(sc, 0, 0, lean=0.0)
fork = bpy.data.objects["Pitchfork"]; fork.parent = fork_root; fork.location = (-0.5, 0.5, 0)
HEAP_AT = (c + 1, c - 9)
heap = HP.add_haystack(sc, *HEAP_AT, 0.01, 0.01)
straws = HP.Straws(sc)
grid = np.zeros((N, N), np.uint8); grid[c - 4:c + 6, c - 8:c + 8] = 1

# ---------------- the throws ----------------
# (start time, kind, straws in it). Each straw flies 0.75 s from Joe's hand to where the simulation
# put it (its angle and its place across its plank are the simulation's; see pipeline/hay.spread).
THROWS = [(0.5, "underarm", 1), (2.7, "overhead", 1), (4.9, "spin", 1), (6.9, "fork", 7), (8.7, "shower", 14)]
FAST0, FAST1, NFAST = 10.0, args.seconds - 0.5, 20000         # then pouring: up to 20,000 straws
d = HY.drop(1, 100000)
t_of, kind_of = [], []
for t0, kind, k in THROWS:
    for i in range(k): t_of.append(t0 + 0.32 + i * (0.04 if kind in ("fork", "shower") else 0)); kind_of.append(kind)
n_slow = len(t_of)
fast_t = FAST0 + (FAST1 - FAST0) * (np.arange(NFAST - n_slow) / (NFAST - n_slow)) ** 2.2   # faster and faster
T_LAND = np.r_[np.array(t_of) + 0.75, fast_t + 0.75]
NTOT = len(T_LAND)
X, Y, ANG, CROSS = HY.spread(d, 0, NTOT, c - 4, c + 1, 9, 4)
HAND_AT = lambda jx, jy: (jx + 0.3, jy + 0.1, 1.0)
GOLD, PALE = np.array(S.lin((255, 196, 52)))[:3], np.array(S.lin((250, 240, 205)))[:3]
TONE = 0.86 + 0.14 * np.random.default_rng(3).random(NTOT)[:, None]
SPIN = np.random.default_rng(5).uniform(-9, 9, (NTOT, 2))

def joe_pose(tt):
    """Joe's spot, facing, lean (fall), hop and walk phase for the throw in progress."""
    jx, jy = lerp(c + 0.5, c + 4.0, smooth((tt - 10.6) / 3.0)), lerp(c + 2.5, c + 5.5, smooth((tt - 10.6) / 3.0))
    ang, fall, hop, walk = math.radians(250), 0.0, 0.0, 0.0
    if 10.6 <= tt < 13.6: walk = (tt * 2.4) % 1; ang = math.radians(240 if int(tt * 1.5) % 2 else 70)   # backing off, glancing back
    for t0, kind, _ in THROWS:
        u = (tt - t0) / 0.6
        if not 0 <= u <= 1: continue
        if kind == "underarm": fall = 0.12 * math.sin(math.pi * u)
        elif kind == "overhead": fall = -0.25 * math.sin(math.pi * u * 0.5) if u < 0.6 else 0.3 * math.sin(math.pi * (u - 0.6) / 0.8)
        elif kind == "spin": ang += 2 * math.pi * smooth(u); hop = 0.25 * math.sin(math.pi * u)
        elif kind in ("fork", "shower"): fall = 0.22 * math.sin(math.pi * u); hop = 0.1 * math.sin(math.pi * u)
    if tt >= FAST0 + 0.6 and tt < 10.6: fall = 0.15 * math.sin(tt * 18)                               # flinging fast
    return jx, jy, ang, fall, hop, walk

screen_path = OUT / "screen.json"
SCREEN = json.loads(screen_path.read_text()) if screen_path.exists() else {}
def to_screen(gx, gy, z=0.0):
    from bpy_extras.object_utils import world_to_camera_view
    from mathutils import Vector
    v = world_to_camera_view(sc.sc, sc.cam, Vector((gx, -gy, z)))
    return [round(v.x * S.W, 1), round((1 - v.y) * S.H, 1)]

t_start = time.time(); rendered = 0
for f in range(NF):
    tt = f / FPS
    path = OUT / f"f_{f:05d}.jpg"
    if path.exists() and str(f) in SCREEN: continue
    jx, jy, ang, fall, hop, walk = joe_pose(tt)
    landed = int(np.searchsorted(T_LAND, tt, "right"))
    # straws in the air: from the hand to the landing spot, arcing and tumbling
    hx, hy, hz = HAND_AT(jx, jy)
    air = np.nonzero((T_LAND > tt) & (T_LAND - 0.75 <= tt))[0][:60]
    u = (tt - (T_LAND[air] - 0.75)) / 0.75
    ax = hx + (X[air] - hx) * u; ay = hy + (Y[air] - hy) * u; az = hz * (1 - u) + 1.4 * np.sin(np.pi * u) + HP.FLOOR_Z * u
    # straws lying on the planks: only the latest 120 (the older ones are on the heap now)
    k0 = max(0, landed - 120); lay = np.arange(k0, landed)
    flash = np.clip(1 - (tt - T_LAND[lay]) / 0.5, 0, 1)                    # just landed: a bright pop
    x = np.r_[X[lay], ax]; y = np.r_[Y[lay], ay]; z = np.r_[np.full(len(lay), HP.FLOOR_Z), az]
    a_ = np.r_[ANG[lay], ANG[air] + SPIN[air, 0] * (1 - u)]
    rgb = np.r_[np.where(CROSS[lay][:, None], GOLD, PALE) * TONE[lay], np.tile(PALE, (len(air), 1))]
    glow = np.r_[np.where(CROSS[lay], 0.9 + 2.5 * flash, 0.3 + 0.8 * flash), np.full(len(air), 0.3)]
    tilt = np.r_[np.zeros(len(lay)), SPIN[air, 1] * (1 - u)]; spin = np.r_[np.zeros(len(lay)), SPIN[air, 0] * (1 - u) * 0.5]
    straws.set(x, y, z, a_, rgb, glow, tilt, spin)
    # the heap: every counted straw that's been raked away
    rad, hgt = HP.heap_size(max(k0, 1)); heap.scale = (max(rad, 0.01), max(rad, 0.01), max(hgt, 0.01))
    # Joe, Daisy (watching, then chewing a straw), the pitchfork in Joe's hands for the forkful
    sc.set_walker(jx, jy, HP.FLOOR_Z + max(0.0, hop), ang, 200.0, walk=walk, fall=fall)
    sc.set_character(daisy, c - 2.0, c + 2.2, HP.FLOOR_Z, math.radians(-30 + 25 * math.sin(tt * 0.9)), 200.0,
                     fall=0.18 * max(0.0, math.sin(tt * 5)) if tt > 7.5 else 0.0)
    fu = (tt - 6.9) / 0.6
    if 0 <= fu <= 1.4:
        fork_root.location = (jx + 0.5 + 0.3 * math.cos(ang), -(jy + 0.5) - 0.3 * math.sin(ang), HP.FLOOR_Z + 0.4)
        fork_root.rotation_euler = (0, -0.6 + 1.2 * smooth(fu), ang)
    else:
        fork_root.location = (c + 4.1, -(c + 3.9), HP.FLOOR_Z); fork_root.rotation_euler = (0.25, 0, 0.6)
    # camera: close by Joe, then pulling back and up to show the heap growing behind him
    v = smooth((tt - 9.6) / 4.0)
    cx, cy = lerp(c + 0.4, c + 1.0, v), lerp(c + 2.6, c - 2.0, v)
    s = 260.0 * (60.0 / 260.0) ** v; pitch = lerp(12.0, 15.0, v); tz = lerp(0.75, 2.4, v); yaw = lerp(-20.0, -14.0, v)
    sc.set_tufts(grid, cx, cy, s); sc.set_floor(s)
    sc.set_camera(cx, cy, s, yaw, pitch, tz)
    bpy.context.view_layer.update()
    SCREEN[str(f)] = dict(straws=landed, gold=int(CROSS[:landed].sum()), joe=to_screen(jx + 0.5, jy + 0.5, 1.4),
                          daisy=to_screen(c - 1.5, c + 2.7, 1.0), heap=to_screen(HEAP_AT[0] + 0.5, HEAP_AT[1] + 0.5, hgt + 0.5))
    sc.render(path); rendered += 1
    if args.pause: time.sleep(args.pause)
    if rendered % 10 == 0:
        screen_path.write_text(json.dumps(SCREEN))
        print(f"frame {f}/{NF} straws {landed:,}  {(time.time() - t_start) / rendered:.2f}s/frame", flush=True)
screen_path.write_text(json.dumps(SCREEN))
print("done", NF, "frames", flush=True)
