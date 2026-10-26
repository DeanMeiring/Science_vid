"""Finish Experiment 5: handwritten captions and notes over the Blender frames, the mirror flash,
the sound design, and Joe's voice (the one-take narration). Writes
renders/ep05_crops/ep05_crops[_draft].mp4 + .jpg.

Usage: .venv/Scripts/python pipeline/compose_ep05.py [--draft]

Look (Dean picked style C): handwritten captions and notes; on each mirror moment a glowing line
down the middle (with a gap around Joe) and "MIRROR!"; while racing (every frame a mirror moment)
the line glows steadily. A little rule card while Joe explains the four crops.
"""
import argparse, json, subprocess, sys, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FPS, ROOT, ffmpeg, FFMPEG_THREADS, gentle
gentle()
from ep05_timeline import LEAD, Timeline
import farm_overview as FO

ap = argparse.ArgumentParser(); ap.add_argument("--draft", action="store_true"); args = ap.parse_args()
tl = Timeline(ROOT / "episodes" / "ep05_crops.py")
D = tl.dir; frames_dir = D / ("frames_draft" if args.draft else "frames")
have = sorted(int(p.stem[2:]) for p in frames_dir.glob("f_*.jpg"))
if not have: sys.exit(f"no frames in {frames_dir}")
if not args.draft and len(have) < tl.nf: sys.exit(f"only {len(have)}/{tl.nf} frames rendered")
SCREEN = {int(k): v for k, v in json.loads((frames_dir / "screen.json").read_text()).items()}
OUT = D / f"ep05_crops{'_draft' if args.draft else ''}.mp4"
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
def al(col, a): return col + (int(255 * a),)

def arrow(dr, a, b, fill=WHITE, w=7):
    """A hand-drawn-ish arrow from a to b (slight curve), outlined so it reads on any colour."""
    a, b = np.array(a, float), np.array(b, float); mid = (a + b) / 2 + np.array([-(b - a)[1], (b - a)[0]]) * 0.15
    pts = [tuple((1 - u) ** 2 * a + 2 * (1 - u) * u * mid + u ** 2 * b) for u in np.linspace(0, 1, 16)]
    d = b - pts[-3]; d /= np.linalg.norm(d) + 1e-9; n = np.array([-d[1], d[0]])
    head = [tuple(b - d * 30 + n * 16), tuple(b), tuple(b - d * 30 - n * 16)]
    for col, ww in ((INK, w + 6), (fill, w)):
        dr.line(pts, fill=col, width=ww, joint="curve"); dr.line(head, fill=col, width=ww, joint="curve")
def pop(tt, t0, t1, rise=0.18): return float(np.clip(min((tt - t0) / rise, (t1 - tt) / rise), 0, 1))

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

# ---------------- the rule card: four crops, lit up as Joe names them ----------------
RULES = [("grass", (104, 170, 62), "left", tl.at("grass,")), ("dirt", (120, 80, 48), "left", tl.at("dirt,")),
         ("wheat", (222, 178, 70), "right", tl.at("wheat,")), ("pumpkins", (236, 120, 30), "right", tl.at("pumpkins,"))]
def rules_fn(active, a):
    def fn(dr):
        y = 230
        for i, (name, col, turn, _) in enumerate(RULES):
            if i > active: break
            on = i == active
            dr.rounded_rectangle((70, y, 130, y + 60), 10, fill=al(col, a), outline=al(INK, a), width=4)
            text(dr, (155, y + 30), name, HAND(66), al(GOLD if on else WHITE, a), 5, "lm")
            text(dr, (470, y + 30), "turn " + turn, HAND(66), al(GOLD if on else WHITE, a), 5, "lm")
            y += 82
    return fn

def mirror_line(img, sp, strength):
    """Glow along the mirror line, leaving a gap where Joe stands."""
    (ax, ay), (bx, by) = sp["axis"]; jx, jy = sp["joe"]
    m = Image.new("L", (W, H), 0); dr = ImageDraw.Draw(m); dr.line([(ax, ay), (bx, by)], fill=255, width=24)
    dr.ellipse([jx - 55, jy - 70, jx + 55, jy + 70], fill=0)
    glow = np.array(m.filter(ImageFilter.GaussianBlur(14.0)), np.float32) / 255 * 0.8
    m2 = Image.new("L", (W, H), 0); d2 = ImageDraw.Draw(m2); d2.line([(ax, ay), (bx, by)], fill=255, width=6)
    d2.ellipse([jx - 55, jy - 70, jx + 55, jy + 70], fill=0)
    a = np.maximum(glow, np.array(m2, np.float32) / 255)[..., None] * strength
    img *= (1 - a); img += np.array([255, 250, 225], np.float32) * a

