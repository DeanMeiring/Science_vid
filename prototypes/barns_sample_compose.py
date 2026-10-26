"""Lay Experiment 6's notes over the moving sample's frames: title, barn numbers, "Daisy's pick",
"goat!", then over the lots: the live counts above each bar of tractors and the games played.

Usage: .venv/Scripts/python prototypes/barns_sample_compose.py
Reads renders/ep06_barns/sample_frames/ (blender/barns_sample.py); writes sample.mp4 (silent).
"""
import json, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
from common import FPS, ffmpeg, FFMPEG_THREADS, gentle
gentle()

D = ROOT / "renders" / "ep06_barns"; FR = D / "sample_frames"
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
def pop(tt, t0, t1, rise=0.2): return float(np.clip(min((tt - t0) / rise, (t1 - tt) / rise), 0, 1))
def arrow(dr, a, b, fill=WHITE, w=7):
    a, b = np.array(a, float), np.array(b, float); mid = (a + b) / 2 + np.array([-(b - a)[1], (b - a)[0]]) * 0.15
    pts = [tuple((1 - u) ** 2 * a + 2 * (1 - u) * u * mid + u ** 2 * b) for u in np.linspace(0, 1, 16)]
    d = b - pts[-3]; d /= np.linalg.norm(d) + 1e-9; n = np.array([-d[1], d[0]])
    head = [tuple(b - d * 30 + n * 16), tuple(b), tuple(b - d * 30 - n * 16)]
    for col, ww in ((INK, w + 6), (fill, w)):
        dr.line(pts, fill=col, width=ww, joint="curve"); dr.line(head, fill=col, width=ww, joint="curve")

ff = subprocess.Popen([ffmpeg(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                       "-r", str(FPS), "-i", "-", *FFMPEG_THREADS, "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                       "-pix_fmt", "yuv420p", str(D / "sample.mp4")], stdin=subprocess.PIPE)
for f in range(NF):
    tt = f / FPS; sp = SCREEN[f]
    im = Image.open(FR / f"f_{f:05d}.jpg").convert("RGB").resize((W, H), Image.BICUBIC)
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); dr = ImageDraw.Draw(ov)
    a = pop(tt, 0, 3.0)
    if a: text(dr, (70, 120), "Experiment #6", MARK(64), al(WHITE, a), 6, "la")
    a = pop(tt, 0.2, 4.6)
    if a:
        for i, (x, y) in enumerate(sp["barns"]): text(dr, (x, y - 40), str(i + 1), MARK(96), al(WHITE, a), 7)
    a = pop(tt, 1.4, 4.4)
    if a:
        dx, dy = sp["daisy"]
        arrow(dr, (dx + 120, dy + 230), (dx + 20, dy + 50), al(GOLD, a)); text(dr, (dx + 160, dy + 280), "Daisy's pick", HAND(72), al(GOLD, a))
    a = pop(tt, 2.5, 4.6)
    if a:
        gx, gy = sp["goat"]; text(dr, (gx, gy - 200), "goat!", HAND(84), al(WHITE, a))
    a = pop(tt, 3.0, 5.0)
    if a: text(dr, (W / 2, 330), "Should Daisy switch?", HAND(90), al(WHITE, a))
    a = min(1.0, max(0.0, (tt - 5.4) / 0.3))
    if a:
        for k in ("stay", "switch"):
            x, y = sp["tops"][k]; n = sp["won"][k]
            text(dr, (x, y - 120), f"{n}", MARK(96), al(GOLD if k == "switch" else WHITE, a), 7)
            text(dr, (x, y - 45), f"{k} wins", HAND(64), al(WHITE, a), 5)
        text(dr, (W - 70, 120), f"games: {sp['played']:,}", HAND(80), al(WHITE, a), 6, "ra")
    im.paste(ov, (0, 0), ov)
    ff.stdin.write(np.asarray(im).tobytes())
ff.stdin.close(); ff.wait()
print("saved", D / "sample.mp4", f"({NF / FPS:.1f}s)")
