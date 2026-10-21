"""Prototype: 'Experiment #1' Langton's Ant Short, narration-driven.

Each narration line sets what the simulation does while it is spoken
(hold, single steps, speed ramp, slow-mo...). The camera fits everything
the ant has touched, so it starts zoomed in and pulls out as it speeds up.
No voice yet: captions are timed like speech (word length based) so a
cloned voice + Whisper word timings can replace the estimate later.
"""
import math, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS = 1080, 1920, 30
from pathlib import Path
FONTS = str(Path(__file__).resolve().parent.parent / "assets" / "fonts") + "/"
OUT = sys.argv[1] if len(sys.argv) > 1 else "experiment_1_2d.mp4"
def font(n, s): return ImageFont.truetype(FONTS + n, s)

# ---------------- narration script ----------------
# (caption text, mode, target step at end of line)
SCRIPT = [
    ("Experiment number 1.", "hold", 0),
    ("Put an ant on a grid of white squares.", "hold", 0),
    ("On a white square, it turns right.", "single", 5),
    ("On a black square, it turns left.", "single", 10),
    ("Then it flips the square's colour and steps forward.", "single", 17),
    ("That's it. Two rules. Now let's speed it up.", "ramp", 250),
    ("For thousands of steps, it just makes a mess.", "ramp", 3500),
    ("No pattern. No order. Just chaos.", "linear", 9600),
    ("Until step 9,977...", "land", 9977),
    ("Out of nowhere, it starts building a highway.", "easein", 12000),
    ("The same 104 steps, over and over, forever.", "linear", 15000),
    ("And nobody has ever proven why.", "linear", 16200),
    ("Next experiment: what happens with three colours?", "linear", 16800),
]
HIGHWAY = 9977

def word_weights(line):
    ws = line.split()
    return ws, np.array([len(w.strip(".,:?'")) + 2.5 for w in ws], float)

# timing: ~2.7 words/s, pause after each line
lines = []
t = 0.4
for text, mode, target in SCRIPT:
    ws, wt = word_weights(text)
    dur = len(ws) / 2.7 + 0.15 * sum(1 for w in ws if w[-1] in ".,:?")
    if mode == "single":
        dur = max(dur, 3.2)
    if mode == "land":
        dur = max(dur, 3.0)
    ends = t + np.cumsum(wt) / wt.sum() * dur
    starts = np.concatenate([[t], ends[:-1]])
    lines.append(dict(text=text, mode=mode, target=target, t0=t, t1=t + dur + 0.45,
                      words=list(zip(ws, starts, ends))))
    t += dur + 0.45
DUR = t + 1.6
lines[-1]["t1"] = DUR
NF = int(DUR * FPS)

# ---------------- step schedule ----------------
sched = np.zeros(NF, np.int64)
prev = 0
for i, ln in enumerate(lines):
    f0 = int(ln["t0"] * FPS); f1 = int(ln["t1"] * FPS) if i < len(lines) - 1 else NF
    s0, s1 = prev, ln["target"]
    for f in range(f0, f1):
        u = (f - f0) / max(1, f1 - f0 - 1)
        m = ln["mode"]
        if m == "hold": v = s0
        elif m == "single": v = s0 + min(s1 - s0, int(u * (s1 - s0) + 0.999))
        elif m == "ramp": v = s0 + (s1 - s0) * (math.expm1(u * 3) / math.expm1(3))
        elif m == "land": v = s0 + (s1 - s0) * (1 - (1 - u) ** 3)        # brakes into the moment
        elif m == "easein": v = s0 + (s1 - s0) * u ** 2.2
        else: v = s0 + (s1 - s0) * u
        sched[f] = int(round(v))
    prev = s1
sched[:int(lines[0]["t0"] * FPS)] = 0
sched = np.maximum.accumulate(sched)
TOTAL = int(sched.max())

