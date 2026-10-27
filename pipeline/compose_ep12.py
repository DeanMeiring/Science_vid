"""Finish Experiment 12: birthday tags, the exact-maths cards, the live tally, pair lines, handwritten captions and
notes over the Blender frames, the sound design and Joe's voice. Writes renders/ep12_birthdays/ep12_birthdays[_draft].mp4 + .jpg.

Usage: .venv/Scripts/python pipeline/compose_ep12.py [--draft]

Every date on a tag is the seeded run's (pipeline/birthdays.py, herd h of the 23-cow stream); the tally is that
stream's running count. Herd 1's pair (cows 8 and 13, 30 Aug) is labelled as one example, not proof. The cards
show the EXACT chances (47.6% / 50.7%); the tally's result is labelled "simulated", next to "exact".
"""
import argparse, json, subprocess, sys, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FPS, ROOT, ffmpeg, FFMPEG_THREADS, gentle
gentle()
from ep12_timeline import HERD, LEAD, PAIR, Timeline
import birthdays as BD

ap = argparse.ArgumentParser(); ap.add_argument("--draft", action="store_true"); args = ap.parse_args()
tl = Timeline(ROOT / "episodes" / "ep12_birthdays.py")
D = tl.dir; frames_dir = D / ("frames_draft" if args.draft else "frames")
have = sorted(int(p.stem[2:]) for p in frames_dir.glob("f_*.jpg"))
if not have: sys.exit(f"no frames in {frames_dir}")
if not args.draft and len(have) < tl.nf: sys.exit(f"only {len(have)}/{tl.nf} frames rendered")
SCREEN = {int(k): v for k, v in json.loads((frames_dir / "screen.json").read_text()).items()}
OUT = D / f"ep12_birthdays{'_draft' if args.draft else ''}.mp4"
W, H = 1080, 1920
FONTS = str(ROOT / "assets" / "fonts") + "/"
def font(n, s): return ImageFont.truetype(FONTS + n, s)
HAND = lambda s: font("PatrickHand-Regular.ttf", s)
MARK = lambda s: font("PermanentMarker-Regular.ttf", s)
INK, GOLD, WHITE, BLUE, RED, TAG = (32, 28, 30), (255, 214, 64), (255, 255, 255), (120, 190, 255), (255, 90, 80), (250, 206, 60)
EXACT22, EXACT23 = BD.exact(22), BD.exact(23)

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
def pop(tt, t0, t1, rise=0.18):
    """0..1 visibility for a note shown between t0 and t1 (quick fade in/out)."""
    return float(np.clip(min((tt - t0) / rise, (t1 - tt) / rise), 0, 1))
def clampxy(x, y, mx, y0, y1): return min(max(x, mx), W - mx), min(max(y, y0), y1)

# ---------------- the tags: one ear tag over each cow ----------------
def tag(dr, x, y, s, size, a, hot=False, big=False):
    f = HAND(size); w = dr.textlength(s, font=f) + size * 0.6; h = size * 1.15
    fill = (255, 120, 110) if hot else TAG
    dr.line([(x, y + h / 2), (x, y + h / 2 + size * 0.5)], fill=al(INK, a), width=4)
    dr.rounded_rectangle((x - w / 2, y - h / 2, x + w / 2, y + h / 2), size * 0.3, fill=al(fill, a * 0.97),
                         outline=al(WHITE if hot else INK, a), width=6 if hot else 3)
    dr.text((x, y + 1), s, font=f, fill=al(INK, a), anchor="mm")
def date(d): return BD.date(d).upper().lstrip("0")

def tags_fn(sp, herd, a, show_dates, hot, scale):
    def fn(dr):
        days = tl.days[herd - 1]
        order = sorted(range(HERD), key=lambda i: sp["tags"][i][1])            # far ones first, near ones on top
        xy = {i: np.array(sp["tags"][i][:2], float) for i in range(HERD)}
        if len(hot) == 2:                                                      # a pair standing close: push the two tags apart
            a_, b_ = hot; d = xy[b_] - xy[a_]; dist = np.linalg.norm(d) + 1e-9; need = scale * 6
            if dist < need: push = d / dist * (need - dist) / 2; xy[a_] = xy[a_] - push; xy[b_] = xy[b_] + push
        for i in order:
            x, y = xy[i]
            if not (-80 < x < W + 80 and -80 < y < H + 80): continue
            big = i in hot
            size = int(scale * (1.5 if big else 1.0))
            tag(dr, x, y - (20 if big else 0), date(days[i]) if show_dates else "?", size, a, hot=big)
    return fn

