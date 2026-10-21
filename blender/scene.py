"""The Langton's Ant scene in Blender, built once and updated per frame.

Used by blender/ant_scene.py (one still) and blender/render_video.py (a whole episode).
Themes (same rules, different skin):
  ant   white squares and raised navy blocks; fresh flips glow pink (like prototypes/ant_3d.py)
  farm  Farmer Joe on a grass field: grass is dug into dirt mounds, then (with 3 colours)
        wheat grows on the dirt, and is harvested back to grass

Camera as in the prototype: pitch 54 deg, yaw orbit, zoom in pixels per cell.
Cells are points with attributes; geometry nodes put one bevelled block on each.
"""
import ctypes, math, sys
import numpy as np
import bpy, bmesh
from mathutils import Matrix, Vector

W, H = 1080, 1920
PITCH = math.radians(54)
GAP = 0.05          # gap around each block
FOC = 1500.0        # focal length in pixels at 1080 wide, as in the prototype
BOARD_Y = 1000      # pixel row the camera target lands on

def lin(rgb):
    """sRGB 0-255 -> linear 0-1 (Blender works in linear)."""
    c = np.array(rgb, float) / 255
    c = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return (*c, 1.0)

THEMES = {
    # floor: "white" squares; block: "black" squares; *_fresh: just flipped
    "ant": dict(floor=(240, 242, 249), floor_fresh=(255, 70, 160), line=(150, 158, 185), line_k=0.22,
                block=(30, 34, 62), block_fresh=(255, 70, 160), block_h=0.42, emit=0.6,
                world=(214, 220, 236), sun=2.0, sun_col=(255, 255, 255), dot=(255, 150, 40),
                crops=[((30, 34, 62), (255, 70, 160), 0.42)]),
    "farm": dict(floor=(104, 170, 62), floor_fresh=(196, 236, 90), line=(70, 128, 40), line_k=0.35,
                 block=(120, 80, 48), block_fresh=(84, 52, 30), block_h=0.14, emit=0.0,
                 world=(178, 210, 240), sun=2.6, sun_col=(255, 244, 222), dot=(255, 214, 64),
                 # colour 1, 2, ...: (colour, fresh colour, height); colour 0 is the grass floor
                 crops=[((120, 80, 48), (84, 52, 30), 0.14), ((222, 178, 70), (255, 222, 120), 0.26)]),
}

def gentle():
    """Below-normal process priority, so the laptop stays usable while rendering."""
    if sys.platform == "win32":
        ctypes.windll.kernel32.SetPriorityClass(ctypes.windll.kernel32.GetCurrentProcess(), 0x4000)

def _node(nt, kind, **ops):
    n = nt.nodes.new(kind)
    for k, v in ops.items(): setattr(n, k, v)
    return n

def _mix(nt, fac, a, b):
    """RGBA mix node; a/b/fac are sockets or constant colours / numbers."""
    m = _node(nt, "ShaderNodeMix", data_type="RGBA")
    for name, v in (("Factor", fac), ("A", a), ("B", b)):
        if isinstance(v, bpy.types.NodeSocket): nt.links.new(v, m.inputs[name])
        else: m.inputs[name].default_value = v
    return m.outputs["Result"]

def _material(name, color, rough=0.55, emit=None):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = color
    b.inputs["Roughness"].default_value = rough
    if emit:
        b.inputs["Emission Color"].default_value = emit[0]; b.inputs["Emission Strength"].default_value = emit[1]
    return m, b

