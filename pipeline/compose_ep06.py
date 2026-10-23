"""Finish Experiment 6: handwritten captions and notes over the Blender frames, the sound design,
and Joe's voice (the one-take narration). Writes renders/ep06_barns/ep06_barns[_draft].mp4 + .jpg.

Usage: .venv/Scripts/python pipeline/compose_ep06.py [--draft]

Notes: barn numbers, "?" over each barn when Joe mentions the tractor, "Daisy's pick", "goat!",
"switch?", "50/50?", the live counts above the two bars of tractors, "2 out of 3!", "1 in 3" /
"2 in 3" over the barns, "there it is!", "10,000 letters!", and the whole farm's labels.
"""
import argparse, json, subprocess, sys, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FPS, ROOT, ffmpeg, FFMPEG_THREADS, gentle
gentle()
from ep06_timeline import LEAD, Timeline
import farm_overview as FO

ap = argparse.ArgumentParser(); ap.add_argument("--draft", action="store_true"); args = ap.parse_args()
tl = Timeline(ROOT / "episodes" / "ep06_barns.py")
D = tl.dir; frames_dir = D / ("frames_draft" if args.draft else "frames")
have = sorted(int(p.stem[2:]) for p in frames_dir.glob("f_*.jpg"))
if not have: sys.exit(f"no frames in {frames_dir}")
if not args.draft and len(have) < tl.nf: sys.exit(f"only {len(have)}/{tl.nf} frames rendered")
SCREEN = {int(k): v for k, v in json.loads((frames_dir / "screen.json").read_text()).items()}
OUT = D / f"ep06_barns{'_draft' if args.draft else ''}.mp4"
W, H = 1080, 1920
FONTS = str(ROOT / "assets" / "fonts") + "/"
def font(n, s): return ImageFont.truetype(FONTS + n, s)
HAND = lambda s: font("PatrickHand-Regular.ttf", s)
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
    """A hand-drawn-ish arrow from a to b (slight curve), outlined so it reads on any colour."""
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

# ---------------- the whole farm's labels ----------------
T_PULL = tl.t_next - 0.3
LABELS = {6: ("Experiment #6", "today: switch!"), 5: ("Experiment #5", "the crop circle"), 4: ("Experiment #4", "Joe & Daisy: spotless!"),
          **{k: (FO.FIELDS[k]["title"], FO.FIELDS[k]["sub"]) for k in (1, 2, 3)}}
