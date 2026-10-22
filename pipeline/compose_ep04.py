"""Finish Experiment 4: handwritten captions and notes over the Blender frames, the sound design,
and Joe's voice (the one-take narration). Writes renders/ep04_farmers/ep04_farmers[_draft].mp4 + .jpg.

Usage: .venv/Scripts/python pipeline/compose_ep04.py [--draft]

Same look as Experiment 3 (handwritten captions and small notes that pop up and go). The counters
are "round n" and "SPEED xn" (Dean: no graph), counted from the same run the picture shows.
"""
import argparse, json, subprocess, sys, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FPS, ROOT, ffmpeg
from ep04_timeline import LEAD, Timeline
import farm_overview as FO

ap = argparse.ArgumentParser(); ap.add_argument("--draft", action="store_true"); args = ap.parse_args()
tl = Timeline(ROOT / "episodes" / "ep04_farmers.py")
D = tl.dir; frames_dir = D / ("frames_draft" if args.draft else "frames")
have = sorted(int(p.stem[2:]) for p in frames_dir.glob("f_*.jpg"))
if not have: sys.exit(f"no frames in {frames_dir}")
if not args.draft and len(have) < tl.nf: sys.exit(f"only {len(have)}/{tl.nf} frames rendered")
SCREEN = {int(k): v for k, v in json.loads((frames_dir / "screen.json").read_text()).items()}
OUT = D / f"ep04_farmers{'_draft' if args.draft else ''}.mp4"
W, H = 1080, 1920
FONTS = str(ROOT / "assets" / "fonts") + "/"
def font(n, s): return ImageFont.truetype(FONTS + n, s)
HAND = lambda s: font("PatrickHand-Regular.ttf", s)
MARK = lambda s: font("PermanentMarker-Regular.ttf", s)
INK, GOLD, WHITE, BLUE = (32, 28, 30), (255, 214, 64), (255, 255, 255), (120, 190, 255)
WHO = ((BLUE, "me"), (GOLD, "Daisy!"))
ACTION = {(0, True): "harvest", (0, False): "plant", (1, True): "munch!", (1, False): "compost"}

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

def al(col, a): return col + (int(255 * a),)

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

def speed_text(f):
    s = tl.speed(f)
    return f"SPEED ×{int(round(s, -1 if s < 1000 else -2)):,}" if s > 4 else ""

# when each overview field's label appears (just after it grows in; see render_ep04.REVEAL)
LABEL_T = {4: tl.t_thanks + 0.5, 1: tl.t_thanks + 1.2, 2: tl.t_thanks + 1.8, 3: tl.t_thanks + 2.4}

