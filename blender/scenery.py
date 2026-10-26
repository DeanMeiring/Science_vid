"""A small farm backdrop for the newer episodes (Dean, Oct 2026: "can we have a small background?"):
rolling hills on the horizon, trees, a wooden fence, a silo, clouds, and a sky that fades from
pale at the horizon to deeper blue overhead.

Grid squares as in scene.py (x right, y towards the camera; the camera usually looks towards -y,
so "behind" means smaller y). Everything here is decoration: nothing the experiments count.
"""
import math
from pathlib import Path
import bpy
import numpy as np
import scene as S

def _mat(name, rgb, rough=0.8, emit=None):
    if name in bpy.data.materials: return bpy.data.materials[name]
    return S._material(name, S.lin(rgb), rough=rough, emit=emit)[0]

def _flat(o):
    """Low-poly look: flat shading."""
    for p in o.data.polygons: p.use_smooth = False

def sky_gradient(sc, horizon=(206, 228, 246), top=(92, 156, 232)):
    """What the camera sees above the ground: pale at the horizon, deeper blue overhead
    (replaces scene.set_sky's flat colour; the scene is still lit by the normal world colour)."""
    sc.set_sky(top)
    wnt = sc.sc.world.node_tree
    tc = S._node(wnt, "ShaderNodeTexCoord"); sep = S._node(wnt, "ShaderNodeSeparateXYZ")
    wnt.links.new(tc.outputs["Generated"], sep.inputs[0])
    ramp = S._node(wnt, "ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.0; ramp.color_ramp.elements[0].color = S.lin(horizon)
    ramp.color_ramp.elements[1].position = 0.45; ramp.color_ramp.elements[1].color = S.lin(top)
    wnt.links.new(sep.outputs["Z"], ramp.inputs["Fac"]); wnt.links.new(ramp.outputs["Color"], sc._sky.inputs["Color"])

def add_hills(sc, cx, cy, seed=1):
    """A ring of rolling hills far behind (and a little to the sides of) (cx, cy)."""
    r = np.random.default_rng(seed)
    greens = [(88, 150, 64), (76, 138, 58), (98, 160, 72), (70, 128, 54)]
    for k in range(9):
        a = math.radians(-150 + k * 15 + r.uniform(-5, 5))             # spread across the far side
        d = r.uniform(70, 110)
        x, y = cx + d * math.cos(a), cy + d * math.sin(a)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=32, ring_count=16, location=(x, -y, -r.uniform(6, 10)))
        o = bpy.context.object; o.scale = (r.uniform(25, 45), r.uniform(18, 30), r.uniform(12, 20))
        o.data.materials.append(_mat(f"Hill{k % 4}", greens[k % 4], 0.95)); bpy.ops.object.shade_smooth()

def add_tree(sc, x, y, size=1.0, kind="round", seed=0):
    """A low-poly tree: a trunk and leafy blobs (round) or stacked cones (pine)."""
    r = np.random.default_rng(seed)
    bark = _mat("Bark", (104, 72, 46), 0.9)
    leaves = [_mat("Leaves0", (74, 140, 58)), _mat("Leaves1", (92, 156, 66)), _mat("Leaves2", (62, 120, 52))]
    bpy.ops.mesh.primitive_cylinder_add(radius=0.18 * size, depth=1.6 * size, vertices=8, location=(x + 0.5, -(y + 0.5), 0.8 * size))
    bpy.context.object.data.materials.append(bark)
    if kind == "round":
        for i in range(3):
            dx, dy, dz = r.uniform(-0.45, 0.45, 2).tolist() + [r.uniform(1.6, 2.3)]
            bpy.ops.mesh.primitive_ico_sphere_add(radius=r.uniform(0.7, 0.95) * size, subdivisions=1,
                                                  location=(x + 0.5 + dx * size, -(y + 0.5) + dy * size, dz * size))
            o = bpy.context.object; o.data.materials.append(leaves[i % 3]); _flat(o)
    else:
        for i in range(3):
            bpy.ops.mesh.primitive_cone_add(radius1=(0.95 - 0.22 * i) * size, radius2=0, depth=1.2 * size, vertices=9,
                                            location=(x + 0.5, -(y + 0.5), (1.3 + 0.6 * i) * size))
            o = bpy.context.object; o.data.materials.append(leaves[2]); _flat(o)

