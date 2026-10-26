"""Three looks for Experiment 4 on the same moment (round 1,178, the biggest mess), with
Experiment 3's handwritten captions and notes laid over the Blender stills.

Usage: .venv/Scripts/python prototypes/farmers_styles.py
Needs renders/ep04_farmers/still_{blocks,colours}_1178.png (blender/farmers_still.py).
Writes renders/ep04_farmers/style_<name>.png and styles.jpg (all three side by side).

  blocks   dirt as raised brown blocks, like Experiment 1
  colours  each square painted in the colour of the farmer who dug it (Joe gold, helper blue)
  graph    colours, plus a hand-drawn graph of the dirt count: up, back down to zero, up, down
"""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
import farmers as FM

D = ROOT / "renders" / "ep04_farmers"
W, H = 1080, 1920
F = str(ROOT / "assets" / "fonts") + "/"
HAND = lambda s: ImageFont.truetype(F + "PatrickHand-Regular.ttf", s)
MARK = lambda s: ImageFont.truetype(F + "PermanentMarker-Regular.ttf", s)
INK, GOLD, WHITE, BLUE = (32, 28, 30), (255, 214, 64), (255, 255, 255), (120, 190, 255)
R = 1178
CAP, ACTIVE = "A hundred rounds. A thousand. What a mess!", 6

def text(dr, xy, s, f, fill, stroke=6, anchor="mm"):
    dr.text(xy, s, font=f, fill=fill, stroke_width=stroke, stroke_fill=INK, anchor=anchor)

def arrow(dr, a, b, fill=WHITE, w=7):
    a, b = np.array(a, float), np.array(b, float); mid = (a + b) / 2 + np.array([-(b - a)[1], (b - a)[0]]) * 0.15
    pts = [tuple((1 - u) ** 2 * a + 2 * (1 - u) * u * mid + u ** 2 * b) for u in np.linspace(0, 1, 16)]
    d = b - pts[-3]; d /= np.linalg.norm(d) + 1e-9; n = np.array([-d[1], d[0]])
    head = [tuple(b - d * 30 + n * 16), tuple(b), tuple(b - d * 30 - n * 16)]
    for col, ww in ((INK, w + 6), (fill, w)):
        dr.line(pts, fill=col, width=ww, joint="curve"); dr.line(head, fill=col, width=ww, joint="curve")

def caption(dr):
    f = HAND(84); words = CAP.split(); rows, row = [], []
    for i, w in enumerate(words):
        if row and dr.textlength(" ".join(x for x, _ in row + [(w, i)]), font=f) > W - 160: rows.append(row); row = []
        row.append((w, i))
    rows.append(row); y = min(1590, 1860 - 92 * len(rows))
    for r in rows:
        line = " ".join(w for w, _ in r); x = (W - dr.textlength(line, font=f)) / 2
        for w, i in r:
            dr.text((x, y), w, font=f, fill=GOLD if i == ACTIVE else WHITE, stroke_width=6, stroke_fill=INK)
            x += dr.textlength(w + " ", font=f)
        y += 92

def notes(dr, sp, coloured):
    text(dr, (70, 120), "Experiment #4", MARK(64), WHITE, 6, "la")
    (jx, jy), (hx, hy) = sp["joe"], sp["helper"]
    arrow(dr, (jx - 30, jy + 250), (jx - 8, jy + 40), GOLD if coloured else WHITE)
    text(dr, (jx - 40, jy + 300), "me", HAND(78), GOLD if coloured else WHITE)
    arrow(dr, (hx + 150, hy - 230), (hx + 18, hy - 70), BLUE if coloured else WHITE)
    text(dr, (hx + 175, hy - 280), "my helper", HAND(78), BLUE if coloured else WHITE)
    text(dr, (W - 70, 120), f"round {R:,}", HAND(70), WHITE, 6, "ra")
    text(dr, (W - 70, 200), f"dirt: {sp['dirt']}", HAND(70), WHITE, 6, "ra")

def graph(dr):
    """The dirt count over the whole 4,724 rounds, hand-drawn style, with a dot at round R."""
    _, h = FM.run(FM.RECORD, 4724, record=True); d = np.array(h["dirt"], float)
    x0, x1, yb, ht = 90, W - 90, 520, 170
    xs = np.linspace(x0, x1, 240); ys = yb - np.interp(np.linspace(0, 4724, 240), np.arange(len(d)), d) / d.max() * ht
    wob = np.random.default_rng(2).normal(0, 1.2, len(xs))
    pts = list(zip(xs, ys + wob))
    dr.line([(x0, yb), (x1, yb)], fill=INK, width=10); dr.line([(x0, yb), (x1, yb)], fill=WHITE, width=4)
    for col, ww in ((INK, 12), (WHITE, 6)): dr.line(pts, fill=col, width=ww, joint="curve")
    done = [(x, y) for x, y in pts if x <= x0 + (x1 - x0) * R / 4724]
    for col, ww in ((INK, 14), (GOLD, 8)): dr.line(done, fill=col, width=ww, joint="curve")
    px, py = done[-1]; dr.ellipse([px - 14, py - 14, px + 14, py + 14], fill=GOLD, outline=INK, width=5)
    text(dr, (x0, yb + 50), "dirt", HAND(56), WHITE, 5, "la")
    for r_, lab in ((2362, "0!"), (4724, "0!")):
        gx = x0 + (x1 - x0) * r_ / 4724; text(dr, (gx, yb + 50), lab, HAND(56), WHITE, 5, "mm")

def look(name, still, coloured, with_graph):
    im = Image.open(D / still).convert("RGB").resize((W, H), Image.BICUBIC)
    sp = json.loads((D / still).with_suffix(".json").read_text())
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); dr = ImageDraw.Draw(ov)
    notes(dr, sp, coloured)
    if with_graph: graph(dr)
    caption(dr)
    im.paste(ov, (0, 0), ov); im.save(D / f"style_{name}.png"); return im

ims = [look("blocks", f"still_blocks_{R}.png", False, False),
       look("colours", f"still_colours_{R}.png", True, False),
       look("graph", f"still_colours_{R}.png", True, True)]
sheet = Image.new("RGB", (3 * 540 + 40, 960 + 90), (250, 248, 240)); dr = ImageDraw.Draw(sheet)
for i, (im, lab) in enumerate(zip(ims, ("A  dirt blocks", "B  who dug it", "C  B + dirt graph"))):
    sheet.paste(im.resize((540, 960), Image.LANCZOS), (10 + i * 550, 80))
    dr.text((20 + i * 550, 20), lab, font=HAND(46), fill=INK)
sheet.save(D / "styles.jpg", quality=92); print("saved", D / "styles.jpg")