# ---------------- simulation ----------------
N = 700
grid = np.zeros((N, N), np.uint8)
last = np.full((N, N), -10 ** 9, np.int64)
DX = [0, 1, 0, -1]; DY = [-1, 0, 1, 0]
x = y = N // 2; d = 0
g2 = grid.copy()
moves = np.zeros((TOTAL, 2), np.int64)
hist = np.zeros((TOTAL + 1, 4), np.int64); hist[0] = (x, y, d, 0)
for s in range(TOTAL):
    c = g2[y, x]
    d = (d + 1) % 4 if c == 0 else (d - 1) % 4
    g2[y, x] ^= 1; moves[s] = (x, y)
    x += DX[d]; y += DY[d]
    hist[s + 1] = (x, y, d, g2[y, x])
mx = np.minimum.accumulate(moves[:, 0]); Mx = np.maximum.accumulate(moves[:, 0])
my = np.minimum.accumulate(moves[:, 1]); My = np.maximum.accumulate(moves[:, 1])

# ---------------- look ----------------
BG = np.array([8, 10, 20], np.float32)
OFF = np.array([238, 240, 248], np.float32)   # "white" squares, slightly cool
ON = np.array([18, 22, 40], np.float32)       # "black" squares
HOT = np.array([255, 70, 160], np.float32)    # fresh flips glow pink
ANT = np.array([255, 150, 40], np.float32)
LINE = np.array([200, 205, 220], np.float32)
BOARD_Y = 1000; BOX = 900

def board(step, cx, cy, s, heat_len):
    x0 = int(math.floor(cx - W / 2 / s)) - 1; x1 = int(math.ceil(cx + W / 2 / s)) + 1
    y0 = int(math.floor(cy - BOARD_Y / s)) - 1; y1 = int(math.ceil(cy + (H - BOARD_Y) / s)) + 1
    xs = np.arange(x0, x1); ys = np.arange(y0, y1)
    xc = np.clip(xs, 0, N - 1); yc = np.clip(ys, 0, N - 1)
    st = grid[yc[:, None], xc[None, :]].astype(np.float32)[..., None]
    age = (step - last[yc[:, None], xc[None, :]]).astype(np.float32)[..., None]
    heat = np.exp(-age / heat_len) * 0.75
    cc = OFF * (1 - st) + ON * st
    cc = cc * (1 - heat) + HOT * heat
    cc = np.clip(cc, 0, 255).astype(np.uint8)
    px = (np.arange(W) - W / 2) / s + cx; py = (np.arange(H) - BOARD_Y) / s + cy
    ix = np.floor(px).astype(int) - x0; iy = np.floor(py).astype(int) - y0
    img = cc[iy[:, None], ix[None, :]]
    if s > 10:
        a = min(1.0, (s - 10) / 20)
        lw = 2 if s > 30 else 1
        fx = px - np.floor(px); fy = py - np.floor(py)
        cols = np.nonzero(fx * s < lw)[0]; rows = np.nonzero(fy * s < lw)[0]
        img = img.astype(np.float32)
        img[:, cols] = img[:, cols] * (1 - 0.35 * a) + 120 * 0.35 * a
        img[rows, :] = img[rows, :] * (1 - 0.35 * a) + 120 * 0.35 * a
    return img.astype(np.float32)

def glow(r):
    k = np.arange(-3 * r, 3 * r + 1)
    return np.exp(-(k[:, None] ** 2 + k[None, :] ** 2) / (2.0 * r * r)).astype(np.float32)

# ---------------- text layers (cropped to their box for speed) ----------------
F_CAP = font("Inter-Black.ttf", 66); F_CNT = font("Anton.ttf", 110); F_LAB = font("Inter-Black.ttf", 40)
F_RULE = font("Inter-Bold.ttf", 44); F_TITLE = font("Anton.ttf", 150); F_SPD = font("Inter-Black.ttf", 46)
CACHE = {}
def layer(key, fn):
    if key in CACHE: return CACHE[key]
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); fn(ImageDraw.Draw(im))
    a = np.array(im)
    alpha = a[..., 3]
    if alpha.max() == 0:
        CACHE[key] = None; return None
    ys, xs = np.nonzero(alpha)
    y0, y1 = max(0, ys.min() - 30), min(H, ys.max() + 31); x0, x1 = max(0, xs.min() - 30), min(W, xs.max() + 31)
    sh = np.array(Image.fromarray(alpha).filter(ImageFilter.GaussianBlur(9)), np.float32)[y0:y1, x0:x1, None] / 255 * 0.8
    sub = a[y0:y1, x0:x1].astype(np.float32)
    if len(CACHE) > 400: CACHE.clear()
    CACHE[key] = (y0, y1, x0, x1, sub[..., :3], sub[..., 3:] / 255, sh)
    return CACHE[key]

