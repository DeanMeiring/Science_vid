"""Shared bits for the pipeline: paths, .env, loading an episode, and the timeline.

Plain numpy only, so Blender's own Python can import it too.
"""
import importlib.util, json, math, os
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
FPS = 30
N = 700                                   # simulation grid (the ant never gets near the edge by step ~17k)
DX = [0, 1, 0, -1]; DY = [-1, 0, 1, 0]    # up, right, down, left (grid y points down)

def load_env():
    p = ROOT / ".env"
    if p.exists():
        for line in p.read_text().splitlines():
            k, _, v = line.partition("=")
            if k.strip() and v.strip() and not k.strip().startswith("#"):
                os.environ.setdefault(k.strip(), v.strip())

def load_episode(path):
    spec = importlib.util.spec_from_file_location("episode", str(path))
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    return mod

def schedule(lines, nf):
    """Step reached at every frame: each line's mode decides how the sim moves while it's spoken."""
    sched = np.zeros(nf, np.int64)
    prev = 0
    for i, ln in enumerate(lines):
        f0 = int(ln["t0"] * FPS); f1 = int(ln["t1"] * FPS) if i < len(lines) - 1 else nf
        s0, s1 = prev, ln["target"]
        for f in range(f0, min(f1, nf)):
            u = (f - f0) / max(1, f1 - f0 - 1)
            m = ln["mode"]
            if m in ("hold", "trip"): v = s0
            elif m == "single": v = s0 + min(s1 - s0, int(u * (s1 - s0) + 0.999))
            elif m == "ramp": v = s0 + (s1 - s0) * (math.expm1(u * 3) / math.expm1(3))
            elif m == "land": v = s0 + (s1 - s0) * (1 - (1 - u) ** 3)      # brakes into the moment
            elif m == "easein": v = s0 + (s1 - s0) * u ** 2.2
            else: v = s0 + (s1 - s0) * u
            sched[f] = int(round(v))
        prev = s1
    sched[:int(lines[0]["t0"] * FPS)] = 0
    return np.maximum.accumulate(sched)

def simulate(total, rule="RL"):
    """Run the rule for `total` steps. rule: one letter per colour, the turn on it ("RL" is
    Langton's ant: right on white/grass, left on black/dirt); each square the walker leaves
    moves on to the next colour. Returns moves (cell changed at each step) and hist
    (x, y, dir, colour under the walker) after each step."""
    k = len(rule); turn = [1 if c == "R" else -1 for c in rule]
    grid = [[0] * N for _ in range(N)]          # plain lists: much faster than numpy per cell
    x = y = N // 2; d = 0
    moves = np.zeros((total, 2), np.int64)
    hist = np.zeros((total + 1, 4), np.int64); hist[0] = (x, y, d, 0)
    mv = moves.tolist(); hs = hist.tolist()
    for s in range(total):
        row = grid[y]; c = row[x]
        d = (d + turn[c]) % 4
        row[x] = (c + 1) % k; mv[s] = (x, y)
        x += DX[d]; y += DY[d]
        if not (0 < x < N - 1 and 0 < y < N - 1):
            raise RuntimeError(f"walked off the {N}x{N} grid at step {s}; make N bigger")
        hs[s + 1] = (x, y, d, grid[y][x])
    return np.array(mv, np.int64).reshape(-1, 2), np.array(hs, np.int64)

def load_timeline(episode_dir):
    """timing.json -> (lines, duration, frame count, step schedule)."""
    tm = json.loads((Path(episode_dir) / "timing.json").read_text())
    nf = int(tm["duration"] * FPS)
    return tm["lines"], tm["duration"], nf, schedule(tm["lines"], nf)

def gentle():
    """Below-normal priority for this process (and the ffmpeg it starts, which inherits it), so
    composing doesn't max out the laptop (Dean, 23 Oct 2026: "relax, the laptop is going crazy")."""
    import sys
    if sys.platform == "win32":
        import ctypes
        k32 = ctypes.windll.kernel32
        k32.GetCurrentProcess.restype = ctypes.c_void_p
        k32.SetPriorityClass.argtypes = [ctypes.c_void_p, ctypes.c_uint32]
        k32.SetPriorityClass(k32.GetCurrentProcess(), 0x4000)   # BELOW_NORMAL_PRIORITY_CLASS
    else:
        os.nice(10)

FFMPEG_THREADS = ["-threads", "4"]   # encoding with every core made the fans roar

def ffmpeg():
    """ffmpeg on PATH, or where winget puts it (PATH only updates in new terminals)."""
    import shutil
    p = shutil.which("ffmpeg")
    if p: return p
    hits = sorted(Path(os.environ.get("LOCALAPPDATA", "")).glob(
        "Microsoft/WinGet/Packages/Gyan.FFmpeg*/ffmpeg-*/bin/ffmpeg.exe"))
    if hits: return str(hits[-1])
    raise SystemExit("ffmpeg not found -- install it with: winget install Gyan.FFmpeg")