# ---------------- captions: phrases from the word timings ----------------
chunks, cur = [], []
for o in tl.words:
    cur.append(o)
    if o["w"][-1] in ".?!" or len(cur) >= 7: chunks.append(cur); cur = []
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

# ---------------- cards, tally, pairs ----------------
def card_fn(n23, a22, a23):
    def fn(dr):
        dr.rounded_rectangle((90, 250, W - 90, 560 if n23 else 420), 28, fill=(250, 244, 226, 235), outline=INK, width=5)
        dr.text((W / 2, 292), "the maths (exact)", font=HAND(50), fill=(110, 100, 90), anchor="mm")
        dr.text((W / 2, 370), f"22 cows: {EXACT22:.1%} have a match", font=HAND(66), fill=al(INK, a22), anchor="mm")
        if n23: dr.text((W / 2, 470), f"23 cows: {EXACT23:.1%}", font=MARK(70), fill=al((200, 60, 40), a23), anchor="mm")
        if n23: dr.text((W / 2, 530), "more likely than not!", font=HAND(48), fill=al(INK, a23), anchor="mm")
    return fn

def tally_fn(h, m, final):
    def fn(dr):
        x0, x1, y = 110, W - 110, 250
        dr.rounded_rectangle((70, y - 40, W - 70, y + 300), 28, fill=(28, 26, 30, 200))
        dr.text((W / 2, y + 10), f"{h:,} herd{'' if h == 1 else 's'} of 23 tested", font=HAND(64), fill=WHITE, anchor="mm")
        dr.text((W / 2, y + 85), f"{m:,} had a match", font=HAND(64), fill=GOLD, anchor="mm")
        p = m / h; by = y + 160
        dr.rounded_rectangle((x0, by, x1, by + 44), 12, fill=(70, 70, 76), outline=WHITE, width=3)
        dr.rounded_rectangle((x0, by, x0 + (x1 - x0) * p, by + 44), 12, fill=GOLD)
        mx = (x0 + x1) / 2; dr.line([(mx, by - 14), (mx, by + 58)], fill=RED, width=6)
        dr.text((mx, by + 80), "half", font=HAND(40), fill=RED, anchor="mm")
        if final:
            dr.text((x0, by + 80), f"simulated {p:.1%}", font=HAND(52), fill=GOLD, anchor="lm")
            dr.text((x1, by + 80), f"exact {EXACT23:.1%}", font=HAND(52), fill=WHITE, anchor="rm")
        else:
            dr.text((x0, by + 80), f"{p:.1%}", font=HAND(52), fill=GOLD, anchor="lm")
    return fn

PAIRS = [(i, j) for i in range(HERD) for j in range(i + 1, HERD)]
assert len(PAIRS) == 253
PAIRS = [PAIRS[k] for k in np.random.default_rng(3).permutation(253)]      # drawn in a mixed order
def lines_fn(sp, n):
    def fn(dr):
        for i, j in PAIRS[:n]:
            (ax, ay, _), (bx, by, _) = sp["mid"][i], sp["mid"][j]
            dr.line([(ax, ay), (bx, by)], fill=(255, 240, 180, 70), width=3)
        for i in range(HERD):
            x, y, _ = sp["mid"][i]; dr.ellipse((x - 9, y - 9, x + 9, y + 9), fill=GOLD, outline=INK, width=3)
        text(dr, (W / 2, 330), f"{n} pairs", MARK(100), GOLD, 8)
        text(dr, (W / 2, 420), "23 × 22 ÷ 2", HAND(60), WHITE, 5)
    return fn

