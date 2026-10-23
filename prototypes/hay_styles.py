"""Experiment 7's look on three stills (the first straws, 2,000, all 100,000), with the handwritten
captions and notes of Experiments 3-6 laid over, and the running estimate of pi.

Usage: .venv/Scripts/python prototypes/hay_styles.py
Needs renders/ep07_pi/still_{close,many,carpet}.png (blender/hay_still.py).
Writes renders/ep07_pi/style_<shot>.png and styles.jpg (side by side).
"""
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "renders" / "ep07_pi"
W, H = 1080, 1920
F = str(ROOT / "assets" / "fonts") + "/"
HAND = lambda s: ImageFont.truetype(F + "PatrickHand-Regular.ttf", s)
MARK = lambda s: ImageFont.truetype(F + "PermanentMarker-Regular.ttf", s)
INK, GOLD, WHITE = (32, 28, 30), (255, 214, 64), (255, 255, 255)

def text(dr, xy, s, f, fill, stroke=6, anchor="mm"):
    dr.text(xy, s, font=f, fill=fill, stroke_width=stroke, stroke_fill=INK, anchor=anchor)

def arrow(dr, a, b, fill=WHITE, w=7):
    a, b = np.array(a, float), np.array(b, float); mid = (a + b) / 2 + np.array([-(b - a)[1], (b - a)[0]]) * 0.15
    pts = [tuple((1 - u) ** 2 * a + 2 * (1 - u) * u * mid + u ** 2 * b) for u in np.linspace(0, 1, 16)]
    d = b - pts[-3]; d /= np.linalg.norm(d) + 1e-9; n = np.array([-d[1], d[0]])
    head = [tuple(b - d * 30 + n * 16), tuple(b), tuple(b - d * 30 - n * 16)]
    for col, ww in ((INK, w + 6), (fill, w)):
        dr.line(pts, fill=col, width=ww, joint="curve"); dr.line(head, fill=col, width=ww, joint="curve")

def caption(dr, cap, active):
    f = HAND(84); words = cap.split(); rows, row = [], []
    for i, w in enumerate(words):
        if row and dr.textlength(" ".join(x for x, _ in row + [(w, i)]), font=f) > W - 160: rows.append(row); row = []
        row.append((w, i))
    rows.append(row); y = min(1590, 1860 - 92 * len(rows))
    for r in rows:
        line = " ".join(w for w, _ in r); x = (W - dr.textlength(line, font=f)) / 2
        for w, i in r:
            dr.text((x, y), w, font=f, fill=GOLD if i == active else WHITE, stroke_width=6, stroke_fill=INK)
            x += dr.textlength(w + " ", font=f)
        y += 92

def counters(dr, n, h, big=False):
    """The tally top right, and pi's running estimate: 2 x straws / crossings."""
    text(dr, (W - 70, 120), f"straws: {n:,}", HAND(76), WHITE, 6, "ra")
    text(dr, (W - 70, 200), f"cross: {h:,}", HAND(76), GOLD, 6, "ra")
    est = 2 * n / h
    if big: text(dr, (W / 2, 440), f"π ≈ {est:.2f}!", HAND(170), GOLD, 9)     # the marker font has no π
    else: text(dr, (W - 70, 300), f"2 × {n:,} ÷ {h:,} = {est:.2f}", HAND(62), WHITE, 5, "ra")

def shot(name, draw):
    im = Image.open(D / f"still_{name}.png").convert("RGB").resize((W, H), Image.BICUBIC)
    sp = json.loads((D / f"still_{name}.json").read_text())
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); draw(ImageDraw.Draw(ov), sp)
    im.paste(ov, (0, 0), ov); im.save(D / f"style_{name}.png"); return im

def close(dr, sp):
    text(dr, (70, 120), "Experiment #7", MARK(64), WHITE, 6, "la")
    counters(dr, sp["n"], sp["cross"])
    pts, cr = sp["straws"], sp["cross_list"]
    i_yes = next(i for i, c_ in enumerate(cr) if c_); i_no = next(i for i, c_ in enumerate(cr) if not c_)
    (yx, yy), (nx, ny) = pts[i_yes], pts[i_no]
    arrow(dr, (yx + 160, yy - 220), (yx + 15, yy - 25), GOLD); text(dr, (yx + 200, yy - 270), "crosses!", HAND(76), GOLD)
    arrow(dr, (nx - 120, ny - 230), (nx - 10, ny - 25), WHITE); text(dr, (nx - 150, ny - 280), "doesn't", HAND(76), WHITE)
    caption(dr, "This one does. This one doesn't.", 2)

def many(dr, sp):
    counters(dr, sp["n"], sp["cross"])
    caption(dr, "A thousand: 3.03.", 2)

def carpet(dr, sp):
    counters(dr, sp["n"], sp["cross"], big=True)
    caption(dr, "A hundred thousand straws... 3.14!", 5)

ims = [shot("close", close), shot("many", many), shot("carpet", carpet)]
sheet = Image.new("RGB", (3 * 540 + 40, 960 + 90), (250, 248, 240)); dr = ImageDraw.Draw(sheet)
for i, (im, lab) in enumerate(zip(ims, ("the first straws", "2,000 straws", "100,000 straws"))):
    sheet.paste(im.resize((540, 960), Image.LANCZOS), (10 + i * 550, 80))
    dr.text((20 + i * 550, 20), lab, font=HAND(46), fill=INK)
sheet.save(D / "styles.jpg", quality=92); print("saved", D / "styles.jpg")
