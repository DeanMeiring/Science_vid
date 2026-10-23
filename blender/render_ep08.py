"""Render Experiment 8's frames (what grows if you plant it?). Notes and sound come later (pipeline/compose_ep08.py).

Usage: blender -b -P blender/render_ep08.py -- [--scale 100] [--every 1] [--start 0] [--end 0] [--pause 1.0]
Frames: renders/ep08_plant/frames[_draft]/f_00000.jpg, plus screen.json. Frames already on disk are skipped.

Five scenes, cut together (pinned to words, see pipeline/ep08_timeline.py), in Joe's garden by the yard
(detailed trees): the mustard (planted, a time-lapse grows it chest-high); the apple tree (planted,
grows, green apples; Joe holds the red one); both seeds in one hole (two separate plants come up); the
rusty tyre (planted; Joe waits in his deck chair through two winters, his moustache growing; weeds come
up round the tyre); Pasteur's swan-neck flask on a little table; then the whole farm.
"""
import argparse, json, math, sys, time
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "pipeline"))
import scene as S
import scenery as SC
import garden_props as GP
import farm_overview as FO
from common import FPS, N, ROOT
from ep08_timeline import Timeline

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

tl = Timeline(ROOT / "episodes" / "ep08_plant.py")
out = tl.dir / ("frames" if args.scale == 100 and args.every == 1 else "frames_draft"); out.mkdir(parents=True, exist_ok=True)
end = args.end or tl.nf
c = N // 2
def smooth(u): u = min(1.0, max(0.0, u)); return u * u * (3 - 2 * u)
def lerp(a, b, u): return a + (b - a) * u
def win(t, w): return smooth((t - w[0]) / max(w[1] - w[0], 1e-6))

# ---------------- the garden ----------------
sc = S.Scene("farm", scale=args.scale)
SC.add_backdrop(sc, c, c - 3, yard=(c - 16, c - 22, c + 14, c + 8), use_kenney="detailed"); SC.add_silo(sc, c - 17, c - 8)
sc.add_barn(c - 13, c - 3, facing=-math.pi / 3)
GP.add_bed(c - 6, c - 1, 15, 3)
grid = np.zeros((N, N), np.uint8); grid[c - 1:c + 2, c - 6:c + 9] = 1                  # no grass tufts on the bed
MUSTARD = GP.add_mustard(c - 4, c); STICK = GP.add_stick(c - 3.1, c + 0.4)
TREE = GP.add_apple_tree(c + 0.5, c - 0.5)
BOTH_M = GP.add_mustard(c + 3.9, c, seed=5); BOTH_A = GP.add_apple_tree(c + 5.0, c - 0.2, size=1.3, seed=8)
for a in BOTH_A["apples"]: a.hide_render = True                                      # a young tree: no fruit yet
TYRE = GP.add_tyre(c + 7, c + 0.3)
CHAIR = GP.add_deckchair(c + 8.3, c + 1.8, rot=math.radians(150))
bpy.ops.mesh.primitive_cube_add(size=1, location=(c + 6.3, -(c + 2.3), 0.25)); TABLE = bpy.context.object
TABLE.scale = (0.5, 0.5, 0.5); TABLE.data.materials.append(GP._mat("ChairWood", (176, 130, 82), 0.7))
FLASK = GP.add_flask(c + 5.8, c + 1.8, z=0.5)
RED_APPLE = GP.add_apple(0, 0, 0)
SEED = GP._sphere((0, 0, 0), 0.03, GP._mat("Seed", (60, 40, 28), 0.6), None)
WEEDS = []
r_ = np.random.default_rng(3)
for k in range(14):                                                                   # weeds round the tyre (seeds already in the soil)
    a, d = r_.uniform(0, 2 * math.pi), r_.uniform(0.5, 1.4)
    w = SC.kenney(["grass_large", "plant_bushSmall", "flower_yellowB", "grass_leafsLarge"][k % 4], c + 7 + d * math.cos(a),
                  c + 0.3 + d * math.sin(a), rot=r_.uniform(0, 6.3), scale=r_.uniform(1.6, 2.4))
    WEEDS.append((w, w.scale[0]))