NUDGE = {5: (-120, -23), 4: (30, -191), 6: (158, -34)}   # #4, #5, #6 sit close together: labels spread out, with arrows
LABEL_T = {6: T_PULL + 0.4, 5: T_PULL + 0.8, 4: T_PULL + 1.1, 1: T_PULL + 1.4, 2: T_PULL + 1.9, 3: T_PULL + 2.4}

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
    q = lambda v: (int(v * 8)) / 8
    B = sp["barns"]
    a = pop(tt, 0.0, 3.0)
    if a: comp(img, layer(("title", q(a)), lambda dr, a=a: text(dr, (70, 120), "Experiment #6", MARK(64), al(WHITE, a), 6, "la")))
    # the barns: numbers, then "?" over each while Joe mentions the tractor
    a = max(pop(tt, 0.3, tl.t_fifty + 0.2), pop(tt, tl.t_her - 0.1, tl.t_1990))
    q_ = pop(tt, tl.t_tractor - 0.1, tl.t_pick - 0.3)
    if a:
        comp(img, layer(("nums", tuple(map(tuple, B)), q(a), q(q_)), lambda dr, B=B, a=a, q_=q_: [
            text(dr, (x, y - 40), "?" if q_ > 0.5 else str(i + 1), MARK(96), al(GOLD if q_ > 0.5 else WHITE, a), 7)
            for i, (x, y) in enumerate(B)]))
    a = pop(tt, tl.t_pick - 0.4, tl.t_goat - 0.3)
    if a:
        dx, dy = sp["daisy"]
        comp(img, layer(("pick", int(dx / 6), int(dy / 6), q(a)), lambda dr, dx=dx, dy=dy, a=a: (
            arrow(dr, (dx + 130, dy + 240), (dx + 20, dy + 50), al(GOLD, a)), text(dr, (dx + 170, dy + 290), "Daisy's pick", HAND(72), al(GOLD, a)))))
    a = pop(tt, tl.t_goat, tl.t_fifty)
    if a: comp(img, layer(("goat", int(B[2][0] / 6), q(a)), lambda dr, x=B[2][0], y=B[2][1], a=a: text(dr, (min(x, W - 130), y + 420), "goat!", HAND(84), al(WHITE, a))))
    a = pop(tt, tl.t_switch - 0.1, tl.t_fifty)
    if a:
        comp(img, layer(("sw", int(B[0][0] / 6), q(a)), lambda dr, B=B, a=a: (
            arrow(dr, (B[0][0] + 60, B[0][1] - 110), (B[1][0] - 60, B[1][1] - 110), al(GOLD, a)),
            text(dr, ((B[0][0] + B[1][0]) / 2, B[0][1] - 200), "switch?", HAND(80), al(GOLD, a)))))
    a = pop(tt, tl.t_fifty - 0.1, tl.t_fifty + 1.2)
    if a: comp(img, layer(("5050", q(a)), lambda dr, a=a: text(dr, (W / 2, 420), "50 / 50 ?", MARK(110), al(WHITE, a), 8)))
    # the 1,000 games: live counts above the bars
    if tl.t_fifty + 0.5 <= tt < tl.t_her:
        for k in ("stay", "switch"):
            x, y = sp["tops"][k]; n = sp[k]; y = max(y, 480)          # stay clear of the games counter
            comp(img, layer(("bar", k, n, int(x / 6), int(y / 6)), lambda dr, x=x, y=y, n=n, k=k: (
                text(dr, (x, y - 120), f"{n}", MARK(96), GOLD if k == "switch" else WHITE, 7),
                text(dr, (x, y - 45), f"{k} wins", HAND(64), WHITE, 5))))
        comp(img, layer(("games", sp["played"]), lambda dr, n=sp["played"]: text(dr, (W - 70, 120), f"games: {n:,}", HAND(80), WHITE, 6, "ra")))
    a = pop(tt, tl.t_23, tl.t_her)
    if a: comp(img, layer(("23", q(a)), lambda dr, a=a: text(dr, (W / 2, 330), "2 out of 3!", MARK(110), al(GOLD, a), 8)))
    # back at the barns: 1 in 3 for her pick, 2 in 3 for the other two
    a = pop(tt, tl.t_her + 0.6, tl.t_1990)
    if a:
        comp(img, layer(("odds", tuple(map(tuple, B)), q(a)), lambda dr, B=B, a=a: (
            text(dr, (B[0][0], B[0][1] - 150), "1 in 3", HAND(76), al(WHITE, a)),
            dr.line([(B[1][0] - 60, B[1][1] - 150), (B[2][0] + 60, B[2][1] - 150)], fill=al(GOLD, a), width=8),
            text(dr, ((B[1][0] + B[2][0]) / 2, B[1][1] - 210), "2 in 3", HAND(76), al(GOLD, a)))))
    a = pop(tt, tl.t_showed + 0.3, tl.t_1990 + 0.3)
    if a: comp(img, layer(("there", int(B[1][0] / 6), q(a)), lambda dr, x=B[1][0], y=B[1][1], a=a: text(dr, (x, y + 560), "there it is!", HAND(84), al(GOLD, a))))
    a = pop(tt, tl.t_1990 + 0.3, tl.t_even)
    if a: comp(img, layer(("letters", q(a)), lambda dr, a=a: text(dr, (W / 2, 330), "10,000 letters!", MARK(100), al(WHITE, a), 8)))
    # the whole farm
    if "fields" in sp:
        for k, t0 in LABEL_T.items():
            a = pop(tt, t0, tl.duration + 1, 0.25)
            fx, fy = sp["fields"][str(k)]
            if not a: continue
            dx, dy = NUDGE.get(k, (0, 0))
            x = min(max(fx + dx, 215), W - 215); y = min(max(fy + dy, 290), 1450)
            title, sub_ = LABELS[k]; today = k == 6
            comp(img, layer(("lab", k, int(x / 6), int(y / 6), int(fx / 6), int(fy / 6), q(a)), lambda dr, x=x, y=y, fx=fx, fy=fy, a=a,
                            title=title, sub_=sub_, today=today, k=k: (
                arrow(dr, (x, y + 25), (fx, fy + 40), al(WHITE, a), 5) if k in NUDGE else None,
                text(dr, (x, y - 62), title, MARK(58 if today else 50), al(GOLD if today else WHITE, a), 6),
                text(dr, (x, y - 8), sub_, HAND(52), al(WHITE, a), 5))))
    # captions
    for t0, t1, c in spans:
        if t0 <= tt < t1:
            act = max([i for i, o in enumerate(c) if o["t0"] + LEAD <= tt] or [0])
            comp(img, layer(("cap", c[0]["t0"], act), caption_fn([o["w"] for o in c], act)))
    frame = np.clip(img, 0, 255).astype(np.uint8)
    if thumb is None and tt >= tl.t_661 + 0.6: thumb = frame            # the two bars: 339 vs 661
    ff.stdin.write(frame.tobytes())
    if f % 150 == 0: print("frame", f, "/", tl.nf, flush=True)
