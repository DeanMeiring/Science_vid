"""A small farm backdrop for the newer episodes (Dean, Oct 2026: "can we have a small background?"):
rolling hills on the horizon, trees, a wooden fence, a silo, clouds, and a sky that fades from
pale at the horizon to deeper blue overhead.

Grid squares as in scene.py (x right, y towards the camera; the camera usually looks towards -y,
so "behind" means smaller y). Everything here is decoration: nothing the experiments count.
"""
import math
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

def add_backdrop(sc, cx, cy, yard=None):
    """All of it round a yard centred on (cx, cy). yard: (x0, y0, x1, y1) of the working area (kept
    clear of trees, fenced at the back and sides)."""
    sky_gradient(sc); add_hills(sc, cx, cy); add_clouds(sc, cx, cy)
    add_trees(sc, cx, cy, keep_clear=yard and (yard[0] - 6, yard[1] - 14, yard[2] + 6, yard[3] + 30))
    if yard: add_fence(sc, yard[0] - 2, yard[1] - 2, yard[2] + 2, yard[3] + 2)
