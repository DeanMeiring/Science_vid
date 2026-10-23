"""Props for Experiment 7 (pi from a bale of hay): a plank floor, a round hay bale, and straws.

Grid squares as in scene.py (x right, y towards the camera). The floor's planks run along x and are
exactly one straw long wide: the cracks sit at whole numbers of y (y = y0, y0 + 1, ...).
"""
import math
import bmesh, bpy
import numpy as np
from mathutils import Matrix
import scene as S

def _mat(name, rgb, rough=0.6):
    if name in bpy.data.materials: return bpy.data.materials[name]
    return S._material(name, S.lin(rgb), rough=rough)[0]

def _wood(name, rgb):
    """Planks: a warm brown with wood grain running along x."""
    if name in bpy.data.materials: return bpy.data.materials[name]
    mat, b = S._material(name, S.lin(rgb), rough=0.75); nt = mat.node_tree
    tc = S._node(nt, "ShaderNodeTexCoord")
    mp = S._node(nt, "ShaderNodeMapping"); mp.inputs["Scale"].default_value = (0.6, 9.0, 1.0)
    nt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
    nz = S._node(nt, "ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 3.0; nz.inputs["Detail"].default_value = 6.0
    nt.links.new(mp.outputs["Vector"], nz.inputs["Vector"])
    col = S._mix(nt, nz.outputs["Fac"], S.lin(tuple(int(v * 0.72) for v in rgb)), S.lin(rgb))
    oi = S._node(nt, "ShaderNodeObjectInfo")                      # each plank a slightly different shade
    col = S._mix(nt, oi.outputs["Random"], col, S.lin(tuple(min(255, int(v * 1.12)) for v in rgb)))
    kn = S._node(nt, "ShaderNodeTexNoise"); kn.inputs["Scale"].default_value = 1.6; kn.inputs["Detail"].default_value = 2.0
    nt.links.new(tc.outputs["Object"], kn.inputs["Vector"])
    ramp = S._node(nt, "ShaderNodeValToRGB"); ramp.color_ramp.elements[0].position = 0.68; ramp.color_ramp.elements[1].position = 0.74
    nt.links.new(kn.outputs["Fac"], ramp.inputs["Fac"])           # knots: small dark patches here and there
    col = S._mix(nt, ramp.outputs["Color"], col, S.lin(tuple(int(v * 0.5) for v in rgb)))
    nt.links.new(col, b.inputs["Base Color"])
    return mat

FLOOR_Z = 0.06                       # plank tops (above the grass, so the cracks show dark, not green)

def add_floor(sc, x0, y0, w, h, z=FLOOR_Z):
    """A plank floor from (x0, y0), w squares along x and h planks (h squares) along y, top at z.
    Planks are separate boxes with a dark gap between them (the cracks)."""
    wood, gap = _wood("Planks", (176, 128, 82)), _mat("Crack", (40, 28, 20), 0.9)
    root = bpy.data.objects.new("Floor", None); sc.sc.collection.objects.link(root)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x0 + w / 2, -(y0 + h / 2), z - 0.06)); under = bpy.context.object
    under.scale = (w + 0.1, h + 0.1, 0.1); under.data.materials.append(gap); under.parent = root
    for k in range(h):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x0 + w / 2, -(y0 + k + 0.5), z - 0.02)); p = bpy.context.object
        p.scale = (w, 0.95, 0.04); p.data.materials.append(wood); p.parent = root
        bev = p.modifiers.new("Bevel", "BEVEL"); bev.width = 0.012; bev.segments = 2
    # nail heads: two across each plank, every 3 squares along it
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.025, segments=8, ring_count=4); nail = bpy.context.object
    nail.scale = (1, 1, 0.35); nail.data.materials.append(_mat("Nail", (70, 66, 62), 0.4)); nail.hide_render = nail.hide_viewport = True
    gx, gk, side = np.meshgrid(np.arange(x0 + 1.5, x0 + w, 3.0), np.arange(h), (0.2, 0.8), indexing="ij")
    pts = np.stack([gx.ravel(), -(y0 + gk.ravel() + side.ravel()), np.full(gx.size, z)], -1)
    nails = bpy.data.objects.new("Nails", S._points_mesh("Nails", pts, dict(scale=np.ones((len(pts), 3)), rot=np.zeros((len(pts), 3)))))
    sc.sc.collection.objects.link(nails); nails.modifiers.new("Inst", "NODES").node_group = S._instancer_nodes("Nails", nail)
    return root

def _box(cx, cy, cz, sx, sy, sz, m):
    """A box centred at grid (cx, cy), height cz."""
    bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, -cy, cz)); o = bpy.context.object
    o.scale = (sx, sy, sz); o.data.materials.append(m); return o

