"""Experiment 8's look on four stills, with the handwritten captions and notes of the series laid over.

Usage: .venv/Scripts/python -X utf8 prototypes/garden_styles.py
Needs renders/ep08_plant/still_{mustard,apple,tyre,winter}.png (blender/garden_still.py).
Writes renders/ep08_plant/styles.jpg (all four side by side).
"""
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
D = ROOT / "renders" / "ep08_plant"
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
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); draw(ImageDraw.Draw(ov))
    im.paste(ov, (0, 0), ov); return im

def mustard(dr):
    text(dr, (70, 120), "Experiment #8", MARK(64), WHITE, 6, "la")
    text(dr, (W - 70, 130), "one season later", HAND(80), WHITE, 6, "ra")
    arrow(dr, (300, 560), (440, 760), GOLD); text(dr, (260, 510), "4 ft!", HAND(96), GOLD)
    caption(dr, "If you plant a mustard seed, you get mustard.", 7)

def apple(dr):
    text(dr, (W - 70, 130), "years later", HAND(80), WHITE, 6, "ra")
    arrow(dr, (250, 860), (260, 1080), WHITE); text(dr, (240, 810), "planted: red", HAND(76), WHITE)
    arrow(dr, (820, 560), (700, 760), (170, 230, 110)); text(dr, (860, 510), "grew: green", HAND(76), (170, 230, 110))
    caption(dr, "Just not the same apple.", 3)

def tyre(dr):
    text(dr, (W - 70, 130), "2 years later", HAND(80), WHITE, 6, "ra")
    arrow(dr, (330, 700), (440, 860), WHITE); text(dr, (300, 650), "weeds.", HAND(88), WHITE)
    caption(dr, "nothing. Well. Weeds. Those were seeds already.", 3)

def winter(dr):
    text(dr, (W - 70, 130), "winter #1", HAND(80), WHITE, 6, "ra")
    text(dr, (W / 2, 520), "still waiting.", HAND(96), WHITE)
    caption(dr, "And if you plant a rusty wheelbarrow tyre, and wait two years...", 9)

ims = [shot("mustard", mustard), shot("apple", apple), shot("tyre", tyre), shot("winter", winter)]
sheet = Image.new("RGB", (4 * 540 + 50, 960 + 90), (250, 248, 240)); dr = ImageDraw.Draw(sheet)
for i, (im, lab) in enumerate(zip(ims, ("mustard", "apple", "the tyre, 2 years on", "time-lapse: winter"))):
    sheet.paste(im.resize((540, 960), Image.LANCZOS), (10 + i * 550, 80))
    dr.text((20 + i * 550, 20), lab, font=HAND(46), fill=INK)
sheet.save(D / "styles.jpg", quality=92); print("saved", D / "styles.jpg")