def add_trees(sc, cx, cy, n=18, r0=16, r1=45, keep_clear=None, seed=2):
    """Trees scattered round (cx, cy), between r0 and r1 squares away, mostly behind and to the sides.
    keep_clear: (x0, y0, x1, y1) where no tree may stand."""
    r = np.random.default_rng(seed); placed = 0
    while placed < n:
        a = r.uniform(-math.pi * 0.95, -math.pi * 0.05) if r.random() < 0.8 else r.uniform(0, 2 * math.pi)
        d = r.uniform(r0, r1); x, y = cx + d * math.cos(a), cy + d * math.sin(a)
        if keep_clear and keep_clear[0] <= x <= keep_clear[2] and keep_clear[1] <= y <= keep_clear[3]: continue
        add_tree(sc, x, y, size=r.uniform(1.2, 2.0), kind="pine" if r.random() < 0.35 else "round", seed=placed)
        placed += 1

def add_fence(sc, x0, y0, x1, y1, sides=("back", "left", "right"), gap=1.6):
    """A wooden post-and-rail fence along the chosen sides of the box (x0, y0)-(x1, y1)."""
    wood = _mat("FenceWood", (150, 110, 74), 0.85)
    def post(x, y):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x, -y, 0.5)); o = bpy.context.object
        o.scale = (0.14, 0.14, 1.0); o.data.materials.append(wood)
    def rail(xa, ya, xb, yb, z):
        bpy.ops.mesh.primitive_cube_add(size=1, location=((xa + xb) / 2, -(ya + yb) / 2, z)); o = bpy.context.object
        o.scale = (max(abs(xb - xa), 0.08), max(abs(yb - ya), 0.08), 0.09); o.data.materials.append(wood)
    runs = {"back": ((x0, y0), (x1, y0)), "front": ((x0, y1), (x1, y1)), "left": ((x0, y0), (x0, y1)), "right": ((x1, y0), (x1, y1))}
    for s_ in sides:
        (xa, ya), (xb, yb) = runs[s_]; L = math.hypot(xb - xa, yb - ya); k = max(1, int(L / gap))
        for i in range(k + 1): post(xa + (xb - xa) * i / k, ya + (yb - ya) * i / k)
        for z in (0.45, 0.8): rail(xa, ya, xb, yb, z)

def add_silo(sc, x, y, height=6.0, radius=1.2):
    body, roof = _mat("SiloBody", (196, 200, 204), 0.5), _mat("SiloRoof", (176, 46, 38), 0.6)
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=height, vertices=32, location=(x + 0.5, -(y + 0.5), height / 2))
    o = bpy.context.object; o.data.materials.append(body); bpy.ops.object.shade_smooth()
    for z in np.arange(0.8, height, 1.2):                                   # metal bands
        bpy.ops.mesh.primitive_torus_add(major_radius=radius + 0.02, minor_radius=0.04, location=(x + 0.5, -(y + 0.5), z))
        bpy.context.object.data.materials.append(_mat("SiloBand", (150, 154, 160), 0.4))
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius * 1.04, segments=32, ring_count=16, location=(x + 0.5, -(y + 0.5), height))
    d = bpy.context.object; d.scale = (1, 1, 0.7); d.data.materials.append(roof); bpy.ops.object.shade_smooth()

def add_clouds(sc, cx, cy, n=7, seed=3):
    """Puffy white clouds high up, far behind."""
    white = _mat("Cloud", (255, 255, 255), 0.9, emit=(S.lin((255, 255, 255)), 0.6))
    r = np.random.default_rng(seed)
    for k in range(n):
        x, y, z = cx + r.uniform(-90, 90), cy - r.uniform(60, 130), r.uniform(28, 45)
        for i in range(5):
            bpy.ops.mesh.primitive_ico_sphere_add(radius=r.uniform(3, 6), subdivisions=2,
                                                  location=(x + r.uniform(-7, 7), -(y + r.uniform(-2, 2)), z + r.uniform(-1, 2)))
            o = bpy.context.object; o.scale = (1.3, 1, 0.6); o.data.materials.append(white); bpy.ops.object.shade_smooth()