def speed_text(f):
    s = tl.speed(f)
    return f"SPEED ×{int(round(s, -1 if s < 1000 else -2)):,}" if s > 4 else ""

# ---------------- the whole farm at the end: a label above each experiment (see render_ep05) ----------------
T_PULL = tl.t_next - 0.3
LABELS = {5: ("Experiment #5", "today: a crop circle!"), 4: ("Experiment #4", "Joe & Daisy: spotless!"),
          **{k: (FO.FIELDS[k]["title"], FO.FIELDS[k]["sub"]) for k in (1, 2, 3)}}
NUDGE = {5: (-160, -40), 4: (200, -40)}     # #4 and #5 sit close together: their labels move apart, with an arrow each
LABEL_T = {5: T_PULL + 0.5, 4: T_PULL + 1.0, 1: T_PULL + 1.3, 2: T_PULL + 1.9, 3: T_PULL + 2.5}

# ---------------- video ----------------
ff = subprocess.Popen([ffmpeg(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                       "-r", str(FPS), "-i", "-", *FFMPEG_THREADS, "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                       "-pix_fmt", "yuv420p", str(D / "_v.mp4")], stdin=subprocess.PIPE)
src_i, base_f, base, thumb = 0, -1, None, None
LAND_T = [t for t, _ in tl.landings]
for f in range(tl.nf):
    tt = f / FPS
    while src_i + 1 < len(have) and have[src_i + 1] <= f: src_i += 1
    if have[src_i] != base_f:
        base_f = have[src_i]; im = Image.open(frames_dir / f"f_{base_f:05d}.jpg").convert("RGB")
        base = np.array(im if im.size == (W, H) else im.resize((W, H), Image.BICUBIC), np.float32)
    img = base.copy()
    sp = SCREEN.get(base_f) or SCREEN[min(SCREEN, key=lambda k: abs(k - base_f))]
    q = lambda v: (int(v * 8)) / 8
    # the mirror flash: a burst on each landing, a steady glow while racing, fading after "circle!"
    burst = max([max(0.0, 1 - (tt - t0) / 1.2) for t0 in LAND_T if t0 <= tt] + [0.0])
    steady = 0.5 if (tl.t_race <= tt < tl.t_race_end) else 0.4 * (1 - min(1, max(0, (tt - tl.t_circle) / 1.5))) if tt >= tl.t_race_end else 0
    strength = max(burst if sp["mirror"] else 0, steady if sp["mirror"] else 0)
    if strength > 0.02: mirror_line(img, sp, strength)
    a = pop(tt, 0.0, 3.0)
    if a: comp(img, layer(("title", q(a)), lambda dr, a=a: text(dr, (70, 120), "Experiment #5", MARK(64), al(WHITE, a), 6, "la")))
    a = pop(tt, 0.4, 2.4)
    if a:
        jx, jy = sp["joe"]; key = ("me", int(jx / 8), int(jy / 8), q(a))
        comp(img, layer(key, lambda dr, jx=jx, jy=jy, a=a: (
            arrow(dr, (jx + 170, jy + 250), (jx + 30, jy + 60), al(WHITE, a)),
            text(dr, (jx + 200, jy + 300), "that's me!", HAND(76), al(WHITE, a)))))
    # the rule card
    act = max([i for i, r in enumerate(RULES) if r[3] - 0.1 <= tt] or [-1])
    a = pop(tt, RULES[0][3] - 0.2, tl.t_rules_end + 1.4, 0.3)
    if act >= 0 and a: comp(img, layer(("rules", act, q(a)), rules_fn(act, a)))
    # counters
    if 0.5 <= tt < T_PULL:
        st, spd = sp["step"] if f == base_f else int(tl.shown[f]), speed_text(f)
        mc = tl.mirror_count(st) if tt >= tl.t_reveal - 0.05 else None
        comp(img, layer(("cnt", st, spd, mc), lambda dr, st=st, spd=spd, mc=mc: (
            text(dr, (W - 70, 120), f"step {st:,}", HAND(80), WHITE, 6, "ra"),
            text(dr, (W - 70, 200), spd, HAND(56), GOLD, 5, "ra") if spd else None,
            text(dr, (W - 70, 270 if spd else 205), f"mirrors: {mc:,}", HAND(64), GOLD, 5, "ra") if mc is not None else None)))
    # "MIRROR!" on each landing
    a = max([pop(tt, t0, t0 + 1.4) for t0 in LAND_T] + [0.0])
    if a and sp["mirror"]:
        top = min(sp["axis"], key=lambda p: p[1]); big = tt >= tl.t_race_end
        comp(img, layer(("mir", int(top[0] / 8), int(top[1] / 8), q(a), big), lambda dr, top=top, a=a, big=big:
                        text(dr, (top[0], max(380, top[1] - 90)), "MIRROR!", MARK(130 if big else 104), al(GOLD, a), 8)))
    # the whole farm
    if "fields" in sp:
        for k, t0 in LABEL_T.items():
            a = pop(tt, t0, tl.duration + 1, 0.25)
            fx, fy = sp["fields"][str(k)]
            if not a: continue
            dx, dy = NUDGE.get(k, (0, 0))
            x = min(max(fx + dx, 215), W - 215); y = min(max(fy + dy, 290), 1450)
            title, sub_ = LABELS[k]; today = k == 5
            comp(img, layer(("lab", k, int(x / 6), int(y / 6), int(fx / 6), int(fy / 6), q(a)), lambda dr, x=x, y=y, fx=fx, fy=fy, a=a,
                            title=title, sub_=sub_, today=today, k=k: (
                arrow(dr, (x + (90 if fx > x else -90), y + 30), (fx, fy + 40), al(WHITE, a), 5) if k in NUDGE else None,
                text(dr, (x, y - 62), title, MARK(58 if today else 50), al(GOLD if today else WHITE, a), 6),
                text(dr, (x, y - 8), sub_, HAND(52), al(WHITE, a), 5))))
    # captions
    for t0, t1, c in spans:
        if t0 <= tt < t1:
            act_w = max([i for i, o in enumerate(c) if o["t0"] + LEAD <= tt] or [0])
            comp(img, layer(("cap", c[0]["t0"], act_w), caption_fn([o["w"] for o in c], act_w)))
    frame = np.clip(img, 0, 255).astype(np.uint8)
    if thumb is None and tt >= tl.t_10k + 0.4: thumb = frame             # "MIRROR!" at step 10,012
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
# one note per step while slow: the crop he leaves behind sets the note (grass low ... pumpkins high)
crop_after = np.zeros(len(tl.hist), np.int8); gg = {}
for i in range(len(tl.hist) - 1):
    p = tuple(tl.hist[i][:2]); gg[p] = (gg.get(p, 0) + 1) % 4; crop_after[i + 1] = gg[p]
prev = 0
for f in range(tl.nf):
    st = int(tl.shown[f]); n = st - prev; tt = f / FPS
    if 0 < n <= 3:
        for i in range(n): pluck(tt + i / FPS / n, NOTES[5 + 2 * crop_after[prev + i + 1]], 0.28)
    elif n > 3 and rng.random() < 0.8:
        pluck(tt + rng.random() / FPS, NOTES[10 + int(rng.integers(0, 8))], 0.1, 10, 0.5)
    prev = st
def chord(t0, base, amp=0.3, decay=2.5):
    for i, mult in enumerate((1, 1.25, 1.5, 2)): pluck(t0 + i * 0.06, base * mult, amp, decay, 2.5)
for i, (t0, _) in enumerate(tl.landings): chord(t0, 392.0 * (1.0, 1.125, 1.25, 1.5)[i], 0.3 + 0.03 * i)
t = np.arange(len(au)) / SR
shimmer = np.sin(2 * np.pi * 784 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 7 * t))     # a bright shimmer while racing
au += shimmer * np.clip(np.minimum((t - tl.t_race) / 0.5, (tl.t_race_end - t) / 0.3), 0, 1) * 0.05
pad = sum(np.sin(2 * np.pi * f_ * t + p) for f_, p in ((98, 0), (147, 1.3), (196, 2.1), (247, 0.7))) / 4
au += pad * np.clip((t - 0.5) / 3, 0, 1) * 0.07
for i, mult in enumerate((1, 1.25, 1.5, 2)): pluck(tl.t_circle + i * 0.1, 523.3 * mult, 0.2, 1.8, 3.0)
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
