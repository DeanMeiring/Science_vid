"""Four looks for Experiment 3 on the same still, to pick a less slick, more personal style.

Usage: .venv/Scripts/python prototypes/style_samples.py renders/ep03_sheep/still_seed3_40.png
Writes renders/ep03_sheep/styles.jpg (all four side by side) and style_<name>.png.

  clean     the look of Experiments 1-2 (bold captions, counter)
  phone     like Joe filmed it on his phone: a bit tilted, grain, warm, REC, handwritten captions
  notebook  the shot taped into Joe's notebook: paper, tape, scribbled notes and arrows
  farmcam   an old security camera on the barn: timestamp, scanlines, faded colour
"""
import math, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = Path(__file__).resolve().parent.parent
F = str(ROOT / "assets" / "fonts") + "/"
def font(n, s): return ImageFont.truetype(F + n, s)
W, H = 1080, 1920
SRC = Image.open(sys.argv[1] if len(sys.argv) > 1 else ROOT / "renders/ep03_sheep/still_seed3_40.png").convert("RGB")
OUT = ROOT / "renders" / "ep03_sheep"
CAP = "Every step, she picks a random direction."
DAISY, BARN = (655, 1115), (530, 860)          # where they are in the still (pixels)
rng = np.random.default_rng(4)

def outlined(dr, xy, txt, f, fill, stroke=6, sfill=(0, 0, 0), anchor="mm"):
    dr.text(xy, txt, font=f, fill=fill, stroke_width=stroke, stroke_fill=sfill, anchor=anchor)

def wrap(dr, txt, f, maxw):
    rows, cur = [], ""
    for w in txt.split():
        t = (cur + " " + w).strip()
        if cur and dr.textlength(t, font=f) > maxw: rows.append(cur); cur = w
        else: cur = t
    return rows + [cur]

def grain(img, amount):
    a = np.asarray(img, np.float32) + rng.normal(0, amount, (img.height, img.width, 1))
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))

def vignette(img, strength):
    y, x = np.mgrid[0:img.height, 0:img.width]
    r = np.hypot((x - img.width / 2) / (img.width / 2), (y - img.height / 2) / (img.height / 2))
    m = np.clip(1 - strength * np.maximum(0, r - 0.55) ** 1.6, 0, 1)[..., None]
    return Image.fromarray((np.asarray(img, np.float32) * m).astype(np.uint8))

# ---------------- clean (Experiments 1-2) ----------------
def clean():
    im = SRC.copy(); dr = ImageDraw.Draw(im)
    outlined(dr, (W / 2, 140), "EXPERIMENT #3", font("Inter-Black.ttf", 40), (255, 214, 64), 3)
    outlined(dr, (W / 2, 225), "STEP 40", font("Anton.ttf", 110), "white", 5)
    y = 1600
    for row in wrap(dr, CAP.upper(), font("Inter-Black.ttf", 66), W - 140):
        outlined(dr, (W / 2, y), row, font("Inter-Black.ttf", 66), "white", 7); y += 82
    return im

# ---------------- phone video ----------------
def phone():
    im = SRC.rotate(-2.2, resample=Image.BICUBIC, expand=False, fillcolor=(80, 140, 60))
    im = im.crop((40, 70, W - 40, H - 70)).resize((W, H), Image.BICUBIC)           # zoom in a touch (hides corners)
    a = np.asarray(im, np.float32); a = a * np.array([1.06, 1.0, 0.9]) + 6           # warm
    im = vignette(grain(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)), 7), 0.9)
    dr = ImageDraw.Draw(im)
    dr.ellipse((60, 92, 92, 124), fill=(235, 40, 40)); dr.text((106, 84), "REC  0:07", font=font("Inter-Bold.ttf", 40), fill="white")
    dr.text((W - 60, 84), "experiment #3", font=font("PatrickHand-Regular.ttf", 54), fill="white", anchor="ra")
    f = font("PatrickHand-Regular.ttf", 74); y = 1600
    for row in wrap(dr, CAP, f, W - 160):
        outlined(dr, (W / 2, y), row, f, "white", 5, (30, 30, 30)); y += 84
    outlined(dr, (W - 70, 1430), "step 40", font("PatrickHand-Regular.ttf", 60), (255, 230, 120), 4, (30, 30, 30), "rm")
    return im