def comp(img, L):
    if L is None: return
    y0, y1, x0, x1, rgb, a, sh = L
    r = img[y0:y1, x0:x1]
    r *= (1 - sh)
    r[:] = r * (1 - a) + rgb * a

def ctext(dr, y, txt, f, fill, stroke=0):
    w = dr.textlength(txt, font=f)
    dr.text(((W - w) / 2, y), txt, font=f, fill=fill, stroke_width=stroke, stroke_fill=(0, 0, 0))

def wrap(words, f, maxw, dr):
    rows, cur = [], []
    for i, w in enumerate(words):
        test = " ".join(x for x, _ in cur + [(w, i)])
        if cur and dr.textlength(test, font=f) > maxw:
            rows.append(cur); cur = []
        cur.append((w, i))
    if cur: rows.append(cur)
    return rows

def caption_fn(words, active):
    def fn(dr):
        rows = wrap([w.upper() for w in words], F_CAP, W - 140, dr)
        y = 1560
        for row in rows:
            txt = " ".join(w for w, _ in row)
            x = (W - dr.textlength(txt, font=F_CAP)) / 2
            for w, i in row:
                col = (255, 214, 64) if i == active else (255, 255, 255)
                dr.text((x, y), w, font=F_CAP, fill=col, stroke_width=7, stroke_fill=(0, 0, 0))
                x += dr.textlength(w + " ", font=F_CAP)
            y += 82
    return fn

def rules_fn(active):
    def fn(dr):
        y = 150
        for k, (sq, turn) in enumerate([("WHITE SQUARE", "TURN RIGHT"), ("BLACK SQUARE", "TURN LEFT")]):
            on = active == k
            dr.rounded_rectangle((70, y, W - 70, y + 118), 30,
                                 fill=(255, 70, 160, 240) if on else (16, 20, 38, 225),
                                 outline=(255, 255, 255, 140 if on else 60), width=3)
            dr.rounded_rectangle((100, y + 27, 164, y + 91), 12, fill=tuple(int(v) for v in (OFF if k == 0 else ON)),
                                 outline=(150, 150, 170), width=3)
            dr.text((190, y + 33), sq, font=F_RULE, fill=(255, 255, 255))
            dr.text((W - 100 - dr.textlength(turn, font=F_RULE), y + 33), turn, font=F_RULE, fill=(255, 255, 255))
            y += 140
    return fn

def counter_fn(step, speed, exp):
    def fn(dr):
        ctext(dr, 110, f"EXPERIMENT #{exp}", F_LAB, (255, 214, 64), 3)
        ctext(dr, 165, f"STEP {step:,}", F_CNT, (255, 255, 255), 5)
        if speed: ctext(dr, 305, speed, F_SPD, (255, 120, 190), 3)
    return fn

def title_fn(alpha):
    def fn(dr):
        a = int(255 * alpha)
        ctext(dr, 640, "EXPERIMENT", F_TITLE, (255, 255, 255, a), 8)
        ctext(dr, 800, "#1", font("Anton.ttf", 260), (255, 214, 64, a), 10)
    return fn

