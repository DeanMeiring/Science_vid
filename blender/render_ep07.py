"""Render Experiment 7's frames (pi from a bale of hay). Notes and sound come later (pipeline/compose_ep07.py).

Usage: blender -b -P blender/render_ep07.py -- [--scale 100] [--every 1] [--start 0] [--end 0] [--pause 1.0]
Frames: renders/ep07_pi/frames[_draft]/f_00000.jpg, plus screen.json. Frames already on disk are skipped.

Story (pinned to words, see pipeline/ep07_timeline.py), from the side in Joe's yard (Kenney backdrop):
Joe holds up a straw, throws it (gold), throws two more, then quicker and quicker, then blurry-fast;
a wheelbarrow rolls in and tips, the tractor backs in and tips its trailer, a combine harvester drives
across spewing straw out of its back. Every straw lands on the planks (counted: gold if it lies across
a crack), lies there a moment, then hops onto the heap behind, which grows into a mountain while Joe
backs away. Daisy chews a straw; a low shot of the mountain; then the whole farm.
"""
import argparse, json, math, sys, time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "pipeline"))
import scene as S
import hay_props as HP
import barns_props as BP
import machines_props as MP
import scenery as SC
import farm_overview as FO
import hay as HY
from common import FPS, N, ROOT
from ep07_timeline import Timeline, FLY

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

tl = Timeline(ROOT / "episodes" / "ep07_pi.py")
out = tl.dir / ("frames" if args.scale == 100 and args.every == 1 else "frames_draft"); out.mkdir(parents=True, exist_ok=True)
end = args.end or tl.nf
c = N // 2
def smooth(u): u = min(1.0, max(0.0, u)); return u * u * (3 - 2 * u)
def lerp(a, b, u): return a + (b - a) * u
rng = np.random.default_rng(11)

# ---------------- the yard ----------------
sc = S.Scene("farm", scale=args.scale)
YARD = (c - 16, c - 22, c + 14, c + 8)
SC.add_backdrop(sc, c, c - 3, yard=YARD, use_kenney=True); SC.add_silo(sc, c - 17, c - 8)
daisy = sc.add_character("sheep")
HP.add_floor(sc, c - 8, c - 4, 16, 10)
sc.add_barn(c - 13, c - 3, facing=-math.pi / 3)
HP.add_bale(sc, c + 2, c + 2, facing=0.3)
HP.add_bucket(sc, c - 5.5, c + 5.2)
HP.add_pitchfork(sc, c + 3.6, c + 3.6, lean=0.25, facing=0.6)
HEAP_AT = (c + 1, c - 12)
heap = HP.add_haystack(sc, *HEAP_AT, 0.01, 0.01)
straws = HP.Straws(sc)
held = bpy.data.objects.new("HeldStraw", bpy.data.objects["StrawSrc"].data); sc.sc.collection.objects.link(held)
chew = bpy.data.objects.new("ChewStraw", bpy.data.objects["StrawSrc"].data); sc.sc.collection.objects.link(chew)
barrow = MP.add_wheelbarrow(c - 14, c + 0.5, facing=0.0)
barrow_hay = HP.add_haystack(sc, 0, 0, 0.3, 0.25); barrow_hay.parent = barrow["load"]; barrow_hay.location = (0, 0, -0.05)
tractor = BP.add_tractor(sc, c + 20, c - 1, facing=0.0)
trailer = MP.add_trailer(c + 17, c - 1, facing=0.0)
trailer_hay = HP.add_haystack(sc, 0, 0, 0.45, 0.3); trailer_hay.parent = trailer["load"]; trailer_hay.location = (0, 0, -0.05)
CY = c - 1.0                                                   # the combine drives along y = CY (clear of the bale)
combine = MP.add_combine(c - 26, CY, facing=0.0)
grid = np.zeros((N, N), np.uint8); grid[c - 4:c + 6, c - 8:c + 8] = 1

