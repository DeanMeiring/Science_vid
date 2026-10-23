"""Finish Experiment 7: handwritten captions and notes over the Blender frames, the sound design, and
Joe's voice (the one-take narration). Writes renders/ep07_pi/ep07_pi[_draft].mp4 + .jpg.

Usage: .venv/Scripts/python -X utf8 pipeline/compose_ep07.py [--draft]

Notes: the tally (straws, gold) and pi's estimate 2 x straws / gold, "1 straw = 1 board", speed lines and
a smear while Joe is blurry-fast, "nom." for Daisy, and the whole farm's labels at the end.
Sound: a whoosh per throw and a plink per landing (higher for gold), a rising buzz while blurry, the
wheelbarrow's rattle, the tractor's engine, the combine's roar and its rain of straw, a pad.
"""
import argparse, json, subprocess, sys, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FPS, ROOT, ffmpeg, FFMPEG_THREADS, gentle
gentle()
from ep07_timeline import LEAD, Timeline
import farm_overview as FO

ap = argparse.ArgumentParser(); ap.add_argument("--draft", action="store_true"); args = ap.parse_args()
tl = Timeline(ROOT / "episodes" / "ep07_pi.py")
D = tl.dir; frames_dir = D / ("frames_draft" if args.draft else "frames")
have = sorted(int(p.stem[2:]) for p in frames_dir.glob("f_*.jpg"))
if not have: sys.exit(f"no frames in {frames_dir}")
if not args.draft and len(have) < tl.nf: sys.exit(f"only {len(have)}/{tl.nf} frames rendered")
SCREEN = {int(k): v for k, v in json.loads((frames_dir / "screen.json").read_text()).items()}
OUT = D / f"ep07_pi{'_draft' if args.draft else ''}.mp4"
W, H = 1080, 1920
FONTS = str(ROOT / "assets" / "fonts") + "/"
def font(n, s): return ImageFont.truetype(FONTS + n, s)
HAND = lambda s: font("PatrickHand-Regular.ttf", s)          # has π, ≈ and ×
MARK = lambda s: font("PermanentMarker-Regular.ttf", s)
INK, GOLD, WHITE = (32, 28, 30), (255, 214, 64), (255, 255, 255)

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
def onscreen(w):
    """The word as captioned: "pi" becomes the symbol (Dean); "pie" (the one you eat) stays a word."""
    core = w.strip(".,:;!?'\"")
    return w.replace(core, "π") if core.lower() == "pi" else w
def caption_fn(words, active):
    words = [onscreen(w) for w in words]
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

def counters_fn(n, g, big):
    def fn(dr):
        text(dr, (W - 70, 120), f"straws: {n:,}", HAND(76), WHITE, 6, "ra")
        text(dr, (W - 70, 200), f"gold: {g:,}", HAND(76), GOLD, 6, "ra")
        if g and not big: text(dr, (W - 70, 290), f"2 × {n:,} ÷ {g:,} = {2 * n / g:.2f}", HAND(60), WHITE, 5, "ra")
        if big: text(dr, (W / 2, 470), f"π ≈ {2 * n / g:.2f}!", HAND(170), GOLD, 9)
    return fn

# speed lines round Joe while he's blurry-fast
def speedlines_fn(cx, cy, seed):
    r = np.random.default_rng(seed)
    def fn(dr):
        for _ in range(16):
            a = r.uniform(0, 2 * np.pi); r0 = r.uniform(150, 210); r1 = r0 + r.uniform(60, 140)
            p0 = (cx + r0 * np.cos(a), cy + r0 * np.sin(a)); p1 = (cx + r1 * np.cos(a), cy + r1 * np.sin(a))
            dr.line([p0, p1], fill=(255, 255, 255, 220), width=6)
    return fn

T_PULL = tl.t_buffon - 0.2
LABELS = {7: (FO.MORE[7]["title"], FO.MORE[7]["sub"]), 6: (FO.MORE[6]["title"], FO.MORE[6]["sub"]),
          5: (FO.MORE[5]["title"], FO.MORE[5]["sub"]), 4: ("Experiment #4", "Joe & Daisy: spotless!"),
          **{k: (FO.FIELDS[k]["title"], FO.FIELDS[k]["sub"]) for k in (1, 2, 3)}}
NUDGE = {7: (14, -208), 6: (175, -168), 4: (30, -76), 5: (-105, 87)}   # #4-#7 sit close together: spread out, with arrows
LABEL_T = {7: T_PULL + 0.5, 5: T_PULL + 1.0, 6: T_PULL + 1.3, 4: T_PULL + 1.5, 1: T_PULL + 1.7, 2: T_PULL + 2.1, 3: T_PULL + 2.5}
B0, B1 = tl.win["blur"]