def add_barn_walls(sc, x0, y0, w, h, height=3.6):
    """A cut-away barn round the floor: plank walls at the back and both sides (none at the front,
    so the camera sees in), posts every 6 squares along the back, a beam along the top."""
    wall, post = _wood("WallPlanks", (150, 104, 66)), _wood("Posts", (110, 76, 48))
    _box(x0 + w / 2, y0 - 0.15, height / 2, w + 0.6, 0.3, height, wall)
    for xs in (x0 - 0.15, x0 + w + 0.15): _box(xs, y0 + h / 2, height / 2, 0.3, h, height, wall)
    for xp in list(np.arange(x0, x0 + w + 0.1, 6.0)) + [x0 + w]:
        _box(xp, y0 - 0.05, height / 2, 0.36, 0.36, height + 0.1, post)
    _box(x0 + w / 2, y0 - 0.05, height + 0.1, w + 0.8, 0.4, 0.3, post)

def add_square_bales(sc, x, y, layers=(3, 2, 1)):
    """A little pyramid of square hay bales (each 1.2 x 0.6 x 0.5, tied with two strings)."""
    hay, twine = bpy.data.materials["Hay"], _mat("Twine", (120, 84, 48), 0.8)
    for row, n in enumerate(layers):
        for k in range(n):
            cx = x + 0.6 + (k - (n - 1) / 2) * 1.25; cz = 0.25 + row * 0.5 + FLOOR_Z
            b = _box(cx, y + 0.5, cz, 1.2, 0.6, 0.5, hay)
            bev = b.modifiers.new("Bevel", "BEVEL"); bev.width = 0.05; bev.segments = 3
            for t in (-0.3, 0.3): _box(cx + t, y + 0.5, cz, 0.03, 0.62, 0.52, twine)

def add_pitchfork(sc, x, y, lean=0.35, facing=0.0):
    wood, steel = _wood("Handle", (168, 120, 72)), _mat("Steel", (150, 154, 160), 0.3)
    root = bpy.data.objects.new("Pitchfork", None); sc.sc.collection.objects.link(root)
    root.location = (x + 0.5, -(y + 0.5), FLOOR_Z); root.rotation_euler = (lean, 0, facing)
    bpy.ops.mesh.primitive_cylinder_add(radius=0.025, depth=1.5, vertices=10, location=(0, 0, 0.95))
    h = bpy.context.object; h.parent = root; h.data.materials.append(wood)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0.22))
    bar = bpy.context.object; bar.scale = (0.03, 0.26, 0.03); bar.parent = root; bar.data.materials.append(steel)
    for t in (-0.12, -0.04, 0.04, 0.12):
        bpy.ops.mesh.primitive_cone_add(radius1=0.012, radius2=0.002, depth=0.36, vertices=8, location=(0, t, 0.04))
        tine = bpy.context.object; tine.rotation_euler = (math.pi, 0, 0); tine.parent = root; tine.data.materials.append(steel)

def add_bucket(sc, x, y):
    wood, band = _wood("Bucket", (150, 104, 60)), _mat("BucketBand", (90, 90, 96), 0.35)
    bpy.ops.mesh.primitive_cone_add(radius1=0.22, radius2=0.28, depth=0.45, vertices=24, end_fill_type="NOTHING",
                                    location=(x + 0.5, -(y + 0.5), 0.225 + FLOOR_Z))
    b = bpy.context.object; b.data.materials.append(wood)
    sol = b.modifiers.new("Solid", "SOLIDIFY"); sol.thickness = 0.03
    bpy.ops.mesh.primitive_cylinder_add(radius=0.22, depth=0.02, vertices=24, location=(x + 0.5, -(y + 0.5), 0.02 + FLOOR_Z))
    bpy.context.object.data.materials.append(wood)
    for zz, r in ((0.08, 0.235), (0.36, 0.27)):
        bpy.ops.mesh.primitive_torus_add(major_radius=r, minor_radius=0.012, location=(x + 0.5, -(y + 0.5), zz + FLOOR_Z))
        bpy.context.object.data.materials.append(band)

def add_lantern(sc, x, y, height=1.6):
    """A lantern hanging from a post, glowing warm."""
    post, metal = _wood("Posts", (110, 76, 48)), _mat("LanternMetal", (40, 40, 44), 0.4)
    glass = S._material("LanternGlass", S.lin((255, 214, 140)), rough=0.2, emit=(S.lin((255, 190, 100)), 6.0))[0]
    _box(x + 0.5, y + 0.5, height / 2 + FLOOR_Z, 0.12, 0.12, height, post)
    _box(x + 0.5, y + 0.5 - 0.18, height - 0.1 + FLOOR_Z, 0.05, 0.36, 0.05, metal)
    lx, ly, lz = x + 0.5, -(y + 0.5) + 0.36, height - 0.32 + FLOOR_Z
    bpy.ops.mesh.primitive_cylinder_add(radius=0.08, depth=0.2, vertices=16, location=(lx, ly, lz)); bpy.context.object.data.materials.append(glass)
    bpy.ops.mesh.primitive_cone_add(radius1=0.1, radius2=0.02, depth=0.08, vertices=16, location=(lx, ly, lz + 0.14))
    bpy.context.object.data.materials.append(metal)
    light = bpy.data.lights.new("LanternLight", "POINT"); light.energy = 30; light.color = (1.0, 0.75, 0.45); light.shadow_soft_size = 0.2
    lo = bpy.data.objects.new("LanternLight", light); sc.sc.collection.objects.link(lo); lo.location = (lx, ly, lz)

