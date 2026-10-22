"""Finish Experiment 3: handwritten captions and notes over the Blender frames, the sound design,
and Joe's voice (the one-take narration). Writes renders/ep03_sheep/ep03_sheep[_draft].mp4 + .jpg.

Usage: .venv/Scripts/python pipeline/compose_ep03.py [--draft]

The look Dean picked: the clean full-screen picture, with light personal touches only
(handwritten captions and small notes that pop up and go; no grain, tilt or filters).
Counters are counted from the same walks the picture shows (pipeline/ep03_timeline.py).
"""
import argparse, json, subprocess, sys, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FPS, ROOT, ffmpeg
from ep03_timeline import LEAD, Timeline

ap = argparse.ArgumentParser(); ap.add_argument("--draft", action="store_true"); args = ap.parse_args()
tl = Timeline(ROOT / "episodes" / "ep03_sheep.py")
D = tl.dir; frames_dir = D / ("frames_draft" if args.draft else "frames")
have = sorted(int(p.stem[2:]) for p in frames_dir.glob("f_*.jpg"))
if not have: sys.exit(f"no frames in {frames_dir}")
if not args.draft and len(have) < tl.nf: sys.exit(f"only {len(have)}/{tl.nf} frames rendered")
SCREEN = {int(k): v for k, v in json.loads((frames_dir / "screen.json").read_text()).items()}
OUT = D / f"ep03_sheep{'_draft' if args.draft else ''}.mp4"
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
    a = np.array(im); al = a[..., 3]
    if al.max() == 0: val = None
    else:
        ys, xs = np.nonzero(al)
        y0, y1, x0, x1 = max(0, ys.min() - 20), min(H, ys.max() + 21), max(0, xs.min() - 20), min(W, xs.max() + 21)
        sh = np.array(Image.fromarray(al).filter(ImageFilter.GaussianBlur(7)), np.float32)[y0:y1, x0:x1, None] / 255 * 0.55
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

def pop(tt, t0, t1, rise=0.18):
    """0..1 visibility for a note shown between t0 and t1 (quick fade in/out)."""
    return float(np.clip(min((tt - t0) / rise, (t1 - tt) / rise), 0, 1))

