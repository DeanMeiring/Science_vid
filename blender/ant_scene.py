"""Experiment #1 (Langton's Ant) as a Blender scene: renders one still frame.

Usage (Blender runs the script; arguments go after "--"):
  blender -b -P blender/ant_scene.py -- --step 12 --theme farm
  blender -b -P blender/ant_scene.py -- --step 5665 --theme ant --scale 100
  blender -b -P blender/ant_scene.py -- --step 12 --save renders/farm.blend

Themes (same rules, different skin):
  ant   white squares and raised navy blocks; fresh flips glow pink (like prototypes/ant_3d.py)
  farm  a little farmer on a grass field: on grass he turns right and digs it into dirt,
        on dirt he turns left and it grows back to grass

Camera as in the prototype: pitch 54 deg, yaw orbit, zoom fits every square touched.
One mesh per cell kind is instanced on points (geometry nodes), so the scene stays light.
Captions and counters stay in Pillow and get laid over the frames later.

Kind to the laptop by default: low process priority, 4 render threads, half size.
"""
import argparse, ctypes, math, sys, time
from pathlib import Path
import numpy as np
import bpy, bmesh
from mathutils import Vector

ROOT = Path(__file__).resolve().parent.parent
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--step", type=int, default=12)
ap.add_argument("--theme", choices=["ant", "farm"], default="farm")
ap.add_argument("--engine", choices=["eevee", "cycles"], default="eevee")
ap.add_argument("--samples", type=int, default=0, help="0 = engine default (eevee 16, cycles 32)")
ap.add_argument("--scale", type=int, default=50, help="resolution %% (100 = 1080x1920)")
ap.add_argument("--threads", type=int, default=4)
ap.add_argument("--yaw", type=float, default=0.0, help="orbit angle in degrees (-18..18 over the video)")
ap.add_argument("--heat-len", type=float, default=0.0, help="fresh-flip trail length in steps (0 = guess)")
ap.add_argument("--repeat", type=int, default=1, help="renders to time (the first includes shader compile)")
ap.add_argument("--out", default="")
ap.add_argument("--save", default="", help="also save the .blend here")
args = ap.parse_args(argv)

if sys.platform == "win32":   # below-normal priority so the laptop stays usable
    ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)

W, H = 1080, 1920
PITCH = math.radians(54)
GAP = 0.05          # gap around each block
FOC = 1500.0        # focal length in pixels at 1080 wide, as in the prototype
BOARD_Y = 1000      # pixel row the camera target lands on
BOX = 900

def lin(rgb):
    """sRGB 0-255 -> linear 0-1 (Blender works in linear)."""
    c = np.array(rgb, float) / 255
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return (*c, 1.0)

THEMES = {
    # floor: "white" squares; block: "black" squares; *_fresh: just flipped
    "ant": dict(floor=(240, 242, 249), floor_fresh=(255, 70, 160), line=(150, 158, 185), line_k=0.22,
                block=(30, 34, 62), block_fresh=(255, 70, 160), block_h=0.42, emit=0.6,
                world=(214, 220, 236), sun=2.0, sun_col=(255, 255, 255), dot=(255, 150, 40)),
    "farm": dict(floor=(104, 170, 62), floor_fresh=(150, 214, 70), line=(70, 128, 40), line_k=0.35,
                 block=(120, 80, 48), block_fresh=(84, 52, 30), block_h=0.14, emit=0.0,
                 world=(178, 210, 240), sun=2.6, sun_col=(255, 244, 222), dot=(255, 214, 64)),
}
T = THEMES[args.theme]
HB = T["block_h"]

# ---------------- simulation (same rule and orientation as the prototype) ----------------
N = 700
DX = [0, 1, 0, -1]; DY = [-1, 0, 1, 0]
grid = np.zeros((N, N), np.uint8)
last = np.full((N, N), -10 ** 9, np.int64)
x = y = N // 2; d = 0
for s in range(args.step):
    d = (d + 1) % 4 if grid[y, x] == 0 else (d - 1) % 4   # white/grass: right, black/dirt: left
    grid[y, x] ^= 1; last[y, x] = s
    x += DX[d]; y += DY[d]
