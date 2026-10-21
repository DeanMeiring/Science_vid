"""Prototype stills: 9 experiments, each in a different look, as vertical Short frames."""
import math, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

TW, TH = 540, 960
from pathlib import Path
FONTS = str(Path(__file__).resolve().parent.parent / "assets" / "fonts") + "/"
rng = np.random.default_rng(7)

def font(n, s): return ImageFont.truetype(FONTS + n, s)

def hexc(h): return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], np.float32)

def grid_to_img(idx, pal, cell, bg, gap=0, size=(TW, 700)):
    """Upscale an index grid with a palette, centred on a (w,h) canvas."""
    h, w = idx.shape
    img = np.array(pal, np.float32)[idx]
    img = np.repeat(np.repeat(img, cell, 0), cell, 1)
    if gap:
        m = np.ones((h * cell, w * cell), bool)
        for k in range(gap):
            m[k::cell, :] = False; m[:, k::cell] = False
        img = np.where(m[..., None], img, img * 0.55 + hexc(bg) * 0.45)
    canvas = np.zeros((size[1], size[0], 3), np.float32) + hexc(bg)
    H2, W2 = img.shape[:2]
    y0 = (size[1] - H2) // 2; x0 = (size[0] - W2) // 2
    ys, xs = max(0, -y0), max(0, -x0)
    canvas[max(0, y0):max(0, y0) + min(H2, size[1]), max(0, x0):max(0, x0) + min(W2, size[0])] = \
        img[ys:ys + size[1], xs:xs + size[0]]
    return canvas

def tile(board, bg, title, sub, style, fg=(255, 255, 255), accent=(255, 214, 64), fontname="Anton.ttf"):
    im = Image.new("RGB", (TW, TH), tuple(int(v) for v in hexc(bg)))
    b = Image.fromarray(np.clip(board, 0, 255).astype(np.uint8))
    im.paste(b, (0, 150))
    d = ImageDraw.Draw(im)
    f1 = font(fontname, 46); f2 = font("Inter-Bold.ttf", 24); f3 = font("Inter-Bold.ttf", 20)
    def c(y, t, f, col, stroke=0):
        w = d.textlength(t, font=f); d.text(((TW - w) / 2, y), t, font=f, fill=col, stroke_width=stroke, stroke_fill=(0, 0, 0))
    light = sum(hexc(bg)) > 300
    c(40, title, f1, fg, 0 if light else 2)
    c(100, sub, f2, accent, 0 if light else 1)
    d.rounded_rectangle((20, TH - 70, TW - 20, TH - 24), 18, fill=(0, 0, 0) if sum(hexc(bg)) > 300 else (255, 255, 255))
    c(TH - 62, "LOOK: " + style, f3, (255, 255, 255) if sum(hexc(bg)) > 300 else (0, 0, 0))
    return im

# ---- 1. turmite LLRR (symmetric) - pastel paper ----
def turmite(rule, steps, n=400):
    g = np.zeros((n, n), np.uint8); x = y = n // 2; d = 0; k = len(rule)
    DX = [0, 1, 0, -1]; DY = [-1, 0, 1, 0]
    turns = [1 if ch == "R" else -1 for ch in rule]
    for _ in range(steps):
        c = g[y, x]; d = (d + turns[c]) % 4; g[y, x] = (c + 1) % k; x += DX[d]; y += DY[d]
        if not (1 < x < n - 2 and 1 < y < n - 2): break
    return g

def crop(g, pad=3):
    ys, xs = np.nonzero(g)
    if len(xs) == 0: return g[:5, :5]
    return g[max(0, ys.min() - pad):ys.max() + pad + 1, max(0, xs.min() - pad):xs.max() + pad + 1]