# ---------------- Joe's notebook ----------------
def notebook():
    paper = np.full((H, W, 3), (247, 240, 222), np.float32)
    paper[np.arange(H) % 64 < 2] = (196, 214, 232)                                 # ruled lines
    paper[:, 118:121] = (226, 120, 120)                                            # margin line
    im = grain(Image.fromarray(paper.astype(np.uint8)), 4)
    shot = SRC.crop((40, 420, W - 40, 1500)).resize((880, 950), Image.BICUBIC)
    border = Image.new("RGB", (912, 982), "white"); border.paste(shot, (16, 16))
    border = border.rotate(1.6, resample=Image.BICUBIC, expand=True, fillcolor=(247, 240, 222))
    sh = Image.new("L", border.size, 0); ImageDraw.Draw(sh).rectangle((10, 10, border.width - 10, border.height - 10), fill=110)
    im.paste((90, 80, 60), (98, 318), sh.filter(ImageFilter.GaussianBlur(14)))
    im.paste(border, (84, 300))
    dr = ImageDraw.Draw(im, "RGBA")
    for x0, y0, ang in ((150, 285, -20), (W - 300, 285, 18)):                     # sticky tape
        tape = Image.new("RGBA", (190, 60), (240, 228, 170, 170)); tape = tape.rotate(ang, expand=True)
        im.paste(tape, (x0, y0), tape)
    dr = ImageDraw.Draw(im)
    mk = font("PermanentMarker-Regular.ttf", 64)
    dr.text((150, 110), "Experiment #3", font=mk, fill=(40, 40, 60))
    dr.text((150, 190), "Daisy got out AGAIN", font=font("PatrickHand-Regular.ttf", 62), fill=(60, 60, 90))
    # notes and arrows on the photo (photo maps 40..1040 x 420..1500 -> ~100..980 x ~316..1266)
    px = lambda p: (100 + (p[0] - 40) * 0.88, 316 + (p[1] - 420) * 0.88)
    dx, dy = px(DAISY); bx, by = px(BARN)
    hand = font("PatrickHand-Regular.ttf", 58); red = (205, 40, 40)
    dr.text((dx + 70, dy + 120), "Daisy!", font=hand, fill=red)
    dr.line([(dx + 80, dy + 115), (dx + 22, dy + 30)], fill=red, width=6); dr.line([(dx + 22, dy + 30), (dx + 50, dy + 40)], fill=red, width=6)
    dr.text((bx - 330, by - 160), "home", font=hand, fill=red)
    dr.line([(bx - 200, by - 120), (bx - 50, by - 40)], fill=red, width=6); dr.line([(bx - 50, by - 40), (bx - 85, by - 40)], fill=red, width=6)
    f = font("PatrickHand-Regular.ttf", 76); y = 1420
    for row in wrap(dr, CAP, f, W - 260):
        dr.text((150, y), row, font=f, fill=(40, 40, 60)); y += 90
    dr.text((150, 1700), "step 40  ||||  ||||  ||||  ...", font=font("PatrickHand-Regular.ttf", 60), fill=(90, 90, 120))
    return im

# ---------------- farm security camera ----------------
def farmcam():
    g = ImageOps.grayscale(SRC).convert("RGB")
    im = Image.blend(SRC, g, 0.55)
    a = np.asarray(im, np.float32) * np.array([0.95, 1.02, 0.95])
    a[np.arange(H) % 4 < 1] *= 0.82                                               # scanlines
    im = vignette(grain(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)), 9), 1.2)
    dr = ImageDraw.Draw(im)
    vt = font("VT323-Regular.ttf", 64)
    dr.text((50, 70), "FARM CAM 2", font=vt, fill=(255, 255, 255))
    dr.text((W - 50, 70), "22-10-2026 06:14:07", font=vt, fill=(255, 255, 255), anchor="ra")
    dr.ellipse((50, 160, 80, 190), fill=(235, 40, 40)); dr.text((95, 148), "REC", font=vt, fill=(255, 255, 255))
    dr.rectangle((DAISY[0] - 60, DAISY[1] - 60, DAISY[0] + 60, DAISY[1] + 50), outline=(255, 214, 64), width=4)
    dr.text((DAISY[0] - 60, DAISY[1] - 110), "SHEEP #1", font=font("VT323-Regular.ttf", 48), fill=(255, 214, 64))
    f = font("VT323-Regular.ttf", 84); y = 1580
    for row in wrap(dr, CAP.upper(), f, W - 140):
        dr.rectangle((W / 2 - dr.textlength(row, font=f) / 2 - 16, y - 50, W / 2 + dr.textlength(row, font=f) / 2 + 16, y + 40), fill=(0, 0, 0))
        dr.text((W / 2, y), row, font=f, fill=(255, 255, 255), anchor="mm"); y += 100
    dr.text((W - 50, 1460), "STEP 0040", font=vt, fill=(255, 214, 64), anchor="ra")
    return im

looks = {"clean": clean(), "phone": phone(), "notebook": notebook(), "farmcam": farmcam()}
for k, im in looks.items(): im.save(OUT / f"style_{k}.png")
sheet = Image.new("RGB", (4 * 540 + 3 * 20, 960 + 70), (24, 24, 30)); dr = ImageDraw.Draw(sheet)
for i, (k, im) in enumerate(looks.items()):
    sheet.paste(im.resize((540, 960), Image.LANCZOS), (i * 560, 70))
    dr.text((i * 560 + 270, 36), f"{i + 1}. {k}", font=font("Inter-Bold.ttf", 34), fill="white", anchor="mm")
sheet.save(OUT / "styles.jpg", quality=90)
print("saved", OUT / "styles.jpg")
