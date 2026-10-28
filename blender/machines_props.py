"""Farm machines for Experiment 7's escalation (Dean, 23 Oct): Joe throws by hand, then a wheelbarrow
dumps, then the tractor with a tipping trailer, then a combine harvester spewing straw out the back.

All built facing +X from simple shapes, placed at grid (x, y) with a world facing; each returns a dict
of the parts that move (set them each frame). The combine is our own design: red with white trim and
no logo (Dean's photo was a John Deere; their green and yellow is their trademark look).
"""
import math
import bpy
from mathutils import Vector
import scene as S

def _mat(name, rgb, rough=0.5, emit=None):
    if name in bpy.data.materials: return bpy.data.materials[name]
    return S._material(name, S.lin(rgb), rough=rough, emit=emit)[0]

def _root(name, x, y, facing, z=0.0):
    r = bpy.data.objects.new(name, None); bpy.context.scene.collection.objects.link(r)
    r.location = (x + 0.5, -(y + 0.5), z); r.rotation_euler = (0, 0, facing)
    return r

def _box(loc, size, m, parent, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc); o = bpy.context.object
    o.scale = size; o.parent = parent; o.data.materials.append(m)
    if bevel:
        b = o.modifiers.new("Bevel", "BEVEL"); b.width = bevel; b.segments = 2
    return o

def _cyl(loc, r, depth, m, parent, rot=(0, 0, 0), verts=24):
    bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, vertices=verts, location=loc); o = bpy.context.object
    o.rotation_euler = rot; o.parent = parent; o.data.materials.append(m); bpy.ops.object.shade_smooth()
    return o

def _wheel(loc, r, w, tyre, hub, parent):
    t = _cyl(loc, r, w, tyre, parent, rot=(math.pi / 2, 0, 0), verts=28)
    h = _cyl((loc[0], loc[1] + (w / 2 + 0.005) * (1 if loc[1] >= 0 else -1), loc[2]), r * 0.5, 0.02, hub, parent, rot=(math.pi / 2, 0, 0))
    return t

def add_wheelbarrow(x, y, facing=0.0, scale=1.6):
    """A wheelbarrow: a metal tray on one wheel at the front, two wooden handles at the back.
    Tip it with parts["tray"].rotation_euler.y (negative = tipping forward); fill with parts["load"]."""
    steel, wood = _mat("BarrowSteel", (64, 120, 168), 0.35), _mat("Handle", (168, 120, 72), 0.7)
    tyre, hub = _mat("Tyre", (28, 28, 30), 0.85), _mat("Hub", (250, 196, 40), 0.35)
    root = _root("Wheelbarrow", x, y, facing); root.scale = (scale,) * 3
    pivot = bpy.data.objects.new("BarrowPivot", None); bpy.context.scene.collection.objects.link(pivot)
    pivot.parent = root; pivot.location = (0.35, 0, 0.16)                  # tips about the wheel's axle
    _wheel((0.35, 0, 0.16), 0.16, 0.08, tyre, hub, root)
    tray = bpy.data.objects.new("BarrowTray", None); bpy.context.scene.collection.objects.link(tray); tray.parent = pivot
    bpy.ops.mesh.primitive_cone_add(vertices=4, radius1=0.32, radius2=0.46, depth=0.26, location=(-0.4, 0, 0.26),
                                    rotation=(0, 0, math.pi / 4), end_fill_type="NGON")
    t = bpy.context.object; t.scale = (1.3, 0.9, 1); t.parent = tray; t.data.materials.append(steel)
    sol = t.modifiers.new("Solid", "SOLIDIFY"); sol.thickness = 0.02
    for s_ in (-1, 1):
        a, b = Vector((-0.15, s_ * 0.22, 0.12)), Vector((-1.05, s_ * 0.28, 0.32))
        v = b - a; h = _cyl((a + b) / 2, 0.022, v.length, wood, tray, rot=v.to_track_quat("Z", "Y").to_euler(), verts=10)
        _box((-0.62, s_ * 0.2, 0.0), (0.03, 0.03, 0.26), steel, tray)             # legs
    load = bpy.data.objects.new("BarrowLoad", None); bpy.context.scene.collection.objects.link(load); load.parent = tray
    load.location = (-0.4, 0, 0.36)
    return dict(root=root, tray=pivot, load=load)

