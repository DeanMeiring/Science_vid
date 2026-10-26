"""Finish Experiment 10: handwritten captions and notes over the Blender frames, the sound design,
and Joe's voice (the one-take narration). Writes renders/ep10_chicken/ep10_chicken[_draft].mp4 + .jpg.

Usage: .venv/Scripts/python pipeline/compose_ep10.py [--draft]

Same look as Experiment 9 (handwritten captions, notes that pop up and go, a counter from the run on screen).
New: name plates over Joe and the chicken (the triangle stays big, so they're small; Dean: "keep big, just
use name plates"), "this one!" over the barn she picks while it's slow, the Sierpinski card, and the
middle hole outlined in red with "never here!" while the counter runs to a million.
"""
import argparse, json, subprocess, sys, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FPS, ROOT, ffmpeg, FFMPEG_THREADS, gentle
gentle()
from ep10_timeline import LEAD, Timeline
import farm_overview as FO

ap = argparse.ArgumentParser(); ap.add_argument("--draft", action="store_true"); args = ap.parse_args()
tl = Timeline(ROOT / "episodes" / "ep10_chicken.py")
D = tl.dir; frames_dir = D / ("frames_draft" if args.draft else "frames")
have = sorted(int(p.stem[2:]) for p in frames_dir.glob("f_*.jpg"))
if not have: sys.exit(f"no frames in {frames_dir}")
if not args.draft and len(have) < tl.nf: sys.exit(f"only {len(have)}/{tl.nf} frames rendered")
SCREEN = {int(k): v for k, v in json.loads((frames_dir / "screen.json").read_text()).items()}
OUT = D / f"ep10_chicken{'_draft' if args.draft else ''}.mp4"
W, H = 1080, 1920
FONTS = str(ROOT / "assets" / "fonts") + "/"
def font(n, s): return ImageFont.truetype(FONTS + n, s)
HAND = lambda s: font("PatrickHand-Regular.ttf", s)
MARK = lambda s: font("PermanentMarker-Regular.ttf", s)
INK, GOLD, WHITE, BLUE, RED = (32, 28, 30), (255, 214, 64), (255, 255, 255), (120, 190, 255), (255, 90, 80)

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
def clampy(y, lo=300, hi=1450): return min(max(y, lo), hi)
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

# the whole farm: a label for every experiment (spread out with arrows where they crowd)
LABELS = {10: (FO.MORE10[10]["title"], FO.MORE10[10]["sub"]), 9: (FO.MORE10[9]["title"], FO.MORE10[9]["sub"]),
          8: (FO.MORE9[8]["title"], FO.MORE9[8]["sub"]), 7: (FO.MORE8[7]["title"], "π from hay"),
          6: (FO.MORE[6]["title"], FO.MORE[6]["sub"]), 5: (FO.MORE[5]["title"], FO.MORE[5]["sub"]),
          4: ("Experiment #4", "Joe & Daisy: spotless!"), **{k: (FO.FIELDS[k]["title"], FO.FIELDS[k]["sub"]) for k in (1, 2, 3)}}