# ---------------- render ----------------
ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                       "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                       "-pix_fmt", "yuv420p", "_v.mp4"], stdin=subprocess.PIPE)
cx = cy = N / 2 + 0.5; s_cur = 110.0
done = 0
events = []  # (time, kind) for audio
rules_t1 = lines[4]["t1"]; rules_t0 = lines[2]["t0"]
for f in range(NF):
    tt = f / FPS
    tgt = sched[f]
    while done < tgt:
        px_, py_ = moves[done]; grid[py_, px_] ^= 1; last[py_, px_] = done; done += 1
    ax, ay, adir, under = hist[done]
    if done == 0:
        bx0 = bx1 = ax; by0 = by1 = ay
    else:
        bx0, bx1 = min(mx[done - 1], ax), max(Mx[done - 1], ax); by0, by1 = min(my[done - 1], ay), max(My[done - 1], ay)
    span = max(bx1 - bx0, (by1 - by0)) + 1 + (3 if done < 30 else 8)
    s_t = min(130.0, BOX / span)
    k = 0.06 if done > 30 else 0.12
    s_cur *= (s_t / s_cur) ** k
    cx += ((bx0 + bx1 + 1) / 2 - cx) * k; cy += ((by0 + by1 + 1) / 2 - cy) * k
    rate = (sched[min(f + 2, NF - 1)] - sched[max(f - 2, 0)]) / 4 * FPS
    img = board(done, cx, cy, s_cur, heat_len=max(1.2, rate * 0.06))
    # ant
    pxl = (ax + 0.5 - cx) * s_cur + W / 2; pyl = (ay + 0.5 - cy) * s_cur + BOARD_Y
    gs = glow(max(5, int(s_cur * 0.5)))
    h2 = gs.shape[0] // 2; X0, Y0 = int(pxl) - h2, int(pyl) - h2
    xa, ya = max(0, X0), max(0, Y0); xb, yb = min(W, X0 + gs.shape[1]), min(H, Y0 + gs.shape[0])
    if xb > xa and yb > ya:
        img[ya:yb, xa:xb] += gs[ya - Y0:yb - Y0, xa - X0:xb - X0, None] * ANT * 0.9
    np.clip(img, 0, 255, out=img)
    # ant body (drawn on a small crop)
    rr = max(4.0, s_cur * 0.34)
    pad = int(rr * 2) + 4
    cx0, cy0 = int(pxl) - pad, int(pyl) - pad
    if 0 <= cx0 and cx0 + 2 * pad < W and 0 <= cy0 and cy0 + 2 * pad < H:
        crop = Image.fromarray(img[cy0:cy0 + 2 * pad, cx0:cx0 + 2 * pad].astype(np.uint8))
        dc = ImageDraw.Draw(crop); lx, ly = pxl - cx0, pyl - cy0
        if s_cur > 22:
            ang = [-math.pi / 2, 0, math.pi / 2, math.pi][adir]
            # tiny ant: three body segments along its heading
            for off, rad in ((-0.75, 0.42), (0.0, 0.30), (0.62, 0.36)):
                bx_, by_ = lx + math.cos(ang) * rr * off, ly + math.sin(ang) * rr * off
                dc.ellipse((bx_ - rr * rad, by_ - rr * rad, bx_ + rr * rad, by_ + rr * rad), fill=(40, 22, 10))
            for side in (-1, 1):  # legs
                for off in (-0.3, 0.0, 0.3):
                    bx_, by_ = lx + math.cos(ang) * rr * off, ly + math.sin(ang) * rr * off
                    ex = bx_ + math.cos(ang + side * math.pi / 2) * rr * 0.75
                    ey = by_ + math.sin(ang + side * math.pi / 2) * rr * 0.75
                    dc.line((bx_, by_, ex, ey), fill=(40, 22, 10), width=max(1, int(rr * 0.08)))
        else:
            dc.ellipse((lx - rr, ly - rr, lx + rr, ly + rr), fill=(255, 190, 90))
        img[cy0:cy0 + 2 * pad, cx0:cx0 + 2 * pad] = np.array(crop, np.float32)
    # slow-mo flash when the highway starts
    if HIGHWAY <= done and abs(tt - lines[8]["t1"]) < 0.25:
        img += (1 - abs(tt - lines[8]["t1"]) / 0.25) * 60
    # overlays
    if tt < lines[1]["t0"] + 0.3:
        comp(img, layer(("title", round(min(1, (lines[1]["t0"] + 0.3 - tt) / 0.3), 2)),
                        title_fn(min(1, (lines[1]["t0"] + 0.3 - tt) / 0.3))))
    elif rules_t0 <= tt < rules_t1:
        comp(img, layer(("rules", int(under)), rules_fn(int(under))))
    elif tt >= rules_t1:
        if lines[8]["t0"] <= tt < lines[8]["t1"] + 0.6 and rate < 600:
            spd = "SLOW MOTION"
        else:
            spd = f"SPEED ×{int(rate):,}" if rate > 4 else ""
        spd_key = spd if not spd.startswith("SPEED") else f"SPEED ×{int(round(rate, -1 if rate < 1000 else -2)):,}"
        comp(img, layer(("cnt", done, spd_key), counter_fn(done, spd_key, 1)))
    for ln in lines:
        if ln["t0"] <= tt < ln["t1"]:
            act = max([i for i, (_, a, _) in enumerate(ln["words"]) if a <= tt] or [0])
            comp(img, layer(("cap", ln["text"], act), caption_fn([w for w, _, _ in ln["words"]], act)))
    ff.stdin.write(np.clip(img, 0, 255).astype(np.uint8).tobytes())
    if f % 300 == 0: print("frame", f, "/", NF, "step", done, flush=True)