# ---------------- where the straws go ----------------
X, Y, ANG, CR = (np.empty(len(tl.land)) for _ in range(4))
o = tl.order
def place(stage, area):
    m = np.nonzero(tl.stage == stage)[0]
    x, y, a, cr = HY.spread(tl.d, 0, len(tl.land), *area)          # same fractions of y and angles as the simulation
    X[m], Y[m], ANG[m], CR[m] = x[o][m], y[o][m], a[o][m], cr[o][m]
for st in ("hand", "quicker", "blur"): place(st, (c - 2.5, c + 3, 5, 2))         # in front of Joe
place("barrow", (c - 7, c - 1, 5, 3))                                              # in front of the wheelbarrow
place("tractor", (c - 2, c - 3, 5, 3))                                             # behind the trailer
place("combine", (c - 8, c - 3, 16, 4))                                            # x is set below, behind the combine
assert (CR.astype(bool) == tl.cross).all()
GOLD, PALE = np.array(S.lin((255, 196, 52)))[:3], np.array(S.lin((250, 240, 205)))[:3]
TONE = 0.86 + 0.14 * rng.random(len(X))[:, None]
SPIN = rng.uniform(-9, 9, (len(X), 2))

# the machines' paths (times from the timeline)
T_BARROW, T_TRACTOR, T_COMBINE = tl.win["barrow"], tl.win["tractor"], tl.win["combine"]
def barrow_state(tt):
    a, b = T_BARROW
    x = lerp(c - 14, c - 7.5, smooth((tt - (a - 1.2)) / 1.0)) if tt < b + 0.4 else lerp(c - 7.5, c - 15, smooth((tt - b - 0.4) / 1.0))
    tip = smooth((tt - a + 0.25) / 0.35) * (1 - smooth((tt - b - 0.1) / 0.3))
    return x, tip
def tractor_state(tt):
    a, b = T_TRACTOR
    x = lerp(c + 20, c + 3, smooth((tt - (a - 1.3)) / 1.1)) if tt < b + 0.3 else lerp(c + 3, c + 22, smooth((tt - b - 0.3) / 1.2))
    tip = smooth((tt - a + 0.25) / 0.35) * (1 - smooth((tt - b - 0.05) / 0.3))
    return x, tip
CX0, CX1 = c - 26, c + 26
def combine_x(tt):
    a, b = T_COMBINE
    return lerp(CX0, CX1, (tt - (a - 1.6)) / ((b + 1.6) - (a - 1.6)))
m = tl.stage == "combine"
rear_x = np.array([combine_x(t) for t in tl.release[m]]) - 0.85 * 1.9
X[m] = np.clip(rear_x - rng.uniform(0.6, 3.0, m.sum()), c - 7.5, c + 7.5)

def release_point(k, hand):
    s = tl.stage[k]
    if s in ("hand", "quicker", "blur"): return hand
    if s == "barrow": return (c - 6.6, c + 0.5, 0.9)
    if s == "tractor": return (c + 1.8, c - 1.0, 0.9)
    return (combine_x(tl.release[k]) - 0.85 * 1.9, CY + 0.5, 1.1)

