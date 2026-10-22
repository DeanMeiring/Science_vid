"""Lay captions, rule cards and counters over the Blender frames, add sound and the voice,
and write the finished Short.

Usage: .venv/Scripts/python pipeline/compose.py episodes/ep01_farm.py [--draft]
  --draft uses frames_draft (half size, every n-th frame) for a quick timing check.
Writes renders/<episode>/<episode>[_draft].mp4 (and a thumbnail .jpg).

Overlays and sound design come from prototypes/ant_3d.py.
"""
import argparse, subprocess, sys, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FPS, ROOT, ffmpeg, load_episode, load_timeline, simulate

ap = argparse.ArgumentParser()
ap.add_argument("episode")
ap.add_argument("--draft", action="store_true")
args = ap.parse_args()

W, H = 1080, 1920
FONTS = str(ROOT / "assets" / "fonts") + "/"
def font(n, s): return ImageFont.truetype(FONTS + n, s)

ep_path = Path(args.episode).resolve(); ep = load_episode(ep_path)
ep_dir = ROOT / "renders" / ep_path.stem
lines, DUR, NF, sched = load_timeline(ep_dir)
TOTAL = int(sched.max())
moves, hist = simulate(TOTAL)
frames_dir = ep_dir / ("frames_draft" if args.draft else "frames")
have = sorted(int(p.stem[2:]) for p in frames_dir.glob("f_*.jpg"))
if not have:
    sys.exit(f"no frames in {frames_dir} -- run blender/render_video.py first")
if not args.draft and len(have) < NF:
    sys.exit(f"only {len(have)}/{NF} frames rendered in {frames_dir} -- finish the render, or use --draft")
OUT = ep_dir / f"{ep_path.stem}{'_draft' if args.draft else ''}.mp4"

# ---------------- text layers (cropped to their box for speed) ----------------
F_CAP = font("Inter-Black.ttf", 66); F_CNT = font("Anton.ttf", 110); F_LAB = font("Inter-Black.ttf", 40)
F_RULE = font("Inter-Bold.ttf", 44); F_TITLE = font("Anton.ttf", 150); F_NUM = font("Anton.ttf", 260)
F_SPD = font("Inter-Black.ttf", 46)
CACHE = {}
def layer(key, fn):
    if key in CACHE: return CACHE[key]
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); fn(ImageDraw.Draw(im))
    a = np.array(im); alpha = a[..., 3]
    if alpha.max() == 0:
        val = None
    else:
        ys, xs = np.nonzero(alpha)
        y0, y1 = max(0, ys.min() - 30), min(H, ys.max() + 31); x0, x1 = max(0, xs.min() - 30), min(W, xs.max() + 31)
        sh = np.array(Image.fromarray(alpha).filter(ImageFilter.GaussianBlur(9)), np.float32)[y0:y1, x0:x1, None] / 255 * 0.8
        sub = a[y0:y1, x0:x1].astype(np.float32)
        val = (y0, y1, x0, x1, sub[..., :3], sub[..., 3:] / 255, sh)
    if len(CACHE) > 400: CACHE.clear()   # clear before inserting (clearing after once crashed the lookup)
    CACHE[key] = val
    return val

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
        y = 1560
        for row in wrap([w.upper() for w in words], F_CAP, W - 140, dr):
            txt = " ".join(w for w, _ in row)
            x = (W - dr.textlength(txt, font=F_CAP)) / 2
            for w, i in row:
                col = (255, 214, 64) if i == active else (255, 255, 255)
                dr.text((x, y), w, font=F_CAP, fill=col, stroke_width=7, stroke_fill=(0, 0, 0))
                x += dr.textlength(w + " ", font=F_CAP)
            y += 82
    return fn

