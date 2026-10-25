"""Finish Experiment 9: handwritten captions and notes over the Blender frames, the sound design,
and Joe's voice (the one-take narration). Writes renders/ep09_helpers/ep09_helpers[_draft].mp4 + .jpg.

Usage: .venv/Scripts/python pipeline/compose_ep09.py [--draft]

Same look as Experiment 4 (handwritten captions, small notes that pop up and go, "round n" and
"SPEED xn" counted from the run on screen). New: a name over each helper, a "bye!" as each one walks
off, "all home: 0 of 3,000", and the tally card (1 to 6 farmers) that fills in as Joe reads it out.
"""
import argparse, json, subprocess, sys, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FPS, ROOT, ffmpeg, FFMPEG_THREADS, gentle
gentle()
from ep09_timeline import CAST, LEAD, Timeline

ap = argparse.ArgumentParser(); ap.add_argument("--draft", action="store_true"); args = ap.parse_args()
tl = Timeline(ROOT / "episodes" / "ep09_helpers.py")
D = tl.dir; frames_dir = D / ("frames_draft" if args.draft else "frames")
have = sorted(int(p.stem[2:]) for p in frames_dir.glob("f_*.jpg"))
if not have: sys.exit(f"no frames in {frames_dir}")
if not args.draft and len(have) < tl.nf: sys.exit(f"only {len(have)}/{tl.nf} frames rendered")
SCREEN = {int(k): v for k, v in json.loads((frames_dir / "screen.json").read_text()).items()}
OUT = D / f"ep09_helpers{'_draft' if args.draft else ''}.mp4"
W, H = 1080, 1920
FONTS = str(ROOT / "assets" / "fonts") + "/"
def font(n, s): return ImageFont.truetype(FONTS + n, s)
HAND = lambda s: font("PatrickHand-Regular.ttf", s)
MARK = lambda s: font("PermanentMarker-Regular.ttf", s)
INK, GOLD, WHITE, BLUE = (32, 28, 30), (255, 214, 64), (255, 255, 255), (120, 190, 255)
RED, PINK, GREEN, GREY = (255, 110, 96), (255, 150, 200), (140, 235, 110), (200, 200, 200)
COL = dict(joe=BLUE, daisy=GOLD, cow=RED, pig=PINK)
NAME = dict(joe="me", daisy="Daisy", cow="cow", pig="pig")
ACTION = {(True, True): "harvest", (True, False): "plant", (False, True): "munch!", (False, False): "compost"}

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

def al(col, a): return col + (int(255 * a),)
def clampx(x, m=150): return min(max(x, m), W - m)
def clampy(y, lo=300, hi=1450): return min(max(y, lo), hi)

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

# ---------------- the moments ----------------
T_ONE_HOME = tl.at("ten.")
T_TRIES = tl.t_left["joe"] + 1.0               # after "bye, me?", during "Three thousand tries"
TEAM = [(tl.t_one, tl.t_two, "1 helper"), (tl.t_two, tl.t_third, "2 helpers"), (tl.t_third, tl.t_sum, "3 helpers")]
# the tally card: (farmers, verdict, colour, when the row appears)
ROWS = [(1, "never", RED, tl.at("One", 2)), (2, "4 in 10", GREEN, tl.at("Two", 1)), (3, "0 of 3,000", RED, tl.at("three", 3)),
        (4, "24 of 3,000", GREEN, tl.t_sum), (5, "0 of 1,500", RED, tl.at("five:")), (6, "1 of 1,500", GREEN, tl.at("six", 1))]
T_ODD, T_EVEN = tl.at("never"), tl.at("sometimes.")
def card_fn(tt):
    def fn(dr):
        x0, y0, x1, y1 = 120, 330, W - 120, 1150
        dr.rounded_rectangle((x0, y0, x1, y1), 36, fill=(250, 244, 226, 235), outline=INK, width=6)
        dr.text((W / 2, y0 + 70), "all home?", font=MARK(72), fill=INK, anchor="mm")
        for n, verdict, col, t0 in ROWS:
            if tt < t0: continue
            y = y0 + 150 + (n - 1) * 110
            label = "Joe alone" if n == 1 else f"{n} farmers"
            dr.text((x0 + 60, y), label, font=HAND(68), fill=INK, anchor="lm")
            dr.text((x1 - 60, y), verdict, font=HAND(68), fill=col, stroke_width=3, stroke_fill=INK, anchor="rm")
            odd = n % 2 == 1
            if (odd and tt >= T_ODD) or (not odd and tt >= T_EVEN):     # ring the odd / even rows as Joe says it
                dr.rounded_rectangle((x0 + 30, y - 46, x1 - 30, y + 46), 24, outline=col, width=5)
    return fn