# ---------------- Joe ----------------
J0 = (c + 0.5, c + 2.5); J1 = (c + 4.6, c + 6.2)            # where he throws from; where he backs off to
BALE = (c + 2.5, c + 2.5)
LAND_J = (c, c + 4)
HAND_IDX = np.nonzero(tl.stage == "hand")[0]; QUICK_IDX = np.nonzero(tl.stage == "quicker")[0]
def joe_pose(tt):
    back = smooth((tt - (T_BARROW[0] - 1.4)) / 2.6)
    jx, jy = lerp(J0[0], J1[0], back), lerp(J0[1], J1[1], back)
    face_throw = math.atan2(-(LAND_J[1] - jy), LAND_J[0] - jx); face_bale = math.atan2(-(BALE[1] - jy), BALE[0] - jx)
    face_heap = math.atan2(-(HEAP_AT[1] - jy), HEAP_AT[0] - jx)
    ang, fall, hop, walk, arms, holding = face_throw, 0.0, 0.0, 0.0, {"right": (0.1, 0.05), "left": (0.05, 0.05)}, False
    t_first = tl.release[HAND_IDX[0]]
    if tt < t_first - 0.55:                                     # showing the first straw
        arms = {"right": (-1.9, 0.15), "left": (0.1, 0.05)}; holding = True; ang = face_throw + 0.5
    for k in HAND_IDX:                                          # reach (not for the first), turn, throw
        r = tl.release[k]; u = tt - (r - 1.05)
        if not -0.0 <= u <= 1.5: continue
        if k == HAND_IDX[0] and u < 0.6: holding = True; continue
        if u < 0.35:
            q = smooth(u / 0.25); ang = face_throw + (face_bale - face_throw) * q; fall = 0.32 * q
            arms = {"right": (-0.9 * q, 0.1), "left": (-0.6 * q, 0.1)}
        elif u < 0.6:
            q = smooth((u - 0.35) / 0.25); ang = face_bale + (face_throw - face_bale) * q; fall = 0.32 * (1 - q)
            arms = {"right": (-0.9 * (1 - q) + 0.2 * q, 0.1), "left": (-0.6 * (1 - q), 0.1)}; holding = True
        else:
            w = (u - 0.6) / 0.9
            sw = (lerp(0.2, 0.95, smooth(w / 0.4)) if w < 0.4 else lerp(0.95, -1.7, smooth((w - 0.4) / 0.3)) if w < 0.7
                  else lerp(-1.7, 0.1, smooth((w - 0.7) / 0.3)))
            arms = {"right": (sw, 0.1), "left": (0.15, 0.1)}; fall = 0.1 * math.sin(math.pi * min(1, w * 1.3)); holding = w < 0.5
    q0, q1 = tl.release[QUICK_IDX[0]] - 0.4, tl.release[QUICK_IDX[-1]] + 0.3
    if q0 <= tt < q1:                                           # quicker: a swing per straw
        k = QUICK_IDX[np.argmin(np.abs(tl.release[QUICK_IDX] - tt))]; w = (tt - tl.release[k]) / 0.35
        sw = lerp(0.9, -1.6, smooth((w + 1) / 1.2)) if w < 0.2 else lerp(-1.6, 0.6, smooth(w / 0.8))
        arms = {"right": (sw, 0.15), "left": (0.3, 0.15)}; fall = 0.06
    b0, b1 = tl.win["blur"]
    if b0 <= tt < b1:                                           # blurry-fast: arms everywhere
        f_ = int(tt * FPS)
        arms = {"right": (rng.uniform(-2.8, 1.0), rng.uniform(0, 0.8)), "left": (rng.uniform(-2.8, 1.0), rng.uniform(0, 0.8))}
        fall = 0.12 * math.sin(f_ * 2.1); hop = 0.06 * abs(math.sin(f_ * 1.7)); ang = face_throw + 0.25 * math.sin(f_ * 1.3)
    if 0 < back < 1:                                            # backing away, glancing back at the heap
        walk = (tt * 2.4) % 1; ang = face_heap + math.pi + (math.pi if int(tt * 1.6) % 2 else 0) * 0.8
        arms = {"right": (0.35 * math.sin(tt * 15), 0.1), "left": (-0.35 * math.sin(tt * 15), 0.1)}
    elif back >= 1:                                             # watching the machines (arms up at the combine)
        ang = face_heap + math.pi * 0.85
        up = smooth((tt - T_COMBINE[0]) / 0.6) * (1 - smooth((tt - tl.t_daisy) / 0.5))
        arms = {"right": (-2.6 * up, 0.4 * up), "left": (-2.6 * up, 0.4 * up)}
    return jx, jy, ang, fall, hop, walk, arms, holding

