"""Props for Experiment 8 (what grows if you plant it?): a dug garden bed, a mustard plant, an apple
tree with apples, a loose apple, a rusty wheelbarrow tyre, a deck chair, a measuring stick and
Pasteur's swan-neck flask.

Grid squares as in scene.py (x right, y towards the camera). Growing things take `grow` (0..1) so a
time-lapse just scales them up.
"""
import math
import bmesh, bpy
import numpy as np
from mathutils import Vector
import scene as S
import scenery as SC

def _mat(name, rgb, rough=0.6, emit=None):
    if name in bpy.data.materials: return bpy.data.materials[name]
    return S._material(name, S.lin(rgb), rough=rough, emit=emit)[0]

def _root(name, x, y, z=0.0, rot=0.0):
    r = bpy.data.objects.new(name, None); bpy.context.scene.collection.objects.link(r)
    r.location = (x + 0.5, -(y + 0.5), z); r.rotation_euler = (0, 0, rot)
    return r

def _sphere(loc, r, m, parent, scale=(1, 1, 1), seg=12):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=r, location=loc, segments=seg, ring_count=max(6, seg // 2))
    o = bpy.context.object; o.scale = scale; o.parent = parent; o.data.materials.append(m); bpy.ops.object.shade_smooth()
    return o

def _stick(a, b, r, m, parent, verts=8):
    a, b = Vector(a), Vector(b); v = b - a
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=v.length, vertices=verts, location=(a + b) / 2)
    o = bpy.context.object; o.rotation_euler = v.to_track_quat("Z", "Y").to_euler(); o.parent = parent
    o.data.materials.append(m); bpy.ops.object.shade_smooth()
    return o

def add_bed(x, y, w, h):
    """A dug garden bed: dark soil, slightly mounded, w x h squares from (x, y)."""
    soil = _mat("Soil", (92, 62, 40), 0.95)
    bpy.ops.mesh.primitive_cube_add(size=1, location=(x + w / 2, -(y + h / 2), 0.04)); o = bpy.context.object
    o.scale = (w, h, 0.1); o.data.materials.append(soil)
    b = o.modifiers.new("Bevel", "BEVEL"); b.width = 0.05; b.segments = 3
    return o

def add_mustard(x, y, seed=1):
    """A clump of black mustard: branching green stems topped with clusters of small yellow flowers.
    Full size about 1.2 squares tall (Joe is about 1.1). Returns its root; scale it to grow it."""
    r = np.random.default_rng(seed)
    stem, leaf, flower = _mat("MustardStem", (88, 140, 62), 0.7), _mat("MustardLeaf", (70, 128, 54), 0.8), _mat("MustardFlower", (250, 214, 40), 0.5)
    root = _root("Mustard", x, y)
    for k in range(7):
        a = r.uniform(0, 2 * math.pi); lean = r.uniform(0.05, 0.25); h = r.uniform(0.9, 1.25)
        top = (lean * math.cos(a), lean * math.sin(a), h)
        _stick((0, 0, 0), top, 0.018, stem, root)
        for j in range(4):                                      # flower clusters along the top of each stem
            u = 0.75 + 0.07 * j
            c = (top[0] * u + r.uniform(-0.05, 0.05), top[1] * u + r.uniform(-0.05, 0.05), top[2] * u + 0.02 * j)
            _sphere(c, r.uniform(0.04, 0.06), flower, root, seg=8)
        _sphere((top[0] * 0.3, top[1] * 0.3, 0.25), 0.12, leaf, root, scale=(1.6, 0.8, 0.3), seg=10)   # a leaf low down
    root.scale = (0.001,) * 3
    return root

def add_apple_tree(x, y, apple_rgb=(140, 200, 70), seed=2, size=3.2):
    """Kenney's oak with apples hung round its canopy (green by default: not the same apple as the
    red one Joe planted). Returns dict(root, apples); scale root to grow it."""
    r = np.random.default_rng(seed)
    root = _root("AppleTree", x, y)
    t = SC.kenney("tree_oak", 0, 0, scale=size); t.parent = root; t.location = (0, 0, 0)
    apple = _mat(f"Apple{apple_rgb}", apple_rgb, 0.35)
    apples = []
    for k in range(26):                                          # on the canopy's surface (roughly)
        a, e = r.uniform(0, 2 * math.pi), r.uniform(-0.2, 0.9)
        rad = 0.42 * size
        c = (rad * math.cos(a) * math.cos(e), rad * math.sin(a) * math.cos(e), 0.62 * size + 0.3 * size * math.sin(e))
        apples.append(_sphere(c, 0.07 * size / 3.2 * 1.3, apple, root, seg=10))
    root.scale = (0.001,) * 3
    return dict(root=root, apples=apples)

