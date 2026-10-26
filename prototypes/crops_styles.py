"""Three looks for Experiment 5 on the same mirror moment (step 10,012), with Experiment 3-4's
handwritten captions and notes laid over the Blender stills.

Usage: .venv/Scripts/python prototypes/crops_styles.py
Needs renders/ep05_crops/still_10012_p{54,78}.png (blender/crops_still.py).
Writes renders/ep05_crops/style_<name>.png and styles.jpg (all three side by side).

  tilted   the usual tilted camera (54 deg), looking along the mirror line
  above    nearly straight down (78 deg): the field reads like a crop circle
  flash    from above, plus the mirror moment: a glowing line down the middle and "mirror!"
"""
import json, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
import crops as CR

D = ROOT / "renders" / "ep05_crops"
W, H = 1080, 1920
F = str(ROOT / "assets" / "fonts") + "/"
HAND = lambda s: ImageFont.truetype(F + "PatrickHand-Regular.ttf", s)
MARK = lambda s: ImageFont.truetype(F + "PermanentMarker-Regular.ttf", s)
INK, GOLD, WHITE = (32, 28, 30), (255, 214, 64), (255, 255, 255)
STEP = 10012
CAP, ACTIVE = "Ten thousand: mirror again.", 3
_, hist = CR.run(STEP, size=701); c = 350
MIRRORS = int(((hist[1:, 0] == c) & (hist[1:, 1] == c) & (hist[1:, 2] == 0)).sum())

def text(dr, xy, s, f, fill, stroke=6, anchor="mm"):
    dr.text(xy, s, font=f, fill=fill, stroke_width=stroke, stroke_fill=INK, anchor=anchor)

def caption(dr):
    f = HAND(84); words = CAP.split(); x = (W - dr.textlength(CAP, font=f)) / 2; y = 1640
    for i, w in enumerate(words):
        dr.text((x, y), w, font=f, fill=GOLD if i == ACTIVE else WHITE, stroke_width=6, stroke_fill=INK)
        x += dr.textlength(w + " ", font=f)

def notes(dr):
    text(dr, (70, 120), "Experiment #5", MARK(64), WHITE, 6, "la")
    text(dr, (W - 70, 120), f"step {STEP:,}", HAND(80), WHITE, 6, "ra")
    text(dr, (W - 70, 205), f"mirrors: {MIRRORS}", HAND(64), GOLD, 5, "ra")

def flash(im, sp):
    """The mirror moment: a glowing line along the mirror, and a note."""
    (ax, ay), (bx, by) = sp["axis"]
    glow = Image.new("L", (W, H), 0); gd = ImageDraw.Draw(glow)
    gd.line([(ax, ay), (bx, by)], fill=255, width=26)
    glow = glow.filter(ImageFilter.GaussianBlur(14.0))
    core = Image.new("L", (W, H), 0); ImageDraw.Draw(core).line([(ax, ay), (bx, by)], fill=255, width=7)
    a = np.maximum(np.array(glow, np.float32) / 255 * 0.8, np.array(core, np.float32) / 255)[..., None]
    arr = np.array(im, np.float32); arr = arr * (1 - a) + np.array([255, 250, 225], np.float32) * a
    im = Image.fromarray(arr.astype(np.uint8))
    dr = ImageDraw.Draw(im)
    top = min((ax, ay), (bx, by), key=lambda p: p[1])
    text(dr, (top[0], max(330, top[1] - 90)), "mirror!", MARK(110), GOLD, 8)
    return im

def look(name, still, with_flash):
    im = Image.open(D / still).convert("RGB").resize((W, H), Image.BICUBIC)
    sp = json.loads((D / still).with_suffix(".json").read_text())
    if with_flash: im = flash(im, sp)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); dr = ImageDraw.Draw(ov)
    notes(dr); caption(dr)
    im.paste(ov, (0, 0), ov); im.save(D / f"style_{name}.png"); return im

ims = [look("tilted", f"still_{STEP}_p54.png", False), look("above", f"still_{STEP}_p78.png", False),
       look("flash", f"still_{STEP}_p78.png", True)]
sheet = Image.new("RGB", (3 * 540 + 40, 960 + 90), (250, 248, 240)); dr = ImageDraw.Draw(sheet)
for i, (im, lab) in enumerate(zip(ims, ("A  tilted", "B  from above", "C  B + mirror flash"))):
    sheet.paste(im.resize((540, 960), Image.LANCZOS), (10 + i * 550, 80))
    dr.text((20 + i * 550, 20), lab, font=HAND(46), fill=INK)
sheet.save(D / "styles.jpg", quality=92); print("saved", D / "styles.jpg", "| mirrors so far:", MIRRORS)