touched = last > -10 ** 9
if touched.any():
    ty, tx = np.nonzero(touched)
    bx0, bx1 = min(tx.min(), x), max(tx.max(), x); by0, by1 = min(ty.min(), y), max(ty.max(), y)
else:
    bx0 = bx1 = x; by0 = by1 = y

# camera fit, as in the prototype (no smoothing for a still)
span = max(bx1 - bx0, by1 - by0) + 1 + (3 if args.step < 30 else 8)
s_px = min(140.0, BOX / span)
cx = (bx0 + bx1 + 1) / 2; cy = (by0 + by1 + 1) / 2
heat_len = args.heat_len or (1.2 if args.step < 30 else 26.0 if args.step > 9977 else 120.0)

# ---------------- scene ----------------
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.resolution_x, sc.render.resolution_y = W, H
sc.render.resolution_percentage = args.scale
sc.render.threads_mode = "FIXED"; sc.render.threads = args.threads
sc.view_settings.view_transform = "Standard"
sc.view_settings.look = "None"
rng = np.random.default_rng(1)

def material(name, color, rough=0.55, emit=None):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = color
    b.inputs["Roughness"].default_value = rough
    if emit:
        b.inputs["Emission Color"].default_value = emit[0]; b.inputs["Emission Strength"].default_value = emit[1]
    return m, b

def node(nt, kind, **ops):
    n = nt.nodes.new(kind)
    for k, v in ops.items(): setattr(n, k, v)
    return n

def mix(nt, fac, a, b):
    """RGBA mix node; a/b/fac are sockets or constant colours / numbers."""
    m = node(nt, "ShaderNodeMix", data_type="RGBA")
    for name, v in (("Factor", fac), ("A", a), ("B", b)):
        if isinstance(v, bpy.types.NodeSocket): nt.links.new(v, m.inputs[name])
        else: m.inputs[name].default_value = v
    return m.outputs["Result"]

# world: soft ambient (sky blue for the farm)
world = bpy.data.worlds.new("World"); sc.world = world; world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = lin(T["world"])
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.35

# sun from back-left, like the prototype's LIGHT (grid y is flipped into world -Y)
L = Vector((-0.45, 0.65, 1.0)).normalized()
sun_d = bpy.data.lights.new("Sun", "SUN"); sun_d.energy = T["sun"]; sun_d.angle = math.radians(12)
sun_d.color = lin(T["sun_col"])[:3]
sun = bpy.data.objects.new("Sun", sun_d); sc.collection.objects.link(sun)
sun.rotation_euler = L.to_track_quat("Z", "Y").to_euler()

# floor with grid lines that fade out as the camera pulls back
fm, fb = material("Floor", lin(T["floor"]), rough=0.85)
nt = fm.node_tree
tc = node(nt, "ShaderNodeTexCoord"); sep = node(nt, "ShaderNodeSeparateXYZ")
nt.links.new(tc.outputs["Object"], sep.inputs[0])
line_w = 0.025 * max(1.0, 30 / s_px)
lines = []
for axis in ("X", "Y"):
    fr = node(nt, "ShaderNodeMath", operation="FRACT"); nt.links.new(sep.outputs[axis], fr.inputs[0])
    dist = node(nt, "ShaderNodeMath", operation="PINGPONG"); dist.inputs[1].default_value = 0.5
    nt.links.new(fr.outputs[0], dist.inputs[0])
    lt = node(nt, "ShaderNodeMath", operation="LESS_THAN"); lt.inputs[1].default_value = line_w
    nt.links.new(dist.outputs[0], lt.inputs[0]); lines.append(lt)
mx = node(nt, "ShaderNodeMath", operation="MAXIMUM")
nt.links.new(lines[0].outputs[0], mx.inputs[0]); nt.links.new(lines[1].outputs[0], mx.inputs[1])
fade = node(nt, "ShaderNodeMath", operation="MULTIPLY")
fade.inputs[1].default_value = T["line_k"] * min(1.0, max(0.0, (s_px - 9) / 18))
nt.links.new(mx.outputs[0], fade.inputs[0])
base = lin(T["floor"])
if args.theme == "farm":
    # each grass square a slightly different green, like a mown field
    fl = node(nt, "ShaderNodeVectorMath", operation="FLOOR"); nt.links.new(tc.outputs["Object"], fl.inputs[0])
    wn = node(nt, "ShaderNodeTexWhiteNoise", noise_dimensions="3D"); nt.links.new(fl.outputs[0], wn.inputs["Vector"])
    vr = node(nt, "ShaderNodeMath", operation="MULTIPLY"); vr.inputs[1].default_value = 0.6
    nt.links.new(wn.outputs["Value"], vr.inputs[0])
    base = mix(nt, vr.outputs[0], lin((92, 156, 54)), lin((126, 186, 70)))