ff.stdin.close(); ff.wait()
if not args.draft and thumb is not None: Image.fromarray(thumb).save(OUT.with_suffix(".jpg"), quality=90)

# ---------------- sound ----------------
SR = 48000; au = np.zeros(int((tl.duration + 1) * SR), np.float32); rng = np.random.default_rng(5)
PENTA = [0, 2, 4, 7, 9]; NOTES = [196.0 * 2 ** ((12 * (i // 5) + PENTA[i % 5]) / 12) for i in range(20)]
def add(t0, w):
    o = int(t0 * SR)
    if 0 <= o < len(au): au[o:o + len(w)] += w[:len(au) - o]
def pluck(t0, f, amp=0.3, decay=7.0, dur=1.0):
    t = np.arange(int(dur * SR)) / SR
    w = (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t) + 0.12 * np.sin(6 * np.pi * f * t)) * np.exp(-t * decay)
    add(t0, w * np.minimum(1, t / 0.004) * amp)
def creak(t0, dur=0.6, amp=0.18):                          # a barn door swinging
    t = np.arange(int(dur * SR)) / SR; f = 180 + 120 * np.sin(2 * np.pi * 3 * t) + 60 * t
    add(t0, np.sign(np.sin(2 * np.pi * np.cumsum(f) / SR)) * 0.4 * np.exp(-((t - dur / 2) / (dur / 2.5)) ** 2) * amp)
def bleat(t0, amp=0.25):                                   # the goat: "meh-eh-eh"
    t = np.arange(int(0.7 * SR)) / SR; f = 420 * (1 + 0.06 * np.sin(2 * np.pi * 11 * t)) * (1 - 0.15 * t)
    ph = 2 * np.pi * np.cumsum(f) / SR
    w = (np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.3 * np.sin(3 * ph)) * np.minimum(1, t / 0.03) * np.exp(-t * 2.5)
    add(t0, w * amp * 0.5)
def horn(t0, amp=0.25):                                    # the tractor: beep-beep
    for k in range(2):
        t = np.arange(int(0.16 * SR)) / SR; ph = 2 * np.pi * 440 * t
        add(t0 + k * 0.22, (np.sign(np.sin(ph)) * 0.4 + np.sin(2 * ph) * 0.3) * np.minimum(1, t / 0.01) * np.minimum(1, (0.16 - t) / 0.02) * amp)
def flutter(t0, dur=2.6, amp=0.2):                         # thousands of letters fluttering down
    t = np.arange(int(dur * SR)) / SR
    add(t0, rng.normal(0, 1, len(t)) * (0.5 + 0.5 * np.sin(2 * np.pi * 17 * t)) * np.sin(np.pi * t / dur) * amp)
def chord(t0, base, amp=0.3, decay=2.5):
    for i, mult in enumerate((1, 1.25, 1.5, 2)): pluck(t0 + i * 0.06, base * mult, amp, decay, 2.5)
# trotting hooves, then the doors
for k in range(int((tl.t_pick - 0.4) / 0.23)): pluck(0.1 + k * 0.23, 900 + 120 * (k % 2), 0.05, 40, 0.1)
creak(tl.t_goat - 0.4); bleat(tl.t_goat + 0.35)
# one note per game: stay wins low, switch wins high; a sparkle once it's racing
prev = 0
for f in range(tl.nf):
    n = tl.won(f)["played"]; tt = f / FPS
    if 0 < n - prev <= 2:
        for i in range(prev, n): pluck(tt, NOTES[5] if tl.stay_win[i] else NOTES[9], 0.3)
    elif n - prev > 2 and rng.random() < 0.85:
        pluck(tt + rng.random() / FPS, NOTES[10 + int(rng.integers(0, 8))], 0.1, 10, 0.5)
    prev = n
chord(tl.t_339, 392.0, 0.28); chord(tl.t_661, 440.0, 0.32); chord(tl.t_23, 523.3, 0.22)
creak(tl.t_showed - 0.2); horn(tl.t_showed + 0.5); chord(tl.t_showed + 0.5, 392.0, 0.2)
flutter(tl.t_1990)
L = int(1.0 * SR); t = np.arange(L) / SR
add(tl.t_next + 0.6, np.convolve(rng.normal(0, 1, L), np.ones(60) / 60, "same") * (t / 1.0) ** 2 * 0.35)
for k, t0 in LABEL_T.items(): pluck(t0, NOTES[6 + 2 * min(k, 6)], 0.16, 5, 1.2)
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
