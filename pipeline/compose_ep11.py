"""Finish Experiment 11: handwritten captions and notes over the Blender frames, the sound design,
and Joe's voice (the one-take narration). Writes renders/ep11_codes/ep11_codes[_draft].mp4 + .jpg.

Usage: .venv/Scripts/python pipeline/compose_ep11.py [--draft]

Same look as Experiment 10. New: the code card at the top (one tile per letter, in that crop's colour; the
crop Joe is standing on lit up while it's slow), a big word as each pattern shows itself, each field's code
over it when all four are side by side, and the 2000 card.
"""
import argparse, json, subprocess, sys, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FPS, ROOT, ffmpeg, FFMPEG_THREADS, gentle
gentle()
from ep11_timeline import HIGHWAY_FROM, LEAD, Timeline

ap = argparse.ArgumentParser(); ap.add_argument("--draft", action="store_true"); args = ap.parse_args()
tl = Timeline(ROOT / "episodes" / "ep11_codes.py")
D = tl.dir; frames_dir = D / ("frames_draft" if args.draft else "frames")
have = sorted(int(p.stem[2:]) for p in frames_dir.glob("f_*.jpg"))
if not have: sys.exit(f"no frames in {frames_dir}")
if not args.draft and len(have) < tl.nf: sys.exit(f"only {len(have)}/{tl.nf} frames rendered")
SCREEN = {int(k): v for k, v in json.loads((frames_dir / "screen.json").read_text()).items()}
OUT = D / f"ep11_codes{'_draft' if args.draft else ''}.mp4"
W, H = 1080, 1920
FONTS = str(ROOT / "assets" / "fonts") + "/"
def font(n, s): return ImageFont.truetype(FONTS + n, s)
HAND = lambda s: font("PatrickHand-Regular.ttf", s)
MARK = lambda s: font("PermanentMarker-Regular.ttf", s)
INK, GOLD, WHITE, BLUE = (32, 28, 30), (255, 214, 64), (255, 255, 255), (120, 190, 255)
CROPS = [(96, 160, 62), (120, 80, 48), (222, 178, 70), (236, 120, 30), (200, 60, 50), (240, 230, 210),
         (150, 90, 160), (70, 120, 200), (250, 190, 210), (40, 70, 45), (180, 210, 90), (110, 200, 200)]   # as the render (0 = grass)

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

def arrow(dr, a, b, fill=WHITE, w=7):
    """A hand-drawn-ish arrow from a to b (slight curve), outlined so it reads on any colour."""
    a, b = np.array(a, float), np.array(b, float); mid = (a + b) / 2 + np.array([-(b - a)[1], (b - a)[0]]) * 0.15
    pts = [tuple((1 - u) ** 2 * a + 2 * (1 - u) * u * mid + u ** 2 * b) for u in np.linspace(0, 1, 16)]
    d = b - pts[-3]; d /= np.linalg.norm(d) + 1e-9; n = np.array([-d[1], d[0]])
    head = [tuple(b - d * 30 + n * 16), tuple(b), tuple(b - d * 30 - n * 16)]
    for col, ww in ((INK, w + 6), (fill, w)):
        dr.line(pts, fill=col, width=ww, joint="curve"); dr.line(head, fill=col, width=ww, joint="curve")

def plate(dr, x, y, s, col, a, size=54):
    """A name plate: a little sign on a post, pointing down at (x, y)."""
    f = HAND(size); w = dr.textlength(s, font=f) + 40; top = y - 150
    dr.line([(x, y - 30), (x, top + 60)], fill=(*INK, int(255 * a)), width=8); dr.line([(x, y - 30), (x, top + 60)], fill=(*col, int(255 * a)), width=4)
    dr.rounded_rectangle((x - w / 2, top, x + w / 2, top + 64), 16, fill=(250, 244, 226, int(240 * a)), outline=(*INK, int(255 * a)), width=4)
    dr.text((x, top + 32), s, font=f, fill=(*INK, int(255 * a)), anchor="mm")

def al(col, a): return col + (int(255 * a),)
def clampx(x, m=150): return min(max(x, m), W - m)
def pop(tt, t0, t1, rise=0.18):
    """0..1 visibility for a note shown between t0 and t1 (quick fade in/out)."""
    return float(np.clip(min((tt - t0) / rise, (t1 - tt) / rise), 0, 1))

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

def speed_text(f):
    s = tl.speed(f)
    return f"SPEED ×{int(round(s, -1 if s < 1000 else -3)):,}" if s > 4 else ""

