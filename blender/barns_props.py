"""Props for Experiment 6 (three barns): a barn whose doors swing open, a goat, and Joe's tractor.

All are built facing +X (like the characters in scene.py) out of simple primitives, and placed in
grid squares: x, y in squares (y grows towards the camera), rotation `facing` in radians (world).
"""
import math
import bmesh, bpy
from mathutils import Matrix, Vector
import scene as S

def _mat(name, rgb, rough=0.6, emit=None):
    if name in bpy.data.materials: return bpy.data.materials[name]
    return S._material(name, S.lin(rgb), rough=rough, emit=emit)[0]

def _part(kind, loc, scale=(1, 1, 1), m=None, rot=None, parent=None, smooth=True, **kw):
    getattr(bpy.ops.mesh, f"primitive_{kind}_add")(location=loc, **kw)
    o = bpy.context.object; o.scale = scale; o.parent = parent
    if rot is not None: o.rotation_euler = rot
    if m is not None: o.data.materials.append(m)
    if smooth: bpy.ops.object.shade_smooth()
    return o

def _stick(a, b, r, m, parent, verts=10):
    a, b = Vector(a), Vector(b); v = b - a
    return _part("cylinder", (a + b) / 2, m=m, rot=v.to_track_quat("Z", "Y").to_euler(), parent=parent,
                 radius=r, depth=v.length, vertices=verts)

def _root(sc, name, x, y, facing, scale):
    r = bpy.data.objects.new(name, None); sc.sc.collection.objects.link(r)
    r.location = (x + 0.5, -(y + 0.5), 0); r.rotation_euler = (0, 0, facing); r.scale = (scale,) * 3
    return r

# ---------------- the barn ----------------
def add_game_barn(sc, x, y, facing=-math.pi / 2, scale=1.8):
    """A red barn with a door opening and two door leaves on hinges. Returns dict(root, hinges=[left, right]);
    open the doors with open_doors(barn, 0..1). Inside (local x -1.75..-0.25) it's dark wood."""
    red, trim = _mat("BarnRed", (176, 46, 38), 0.8), _mat("BarnTrim", (240, 236, 226), 0.7)
    roofm, inside = _mat("BarnRoof", (70, 62, 60), 0.85), _mat("BarnInside", (58, 40, 30), 0.95)
    root = _root(sc, "GameBarn", x, y, facing, scale)
    def box(c, size, m): return _part("cube", c, size, m, parent=root, smooth=False, size=1)
    W, D, Hh, dw, dh = 1.5, 1.6, 1.1, 0.64, 0.82                  # width (y), depth (x), wall height, door w/h
    fx = -0.2                                                      # the front wall's x
    box((fx - D / 2, -W / 2 + 0.03, Hh / 2), (D, 0.06, Hh), red); box((fx - D / 2, W / 2 - 0.03, Hh / 2), (D, 0.06, Hh), red)
    box((fx - D + 0.03, 0, Hh / 2), (0.06, W, Hh), red)                                                     # back wall
    side = (W - dw) / 2
    box((fx - 0.03, -(dw / 2 + side / 2), Hh / 2), (0.06, side, Hh), red)                                  # front, left of the door
    box((fx - 0.03, dw / 2 + side / 2, Hh / 2), (0.06, side, Hh), red)                                     # front, right
    box((fx - 0.03, 0, dh + (Hh - dh) / 2), (0.06, dw, Hh - dh), red)                                      # above the door
    box((fx - D / 2, 0, 0.01), (D - 0.1, W - 0.1, 0.02), inside)                                           # floor
    box((fx - D + 0.07, 0, Hh / 2), (0.02, W - 0.14, Hh), inside)                                          # inner back
    for s_ in (-1, 1): box((fx - D / 2, s_ * (W / 2 - 0.07), Hh / 2), (D - 0.1, 0.02, Hh), inside)        # inner sides
    box((fx - D / 2, 0, Hh - 0.02), (D - 0.1, W - 0.1, 0.03), inside)                                     # ceiling
    # gable roof (ridge front to back)
    bm = bmesh.new()
    v = [[bm.verts.new((x_, -0.86, Hh)), bm.verts.new((x_, 0.86, Hh)), bm.verts.new((x_, 0, Hh + 0.62))] for x_ in (fx - D - 0.06, fx + 0.06)]
    bm.faces.new((v[0][0], v[1][0], v[1][2], v[0][2])); bm.faces.new((v[0][1], v[0][2], v[1][2], v[1][1]))
    bm.faces.new((v[0][0], v[0][2], v[0][1])); bm.faces.new((v[1][0], v[1][1], v[1][2]))
    bm.faces.new((v[0][0], v[0][1], v[1][1], v[1][0])); bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    rm = bpy.data.meshes.new("Roof"); bm.to_mesh(rm); bm.free(); rm.materials.append(roofm); rm.materials.append(red)
    for f_ in rm.polygons:                                         # the triangles at the ends are red walls, not roof
        if len(f_.vertices) == 3: f_.material_index = 1
    roof = bpy.data.objects.new("Roof", rm); sc.sc.collection.objects.link(roof); roof.parent = root
    box((fx + 0.01, 0, dh + 0.03), (0.04, dw + 0.08, 0.06), trim)                                          # door frame
    for s_ in (-1, 1): box((fx + 0.01, s_ * (dw / 2 + 0.02), dh / 2), (0.04, 0.05, dh), trim)
    box((fx + 0.01, 0, Hh + 0.2), (0.04, 0.9, 0.04), trim)                                                 # gable trim
    hinges = []
    for s_ in (-1, 1):                                             # two leaves, hinged at the door's sides
        h = bpy.data.objects.new("Hinge", None); sc.sc.collection.objects.link(h); h.parent = root
        h.location = (fx + 0.04, s_ * dw / 2, 0)
        leaf = _part("cube", (0, -s_ * dw / 4, dh / 2), (0.04, dw / 2 - 0.01, dh - 0.02), red, parent=h, smooth=False, size=1)
        for a in (1, -1):                                          # the white cross on each leaf
            d = _part("cube", (0.025, -s_ * dw / 4, dh / 2), (0.02, 0.04, 0.9 * math.hypot(dw / 2, dh) * 0.85), trim,
                      parent=h, smooth=False, size=1)
            d.rotation_euler = (a * math.atan2(dw / 2, dh), 0, 0)
        hinges.append((h, s_))
    return dict(root=root, hinges=hinges)