# ---------------- video ----------------
ff = subprocess.Popen([ffmpeg(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                       "-r", str(FPS), "-i", "-", *FFMPEG_THREADS, "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                       "-pix_fmt", "yuv420p", str(D / "_v.mp4")], stdin=subprocess.PIPE)
src_i, base_f, base, thumb = 0, -1, None, None
g8 = lambda v: int(v / 8)
q = lambda v: (int(v * 8)) / 8
for f in range(tl.nf):
    tt = f / FPS
    while src_i + 1 < len(have) and have[src_i + 1] <= f: src_i += 1
    if have[src_i] != base_f:
        base_f = have[src_i]; im = Image.open(frames_dir / f"f_{base_f:05d}.jpg").convert("RGB")
        base = np.array(im if im.size == (W, H) else im.resize((W, H), Image.BICUBIC), np.float32)
    img = base.copy()
    sp = SCREEN.get(base_f) or SCREEN[min(SCREEN, key=lambda k: abs(k - base_f))]
    herd, m = tl.herd_at(f)
    racing = tl.rate[f] > 12
    a = pop(tt, 0.0, 3.4)
    if a: comp(img, layer(("title", q(a)), lambda dr, a=a: text(dr, (70, 120), "Experiment #12", MARK(64), al(WHITE, a), 6, "la")))
    if tt < 3.6:
        a = pop(tt, 0.3, 3.6, 0.25); jx, jy = sp["joe"][:2]
        comp(img, layer(("pj", g8(jx), g8(jy), q(a)), lambda dr, x=jx, y=jy, a=a: plate(dr, x, y, "Joe", BLUE, a)))
    # the tags: "?" until "birthdays", then the herd on screen; hidden once the tally has landed
    a = pop(tt, 0.4, tl.t_land + 0.4, 0.25)
    if a and sp["shot"] != "pull":
        show = tt >= tl.t_tags
        hot = PAIR if (herd == 1 and tl.t_pair <= tt < tl.t_test + 0.3) else ()
        if herd > 1:                                       # any herd with a match shows its pair(s) red too
            hot = tuple(sorted({i for p in BD.matches(tl.days[herd - 1]) for i in p}))
        scale = max(24, min(46, sp["s"] * 0.34))
        comp(img, layer(("tags", herd, show, hot, q(a * (0.6 if racing else 1)), tuple(g8(v) for t in sp["tags"] for v in t[:2]), int(scale)),
                        tags_fn(sp, herd, a * (0.6 if racing else 1), show, hot, scale)))
    # herd 1's pair: one example, not proof
    a = pop(tt, tl.t_pair + 0.2, tl.t_test + 0.3)
    if a:
        (ax, ay, _), (bx, by, _) = sp["mid"][PAIR[0]], sp["mid"][PAIR[1]]
        comp(img, layer(("pair", g8(ax), g8(ay), g8(bx), g8(by), q(a)), lambda dr, a=a, ax=ax, ay=ay, bx=bx, by=by: (
            dr.line([(ax, ay - 20), (bx, by - 20)], fill=al(INK, a), width=13), dr.line([(ax, ay - 20), (bx, by - 20)], fill=al(RED, a), width=7),
            text(dr, (W / 2, 300), "same birthday!", MARK(84), al(GOLD, a), 7),
            text(dr, (W / 2, 390), "(herd #1: just one example)", HAND(54), al(WHITE, a), 5))))
    # the exact cards on "22" and "23:"
    if tl.t_card22 - 0.1 <= tt < tl.t_pair:
        a22 = min(1.0, (tt - tl.t_card22 + 0.1) / 0.2); a23 = float(np.clip((tt - tl.t_card23) / 0.2, 0, 1))
        comp(img, layer(("card", tt >= tl.t_card23, q(a22), q(a23)), card_fn(tt >= tl.t_card23, a22, a23)))
    # the tally
    if tl.t_test <= tt < tl.t_lines - 0.2:
        comp(img, layer(("tally", herd, m, tt >= tl.t_rate), tally_fn(herd, m, tt >= tl.t_rate)))
    # the pairs
    n = int(tl.lines[f])
    if n:
        comp(img, layer(("lines", n, tuple(g8(v) for t in sp["mid"] for v in t[:2])), lines_fn(sp, n)))
    # cakes
    a = pop(tt, tl.t_cake + 0.4, tl.t_pull + 0.5)
    if a:
        px, py = sp["pile"][:2]
        comp(img, layer(("cakes", g8(px), g8(py), q(a)), lambda dr, a=a, x=px, y=py: (
            text(dr, (W / 2, 330), f"{tl.hits:,} cakes", MARK(96), al(GOLD, a), 8),
            text(dr, (W / 2, 420), "one per matching herd", HAND(56), al(WHITE, a), 5),
            arrow(dr, (W / 2 + 80, 470), (x, y - 40), al(WHITE, a), 6))))
    # the whole farm
    if "fields" in sp:
        fs = sp["fields"]
        farm = np.array([fs[str(k)][:2] for k in range(1, 11)]).mean(0)
        for k, (t0, xy, title, sub_) in enumerate((
                (tl.t_pull + 1.2, farm, "Experiments #1-#10", "the farm so far"),
                (tl.t_pull + 0.8, fs["11"][:2], "Experiment #11", "crop codes"),
                (tl.t_pull + 1.6, fs["12"][:2], "Experiment #12", "today: birthday cows"))):
            a = pop(tt, t0, tl.duration + 1, 0.25)
            if not a: continue
            fx, fy = xy; today = k == 2
            x, y = clampxy(fx + (150 if today else 0), fy + (-150 if today else 40), 230, 290, 1530)
            comp(img, layer(("lab", k, g8(x), g8(y), g8(fx), g8(fy), q(a)), lambda dr, x=x, y=y, fx=fx, fy=fy, a=a, title=title, sub_=sub_, today=today: (
                arrow(dr, (x - 60, y + 20), (fx + 10, fy + 70), al(WHITE, a), 5) if today else None,
                text(dr, (x, y - 62), title, MARK(58 if today else 50), al(GOLD if today else WHITE, a), 6),
                text(dr, (x, y - 8), sub_, HAND(52), al(WHITE, a), 5))))
    # captions
    for t0, t1, c in spans:
        if t0 <= tt < t1:
            act = max([i for i, o in enumerate(c) if o["t0"] + LEAD <= tt] or [0])
            comp(img, layer(("cap", c[0]["t0"], act), caption_fn([o["w"] for o in c], act)))
    frame = np.clip(img, 0, 255).astype(np.uint8)
    if thumb is None and tt >= tl.t_pair + 0.8: thumb = frame        # the pair, lit up
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
def tap(t0, amp=0.25):
    L = int(0.05 * SR); t = np.arange(L) / SR; o = int(t0 * SR)
    au[o:o + L] += (rng.normal(0, 1, L) * np.exp(-t * 90) * amp)[:len(au) - o]
def chord(t0, base, amp=0.3, decay=2.5, mults=(1, 1.25, 1.5, 2)):
    for i, mult in enumerate(mults): pluck(t0 + i * 0.07, base * mult, amp, decay, 2.5)
def whoosh(t_end, dur=0.8, amp=0.5):
    L = int(dur * SR); t = np.arange(L) / SR; o = int((t_end - dur) * SR)
    au[o:o + L] += np.convolve(rng.normal(0, 1, L), np.ones(60) / 60, "same") * (t / dur) ** 2 * amp
for i in range(HERD): tap(tl.t_tags + i * 0.02, 0.12)                       # the tags flip to dates
prev = 1
for f in range(tl.nf):
    h = int(tl.sched[f]); n = h - prev; tt = f / FPS
    if 0 < n <= 2:                                                           # a new herd: a clack, a ding if it matched
        for k in range(n):
            tap(tt, 0.3)
            if tl.running[prev + k] > tl.running[prev + k - 1]: pluck(tt, NOTES[10], 0.18, 8, 0.6)
    elif n > 2 and rng.random() < 0.85:                                      # racing: a patter
        tap(tt + rng.random() / FPS, 0.1); pluck(tt + rng.random() / FPS, NOTES[8 + int(rng.integers(0, 6))] * 2, 0.05, 12, 0.4)
    prev = h
chord(tl.t_card23, 392.0, 0.26); pluck(tl.t_pair + 0.2, NOTES[12], 0.3, 4, 1.5)
chord(tl.t_land, 523.3, 0.28); chord(tl.t_rate, 392.0, 0.2, 3.0)
for k in range(0, 253, 11): pluck(tl.t_lines + (tl.t_253 - tl.t_lines) * (k / 253) ** (1 / 1.5), NOTES[5 + k % 10] * 2, 0.05, 10, 0.4)
for k in range(30): tap(tl.t_cake + (tl.t_flour - tl.t_cake) * (k + 0.5) / 30 / 1.5, 0.12)   # cakes land
pluck(tl.t_flour + 0.15, 98.0, 0.3, 3, 1.5)
whoosh(tl.t_pull + 1.0, 1.0, 0.35)
for i, t0 in enumerate((tl.t_pull + 0.8, tl.t_pull + 1.2, tl.t_pull + 1.6)): pluck(t0, 523.3 * (1 + 0.25 * i), 0.16, 5, 1.2)
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
