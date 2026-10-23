"""Finish Experiment 8: handwritten captions and notes over the Blender frames, the sound design, and
Joe's voice (the one-take narration). Writes renders/ep08_plant/ep08_plant[_draft].mp4 + .jpg.

Usage: .venv/Scripts/python -X utf8 pipeline/compose_ep08.py [--draft]

Notes: "4 ft!" at the measuring stick, "planted: red / grew: green" at the apples, a thought bubble of a
mustard-apple crossed out, "2 years later", "weeds.", the law, "Pasteur, 1859" at the flask, and the whole
farm's labels at the end.
Sound: a plink per seed, a rising shimmer through each time-lapse, a clunk for the tyre, a ticking clock
while Joe waits, a pop per weed, a pad.
"""
import argparse, json, subprocess, sys, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FPS, ROOT, ffmpeg, FFMPEG_THREADS, gentle
gentle()
from ep08_timeline import LEAD, Timeline
import farm_overview as FO

ap = argparse.ArgumentParser(); ap.add_argument("--draft", action="store_true"); args = ap.parse_args()
tl = Timeline(ROOT / "episodes" / "ep08_plant.py")
D = tl.dir; frames_dir = D / ("frames_draft" if args.draft else "frames")
have = sorted(int(p.stem[2:]) for p in frames_dir.glob("f_*.jpg"))
if not have: sys.exit(f"no frames in {frames_dir}")
if not args.draft and len(have) < tl.nf: sys.exit(f"only {len(have)}/{tl.nf} frames rendered")
SCREEN = {int(k): v for k, v in json.loads((frames_dir / "screen.json").read_text()).items()}
OUT = D / f"ep08_plant{'_draft' if args.draft else ''}.mp4"
W, H = 1080, 1920
FONTS = str(ROOT / "assets" / "fonts") + "/"
def font(n, s): return ImageFont.truetype(FONTS + n, s)
HAND = lambda s: font("PatrickHand-Regular.ttf", s)          # has π, ≈ and ×
MARK = lambda s: font("PermanentMarker-Regular.ttf", s)
INK, GOLD, WHITE, RED = (32, 28, 30), (255, 214, 64), (255, 255, 255), (230, 50, 44)

# ---------------- text layers (cached, cropped to their box) ----------------
CACHE = {}
def layer(key, fn):
    if key in CACHE: return CACHE[key]
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); fn(ImageDraw.Draw(im))
    a = np.array(im); al_ = a[..., 3]
    if al_.max() == 0: val = None
    else:
        ys, xs = np.nonzero(al_)
        y0, y1, x0, x1 = max(0, ys.min() - 20), min(H, ys.max() + 21), max(0, xs.min() - 20), min(W, xs.max() + 21)
        sh = np.array(Image.fromarray(al_).filter(ImageFilter.GaussianBlur(7)), np.float32)[y0:y1, x0:x1, None] / 255 * 0.55
        sub = a[y0:y1, x0:x1].astype(np.float32)
        val = (y0, y1, x0, x1, sub[..., :3], sub[..., 3:] / 255, sh)
    if len(CACHE) > 300: CACHE.clear()       # clear before inserting (clearing after once crashed the lookup)
    CACHE[key] = val
    return val
def comp(img, L):
    if L is None: return
    y0, y1, x0, x1, rgb, a, sh = L
    r = img[y0:y1, x0:x1]; r *= (1 - sh); r[:] = r * (1 - a) + rgb * a

def text(dr, xy, s, f, fill, stroke=6, anchor="mm"):
    dr.text(xy, s, font=f, fill=fill, stroke_width=stroke, stroke_fill=INK, anchor=anchor)