def open_doors(barn, u):
    """u = 0 shut, 1 wide open (each leaf swings 80 degrees outwards, so it's still seen)."""
    for h, s_ in barn["hinges"]: h.rotation_euler = (0, 0, s_ * math.radians(80) * u)

# ---------------- the goat ----------------
def add_goat(sc, x, y, facing=0.0, scale=1.9):
    coat, patch = _mat("GoatCoat", (236, 230, 218), 0.9), _mat("GoatPatch", (150, 112, 78), 0.9)
    horn, dark = _mat("GoatHorn", (128, 116, 100), 0.5), _mat("GoatDark", (30, 26, 24), 0.3)
    shine = _mat("EyeShineG", (255, 255, 255), 0.3, emit=(S.lin((255, 255, 255)), 2.0))
    root = _root(sc, "Goat", x, y, facing, scale)
    _part("uv_sphere", (0, 0, 0.36), (1.25, 0.72, 0.72), coat, parent=root, radius=0.2, segments=24, ring_count=12)   # body
    _part("uv_sphere", (-0.08, 0.04, 0.42), (1.1, 0.8, 0.6), patch, parent=root, radius=0.12, segments=16, ring_count=8)
    for lx in (0.15, -0.15):
        for ly in (0.08, -0.08):
            _stick((lx, ly, 0.3), (lx, ly, 0.0), 0.022, coat, root)
            _part("uv_sphere", (lx, ly, 0.01), (1, 1, 0.6), dark, parent=root, radius=0.026, segments=10, ring_count=6)
    _stick((0.2, 0, 0.42), (0.27, 0, 0.56), 0.06, coat, root)                                                       # neck
    _part("uv_sphere", (0.31, 0, 0.6), (1.35, 0.8, 0.8), coat, parent=root, radius=0.08, segments=16, ring_count=8)  # head
    _part("uv_sphere", (0.4, 0, 0.57), (1, 0.8, 0.7), patch, parent=root, radius=0.045, segments=12, ring_count=6)   # muzzle
    _part("cone", (0.36, 0, 0.49), (1, 1, 1), _mat("GoatBeard", (210, 204, 190), 0.9), parent=root,
          rot=(math.pi, 0, 0), radius1=0.03, radius2=0.004, depth=0.09, vertices=10)                                # beard
    for s_ in (-1, 1):
        _part("cone", (0.27, s_ * 0.035, 0.7), (1, 1, 1), horn, parent=root, rot=(0, -0.7, 0), radius1=0.022, radius2=0.004,
              depth=0.13, vertices=10)                                                                               # horns, swept back
        _part("uv_sphere", (0.27, s_ * 0.085, 0.62), (0.5, 1.4, 0.35), coat, parent=root, radius=0.04, segments=10, ring_count=6)  # ears
        _part("uv_sphere", (0.37, s_ * 0.045, 0.63), m=dark, parent=root, radius=0.013, segments=10, ring_count=6)  # eyes
        _part("uv_sphere", (0.38, s_ * 0.042, 0.635), m=shine, parent=root, radius=0.004, segments=6, ring_count=4)
    _part("cone", (-0.25, 0, 0.47), (1, 1, 1), coat, parent=root, rot=(0, -0.9, 0), radius1=0.03, radius2=0.005, depth=0.08, vertices=8)
    return root

