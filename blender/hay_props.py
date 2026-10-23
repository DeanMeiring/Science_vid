"""Props for Experiment 7 (pi from a bale of hay): a plank floor, a round hay bale, and straws.

Grid squares as in scene.py (x right, y towards the camera). The floor's planks run along x and are
exactly one straw long wide: the cracks sit at whole numbers of y (y = y0, y0 + 1, ...).
"""
import math
import bpy
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
    return root

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
        # one straw: a thin tube 1 square long along x, centred on the origin
        bpy.ops.mesh.primitive_cylinder_add(radius=0.016, depth=1.0, vertices=8, location=(0, 0, 0))
        src = bpy.context.object; src.rotation_euler = (0, math.pi / 2, 0); bpy.ops.object.transform_apply(rotation=True)
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