tiles = []
g = crop(turmite("LLRR", 140000))
pal = ["#f6efe2", "#f4a6a6", "#9ad0c2", "#5b6c9e"]
cell = max(1, min(TW // g.shape[1], 700 // g.shape[0]))
tiles.append(tile(grid_to_img(g, [hexc(p) for p in pal], cell, "#f6efe2"), "#f6efe2",
                  "4 COLOURS, 1 ANT", "rule LLRR draws a perfect mirror", "pastel paper",
                  fg=(40, 40, 60), accent=(214, 90, 110)))

# ---- 2. turmite LRRRRRLLR (fills a square) - rainbow neon ----
g = crop(turmite("LRRRRRLLR", 250000))
pal = ["#07070d"] + [tuple(int(255 * v) for v in __import__("colorsys").hsv_to_rgb(0.5 + i / 16, 0.75, 0.35 + 0.65 * i / 7)) for i in range(8)]
pal = [hexc(pal[0])] + [np.array(p, np.float32) for p in pal[1:]]
cell = max(1, min(TW // g.shape[1], 700 // g.shape[0]))
tiles.append(tile(grid_to_img(g, pal, cell, "#07070d"), "#07070d",
                  "9 COLOURS", "this ant builds a square", "rainbow neon"))

# ---- 3. Game of Life, Gosper glider gun - terminal green ----
gun = ["........................O...........", "......................O.O...........",
       "............OO......OO............OO", "...........O...O....OO............OO",
       "OO........O.....O...OO..............", "OO........O...O.OO....O.O...........",
       "..........O.....O.......O...........", "...........O...O....................",
       "............OO......................"]
L = np.zeros((90, 70), np.uint8)
for r, row in enumerate(gun):
    for cc, ch in enumerate(row):
        if ch == "O": L[5 + cc, 60 - r] = 1   # rotated so gliders fly down
age = np.zeros_like(L, np.float32)
for _ in range(240):
    nb = sum(np.roll(np.roll(L, i, 0), j, 1) for i in (-1, 0, 1) for j in (-1, 0, 1) if (i, j) != (0, 0))
    new = ((nb == 3) | ((L == 1) & (nb == 2))).astype(np.uint8)
    new[-2:, :] = 0; new[:, :2] = 0
    age = np.where(new == 1, 1.0, age * 0.9); L = new
cell = 7
lvl = np.clip((age * 5).astype(int), 0, 5)
pal = [hexc("#03140a"), hexc("#06301a"), hexc("#0b5a2e"), hexc("#14894a"), hexc("#2fd27a"), hexc("#b6ffcf")]
tiles.append(tile(grid_to_img(lvl, pal, cell, "#03140a", gap=1), "#03140a",
                  "THE GLIDER GUN", "it makes spaceships forever", "terminal green",
                  fg=(182, 255, 207), accent=(47, 210, 122), fontname="Inter-Black.ttf"))

# ---- 4. Abelian sandpile - mandala ----
n = 181; S = np.zeros((n, n), np.int64); S[n // 2, n // 2] = 30000
while True:
    t = S >= 4
    if not t.any(): break
    q = S // 4
    S = S % 4 + np.roll(q, 1, 0) + np.roll(q, -1, 0) + np.roll(q, 1, 1) + np.roll(q, -1, 1)
pal = [hexc("#1b0f2e"), hexc("#3a86ff"), hexc("#ffbe0b"), hexc("#ff006e")]
g = crop(S, 2)
cell = max(1, min(TW // g.shape[1], 700 // g.shape[0]))
tiles.append(tile(grid_to_img(g, pal, cell, "#1b0f2e"), "#1b0f2e",
                  "30,000 GRAINS", "drop sand on one square", "sand mandala"))

# ---- 5. Gray-Scott reaction diffusion - coral ----
h, w = 175, 135
U = np.ones((h, w)); V = np.zeros((h, w))
for _ in range(14):
    y0, x0 = rng.integers(10, h - 10), rng.integers(10, w - 10)
    U[y0 - 3:y0 + 3, x0 - 3:x0 + 3] = 0.5; V[y0 - 3:y0 + 3, x0 - 3:x0 + 3] = 0.25
F, K = 0.0545, 0.062
def lap(Z): return np.roll(Z, 1, 0) + np.roll(Z, -1, 0) + np.roll(Z, 1, 1) + np.roll(Z, -1, 1) - 4 * Z
for _ in range(9000):
    uvv = U * V * V
    U += 0.16 * lap(U) - uvv + F * (1 - U)
    V += 0.08 * lap(V) + uvv - (F + K) * V
v = np.clip((V - V.min()) / (V.max() - V.min() + 1e-9), 0, 1)
a, b = hexc("#08243a"), hexc("#ff7a59")
img = a * (1 - v[..., None]) + b * v[..., None] + hexc("#ffe0a0") * (v[..., None] ** 4)
img = np.array(Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).resize((TW, 700), Image.BICUBIC), np.float32)
tiles.append(tile(img, "#08243a", "2 CHEMICALS", "...grow into coral", "ocean coral"))

# ---- 6. Physarum slime mould - gold ----
h, w = 350, 270; T = np.zeros((h, w), np.float32)
na = 25000
pa = rng.uniform(0, 2 * np.pi, na); rr_ = rng.uniform(0, 60, na); px = w / 2 + rr_ * np.cos(pa); py = h / 2 + rr_ * np.sin(pa)
SA, RA, SO, SS = 0.4, 0.3, 9.0, 1.0
def sense(a):
    sx = (px + SO * np.cos(a)).astype(int) % w; sy = (py + SO * np.sin(a)).astype(int) % h
    return T[sy, sx]
for _ in range(700):
    l, c_, r = sense(pa - SA), sense(pa), sense(pa + SA)
    turn = np.where((c_ >= l) & (c_ >= r), 0, np.where(l > r, -RA, RA))
    turn = np.where((c_ < l) & (c_ < r), rng.choice([-RA, RA], na), turn)
    pa += turn
    px = (px + SS * np.cos(pa)) % w; py = (py + SS * np.sin(pa)) % h
    np.add.at(T, (py.astype(int), px.astype(int)), 0.3)
    T = (T + np.roll(T, 1, 0) + np.roll(T, -1, 0) + np.roll(T, 1, 1) + np.roll(T, -1, 1)) / 5 * 0.85
v = np.clip(T / np.percentile(T, 99.5), 0, 1) ** 0.7
img = hexc("#0a0705") * (1 - v[..., None]) + hexc("#ffb703") * v[..., None] + hexc("#fff3c4") * (v[..., None] ** 3)
img = np.array(Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).resize((TW, 700), Image.BICUBIC), np.float32)
tiles.append(tile(img, "#0a0705", "25,000 BLOBS", "slime mould builds a network", "gold on black"))

# ---- 7. double pendulum chaos - rainbow fan ----
import colorsys
M = 120; th1 = np.full(M, 2.6) + np.linspace(0, 1e-3, M); th2 = np.full(M, 2.6); w1 = np.zeros(M); w2 = np.zeros(M)
gg, dt = 9.81, 0.002
def acc(t1, t2, a1, a2):
    dl = t1 - t2; den = 3 - np.cos(2 * dl)
    A1 = (-gg * 3 * np.sin(t1) - gg * np.sin(t1 - 2 * t2) - 2 * np.sin(dl) * (a2 ** 2 + a1 ** 2 * np.cos(dl))) / den
    A2 = (2 * np.sin(dl) * (2 * a1 ** 2 + 2 * gg * np.cos(t1) + a2 ** 2 * np.cos(dl))) / den
    return A1, A2
for _ in range(int(7.5 / dt)):
    A1, A2 = acc(th1, th2, w1, w2); w1 += A1 * dt; w2 += A2 * dt; th1 += w1 * dt; th2 += w2 * dt
im = Image.new("RGB", (TW * 2, 1400), (10, 8, 24)); dr = ImageDraw.Draw(im)
cx, cy, Lp = TW, 560, 300
for i in range(M):
    col = tuple(int(255 * v) for v in colorsys.hsv_to_rgb(i / M * 0.85, 0.75, 1))
    x1 = cx + Lp * np.sin(th1[i]); y1 = cy + Lp * np.cos(th1[i])
    x2 = x1 + Lp * np.sin(th2[i]); y2 = y1 + Lp * np.cos(th2[i])
    dr.line([(cx, cy), (x1, y1), (x2, y2)], fill=col, width=4)
    dr.ellipse((x2 - 9, y2 - 9, x2 + 9, y2 + 9), fill=col)
dr.ellipse((cx - 12, cy - 12, cx + 12, cy + 12), fill=(255, 255, 255))
img = np.array(im.resize((TW, 700), Image.LANCZOS), np.float32)
tiles.append(tile(img, "#0a0818", "120 PENDULUMS", "started 0.001° apart", "rainbow fan"))

# ---- 8. Lorenz attractor - blueprint ----
p = np.array([0.1, 0, 0]); pts = []
for _ in range(60000):
    x, y, z = p; p = p + 0.004 * np.array([10 * (y - x), x * (28 - z) - y, x * y - 8 / 3 * z]); pts.append(p.copy())
pts = np.array(pts)
im = Image.new("RGB", (TW * 2, 1400), (16, 52, 110)); dr = ImageDraw.Draw(im)
for gx in range(0, TW * 2, 40): dr.line([(gx, 0), (gx, 1400)], fill=(30, 72, 140), width=1)
for gy in range(0, 1400, 40): dr.line([(0, gy), (TW * 2, gy)], fill=(30, 72, 140), width=1)
X = TW + pts[:, 0] * 22; Y = 1250 - pts[:, 2] * 22
dr.line(list(zip(X, Y)), fill=(225, 240, 255), width=2)
img = np.array(im.resize((TW, 700), Image.LANCZOS), np.float32)
tiles.append(tile(img, "#10346e", "THE BUTTERFLY", "3 equations that never repeat", "blueprint",
                  fontname="SourceSerif-Bold.ttf"))

# ---- 9. Rule 30 - chalkboard ----
wR, hR = 271, 135
R = np.zeros((hR, wR), np.uint8); R[0, wR // 2] = 1
for i in range(1, hR):
    l, c_, r = np.roll(R[i - 1], 1), R[i - 1], np.roll(R[i - 1], -1)
    R[i] = (30 >> (l * 4 + c_ * 2 + r)) & 1
R = R[:, wR // 2 - 134:wR // 2 + 135]
img = grid_to_img(R, [hexc("#1f2b24"), hexc("#e8efe6")], 2, "#1f2b24")
tiles.append(tile(img, "#1f2b24", "RULE 30", "1 line of rules, pure chaos", "chalkboard",
                  fg=(232, 239, 230), accent=(255, 200, 120), fontname="SourceSerif-Bold.ttf"))

sheet = Image.new("RGB", (TW * 3 + 40, TH * 3 + 40), (255, 255, 255))
for i, t in enumerate(tiles):
    sheet.paste(t, (10 + (i % 3) * (TW + 10), 10 + (i // 3) * (TH + 10)))
sheet.save(sys.argv[1] if len(sys.argv) > 1 else "experiment_ideas.jpg", quality=88)
print("saved")