# ---------------- the tractor ----------------
def add_tractor(sc, x, y, facing=0.0, scale=1.6):
    """Joe's shiny red tractor (about 1 square long before scaling)."""
    red, black = _mat("TractorRed", (206, 34, 28), 0.25), _mat("Tyre", (28, 28, 30), 0.85)
    hub, metal = _mat("Hub", (250, 196, 40), 0.35), _mat("TractorMetal", (176, 180, 188), 0.3)
    glass = _mat("Headlight", (255, 246, 210), 0.2, emit=(S.lin((255, 240, 200)), 1.5))
    root = _root(sc, "Tractor", x, y, facing, scale)
    _part("cube", (0.14, 0, 0.36), (0.5, 0.26, 0.2), red, parent=root, smooth=False, size=1)          # hood
    _part("cube", (0.4, 0, 0.36), (0.03, 0.22, 0.17), metal, parent=root, smooth=False, size=1)       # grille
    _part("cube", (-0.2, 0, 0.36), (0.26, 0.36, 0.18), red, parent=root, smooth=False, size=1)        # body under the seat
    _part("cube", (-0.24, 0, 0.5), (0.14, 0.16, 0.05), black, parent=root, smooth=False, size=1)      # seat
    _part("cube", (-0.31, 0, 0.6), (0.03, 0.16, 0.18), black, parent=root, smooth=False, size=1)      # seat back
    _stick((-0.1, 0, 0.45), (-0.06, 0, 0.62), 0.012, black, root)                                      # steering wheel post
    _part("torus", (-0.05, 0, 0.63), (1, 1, 1), black, parent=root, rot=(0, -0.6, 0), major_radius=0.06, minor_radius=0.01)
    _stick((0.26, 0.08, 0.46), (0.26, 0.08, 0.72), 0.02, metal, root)                                  # exhaust
    for s_ in (-1, 1):
        for wx, r, w in ((-0.2, 0.26, 0.14), (0.28, 0.14, 0.09)):                                       # rear and front wheels
            yy = s_ * (0.26 if wx < 0 else 0.18)
            _part("cylinder", (wx, yy, r), (1, 1, 1), black, parent=root, rot=(math.pi / 2, 0, 0), radius=r, depth=w, vertices=28)
            _part("cylinder", (wx, yy + s_ * w / 2, r), (1, 1, 1), hub, parent=root, rot=(math.pi / 2, 0, 0),
                  radius=r * 0.5, depth=0.02, vertices=20)
        _part("uv_sphere", (0.4, s_ * 0.09, 0.42), (0.5, 1, 1), glass, parent=root, radius=0.03, segments=12, ring_count=6)
        _part("cube", (-0.2, s_ * 0.26, 0.5), (0.3, 0.16, 0.03), red, parent=root, smooth=False, size=1)  # mudguards
    return root

def tractor_mesh(sc):
    """One mesh of a tractor (for instancing many little ones): builds one, joins it, hides the source."""
    r = add_tractor(sc, 0, 0, 0, 1.0); r.location = (0, 0, 0)
    parts = [o for o in r.children_recursive if o.type == "MESH"]
    bpy.ops.object.select_all(action="DESELECT")
    for o in parts: o.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    for o in parts:
        mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
    bpy.ops.object.join()
    src = bpy.context.object; src.name = "TractorToken"; src.hide_render = True; src.hide_viewport = True
    bpy.data.objects.remove(r)
    return src