nt.links.new(mix(nt, fade.outputs[0], base, lin(T["line"])), fb.inputs["Base Color"])
bpy.ops.mesh.primitive_plane_add(size=4000, location=(0, 0, 0))
floor = bpy.context.object; floor.name = "Floor"; floor.data.materials.append(fm)

# one block mesh (bevelled, base at z=0, height 1 so instances scale it to HB)
bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
for v in bm.verts:
    v.co.x *= 1 - 2 * GAP; v.co.y *= 1 - 2 * GAP; v.co.z += 0.5
bmesh.ops.bevel(bm, geom=list(bm.edges), offset=0.035 if args.theme == "ant" else 0.06,
                segments=2 if args.theme == "ant" else 3, affect="EDGES", profile=0.5)
bme = bpy.data.meshes.new("Block"); bm.to_mesh(bme); bm.free()
block = bpy.data.objects.new("Block", bme); sc.collection.objects.link(block)
block.hide_render = True; block.hide_viewport = True

# cell material: floor tile or block, each fading to its "fresh" colour by heat
bmat, bb = material("Block", lin(T["block"]), rough=0.45 if args.theme == "ant" else 0.95)
nt = bmat.node_tree
a_heat = node(nt, "ShaderNodeAttribute", attribute_type="INSTANCER", attribute_name="heat")
a_blk = node(nt, "ShaderNodeAttribute", attribute_type="INSTANCER", attribute_name="block")
blk_col = mix(nt, a_heat.outputs["Fac"], lin(T["block"]), lin(T["block_fresh"]))
if args.theme == "farm":
    # ploughed furrows across the dirt, a bit of grain, slightly bumpy
    tcb = node(nt, "ShaderNodeTexCoord")
    wave = node(nt, "ShaderNodeTexWave", wave_type="BANDS", bands_direction="X")
    wave.inputs["Scale"].default_value = 2.2; wave.inputs["Distortion"].default_value = 1.5
    nt.links.new(tcb.outputs["Object"], wave.inputs["Vector"])
    nz = node(nt, "ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 18
    nt.links.new(tcb.outputs["Object"], nz.inputs["Vector"])
    grain = node(nt, "ShaderNodeMath", operation="MULTIPLY"); grain.inputs[1].default_value = 0.5
    nt.links.new(nz.outputs["Fac"], grain.inputs[0])
    blk_col = mix(nt, grain.outputs[0], blk_col, lin((70, 44, 26)))
    bump = node(nt, "ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.9
    nt.links.new(wave.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], bb.inputs["Normal"])
flo_col = mix(nt, a_heat.outputs["Fac"], lin(T["floor"]), lin(T["floor_fresh"]))
nt.links.new(mix(nt, a_blk.outputs["Fac"], flo_col, blk_col), bb.inputs["Base Color"])
if T["emit"]:
    bb.inputs["Emission Color"].default_value = lin(T["block_fresh"])
    em = node(nt, "ShaderNodeMath", operation="MULTIPLY"); em.inputs[1].default_value = T["emit"]
    nt.links.new(a_heat.outputs["Fac"], em.inputs[0]); nt.links.new(em.outputs[0], bb.inputs["Emission Strength"])
bme.materials.append(bmat)

def instancer(name, src, pts, attrs):
    """Points mesh + geometry nodes that put `src` on every point (scaled by the 'scale' attribute)."""
    n = len(pts)
    pm = bpy.data.meshes.new(name); pm.vertices.add(n)
    pm.vertices.foreach_set("co", np.asarray(pts, np.float32).ravel())
    for k, v in attrs.items():
        v = np.asarray(v, np.float32)
        if v.ndim == 2: pm.attributes.new(k, "FLOAT_VECTOR", "POINT").data.foreach_set("vector", v.ravel())
        else: pm.attributes.new(k, "FLOAT", "POINT").data.foreach_set("value", v)
    ob = bpy.data.objects.new(name, pm); sc.collection.objects.link(ob)
    ng = bpy.data.node_groups.new(name + "Nodes", "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    gi = ng.nodes.new("NodeGroupInput"); go = ng.nodes.new("NodeGroupOutput")
    inst = ng.nodes.new("GeometryNodeInstanceOnPoints")
    oi = ng.nodes.new("GeometryNodeObjectInfo"); oi.inputs["Object"].default_value = src
    ng.links.new(gi.outputs["Geometry"], inst.inputs["Points"])
    ng.links.new(oi.outputs["Geometry"], inst.inputs["Instance"])
    if "scale" in attrs:
        na = ng.nodes.new("GeometryNodeInputNamedAttribute"); na.data_type = "FLOAT_VECTOR"
        na.inputs["Name"].default_value = "scale"; ng.links.new(na.outputs["Attribute"], inst.inputs["Scale"])
    if "rot" in attrs:
        nr = ng.nodes.new("GeometryNodeInputNamedAttribute"); nr.data_type = "FLOAT_VECTOR"
        nr.inputs["Name"].default_value = "rot"; ng.links.new(nr.outputs["Attribute"], inst.inputs["Rotation"])
    ng.links.new(inst.outputs["Instances"], go.inputs["Geometry"])
    ob.modifiers.new("Inst", "NODES").node_group = ng
    return ob

# cells: one per block square (raised) or recently flipped floor square (flat tile)
heat = np.exp(-(args.step - last) / heat_len) * 0.8
sel = (grid == 1) | (touched & (heat > 0.05))
py_, px_ = np.nonzero(sel)
n = len(px_)
is_blk = grid[py_, px_].astype(np.float32)
pts = np.stack([px_ + 0.5, -(py_ + 0.5), np.zeros(n)], -1)
scl = np.stack([np.ones(n), np.ones(n), np.where(is_blk > 0, HB, 0.006)], -1)
instancer("Cells", block, pts, dict(scale=scl, heat=heat[py_, px_], block=is_blk))

# grass tufts on grass squares near the camera (only while zoomed in enough to see them)
if args.theme == "farm" and s_px > 30:
    bm = bmesh.new()
    for k in range(3):   # three crossed blades
        a = k * math.pi / 3; ca, sa = math.cos(a) * 0.022, math.sin(a) * 0.022
        v0 = bm.verts.new((-ca, -sa, 0)); v1 = bm.verts.new((ca, sa, 0)); v2 = bm.verts.new((0.01, 0.006, 0.16))
        bm.faces.new((v0, v1, v2))
    tm = bpy.data.meshes.new("Tuft"); bm.to_mesh(tm); bm.free()
    tuft = bpy.data.objects.new("Tuft", tm); sc.collection.objects.link(tuft)
    tuft.hide_render = True; tuft.hide_viewport = True
    gm, gb = material("Grass", lin((96, 170, 52)), rough=0.7)
    gnt = gm.node_tree
    oinf = node(gnt, "ShaderNodeObjectInfo")
    gcol = mix(gnt, oinf.outputs["Random"], lin((110, 180, 60)), lin((175, 225, 95)))
    gnt.links.new(gcol, gb.inputs["Base Color"])
    gnt.links.new(gcol, gb.inputs["Emission Color"])   # thin blades lit from behind go black; lift them
    gb.inputs["Emission Strength"].default_value = 0.35
    tm.materials.append(gm)
    R = int(1.3 * max(W, H) / s_px) + 2
    gx, gy = np.meshgrid(np.arange(int(cx) - R, int(cx) + R), np.arange(int(cy) - R, int(cy) + R))
    gx, gy = gx.ravel(), gy.ravel()
    ok = (gx >= 0) & (gx < N) & (gy >= 0) & (gy < N)
    gx, gy = gx[ok], gy[ok]
    gx, gy = gx[grid[gy, gx] == 0], gy[grid[gy, gx] == 0]
    per = 8
    tx_ = np.repeat(gx, per) + rng.uniform(0.08, 0.92, gx.size * per)
    ty_ = np.repeat(gy, per) + rng.uniform(0.08, 0.92, gx.size * per)
    m = tx_.size
    tpts = np.stack([tx_, -ty_, np.zeros(m)], -1)
    s = rng.uniform(0.7, 1.4, m)
    instancer("Tufts", tuft, tpts, dict(scale=np.stack([s, s, s * rng.uniform(0.8, 1.3, m)], -1),
                                         rot=np.stack([rng.normal(0, 0.15, m), rng.normal(0, 0.15, m),
                                                       rng.uniform(0, 2 * math.pi, m)], -1)))

# ---------------- the character (stands on its square, faces where it will step) ----------------
hx, hy = DX[d], -DY[d]
root = bpy.data.objects.new("Walker", None); sc.collection.objects.link(root)
root.location = (x + 0.5, -(y + 0.5), HB if grid[y, x] == 1 else 0.0)
root.rotation_euler = (0, 0, math.atan2(hy, hx))
if args.theme == "farm": root.scale = (1.6, 1.6, 1.6)   # chunky enough to read on a phone
MATS = {}
def mat(name, rgb, rough=0.6):
    if name not in MATS: MATS[name] = material(name, lin(rgb), rough=rough)[0]
    return MATS[name]
def part(kind, loc, scale=(1, 1, 1), m=None, rot=None, **kw):
    getattr(bpy.ops.mesh, f"primitive_{kind}_add")(location=loc, **kw)
    o = bpy.context.object; o.scale = scale; o.parent = root
    if rot is not None: o.rotation_euler = rot
    o.data.materials.append(m); bpy.ops.object.shade_smooth()
    return o
def stick(a, b, r, m, verts=8):
    a, b = Vector(a), Vector(b); v = b - a
    return part("cylinder", (a + b) / 2, m=m, rot=v.to_track_quat("Z", "Y").to_euler(),
                radius=r, depth=v.length, vertices=verts)

if s_px <= 16:   # too small to see: a glowing dot instead
    dm, _ = material("Dot", lin(T["dot"]), emit=(lin(T["dot"]), 6.0))
    bpy.ops.mesh.primitive_uv_sphere_add(radius=7 / s_px, location=(0, 0, 0.2))
    dot = bpy.context.object; dot.parent = root; dot.data.materials.append(dm)
elif args.theme == "ant":
    am = mat("Ant", (52, 28, 14), 0.3)
    for o_, r, z in ((-0.3, 0.17, 0.16), (0.0, 0.11, 0.15), (0.24, 0.13, 0.16)):
        part("uv_sphere", (o_, 0, z), (1.15, 1, 0.9), am, radius=r, segments=24, ring_count=12)
    for side in (-1, 1):
        for o_ in (-0.18, 0.0, 0.18):
            stick((o_, 0, 0.12), (o_ * 1.6, side * 0.32, 0.0), 0.018, am)
        stick((0.33, 0, 0.2), (0.55, side * 0.18, 0.32), 0.012, am, 6)
else:
    # a small chunky farmer (about 0.75 squares tall), built facing +X
    jeans = mat("Overalls", (52, 92, 170)); shirt = mat("Shirt", (210, 52, 44))
    skin = mat("Skin", (240, 190, 150), 0.5); straw = mat("Straw", (232, 196, 100), 0.8)
    boot = mat("Boots", (70, 44, 30)); wood = mat("Wood", (150, 104, 60)); metal = mat("Metal", (170, 175, 185), 0.3)
    band = mat("HatBand", (170, 40, 36))
    for side in (-1, 1):
        part("uv_sphere", (0.03, side * 0.075, 0.035), (1.5, 1, 0.7), boot, radius=0.05, segments=16, ring_count=8)
        part("cylinder", (0, side * 0.075, 0.13), m=jeans, radius=0.05, depth=0.17, vertices=16)
    part("uv_sphere", (0, 0, 0.3), (0.85, 1, 1.05), jeans, radius=0.15, segments=24, ring_count=12)   # belly
    part("uv_sphere", (0.01, 0, 0.36), (0.8, 0.95, 0.8), shirt, radius=0.14, segments=24, ring_count=12)  # chest
    for side in (-1, 1):   # overall straps
        part("cube", (0.1, side * 0.06, 0.38), (0.012, 0.022, 0.07), jeans)
        # arms: right hand holds the hoe in front, left swings back
        hand = (0.17, side * 0.14, 0.27) if side > 0 else (-0.04, -0.17, 0.25)
        stick((0.0, side * 0.13, 0.42), hand, 0.035, shirt)
        part("uv_sphere", hand, m=skin, radius=0.035, segments=12, ring_count=6)
    part("uv_sphere", (0.01, 0, 0.56), m=skin, radius=0.11, segments=24, ring_count=12)   # head
    part("uv_sphere", (0.115, 0, 0.55), m=skin, radius=0.025, segments=12, ring_count=6)  # nose
    eye = mat("Eye", (20, 20, 24), 0.2)
    for side in (-1, 1):
        part("uv_sphere", (0.095, side * 0.04, 0.585), m=eye, radius=0.014, segments=10, ring_count=6)
    part("cylinder", (0, 0, 0.63), m=straw, radius=0.2, depth=0.02, vertices=32)          # hat brim
    part("cylinder", (0, 0, 0.68), m=straw, radius=0.1, depth=0.09, vertices=24)          # hat crown
    part("cylinder", (0, 0, 0.655), m=band, radius=0.102, depth=0.025, vertices=24)
    # hoe: handle from the hand down to the ground in front, blade at the end
    stick((0.1, 0.14, 0.45), (0.4, 0.14, 0.02), 0.014, wood)
    part("cube", (0.41, 0.14, 0.03), (0.02, 0.06, 0.035), metal)

glow_d = bpy.data.lights.new("Glow", "POINT"); glow_d.energy = 6.0 * max(1, 30 / s_px) ** 2
glow_d.color = (1.0, 0.6, 0.2) if args.theme == "ant" else (1.0, 0.9, 0.7); glow_d.shadow_soft_size = 0.2
glow = bpy.data.objects.new("Glow", glow_d); sc.collection.objects.link(glow)
glow.parent = root; glow.location = (0, 0, 0.9)

# camera: pitch 54, yaw orbit, distance set by the zoom (pixels per cell)
cam_d = bpy.data.cameras.new("Cam"); cam_d.sensor_fit = "HORIZONTAL"; cam_d.sensor_width = 36
cam_d.lens = FOC * 36 / W; cam_d.clip_end = 10000
cam_d.shift_y = (BOARD_Y - H / 2) / H
cam = bpy.data.objects.new("Cam", cam_d); sc.collection.objects.link(cam); sc.camera = cam
yaw = math.radians(args.yaw)
fwd = Vector((math.sin(yaw) * math.cos(PITCH), math.cos(yaw) * math.cos(PITCH), -math.sin(PITCH)))
cam.location = Vector((cx, -cy, 0)) - fwd * (FOC / s_px)
cam.rotation_euler = (math.pi / 2 - PITCH, 0, -yaw)

# ---------------- engine ----------------
if args.engine == "cycles":
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = args.samples or 32
    sc.cycles.use_denoising = True; sc.cycles.denoiser = "OPENIMAGEDENOISE"
    sc.cycles.max_bounces = 4; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 2
    sc.cycles.transmission_bounces = 0; sc.cycles.volume_bounces = 0
else:
    engines = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
    sc.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in engines else "BLENDER_EEVEE"
    sc.eevee.taa_render_samples = args.samples or 16

out = args.out or str(ROOT / "renders" / f"{args.theme}_{args.engine}_step{args.step}_{args.scale}.png")
Path(out).parent.mkdir(parents=True, exist_ok=True)
sc.render.filepath = out
sc.render.image_settings.file_format = "PNG"
if args.save:
    Path(args.save).parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(Path(args.save).resolve()))

times = []
for _ in range(max(1, args.repeat)):
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    times.append(time.time() - t0)
print(f"BENCH theme={args.theme} engine={args.engine} step={args.step} cells={n} zoom={s_px:.1f}px "
      f"res={W * args.scale // 100}x{H * args.scale // 100} threads={args.threads} "
      f"times={' '.join(f'{t:.1f}s' for t in times)} -> {out}", flush=True)
