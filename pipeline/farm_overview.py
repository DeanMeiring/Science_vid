"""The whole farm at the end of Experiment 4: every experiment so far laid out around today's field,
for the zoom out ("The farm's getting busy"). Shared by the render (pixels) and compose (labels).

Positions are grid squares relative to Joe's start in Experiment 4 (y grows towards the camera):
  #1 the highway field (rule RL, 16,800 steps, where Experiment 1 ended)       far left
  #2 the wheat field (rule RLR, 1,200,000 steps, where Experiment 2 ended)     far right
  #3 the lost sheep: Daisy's and the herd's trails, and the barn (Experiment 3) near
  #4 today's field: spotless, Joe and Daisy back where they started            middle
Each field is the real end state of its episode's simulation.
"""
import sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import N, ROOT, load_episode, simulate
import walks as WK

SZ = 1024                                    # canvas: one pixel per square, centred on today's field
DIRT, WHEAT = (100, 62, 34), (222, 178, 70)       # dirt a little darker than in the episodes, to read from far away
# where each field's middle goes, and its label (title, what happened)
FIELDS = {1: dict(at=(-150, -165), title="Experiment #1", sub="the highway"),
          2: dict(at=(150, -175), title="Experiment #2", sub="wheat: still a mess"),
          3: dict(at=(0, 175), title="Experiment #3", sub="the lost sheep"),
          4: dict(at=(0, 0), title="Experiment #4", sub="today: spotless!")}

def hsv2rgb(h, s, v):
    i = np.floor(h * 6).astype(int) % 6; f = h * 6 - np.floor(h * 6)
    p, q, t_ = v * (1 - s), v * (1 - f * s), v * (1 - (1 - f) * s)
    return np.stack([np.choose(i, [v, q, p, p, t_, v]), np.choose(i, [t_, v, v, q, p, p]), np.choose(i, [p, p, t_, v, v, q])], -1)