# ---------------- video ----------------
ff = subprocess.Popen([ffmpeg(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                       "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                       "-pix_fmt", "yuv420p", str(D / "_v.mp4")], stdin=subprocess.PIPE)
src_i, base_f, base, thumb = 0, -1, None, None
T_HOME_NOTE = (tl.t_yes, tl.t_yes + 1.3)
for f in range(tl.nf):
    tt = f / FPS
    while src_i + 1 < len(have) and have[src_i + 1] <= f: src_i += 1
    if have[src_i] != base_f:
        base_f = have[src_i]; im = Image.open(frames_dir / f"f_{base_f:05d}.jpg").convert("RGB")
        base = np.array(im if im.size == (W, H) else im.resize((W, H), Image.BICUBIC), np.float32)
    img = base.copy()
    sp = SCREEN.get(base_f) or SCREEN[min(SCREEN, key=lambda k: abs(k - base_f))]
    q = lambda v: (int(v * 8)) / 8                              # few cached versions of a fading note
    # the title, small, handwritten
    a = pop(tt, 0.0, 3.4)
    if a: comp(img, layer(("title", q(a)), lambda dr, a=a: text(dr, (70, 120), "Experiment #3", MARK(64),
                                                                  WHITE + (int(255 * a),), 6, "la")))
    # "Daisy!" and "home", with arrows
    a = pop(tt, 0.8, 4.6)
    if a and sp["daisy"][2] > 0:
        dx, dy = sp["daisy"][:2]; key = ("daisy", int(dx / 6), int(dy / 6), q(a))
        def fn(dr, dx=dx, dy=dy, a=a):
            tx, ty = dx + 150, dy + 210
            arrow(dr, (tx - 40, ty - 50), (dx + 25, dy + 35), WHITE + (int(255 * a),))
            text(dr, (tx + 10, ty), "Daisy!", HAND(78), WHITE + (int(255 * a),), 6, "lm")
        comp(img, layer(key, fn))
    a = pop(tt, 2.0, 5.2)
    if a and sp["barn"][2] > 0:
        bx, by = sp["barn"][:2]; key = ("home", int(bx / 6), int(by / 6), q(a))
        def fn(dr, bx=bx, by=by, a=a):
            tx, ty = bx - 260, by - 230
            arrow(dr, (tx + 90, ty + 40), (bx - 60, by - 60), WHITE + (int(255 * a),))
            text(dr, (tx, ty), "home", HAND(78), WHITE + (int(255 * a),), 6, "mm")
        comp(img, layer(key, fn))
    # Daisy's step counter, then "home!" on Yes
    if tl.at("No") - 0.2 <= tt < tl.t_yes:
        st = int(tl.daisy_step[f])
        comp(img, layer(("step", st), lambda dr, st=st: text(dr, (W / 2, 150), f"step {st:,}", HAND(92), WHITE, 6)))
    a = pop(tt, *T_HOME_NOTE)
    if a:
        hx_, hy_ = sp["home"][:2]; grow = 0.7 + 0.3 * min(1, (tt - tl.t_yes) / 0.15)
        comp(img, layer(("homenote", int(hx_ / 6), int(hy_ / 6), q(a), round(grow, 2)),
                        lambda dr, a=a, g=grow, x=hx_, y=hy_: text(dr, (x, y - 170), "home!", MARK(int(110 * g)),
                                                                  GOLD + (int(255 * a),), 8)))
    # the herd's counter
    if tl.t_herd + 0.4 <= tt < tl.t_chicken + 0.3:
        k = tl.home_count(tl.herd_home, int(tl.herd_step[f])); n = len(tl.herd); st = int(tl.herd_step[f])
        comp(img, layer(("herd", k, st // 50), lambda dr, k=k, n=n, st=st: (
            text(dr, (W / 2, 140), f"home: {k} / {n} sheep", HAND(88), WHITE, 6),
            text(dr, (W / 2, 235), f"{st:,} steps each", HAND(60), WHITE, 5))))
    # the chickens' counter
    if tl.t_fly <= tt < tl.t_quote:
        k = tl.home_count(tl.flock_home, int(tl.flock_step[f])); n = len(tl.flock); st = int(tl.flock_step[f])
        comp(img, layer(("flock", k, st // 25), lambda dr, k=k, n=n, st=st: (
            text(dr, (W / 2, 140), f"home: {k} / {n} chickens", HAND(88), WHITE, 6),
            text(dr, (W / 2, 235), f"{st:,} flaps each", HAND(60), WHITE, 5))))
    # Joe, at the end
    a = pop(tt, tl.t_next + 0.6, tl.duration + 1)
    if a and sp["joe"][2] > 0:
        jx, jy = sp["joe"][:2]; key = ("joe", int(jx / 6), int(jy / 6), q(a))
        def fn(dr, jx=jx, jy=jy, a=a):
            tx, ty = jx + 170, jy - 260
            arrow(dr, (tx - 30, ty + 50), (jx + 40, jy - 50), WHITE + (int(255 * a),))
            text(dr, (tx, ty), "that's me!", HAND(76), WHITE + (int(255 * a),), 6, "lm")
        comp(img, layer(key, fn))
    # captions
    for t0, t1, c in spans:
        if t0 <= tt < t1:
            act = max([i for i, o in enumerate(c) if o["t0"] + LEAD <= tt] or [0])
            comp(img, layer(("cap", c[0]["t0"], act), caption_fn([o["w"] for o in c], act)))
    frame = np.clip(img, 0, 255).astype(np.uint8)
    if thumb is None and tt >= tl.t_herd + 4.0: thumb = frame        # the herd's colourful ribbons
    ff.stdin.write(frame.tobytes())
    if f % 150 == 0: print("frame", f, "/", tl.nf, flush=True)
ff.stdin.close(); ff.wait()
if not args.draft and thumb is not None: Image.fromarray(thumb).save(OUT.with_suffix(".jpg"), quality=90)

# ---------------- sound ----------------
SR = 48000; au = np.zeros(int((tl.duration + 1) * SR), np.float32); rng = np.random.default_rng(5)
PENTA = [0, 2, 4, 7, 9]; NOTES = [196.0 * 2 ** ((12 * (i // 5) + PENTA[i % 5]) / 12) for i in range(20)]
def pluck(t0, f, amp=0.3, decay=7.0, dur=1.0):
    L = int(dur * SR); t = np.arange(L) / SR
    w = (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(4 * np.pi * f * t) + 0.12 * np.sin(6 * np.pi * f * t)) * np.exp(-t * decay)
    w *= np.minimum(1, t / 0.004); o = int(t0 * SR)
    if o < len(au): au[o:o + L] += (w * amp)[:len(au) - o]
def note_for(dist): return NOTES[max(0, 15 - min(15, int(dist) // 4))]   # close to home = high
prev = 0
for f in range(tl.nf):                                     # Daisy: a pluck per step, sparkle when fast
    st = int(tl.daisy_step[f]); n = st - prev; prev = st
    if tl.t_herd <= f / FPS: break
    dist = np.abs(tl.daisy[min(st, len(tl.daisy) - 1)]).sum()
    if 0 < n <= 2:
        for i in range(n): pluck(f / FPS + i / FPS / n, note_for(dist))
    elif n > 2 and rng.random() < 0.7:
        pluck(f / FPS + rng.random() / FPS, note_for(dist) * 2, 0.12, 10, 0.6)
# "Yes!": a bell chord rising, and a soft whoosh
for i, mult in enumerate((1, 1.25, 1.5, 2)):
    pluck(tl.t_yes + i * 0.07, 392.0 * mult, 0.32, 2.5, 2.5)
L = int(0.8 * SR); t = np.arange(L) / SR; o = int((tl.t_yes - 0.6) * SR)
au[o:o + L] += np.convolve(rng.normal(0, 1, L), np.ones(60) / 60, "same") * (t / 0.8) ** 2 * 0.5
# the herd and the chickens: a soft ding as each one gets home (higher for chickens)
def dings(homes, steps, t0, octave, amp):
    last_t = -1
    for h in sorted(x for x in homes if x is not None):
        fi = np.searchsorted(steps, h)
        if fi >= tl.nf: continue
        tt = max(fi / FPS, t0, last_t + 0.09); last_t = tt
        pluck(tt, NOTES[int(rng.integers(5, 15))] * octave, amp, 5, 1.2)
dings(tl.herd_home, tl.herd_step, tl.t_herd, 2, 0.16)
L = int(0.9 * SR); t = np.arange(L) / SR; o = int(tl.t_fly * SR)      # flutter as the chickens take off
au[o:o + L] += rng.normal(0, 1, L) * (0.5 + 0.5 * np.sin(2 * np.pi * 22 * t)) * np.exp(-t * 3) * 0.25
dings(tl.flock_home, tl.flock_step, tl.t_fly, 4, 0.18)
# a soft warm pad under everything; a final chord at the end
t = np.arange(len(au)) / SR
pad = sum(np.sin(2 * np.pi * f_ * t + p) for f_, p in ((98, 0), (147, 1.3), (196, 2.1), (247, 0.7))) / 4
swell = np.clip((t - 0.5) / 3, 0, 1) * (0.7 + 0.3 * ((t > tl.t_chicken) & (t < tl.t_next)))
au += pad * swell * 0.07
for i, mult in enumerate((1, 1.25, 1.5)): pluck(tl.t_next + 2.4 + i * 0.12, 261.6 * mult, 0.18, 1.6, 3.0)
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