bpy.ops.mesh.primitive_plane_add(size=80, location=(c + 0.5, -(c + 0.5), 0.12)); SNOW = bpy.context.object
SNOW.data.materials.append(S._material("Snow", S.lin((246, 248, 252)), rough=0.8)[0])
MOUSTACHE = [o for o in sc.body.children_recursive if o.type == "MESH" and o.data.materials and o.data.materials[0].name.startswith("Moustache")]
M_SCALE = [tuple(o.scale) for o in MOUSTACHE]

# the sky and the sun, for the time-lapses (day -> dusk -> night -> dawn)
wnt = sc.sc.world.node_tree
RAMP = next(n for n in wnt.nodes if n.type == "VALTORGB")
SUN = next(o for o in bpy.data.objects if o.type == "LIGHT" and o.data.type == "SUN"); SUN_E = SUN.data.energy
WORLD_BG = wnt.nodes["Background"]; WORLD_S = WORLD_BG.inputs["Strength"].default_value
DAY = (S.lin((206, 228, 246)), S.lin((92, 156, 232))); DUSK = (S.lin((250, 170, 120)), S.lin((80, 90, 160)))
NIGHT = (S.lin((40, 50, 90)), S.lin((10, 14, 36)))
def mixc(a, b, u): return tuple(a[i] + (b[i] - a[i]) * u for i in range(4))
def set_sky(light):
    """light 1 = day, 0.5 = dusk, 0 = night."""
    if light >= 0.5: lo, hi, u = DUSK, DAY, (light - 0.5) * 2
    else: lo, hi, u = NIGHT, DUSK, light * 2
    RAMP.color_ramp.elements[0].color = mixc(lo[0], hi[0], u); RAMP.color_ramp.elements[1].color = mixc(lo[1], hi[1], u)
    SUN.data.energy = SUN_E * (0.15 + 0.85 * light); WORLD_BG.inputs["Strength"].default_value = WORLD_S * (0.3 + 0.7 * light)
LAPSES = [(tl.grow_mustard, 3), (tl.grow_apple, 4), (tl.grow_both, 2), (tl.wait, 4)]      # (window, days and nights shown)
def light_at(tt):
    for (a, b), n in LAPSES:
        if a <= tt <= b: return 0.5 + 0.5 * math.cos(2 * math.pi * n * (tt - a) / (b - a))
    return 1.0
def snowing(tt):
    a, b = tl.wait
    u = (tt - a) / (b - a)
    return a <= tt <= b and (0.15 < u < 0.35 or 0.65 < u < 0.85)                  # two winters

# ---------------- the whole farm at the end ----------------
E4 = (c + 260, c)                                               # Experiment 4's field in this grid (#8 sits at -260, 0 from it)
OV_RGBA, OV_FID, OV_BOX, OV_BARN = FO.build_upto7()
STAG = (np.sin(np.arange(FO.SZ)[:, None] * 12.9898 + np.arange(FO.SZ)[None, :] * 78.233) * 43758.5453) % 1.0
T_PULL = tl.s_end
REVEAL = {7: T_PULL + 0.5, 5: T_PULL + 0.8, 6: T_PULL + 1.0, 1: T_PULL + 1.2, 2: T_PULL + 1.5, 3: T_PULL + 1.8}
def overview(tt):
    a = np.zeros((FO.SZ, FO.SZ), np.float32)
    for k, t0 in REVEAL.items():
        mm = OV_FID == k; a[mm] = np.clip((tt - t0) / 0.4 - STAG[mm] * 1.0, 0, 1)
    img = OV_RGBA.copy(); img[..., 3] *= a
    return img
sc.add_barn(E4[0] + OV_BARN[0], E4[1] + OV_BARN[1], facing=-math.pi / 2)        # Experiment 3's barn
BOXES = {k: (b[0] + E4[0] - c, b[1] + E4[1] - c, b[2] + E4[0] - c, b[3] + E4[1] - c) for k, b in OV_BOX.items()}
BOXES[8] = (-7, -3, 9, 3)
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

# ---------------- Joe, scene by scene ----------------
UP, CAMWARD = math.pi / 2, -math.pi / 2 + 0.35             # facing the bed; facing (roughly) the camera
def plant_pose(u):
    """Kneeling to plant: down, a pat, up (u 0..1)."""
    k = math.sin(math.pi * min(1.0, u))
    return 0.45 * k, {"right": (-0.9 * k, 0.1), "left": (-0.7 * k, 0.1)}