def add_backdrop(sc, cx, cy, yard=None, use_kenney=False):
    """All of it round a yard centred on (cx, cy). yard: (x0, y0, x1, y1) of the working area (kept
    clear of trees, fenced at the back and sides). use_kenney: Kenney's trees, bushes, flowers and
    rocks instead of the home-made trees (needs the kits in assets/thirdparty/kenney); "detailed": our
    detailed trees with Kenney's bushes and flowers."""
    sky_gradient(sc); add_hills(sc, cx, cy); add_clouds(sc, cx, cy)
    clear = yard and (yard[0] - 6, yard[1] - 14, yard[2] + 6, yard[3] + 30)
    if use_kenney == "detailed":                                   # our detailed trees, Kenney's bushes and flowers
        detailed_trees(cx, cy, keep_clear=clear)
        if yard: kenney_dressing(cx, cy, yard)
    elif use_kenney:
        kenney_trees(cx, cy, keep_clear=clear)
        if yard: kenney_dressing(cx, cy, yard)
    else: add_trees(sc, cx, cy, keep_clear=clear)
    if yard: add_fence(sc, yard[0] - 2, yard[1] - 2, yard[2] + 2, yard[3] + 2)

# ---------------- Kenney's CC0 models (assets/thirdparty/kenney, never committed) ----------------
KENNEY = Path(__file__).resolve().parent.parent / "assets" / "thirdparty" / "kenney"
_kenney_cache = {}

def _farm_colours(m):
    """Kenney's kit is teal and orange; turn its teal (leaves, grass) into the farm's greens."""
    import colorsys
    if not m or not m.use_nodes or getattr(m, "_farmed", False): return
    for n in m.node_tree.nodes:
        if n.type != "BSDF_PRINCIPLED": continue
        r, g, b, a = n.inputs["Base Color"].default_value
        h, s_, v = colorsys.rgb_to_hsv(r, g, b)
        if 0.38 <= h <= 0.58 and s_ > 0.2:                       # teal / cyan -> leaf green
            n.inputs["Base Color"].default_value = (*colorsys.hsv_to_rgb(0.29 + (h - 0.48) * 0.3, min(1, s_ * 1.1), v * 0.9), a)

def kenney(name, x, y, rot=0.0, scale=1.0, z=0.0, kit="nature"):
    """Place one of Kenney's models (by file name without .glb, e.g. "tree_oak", "barrel") at grid
    (x, y). The model is imported once; later copies share its mesh. Returns the new object."""
    if name not in _kenney_cache:
        folder = KENNEY / ("nature/Models/GLTF format" if kit == "nature" else "survival/Models/GLB format")
        path = folder / f"{name}.glb"
        if not path.exists(): raise FileNotFoundError(f"{path} (download the Kenney kits into assets/thirdparty/kenney)")
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=str(path))
        new = [o for o in bpy.data.objects if o not in before]
        meshes = [o for o in new if o.type == "MESH"]
        bpy.ops.object.select_all(action="DESELECT")
        for o in meshes: o.select_set(True)
        bpy.context.view_layer.objects.active = meshes[0]
        for o in meshes:                                   # bake parents' transforms in, then join into one mesh
            mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
        if len(meshes) > 1: bpy.ops.object.join()
        src = bpy.context.view_layer.objects.active
        for o in new:
            if o != src and o.name in bpy.data.objects: bpy.data.objects.remove(o)
        src.name = f"K_{name}"; src.hide_render = True; src.hide_viewport = True
        for m in src.data.materials: _farm_colours(m)
        _kenney_cache[name] = src
    src = _kenney_cache[name]
    o = bpy.data.objects.new(f"{name}", src.data); sc_ = bpy.context.scene; sc_.collection.objects.link(o)
    o.location = (x + 0.5, -(y + 0.5), z); o.rotation_euler = (0, 0, rot); o.scale = (scale,) * 3
    return o

def kenney_trees(cx, cy, n=22, r0=16, r1=45, keep_clear=None, seed=2):
    """Kenney's trees scattered round (cx, cy), mostly behind and to the sides (like add_trees)."""
    r = np.random.default_rng(seed); kinds = ["tree_oak", "tree_detailed", "tree_default", "tree_fat", "tree_pineRoundA",
                                              "tree_pineDefaultA", "tree_pineRoundC"]
    placed = 0
    while placed < n:
        a = r.uniform(-math.pi * 0.95, -math.pi * 0.05) if r.random() < 0.8 else r.uniform(0, 2 * math.pi)
        d = r.uniform(r0, r1); x, y = cx + d * math.cos(a), cy + d * math.sin(a)
        if keep_clear and keep_clear[0] <= x <= keep_clear[2] and keep_clear[1] <= y <= keep_clear[3]: continue
        kenney(kinds[int(r.integers(0, len(kinds)))], x, y, rot=r.uniform(0, 2 * math.pi), scale=r.uniform(4.0, 6.0))
        placed += 1