SWATCH = {"farm": [(110, 176, 64), (120, 80, 48)], "ant": [(238, 240, 248), (18, 22, 40)]}[ep.THEME]
ACTIVE = {"farm": (236, 160, 40, 240), "ant": (255, 70, 160, 240)}[ep.THEME]
def rules_fn(active):
    def fn(dr):
        y = 150
        for k, (sq, turn) in enumerate(ep.RULES):
            on = active == k
            dr.rounded_rectangle((70, y, W - 70, y + 118), 30, fill=ACTIVE if on else (16, 20, 38, 225),
                                 outline=(255, 255, 255, 140 if on else 60), width=3)
            dr.rounded_rectangle((100, y + 27, 164, y + 91), 12, fill=SWATCH[k], outline=(150, 150, 170), width=3)
            dr.text((190, y + 33), sq, font=F_RULE, fill=(255, 255, 255))
            dr.text((W - 100 - dr.textlength(turn, font=F_RULE), y + 33), turn, font=F_RULE, fill=(255, 255, 255))
            y += 140
    return fn

def counter_fn(step, speed):
    def fn(dr):
        ctext(dr, 110, f"EXPERIMENT #{ep.EXPERIMENT}", F_LAB, (255, 214, 64), 3)
        ctext(dr, 165, f"STEP {step:,}", F_CNT, (255, 255, 255), 5)
        if speed: ctext(dr, 305, speed, F_SPD, (255, 200, 90), 3)
    return fn

def title_fn(alpha):
    def fn(dr):
        a = int(255 * alpha)
        ctext(dr, 640, "EXPERIMENT", F_TITLE, (255, 255, 255, a), 8)
        ctext(dr, 800, f"#{ep.EXPERIMENT}", F_NUM, (255, 214, 64, a), 10)
    return fn