def build():
    """Returns (rgba canvas (SZ, SZ, 4) floats in sRGB, row 0 = grid row -SZ/2; field id per pixel;
    each field's box {id: (x0, y0, x1, y1)}; the barn's door square for #3)."""
    rgba = np.zeros((SZ, SZ, 4), np.float32); fid = np.zeros((SZ, SZ), np.int8); boxes = {}
    def place(k, xs, ys, cols):
        cx, cy = FIELDS[k]["at"]
        ox = cx - (xs.min() + xs.max()) // 2; oy = cy - (ys.min() + ys.max()) // 2
        px, py = xs + ox + SZ // 2, ys + oy + SZ // 2
        rgba[py, px, :3] = cols; rgba[py, px, 3] = 1; fid[py, px] = k
        boxes[k] = (int(xs.min() + ox), int(ys.min() + oy), int(xs.max() + ox), int(ys.max() + oy))
        return ox, oy
    for k, (rule, steps) in ((1, ("RL", 16800)), (2, ("RLR", 1200000))):
        mv, _ = simulate(steps, rule); g = np.zeros((N, N), np.uint8)
        for x, y in mv: g[y, x] = (g[y, x] + 1) % len(rule)
        ys, xs = np.nonzero(g)
        cols = np.where((g[ys, xs] == 1)[:, None], np.array(DIRT) / 255, np.array(WHEAT) / 255)
        place(k, xs - N // 2, ys - N // 2, cols)
    # #3: the trails as Experiment 3 left them (soft gold for Daisy, pastel for the herd)
    ep = load_episode(ROOT / "episodes" / "ep03_sheep.py")
    pal = np.array([0.07, 0.02, 0.95, 0.88, 0.80, 0.74, 0.66, 0.58, 0.52, 0.98, 0.16])
    paths = [WK.daisy(ep.DAISY["seed"], ep.DAISY["home_step"])]
    for p in WK.herd(ep.HERD["seed"], ep.HERD["sheep"], ep.HERD["steps"]):
        h = WK.first_home(p); paths.append(p[:(h or len(p) - 1) + 1])
    pts, hue = [], []
    for k, p in enumerate(paths[::-1]):                       # Daisy last, on top
        pts.append(p); hue.append(np.full(len(p), 0.12 if k == len(paths) - 1 else pal[k % len(pal)]))
    pts = np.vstack(pts); hue = np.concatenate(hue)
    sat = np.where(hue == 0.12, 0.35, 0.4)
    keep = ~((pts[:, 0] >= -1) & (pts[:, 0] <= 1) & (pts[:, 1] >= -5) & (pts[:, 1] <= -2))   # not under the barn
    ox, oy = place(3, pts[keep, 0], pts[keep, 1], hsv2rgb(hue[keep], sat[keep], np.full(keep.sum(), 0.9)))
    barn = (ox, oy - 2)                                       # Experiment 3's barn stood 2 squares above home
    boxes[4] = (-17, -17, 17, 17)
    return rgba, fid, boxes, barn

if __name__ == "__main__":
    from PIL import Image
    rgba, fid, boxes, barn = build()
    im = np.full((SZ, SZ, 3), (104, 170, 62), np.float32) / 255
    a = rgba[..., 3:]; im = im * (1 - a) + rgba[..., :3] * a
    Image.fromarray((im * 255).astype(np.uint8)).save(ROOT / "renders" / "ep04_farmers" / "overview_map.png")
    print(boxes, "barn", barn)

# ---------------- the farm after Experiment 6 (for Experiment 7's zoom out, and later ones) ----------------
# Positions relative to Experiment 4's field (as FIELDS): #5 where it was in Experiment 5 (90 left, 20 up),
# #6 where it was in Experiment 6 (110 right, 40 down), #7 (the hay yard) in the free space on the left.
MORE = {5: dict(at=(-90, -20), title="Experiment #5", sub="the crop circle"),
        6: dict(at=(110, 40), title="Experiment #6", sub="switch!"),
        7: dict(at=(-170, 0), title="Experiment #7", sub="today: pi from hay!")}

def build_all():
    """build(), plus Experiment 5's crop circle and Experiment 6's three barns with their two bars of
    tractors (339 stay, 661 switch) painted in. Returns rgba, fid, boxes, barn (as build)."""
    import crops as CR, barns as BG
    rgba, fid, boxes, barn = build()
    g5, _ = CR.run(100044, size=N); c = N // 2
    ys, xs = np.nonzero(g5); k = g5[ys, xs]
    col = np.array([(0, 0, 0), (120, 80, 48), (222, 178, 70), (236, 120, 30)]) / 255
    px, py = xs - c - 90 + SZ // 2, ys - c - 20 + SZ // 2
    rgba[py, px, :3] = col[k]; rgba[py, px, 3] = 1; fid[py, px] = 5
    boxes[5] = (int(xs.min() - c - 90), int(ys.min() - c - 20), int(xs.max() - c - 90), int(ys.max() - c - 20))
    # #6: three red barns in a row (door squares at x -3.6, 0, +3.6 from 110; 3 squares wide) and, behind
    # them, the two bars: one square per 10 wins, 10 wide (stay on the left, switch on the right)
    g = BG.games(1, 1000); stay = int((g["pick"] == g["prize"]).sum()); switch = 1000 - stay
    bx0, by0 = 110, 40
    for dx in (-4, 0, 4):
        rgba[SZ // 2 + by0 - 4:SZ // 2 + by0 - 1, SZ // 2 + bx0 + dx - 1:SZ // 2 + bx0 + dx + 2, :3] = np.array((176, 46, 38)) / 255
        rgba[SZ // 2 + by0 - 4:SZ // 2 + by0 - 1, SZ // 2 + bx0 + dx - 1:SZ // 2 + bx0 + dx + 2, 3] = 1
    for side, wins in ((-4, stay), (4, switch)):
        rows = int(round(wins * 0.7 * 0.55 / 5.5))                  # the bars' real length in squares (0.7 per 10 wins)
        x0 = SZ // 2 + bx0 + side - 3; y1 = SZ // 2 + by0 - 9
        rgba[y1 - rows:y1, x0:x0 + 6, :3] = np.array((206, 34, 28)) / 255; rgba[y1 - rows:y1, x0:x0 + 6, 3] = 1
    fid[SZ // 2 + by0 - 60:SZ // 2 + by0, SZ // 2 + bx0 - 8:SZ // 2 + bx0 + 9][rgba[SZ // 2 + by0 - 60:SZ // 2 + by0,
        SZ // 2 + bx0 - 8:SZ // 2 + bx0 + 9, 3] > 0] = 6
    boxes[6] = (bx0 - 8, by0 - 60, bx0 + 8, by0)
    return rgba, fid, boxes, barn

# ---------------- the farm after Experiment 7 (for Experiment 8's zoom out) ----------------
# #7 (the hay yard) at -170, 0 from Experiment 4's field: its plank floor and the hay mountain (seen from
# above, a golden disc 12 squares across its middle); #8 (the garden) on the far left at -260, 0.
MORE8 = {7: dict(title="Experiment #7", sub="pi from hay"), 8: dict(title="Experiment #8", sub="today: what grows?")}

def build_upto7():
    """build_all(), plus Experiment 7's plank floor and hay mountain painted in."""
    rgba, fid, boxes, barn = build_all()
    h = SZ // 2
    x0, x1, y0, y1 = -178, -162, -4, 6                            # the plank floor
    rgba[h + y0:h + y1, h + x0:h + x1, :3] = np.array((176, 128, 82)) / 255; rgba[h + y0:h + y1, h + x0:h + x1, 3] = 1
    yy, xx = np.mgrid[-14:15, -14:15]; disc = xx ** 2 + yy ** 2 <= 12 ** 2   # the mountain
    shade = 0.85 + 0.15 * (1 - np.sqrt(xx ** 2 + yy ** 2) / 12)
    ys, xs = np.nonzero(disc); cy, cx = -12, -169
    rgba[h + cy + ys - 14, h + cx + xs - 14, :3] = (np.array((230, 196, 110)) / 255)[None] * shade[ys, xs, None]
    rgba[h + cy + ys - 14, h + cx + xs - 14, 3] = 1
    fid[h - 26:h + 7, h - 184:h - 154][rgba[h - 26:h + 7, h - 184:h - 154, 3] > 0] = 7
    boxes[7] = (-182, -24, -156, 6)
    return rgba, fid, boxes, barn

# ---------------- the farm after Experiment 8 (for Experiment 9's zoom out) ----------------
# #8 (the garden) on the far left at -260, 0 from Experiment 4's field: the long bed with the mustard,
# the apple trees and the tyre in its ring of weeds; #9 (Joe and three helpers) on the right at +220, 0.
MORE9 = {8: dict(title="Experiment #8", sub="what grows?"), 9: dict(title="Experiment #9", sub="today: 3 helpers")}

def build_upto8():
    """build_upto7(), plus Experiment 8's garden painted in."""
    rgba, fid, boxes, barn = build_upto7()
    h = SZ // 2; ox = -260
    def paint(x0, x1, y0, y1, rgb):
        rgba[h + y0:h + y1, h + ox + x0:h + ox + x1, :3] = np.array(rgb) / 255; rgba[h + y0:h + y1, h + ox + x0:h + ox + x1, 3] = 1
    paint(-6, 9, -2, 2, DIRT)                                        # the bed
    for x in (-4, 3, 4):                                             # mustard (the two in "both" too)
        paint(x, x + 1, -1, 1, (238, 206, 60))
    for x, r in ((0, 2), (5, 1)):                                    # the apple trees, from above
        paint(x - r, x + r + 1, -r - 1, r, (64, 140, 52))
    paint(6, 9, -2, 1, (40, 36, 34)); paint(7, 8, -1, 0, (90, 150, 60))   # the tyre and the weeds in it
    fid[h - 4:h + 4, h + ox - 8:h + ox + 11][rgba[h - 4:h + 4, h + ox - 8:h + ox + 11, 3] > 0] = 8
    boxes[8] = (ox - 7, -3, ox + 9, 3)
    return rgba, fid, boxes, barn