def kenney_dressing(cx, cy, yard, seed=4):
    """Bushes, flowers, rocks, stumps and mushrooms round the yard's edge; log stacks by the fence."""
    r = np.random.default_rng(seed); x0, y0, x1, y1 = yard
    small = ["plant_bush", "plant_bushDetailed", "plant_bushLarge", "flower_yellowA", "flower_redA", "flower_purpleB",
             "flower_yellowC", "rock_smallA", "rock_smallC", "stump_round", "mushroom_redGroup", "grass_large"]
    for k in range(60):
        side = int(r.integers(0, 3))
        if side == 0: x, y = r.uniform(x0 - 4, x1 + 4), y0 - r.uniform(2.5, 6)
        elif side == 1: x, y = x0 - r.uniform(2.5, 6), r.uniform(y0, y1 + 6)
        else: x, y = x1 + r.uniform(2.5, 6), r.uniform(y0, y1 + 6)
        nm = small[int(r.integers(0, len(small)))]
        kenney(nm, x, y, rot=r.uniform(0, 2 * math.pi), scale=r.uniform(2.0, 3.2) if "flower" in nm or "grass" in nm else r.uniform(1.8, 2.6))
    kenney("log_stackLarge", x0 + 3, y0 - 1.2, rot=0.1, scale=2.5)