# ---------------- video ----------------
ff = subprocess.Popen([ffmpeg(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                       "-r", str(FPS), "-i", "-", *FFMPEG_THREADS, "-c:v", "libx264", "-preset", "medium", "-crf", "19",
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
    who = sp["who"]
    q = lambda v: (int(v * 8)) / 8                              # few cached versions of a fading note
    a = pop(tt, 0.0, 3.4)
    if a: comp(img, layer(("title", q(a)), lambda dr, a=a: text(dr, (70, 120), "Experiment #9", MARK(64), al(WHITE, a), 6, "la")))
    # a name over everyone at the start
    a = pop(tt, 0.4, 3.4)
    if a:
        for name, (x, y, z) in who.items():
            comp(img, layer(("name", name, int(x / 8), int(y / 8), q(a)),
                            lambda dr, n=name, x=x, y=y, a=a: text(dr, (clampx(x), clampy(y - 100)), NAME[n], HAND(70), al(COL[n], a))))
    # what each of them just did, while it's slow (during the rule)
    if sp.get("act") and 3.4 <= tt < tl.t_one:
        last_act, last_act_t = sp["act"], tt
    a = pop(tt, last_act_t - 0.05, last_act_t + 0.55) if last_act and tt < tl.t_one else 0
    if a and last_act["who"] in who:
        n = last_act["who"]; px, py = who[n][:2]; word = ACTION[(n == "joe", last_act["dug"])]
        comp(img, layer(("act", word, n, int(px / 8), int(py / 8), q(a)),
                        lambda dr, w=word, x=px, y=py, a=a, n=n: text(dr, (clampx(x), clampy(y - 110)), w, HAND(66), al(COL[n], a))))
    # which team is on the field
    for t0, t1, s in TEAM:
        a = pop(tt, t0, t1, 0.12)
        if a: comp(img, layer(("team", s, q(a)), lambda dr, s=s, a=a: text(dr, (70, 120), s, MARK(64), al(WHITE, a), 6, "la")))
    # counters
    if 0.6 <= tt < tl.t_sum:
        rnd, spd = tl.round_at(f), speed_text(f)
        comp(img, layer(("cnt", rnd, spd), lambda dr, r=rnd, s=spd: (
            text(dr, (W - 70, 120), f"round {r:,}", HAND(80), WHITE, 6, "ra"),
            text(dr, (W - 70, 205), s, HAND(58), GOLD, 5, "ra") if s else None)))
    # one helper: home
    a = pop(tt, T_ONE_HOME, tl.t_two)
    if a: comp(img, layer(("home1", q(a)), lambda dr, a=a: text(dr, (W / 2, 560), "home!", MARK(130), al(GOLD, a), 8)))
    # two helpers: a "bye!" as each walks off, then the 3,000 tries
    for name, t0 in tl.t_left.items():
        a = pop(tt, t0 - 0.05, t0 + 1.0)
        if a and name in who:
            x, y = who[name][:2]; s = "bye, me?" if name == "joe" else f"bye, {NAME[name]}!"
            tx, ty = clampx(x + (-220 if x > W / 2 else 220), 200), clampy(y + (220 if y < H / 2 else -220))
            comp(img, layer(("bye", name, int(x / 8), int(y / 8), q(a)), lambda dr, s=s, x=x, y=y, tx=tx, ty=ty, a=a, n=name: (
                arrow(dr, (tx, ty - 40 if ty > y else ty + 40), (x, y), al(COL[n], a)),
                text(dr, (tx, ty), s, HAND(76), al(COL[n], a)))))
    a = pop(tt, T_TRIES, tl.t_third)
    if a: comp(img, layer(("tries", q(a)), lambda dr, a=a: (
        text(dr, (W / 2, 520), "all home:", HAND(96), al(WHITE, a)),
        text(dr, (W / 2, 640), "0 of 3,000", MARK(120), al(RED, a), 8))))
    # three helpers: the pig, then everybody home
    a = pop(tt, tl.t_pig - 0.1, tl.t_more)
    if a and "pig" in who:
        x, y = who["pig"][:2]
        comp(img, layer(("pig", int(x / 8), int(y / 8), q(a)), lambda dr, x=x, y=y, a=a: (
            arrow(dr, (clampx(x + 160), clampy(y - 260)), (x + 15, y - 70), al(PINK, a)),
            text(dr, (clampx(x + 180), clampy(y - 310)), "the pig!", HAND(84), al(PINK, a)))))
    a = pop(tt, tl.t_home, tl.t_sum)
    if a: comp(img, layer(("home3", q(a)), lambda dr, a=a: (
        text(dr, (W / 2, 520), "all grass!", HAND(96), al(WHITE, a)),
        text(dr, (W / 2, 640), "everybody home!", MARK(100), al(GOLD, a), 8))))
    # the tally card
    a = pop(tt, tl.t_sum, tl.t_but, 0.25)
    if a:
        L = layer(("card", sum(tt >= r[3] for r in ROWS), tt >= T_ODD, tt >= T_EVEN), card_fn(tt))
        if L is not None:
            y0, y1, x0, x1, rgb, aa, sh = L; comp(img, (y0, y1, x0, x1, rgb, aa * a, sh * a))
    # keeping the pig
    a = pop(tt, tl.at("keeping") - 0.1, tl.duration + 1)
    if a and "pig" in who:
        x, y = who["pig"][:2]
        comp(img, layer(("keep", int(x / 8), int(y / 8), q(a)), lambda dr, x=x, y=y, a=a: (
            text(dr, (clampx(x), clampy(y - 230)), "keeper", MARK(90), al(PINK, a), 7))))
    # captions
    for t0, t1, c in spans:
        if t0 <= tt < t1:
            act = max([i for i, o in enumerate(c) if o["t0"] + LEAD <= tt] or [0])
            comp(img, layer(("cap", c[0]["t0"], act), caption_fn([o["w"] for o in c], act)))
    frame = np.clip(img, 0, 255).astype(np.uint8)
    if thumb is None and tt >= T_TRIES + 0.4: thumb = frame        # the trails walking off, and "0 of 3,000"
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
def pop_snd(t0, amp=0.25):
    L = int(0.08 * SR); t = np.arange(L) / SR; o = int(t0 * SR)
    au[o:o + L] += (np.sin(2 * np.pi * (500 + 900 * t / 0.08) * t) * np.exp(-t * 60) * amp)[:len(au) - o]
# the mess as music: notes climb with the amount of dirt, and fall back as it's undone (per run)
dirt_n = {}
for run, mv in tl.moves.items():
    dn = np.zeros(len(mv) + 1, np.int32); dset = set()
    for i, (k, sq, dug, _, _) in enumerate(mv):
        (dset.add if dug else dset.discard)(sq); dn[i + 1] = len(dset)
    dirt_n[run] = dn
def note_for(n, k): return NOTES[min(19, 3 + n // 14 + 2 * k)]
prev, prev_scene = 0, -1
for f in range(tl.nf):
    si = int(tl.scene[f]); run = tl.scenes[si][0]; mv = tl.moves[run]
    m = int(tl.sched[f])
    if si != prev_scene: prev, prev_scene = m, si
    n = m - prev; tt = f / FPS
    if 0 < n <= 3:                                           # slow: one note per move (each farmer a little higher)
        for i in range(n):
            k, sq, dug = mv[prev + i][:3]; t0 = tt + i / FPS / n
            pluck(t0, note_for(dirt_n[run][prev + i + 1], k) * (1 if dug else 0.75), 0.3)
            if not dug and tl.rate[f] < FPS * 0.5: pop_snd(t0 + 0.12)          # compost / a sprout pops up
    elif n > 3 and rng.random() < 0.8:                       # fast: a sparkle that follows the mess
        pluck(tt + rng.random() / FPS, note_for(min(dirt_n[run][m], 300), 0) * 2, 0.11, 10, 0.5)
    prev = m
def chord(t0, base, amp=0.3, decay=2.5, mults=(1, 1.25, 1.5, 2)):
    for i, mult in enumerate(mults): pluck(t0 + i * 0.07, base * mult, amp, decay, 2.5)
def whoosh(t_end, dur=0.8, amp=0.5):
    L = int(dur * SR); t = np.arange(L) / SR; o = int((t_end - dur) * SR)
    au[o:o + L] += np.convolve(rng.normal(0, 1, L), np.ones(60) / 60, "same") * (t / dur) ** 2 * amp
for t0 in (tl.t_one, tl.t_two, tl.t_third): whoosh(t0, 0.35, 0.3)              # the cuts
chord(T_ONE_HOME, 392.0, 0.3)
for i, t0 in enumerate(tl.t_left.values()): pluck(t0, NOTES[9 - 2 * i], 0.22, 4, 1.5); pluck(t0 + 0.12, NOTES[7 - 2 * i], 0.18, 4, 1.5)   # "bye" falls
chord(T_TRIES, 147.0, 0.3, 2.0, (1, 1.19, 1.5))                                # a minor thud
pluck(tl.t_pig, 523.3, 0.22, 5, 1.2); pop_snd(tl.t_pig + 0.05, 0.3)
chord(tl.t_home, 392.0, 0.34); chord(tl.t_home + 0.35, 523.3, 0.22)
for n, _, _, t0 in ROWS: pluck(t0, NOTES[6 + n] * (1 if n % 2 == 0 else 0.84), 0.16, 5, 1.2)   # a ding per row
t = np.arange(len(au)) / SR
pad = sum(np.sin(2 * np.pi * f_ * t + p) for f_, p in ((98, 0), (147, 1.3), (196, 2.1), (247, 0.7))) / 4
au += pad * np.clip((t - 0.5) / 3, 0, 1) * 0.07
for i, mult in enumerate((1, 1.25, 1.5)): pluck(tl.at("keeping") + 0.6 + i * 0.12, 261.6 * mult, 0.18, 1.6, 3.0)
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