ff.stdin.close(); ff.wait()

# ---------------- sound ----------------
SR = 48000
au = np.zeros(int(DUR * SR) + SR, np.float32)
rng = np.random.default_rng(3)
def lp(x, k):
    c = np.cumsum(np.concatenate([np.zeros(k), x])); return (c[k:] - c[:-k]) / k
prev = 0
for f in range(NF):
    n = sched[f] - prev; prev = sched[f]
    if 0 < n <= 2:
        for i in range(n):
            L = int(0.06 * SR); t_ = np.arange(L) / SR
            hi = 1 if hist[sched[f] - n + i][3] else 0
            tk = (np.sin(2 * np.pi * (900 + 500 * hi) * t_) * np.exp(-t_ * 70) + rng.normal(0, .3, L) * np.exp(-t_ * 250)) * 0.3
            o = int(f / FPS * SR) + int(i * SR / FPS / n); au[o:o + L] += tk
rate = np.gradient(sched.astype(float)) * FPS
ti = np.clip((np.arange(au.size) / SR * FPS).astype(int), 0, NF - 1)
amp = np.clip((np.log10(np.maximum(rate, 1)) - 0.8) / 2.6, 0, 1)
amp_s = np.interp(np.arange(au.size), np.arange(NF) * SR / FPS, amp)
fr = 60 + 55 * np.log10(np.maximum(np.interp(np.arange(au.size), np.arange(NF) * SR / FPS, rate), 1))
ph = np.cumsum(2 * np.pi * fr / SR)
noise = lp(rng.normal(0, 1, au.size), 25)
au += amp_s * 0.16 * (np.sin(ph) + 0.35 * np.sin(2 * ph) + 0.18 * np.sin(3.01 * ph) + noise * 2.5)
# riser into the highway moment, then a boom
T = lines[8]["t1"]; o = int(T * SR)
L = int(2.4 * SR); t_ = np.arange(L) / SR
riser = lp(rng.normal(0, 1, L), 30) * (t_ / 2.4) ** 2 * 2.2
au[o - L:o] += riser
L = int(2.5 * SR); t_ = np.arange(L) / SR
au[o:o + L] += np.sin(2 * np.pi * (60 - 22 * np.minimum(t_, 1)) * t_) * np.exp(-t_ * 2.2) * 0.75 \
               + lp(rng.normal(0, 1, L), 8) * np.exp(-t_ * 5) * 0.6
fade = np.ones_like(au); n2 = int(1.2 * SR); fade[-n2:] = np.linspace(1, 0, n2)
au *= fade; au /= np.abs(au).max() / 0.85
with wave.open("_a.wav", "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((au * 32767).astype(np.int16).tobytes())
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", "_v.mp4", "-i", "_a.wav", "-c:v", "copy", "-c:a", "aac",
                "-b:a", "160k", "-shortest", OUT], check=True)
print("done", OUT, round(DUR, 1), "s")
