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
                 crops=[((120, 80, 48), (84, 52, 30), 0.14), ((222, 178, 70), (255, 222, 120), 0.26),
                        ((66, 116, 44), (110, 170, 70), 0.14)]),        # pumpkins (Experiment 5): leaves under them
}

def gentle():
    """Below-normal process priority, so the laptop stays usable while rendering."""
    if sys.platform == "win32":
        k32 = ctypes.windll.kernel32
        # handles are pointer-sized: without these types the handle gets cut to 32 bits and the
        # call silently fails (renders ran at normal priority until Oct 2026)
        k32.GetCurrentProcess.restype = ctypes.c_void_p
        k32.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        if not k32.SetPriorityClass(k32.GetCurrentProcess(), 0x4000):   # BELOW_NORMAL_PRIORITY_CLASS
            print("warning: couldn't lower the process priority", flush=True)

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
    def __init__(self, theme="farm", scale=50, threads=4, engine="eevee", samples=0, character=None):
        """character: who walks: "joe" (farm default), "ant" (ant default) or "sheep" (Daisy)."""
        self.character = character or ("ant" if theme == "ant" else "joe")
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
            if farm and i == 2:   # wheat: fine golden streaks
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
        # painted cells (Experiment 3's trails): their own colour, glowing a little
        a_paint = _node(nt, "ShaderNodeAttribute", attribute_type="INSTANCER", attribute_name="paint")
        a_pw = _node(nt, "ShaderNodeAttribute", attribute_type="INSTANCER", attribute_name="painted")
        col = _mix(nt, a_pw.outputs["Fac"], col, a_paint.outputs["Color"])
        nt.links.new(col, bb.inputs["Base Color"])
        if not T["emit"]:
            nt.links.new(a_paint.outputs["Color"], bb.inputs["Emission Color"])
            pe = _node(nt, "ShaderNodeMath", operation="MULTIPLY"); pe.inputs[1].default_value = 0.35
            nt.links.new(a_pw.outputs["Fac"], pe.inputs[0]); nt.links.new(pe.outputs[0], bb.inputs["Emission Strength"])
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
        # pumpkins: a ribbed, squashed orange ball with a little green stem
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=0.26)
        for v in bm.verts:
            a = math.atan2(v.co.y, v.co.x); k = 1 - 0.07 * (0.5 + 0.5 * math.cos(8 * a))
            v.co.x *= k; v.co.y *= k; v.co.z = v.co.z * 0.72 + 0.19
        n_body = len(bm.faces)
        bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=0.035, radius2=0.025, depth=0.1,
                              matrix=Matrix.Translation((0.01, 0, 0.41)) @ Matrix.Rotation(0.25, 4, "Y"))
        pme = bpy.data.meshes.new("Pumpkin"); bm.to_mesh(pme); bm.free()
        pm_, pb_ = _material("Pumpkin", lin((236, 120, 30)), rough=0.45)
        oinf3 = _node(pm_.node_tree, "ShaderNodeObjectInfo")
        pm_.node_tree.links.new(_mix(pm_.node_tree, oinf3.outputs["Random"], lin((222, 104, 24)), lin((250, 146, 44))),
                                pb_.inputs["Base Color"])
        pme.materials.append(pm_); pme.materials.append(_material("PumpkinStem", lin((76, 110, 40)), rough=0.8)[0])
        for i, f_ in enumerate(pme.polygons): f_.material_index = 0 if i < n_body else 1
        for f_ in pme.polygons: f_.use_smooth = True
        pumpkin = bpy.data.objects.new("Pumpkin", pme); self.sc.collection.objects.link(pumpkin)
        pumpkin.hide_render = True; pumpkin.hide_viewport = True
        self.pumpkins = bpy.data.objects.new("Pumpkins", _points_mesh("Pumpkins", [], {}))
        self.sc.collection.objects.link(self.pumpkins)
        self.pumpkins.modifiers.new("Inst", "NODES").node_group = _instancer_nodes("Pumpkins", pumpkin)

    def _walker(self):
        self.root = bpy.data.objects.new("Walker", None); self.sc.collection.objects.link(self.root)
        self.body = bpy.data.objects.new("Body", None); self.sc.collection.objects.link(self.body)
        self.body.parent = self.root
        mats = {}
        def mat(name, rgb, rough=0.6):
            rgb = getattr(self, "_recolour", {}).get(name, rgb)
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
        self.legs = []; self.hat = None; self.arms = {}; self.tool = []
        if self.character == "sheep":
            # Daisy: a fluffy white body, black face and legs, built facing +X, trotting on diagonal leg pairs
            self.body.scale = (2.1, 2.1, 2.1)          # big enough to read on a phone
            wool = mat("Wool", (246, 244, 236), 0.9); black = mat("SheepBlack", (34, 30, 32), 0.6)
            eye = mat("Eye", (20, 20, 24), 0.2)
            white = _material("EyeShine", lin((255, 255, 255)), emit=(lin((255, 255, 255)), 2.0))[0]
            for side in (-1, 1):
                hip = bpy.data.objects.new(f"Hip{side}", None); self.sc.collection.objects.link(hip)
                hip.parent = self.body; hip.location = (0, 0, 0.17); self.legs.append(hip)
                for lx, ly in ((0.1, 0.065 * side), (-0.1, -0.065 * side)):     # front one side, back the other
                    part("cylinder", (lx, ly, -0.085), m=black, parent=hip, radius=0.022, depth=0.17, vertices=10)
            for dx, dy, dz, r in ((0, 0, 0.3, 0.13), (0.08, 0.05, 0.31, 0.1), (0.08, -0.05, 0.31, 0.1),
                                  (-0.09, 0.05, 0.3, 0.1), (-0.09, -0.05, 0.3, 0.1), (0.0, 0.0, 0.38, 0.1),
                                  (0.1, 0.0, 0.37, 0.08), (-0.11, 0.0, 0.37, 0.08), (0.0, 0.08, 0.27, 0.09),
                                  (0.0, -0.08, 0.27, 0.09)):                   # a fluffy cloud of wool
                part("uv_sphere", (dx, dy, dz), m=wool, radius=r, segments=16, ring_count=8)
            part("uv_sphere", (0.2, 0, 0.36), (1.25, 0.85, 0.95), black, radius=0.065, segments=16, ring_count=8)  # face
            part("uv_sphere", (0.19, 0, 0.42), (1.0, 1.4, 0.7), wool, radius=0.05, segments=12, ring_count=6)      # tuft
            for side in (-1, 1):
                part("uv_sphere", (0.17, side * 0.075, 0.37), (0.6, 1.2, 0.45), black, radius=0.04, segments=10, ring_count=6)  # ears
                part("uv_sphere", (0.255, side * 0.032, 0.385), m=eye, radius=0.013, segments=10, ring_count=6)
                part("uv_sphere", (0.265, side * 0.028, 0.39), m=white, radius=0.004, segments=6, ring_count=4)
        elif self.character == "cow":
            # Experiment 9's cow: white with black patches, a pink muzzle, little horns; built facing +X
            self.body.scale = (2.1, 2.1, 2.1)
            hide = mat("CowWhite", (244, 242, 236), 0.8); black = mat("CowBlack", (30, 28, 30), 0.7)
            pink = mat("CowPink", (236, 160, 160), 0.6); horn = mat("CowHorn", (226, 214, 188), 0.5)
            eye = mat("Eye", (20, 20, 24), 0.2)
            white = _material("EyeShine", lin((255, 255, 255)), emit=(lin((255, 255, 255)), 2.0))[0]
            for side in (-1, 1):
                hip = bpy.data.objects.new(f"Hip{side}", None); self.sc.collection.objects.link(hip)
                hip.parent = self.body; hip.location = (0, 0, 0.2); self.legs.append(hip)
                for lx, ly in ((0.13, 0.07 * side), (-0.13, -0.07 * side)):
                    part("cylinder", (lx, ly, -0.1), m=hide, parent=hip, radius=0.026, depth=0.2, vertices=10)
                    part("cylinder", (lx, ly, -0.19), m=black, parent=hip, radius=0.028, depth=0.03, vertices=10)  # hooves
            part("uv_sphere", (0, 0, 0.34), (1.55, 0.85, 0.85), hide, radius=0.16, segments=24, ring_count=12)   # body
            for dx, dy, dz, r in ((0.06, 0.1, 0.38, 0.07), (-0.12, -0.1, 0.33, 0.08), (-0.05, 0.08, 0.44, 0.06), (0.12, -0.09, 0.36, 0.05)):
                part("uv_sphere", (dx, dy, dz), (1.3, 0.55, 1.0), black, radius=r, segments=12, ring_count=6)    # patches
            part("uv_sphere", (0.28, 0, 0.44), (1.15, 0.85, 0.9), hide, radius=0.085, segments=16, ring_count=8)  # head
            part("uv_sphere", (0.355, 0, 0.405), (0.85, 1.1, 0.75), pink, radius=0.06, segments=16, ring_count=8)  # muzzle
            part("cylinder", (-0.27, 0, 0.3), m=hide, rot=(0, 0.35, 0), radius=0.012, depth=0.18, vertices=6)    # tail
            part("uv_sphere", (-0.3, 0, 0.21), m=black, radius=0.022, segments=8, ring_count=4)
            for side in (-1, 1):
                part("uv_sphere", (0.4, side * 0.022, 0.41), m=black, radius=0.009, segments=8, ring_count=4)    # nostrils
                part("cone", (0.26, side * 0.05, 0.53), m=horn, rot=(side * -0.5, 0, 0), radius1=0.016, radius2=0.004, depth=0.06, vertices=8)
                part("uv_sphere", (0.25, side * 0.1, 0.47), (0.5, 1.3, 0.4), black, radius=0.035, segments=10, ring_count=6)  # ears
                part("uv_sphere", (0.33, side * 0.045, 0.47), m=eye, radius=0.014, segments=10, ring_count=6)
                part("uv_sphere", (0.342, side * 0.042, 0.476), m=white, radius=0.004, segments=6, ring_count=4)
        elif self.character == "pig":
            # Experiment 9's pig: round and pink, a snout, floppy ears, a curly tail; built facing +X
            self.body.scale = (2.1, 2.1, 2.1)
            skin = mat("PigPink", (246, 172, 178), 0.55); snout = mat("PigSnout", (226, 128, 140), 0.5)
            dark = mat("PigDark", (90, 40, 50), 0.4); eye = mat("Eye", (20, 20, 24), 0.2)
            white = _material("EyeShine", lin((255, 255, 255)), emit=(lin((255, 255, 255)), 2.0))[0]
            for side in (-1, 1):
                hip = bpy.data.objects.new(f"Hip{side}", None); self.sc.collection.objects.link(hip)
                hip.parent = self.body; hip.location = (0, 0, 0.13); self.legs.append(hip)
                for lx, ly in ((0.1, 0.07 * side), (-0.1, -0.07 * side)):
                    part("cylinder", (lx, ly, -0.065), m=skin, parent=hip, radius=0.028, depth=0.13, vertices=10)
            part("uv_sphere", (0, 0, 0.25), (1.35, 1.0, 0.92), skin, radius=0.16, segments=24, ring_count=12)   # body
            part("uv_sphere", (0.2, 0, 0.29), (1.0, 1.0, 0.95), skin, radius=0.1, segments=16, ring_count=8)     # head
            part("cylinder", (0.3, 0, 0.27), m=snout, rot=(0, math.pi / 2, 0), radius=0.045, depth=0.05, vertices=16)
            for side in (-1, 1):
                part("uv_sphere", (0.326, side * 0.017, 0.272), m=dark, radius=0.01, segments=8, ring_count=4)   # nostrils
                part("cone", (0.18, side * 0.075, 0.38), m=skin, rot=(side * -0.6, 0.5, 0), radius1=0.04, radius2=0.006, depth=0.08, vertices=8)
                part("uv_sphere", (0.275, side * 0.045, 0.33), m=eye, radius=0.013, segments=10, ring_count=6)
                part("uv_sphere", (0.287, side * 0.042, 0.336), m=white, radius=0.004, segments=6, ring_count=4)
            for i in range(5):                                                                  # a curly tail
                a = i * 1.4
                part("uv_sphere", (-0.215 - 0.012 * i, 0.025 * math.sin(a), 0.3 + 0.025 * math.cos(a)), m=skin,
                     radius=0.012, segments=8, ring_count=4)
        elif self.character == "chicken":
            # Experiment 10's chicken: a plump white hen, red comb and wattle, yellow beak and legs; built facing +X
            self.body.scale = (2.1, 2.1, 2.1)
            white_f = mat("Feathers", (250, 248, 242), 0.85); red = mat("Comb", (220, 40, 36), 0.5)
            yellow = mat("Beak", (246, 176, 40), 0.45); eye = mat("Eye", (20, 20, 24), 0.2)
            shine = _material("EyeShine", lin((255, 255, 255)), emit=(lin((255, 255, 255)), 2.0))[0]
            for side in (-1, 1):
                hip = bpy.data.objects.new(f"Hip{side}", None); self.sc.collection.objects.link(hip)
                hip.parent = self.body; hip.location = (0, side * 0.045, 0.12); self.legs.append(hip)
                part("cylinder", (0, 0, -0.06), m=yellow, parent=hip, radius=0.012, depth=0.12, vertices=8)
                for a in (-0.5, 0, 0.5):                                                   # three toes
                    part("cube", (0.035 * math.cos(a), 0.035 * math.sin(a), -0.118), (0.035, 0.007, 0.004), yellow,
                         rot=(0, 0, a), parent=hip, size=1)
            part("uv_sphere", (0, 0, 0.22), (1.25, 0.95, 0.95), white_f, radius=0.11, segments=24, ring_count=12)  # body
            part("uv_sphere", (0.09, 0, 0.32), (0.9, 0.85, 1.0), white_f, radius=0.065, segments=16, ring_count=8)  # head
            part("cone", (0.155, 0, 0.315), m=yellow, rot=(0, math.pi / 2, 0), radius1=0.02, radius2=0.0, depth=0.05, vertices=10)
            part("uv_sphere", (0.13, 0, 0.27), (0.6, 0.5, 1.2), red, radius=0.022, segments=10, ring_count=6)      # wattle
            for dx, dz, r in ((0.06, 0.385, 0.022), (0.09, 0.39, 0.024), (0.115, 0.375, 0.02)):
                part("uv_sphere", (dx, 0, dz), (1, 0.6, 1), red, radius=r, segments=10, ring_count=6)            # comb
            for side in (-1, 1):
                part("uv_sphere", (0.125, side * 0.04, 0.33), m=eye, radius=0.011, segments=10, ring_count=6)
                part("uv_sphere", (0.133, side * 0.039, 0.335), m=shine, radius=0.0035, segments=6, ring_count=4)
                part("uv_sphere", (-0.01, side * 0.1, 0.23), (1.4, 0.35, 0.8), white_f, radius=0.07, segments=12, ring_count=6)  # wings
            for a in (-0.25, 0, 0.25):                                                       # tail feathers
                part("uv_sphere", (-0.13, a * 0.1, 0.31), (0.5, 0.25, 1.1), white_f, rot=(a, -0.5, 0), radius=0.06,
                     segments=10, ring_count=6)
        elif self.theme == "ant":
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
            self.arms = {}
            for side in (-1, 1):
                part("cube", (0.1, side * 0.06, 0.38), (0.012, 0.022, 0.07), jeans)   # overall straps
                hand = (0.17, side * 0.14, 0.27) if side > 0 else (-0.04, -0.17, 0.25)
                # a shoulder joint: the arm and hand hang from it, so set_walker(arms=...) can swing them
                sh = bpy.data.objects.new(f"Shoulder{side}", None); self.sc.collection.objects.link(sh)
                sh.parent = self.body; sh.location = (0.0, side * 0.13, 0.42)
                rel = (hand[0], hand[1] - side * 0.13, hand[2] - 0.42)
                stick((0, 0, 0), rel, 0.035, shirt, parent=sh)
                part("uv_sphere", rel, m=skin, radius=0.035, segments=12, ring_count=6, parent=sh)
                self.arms["left" if side > 0 else "right"] = (sh, rel)
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
            self.tool = [stick((0.1, 0.14, 0.45), (0.4, 0.14, 0.02), 0.014, wood),                # hoe
                         part("cube", (0.41, 0.14, 0.03), (0.02, 0.06, 0.035), metal)]
        # far away: a glowing dot instead
        dm, _ = _material("Dot", lin(self.T["dot"]), emit=(lin(self.T["dot"]), 6.0))
        bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, location=(0, 0, 0.2))
        self.dot = bpy.context.object; self.dot.parent = self.root; self.dot.data.materials.append(dm)
        gd = bpy.data.lights.new("Glow", "POINT"); gd.shadow_soft_size = 0.2
        gd.color = (1.0, 0.6, 0.2) if self.theme == "ant" else (1.0, 0.9, 0.7)
        self.glow = bpy.data.objects.new("Glow", gd); self.sc.collection.objects.link(self.glow)
        self.glow.parent = self.root; self.glow.location = (0, 0, 0.9)

    def set_dots(self, xs, ys, s_px, colour=(255, 255, 255), zs=None):
        """Small glowing markers for many walkers at once (e.g. a herd of sheep seen from far away)."""
        if not hasattr(self, "dots"):
            dm, _ = _material("HerdDot", lin(colour), emit=(lin(colour), 3.0))
            bpy.ops.mesh.primitive_uv_sphere_add(radius=1.0, segments=12, ring_count=6, location=(0, 0, 0))
            src = bpy.context.object; src.data.materials.append(dm); src.hide_render = True; src.hide_viewport = True
            self.dots = bpy.data.objects.new("Herd", _points_mesh("Herd", [], {})); self.sc.collection.objects.link(self.dots)
            self.dots.modifiers.new("Inst", "NODES").node_group = _instancer_nodes("Herd", src)
        n = len(xs); r = max(0.1, 5 / s_px)      # small up close, still visible from far away
        old = self.dots.data
        z = np.full(n, r) if zs is None else np.asarray(zs, float)
        self.dots.data = _points_mesh("Herd", np.stack([np.asarray(xs) + 0.5, -(np.asarray(ys) + 0.5), z], -1),
                                      dict(scale=np.full((n, 3), r), rot=np.zeros((n, 3))))
        bpy.data.meshes.remove(old)

    def set_trail_image(self, rgba, x0, y0, z=0.02, gap=0.07, glow=0.35, cell=1.0):
        """Paint trails as one image lying on the field (light, however long the trails get).
        rgba: (S, S, 4) floats 0..1 in sRGB, row 0 = grid row y0, column 0 = grid column x0.
        Each pixel is one square, drawn with a thin grass-coloured gap round it, glowing a little.
        cell: squares per pixel (e.g. 0.125 for fine footprints; the gap is set when first made)."""
        S = rgba.shape[0]
        if getattr(self, "_trail_size", None) != S:
            img = bpy.data.images.new("Trail", S, S, alpha=True); img.colorspace_settings.name = "sRGB"
            mat = bpy.data.materials.new("Trail"); mat.use_nodes = True; nt = mat.node_tree
            for n_ in list(nt.nodes): nt.nodes.remove(n_)
            outn = _node(nt, "ShaderNodeOutputMaterial"); bsdf = _node(nt, "ShaderNodeBsdfPrincipled")
            tex = _node(nt, "ShaderNodeTexImage", interpolation="Closest"); tex.image = img
            uv = _node(nt, "ShaderNodeTexCoord")
            # the gap: UV * S is the position in squares; keep only the inside of each square
            mul = _node(nt, "ShaderNodeVectorMath", operation="MULTIPLY"); mul.inputs[1].default_value = (S, S, 1)
            nt.links.new(uv.outputs["UV"], mul.inputs[0]); self._trail_scale = mul.inputs[1]
            fr = _node(nt, "ShaderNodeVectorMath", operation="FRACTION"); nt.links.new(mul.outputs[0], fr.inputs[0])
            sp = _node(nt, "ShaderNodeSeparateXYZ"); nt.links.new(fr.outputs[0], sp.inputs[0])
            gx = _node(nt, "ShaderNodeMath", operation="GREATER_THAN"); gx.inputs[1].default_value = gap
            gy = _node(nt, "ShaderNodeMath", operation="GREATER_THAN"); gy.inputs[1].default_value = gap
            nt.links.new(sp.outputs["X"], gx.inputs[0]); nt.links.new(sp.outputs["Y"], gy.inputs[0])
            m1 = _node(nt, "ShaderNodeMath", operation="MULTIPLY"); nt.links.new(gx.outputs[0], m1.inputs[0]); nt.links.new(gy.outputs[0], m1.inputs[1])
            m2 = _node(nt, "ShaderNodeMath", operation="MULTIPLY"); nt.links.new(m1.outputs[0], m2.inputs[0]); nt.links.new(tex.outputs["Alpha"], m2.inputs[1])
            nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"]); nt.links.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
            bsdf.inputs["Emission Strength"].default_value = glow; bsdf.inputs["Roughness"].default_value = 0.8
            transp = _node(nt, "ShaderNodeBsdfTransparent"); mixs = _node(nt, "ShaderNodeMixShader")
            nt.links.new(m2.outputs[0], mixs.inputs[0]); nt.links.new(transp.outputs[0], mixs.inputs[1]); nt.links.new(bsdf.outputs[0], mixs.inputs[2])
            nt.links.new(mixs.outputs[0], outn.inputs["Surface"])
            if hasattr(mat, "surface_render_method"): mat.surface_render_method = "DITHERED"
            bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0)); pl = bpy.context.object; pl.name = "TrailPlane"
            pl.data.materials.append(mat)
            old = getattr(self, "trail_plane", None)
            if old: bpy.data.objects.remove(old)
            self.trail_plane, self.trail_img, self._trail_size = pl, img, S
        pl = self.trail_plane
        pl.scale = (S * cell, S * cell, 1); pl.location = (x0 + S * cell / 2, -(y0 + S * cell / 2), z)
        self.trail_img.pixels.foreach_set(np.ascontiguousarray(rgba[::-1], np.float32).ravel())   # Blender rows go bottom-up
        self.trail_img.update()

    def set_beads(self, pts, rgb, radius=0.3):
        """Glowing beads (e.g. the squares a chicken has flown through, in 3D): pts (n, 3) in
        (grid x, grid y, height); rgb (n, 3) linear colours."""
        if not hasattr(self, "beads"):
            mat, b = _material("Bead", (1, 1, 1, 1), rough=0.4)
            nt = mat.node_tree; at = _node(nt, "ShaderNodeAttribute", attribute_type="INSTANCER", attribute_name="paint")
            nt.links.new(at.outputs["Color"], b.inputs["Base Color"]); nt.links.new(at.outputs["Color"], b.inputs["Emission Color"])
            b.inputs["Emission Strength"].default_value = 1.2
            bpy.ops.mesh.primitive_ico_sphere_add(radius=1.0, subdivisions=2, location=(0, 0, 0))
            src = bpy.context.object; src.data.materials.append(mat); src.hide_render = True; src.hide_viewport = True
            self.beads = bpy.data.objects.new("Beads", _points_mesh("Beads", [], {})); self.sc.collection.objects.link(self.beads)
            self.beads.modifiers.new("Inst", "NODES").node_group = _instancer_nodes("Beads", src)
        pts = np.asarray(pts, float); n = len(pts)
        world = np.stack([pts[:, 0] + 0.5, -(pts[:, 1] + 0.5), pts[:, 2]], -1) if n else np.zeros((0, 3))
        old = self.beads.data
        self.beads.data = _points_mesh("Beads", world, dict(scale=np.full((n, 3), radius), rot=np.zeros((n, 3)), paint=rgb))
        bpy.data.meshes.remove(old)

    def add_nest(self, x, y, z):
        """The chickens' home in the sky: a straw nest sitting on a little cloud (grid x, y; height z)."""
        straw = _material("Nest", lin((214, 170, 80)), rough=0.9)[0]
        puff = _material("Cloud", lin((255, 255, 255)), rough=1.0, emit=(lin((255, 255, 255)), 0.25))[0]
        bpy.ops.mesh.primitive_torus_add(major_radius=0.9, minor_radius=0.35, location=(x + 0.5, -(y + 0.5), z - 0.3))
        nest = bpy.context.object; nest.data.materials.append(straw); bpy.ops.object.shade_smooth()
        for dx, dy, dz, r in ((0, 0, -1.3, 1.6), (1.5, 0.3, -1.5, 1.2), (-1.5, -0.2, -1.5, 1.25), (0.4, 1.3, -1.6, 1.1),
                              (-0.5, -1.3, -1.6, 1.1), (2.4, -0.8, -1.9, 0.8), (-2.3, 0.9, -1.9, 0.85)):
            bpy.ops.mesh.primitive_uv_sphere_add(radius=r, segments=20, ring_count=10, location=(x + 0.5 + dx, -(y + 0.5) + dy, z + dz))
            o = bpy.context.object; o.scale = (1, 1, 0.7); o.data.materials.append(puff); bpy.ops.object.shade_smooth()
        gd = bpy.data.lights.new("NestGlow", "POINT"); gd.energy = 0; gd.color = (1.0, 0.85, 0.5); gd.shadow_soft_size = 0.5
        self.nest_glow = bpy.data.objects.new("NestGlow", gd); self.sc.collection.objects.link(self.nest_glow)
        self.nest_glow.location = (x + 0.5, -(y + 0.5), z + 0.6)
        return nest

    def set_sky(self, rgb):
        """What the camera sees above the horizon (the scene is still lit by the normal world colour)."""
        wnt = self.sc.world.node_tree
        if not hasattr(self, "_sky"):
            self._sky = _node(wnt, "ShaderNodeBackground"); lp = _node(wnt, "ShaderNodeLightPath"); mx = _node(wnt, "ShaderNodeMixShader")
            wnt.links.new(wnt.nodes["Background"].outputs[0], mx.inputs[1]); wnt.links.new(self._sky.outputs[0], mx.inputs[2])
            wnt.links.new(lp.outputs["Is Camera Ray"], mx.inputs[0]); wnt.links.new(mx.outputs[0], wnt.nodes["World Output"].inputs["Surface"])
        self._sky.inputs["Color"].default_value = lin(rgb); self._sky.inputs["Strength"].default_value = 1.0

    def add_character(self, character, recolour=None):
        """A second character (e.g. Joe watching while Daisy walks). Returns a handle for set_character.
        recolour: {material name: rgb}, e.g. {"Shirt": (60, 140, 230)} for a farmer who isn't Joe."""
        keep = {k: getattr(self, k) for k in ("root", "body", "legs", "hat", "dot", "glow", "arms", "tool", "character")}
        self.character = character; self._recolour = recolour or {}
        try: self._walker()
        finally: self._recolour = {}
        handle = {k: getattr(self, k) for k in ("root", "body", "legs", "hat", "dot", "glow", "arms", "tool")}
        for k, v in keep.items(): setattr(self, k, v)
        return handle

    def set_character(self, handle, *args, **kw):
        """set_walker for a character made with add_character."""
        keep = {k: getattr(self, k) for k in handle}
        for k, v in handle.items(): setattr(self, k, v)
        try: self.set_walker(*args, **kw)
        finally:
            for k, v in keep.items(): setattr(self, k, v)

    def add_barn(self, x, y, facing=0.0):
        """A little red barn with its door at grid cell (x, y), facing `facing` radians (world)."""
        red = _material("BarnRed", lin((176, 46, 38)), rough=0.8)[0]; trim = _material("BarnTrim", lin((240, 236, 226)), rough=0.7)[0]
        roofm = _material("BarnRoof", lin((70, 62, 60)), rough=0.85)[0]
        barn = bpy.data.objects.new("Barn", None); self.sc.collection.objects.link(barn)
        barn.location = (x + 0.5, -(y + 0.5), 0); barn.rotation_euler = (0, 0, facing)
        barn.scale = (1.8, 1.8, 1.8)            # big enough to read as "home" from far away
        def box(loc, size, m):
            bpy.ops.mesh.primitive_cube_add(size=1, location=loc); o = bpy.context.object
            o.scale = size; o.parent = barn; o.data.materials.append(m); return o
        box((-1.0, 0, 0.55), (1.6, 1.5, 1.1), red)                                  # walls (door side faces +X)
        # gable roof: the ridge runs front to back, so the triangle faces the door like a classic barn
        bm = bmesh.new()
        v = [[bm.verts.new((x_, -0.84, 1.1)), bm.verts.new((x_, 0.84, 1.1)), bm.verts.new((x_, 0, 1.72))]
             for x_ in (-1.86, -0.14)]
        bm.faces.new((v[0][0], v[1][0], v[1][2], v[0][2])); bm.faces.new((v[0][1], v[0][2], v[1][2], v[1][1]))
        bm.faces.new((v[0][0], v[0][2], v[0][1])); bm.faces.new((v[1][0], v[1][1], v[1][2]))
        bm.faces.new((v[0][0], v[0][1], v[1][1], v[1][0]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        rm = bpy.data.meshes.new("Roof"); bm.to_mesh(rm); bm.free()
        roof = bpy.data.objects.new("Roof", rm); self.sc.collection.objects.link(roof); roof.parent = barn
        rm.materials.append(roofm)
        gable = box((-0.17, 0, 1.3), (0.02, 1.1, 0.06), trim)                       # a trim line under the gable
        box((-0.19, 0, 0.42), (0.04, 0.7, 0.84), trim)                               # door frame
        box((-0.17, 0, 0.4), (0.04, 0.6, 0.76), red)                                 # door
        for a in (1, -1):                                                            # the white cross on the door
            d = box((-0.15, 0, 0.4), (0.03, 0.06, 0.95), trim); d.rotation_euler = (a * 0.67, 0, 0)
        return barn

    def _camera(self):
        cd = bpy.data.cameras.new("Cam"); cd.sensor_fit = "HORIZONTAL"; cd.sensor_width = 36
        cd.lens = FOC * 36 / W; cd.clip_end = 10000; cd.shift_y = (BOARD_Y - H / 2) / H
        self.cam = bpy.data.objects.new("Cam", cd); self.sc.collection.objects.link(self.cam); self.sc.camera = self.cam

    # ---------- per frame ----------
    def set_cells(self, xs, ys, hz, heat, kind, paint=None):
        """One point per visible cell: hz block height in cells (0 = flat floor tile), heat 0..1,
        kind = colour number (0 floor tile, 1 dirt, 2 wheat, ...).
        paint: optional (n, 3) linear RGB per cell; cells with a paint colour show it instead (trails)."""
        n = len(xs)
        pts = np.stack([xs + 0.5, -(ys + 0.5), np.zeros(n)], -1)
        hz = np.where(np.asarray(kind) > 0, np.maximum(hz, 0.008), 0.006)
        scl = np.stack([np.ones(n), np.ones(n), hz], -1)
        old = self.cells.data
        painted = np.zeros(n, np.float32) if paint is None else np.ones(n, np.float32)
        paint = np.zeros((n, 3), np.float32) if paint is None else np.asarray(paint, np.float32)
        self.cells.data = _points_mesh("Cells", pts, dict(scale=scl, rot=np.zeros((n, 3)), heat=heat,
                                                         block=np.asarray(kind, np.float32), paint=paint, painted=painted))
        bpy.data.meshes.remove(old)

    def set_tufts(self, grid, cx, cy, s_px, per=8, hz=None):
        """Grass tufts on grass squares and wheat stalks on wheat squares around the camera, only
        while zoomed in enough to see them. hz: block height per cell (for the stalks to stand on)."""
        if self.theme != "farm": return
        show = s_px > 30
        self.tufts.hide_render = self.stalks.hide_render = not show
        self.pumpkins.hide_render = s_px <= 12
        if not show: return
        R = int(1.3 * max(W, H) / s_px) + 2
        gx, gy = np.meshgrid(np.arange(int(cx) - R, int(cx) + R), np.arange(int(cy) - R, int(cy) + R))
        gx, gy = gx.ravel(), gy.ravel()
        inside = (gx >= 0) & (gx < grid.shape[1]) & (gy >= 0) & (gy < grid.shape[0])
        gx, gy = gx[inside], gy[inside]          # off the grid: no tufts (and no wrapping round to the far side)
        wheat = grid[gy, gx] == 2
        self._stalks(gx[wheat], gy[wheat], hz[gy[wheat], gx[wheat]] if hz is not None
                     else np.full(int(wheat.sum()), self.heights[2]))
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

    def set_pumpkins(self, grid, cx, cy, s_px):
        """One pumpkin on each pumpkin square (colour 3) near the camera; from far away the leafy
        squares alone show them. Called with set_tufts."""
        if s_px <= 12: return
        R = int(1.3 * max(W, H) / s_px) + 2
        sub_ = grid[max(0, int(cy) - R):int(cy) + R, max(0, int(cx) - R):int(cx) + R]
        gy, gx = np.nonzero(sub_ == 3); gy = gy + max(0, int(cy) - R); gx = gx + max(0, int(cx) - R)
        h = lambda s: (np.sin((gx * 12.9898 + gy * 78.233 + s) * 1.7) * 43758.5453) % 1.0
        n = len(gx); sc_ = 0.85 + 0.3 * h(1.1)
        old = self.pumpkins.data
        self.pumpkins.data = _points_mesh("Pumpkins", np.stack([gx + 0.5 + (h(2.2) - 0.5) * 0.12, -(gy + 0.5 + (h(3.3) - 0.5) * 0.12),
                                                                np.full(n, self.heights[3])], -1) if n else [],
                                          dict(scale=np.stack([sc_, sc_, sc_], -1), rot=np.stack([np.zeros(n), np.zeros(n), h(4.4) * 6.283], -1)) if n else {})
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

    def set_walker(self, x, y, z, ang, s_px, walk=0.0, fall=0.0, hat=None, arms=None, tool=True):
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
        # arms: {"right"/"left": (swing, out)} in radians -- swing > 0 takes the hand back, < 0 forward
        # and up; out lifts it sideways. Missing arms hang as built.
        for k, (sh, _) in self.arms.items():
            sw, out = (arms or {}).get(k, (0.0, 0.0))
            sh.rotation_euler = ((1 if k == "left" else -1) * out, sw, 0)
        for o in self.tool: o.hide_render = far or not tool

    def hand_position(self, which="right"):
        """Where a hand is in the world right now (call after set_walker and a view-layer update)."""
        from mathutils import Vector
        sh, rel = self.arms[which]
        return tuple(sh.matrix_world @ Vector(rel))

    def set_camera(self, cx, cy, s_px, yaw_deg, pitch_deg=None, tz=0.0):
        """Look at grid point (cx, cy) at height tz, s_px pixels per cell there; pitch defaults to 54 deg."""
        yaw = math.radians(yaw_deg); pitch = PITCH if pitch_deg is None else math.radians(pitch_deg)
        fwd = Vector((math.sin(yaw) * math.cos(pitch), math.cos(yaw) * math.cos(pitch), -math.sin(pitch)))
        self.cam.location = Vector((cx, -cy, tz)) - fwd * (FOC / s_px)
        self.cam.rotation_euler = (math.pi / 2 - pitch, 0, -yaw)

    def render(self, path, fmt="JPEG"):
        self.sc.render.filepath = str(path)
        self.sc.render.image_settings.file_format = fmt
        if fmt == "JPEG": self.sc.render.image_settings.quality = 94
        bpy.ops.render.render(write_still=True)