def add_trailer(x, y, facing=0.0, scale=1.6):
    """A tipping trailer: a red bed on two wheels with a drawbar. Tip it with parts["bed"].rotation_euler.y
    (positive = tipping back to dump out of the rear)."""
    red, tyre, hub = _mat("TractorRed", (206, 34, 28), 0.25), _mat("Tyre", (28, 28, 30), 0.85), _mat("Hub", (250, 196, 40), 0.35)
    wood = _mat("TrailerWood", (150, 104, 62), 0.7)
    root = _root("Trailer", x, y, facing); root.scale = (scale,) * 3
    for s_ in (-1, 1): _wheel((-0.15, s_ * 0.36, 0.18), 0.18, 0.1, tyre, hub, root)
    _box((0.45, 0, 0.22), (0.5, 0.05, 0.04), red, root)                          # drawbar
    pivot = bpy.data.objects.new("TrailerPivot", None); bpy.context.scene.collection.objects.link(pivot)
    pivot.parent = root; pivot.location = (-0.55, 0, 0.32)                        # hinged at the back
    bed = bpy.data.objects.new("TrailerBed", None); bpy.context.scene.collection.objects.link(bed); bed.parent = pivot
    _box((0.4, 0, 0.0), (1.0, 0.66, 0.05), wood, bed)
    for s_ in (-1, 1): _box((0.4, s_ * 0.33, 0.14), (1.0, 0.04, 0.28), red, bed)
    _box((0.89, 0, 0.14), (0.04, 0.66, 0.28), red, bed)
    load = bpy.data.objects.new("TrailerLoad", None); bpy.context.scene.collection.objects.link(load); load.parent = bed
    load.location = (0.4, 0, 0.2)
    return dict(root=root, bed=pivot, load=load)

def add_combine(x, y, facing=0.0, scale=1.9):
    """A combine harvester (our own design): a red body with white trim, a glass cab, big front
    wheels, small rear wheels, a wide header at the front with a turning reel, a grain tank, an
    unloading spout and an exhaust stack. Straw comes out of the back (parts["rear"] is where).
    Spin the reel with parts["reel"].rotation_euler.y."""
    red, white = _mat("CombineRed", (196, 40, 32), 0.35), _mat("CombineWhite", (238, 236, 230), 0.4)
    dark, glass = _mat("CombineDark", (40, 40, 44), 0.5), _mat("CabGlass", (150, 200, 230), 0.1, emit=(S.lin((150, 200, 230)), 0.3))
    tyre, hub, steel = _mat("Tyre", (28, 28, 30), 0.85), _mat("CombineHub", (238, 236, 230), 0.4), _mat("Steel", (150, 154, 160), 0.3)
    root = _root("Combine", x, y, facing); root.scale = (scale,) * 3
    _box((0.0, 0, 0.75), (1.6, 0.9, 0.7), red, root, bevel=0.04)                 # body
    _box((0.0, 0, 0.42), (1.62, 0.92, 0.06), white, root)                         # trim stripe
    _box((-0.1, 0, 1.25), (1.1, 0.8, 0.32), red, root, bevel=0.05)               # grain tank
    _box((0.55, 0, 1.38), (0.42, 0.55, 0.45), glass, root, bevel=0.03)           # cab (glass)
    _box((0.55, 0, 1.63), (0.48, 0.6, 0.05), white, root)                         # cab roof
    for s_ in (-1, 1):
        _wheel((0.45, s_ * 0.5, 0.42), 0.42, 0.24, tyre, hub, root)              # big drive wheels
        _wheel((-0.6, s_ * 0.42, 0.25), 0.25, 0.16, tyre, hub, root)             # steering wheels
    _cyl((-0.55, 0.25, 1.75), 0.04, 0.5, dark, root)                              # exhaust stack
    spout = _cyl((-0.3, 0.75, 1.45), 0.06, 1.2, red, root, rot=(math.pi / 2 - 0.2, 0, 0.15), verts=16)   # unloading auger
    _box((1.05, 0, 0.55), (0.5, 0.3, 0.25), red, root)                            # feeder house
    _box((1.45, 0, 0.32), (0.45, 2.3, 0.18), red, root, bevel=0.02)              # header
    _box((1.6, 0, 0.22), (0.15, 2.3, 0.05), steel, root)                          # cutter bar
    reel = bpy.data.objects.new("Reel", None); bpy.context.scene.collection.objects.link(reel); reel.parent = root
    reel.location = (1.45, 0, 0.58)
    _cyl((0, 0, 0), 0.03, 2.2, steel, reel, rot=(math.pi / 2, 0, 0), verts=10)
    for k in range(6):                                                           # the reel's bats
        a = k * math.pi / 3
        _box((0.22 * math.cos(a), 0, 0.22 * math.sin(a)), (0.03, 2.2, 0.03), white, reel)
    rear = bpy.data.objects.new("CombineRear", None); bpy.context.scene.collection.objects.link(rear); rear.parent = root
    rear.location = (-0.85, 0, 0.6)
    return dict(root=root, reel=reel, rear=rear, spout=spout)
