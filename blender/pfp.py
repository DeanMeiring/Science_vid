"""Profile picture of Farmer Joe (the same 3D model as in the episodes), for Instagram and YouTube.

Usage: blender -b -P blender/pfp.py            -> renders/pfp/joe_<look>.png (1080x1080)
Profile pictures are cropped to a circle, so Joe stays in the middle with room around him.
"""
import math, sys
from pathlib import Path
import numpy as np
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "pipeline"))
import scene as S
from common import N, ROOT

S.gentle()
OUT = ROOT / "renders" / "pfp"; OUT.mkdir(parents=True, exist_ok=True)

sc = S.Scene("farm", scale=100, threads=4, samples=32)
sc.sc.render.resolution_x = sc.sc.render.resolution_y = 1080
cam = sc.cam.data; cam.shift_y = 0; cam.sensor_fit = "AUTO"

# a little field: Joe on grass, a few freshly dug dirt mounds behind him
grid = np.zeros((N, N), np.uint8)
c = N // 2
dirt = [(c + 1, c - 1), (c + 2, c - 1), (c + 1, c - 2), (c - 1, c - 2), (c + 2, c + 1), (c - 2, c - 1)]
for x, y in dirt: grid[y, x] = 1
xs = np.array([d[0] for d in dirt]); ys = np.array([d[1] for d in dirt])
sc.set_cells(xs, ys, np.ones(len(xs)), np.zeros(len(xs)), np.ones(len(xs), np.float32))
sc.set_tufts(grid, c + 0.5, c + 0.5, 120, per=10)
sc.set_floor(120)

# ---- extra character for the close-up: bigger eyes with highlights, rosy cheeks, a moustache ----
def blob(loc, r, rgb, scale=(1, 1, 1), emit=0.0, rough=0.5):
    bpy.ops.mesh.primitive_uv_sphere_add(location=loc, radius=r, segments=24, ring_count=12)
    o = bpy.context.object; o.scale = scale; o.parent = sc.body
    m, b = S._material("m", S.lin(rgb), rough=rough)
    if emit: b.inputs["Emission Color"].default_value = S.lin(rgb); b.inputs["Emission Strength"].default_value = emit
    o.data.materials.append(m); bpy.ops.object.shade_smooth()
for side in (-1, 1):
    blob((0.098, side * 0.042, 0.592), 0.021, (24, 20, 22), rough=0.15)            # eyes
    blob((0.115, side * 0.036, 0.6), 0.006, (255, 255, 255), emit=2.0)             # eye highlights
    blob((0.085, side * 0.072, 0.538), 0.026, (240, 120, 120), (0.6, 1, 0.8))      # cheeks
    blob((0.112, side * 0.03, 0.528), 0.03, (110, 72, 44), (0.55, 1.35, 0.55), rough=0.9)   # moustache

# soft light from the front so his face isn't in shadow
key = bpy.data.lights.new("Key", "AREA"); key.energy = 60; key.size = 2.5; key.color = (1.0, 0.96, 0.9)
key_o = bpy.data.objects.new("Key", key); sc.sc.collection.objects.link(key_o)

# what the camera sees behind him (the scene is still lit by the normal sky)
wnt = sc.sc.world.node_tree
bg_cam = wnt.nodes.new("ShaderNodeBackground"); lp = wnt.nodes.new("ShaderNodeLightPath")
mixw = wnt.nodes.new("ShaderNodeMixShader")
wnt.links.new(wnt.nodes["Background"].outputs[0], mixw.inputs[1]); wnt.links.new(bg_cam.outputs[0], mixw.inputs[2])
wnt.links.new(lp.outputs["Is Camera Ray"], mixw.inputs[0])
wnt.links.new(mixw.outputs[0], wnt.nodes["World Output"].inputs["Surface"])

def shot(name, cam_dir, dist, height, target_z, lens, face_offset_deg=-25):
    """cam_dir: horizontal direction from Joe to the camera (world). Joe turns towards it,
    a bit off to one side, for a friendly three-quarter view."""
    jx, jy = c + 0.5, -(c + 0.5)
    d = Vector((cam_dir[0], cam_dir[1], 0)).normalized()
    face = math.atan2(d.y, d.x) + math.radians(face_offset_deg)
    sc.set_walker(jx, c + 0.5, 0.0, face, 120)
    sc.glow.data.energy = 4.0
    cam.lens = lens
    loc = Vector((jx, jy, 0)) + d * dist + Vector((0, 0, height))
    sc.cam.location = loc
    sc.cam.rotation_euler = (Vector((jx, jy, target_z)) - loc).to_track_quat("-Z", "Y").to_euler()
    key_o.location = loc + Vector((0.4, 0.3, 0.9))
    key_o.rotation_euler = (Vector((jx, jy, target_z)) - key_o.location).to_track_quat("-Z", "Y").to_euler()
    sc.render(OUT / f"joe_{name}.png", "PNG")
    print("saved", OUT / f"joe_{name}.png", flush=True)

SKY, YELLOW = (92, 170, 245), (245, 183, 43)
for bg_name, bg in (("sky", SKY), ("yellow", YELLOW)):
    bg_cam.inputs["Color"].default_value = S.lin(bg); bg_cam.inputs["Strength"].default_value = 1.0
    # head, hat and shoulders in the middle of the circle
    shot(f"portrait_{bg_name}", (0.3, -1.0), 2.5, 0.55, 0.78, 50, -18)
# full body with the field and sky
bg_cam.inputs["Color"].default_value = S.lin(SKY)
shot("full_sky", (0.35, -1.0), 3.6, 0.5, 0.6, 50, -22)
