"""One still of Experiment 5: Joe's four-crop field at a given step (pick a mirror moment).

Usage: blender -b -P blender/crops_still.py -- --step 10012 --pitch 54 [--scale 50] [--out file.png]
The camera looks along the mirror line (yaw 90), so the two mirrored halves are left and right.
Also writes <out>.json: where Joe and the mirror line are on screen (for notes in Pillow).
"""
import argparse, json, math, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "pipeline"))
import scene as S
import crops as CR
from common import N, ROOT

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--step", type=int, default=10012)
ap.add_argument("--pitch", type=float, default=54)
ap.add_argument("--scale", type=int, default=50)
ap.add_argument("--out", default="")
args = ap.parse_args(argv)
S.gentle()

g, hist = CR.run(args.step, size=N); c = N // 2
x, y, d = hist[-1]
ys, xs = np.nonzero(g); kind = g[ys, xs].astype(int)
sc = S.Scene("farm", scale=args.scale)
sc.set_cells(xs, ys, np.array(sc.heights)[kind], np.zeros(len(xs)), kind)
# the camera looks along the mirror line (between rows c and c+1), from beyond the field's left end
x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
cx, cy = (x0 + x1) / 2 + 2.5, c + 1.0          # a little beyond the middle: the field sits above the captions
s_px = min(110.0, 1000 / (max(y1 - y0, (x1 - x0) * (0.8 if args.pitch < 70 else 0.6)) + 1))
sc.set_tufts(g, cx, cy, s_px); sc.set_pumpkins(g, cx, cy, s_px); sc.set_floor(s_px)
ANGS = [math.pi / 2, 0, -math.pi / 2, math.pi]
sc.set_walker(x + 0.5, y + 0.5, sc.heights[g[y, x]] if g[y, x] else 0.02, ANGS[d], s_px)
sc.set_camera(cx, cy, s_px, 90, args.pitch)
out = Path(args.out or ROOT / "renders" / "ep05_crops" / f"still_{args.step}_p{int(args.pitch)}.png")
out.parent.mkdir(parents=True, exist_ok=True)
sc.render(out, "PNG")
import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector
def screen(gx, gy, z=0.0):
    v = world_to_camera_view(bpy.context.scene, sc.cam, Vector((gx, -gy, z)))
    return [round(v.x * 1080), round((1 - v.y) * 1920)]
out.with_suffix(".json").write_text(json.dumps(dict(
    step=args.step, joe=screen(x + 0.5, y + 0.5, 0.9), axis=[screen(x0 - 1, cy, 0.3), screen(x1 + 1, cy, 0.3)],
    crops=np.bincount(kind, minlength=4).tolist())))
print("saved", out, f"zoom {s_px:.1f}px, field {x1 - x0}x{y1 - y0}, Joe at ({x - c}, {y - c}) facing {d}", flush=True)