# ---------------- video ----------------
ff = subprocess.Popen([ffmpeg(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                       "-r", str(FPS), "-i", "-", *FFMPEG_THREADS, "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                       "-pix_fmt", "yuv420p", str(D / "_v.mp4")], stdin=subprocess.PIPE)
src_i, base_f, base, thumb, prev = 0, -1, None, None, []
for f in range(tl.nf):
    tt = f / FPS
    while src_i + 1 < len(have) and have[src_i + 1] <= f: src_i += 1
    if have[src_i] != base_f:
        base_f = have[src_i]; im = Image.open(frames_dir / f"f_{base_f:05d}.jpg").convert("RGB")
        base = np.array(im if im.size == (W, H) else im.resize((W, H), Image.BICUBIC), np.float32)
    img = base.copy()
    # blurry-fast: blend the last frames (a smear) and draw speed lines round Joe
    blur = B0 - 0.2 <= tt < B1 + 0.2
    if blur and prev: img = img * 0.5 + prev[-1] * 0.3 + prev[0] * 0.2
    prev = (prev + [base.copy()])[-2:]
    sp = SCREEN.get(base_f) or SCREEN[min(SCREEN, key=lambda k: abs(k - base_f))]
    q = lambda v: (int(v * 8)) / 8
    if blur:
        jx, jy = sp["joe"][:2]; comp(img, layer(("lines", f % 4, int(jx / 10), int(jy / 10)), speedlines_fn(jx, jy, f % 4)))
    a = pop(tt, 0.0, 3.0)
    if a: comp(img, layer(("title", q(a)), lambda dr, a=a: text(dr, (70, 120), "Experiment #7", MARK(64), al(WHITE, a), 6, "la")))
    a = pop(tt, tl.at("My") - 0.1, tl.t_faster)
    if a: comp(img, layer(("board", q(a)), lambda dr, a=a: text(dr, (W / 2, 1300), "1 straw = 1 board", HAND(80), al(WHITE, a))))
    if 3.0 <= tt < T_PULL:
        n, g = sp["straws"], sp["gold"]
        big = tl.t_314 - 0.1 <= tt < tl.t_daisy + 0.4
        comp(img, layer(("cnt", n, g, big), counters_fn(n, g, big)))
    a = pop(tt, tl.t_daisy + 0.2, tl.t_mountain - 0.1)
    if a:
        dx, dy = sp["daisy"][:2]
        comp(img, layer(("nom", int(dx / 8), int(dy / 8), q(a)), lambda dr, dx=dx, dy=dy, a=a: text(dr, (min(dx + 200, W - 140), dy - 160), "nom.", HAND(90), al(WHITE, a))))
    if "fields" in sp:
        for k, t0 in LABEL_T.items():
            a = pop(tt, t0, tl.duration + 1, 0.25)
            fx, fy = sp["fields"][str(k)][:2]
            if not a: continue
            dx, dy = NUDGE.get(k, (0, 0))
            x = min(max(fx + dx, 215), W - 215); y = min(max(fy + dy, 290), 1450)
            title, sub_ = LABELS[k]; today = k == 7
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
    if thumb is None and tt >= tl.t_314 + 0.3: thumb = frame                  # "π ≈ 3.14!" over the hay
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
def noise(t0, dur, amp, lo=1, hi=60, env=None):
    L = int(dur * SR); t = np.arange(L) / SR; n = np.convolve(rng.normal(0, 1, L), np.ones(hi) / hi, "same")
    add(t0, n * (env(t / dur) if env else np.sin(np.pi * t / dur)) * amp)
def engine(t0, dur, f0, amp):                                  # a chugging motor
    t = np.arange(int(dur * SR)) / SR; ph = 2 * np.pi * np.cumsum(f0 * (1 + 0.05 * np.sin(2 * np.pi * 3 * t))) / SR
    w = (np.sign(np.sin(ph)) * 0.5 + np.sin(2 * ph) * 0.3) * (0.6 + 0.4 * np.sin(2 * np.pi * 9 * t) ** 2)
    add(t0, w * np.minimum(1, np.minimum(t / 0.3, (dur - t) / 0.4)) * amp)
NOTE_G, NOTE_P = 784.0, 392.0
for k in range(10):                                            # the first ten: a whoosh off the hand, a plink on landing
    noise(tl.release[k], 0.25, 0.12, hi=30); pluck(tl.land[k], NOTE_G if tl.cross[k] else NOTE_P, 0.3)
for tt in np.arange(B0, B1, 0.04): pluck(tt, NOTE_G * (1 + (tt - B0) / (B1 - B0)), 0.06, 30, 0.12)   # the blur: a buzz of plinks
a, b = tl.win["barrow"]; noise(a - 1.0, 1.1, 0.10, hi=12); noise(a, b - a + 0.3, 0.25, hi=40)          # rattle, then hay pouring
a, b = tl.win["tractor"]; engine(a - 1.4, b - a + 3.0, 38, 0.10); noise(a, b - a + 0.3, 0.3, hi=40)
a, b = tl.win["combine"]; engine(a - 1.6, b - a + 3.4, 55, 0.14); noise(a, b - a, 0.4, hi=25)
for t0, nm in ((tl.t_303, 0), (tl.t_313, 1), (tl.t_314, 2)):                                           # a chord per milestone
    for i, mult in enumerate((1, 1.25, 1.5, 2)): pluck(t0 + i * 0.06, 392.0 * (1.0, 1.125, 1.25)[nm] * mult, 0.25, 2.5, 2.5)
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