def _instancer_nodes(name, src):
    ng = bpy.data.node_groups.new(name + "Nodes", "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    gi = ng.nodes.new("NodeGroupInput"); go = ng.nodes.new("NodeGroupOutput")
    inst = ng.nodes.new("GeometryNodeInstanceOnPoints")
    oi = ng.nodes.new("GeometryNodeObjectInfo"); oi.inputs["Object"].default_value = src
    ng.links.new(gi.outputs["Geometry"], inst.inputs["Points"])
    ng.links.new(oi.outputs["Geometry"], inst.inputs["Instance"])
    for attr, sock in (("scale", "Scale"), ("rot", "Rotation")):
        na = ng.nodes.new("GeometryNodeInputNamedAttribute"); na.data_type = "FLOAT_VECTOR"
        na.inputs["Name"].default_value = attr; ng.links.new(na.outputs["Attribute"], inst.inputs[sock])
    ng.links.new(inst.outputs["Instances"], go.inputs["Geometry"])
    return ng

def _points_mesh(name, pts, attrs):
    n = len(pts)
    pm = bpy.data.meshes.new(name); pm.vertices.add(n)
    if n: pm.vertices.foreach_set("co", np.asarray(pts, np.float32).ravel())
    for k, v in attrs.items():
        v = np.asarray(v, np.float32)
        if v.ndim == 2 or k in ("scale", "rot"):
            a = pm.attributes.new(k, "FLOAT_VECTOR", "POINT")
            if n: a.data.foreach_set("vector", v.reshape(-1))
        else:
            a = pm.attributes.new(k, "FLOAT", "POINT")
            if n: a.data.foreach_set("value", v)
    return pm


class Scene:
    def __init__(self, theme="farm", scale=50, threads=4, engine="eevee", samples=0):
        self.theme = theme; self.T = T = THEMES[theme]; self.HB = T["block_h"]
        self.heights = [0.0] + [c[2] for c in T["crops"]]    # block height per colour
        bpy.ops.wm.read_factory_settings(use_empty=True)
        sc = self.sc = bpy.context.scene
        sc.render.resolution_x, sc.render.resolution_y = W, H
        sc.render.resolution_percentage = scale
        sc.render.threads_mode = "FIXED"; sc.render.threads = threads
        sc.view_settings.view_transform = "Standard"; sc.view_settings.look = "None"
        if engine == "cycles":
            sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"
            sc.cycles.samples = samples or 32
            sc.cycles.use_denoising = True; sc.cycles.denoiser = "OPENIMAGEDENOISE"
            sc.cycles.max_bounces = 4; sc.cycles.diffuse_bounces = 2; sc.cycles.glossy_bounces = 2
            sc.cycles.transmission_bounces = 0; sc.cycles.volume_bounces = 0
        else:
            engines = [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
            sc.render.engine = "BLENDER_EEVEE_NEXT" if "BLENDER_EEVEE_NEXT" in engines else "BLENDER_EEVEE"
            sc.eevee.taa_render_samples = samples or 16
        self._world(); self._sun(); self._floor(); self._cells()
        if theme == "farm": self._tufts()
        self._walker(); self._camera()

    # ---------- building ----------
    def _world(self):
        world = bpy.data.worlds.new("World"); self.sc.world = world; world.use_nodes = True
        world.node_tree.nodes["Background"].inputs["Color"].default_value = lin(self.T["world"])
        world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.35

    def _sun(self):
        # from back-left, like the prototype's LIGHT (grid y is flipped into world -Y)
        L = Vector((-0.45, 0.65, 1.0)).normalized()
        d = bpy.data.lights.new("Sun", "SUN"); d.energy = self.T["sun"]; d.angle = math.radians(12)
        d.color = lin(self.T["sun_col"])[:3]
        o = bpy.data.objects.new("Sun", d); self.sc.collection.objects.link(o)
        o.rotation_euler = L.to_track_quat("Z", "Y").to_euler()

    def _floor(self):
        """Floor with grid lines that fade out as the camera pulls back."""
        T = self.T
        fm, fb = _material("Floor", lin(T["floor"]), rough=0.85)
        nt = fm.node_tree
        tc = _node(nt, "ShaderNodeTexCoord"); sep = _node(nt, "ShaderNodeSeparateXYZ")
        nt.links.new(tc.outputs["Object"], sep.inputs[0])
        self._line_w = []
        lines = []
        for axis in ("X", "Y"):
            fr = _node(nt, "ShaderNodeMath", operation="FRACT"); nt.links.new(sep.outputs[axis], fr.inputs[0])
            dist = _node(nt, "ShaderNodeMath", operation="PINGPONG"); dist.inputs[1].default_value = 0.5
            nt.links.new(fr.outputs[0], dist.inputs[0])
            lt = _node(nt, "ShaderNodeMath", operation="LESS_THAN")
            nt.links.new(dist.outputs[0], lt.inputs[0]); lines.append(lt); self._line_w.append(lt.inputs[1])
        mx = _node(nt, "ShaderNodeMath", operation="MAXIMUM")
        nt.links.new(lines[0].outputs[0], mx.inputs[0]); nt.links.new(lines[1].outputs[0], mx.inputs[1])
        fade = _node(nt, "ShaderNodeMath", operation="MULTIPLY"); self._line_fade = fade.inputs[1]
        nt.links.new(mx.outputs[0], fade.inputs[0])
        base = lin(T["floor"])
        if self.theme == "farm":
            # each grass square a slightly different green, like a mown field
            fl = _node(nt, "ShaderNodeVectorMath", operation="FLOOR"); nt.links.new(tc.outputs["Object"], fl.inputs[0])
            wn = _node(nt, "ShaderNodeTexWhiteNoise", noise_dimensions="3D"); nt.links.new(fl.outputs[0], wn.inputs["Vector"])
            vr = _node(nt, "ShaderNodeMath", operation="MULTIPLY"); vr.inputs[1].default_value = 0.6
            nt.links.new(wn.outputs["Value"], vr.inputs[0])
            base = _mix(nt, vr.outputs[0], lin((92, 156, 54)), lin((126, 186, 70)))
        nt.links.new(_mix(nt, fade.outputs[0], base, lin(T["line"])), fb.inputs["Base Color"])
        bpy.ops.mesh.primitive_plane_add(size=4000, location=(0, 0, 0))
        o = bpy.context.object; o.name = "Floor"; o.data.materials.append(fm)

    def _cells(self):
        T, farm = self.T, self.theme == "farm"
        bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
        for v in bm.verts:   # base at z=0, height 1: instances scale it to the block height
            v.co.x *= 1 - 2 * GAP; v.co.y *= 1 - 2 * GAP; v.co.z += 0.5
        bmesh.ops.bevel(bm, geom=list(bm.edges), offset=0.06 if farm else 0.035,
                        segments=3 if farm else 2, affect="EDGES", profile=0.5)
        me = bpy.data.meshes.new("Block"); bm.to_mesh(me); bm.free()
        block = bpy.data.objects.new("Block", me); self.sc.collection.objects.link(block)
        block.hide_render = True; block.hide_viewport = True
        # floor tile or block, each fading to its "fresh" colour by heat
        mat, bb = _material("Block", lin(T["block"]), rough=0.95 if farm else 0.45)
        nt = mat.node_tree
        a_heat = _node(nt, "ShaderNodeAttribute", attribute_type="INSTANCER", attribute_name="heat")
        a_blk = _node(nt, "ShaderNodeAttribute", attribute_type="INSTANCER", attribute_name="block")
        blk_col = _mix(nt, a_heat.outputs["Fac"], lin(T["block"]), lin(T["block_fresh"]))
        if farm:
            # ploughed furrows across the dirt, a bit of grain
            tcb = _node(nt, "ShaderNodeTexCoord")
            wave = _node(nt, "ShaderNodeTexWave", wave_type="BANDS", bands_direction="X")
            wave.inputs["Scale"].default_value = 2.2; wave.inputs["Distortion"].default_value = 1.5
            nt.links.new(tcb.outputs["Object"], wave.inputs["Vector"])
            nz = _node(nt, "ShaderNodeTexNoise"); nz.inputs["Scale"].default_value = 18
            nt.links.new(tcb.outputs["Object"], nz.inputs["Vector"])
            grain = _node(nt, "ShaderNodeMath", operation="MULTIPLY"); grain.inputs[1].default_value = 0.5
            nt.links.new(nz.outputs["Fac"], grain.inputs[0])
            blk_col = _mix(nt, grain.outputs[0], blk_col, lin((70, 44, 26)))
            bump = _node(nt, "ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.9
            nt.links.new(wave.outputs["Fac"], bump.inputs["Height"]); nt.links.new(bump.outputs["Normal"], bb.inputs["Normal"])
        flo_col = _mix(nt, a_heat.outputs["Fac"], lin(T["floor"]), lin(T["floor_fresh"]))
        # "block" holds the colour number: 0 floor tile, 1 first block colour, 2 second (wheat)...
        is1 = _node(nt, "ShaderNodeMath", operation="GREATER_THAN"); is1.inputs[1].default_value = 0.5
        nt.links.new(a_blk.outputs["Fac"], is1.inputs[0])
        col = _mix(nt, is1.outputs[0], flo_col, blk_col)
        for i, (c, fresh, _h) in enumerate(T["crops"][1:], start=2):
            ci = _mix(nt, a_heat.outputs["Fac"], lin(c), lin(fresh))
            if farm:   # wheat: fine golden streaks
                tcw = _node(nt, "ShaderNodeTexCoord")
                ww = _node(nt, "ShaderNodeTexWave", wave_type="BANDS", bands_direction="Y")
                ww.inputs["Scale"].default_value = 9; ww.inputs["Distortion"].default_value = 3
                nt.links.new(tcw.outputs["Object"], ww.inputs["Vector"])
                st = _node(nt, "ShaderNodeMath", operation="MULTIPLY"); st.inputs[1].default_value = 0.35
                nt.links.new(ww.outputs["Fac"], st.inputs[0])
                ci = _mix(nt, st.outputs[0], ci, lin((176, 128, 40)))
            isi = _node(nt, "ShaderNodeMath", operation="GREATER_THAN"); isi.inputs[1].default_value = i - 0.5
            nt.links.new(a_blk.outputs["Fac"], isi.inputs[0])
            col = _mix(nt, isi.outputs[0], col, ci)
        nt.links.new(col, bb.inputs["Base Color"])
        if T["emit"]:
            bb.inputs["Emission Color"].default_value = lin(T["block_fresh"])
            em = _node(nt, "ShaderNodeMath", operation="MULTIPLY"); em.inputs[1].default_value = T["emit"]
            nt.links.new(a_heat.outputs["Fac"], em.inputs[0]); nt.links.new(em.outputs[0], bb.inputs["Emission Strength"])
        me.materials.append(mat)
        self.cells = bpy.data.objects.new("Cells", _points_mesh("Cells", [], {}))
        self.sc.collection.objects.link(self.cells)
        self.cells.modifiers.new("Inst", "NODES").node_group = _instancer_nodes("Cells", block)

    def _tufts(self):
        bm = bmesh.new()
        for k in range(3):   # three crossed blades
            a = k * math.pi / 3; ca, sa = math.cos(a) * 0.022, math.sin(a) * 0.022
            v0 = bm.verts.new((-ca, -sa, 0)); v1 = bm.verts.new((ca, sa, 0)); v2 = bm.verts.new((0.01, 0.006, 0.16))
            bm.faces.new((v0, v1, v2))
        tm = bpy.data.meshes.new("Tuft"); bm.to_mesh(tm); bm.free()
        tuft = bpy.data.objects.new("Tuft", tm); self.sc.collection.objects.link(tuft)
        tuft.hide_render = True; tuft.hide_viewport = True
        gm, gb = _material("Grass", lin((96, 170, 52)), rough=0.7)
        gnt = gm.node_tree
        oinf = _node(gnt, "ShaderNodeObjectInfo")
        gcol = _mix(gnt, oinf.outputs["Random"], lin((110, 180, 60)), lin((175, 225, 95)))
        gnt.links.new(gcol, gb.inputs["Base Color"])
        gnt.links.new(gcol, gb.inputs["Emission Color"])   # thin blades lit from behind go black; lift them
        gb.inputs["Emission Strength"].default_value = 0.35
        tm.materials.append(gm)
        self.tufts = bpy.data.objects.new("Tufts", _points_mesh("Tufts", [], {}))
        self.sc.collection.objects.link(self.tufts)
        self.tufts.modifiers.new("Inst", "NODES").node_group = _instancer_nodes("Tufts", tuft)
        # wheat: a thin stalk with an ear on top
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=False, segments=6, radius1=0.008, radius2=0.006, depth=0.22,
                              matrix=Matrix.Translation((0, 0, 0.11)))
        bmesh.ops.create_uvsphere(bm, u_segments=8, v_segments=6, radius=0.024,
                                  matrix=Matrix.Translation((0, 0, 0.25)) @ Matrix.Diagonal((0.75, 0.75, 2.3, 1)))
        sme = bpy.data.meshes.new("Stalk"); bm.to_mesh(sme); bm.free()
        stalk = bpy.data.objects.new("Stalk", sme); self.sc.collection.objects.link(stalk)
        stalk.hide_render = True; stalk.hide_viewport = True
        wm, wb = _material("WheatStalk", lin((226, 182, 76)), rough=0.6)
        oinf2 = _node(wm.node_tree, "ShaderNodeObjectInfo")
        wm.node_tree.links.new(_mix(wm.node_tree, oinf2.outputs["Random"], lin((214, 164, 60)), lin((246, 210, 110))),
                               wb.inputs["Base Color"])
        sme.materials.append(wm)
        self.stalks = bpy.data.objects.new("Stalks", _points_mesh("Stalks", [], {}))
        self.sc.collection.objects.link(self.stalks)
        self.stalks.modifiers.new("Inst", "NODES").node_group = _instancer_nodes("Stalks", stalk)

    def _walker(self):
        self.root = bpy.data.objects.new("Walker", None); self.sc.collection.objects.link(self.root)
        self.body = bpy.data.objects.new("Body", None); self.sc.collection.objects.link(self.body)
        self.body.parent = self.root
        mats = {}
        def mat(name, rgb, rough=0.6):
            if name not in mats: mats[name] = _material(name, lin(rgb), rough=rough)[0]
            return mats[name]
        def part(kind, loc, scale=(1, 1, 1), m=None, rot=None, parent=None, **kw):
            getattr(bpy.ops.mesh, f"primitive_{kind}_add")(location=loc, **kw)
            o = bpy.context.object; o.scale = scale; o.parent = parent or self.body
            if rot is not None: o.rotation_euler = rot
            o.data.materials.append(m); bpy.ops.object.shade_smooth()
            return o
        def stick(a, b, r, m, verts=8, parent=None):
            a, b = Vector(a), Vector(b); v = b - a
            return part("cylinder", (a + b) / 2, m=m, rot=v.to_track_quat("Z", "Y").to_euler(),
                        radius=r, depth=v.length, vertices=verts, parent=parent)
        self.legs = []; self.hat = None
        if self.theme == "ant":
            am = mat("Ant", (52, 28, 14), 0.3)
            for o_, r, z in ((-0.3, 0.17, 0.16), (0.0, 0.11, 0.15), (0.24, 0.13, 0.16)):
                part("uv_sphere", (o_, 0, z), (1.15, 1, 0.9), am, radius=r, segments=24, ring_count=12)
            for side in (-1, 1):
                for o_ in (-0.18, 0.0, 0.18):
                    stick((o_, 0, 0.12), (o_ * 1.6, side * 0.32, 0.0), 0.018, am)
                stick((0.33, 0, 0.2), (0.55, side * 0.18, 0.32), 0.012, am, 6)
        else:
            # a small chunky farmer, built facing +X, scaled up to read on a phone
            self.body.scale = (1.6, 1.6, 1.6)
            jeans = mat("Overalls", (52, 92, 170)); shirt = mat("Shirt", (210, 52, 44))
            skin = mat("Skin", (240, 190, 150), 0.5); straw = mat("Straw", (232, 196, 100), 0.8)
            boot = mat("Boots", (70, 44, 30)); wood = mat("Wood", (150, 104, 60)); metal = mat("Metal", (170, 175, 185), 0.3)
            band = mat("HatBand", (170, 40, 36)); eye = mat("Eye", (20, 20, 24), 0.2)
            for side in (-1, 1):
                hip = bpy.data.objects.new(f"Hip{side}", None); self.sc.collection.objects.link(hip)
                hip.parent = self.body; hip.location = (0, side * 0.075, 0.22); self.legs.append(hip)
                part("uv_sphere", (0.03, 0, -0.185), (1.5, 1, 0.7), boot, parent=hip, radius=0.05, segments=16, ring_count=8)
                part("cylinder", (0, 0, -0.09), m=jeans, parent=hip, radius=0.05, depth=0.17, vertices=16)
            part("uv_sphere", (0, 0, 0.3), (0.85, 1, 1.05), jeans, radius=0.15, segments=24, ring_count=12)
            part("uv_sphere", (0.01, 0, 0.36), (0.8, 0.95, 0.8), shirt, radius=0.14, segments=24, ring_count=12)
            for side in (-1, 1):
                part("cube", (0.1, side * 0.06, 0.38), (0.012, 0.022, 0.07), jeans)   # overall straps
                hand = (0.17, side * 0.14, 0.27) if side > 0 else (-0.04, -0.17, 0.25)
                stick((0.0, side * 0.13, 0.42), hand, 0.035, shirt)
                part("uv_sphere", hand, m=skin, radius=0.035, segments=12, ring_count=6)
            part("uv_sphere", (0.01, 0, 0.56), m=skin, radius=0.11, segments=24, ring_count=12)   # head
            part("uv_sphere", (0.115, 0, 0.55), m=skin, radius=0.025, segments=12, ring_count=6)  # nose
            # the face from his profile picture: big shiny eyes, rosy cheeks, a moustache
            white = _material("EyeShine", lin((255, 255, 255)), emit=(lin((255, 255, 255)), 2.0))[0]
            cheek = mat("Cheek", (240, 120, 120)); tache = mat("Moustache", (110, 72, 44), 0.9)
            for side in (-1, 1):
                part("uv_sphere", (0.098, side * 0.042, 0.592), m=eye, radius=0.021, segments=16, ring_count=8)
                part("uv_sphere", (0.115, side * 0.036, 0.6), m=white, radius=0.006, segments=8, ring_count=6)
                part("uv_sphere", (0.085, side * 0.072, 0.538), (0.6, 1, 0.8), cheek, radius=0.026, segments=12, ring_count=8)
                part("uv_sphere", (0.112, side * 0.03, 0.528), (0.55, 1.35, 0.55), tache, radius=0.03, segments=12, ring_count=8)
            # his little hat, on its own so it can fly off (it follows the body unless told otherwise)
            self.hat = bpy.data.objects.new("Hat", None); self.sc.collection.objects.link(self.hat)
            self.hat.parent = self.root; self.hat.scale = self.body.scale
            part("cylinder", (0, 0, 0.63), m=straw, radius=0.2, depth=0.02, vertices=32, parent=self.hat)    # brim
            part("cylinder", (0, 0, 0.68), m=straw, radius=0.1, depth=0.09, vertices=24, parent=self.hat)    # crown
            part("cylinder", (0, 0, 0.655), m=band, radius=0.102, depth=0.025, vertices=24, parent=self.hat)
            stick((0.1, 0.14, 0.45), (0.4, 0.14, 0.02), 0.014, wood)                              # hoe
            part("cube", (0.41, 0.14, 0.03), (0.02, 0.06, 0.035), metal)
        # far away: a glowing dot instead
        dm, _ = _material("Dot", lin(self.T["dot"]), emit=(lin(self.T["dot"]), 6.0))
        bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, location=(0, 0, 0.2))
        self.dot = bpy.context.object; self.dot.parent = self.root; self.dot.data.materials.append(dm)
        gd = bpy.data.lights.new("Glow", "POINT"); gd.shadow_soft_size = 0.2
        gd.color = (1.0, 0.6, 0.2) if self.theme == "ant" else (1.0, 0.9, 0.7)
        self.glow = bpy.data.objects.new("Glow", gd); self.sc.collection.objects.link(self.glow)
        self.glow.parent = self.root; self.glow.location = (0, 0, 0.9)

    def _camera(self):
        cd = bpy.data.cameras.new("Cam"); cd.sensor_fit = "HORIZONTAL"; cd.sensor_width = 36
        cd.lens = FOC * 36 / W; cd.clip_end = 10000; cd.shift_y = (BOARD_Y - H / 2) / H
        self.cam = bpy.data.objects.new("Cam", cd); self.sc.collection.objects.link(self.cam); self.sc.camera = self.cam

    # ---------- per frame ----------
    def set_cells(self, xs, ys, hz, heat, kind):
        """One point per visible cell: hz block height in cells (0 = flat floor tile), heat 0..1,
        kind = colour number (0 floor tile, 1 dirt, 2 wheat, ...)."""
        n = len(xs)
        pts = np.stack([xs + 0.5, -(ys + 0.5), np.zeros(n)], -1)
        hz = np.where(np.asarray(kind) > 0, np.maximum(hz, 0.008), 0.006)
        scl = np.stack([np.ones(n), np.ones(n), hz], -1)
        old = self.cells.data
        self.cells.data = _points_mesh("Cells", pts, dict(scale=scl, rot=np.zeros((n, 3)), heat=heat,
                                                         block=np.asarray(kind, np.float32)))
        bpy.data.meshes.remove(old)

    def set_tufts(self, grid, cx, cy, s_px, per=8, hz=None):
        """Grass tufts on grass squares and wheat stalks on wheat squares around the camera, only
        while zoomed in enough to see them. hz: block height per cell (for the stalks to stand on)."""
        if self.theme != "farm": return
        show = s_px > 30
        self.tufts.hide_render = self.stalks.hide_render = not show
        if not show: return
        R = int(1.3 * max(W, H) / s_px) + 2
        gx, gy = np.meshgrid(np.arange(int(cx) - R, int(cx) + R), np.arange(int(cy) - R, int(cy) + R))
        gx, gy = gx.ravel(), gy.ravel()
        wheat = grid[gy, gx] == 2
        self._stalks(gx[wheat], gy[wheat], hz[gy[wheat], gx[wheat]] if hz is not None
                     else np.full(int(wheat.sum()), self.heights[-1]))
        keep = grid[gy, gx] == 0
        gx, gy = gx[keep], gy[keep]
        # the same tufts on the same square every frame (hash of the cell, not a fresh random draw)
        k = np.arange(per)
        h = lambda s: (np.sin((gx[:, None] * 12.9898 + gy[:, None] * 78.233 + k[None, :] * 37.719 + s) * 1.7) * 43758.5453) % 1.0
        tx = (gx[:, None] + 0.08 + 0.84 * h(0.0)).ravel(); ty = (gy[:, None] + 0.08 + 0.84 * h(1.3)).ravel()
        s = (0.7 + 0.7 * h(2.1)).ravel(); sz = s * (0.8 + 0.5 * h(3.7)).ravel()
        m = tx.size
        rot = np.stack([(h(4.2).ravel() - 0.5) * 0.3, (h(5.9).ravel() - 0.5) * 0.3, h(6.4).ravel() * 2 * math.pi], -1)
        old = self.tufts.data
        self.tufts.data = _points_mesh("Tufts", np.stack([tx, -ty, np.zeros(m)], -1),
                                       dict(scale=np.stack([s, s, sz], -1), rot=rot))
        bpy.data.meshes.remove(old)

    def _stalks(self, gx, gy, z, per=7):
        k = np.arange(per)
        h = lambda s: (np.sin((gx[:, None] * 12.9898 + gy[:, None] * 78.233 + k[None, :] * 37.719 + s) * 1.7) * 43758.5453) % 1.0
        tx = (gx[:, None] + 0.14 + 0.72 * h(0.4)).ravel(); ty = (gy[:, None] + 0.14 + 0.72 * h(1.9)).ravel()
        tz = np.repeat(np.asarray(z, float), per)
        sc_ = (0.8 + 0.5 * h(2.7)).ravel(); m = tx.size
        rot = np.stack([(h(4.6).ravel() - 0.5) * 0.4, (h(5.1).ravel() - 0.5) * 0.4, h(6.8).ravel() * 2 * math.pi], -1)
        old = self.stalks.data
        self.stalks.data = _points_mesh("Stalks", np.stack([tx, -ty, tz], -1),
                                        dict(scale=np.stack([sc_, sc_, sc_], -1), rot=rot))
        bpy.data.meshes.remove(old)

    def set_floor(self, s_px):
        self._line_fade.default_value = self.T["line_k"] * min(1.0, max(0.0, (s_px - 9) / 18))
        for sock in self._line_w: sock.default_value = 0.025 * max(1.0, 30 / s_px)

    def set_walker(self, x, y, z, ang, s_px, walk=0.0, fall=0.0, hat=None):
        """x, y in cells (centre of the square = +0.5); walk 0..1 = progress of the current step.
        fall 0..1: tipped forward onto his face (1 = flat). hat: None = on his head, or
        ((x, y, z), (rx, ry, rz)) in his own frame (x forward) when it has come off."""
        self.root.location = (x, -y, z); self.root.rotation_euler = (0, 0, ang)
        far = s_px <= 16
        self.dot.hide_render = not far
        self.dot.scale = (7 / s_px,) * 3
        for o in self.body.children_recursive: o.hide_render = far
        if self.hat:
            for o in self.hat.children_recursive: o.hide_render = far
        # a little walk cycle: legs swing and the body bobs while moving between squares
        sw = math.sin(walk * math.pi * 2) * (1 - walk) * 0.5
        for i, hip in enumerate(self.legs):
            hip.rotation_euler = (0, sw * (1 if i else -1), 0)
        self.body.location = (0, 0, abs(math.sin(walk * math.pi)) * 0.04 * (1 - walk))
        self.body.rotation_euler = (0, fall * math.radians(84), 0)   # pivots at his feet, face first
        if self.hat:
            if hat is None:
                self.hat.location = self.body.location; self.hat.rotation_euler = self.body.rotation_euler
            else:
                self.hat.location, self.hat.rotation_euler = hat
        self.glow.data.energy = 6.0 * max(1, 30 / s_px) ** 2

    def set_camera(self, cx, cy, s_px, yaw_deg):
        yaw = math.radians(yaw_deg)
        fwd = Vector((math.sin(yaw) * math.cos(PITCH), math.cos(yaw) * math.cos(PITCH), -math.sin(PITCH)))
        self.cam.location = Vector((cx, -cy, 0)) - fwd * (FOC / s_px)
        self.cam.rotation_euler = (math.pi / 2 - PITCH, 0, -yaw)

    def render(self, path, fmt="JPEG"):
        self.sc.render.filepath = str(path)
        self.sc.render.image_settings.file_format = fmt
        if fmt == "JPEG": self.sc.render.image_settings.quality = 94
        bpy.ops.render.render(write_still=True)