def al(col, a): return col + (int(255 * a),)
def pop(tt, t0, t1, rise=0.18): return float(np.clip(min((tt - t0) / rise, (t1 - tt) / rise), 0, 1))
def arrow(dr, a, b, fill=WHITE, w=7):
    a, b = np.array(a, float), np.array(b, float); mid = (a + b) / 2 + np.array([-(b - a)[1], (b - a)[0]]) * 0.15
    pts = [tuple((1 - u) ** 2 * a + 2 * (1 - u) * u * mid + u ** 2 * b) for u in np.linspace(0, 1, 16)]
    d = b - pts[-3]; d /= np.linalg.norm(d) + 1e-9; n = np.array([-d[1], d[0]])
    head = [tuple(b - d * 30 + n * 16), tuple(b), tuple(b - d * 30 - n * 16)]
    for col, ww in ((INK, w + 6), (fill, w)):
        dr.line(pts, fill=col, width=ww, joint="curve"); dr.line(head, fill=col, width=ww, joint="curve")
def clampxy(x, y, mx=200, top=260, bot=1450): return min(max(x, mx), W - mx), min(max(y, top), bot)

# ---------------- captions: phrases from the word timings ----------------
chunks, cur = [], []
for o in tl.words:
    cur.append(o)
    if o["w"][-1] in ".?!:" or len(cur) >= 7: chunks.append(cur); cur = []
if cur: chunks.append(cur)
spans = []
for i, c in enumerate(chunks):
    t0 = c[0]["t0"] + LEAD - 0.05
    t1 = chunks[i + 1][0]["t0"] + LEAD - 0.05 if i + 1 < len(chunks) else c[-1]["t1"] + LEAD + 0.8
    spans.append((t0, min(t1, c[-1]["t1"] + LEAD + 0.9), c))
F_CAP = HAND(84)
def caption_fn(words, active):
    def fn(dr):
        rows, row = [], []
        for i, w in enumerate(words):
            if row and dr.textlength(" ".join(x for x, _ in row + [(w, i)]), font=F_CAP) > W - 160: rows.append(row); row = []
            row.append((w, i))
        rows.append(row)
        y = min(1590, 1860 - 92 * len(rows))
        for r in rows:
            line = " ".join(w for w, _ in r); x = (W - dr.textlength(line, font=F_CAP)) / 2
            for w, i in r:
                dr.text((x, y), w, font=F_CAP, fill=GOLD if i == active else WHITE, stroke_width=6, stroke_fill=INK)
                x += dr.textlength(w + " ", font=F_CAP)
            y += 92
    return fn

def note_fn(x, y, s, a, size=86, col=WHITE, to=None):
    """A handwritten note at (x, y), with an arrow to `to` if given."""
    def fn(dr):
        if to: arrow(dr, (x, y + (45 if to[1] > y else -50)), to, al(WHITE, a), 6)
        text(dr, (x, y), s, HAND(size), al(col, a), 6)
    return fn

def bubble_fn(x, y, a, cross):
    """Joe's thought: a mustard-apple (an apple with mustard flowers on top), crossed out."""
    def fn(dr):
        for k, (dx, dy, r) in enumerate(((-150, 210, 16), (-115, 165, 24))):       # the little thought dots
            dr.ellipse([x + dx - r, y + dy - r, x + dx + r, y + dy + r], fill=al(WHITE, a), outline=al(INK, a), width=5)
        dr.ellipse([x - 190, y - 140, x + 190, y + 140], fill=al(WHITE, a), outline=al(INK, a), width=7)
        dr.ellipse([x - 70, y - 40, x + 70, y + 90], fill=al(RED, a), outline=al(INK, a), width=5)               # the apple
        for k in range(5):                                                                                     # mustard on top
            sx = x - 40 + 20 * k; dr.line([(sx, y - 38), (sx + (k - 2) * 8, y - 100)], fill=al((88, 140, 62), a), width=6)
            dr.ellipse([sx + (k - 2) * 8 - 14, y - 118, sx + (k - 2) * 8 + 14, y - 92], fill=al((250, 214, 40), a), outline=al(INK, a), width=3)
        if cross:
            for p, q in (((x - 130, y - 110), (x + 130, y + 110)), ((x + 130, y - 110), (x - 130, y + 110))):
                dr.line([p, q], fill=al(INK, a), width=30); dr.line([p, q], fill=al(RED, a), width=18)
    return fn