# ---------------- the whole farm at the end ----------------
E4 = (c + 170, c)                                               # Experiment 4's field in this grid (#7 sits at -170, 0 from it)
OV_RGBA, OV_FID, OV_BOX, OV_BARN = FO.build_all()
STAG = (np.sin(np.arange(FO.SZ)[:, None] * 12.9898 + np.arange(FO.SZ)[None, :] * 78.233) * 43758.5453) % 1.0
T_PULL = tl.t_buffon - 0.2
REVEAL = {5: T_PULL + 0.6, 6: T_PULL + 0.9, 1: T_PULL + 1.2, 2: T_PULL + 1.6, 3: T_PULL + 2.0}
def overview(tt):
    a = np.zeros((FO.SZ, FO.SZ), np.float32)
    for k, t0 in REVEAL.items():
        mm = OV_FID == k; a[mm] = np.clip((tt - t0) / 0.5 - STAG[mm] * 1.2, 0, 1)
    img = OV_RGBA.copy(); img[..., 3] *= a
    return img
sc.add_barn(E4[0] + OV_BARN[0], E4[1] + OV_BARN[1], facing=-math.pi / 2)        # Experiment 3's barn
BOXES = {k: (b[0] + E4[0] - c, b[1] + E4[1] - c, b[2] + E4[0] - c, b[3] + E4[1] - c) for k, b in OV_BOX.items()}
BOXES[7] = (-8, -24, 8, 6)
allb = np.array(list(BOXES.values()))
OV_C = ((allb[:, 0].min() + allb[:, 2].max()) / 2 + c, (allb[:, 1].min() + allb[:, 3].max()) / 2 + c)
OV_S = 1000 / (allb[:, 2].max() - allb[:, 0].min() + 40)
HIDE_AT_END = [ob for ob in bpy.data.objects if ob.type == "MESH" and ob.data.materials and
               ob.data.materials[0] and ob.data.materials[0].name.startswith(("Hill", "Cloud"))]

def to_screen(gx, gy, z=0.0):
    from bpy_extras.object_utils import world_to_camera_view
    from mathutils import Vector
    v = world_to_camera_view(sc.sc, sc.cam, Vector((gx, -gy, z)))
    return [round(v.x * S.W, 1), round((1 - v.y) * S.H, 1), round(v.z, 2)]
screen_path = out / "screen.json"
SCREEN = json.loads(screen_path.read_text()) if screen_path.exists() else {}

# ---------------- camera shots: (x, y, zoom, pitch, height, yaw) ----------------
DAISY_AT = (c - 4, c + 4.2)
def shot(tt):
    if tt < tl.t_faster: return (c + 0.2, c + 3.4, 210.0, 16.0, 0.75, -20.0)
    if tt < tl.t_ten: return (c + 0.2, c + 3.0, 170.0, 16.0, 0.8, -18.0)
    if tt < tl.t_299 + 0.6: return (c + 0.5, c + 2.0, 120.0, 15.0, 1.0, -16.0)
    if tt < T_COMBINE[0] - 0.6: return (c + 0.5, c - 1.0, 46.0, 16.0, 1.6, -12.0)
    if tt < tl.t_daisy: return (c + 0.5, c - 3.0, 28.0, 15.0, 2.6, -10.0)
    if tt < tl.t_mountain: return (DAISY_AT[0] + 0.5, DAISY_AT[1] + 0.5, 240.0, 12.0, 0.6, -20.0)
    if tt < T_PULL: return (J1[0], J1[1], 110.0, 6.0, 2.4, -12.0)
    return (OV_C[0], OV_C[1], OV_S, 62.0, 0.0, 6.0)