def add_bale(sc, x, y, facing=0.0, radius=0.75, length=1.3):
    """A round hay bale lying on its side (its round faces look along `facing`)."""
    if "Hay" not in bpy.data.materials:
        mat, b = S._material("Hay", S.lin((222, 186, 96)), rough=0.95); nt = mat.node_tree
        tc = S._node(nt, "ShaderNodeTexCoord")
        nz = S._node(nt, "ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 40.0; nz.inputs["Detail"].default_value = 8.0
        nt.links.new(tc.outputs["Object"], nz.inputs["Vector"])
        wv = S._node(nt, "ShaderNodeTexWave", wave_type="RINGS"); wv.inputs["Scale"].default_value = 3.0
        wv.inputs["Distortion"].default_value = 4.0; nt.links.new(tc.outputs["Object"], wv.inputs["Vector"])
        m1 = S._node(nt, "ShaderNodeMath", operation="MULTIPLY"); nt.links.new(nz.outputs["Fac"], m1.inputs[0]); nt.links.new(wv.outputs["Fac"], m1.inputs[1])
        col = S._mix(nt, m1.outputs[0], S.lin((246, 214, 128)), S.lin((168, 128, 56)))
        nt.links.new(col, b.inputs["Base Color"])
        bump = S._node(nt, "ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.6
        nt.links.new(nz.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=length, vertices=48, location=(x + 0.5, -(y + 0.5), radius + FLOOR_Z))
    o = bpy.context.object; o.rotation_euler = (0, math.pi / 2, facing); o.data.materials.append(bpy.data.materials["Hay"])
    bev = o.modifiers.new("Bevel", "BEVEL"); bev.width = 0.08; bev.segments = 4
    bpy.ops.object.shade_smooth()
    return o

class Straws:
    """Many straws drawn as one instanced object; each straw has its own colour (paint)."""
    def __init__(self, sc):
        self.sc = sc
        mat, b = S._material("Straw", (1, 1, 1, 1), rough=0.5); nt = mat.node_tree
        at = S._node(nt, "ShaderNodeAttribute", attribute_type="INSTANCER", attribute_name="paint")
        nt.links.new(at.outputs["Color"], b.inputs["Base Color"]); nt.links.new(at.outputs["Color"], b.inputs["Emission Color"])
        aw = S._node(nt, "ShaderNodeAttribute", attribute_type="INSTANCER", attribute_name="glow")
        nt.links.new(aw.outputs["Fac"], b.inputs["Emission Strength"])
        # one straw: 1 square long along x, centred on the origin, gently bent in the floor plane and
        # tapered at both ends (a ring of 6 points at 9 places along it)
        bm = bmesh.new(); rings = []
        for i in range(9):
            u = i / 8; xx = u - 0.5; bend = 0.035 * (1 - (2 * u - 1) ** 2); r = 0.008 + 0.022 * math.sin(math.pi * u) ** 0.5
            rings.append([bm.verts.new((xx, bend + r * math.cos(a), r * math.sin(a) + r)) for a in np.linspace(0, 2 * math.pi, 7)[:-1]])
        for a_, b_ in zip(rings, rings[1:]):
            for j in range(6): bm.faces.new((a_[j], a_[(j + 1) % 6], b_[(j + 1) % 6], b_[j]))
        bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
        me = bpy.data.meshes.new("Straw"); bm.to_mesh(me); bm.free()
        for f_ in me.polygons: f_.use_smooth = True
        src = bpy.data.objects.new("StrawSrc", me); sc.sc.collection.objects.link(src)
        src.data.materials.append(mat); src.hide_render = True; src.hide_viewport = True
        self.obj = bpy.data.objects.new("Straws", S._points_mesh("Straws", [], {})); sc.sc.collection.objects.link(self.obj)
        self.obj.modifiers.new("Inst", "NODES").node_group = S._instancer_nodes("Straws", src)

    def set(self, x, y, z, ang, rgb, glow, tilt=None, spin=None):
        """Straw middles (grid x, y, height z), directions ang (radians, in the floor plane, grid
        convention), linear colours rgb (n, 3) and glow (n,). tilt/spin: extra rotation while falling."""
        n = len(x)
        rot = np.zeros((n, 3)); rot[:, 2] = -np.asarray(ang)        # grid y points down the screen: flip
        if tilt is not None: rot[:, 1] = tilt
        if spin is not None: rot[:, 0] = spin
        pts = np.stack([np.asarray(x) + 0.0, -np.asarray(y), np.asarray(z)], -1) if n else np.zeros((0, 3))
        old = self.obj.data
        self.obj.data = S._points_mesh("Straws", pts, dict(scale=np.ones((n, 3)), rot=rot, paint=rgb, glow=glow))
        bpy.data.meshes.remove(old)