def card_fn(code, lit):
    """The code: a tile per letter in its crop's colour; `lit` = the letter Joe is on (or None)."""
    def fn(dr):
        n = len(code); tw = min(76, (W - 120) // n); x0 = (W - tw * n) / 2; y0 = 250
        for i, ch in enumerate(code):
            x = x0 + i * tw
            dr.rounded_rectangle((x + 4, y0, x + tw - 4, y0 + tw + 10), 12, fill=CROPS[i] + (235,), outline=INK, width=4)
            dr.text((x + tw / 2, y0 + tw / 2 + 5), ch, font=MARK(int(tw * 0.62)), fill=WHITE, stroke_width=4, stroke_fill=INK, anchor="mm")
            if i == lit:
                dr.rounded_rectangle((x - 2, y0 - 8, x + tw + 2, y0 + tw + 18), 14, outline=GOLD, width=7)
    return fn

WORD = {"spiral": "a spiral!", "square": "a square!", "triangle": "a triangle!", "highway": "a highway!"}
T_RULE = {"R": tl.at("R,"), "L": tl.at("L,")}
T_2000 = tl.at("2000,")
T_HW = tl.at("then", 3)                                  # "then builds a highway"
def clampxy(x, y, mx, y0, y1): return min(max(x, mx), W - mx), min(max(y, y0), y1)

# ---------------- video ----------------
ff = subprocess.Popen([ffmpeg(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                       "-r", str(FPS), "-i", "-", *FFMPEG_THREADS, "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                       "-pix_fmt", "yuv420p", str(D / "_v.mp4")], stdin=subprocess.PIPE)
src_i, base_f, base, thumb = 0, -1, None, None
for f in range(tl.nf):
    tt = f / FPS
    while src_i + 1 < len(have) and have[src_i + 1] <= f: src_i += 1
    if have[src_i] != base_f:
        base_f = have[src_i]; im = Image.open(frames_dir / f"f_{base_f:05d}.jpg").convert("RGB")
        base = np.array(im if im.size == (W, H) else im.resize((W, H), Image.BICUBIC), np.float32)
    img = base.copy()
    sp = SCREEN.get(base_f) or SCREEN[min(SCREEN, key=lambda k: abs(k - base_f))]
    q = lambda v: (int(v * 8)) / 8                              # few cached versions of a fading note
    g8 = lambda v: int(v / 8)
    name = tl.field_at(f); code = tl.code[name]
    a = pop(tt, 0.0, 3.4)
    if a: comp(img, layer(("title", q(a)), lambda dr, a=a: text(dr, (70, 120), "Experiment #11", MARK(64), al(WHITE, a), 6, "la")))
    # the code card, until all four are side by side
    if tt < tl.t_same:
        lit = sp.get("crop") if sp.get("slow") and sp.get("field") == name else None
        for letter, t0 in T_RULE.items():                       # "R, turn right. L, turn left": light the first of each
            if t0 <= tt < t0 + 1.0: lit = code.index(letter)
        comp(img, layer(("card", code, lit), card_fn(code, lit)))
    # Joe's name plate while he's big enough to see
    if sp["s"] >= 12 and tt < tl.t_same:
        jx, jy = sp["joe"][:2]
        comp(img, layer(("pj", g8(jx), g8(jy)), lambda dr, x=jx, y=jy: plate(dr, x, y, "Joe", BLUE, 1.0)))
    # the counter
    if 0.6 <= tt < tl.t_same:
        n, spd = tl.steps_at(f), speed_text(f)
        comp(img, layer(("cnt", n, spd), lambda dr, n=n, s=spd: (
            text(dr, (W - 70, 120), f"{n:,} step{'' if n == 1 else 's'}", HAND(80), WHITE, 6, "ra"),
            text(dr, (W - 70, 205), s, HAND(58), GOLD, 5, "ra") if s else None)))
    # each pattern, named as it shows itself
    for nm, t0 in tl.reveal.items():
        a = pop(tt, t0, t0 + 1.4)
        if a: comp(img, layer(("rev", nm, q(a)), lambda dr, w=WORD[nm], a=a: text(dr, (W / 2, 520), w, MARK(120), al(GOLD, a), 8)))
    a = pop(tt, T_HW, tl.t_same)
    if a: comp(img, layer(("hw", q(a)), lambda dr, a=a: text(dr, (W / 2, 640), f"from step {HIGHWAY_FROM:,}", HAND(70), al(WHITE, a), 6)))
    # all four side by side: each one's code over it
    if "codes" in sp and tt < tl.t_pull + 0.4:
        a = pop(tt, tl.t_same + 0.8, tl.t_pull + 0.4, 0.25)
        for nm, (x, y, z) in sp["codes"].items():
            if not a or z <= 0: continue
            comp(img, layer(("cl", nm, g8(x), g8(y), q(a)), lambda dr, x=x, y=y, a=a, s=tl.code[nm]:
                            text(dr, (clampx(x, 200), max(300, y - 20)), s, HAND(56), al(WHITE, a), 5)))
    a = pop(tt, T_2000, tl.t_pull)
    if a: comp(img, layer(("2000", q(a)), lambda dr, a=a: (
        text(dr, (W / 2, 330), "Gajardo et al., 2000:", HAND(70), al(WHITE, a), 6),
        text(dr, (W / 2, 420), "one walker can compute any logic circuit", HAND(56), al(GOLD, a), 5))))
    # the whole farm: today's four codes are so big the rest of it is small, so one label for #1-#10
    if "fields" in sp:
        fs = sp["fields"]; farm = np.array([fs[str(k)][:2] for k in range(1, 11)])
        for key, t0, (fx, fy), title, sub_, col in (
                ("farm", tl.t_pull + 0.9, (farm[:, 0].mean(), farm[:, 1].min()), "Experiments #1-#10", "the rest of the farm", WHITE),
                ("today", tl.t_pull + 0.4, tuple(fs["11"][:2]), "Experiment #11", "today: crop codes", GOLD)):
            a = pop(tt, t0, tl.duration + 1, 0.25)
            if not a: continue
            x, y = clampxy(fx, fy - 20, 260, 290, 1530)
            comp(img, layer(("lab", key, g8(x), g8(y), q(a)), lambda dr, x=x, y=y, a=a, title=title, sub_=sub_, col=col: (
                text(dr, (x, y - 62), title, MARK(58), al(col, a), 6), text(dr, (x, y - 4), sub_, HAND(54), al(WHITE, a), 5))))
    # captions
    for t0, t1, c in spans:
        if t0 <= tt < t1:
            act = max([i for i, o in enumerate(c) if o["t0"] + LEAD <= tt] or [0])
            comp(img, layer(("cap", c[0]["t0"], act), caption_fn([o["w"] for o in c], act)))
    frame = np.clip(img, 0, 255).astype(np.uint8)
    if thumb is None and tt >= tl.t_same + 1.8: thumb = frame        # all four patterns side by side
    ff.stdin.write(frame.tobytes())
    if f % 150 == 0: print("frame", f, "/", tl.nf, flush=True)
ff.stdin.close(); ff.wait()
if thumb is not None: Image.fromarray(thumb).save(OUT.with_suffix(".jpg"), quality=90)

# ---------------- sound ----------------
SR = 48000; au = np.zeros(int((tl.duration + 1) * SR), np.float32); rng = np.random.default_rng(5)
PENTA = [0, 2, 4, 7, 9]; NOTES = [196.0 * 2 ** ((12 * (i // 5) + PENTA[i % 5]) / 12) for i in range(20)]
def pluck(t0, f, amp=0.3, decay=7.0, dur=1.0):
    L = int(dur * SR); t = np.arange(L) / SR
    w = (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t) + 0.12 * np.sin(6 * np.pi * f * t)) * np.exp(-t * decay)
    w *= np.minimum(1, t / 0.004); o = int(t0 * SR)
    if o < len(au): au[o:o + L] += (w * amp)[:len(au) - o]
prev, prev_scene = 0, -1
for f in range(tl.nf):
    si = int(tl.scene[f]); cc = tl.log[tl.scenes[si][0]]["cc"]
    m = int(tl.sched[f])
    if si != prev_scene: prev, prev_scene = m, si
    n = m - prev; tt = f / FPS
    if 0 < n <= 2:                                           # slow: a note per step, its pitch the crop he plants
        for i in range(n): pluck(tt + i / FPS / n, NOTES[3 + int(cc[prev + i])], 0.28)
    elif n > 2 and rng.random() < 0.85:                      # fast: a sparkle in the crops' notes
        pluck(tt + rng.random() / FPS, NOTES[4 + int(cc[min(m, len(cc) - 1)])] * 2, 0.08, 12, 0.4)
    prev = m
def chord(t0, base, amp=0.3, decay=2.5, mults=(1, 1.25, 1.5, 2)):
    for i, mult in enumerate(mults): pluck(t0 + i * 0.07, base * mult, amp, decay, 2.5)
def whoosh(t_end, dur=0.8, amp=0.5):
    L = int(dur * SR); t = np.arange(L) / SR; o = int((t_end - dur) * SR)
    au[o:o + L] += np.convolve(rng.normal(0, 1, L), np.ones(60) / 60, "same") * (t / dur) ** 2 * amp
for t0, base_ in zip(tl.reveal.values(), (392.0, 440.0, 349.2, 523.3)): chord(t0, base_, 0.28)
for t0 in (tl.t_square, tl.t_tri, tl.t_hw): whoosh(t0, 0.3, 0.25)
whoosh(tl.t_same + 1.0, 1.0, 0.3); chord(T_2000, 261.6, 0.2, 2.0, (1, 1.25, 1.5))
whoosh(tl.t_pull + 1.0, 1.0, 0.35)
for i, t0 in enumerate((tl.t_pull + 0.4, tl.t_pull + 0.9)): pluck(t0, 523.3 * (1 + 0.25 * i), 0.16, 5, 1.2)   # a ding per label
t = np.arange(len(au)) / SR
pad = sum(np.sin(2 * np.pi * f_ * t + p) for f_, p in ((98, 0), (147, 1.3), (196, 2.1), (247, 0.7))) / 4
au += pad * np.clip((t - 0.5) / 3, 0, 1) * 0.07
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