NUDGE = {7: (-38, -104), 6: (56, -96), 5: (-88, 247), 8: (70, 315), 3: (-185, 450), 9: (40, 330), 10: (-101, 492)}
LABEL_T = {10: tl.t_pull + 0.3, 9: tl.t_pull + 0.5, 8: tl.t_pull + 0.7, 7: tl.t_pull + 0.9, 5: tl.t_pull + 1.1,
           6: tl.t_pull + 1.3, 4: tl.t_pull + 1.5, 1: tl.t_pull + 1.7, 2: tl.t_pull + 2.0, 3: tl.t_pull + 2.3}
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
    slow = tl.rate[f] < FPS * 0.5
    a = pop(tt, 0.0, 3.4)
    if a: comp(img, layer(("title", q(a)), lambda dr, a=a: text(dr, (70, 120), "Experiment #10", MARK(64), al(WHITE, a), 6, "la")))
    a = pop(tt, tl.t_four, tl.t_pull, 0.12)
    if a: comp(img, layer(("four", q(a)), lambda dr, a=a: text(dr, (70, 120), "4 barns", MARK(64), al(WHITE, a), 6, "la")))
    # name plates: Joe always, the chicken while she's slow enough to follow (or still)
    if tt < tl.t_pull + 0.2:
        a = pop(tt, 0.2, tl.t_pull + 0.2, 0.25)
        jx, jy = sp["joe"][:2]
        comp(img, layer(("pj", g8(jx), g8(jy), q(a)), lambda dr, x=jx, y=jy, a=a: plate(dr, x, y, "Joe", BLUE, a)))
        if slow or tl.speed(f) < 1:
            cx_, cy_ = sp["chicken"][:2]
            comp(img, layer(("pc", g8(cx_), g8(cy_), q(a)), lambda dr, x=cx_, y=cy_, a=a: plate(dr, x, y, "the chicken", WHITE, a)))
    # the barn she picked, while it's slow
    if sp.get("picked") is not None and tt < tl.t_ten:
        bx, by = sp["barns"][sp["picked"]][:2]
        comp(img, layer(("pick", g8(bx), g8(by)), lambda dr, x=bx, y=by: text(dr, (clampx(x), clampy(y - 90)), "this one!", HAND(64), GOLD)))
    # the counter
    if 0.6 <= tt < tl.t_pull:
        n, spd = tl.hops_at(f), speed_text(f)
        comp(img, layer(("cnt", n, spd), lambda dr, n=n, s=spd: (
            text(dr, (W - 70, 120), f"{n:,} hop{'' if n == 1 else 's'}", HAND(80), WHITE, 6, "ra"),
            text(dr, (W - 70, 205), s, HAND(58), GOLD, 5, "ra") if s else None)))
    # the name of the thing
    a = pop(tt, tl.t_name, tl.t_million - 0.2)
    if a: comp(img, layer(("name", q(a)), lambda dr, a=a: (
        text(dr, (W / 2, 330), "the Sierpiński triangle", HAND(96), al(GOLD, a), 7),   # the marker font has no ń
        text(dr, (W / 2, 425), "Wacław Sierpiński, 1915", HAND(64), al(WHITE, a), 5))))
    # the middle: outlined in red, never landed on
    a = pop(tt, tl.t_million, tl.t_four)
    if a and "mid" in sp:
        pts = [tuple(m[:2]) for m in sp["mid"]]; mx = sum(p[0] for p in pts) / 3; my = sum(p[1] for p in pts) / 3
        comp(img, layer(("mid", tuple(g8(v) for p in pts for v in p), q(a)), lambda dr, pts=pts, a=a, mx=mx, my=my: (
            dr.line(pts + [pts[0]], fill=al(INK, a), width=16, joint="curve"), dr.line(pts + [pts[0]], fill=al(RED, a), width=9, joint="curve"),
            text(dr, (mx, my - 30), "never here!", HAND(74), al(RED, a)),
            text(dr, (mx, my + 40), "0 footprints", HAND(56), al(WHITE, a), 5))))
    a = pop(tt, tl.t_square - 0.2, tl.t_pull)
    if a: comp(img, layer(("nopat", q(a)), lambda dr, a=a: text(dr, (W / 2, 420), "no pattern!", MARK(100), al(GOLD, a), 8)))
    # the whole farm
    if "fields" in sp:
        for k, t0 in LABEL_T.items():
            a = pop(tt, t0, tl.duration + 1, 0.25)
            if not a or str(k) not in sp["fields"]: continue
            fx, fy = sp["fields"][str(k)][:2]
            dx, dy = NUDGE.get(k, (0, 0))
            x, y = clampxy(fx + dx, fy + dy, 215, 290, 1530)
            title, sub_ = LABELS[k]; today = k == 10
            comp(img, layer(("lab", k, int(x / 6), int(y / 6), int(fx / 6), int(fy / 6), q(a)), lambda dr, x=x, y=y, fx=fx, fy=fy, a=a,
                            title=title, sub_=sub_, today=today, k=k: (
                arrow(dr, (x, y + (25 if fy > y else -95)), (fx, fy + 40 if fy > y else fy + 30), al(WHITE, a), 5) if k in NUDGE else None,
                text(dr, (x, y - 62), title, MARK(58 if today else 50), al(GOLD if today else WHITE, a), 6),
                text(dr, (x, y - 8), sub_, HAND(52), al(WHITE, a), 5))))
    # captions
    for t0, t1, c in spans:
        if t0 <= tt < t1:
            act = max([i for i, o in enumerate(c) if o["t0"] + LEAD <= tt] or [0])
            comp(img, layer(("cap", c[0]["t0"], act), caption_fn([o["w"] for o in c], act)))
    frame = np.clip(img, 0, 255).astype(np.uint8)
    if thumb is None and tt >= tl.t_name + 0.6: thumb = frame        # the triangle, named
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
def boing(t0, f0, amp=0.22, dur=0.35):
    """A little hop: a pitch that rises and falls."""
    L = int(dur * SR); t = np.arange(L) / SR; o = int(t0 * SR)
    fr = f0 * (1 + 0.5 * np.sin(np.pi * t / dur)); ph = 2 * np.pi * np.cumsum(fr) / SR
    au[o:o + L] += (np.sin(ph) * np.exp(-t * 6) * np.minimum(1, t / 0.01) * amp)[:len(au) - o]