def joe(tt):
    """(x, y, z, ang, fall, arms, holding) for Joe."""
    if tt < tl.s_apple:
        u = tt / 1.2; f, arms = plant_pose(u) if u < 1 else (0.0, {})
        return c - 3.0, c + 1.3, 0.0, UP if tt < 1.4 else CAMWARD, f, arms, None
    if tt < tl.s_both:
        u = (tt - tl.s_apple) / 1.0; f, arms = plant_pose(u) if u < 1 else (0.0, {})
        holding = "apple" if tt > tl.grow_apple[1] - 0.6 else None
        if holding: arms = {"right": (-1.7, 0.2), "left": (0.1, 0.05)}
        return c - 0.8, c + 1.8, 0.0, UP if tt < tl.s_apple + 1.2 else CAMWARD + 0.3, f, arms, holding
    if tt < tl.s_tyre:
        u = (tt - tl.s_both) / 1.0; f, arms = plant_pose(u) if u < 1 else (0.0, {})
        return c + 3.3, c + 1.4, 0.0, UP if tt < tl.s_both + 1.2 else CAMWARD, f, arms, None
    a, b = tl.plant_tyre
    if tt < b:                                                  # carrying the tyre, then lowering it in
        u = (tt - a) / (b - a); f = 0.45 * smooth((u - 0.5) / 0.4)
        return c + 7.0, c + 1.5, 0.0, UP, f, {"right": (-1.0, 0.25), "left": (-1.0, 0.25)}, "tyre" if u < 0.85 else None
    if tt < b + 0.4:                                            # to the deck chair
        u = (tt - b) / 0.4
        return lerp(c + 7.0, c + 7.8, u), lerp(c + 1.5, c + 1.8, u), 0.0, math.radians(150) + math.pi, 0.0, {}, None
    return c + 7.8, c + 1.8, 0.25, math.radians(150), -0.35, {"right": (0.4, 0.1), "left": (0.4, 0.1)}, None   # lounging

# ---------------- camera shots: (x, y, zoom, pitch, height, yaw), cut at each scene ----------------
def shot(tt):
    if tt < tl.s_apple: return (c - 3.6, c + 1.2, 290.0, 8.0, 0.7, -15.0)
    if tt < tl.s_both: return (c + 0.4, c + 0.8, 175.0, 4.0, 1.7, -12.0)
    if tt < tl.s_tyre: return (c + 4.3, c + 1.0, 280.0, 8.0, 0.6, -15.0)
    if tt < tl.s_law: return (c + 8.0, c + 1.6, 230.0, 10.0, 0.55, -18.0)
    if tt < T_PULL: return (c + 7.6, c + 2.0, 240.0, 9.0, 0.7, -18.0)
    return (OV_C[0], OV_C[1], OV_S, 62.0, 0.0, 6.0)
