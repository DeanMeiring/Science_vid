"""Lay style C over the moving sample's frames: title, step / SPEED / mirrors counters, and the
mirror flash (a glowing line down the middle, with a gap around Joe, and "MIRROR!").

While slow, each mirror moment flashes once; while fast every frame is a mirror moment, so the
line glows steadily. A big "MIRROR!" at the end (step 10,012).

Usage: .venv/Scripts/python prototypes/crops_sample_compose.py
Reads renders/ep05_crops/sample_frames/ (blender/crops_sample.py); writes sample.mp4 (silent).
"""
import json, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
from common import FPS, ffmpeg, FFMPEG_THREADS, gentle
gentle()

D = ROOT / "renders" / "ep05_crops"; FR = D / "sample_frames"
SCREEN = {int(k): v for k, v in json.loads((FR / "screen.json").read_text()).items()}
NF = max(SCREEN) + 1
W, H = 1080, 1920
F = str(ROOT / "assets" / "fonts") + "/"
HAND = lambda s: ImageFont.truetype(F + "PatrickHand-Regular.ttf", s)
MARK = lambda s: ImageFont.truetype(F + "PermanentMarker-Regular.ttf", s)
INK, GOLD, WHITE = (32, 28, 30), (255, 214, 64), (255, 255, 255)

def text(dr, xy, s, f, fill, stroke=6, anchor="mm"):
    dr.text(xy, s, font=f, fill=fill, stroke_width=stroke, stroke_fill=INK, anchor=anchor)
def alpha(col, a): return col + (int(255 * a),)
def pop(tt, t0, t1, rise=0.15): return float(np.clip(min((tt - t0) / rise, (t1 - tt) / rise), 0, 1))

def mirror_line(arr, sp, strength):
    """Glow along the mirror line, leaving a gap where Joe stands."""
    (ax, ay), (bx, by) = sp["axis"]; jx, jy = sp["joe"]
    m = Image.new("L", (W, H), 0); dr = ImageDraw.Draw(m)
    dr.line([(ax, ay), (bx, by)], fill=255, width=24)
    dr.ellipse([jx - 55, jy - 70, jx + 55, jy + 70], fill=0)            # keep Joe visible
    glow = np.array(m.filter(ImageFilter.GaussianBlur(14.0)), np.float32) / 255 * 0.8
    m2 = Image.new("L", (W, H), 0); d2 = ImageDraw.Draw(m2); d2.line([(ax, ay), (bx, by)], fill=255, width=6)
    d2.ellipse([jx - 55, jy - 70, jx + 55, jy + 70], fill=0)
    a = np.maximum(glow, np.array(m2, np.float32) / 255)[..., None] * strength
    return arr * (1 - a) + np.array([255, 250, 225], np.float32) * a

ff = subprocess.Popen([ffmpeg(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                       "-r", str(FPS), "-i", "-", *FFMPEG_THREADS, "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                       "-pix_fmt", "yuv420p", str(D / "sample.mp4")], stdin=subprocess.PIPE)
last_flash = -9.0
for f in range(NF):
    tt = f / FPS; sp = SCREEN[f]
    arr = np.array(Image.open(FR / f"f_{f:05d}.jpg").convert("RGB").resize((W, H), Image.BICUBIC), np.float32)
    if sp["mirror"] and not sp["fast"] and (f == 0 or SCREEN[f - 1]["step"] != sp["step"]): last_flash = tt
    flash = max(0.0, 1 - (tt - last_flash) / 0.6) if not sp["fast"] else 0.55
    if tt >= 9.0: flash = max(flash, min(1.0, (tt - 9.0) / 0.2))
    if flash > 0.01: arr = mirror_line(arr, sp, flash)
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); dr = ImageDraw.Draw(ov)
    a = pop(tt, 0, 3.2)
    if a: text(dr, (70, 120), "Experiment #5", MARK(64), alpha(WHITE, a), 6, "la")
    text(dr, (W - 70, 120), f"step {sp['step']:,}", HAND(80), WHITE, 6, "ra")
    spd = sp["speed"] / 4.0                                  # SPEED x1 = the slow walk (4 steps a second)
    if sp["fast"] and spd > 4: text(dr, (W - 70, 200), f"SPEED ×{int(round(spd, -1 if spd < 1000 else -2)):,}", HAND(56), GOLD, 5, "ra")
    text(dr, (W - 70, 270 if sp["fast"] else 205), f"mirrors: {sp['mirrors']}", HAND(64), GOLD, 5, "ra")
    top = min(sp["axis"], key=lambda p: p[1])
    a = max(flash if not sp["fast"] else 0, 1.0 if tt >= 9.0 else 0)
    if a > 0.05:
        size = 130 if tt >= 9.0 else 100
        text(dr, (top[0], max(360, top[1] - 90)), "MIRROR!", MARK(size), alpha(GOLD, a), 8)
    im.paste(ov, (0, 0), ov)
    ff.stdin.write(np.asarray(im).tobytes())
ff.stdin.close(); ff.wait()
print("saved", D / "sample.mp4", f"({NF / FPS:.1f}s)")