# ---------------- video ----------------
ff = subprocess.Popen([ffmpeg(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                       "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                       "-pix_fmt", "yuv420p", str(D / "_v.mp4")], stdin=subprocess.PIPE)
src_i, base_f, base, thumb = 0, -1, None, None
last_act, last_act_t = None, -9.0
for f in range(tl.nf):
    tt = f / FPS
    while src_i + 1 < len(have) and have[src_i + 1] <= f: src_i += 1
    if have[src_i] != base_f:
        base_f = have[src_i]; im = Image.open(frames_dir / f"f_{base_f:05d}.jpg").convert("RGB")
        base = np.array(im if im.size == (W, H) else im.resize((W, H), Image.BICUBIC), np.float32)
    img = base.copy()
    sp = SCREEN.get(base_f) or SCREEN[min(SCREEN, key=lambda k: abs(k - base_f))]
    q = lambda v: (int(v * 8)) / 8                              # few cached versions of a fading note
    a = pop(tt, 0.0, 3.4)
    if a: comp(img, layer(("title", q(a)), lambda dr, a=a: text(dr, (70, 120), "Experiment #4", MARK(64), al(WHITE, a), 6, "la")))
    # "me" and "Daisy!", with arrows in their colours
    a = pop(tt, 0.5, 3.6)
    if a:
        (jx, jy), (dx, dy) = sp["joe"][:2], sp["daisy"][:2]; left = jx < dx
        key = ("who", int(jx / 8), int(jy / 8), int(dx / 8), int(dy / 8), q(a))
        def fn(dr, jx=jx, jy=jy, dx=dx, dy=dy, a=a, left=left):
            sj, sd = (-1 if left else 1), (1 if left else -1)
            arrow(dr, (jx + sj * 150, jy + 250), (jx + sj * 20, jy + 60), al(BLUE, a))
            text(dr, (jx + sj * 180, jy + 300), "me", HAND(80), al(BLUE, a))
            arrow(dr, (dx + sd * 150, dy - 250), (dx + sd * 25, dy - 70), al(GOLD, a))
            text(dr, (dx + sd * 180, dy - 300), "Daisy!", HAND(80), al(GOLD, a))
        comp(img, layer(key, fn))
    # what each of them just did, while it's slow
    if sp.get("act") and 3.4 <= tt < tl.t_slow_end + 0.6:
        last_act, last_act_t = sp["act"], tt
    a = pop(tt, last_act_t - 0.05, last_act_t + 0.55) if last_act and tt < tl.t_slow_end + 1.0 else 0
    if a:
        who = last_act["who"]; px, py = sp["joe" if who == 0 else "daisy"][:2]
        ox = sp["daisy" if who == 0 else "joe"][0]                   # the note goes on the side away from the other one
        word = ACTION[(who, last_act["dug"])]; col = WHO[who][0]
        comp(img, layer(("act", word, int(px / 8), int(py / 8), px >= ox, q(a)),
                        lambda dr, w=word, x=px, y=py, a=a, col=col, ox=ox: text(dr, (min(max(x + (200 if x >= ox else -200), 150), W - 150), y - 110), w, HAND(76), al(col, a))))
    # counters
    if 0.6 <= tt < tl.t_thanks:
        rnd, spd = sp["round"] if f == base_f else int(tl.sched[f]) // 2, speed_text(f)
        comp(img, layer(("cnt", rnd, spd), lambda dr, r=rnd, s=spd: (
            text(dr, (W - 70, 120), f"round {r:,}", HAND(80), WHITE, 6, "ra"),
            text(dr, (W - 70, 205), s, HAND(58), GOLD, 5, "ra") if s else None)))
    # the big moments
    a = pop(tt, tl.t_meet - 0.1, tl.t_meet + 1.7)
    if a:
        mx = (sp["joe"][0] + sp["daisy"][0]) / 2; my = min(sp["joe"][1], sp["daisy"][1])
        comp(img, layer(("meet", int(mx / 8), int(my / 8), q(a)),
                        lambda dr, x=mx, y=my, a=a: text(dr, (x, max(330, y - 220)), "we meet!", HAND(104), al(WHITE, a))))
    a = pop(tt, tl.t_clean, tl.t_again)
    if a: comp(img, layer(("clean", q(a)), lambda dr, a=a: text(dr, (W / 2, 560), "spotless!", MARK(120), al(GOLD, a), 8)))
    a = pop(tt, tl.t_home, tl.t_thanks + 0.2)
    if a: comp(img, layer(("home", q(a)), lambda dr, a=a: text(dr, (W / 2, 560), "home!", MARK(130), al(GOLD, a), 8)))
    # the whole farm: a label above each experiment
    if "fields" in sp:
        for k, t0 in LABEL_T.items():
            a = pop(tt, t0, tl.duration + 1, 0.25)
            x, y, z = sp["fields"][str(k)]
            if not a or z <= 0: continue
            x = min(max(x, 190), W - 190); y = min(max(y, 290), 1450)
            fd = FO.FIELDS[k]
            comp(img, layer(("lab", k, int(x / 6), int(y / 6), q(a)), lambda dr, x=x, y=y, a=a, fd=fd, k=k: (
                text(dr, (x, y - 62), fd["title"], MARK(50 if k != 4 else 58), al(GOLD if k == 4 else WHITE, a), 6),
                text(dr, (x, y - 8), fd["sub"], HAND(52), al(WHITE, a), 5))))
    # captions
    for t0, t1, c in spans:
        if t0 <= tt < t1:
            act = max([i for i, o in enumerate(c) if o["t0"] + LEAD <= tt] or [0])
            comp(img, layer(("cap", c[0]["t0"], act), caption_fn([o["w"] for o in c], act)))
    frame = np.clip(img, 0, 255).astype(np.uint8)
    if thumb is None and int(tl.sched[f]) // 2 >= 1100: thumb = frame        # the biggest, most colourful mess
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
def pop_snd(t0, amp=0.25):
    L = int(0.08 * SR); t = np.arange(L) / SR; o = int(t0 * SR)
    au[o:o + L] += (np.sin(2 * np.pi * (500 + 900 * t / 0.08) * t) * np.exp(-t * 60) * amp)[:len(au) - o]
# the mess as music: notes climb with the amount of dirt, and fall back as it's undone
dirt_n = np.zeros(len(tl.moves) + 1, np.int32); dset = set()
for i, (k, sq, dug, _, _) in enumerate(tl.moves):
    (dset.add if dug else dset.discard)(sq); dirt_n[i + 1] = len(dset)
def note_for(n, k): return NOTES[min(19, 3 + n // 14 + 2 * k)]
prev = 0
for f in range(tl.nf):
    m = int(tl.sched[f]); n = m - prev
    tt = f / FPS
    if 0 < n <= 3:                                           # slow: one note per move (Daisy a little higher)
        for i in range(n):
            k, sq, dug = tl.moves[prev + i][:3]; t0 = tt + i / FPS / n
            pluck(t0, note_for(dirt_n[prev + i + 1], k) * (1 if dug else 0.75), 0.3)
            if not dug and tl.rate[f] < FPS * 0.5: pop_snd(t0 + 0.12)          # compost / a sprout pops up
    elif n > 3 and rng.random() < 0.8:                       # fast: a sparkle that follows the mess
        pluck(tt + rng.random() / FPS, note_for(dirt_n[m], 0) * 2, 0.11, 10, 0.5)
    prev = m
def chord(t0, base, amp=0.3, decay=2.5):
    for i, mult in enumerate((1, 1.25, 1.5, 2)): pluck(t0 + i * 0.07, base * mult, amp, decay, 2.5)
def whoosh(t_end, dur=0.8, amp=0.5):
    L = int(dur * SR); t = np.arange(L) / SR; o = int((t_end - dur) * SR)
    au[o:o + L] += np.convolve(rng.normal(0, 1, L), np.ones(60) / 60, "same") * (t / dur) ** 2 * amp
whoosh(tl.t_meet); chord(tl.t_meet, 330.0, 0.22, 3.0)
chord(tl.t_clean, 392.0, 0.3); chord(tl.t_home, 392.0, 0.34); chord(tl.t_home + 0.35, 523.3, 0.2)
whoosh(tl.t_thanks + 0.9, 1.0, 0.35)
for k, t0 in LABEL_T.items(): pluck(t0, NOTES[8 + 2 * k], 0.16, 5, 1.2)              # a ding per label
t = np.arange(len(au)) / SR
pad = sum(np.sin(2 * np.pi * f_ * t + p) for f_, p in ((98, 0), (147, 1.3), (196, 2.1), (247, 0.7))) / 4
au += pad * np.clip((t - 0.5) / 3, 0, 1) * 0.07
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