# ---------------- video ----------------
ff = subprocess.Popen([ffmpeg(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                       "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                       "-pix_fmt", "yuv420p", str(ep_dir / "_v.mp4")], stdin=subprocess.PIPE)
r0, r1 = ep.RULE_LINES; hl = lines[ep.HIGHWAY_LINE]
src_i = 0; base = None; base_f = -1
thumb = None
for f in range(NF):
    tt = f / FPS
    while src_i + 1 < len(have) and have[src_i + 1] <= f: src_i += 1
    if have[src_i] != base_f:
        base_f = have[src_i]
        im = Image.open(frames_dir / f"f_{base_f:05d}.jpg").convert("RGB")
        base = np.array(im if im.size == (W, H) else im.resize((W, H), Image.BICUBIC), np.float32)
    img = base.copy()
    done = int(sched[f]); under = int(hist[done][3])
    rate = (sched[min(f + 2, NF - 1)] - sched[max(f - 2, 0)]) / 4 * FPS
    if ep.HIGHWAY <= done and abs(tt - hl["t1"]) < 0.25:          # flash as the highway starts
        img += (1 - abs(tt - hl["t1"]) / 0.25) * 60
    if tt < lines[1]["t0"] + 0.3:
        al = round(min(1, (lines[1]["t0"] + 0.3 - tt) / 0.3), 2)
        comp(img, layer(("title", al), title_fn(al)))
    elif lines[r0]["t0"] <= tt < lines[r1]["t1"]:
        comp(img, layer(("rules", under), rules_fn(under)))
    elif tt >= lines[r1]["t1"]:
        if hl["t0"] <= tt < hl["t1"] + 0.6 and rate < 600:
            spd = "SLOW MOTION"
        else:
            spd = f"SPEED ×{int(round(rate, -1 if rate < 1000 else -2)):,}" if rate > 4 else ""
        comp(img, layer(("cnt", done, spd), counter_fn(done, spd)))
    for ln in lines:
        if ln["t0"] <= tt < ln["t1"]:
            act = max([i for i, (_, a, _) in enumerate(ln["words"]) if a <= tt] or [0])
            comp(img, layer(("cap", ln["text"], act), caption_fn([w for w, _, _ in ln["words"]], act)))
    frame = np.clip(img, 0, 255).astype(np.uint8)
    if thumb is None and tt >= hl["t1"] + 1.5: thumb = frame   # the highway just after it starts
    ff.stdin.write(frame.tobytes())
    if f % 150 == 0: print("frame", f, "/", NF, flush=True)
ff.stdin.close(); ff.wait()
if thumb is not None:
    Image.fromarray(thumb).save(OUT.with_suffix(".jpg"), quality=90)

# ---------------- sound ----------------
SR = 48000
au = np.zeros(int(DUR * SR) + SR, np.float32)
rng = np.random.default_rng(3)
def lp(x, k):
    c = np.cumsum(np.concatenate([np.zeros(k), x])); return (c[k:] - c[:-k]) / k
prev = 0
for f in range(NF):   # a tick per step while slow (higher on dirt)
    n = sched[f] - prev; prev = sched[f]
    if 0 < n <= 2:
        for i in range(n):
            L = int(0.06 * SR); t_ = np.arange(L) / SR
            hi = 1 if hist[sched[f] - n + i][3] else 0
            tk = (np.sin(2 * np.pi * (900 + 500 * hi) * t_) * np.exp(-t_ * 70) + rng.normal(0, .3, L) * np.exp(-t_ * 250)) * 0.3
            o = int(f / FPS * SR) + int(i * SR / FPS / n); au[o:o + L] += tk
rate = np.gradient(sched.astype(float)) * FPS
amp = np.clip((np.log10(np.maximum(rate, 1)) - 0.8) / 2.6, 0, 1)
amp_s = np.interp(np.arange(au.size), np.arange(NF) * SR / FPS, amp)
fr = 60 + 55 * np.log10(np.maximum(np.interp(np.arange(au.size), np.arange(NF) * SR / FPS, rate), 1))
ph = np.cumsum(2 * np.pi * fr / SR)
noise = lp(rng.normal(0, 1, au.size), 25)
au += amp_s * 0.16 * (np.sin(ph) + 0.35 * np.sin(2 * ph) + 0.18 * np.sin(3.01 * ph) + noise * 2.5)
T = hl["t1"]; o = int(T * SR)               # riser into the highway moment, then a boom
L = int(2.4 * SR); t_ = np.arange(L) / SR
au[o - L:o] += lp(rng.normal(0, 1, L), 30) * (t_ / 2.4) ** 2 * 2.2
L = int(2.5 * SR); t_ = np.arange(L) / SR
au[o:o + L] += np.sin(2 * np.pi * (60 - 22 * np.minimum(t_, 1)) * t_) * np.exp(-t_ * 2.2) * 0.75 \
               + lp(rng.normal(0, 1, L), 8) * np.exp(-t_ * 5) * 0.6
au /= np.abs(au).max() / 0.85
with wave.open(str(ep_dir / "voice.wav")) as w:
    vo = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32767
vo = np.pad(vo, (0, max(0, au.size - vo.size)))[:au.size]
# duck the effects under the voice
env = lp(np.abs(vo), 2400); duck = 1 - 0.55 * np.clip(env / (env.max() * 0.25 + 1e-9), 0, 1)
mix = au * 0.45 * duck + vo / (np.abs(vo).max() + 1e-9) * 0.9
fade = np.ones_like(mix); n2 = int(1.2 * SR); fade[-n2:] = np.linspace(1, 0, n2)
mix *= fade; mix /= max(1.0, np.abs(mix).max() / 0.95)
with wave.open(str(ep_dir / "_a.wav"), "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix * 32767).astype(np.int16).tobytes())
subprocess.run([ffmpeg(), "-y", "-loglevel", "error", "-i", str(ep_dir / "_v.mp4"), "-i", str(ep_dir / "_a.wav"),
                "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", str(OUT)], check=True)
(ep_dir / "_v.mp4").unlink(); (ep_dir / "_a.wav").unlink()
print("done", OUT, round(DUR, 1), "s")