def add_apple(x, y, z, rgb=(210, 40, 36), parent=None):
    """One apple (red: the one Joe planted the seeds of), with a little stalk."""
    o = _sphere((x, y, z), 0.09, _mat(f"Apple{rgb}", rgb, 0.3), parent, scale=(1, 1, 0.9))
    _stick((0, 0, 0.08), (0.01, 0, 0.14), 0.008, _mat("AppleStalk", (90, 60, 30)), o)
    return o

def add_tyre(x, y, tilt=0.5):
    """A rusty wheelbarrow tyre, half buried and tipped over."""
    rubber, rust = _mat("OldRubber", (46, 40, 36), 0.9), _mat("Rust", (150, 74, 36), 0.85)
    root = _root("Tyre", x, y, z=0.12, rot=0.4)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.36, minor_radius=0.11, major_segments=32, minor_segments=12, location=(0, 0, 0))
    o = bpy.context.object; o.parent = root; o.data.materials.append(rubber); o.rotation_euler = (math.pi / 2 - tilt, 0, 0)
    bpy.ops.object.shade_smooth()
    bpy.ops.mesh.primitive_cylinder_add(radius=0.25, depth=0.12, vertices=24, location=(0, 0, 0))
    h = bpy.context.object; h.parent = root; h.data.materials.append(rust); h.rotation_euler = (math.pi / 2 - tilt, 0, 0)
    return root

def add_deckchair(x, y, rot=0.0):
    """A striped deck chair (red and white), facing `rot`."""
    wood, red, white = _mat("ChairWood", (176, 130, 82), 0.7), _mat("ChairRed", (210, 52, 48), 0.6), _mat("ChairWhite", (240, 236, 228), 0.6)
    root = _root("DeckChair", x, y, rot=rot)
    for s_ in (-1, 1):
        _stick((0.35, s_ * 0.3, 0), (-0.25, s_ * 0.3, 0.75), 0.025, wood, root)     # back legs / back frame
        _stick((-0.3, s_ * 0.3, 0), (0.2, s_ * 0.3, 0.45), 0.025, wood, root)      # front legs
    for k in range(5):                                          # the striped canvas, as five strips
        u0, u1 = k / 5, (k + 1) / 5
        a = Vector((0.3 - 0.5 * u0, 0, 0.35 + 0.4 * u0)); b = Vector((0.3 - 0.5 * u1, 0, 0.35 + 0.4 * u1))
        bpy.ops.mesh.primitive_cube_add(size=1, location=(a + b) / 2); o = bpy.context.object
        o.scale = ((a - b).length + 0.01, 0.56, 0.015); o.rotation_euler = (0, math.atan2(-(b - a).z, -(b - a).x) + math.pi, 0)
        o.parent = root; o.data.materials.append(red if k % 2 == 0 else white)
    return root

def add_stick(x, y, height=1.2):
    """A measuring stick with marks every 0.1 (a foot is about 0.3 here)."""
    wood, ink = _mat("StickWood", (236, 214, 160), 0.6), _mat("StickInk", (40, 30, 26), 0.5)
    root = _root("Stick", x, y)
    _stick((0, 0, 0), (0, 0, height), 0.03, wood, root)
    for k in range(1, 12):
        bpy.ops.mesh.primitive_cube_add(size=1, location=(0.032, 0, k * height / 12)); o = bpy.context.object
        o.scale = (0.01, 0.05 if k % 3 else 0.08, 0.01); o.parent = root; o.data.materials.append(ink)
    return root

def add_flask(x, y, z=0.0):
    """Pasteur's swan-neck flask: a round glass flask of broth with a long S-bent neck."""
    glass = _mat("FlaskGlass", (220, 236, 245), 0.05)
    if glass.node_tree:
        b = glass.node_tree.nodes.get("Principled BSDF")
        if b: b.inputs["Alpha"].default_value = 0.35
        if hasattr(glass, "surface_render_method"): glass.surface_render_method = "BLENDED"
    broth = _mat("Broth", (214, 168, 80), 0.3)
    root = _root("Flask", x, y, z)
    _sphere((0, 0, 0.18), 0.18, glass, root, seg=24)
    _sphere((0, 0, 0.12), 0.15, broth, root, scale=(1, 1, 0.55), seg=20)
    pts = [(0, 0, 0.34), (0, 0, 0.5), (0.08, 0, 0.6), (0.2, 0, 0.58), (0.28, 0, 0.45), (0.36, 0, 0.42), (0.46, 0, 0.5)]
    for a, b in zip(pts, pts[1:]): _stick(a, b, 0.035, glass, root, verts=12)
    return root