CUTS = (tl.s_apple, tl.s_both, tl.s_tyre, tl.s_law)
cam = list(shot(0)); ov_set = -1; hidden = False
t_start = time.time(); rendered = 0
for f in range(end):
    tt = f / FPS
    tgt = shot(tt)
    if f == 0 or any(abs(tt - t0) < 0.5 / FPS for t0 in CUTS): cam = list(tgt)
    k_ = 0.22 if tt >= T_PULL else 0.1
    if tt >= T_PULL:
        u = smooth((tt - T_PULL) / 2.6); a = shot(T_PULL - 0.01)
        tgt = (lerp(a[0], tgt[0], u), lerp(a[1], tgt[1], u), a[2] * (tgt[2] / a[2]) ** u, lerp(a[3], tgt[3], u), lerp(a[4], tgt[4], u), lerp(a[5], tgt[5], u))
    cam[2] *= (tgt[2] / cam[2]) ** k_
    for i in (0, 1, 3, 4, 5): cam[i] += (tgt[i] - cam[i]) * k_
    if f < args.start or f % args.every: continue
    path = out / f"f_{f:05d}.jpg"
    if path.exists() and str(f) in SCREEN: continue
    # ---- growing things
    MUSTARD.scale = (max(0.001, win(tt, tl.grow_mustard)),) * 3
    STICK.hide_render = tt < tl.grow_mustard[1] - 0.5
    g = win(tt, tl.grow_apple); TREE["root"].scale = (max(0.001, g),) * 3
    for ap_ in TREE["apples"]: ap_.hide_render = g < 0.85
    g2 = win(tt, tl.grow_both); BOTH_M.scale = (max(0.001, 0.55 * g2),) * 3; BOTH_A["root"].scale = (max(0.001, g2),) * 3
    tyre_in = tt >= tl.plant_tyre[0] + 0.85 * (tl.plant_tyre[1] - tl.plant_tyre[0])
    TYRE.hide_render = not tyre_in
    for w, s0 in WEEDS: w.scale = (max(0.001, s0 * smooth((tt - tl.weeds) / 0.5)),) * 3
    FLASK.hide_render = TABLE.hide_render = tt < tl.s_law
    for o in FLASK.children_recursive: o.hide_render = tt < tl.s_law
    # ---- time: the sky, snow, the moustache
    set_sky(light_at(tt)); snow = snowing(tt); SNOW.hide_render = not snow
    beard = 1 + 1.6 * win(tt, tl.wait)
    for o, s0 in zip(MOUSTACHE, M_SCALE): o.scale = (s0[0] * (1 + 0.3 * (beard - 1)), s0[1] * beard, s0[2] * (1 + 0.6 * (beard - 1)))
    # ---- Joe, the seed and what he's holding
    jx, jy, jz, ang, fall, arms, holding = joe(tt)
    sc.set_walker(jx + 0.5, jy + 0.5, jz, ang, cam[2], fall=fall, arms=arms, tool=False)
    bpy.context.view_layer.update()
    hw = sc.hand_position("right")
    RED_APPLE.hide_render = holding != "apple"
    if holding == "apple": RED_APPLE.location = (hw[0], hw[1], hw[2] + 0.08)
    if holding == "tyre":
        TYRE.hide_render = False; TYRE.location = (hw[0], hw[1], hw[2] + 0.1)
    elif tyre_in: TYRE.location = (c + 7.5, -(c + 0.8), 0.12)
    seed_t = [(0.55, c - 4, c), (tl.s_apple + 0.5, c + 0.5, c - 0.5), (tl.s_both + 0.5, c + 4.5, c)]
    SEED.hide_render = True
    for t0, sx, sy in seed_t:
        if t0 <= tt < t0 + 0.4:
            u = (tt - t0) / 0.4; SEED.hide_render = False
            SEED.location = (lerp(hw[0], sx + 0.5, u), lerp(hw[1], -(sy + 0.5), u), lerp(hw[2], 0.1, u))
    # ---- the farm at the end
    g_ = grid.copy()
    if snow: g_[:] = 1
    sc.set_tufts(g_, cam[0], cam[1], cam[2]); sc.set_floor(cam[2])
    if tt >= T_PULL:
        if not hidden:
            for ob in HIDE_AT_END: ob.hide_render = True
            hidden = True
        key = round(min(tt, max(REVEAL.values()) + 1.5), 2)
        if key != ov_set:                            # lifted: from far away the floor shows through a plane at z=0.02
            sc.set_trail_image(overview(tt), E4[0] - FO.SZ // 2, E4[1] - FO.SZ // 2, glow=0.15, z=0.4); ov_set = key
    sc.set_camera(cam[0], cam[1], cam[2], cam[5], cam[3], cam[4])
    bpy.context.view_layer.update()
    rec = dict(joe=to_screen(jx + 0.5, jy + 0.5, 1.4), mustard=to_screen(c - 3.5, c + 0.5, 1.3), stick=to_screen(c - 2.6, c + 0.9, 1.2),
               tree=to_screen(c + 1.0, c, 2.6), red=to_screen(hw[0], -hw[1], hw[2]), both=to_screen(c + 5.0, c + 0.5, 1.3),
               tyre=to_screen(c + 7.5, c + 0.8, 0.4), flask=to_screen(c + 6.3, c + 2.3, 1.0), light=round(light_at(tt), 2), snow=snow)
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