# ---------------- detailed trees (Dean, 23 Oct: "make the trees a bit more detailed") ----------------
def _bark():
    if "BarkDetailed" in bpy.data.materials: return bpy.data.materials["BarkDetailed"]
    mat, b = S._material("BarkDetailed", S.lin((112, 78, 50)), rough=0.95); nt = mat.node_tree
    tc = S._node(nt, "ShaderNodeTexCoord")
    mp = S._node(nt, "ShaderNodeMapping"); mp.inputs["Scale"].default_value = (6.0, 6.0, 1.2)       # long vertical grain
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nz = S._node(nt, "ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 4.0; nz.inputs["Detail"].default_value = 8.0
    nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    nt.links.new(S._mix(nt, nz.outputs["Fac"], S.lin((70, 48, 30)), S.lin((132, 96, 64))), b.inputs["Base Color"])
    bump = S._node(nt, "ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.8
    nt.links.new(nz.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return mat

def _leaves(k):
    """Leaf material k (0-2): a green with leafy speckle and bumps, each a slightly different shade."""
    name = f"LeavesDetailed{k}"
    if name in bpy.data.materials: return bpy.data.materials[name]
    base = [(70, 138, 56), (88, 154, 62), (60, 120, 50)][k]
    mat, b = S._material(name, S.lin(base), rough=0.8); nt = mat.node_tree
    tc = S._node(nt, "ShaderNodeTexCoord")
    vo = S._node(nt, "ShaderNodeTexVoronoi"); vo.inputs["Scale"].default_value = 9.0           # leaf-sized cells
    nt.links.new(tc.outputs["Object"], vo.inputs["Vector"])
    nz = S._node(nt, "ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 2.0
    nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
    col = S._mix(nt, vo.outputs["Distance"], S.lin(tuple(min(255, int(v * 1.25)) for v in base)), S.lin(tuple(int(v * 0.7) for v in base)))
    col = S._mix(nt, nz.outputs["Fac"], col, S.lin(tuple(min(255, int(v * 1.1)) for v in base)))
    nt.links.new(col, b.inputs["Base Color"])
    bump = S._node(nt, "ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.6
    nt.links.new(vo.outputs["Distance"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    return mat

def _tapered(a, b, r0, r1, m, parent=None):
    """A tapering branch from a (radius r0) to b (radius r1)."""
    from mathutils import Vector
    a, b = Vector(a), Vector(b); v = b - a
    bpy.ops.mesh.primitive_cone_add(radius1=r0, radius2=r1, depth=v.length, vertices=10, location=(a + b) / 2)
    o = bpy.context.object; o.rotation_euler = v.to_track_quat("Z", "Y").to_euler(); o.data.materials.append(m)
    o.parent = parent; bpy.ops.object.shade_smooth()
    return o

def _blob(loc, r, m, parent):
    """A leaf cluster: a lumpy, bumpy ball."""
    bpy.ops.mesh.primitive_ico_sphere_add(radius=r, subdivisions=3, location=loc); o = bpy.context.object
    tex = bpy.data.textures.get("LeafLumps") or bpy.data.textures.new("LeafLumps", "CLOUDS")
    tex.noise_scale = 0.35
    d = o.modifiers.new("Lumps", "DISPLACE"); d.texture = tex; d.strength = r * 0.35; d.mid_level = 0.5
    d.texture_coords = "OBJECT"
    o.data.materials.append(m); o.parent = parent; bpy.ops.object.shade_smooth()
    o["leaf_r"] = r                                   # so fruit can be hung on its surface
    return o

def add_detailed_tree(x, y, size=3.0, kind="round", seed=0):
    """A more detailed tree: a flared, tapering trunk with branches and a canopy of lumpy leaf clusters
    (round), or a pine of ragged layered tiers. About `size` squares tall. Returns its root (an empty)."""
    r = np.random.default_rng(seed); bark = _bark()
    root = bpy.data.objects.new("Tree", None); bpy.context.scene.collection.objects.link(root)
    root.location = (x + 0.5, -(y + 0.5), 0); root.rotation_euler = (0, 0, r.uniform(0, 6.3)); root.scale = (size / 3.0,) * 3
    if kind == "pine":
        _tapered((0, 0, 0), (0, 0, 3.0), 0.16, 0.03, bark, root)
        for i in range(5):
            z = 0.7 + i * 0.48; rad = 1.05 - i * 0.18
            bpy.ops.mesh.primitive_cone_add(radius1=rad, radius2=0.02, depth=0.9, vertices=14, location=(0, 0, z + 0.35))
            o = bpy.context.object; o.parent = root; o.data.materials.append(_leaves(2))
            for v in o.data.vertices:                              # ragged edges: tips pulled out and down
                if v.co.z < 0 and (v.index % 2): v.co.x *= 1.18; v.co.y *= 1.18; v.co.z -= 0.08
        return root
    _tapered((0, 0, 0), (0, 0, 0.35), 0.32, 0.2, bark, root)          # the flared foot
    top = (r.uniform(-0.1, 0.1), r.uniform(-0.1, 0.1), 1.6)
    _tapered((0, 0, 0.3), top, 0.2, 0.12, bark, root)
    tips = []
    for k in range(4):                                                  # main branches
        a = k * math.pi / 2 + r.uniform(-0.4, 0.4); h = r.uniform(1.1, 1.5)
        tip = (0.75 * math.cos(a), 0.75 * math.sin(a), h + r.uniform(0.5, 0.8))
        _tapered((top[0] * 0.7, top[1] * 0.7, h), tip, 0.09, 0.03, bark, root); tips.append(tip)
    tips.append((top[0], top[1], 2.4))
    for k, t in enumerate(tips):                                        # leaf clusters round each branch end
        for j in range(4):
            off = r.normal(0, 0.28, 3)
            _blob((t[0] + off[0], t[1] + off[1], t[2] + abs(off[2]) * 0.6), r.uniform(0.45, 0.62), _leaves(int(r.integers(0, 3))), root)
    return root

def detailed_trees(cx, cy, n=22, r0=16, r1=45, keep_clear=None, seed=2):
    """Detailed trees scattered round (cx, cy), mostly behind and to the sides (like add_trees)."""
    r = np.random.default_rng(seed); placed = 0
    while placed < n:
        a = r.uniform(-math.pi * 0.95, -math.pi * 0.05) if r.random() < 0.8 else r.uniform(0, 2 * math.pi)
        d = r.uniform(r0, r1); x, y = cx + d * math.cos(a), cy + d * math.sin(a)
        if keep_clear and keep_clear[0] <= x <= keep_clear[2] and keep_clear[1] <= y <= keep_clear[3]: continue
        add_detailed_tree(x, y, size=r.uniform(4.0, 6.5), kind="pine" if r.random() < 0.35 else "round", seed=placed + 100)
        placed += 1