def tap(t0, amp=0.25):
    L = int(0.05 * SR); t = np.arange(L) / SR; o = int(t0 * SR)
    au[o:o + L] += (rng.normal(0, 1, L) * np.exp(-t * 90) * amp)[:len(au) - o]
prev, prev_scene = 0, -1
for f in range(tl.nf):
    si = int(tl.scene[f]); run = tl.scenes[si][0]; pick = tl.pts[run][1]
    h = int(tl.sched[f])
    if si != prev_scene: prev, prev_scene = h, si
    n = h - prev; tt = f / FPS
    if 0 < n <= 2:                                           # slow: a hop (pitch by barn) and a footprint
        for i in range(n):
            k = int(pick[prev + i]); boing(tt - 0.5, NOTES[5 + 2 * k], 0.2); tap(tt, 0.3)
    elif n > 2 and rng.random() < 0.85:                      # fast: a patter of footprints
        tap(tt + rng.random() / FPS, 0.12); pluck(tt + rng.random() / FPS, NOTES[8 + int(rng.integers(0, 6))] * 2, 0.06, 12, 0.4)
    prev = h
def chord(t0, base, amp=0.3, decay=2.5, mults=(1, 1.25, 1.5, 2)):
    for i, mult in enumerate(mults): pluck(t0 + i * 0.07, base * mult, amp, decay, 2.5)
def whoosh(t_end, dur=0.8, amp=0.5):
    L = int(dur * SR); t = np.arange(L) / SR; o = int((t_end - dur) * SR)
    au[o:o + L] += np.convolve(rng.normal(0, 1, L), np.ones(60) / 60, "same") * (t / dur) ** 2 * amp
chord(tl.t_tri, 392.0, 0.3); chord(tl.t_name, 523.3, 0.24)
chord(tl.t_million, 147.0, 0.26, 2.0, (1, 1.19, 1.5)); pluck(tl.t_not, 98.0, 0.3, 3, 1.5)
whoosh(tl.t_four, 0.35, 0.3); chord(tl.t_square, 294.0, 0.2, 2.5, (1, 1.19, 1.5))
whoosh(tl.t_pull + 1.0, 1.0, 0.35)
for k, t0 in LABEL_T.items(): pluck(t0, 196.0 * 2 ** ((12 + 2 * k) / 12), 0.16, 5, 1.2)              # a ding per label
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
