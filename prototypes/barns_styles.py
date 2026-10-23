"""Experiment 6's look on two stills (the game, and the 1,000 games' results), with the handwritten
captions and notes of Experiments 3-5 laid over.

Usage: .venv/Scripts/python prototypes/barns_styles.py
Needs renders/ep06_barns/still_{game,results}.png (blender/barns_still.py).
Writes renders/ep06_barns/style_{game,results}.png and styles.jpg (side by side).
"""
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "renders" / "ep06_barns"
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

def shot(name, draw):
    im = Image.open(D / f"still_{name}.png").convert("RGB").resize((W, H), Image.BICUBIC)
    sp = json.loads((D / f"still_{name}.json").read_text())
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); draw(ImageDraw.Draw(ov), sp)
    im.paste(ov, (0, 0), ov); im.save(D / f"style_{name}.png"); return im

def game(dr, sp):
    text(dr, (70, 120), "Experiment #6", MARK(64), WHITE, 6, "la")
    for i, (x, y) in enumerate(sp["barns"]): text(dr, (x, y - 40), str(i + 1), MARK(96), WHITE, 7)
    dx, dy = sp["daisy"]
    arrow(dr, (dx + 120, dy + 230), (dx + 20, dy + 50), GOLD); text(dr, (dx + 160, dy + 280), "Daisy's pick", HAND(72), GOLD)
    gx, gy = sp["goat"]
    text(dr, (gx + 40, gy - 330), "goat!", HAND(84), WHITE)
    caption(dr, "I know where the tractor is, so I open a barn with a goat.", 9)

def results(dr, sp):
    for k, lab in (("stay", "stay"), ("switch", "switch")):
        x, y = sp["top"][k]; n = sp["wins"][k]
        text(dr, (x, y - 120), f"{n}", MARK(96), GOLD if k == "switch" else WHITE, 7)
        text(dr, (x, y - 45), f"{lab} wins", HAND(64), WHITE, 5)
    text(dr, (W - 70, 120), "1,000 games", HAND(80), WHITE, 6, "ra")
    caption(dr, "Staying won 339. Switching won 661!", 4)

ims = [shot("game", game), shot("results", results)]
sheet = Image.new("RGB", (2 * 540 + 30, 960 + 90), (250, 248, 240)); dr = ImageDraw.Draw(sheet)
for i, (im, lab) in enumerate(zip(ims, ("the game", "1,000 games: one tractor per win"))):
    sheet.paste(im.resize((540, 960), Image.LANCZOS), (10 + i * 550, 80))
    dr.text((20 + i * 550, 20), lab, font=HAND(46), fill=INK)
sheet.save(D / "styles.jpg", quality=92); print("saved", D / "styles.jpg")
