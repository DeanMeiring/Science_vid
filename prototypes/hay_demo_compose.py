"""Lay notes over the Experiment 7 live demo: the tally and pi's estimate, a deadpan label for each
kind of throw, "gold." / "not gold." on the first landings, and "this is a heap." when it grows.

Usage: .venv/Scripts/python -X utf8 prototypes/hay_demo_compose.py
Reads renders/ep07_pi/demo_frames/ (blender/hay_demo.py); writes demo.mp4 (silent).
"""
import json, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
from common import FPS, ffmpeg

D = ROOT / "renders" / "ep07_pi"; FR = D / "demo_frames"
SCREEN = {int(k): v for k, v in json.loads((FR / "screen.json").read_text()).items()}
NF = max(SCREEN) + 1
W, H = 1080, 1920
F = str(ROOT / "assets" / "fonts") + "/"
HAND = lambda s: ImageFont.truetype(F + "PatrickHand-Regular.ttf", s)
MARK = lambda s: ImageFont.truetype(F + "PermanentMarker-Regular.ttf", s)
INK, GOLD, WHITE = (32, 28, 30), (255, 214, 64), (255, 255, 255)

def text(dr, xy, s, f, fill, stroke=6, anchor="mm"):
    dr.text(xy, s, font=f, fill=fill, stroke_width=stroke, stroke_fill=INK, anchor=anchor)
def al(col, a): return col + (int(255 * a),)
def pop(tt, t0, t1, rise=0.15): return float(np.clip(min((tt - t0) / rise, (t1 - tt) / rise), 0, 1))

# the throws in blender/hay_demo.py, each with a label in Joe's deadpan voice
LABELS = [(0.5, "careful toss."), (2.7, "big fling."), (4.9, "fancy spin."), (6.9, "the fork."), (8.7, "both hands.")]

ff = subprocess.Popen([ffmpeg(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                       "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                       "-pix_fmt", "yuv420p", str(D / "demo.mp4")], stdin=subprocess.PIPE)
prev = 0; landings = []
for f in range(NF):
    tt = f / FPS; sp = SCREEN[f]
    if sp["straws"] > prev and len(landings) < 3:                 # remember the first landings and whether they were gold
        landings.append((tt, sp["gold"] > (SCREEN[f - 1]["gold"] if f else 0)))
    prev = sp["straws"]
    im = Image.open(FR / f"f_{f:05d}.jpg").convert("RGB").resize((W, H), Image.BICUBIC)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); dr = ImageDraw.Draw(ov)
    a = pop(tt, 0, 3.0)
    if a: text(dr, (70, 120), "Experiment #7", MARK(64), al(WHITE, a), 6, "la")
    n, g = sp["straws"], sp["gold"]
    text(dr, (W - 70, 120), f"straws: {n:,}", HAND(76), WHITE, 6, "ra")
    text(dr, (W - 70, 200), f"gold: {g:,}", HAND(76), GOLD, 6, "ra")
    if g: text(dr, (W - 70, 290), f"2 × {n:,} ÷ {g:,} = {2 * n / g:.2f}", HAND(60), WHITE, 5, "ra")
    jx, jy = sp["joe"]
    for t0, lab in LABELS:
        a = pop(tt, t0, t0 + 1.6)
        if a: text(dr, (min(max(jx, 230), W - 230), jy - 330), lab, HAND(84), al(WHITE, a))
    for t0, gold in landings:
        a = pop(tt, t0, t0 + 1.1)
        if a: text(dr, (W / 2, 1250), "gold." if gold else "not gold.", HAND(100), al(GOLD if gold else WHITE, a))
    a = pop(tt, 12.2, 15.0)
    if a:
        hx, hy = sp["heap"]; text(dr, (min(max(hx, 260), W - 260), max(hy - 60, 380)), "this is a heap.", HAND(84), al(WHITE, a))
    a = pop(tt, 10.8, 13.4)
    if a: text(dr, (min(max(jx, 230), W - 230), jy - 330), "backing away.", HAND(84), al(WHITE, a))
    im.paste(ov, (0, 0), ov)
    ff.stdin.write(np.asarray(im).tobytes())
ff.stdin.close(); ff.wait()
print("saved", D / "demo.mp4", f"({NF / FPS:.1f}s)")
