"""Lay style C's notes over the moving sample's frames: title, "me" / "Daisy!" arrows, round and
dirt counters, the hand-drawn dirt graph with a dot riding along it, "we meet!" and "spotless!".

Usage: .venv/Scripts/python prototypes/farmers_sample_compose.py
Reads renders/ep04_farmers/sample_frames/ (blender/farmers_sample.py); writes sample.mp4 (silent).
"""
import json, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
import farmers as FM
from common import FPS, ffmpeg, FFMPEG_THREADS, gentle
gentle()

D = ROOT / "renders" / "ep04_farmers"; FR = D / "sample_frames"
SCREEN = {int(k): v for k, v in json.loads((FR / "screen.json").read_text()).items() if v.get("joe")}
NF = max(SCREEN) + 1
W, H = 1080, 1920
F = str(ROOT / "assets" / "fonts") + "/"
HAND = lambda s: ImageFont.truetype(F + "PatrickHand-Regular.ttf", s)
MARK = lambda s: ImageFont.truetype(F + "PermanentMarker-Regular.ttf", s)
INK, GOLD, WHITE, BLUE = (32, 28, 30), (255, 214, 64), (255, 255, 255), (120, 190, 255)

def text(dr, xy, s, f, fill, stroke=6, anchor="mm"):
    dr.text(xy, s, font=f, fill=fill, stroke_width=stroke, stroke_fill=INK, anchor=anchor)

def arrow(dr, a, b, fill=WHITE, w=7):
    a, b = np.array(a, float), np.array(b, float); mid = (a + b) / 2 + np.array([-(b - a)[1], (b - a)[0]]) * 0.15
    pts = [tuple((1 - u) ** 2 * a + 2 * (1 - u) * u * mid + u ** 2 * b) for u in np.linspace(0, 1, 16)]
    d = b - pts[-3]; d /= np.linalg.norm(d) + 1e-9; n = np.array([-d[1], d[0]])
    head = [tuple(b - d * 30 + n * 16), tuple(b), tuple(b - d * 30 - n * 16)]
    for col, ww in ((INK, w + 6), (fill, w)):
        dr.line(pts, fill=col, width=ww, joint="curve"); dr.line(head, fill=col, width=ww, joint="curve")

def alpha(col, a): return col + (int(255 * a),)
def pop(tt, t0, t1, rise=0.2): return float(np.clip(min((tt - t0) / rise, (t1 - tt) / rise), 0, 1))

# the graph: dirt count over the whole 4,724 rounds (the sample only gets halfway, to the first 0)
_, h = FM.run(FM.RECORD, 4724, record=True); DIRT = np.array(h["dirt"], float)
GX0, GX1, GYB, GHT = 90, W - 90, 470, 160
gx = np.linspace(GX0, GX1, 300)
gy = GYB - np.interp(np.linspace(0, 4724, 300), np.arange(len(DIRT)), DIRT) / DIRT.max() * GHT
gy += np.random.default_rng(2).normal(0, 1.2, len(gx))
def graph(dr, rnd, a):
    for col, ww in ((INK, 10), (WHITE, 4)): dr.line([(GX0, GYB), (GX1, GYB)], fill=alpha(col, a), width=ww)
    pts = list(zip(gx, gy))
    for col, ww in ((INK, 12), (WHITE, 6)): dr.line(pts, fill=alpha(col, a), width=ww, joint="curve")
    cut = GX0 + (GX1 - GX0) * rnd / 4724
    done = [(x, y) for x, y in pts if x <= cut]
    if len(done) > 1:
        for col, ww in ((INK, 14), (GOLD, 8)): dr.line(done, fill=alpha(col, a), width=ww, joint="curve")
    py = np.interp(cut, gx, gy)
    dr.ellipse([cut - 14, py - 14, cut + 14, py + 14], fill=alpha(GOLD, a), outline=alpha(INK, a), width=5)
    text(dr, (GX0, GYB + 48), "dirt", HAND(56), alpha(WHITE, a), 5, "la")

ff = subprocess.Popen([ffmpeg(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                       "-r", str(FPS), "-i", "-", *FFMPEG_THREADS, "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                       "-pix_fmt", "yuv420p", str(D / "sample.mp4")], stdin=subprocess.PIPE)
t_meet = min(f for f, s in SCREEN.items() if s["round"] >= 1181) / FPS
t_clean = min(f for f, s in SCREEN.items() if s["round"] >= 2362) / FPS
for f in range(NF):
    tt = f / FPS; sp = SCREEN[f]
    im = Image.open(FR / f"f_{f:05d}.jpg").convert("RGB").resize((W, H), Image.BICUBIC)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); dr = ImageDraw.Draw(ov)
    a = pop(tt, 0, 3.2)
    if a: text(dr, (70, 120), "Experiment #4", MARK(64), alpha(WHITE, a), 6, "la")
    a = pop(tt, 0.4, 2.9)
    if a:
        jx, jy = sp["joe"][:2]; dx, dy = sp["daisy"][:2]
        left = jx < dx
        arrow(dr, (jx + (-170 if left else 170), jy + 260), (jx + (-20 if left else 20), jy + 60), alpha(BLUE, a))
        text(dr, (jx + (-200 if left else 200), jy + 310), "me", HAND(80), alpha(BLUE, a))
        arrow(dr, (dx + (170 if left else -170), dy - 260), (dx + (25 if left else -25), dy - 70), alpha(GOLD, a))
        text(dr, (dx + (200 if left else -200), dy - 310), "Daisy!", HAND(80), alpha(GOLD, a))
    if tt > 0.4:
        text(dr, (W - 70, 120), f"round {sp['round']:,}", HAND(70), WHITE, 6, "ra")
        text(dr, (W - 70, 200), f"dirt: {sp['dirt']}", HAND(70), WHITE, 6, "ra")
    a = min(1.0, max(0.0, (tt - 3.0) / 0.4))
    if a: graph(dr, sp["round"], a)
    a = pop(tt, t_meet - 0.1, t_meet + 1.4)
    if a: text(dr, (W / 2, 640), "we meet!", HAND(96), alpha(WHITE, a))
    a = pop(tt, t_clean, NF / FPS + 1)
    if a:
        text(dr, (W / 2, 760), "spotless!", HAND(130), alpha(GOLD, a))
        text(dr, (GX0 + (GX1 - GX0) / 2, GYB + 48), "0!", HAND(56), alpha(WHITE, a))
    im.paste(ov, (0, 0), ov)
    ff.stdin.write(np.asarray(im).tobytes())
ff.stdin.close(); ff.wait()
print("saved", D / "sample.mp4", f"({NF / FPS:.1f}s)")
