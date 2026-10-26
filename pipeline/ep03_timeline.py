"""Experiment 3's timeline, shared by the Blender render and the compose step so they always agree.

Everything is pinned to words in the narration (words.json from pipeline/align.py):
  Daisy:    one step at a time while Joe explains, 100 steps on "hundred", 1,000 on "thousand",
            far out by "barn", and home exactly on "Yes!"
  herd:     40 sheep set off on "1921" and race to 20,000 steps by just after "Eventually"
  chickens: take off on "fly" and race to 4,000 steps by "back"
Counters come from these exact walks (pipeline/walks.py), so what's on screen is what happened.
"""
import json, math
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
import sys; sys.path.insert(0, str(HERE))
from common import FPS, ROOT, load_episode
import walks as WK

LEAD = 0.3          # the voice starts this long after the picture (Daisy is already walking)
TAIL = 1.6          # picture after the last word

class Timeline:
    def __init__(self, ep_path):
        self.ep = ep = load_episode(ep_path)
        self.dir = ROOT / "renders" / Path(ep_path).stem
        self.words = json.loads((self.dir / "words.json").read_text())
        self.duration = self.words[-1]["t1"] + LEAD + TAIL
        self.nf = int(self.duration * FPS)
        t = np.arange(self.nf) / FPS
        W = self.at
        # ---- Daisy
        H = ep.DAISY["home_step"]
        self.daisy = WK.daisy(ep.DAISY["seed"], H)
        k = [(0.25, 0), (W("all.") + 0.25, 14), (W("hundred"), 100), (W("thousand"), 1000), (W("barn."), 3600), (W("Yes!"), H)]
        self.t_yes = W("Yes!")
        self.daisy_step = self._keyframes(t, k, single_until=1)
        # ---- herd
        self.herd = WK.herd(ep.HERD["seed"], ep.HERD["sheep"], ep.HERD["steps"])
        self.herd_home = [WK.first_home(p) for p in self.herd]
        h0, h1 = W("1921,"), W("Eventually.") + 0.6
        self.t_herd = h0
        self.herd_step = self._ramp(t, h0, h1, ep.HERD["steps"])
        # ---- chickens
        self.flock = WK.flock(ep.FLOCK["seed"], ep.FLOCK["chickens"], ep.FLOCK["steps"])
        self.flock_home = [WK.first_home(p) for p in self.flock]
        c0, c1 = W("fly."), W("back.")
        self.t_chicken, self.t_fly = W("But"), c0
        self.flock_step = self._ramp(t, c0, c1, ep.FLOCK["steps"])
        self.t_quote, self.t_next = W("As"), W("Next")

    def at(self, word, nth=0):
        """Video time at which `word` (as written in the script) starts."""
        key = lambda w: w.lower().strip(".,:;!?'\"")
        hits = [o["t0"] for o in self.words if key(o["w"]) == key(word)]
        if len(hits) <= nth: raise KeyError(f"{word!r} isn't in the narration")
        return hits[nth] + LEAD

    @staticmethod
    def _keyframes(t, k, single_until):
        """Steps reached at each time: one step at a time over the first segment(s), then
        exponential (straight lines in log-steps) between the later keyframes."""
        out = np.zeros(len(t), np.int64)
        for i in range(len(k) - 1):
            (ta, sa), (tb, sb) = k[i], k[i + 1]
            m = (t >= ta) & (t < tb); u = (t[m] - ta) / (tb - ta)
            if i < single_until: out[m] = np.floor(sa + (sb - sa) * u)
            else: out[m] = np.round(np.expm1(np.log1p(sa) + (np.log1p(sb) - np.log1p(sa)) * u))
        out[t >= k[-1][0]] = k[-1][1]
        return np.maximum.accumulate(out)

    @staticmethod
    def _ramp(t, t0, t1, total):
        u = np.clip((t - t0) / (t1 - t0), 0, 1)
        return np.floor(total * np.expm1(3.0 * u) / np.expm1(3.0)).astype(np.int64)

    def home_count(self, homes, step):
        return sum(1 for h in homes if h is not None and h <= step)

if __name__ == "__main__":
    tl = Timeline(sys.argv[1] if len(sys.argv) > 1 else ROOT / "episodes" / "ep03_sheep.py")
    print(f"{tl.duration:.1f}s, {tl.nf} frames | Yes! at {tl.t_yes:.2f}s, herd from {tl.t_herd:.2f}s, chickens fly at {tl.t_fly:.2f}s")
    f = lambda s: int(s * FPS)
    for name, s in (("hundred", tl.at("hundred")), ("thousand", tl.at("thousand")), ("barn", tl.at("barn.")), ("Yes", tl.t_yes)):
        st = tl.daisy_step[min(f(s), tl.nf - 1)]
        print(f"  Daisy at '{name}' ({s:.1f}s): step {st}, {int(np.abs(tl.daisy[st]).sum())} squares from home")
    print("  herd home at the end:", tl.home_count(tl.herd_home, tl.herd_step[-1]), "/", len(tl.herd),
          "| chickens home at the end:", tl.home_count(tl.flock_home, tl.flock_step[-1]), "/", len(tl.flock))