LABELS = {8: (FO.MORE8[8]["title"], FO.MORE8[8]["sub"]), 7: (FO.MORE8[7]["title"], "π from hay"),
          6: (FO.MORE[6]["title"], FO.MORE[6]["sub"]), 5: (FO.MORE[5]["title"], FO.MORE[5]["sub"]),
          4: ("Experiment #4", "Joe & Daisy: spotless!"), **{k: (FO.FIELDS[k]["title"], FO.FIELDS[k]["sub"]) for k in (1, 2, 3)}}
NUDGE = {}                                                       # set after looking at the draft
T_PULL = tl.s_end
LABEL_T = {8: T_PULL + 0.3, 7: T_PULL + 0.7, 5: T_PULL + 1.0, 6: T_PULL + 1.2, 4: T_PULL + 1.4, 1: T_PULL + 1.6,
           2: T_PULL + 1.9, 3: T_PULL + 2.2}

# ---------------- video ----------------
ff = subprocess.Popen([ffmpeg(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                       "-r", str(FPS), "-i", "-", *FFMPEG_THREADS, "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                       "-pix_fmt", "yuv420p", str(D / "_v.mp4")], stdin=subprocess.PIPE)
src_i, base_f, base, thumb = 0, -1, None, None
q = lambda v: (int(v * 8)) / 8
g8 = lambda v: int(v / 8)
for f in range(tl.nf):
    tt = f / FPS
    while src_i + 1 < len(have) and have[src_i + 1] <= f: src_i += 1
    if have[src_i] != base_f:
        base_f = have[src_i]; im = Image.open(frames_dir / f"f_{base_f:05d}.jpg").convert("RGB")
        base = np.array(im if im.size == (W, H) else im.resize((W, H), Image.BICUBIC), np.float32)
    img = base.copy()
    sp = SCREEN.get(base_f) or SCREEN[min(SCREEN, key=lambda k: abs(k - base_f))]
    a = pop(tt, 0.0, 3.0)
    if a: comp(img, layer(("title", q(a)), lambda dr, a=a: text(dr, (70, 120), "Experiment #8", MARK(64), al(WHITE, a), 6, "la")))
    # the mustard: "one season later", then "4 ft!" at the stick
    a = pop(tt, tl.grow_mustard[0] + 0.3, tl.grow_mustard[1])
    if a: comp(img, layer(("season", q(a)), lambda dr, a=a: text(dr, (W / 2, 330), "one season later...", HAND(80), al(WHITE, a))))
    a = pop(tt, tl.grow_mustard[1] - 0.6, tl.s_apple)
    if a:
        sx, sy = sp["stick"][:2]; x, y = clampxy(sx + 230, sy - 150)
        comp(img, layer(("4ft", g8(sx), g8(sy), q(a)), note_fn(x, y, "4 ft!", a, 110, GOLD, (sx + 30, sy + 20))))
    # the apple: what Joe planted (red) and what grew (green)
    a = pop(tt, tl.grow_apple[1] - 0.5, tl.s_both)
    if a:
        rx, ry = sp["red"][:2]; x, y = clampxy(rx - 40, ry - 230)
        comp(img, layer(("red", g8(rx), g8(ry), q(a)), note_fn(x, y, "planted: red", a, 74, WHITE, (rx, ry - 30))))
        tx, ty = sp["tree"][:2]; x, y = clampxy(tx, ty - 260)
        comp(img, layer(("green", g8(tx), g8(ty), q(a)), note_fn(x, y, "grew: green", a, 74, (190, 236, 90))))
    # both: the thought bubble, crossed out on "not"
    a = pop(tt, tl.bubble[0], tl.bubble[1] + 0.3)
    if a:
        jx, jy = sp["joe"][:2]; x, y = clampxy(jx + 170, jy - 330, 230, 330)
        cross = tt >= tl.at("not", 1) - 0.05
        comp(img, layer(("bubble", g8(x), g8(y), q(a), cross), bubble_fn(x, y, a, cross)))
    # the tyre: two years go by, then weeds
    a = pop(tt, tl.wait[0] + 0.2, tl.weeds - 0.2)
    if a:
        u = np.clip((tt - tl.wait[0]) / (tl.wait[1] - tl.wait[0]), 0, 1); yrs = "1 year later..." if u < 0.5 else "2 years later..."
        comp(img, layer(("years", yrs, q(a)), lambda dr, a=a, yrs=yrs: text(dr, (W / 2, 330), yrs, HAND(84), al(WHITE, a))))
    a = pop(tt, tl.weeds + 0.1, tl.s_law)
    if a:
        tx, ty = sp["tyre"][:2]; x, y = clampxy(tx - 60, ty - 300)
        comp(img, layer(("weeds", g8(tx), g8(ty), q(a)), note_fn(x, y, "weeds.", a, 96, WHITE, (tx, ty - 50))))
    # the law, and Pasteur's flask
    a = pop(tt, tl.at("biogenesis:") - 0.1, T_PULL - 0.1)
    if a: comp(img, layer(("law", q(a)), lambda dr, a=a: (text(dr, (W / 2, 290), "BIOGENESIS", MARK(92), al(GOLD, a), 7),
                                                         text(dr, (W / 2, 390), "life only comes from life", HAND(70), al(WHITE, a)))))
    a = pop(tt, tl.pasteur, T_PULL - 0.1)
    if a:
        fx, fy = sp["flask"][:2]; x, y = clampxy(fx + 60, fy - 250)
        comp(img, layer(("pasteur", g8(fx), g8(fy), q(a)), note_fn(x, y, "Pasteur, 1859", a, 76, WHITE, (fx, fy - 20))))
    # the whole farm
    if "fields" in sp:
        for k, t0 in LABEL_T.items():
            a = pop(tt, t0, tl.duration + 1, 0.25)
            if not a or str(k) not in sp["fields"]: continue
            fx, fy = sp["fields"][str(k)][:2]
            dx, dy = NUDGE.get(k, (0, 0))
            x, y = clampxy(fx + dx, fy + dy, 215, 290)
            title, sub_ = LABELS[k]; today = k == 8
            comp(img, layer(("lab", k, int(x / 6), int(y / 6), int(fx / 6), int(fy / 6), q(a)), lambda dr, x=x, y=y, fx=fx, fy=fy, a=a,
                            title=title, sub_=sub_, today=today, k=k: (
                arrow(dr, (x, y + (25 if fy > y else -95)), (fx, fy + 40 if fy > y else fy + 30), al(WHITE, a), 5) if k in NUDGE else None,
                text(dr, (x, y - 62), title, MARK(58 if today else 50), al(GOLD if today else WHITE, a), 6),
                text(dr, (x, y - 8), sub_, HAND(52), al(WHITE, a), 5))))
    for t0, t1, c in spans:
        if t0 <= tt < t1:
            act = max([i for i, o in enumerate(c) if o["t0"] + LEAD <= tt] or [0])
            comp(img, layer(("cap", c[0]["t0"], act), caption_fn([o["w"] for o in c], act)))
    frame = np.clip(img, 0, 255).astype(np.uint8)
    if thumb is None and tt >= tl.weeds + 0.6: thumb = frame                   # the tyre, the weeds, "weeds."
    ff.stdin.write(frame.tobytes())
    if f % 150 == 0: print("frame", f, "/", tl.nf, flush=True)
ff.stdin.close(); ff.wait()
if not args.draft and thumb is not None: Image.fromarray(thumb).save(OUT.with_suffix(".jpg"), quality=90)

# ---------------- sound ----------------
SR = 48000; au = np.zeros(int((tl.duration + 1) * SR), np.float32); rng = np.random.default_rng(5)
def add(t0, w):
    o = int(t0 * SR)
    if 0 <= o < len(au): au[o:o + len(w)] += w[:len(au) - o]
def pluck(t0, f, amp=0.3, decay=7.0, dur=1.0):
    t = np.arange(int(dur * SR)) / SR
    w = (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t) + 0.12 * np.sin(6 * np.pi * f * t)) * np.exp(-t * decay)
    add(t0, w * np.minimum(1, t / 0.004) * amp)
def noise(t0, dur, amp, hi=60, env=None):
    L = int(dur * SR); t = np.arange(L) / SR; n = np.convolve(rng.normal(0, 1, L), np.ones(hi) / hi, "same")
    add(t0, n * (env(t / dur) if env else np.sin(np.pi * t / dur)) * amp)
def shimmer(a, b, amp=0.05):                                   # a time-lapse: notes rising faster and faster
    tt, k = a, 0
    while tt < b:
        u = (tt - a) / (b - a); pluck(tt, 523.3 * 2 ** ((k % 12) / 12), amp, 12, 0.4); tt += 0.16 - 0.11 * u; k += 2
for t0 in (0.55, tl.s_apple + 0.5, tl.s_both + 0.5): pluck(t0, 880, 0.22, 10, 0.6)      # a seed drops in
for w_ in (tl.grow_mustard, tl.grow_apple, tl.grow_both): shimmer(*w_)
a, b = tl.plant_tyre; noise(b - 0.3, 0.25, 0.5, hi=200); pluck(b - 0.3, 82, 0.4, 6, 1.0)                # clunk
for t0 in np.arange(tl.wait[0], tl.wait[1], 0.25): pluck(t0, 1600 if int((t0 - tl.wait[0]) / 0.25) % 2 else 1200, 0.06, 40, 0.1)   # tick-tock
for k in range(6): pluck(tl.weeds + k * 0.07, 660 * 2 ** (k / 12), 0.12, 14, 0.4)               # weeds pop up
for i, mult in enumerate((1, 1.25, 1.5, 2)): pluck(tl.at("biogenesis:") + i * 0.06, 392.0 * mult, 0.22, 2.5, 2.5)
for k, t0 in LABEL_T.items(): pluck(t0, 196.0 * 2 ** ((12 + 2 * k) / 12), 0.16, 5, 1.2)
t = np.arange(len(au)) / SR
pad = sum(np.sin(2 * np.pi * f_ * t + p) for f_, p in ((98, 0), (147, 1.3), (196, 2.1), (247, 0.7))) / 4
au += pad * np.clip((t - 0.5) / 3, 0, 1) * 0.07
for i, mult in enumerate((1, 1.25, 1.5)): pluck(tl.duration - 1.6 + i * 0.12, 261.6 * mult, 0.18, 1.6, 3.0)
au /= np.abs(au).max() / 0.8
with wave.open(str(D / "narration_flow.wav")) as w:
    sr0 = w.getframerate(); vo0 = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32767
vo = np.zeros_like(au); v48 = np.interp(np.arange(int(len(vo0) * SR / sr0)) * sr0 / SR, np.arange(len(vo0)), vo0)
o = int(LEAD * SR); vo[o:o + len(v48)] = v48[:len(vo) - o]
env = np.convolve(np.abs(vo), np.ones(2400) / 2400, "same"); duck = 1 - 0.6 * np.clip(env / (env.max() * 0.25 + 1e-9), 0, 1)
mix = au * 0.42 * duck + vo / (np.abs(vo).max() + 1e-9) * 0.9
fade = np.ones_like(mix); n2 = int(1.0 * SR); fade[-n2:] = np.linspace(1, 0, n2); mix *= fade
mix /= max(1.0, np.abs(mix).max() / 0.95)
with wave.open(str(D / "_a.wav"), "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix * 32767).astype(np.int16).tobytes())
subprocess.run([ffmpeg(), "-y", "-loglevel", "error", "-i", str(D / "_v.mp4"), "-i", str(D / "_a.wav"), "-c:v", "copy",
                "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(OUT)], check=True)
(D / "_v.mp4").unlink(); (D / "_a.wav").unlink()
print("done", OUT, round(tl.duration, 1), "s")