CUTS = (tl.t_daisy, tl.t_mountain)                              # hard cuts (no glide)
cam = list(shot(0)); ov_set = -1; REL_AT = {}; hidden = False
t_start = time.time(); rendered = 0
for f in range(end):
    tt = f / FPS
    tgt = shot(tt)
    if any(abs(tt - t0) < 0.5 / FPS for t0 in CUTS): cam = list(tgt)
    k_ = 0.22 if tt >= T_PULL else 0.09
    if tt >= T_PULL:
        u = smooth((tt - T_PULL) / 2.8); a = shot(T_PULL - 0.01)
        tgt = (lerp(a[0], tgt[0], u), lerp(a[1], tgt[1], u), a[2] * (tgt[2] / a[2]) ** u, lerp(a[3], tgt[3], u), lerp(a[4], tgt[4], u), lerp(a[5], tgt[5], u))
    cam[2] *= (tgt[2] / cam[2]) ** k_
    for i in (0, 1, 3, 4, 5): cam[i] += (tgt[i] - cam[i]) * k_
    jx, jy, ang, fall, hop, walk, arms, holding = joe_pose(tt)   # (always: the blur poses use the random stream)
    if f < args.start or f % args.every: continue
    path = out / f"f_{f:05d}.jpg"
    if path.exists() and str(f) in SCREEN: continue
    # ---- Joe, and the straw in his hand
    sc.set_walker(jx, jy, HP.FLOOR_Z + max(0.0, hop), ang, cam[2], walk=walk, fall=fall, arms=arms, tool=False)
    bpy.context.view_layer.update()
    hw = sc.hand_position("right"); hand = (hw[0], -hw[1], hw[2])
    held.hide_render = not holding
    if holding: held.location = hw; held.rotation_euler = (0.4, 1.2, ang)
    # ---- the straws: flying, lying on the planks (flashing as they land), hopping onto the heap
    landed, gold = tl.counted(tt); heaped = tl.on_heap(tt)
    fly = np.nonzero((tl.release <= tt) & (tl.land > tt))[0]
    if len(fly) > 300: fly = fly[np.linspace(0, len(fly) - 1, 300).astype(int)]
    lie = np.arange(heaped, landed)
    if len(lie) > 450: lie = lie[np.r_[np.linspace(0, len(lie) - 160, 290).astype(int), np.arange(len(lie) - 160, len(lie))]]
    hop_ = np.nonzero((tl.to_heap <= tt) & (tl.to_heap > tt - 0.45))[0]
    if len(hop_) > 160: hop_ = hop_[np.linspace(0, len(hop_) - 1, 160).astype(int)]
    for k in fly: REL_AT.setdefault(int(k), release_point(int(k), hand))
    rel = np.array([REL_AT[int(k)] for k in fly]).reshape(-1, 3)
    uf = (tt - tl.release[fly]) / np.maximum(tl.land[fly] - tl.release[fly], 1e-6)
    fx = rel[:, 0] + (X[fly] - rel[:, 0]) * uf; fy = rel[:, 1] + (Y[fly] - rel[:, 1]) * uf
    fz = rel[:, 2] * (1 - uf) + 0.8 * np.sin(np.pi * uf) + HP.FLOOR_Z * uf
    rad, hgt = HP.heap_size(max(heaped, 1), r_full=12.0)
    uh = (tt - tl.to_heap[hop_]) / 0.45
    hx_ = X[hop_] + (HEAP_AT[0] + 0.5 + rng.uniform(-0.3, 0.3, len(hop_)) * rad - X[hop_]) * uh
    hy_ = Y[hop_] + (HEAP_AT[1] + 0.5 + rad * 0.5 - Y[hop_]) * uh
    hz_ = HP.FLOOR_Z + (hgt * 0.6) * uh + 1.2 * np.sin(np.pi * uh)
    flash = np.clip(1 - (tt - tl.land[lie]) / 0.5, 0, 1)
    cr_l, cr_h = tl.cross[lie], tl.cross[hop_]
    x = np.r_[X[lie], fx, hx_]; y = np.r_[Y[lie], fy, hy_]
    z = np.r_[np.full(len(lie), HP.FLOOR_Z), fz, hz_]
    a_ = np.r_[ANG[lie], ANG[fly] + SPIN[fly, 0] * (1 - uf), ANG[hop_] + SPIN[hop_, 0] * uh]
    rgb = np.r_[np.where(cr_l[:, None], GOLD, PALE) * TONE[lie], np.tile(PALE, (len(fly), 1)), np.where(cr_h[:, None], GOLD, PALE)]
    glow = np.r_[np.where(cr_l, 0.9 + 2.5 * flash, 0.3 + 0.8 * flash), np.full(len(fly), 0.3), np.where(cr_h, 0.9, 0.3)]
    tilt = np.r_[np.zeros(len(lie)), SPIN[fly, 1] * (1 - uf), SPIN[hop_, 1] * uh]
    spin = np.r_[np.zeros(len(lie)), SPIN[fly, 0] * (1 - uf) * 0.5, SPIN[hop_, 0] * uh * 0.5]
    straws.set(x, y, z, a_, rgb, glow, tilt, spin)
    heap.scale = (max(rad, 0.01), max(rad, 0.01), max(hgt, 0.01))
    # ---- the machines
    bx, tip = barrow_state(tt)
    barrow["root"].location = (bx + 0.5, -(c + 0.5 + 0.5), 0); barrow["tray"].rotation_euler = (0, -0.9 * tip, 0)
    barrow_hay.hide_render = tip > 0.35 or tt > T_BARROW[1]
    tx, tip2 = tractor_state(tt)
    tractor.location = (tx + 2.6 + 0.5, -(c - 1 + 0.5), 0); trailer["root"].location = (tx + 0.5, -(c - 1 + 0.5), 0)
    trailer["bed"].rotation_euler = (0, 0.7 * tip2, 0); trailer_hay.hide_render = tip2 > 0.35 or tt > T_TRACTOR[1]
    combine["root"].location = (combine_x(tt) + 0.5, -(CY + 0.5), 0); combine["reel"].rotation_euler = (0, tt * 6.0, 0)
    # ---- Daisy (chewing a straw at the end)
    chewing = tt >= tl.t_daisy - 0.3
    sc.set_character(daisy, DAISY_AT[0] + 0.5, DAISY_AT[1] + 0.5, HP.FLOOR_Z, math.radians(-30), cam[2],
                     fall=0.12 * max(0.0, math.sin(tt * 9)) if chewing else 0.0)
    chew.hide_render = not chewing
    if chewing:
        a0 = math.radians(-30)
        chew.location = (DAISY_AT[0] + 0.5 + 0.55 * math.cos(a0), -(DAISY_AT[1] + 0.5) + 0.55 * math.sin(a0), 0.78)
        chew.rotation_euler = (0, 0.15, a0 + math.pi / 2 + 0.25 * math.sin(tt * 9))
    # ---- the farm at the end
    sc.set_tufts(grid, cam[0], cam[1], cam[2]); sc.set_floor(cam[2])
    if tt >= T_PULL:
        if not hidden:
            for ob in HIDE_AT_END: ob.hide_render = True
            hidden = True
        key = round(min(tt, max(REVEAL.values()) + 1.8), 2)
        if key != ov_set:                            # lifted: from far away the floor shows through a plane at z=0.02
            sc.set_trail_image(overview(tt), E4[0] - FO.SZ // 2, E4[1] - FO.SZ // 2, glow=0.15, z=0.4); ov_set = key
    sc.set_camera(cam[0], cam[1], cam[2], cam[5], cam[3], cam[4])
    bpy.context.view_layer.update()
    rec = dict(straws=landed, gold=gold, joe=to_screen(jx, jy, 1.4), daisy=to_screen(DAISY_AT[0] + 0.5, DAISY_AT[1] + 0.5, 1.2),
               heap=to_screen(HEAP_AT[0] + 0.5, HEAP_AT[1] + 0.5, hgt + 0.4), stage=str(tl.stage[max(landed - 1, 0)]) if landed else "")
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
