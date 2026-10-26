"""Experiment 10's timeline, shared by the Blender render and the compose step so they always agree.

Two runs of the chaos game (pipeline/chaos.py), cut on words:
  "tri":    three barns. One hop at a time (about one a second) while Joe asks and explains, 10 hops by
            "Ten"; held on "a mess"; 100 on "hundred", 1,000 on "thousand", 10,000 on "Ten thousand",
            100,000 by "Sierpinski", 1,000,000 on "middle".
  "square": four barns, next to the triangle: racing from "Four" to 100,000 on "square", then still.
After "Go figure" the camera pulls back over the whole farm (pipeline/farm_overview.build_upto9).
"""
import json, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import FPS, ROOT, load_episode
import chaos as CH

LEAD = 0.3          # the voice starts this long after the picture (she's already hopping)
TAIL = 4.2          # picture after the last word (the pull back over the whole farm)
SLOW = 1.0          # hops per second while slow: SPEED x1
N_TRI, N_SQ = 1_000_000, 100_000
SQ = CH.SQUARE * np.array([1.0, np.sqrt(3) / 2])          # the four barns: a square-ish field the triangle's size

class Timeline:
    def __init__(self, ep_path):
        self.ep = load_episode(ep_path)
        self.dir = ROOT / "renders" / Path(ep_path).stem
        self.words = json.loads((self.dir / "words.json").read_text())
        self.duration = self.words[-1]["t1"] + LEAD + TAIL
        self.nf = int(self.duration * FPS)
        self.pts = {"tri": CH.hops(CH.TRI, N_TRI, seed=1), "square": CH.hops(SQ, N_SQ, seed=2)}
        W = self.at
        self.t_ten, self.t_mess = W("Ten"), W("mess.")
        self.t_tri, self.t_name, self.t_1915 = W("Triangles,"), W("Sierpinski"), W("nineteen")
        self.t_million, self.t_middle, self.t_not = W("million"), W("middle."), W("Not")
        self.t_four, self.t_square, self.t_same = W("Four"), W("square."), W("Same")
        self.t_pull = W("figure.") + 0.4
        self.scenes = [   # (run, start, end, keys: (time, hops done, mode to the next key))
            ("tri", 0.0, self.t_four,
             [(0.35, 0, "lin"), (self.t_ten, 10, "hold"), (W("A", 3) - 0.5, 10, "exp"), (W("hundred:"), 100, "exp"),
              (W("thousand."), 1000, "exp"), (W("thousand.", 1), 10_000, "exp"), (self.t_name, 100_000, "hold"),
              (self.t_million, 100_000, "exp"), (self.t_middle, N_TRI, "hold")]),
            ("square", self.t_four, self.duration,
             [(self.t_four + 0.3, 0, "exp"), (self.t_square, N_SQ, "hold")]),
        ]
        t = np.arange(self.nf) / FPS
        self.scene = np.zeros(self.nf, int); self.sched = np.zeros(self.nf)
        for i, (run, t0, t1, k) in enumerate(self.scenes):
            m = (t >= t0) & (t < t1); self.scene[m] = i
            s = np.full(m.sum(), float(k[0][1])); tt = t[m]
            for (ta, ma, mode), (tb, mb, _) in zip(k, k[1:]):
                w = (tt >= ta) & (tt < tb); u = (tt[w] - ta) / (tb - ta)
                if mode == "lin": s[w] = ma + (mb - ma) * u
                elif mode == "exp": s[w] = np.expm1(np.log1p(ma) + (np.log1p(mb) - np.log1p(ma)) * u)
                else: s[w] = ma
            s[tt >= k[-1][0]] = k[-1][1]
            self.sched[m] = np.maximum.accumulate(s)
        self.rate = np.gradient(self.sched) * FPS
        cut = np.r_[False, np.diff(self.scene) != 0]
        self.rate[cut] = 0; self.rate[np.r_[cut[1:], False]] = 0     # no speed spike at the cut

    def at(self, word, nth=0):
        """Video time at which `word` (as written in the script) starts."""
        key = lambda w: w.lower().strip(".,:;!?'\"")
        hits = [o["t0"] for o in self.words if key(o["w"]) == key(word)]
        if len(hits) <= nth: raise KeyError(f"{word!r} isn't in the narration")
        return hits[nth] + LEAD

    def run_at(self, f):
        return self.scenes[self.scene[min(f, self.nf - 1)]][0]

    def hops_at(self, f):
        return int(self.sched[min(f, self.nf - 1)])

    def speed(self, f):
        """SPEED xn for the counter (0 while slow or still)."""
        return self.rate[min(f, self.nf - 1)] / SLOW

if __name__ == "__main__":
    tl = Timeline(sys.argv[1] if len(sys.argv) > 1 else ROOT / "episodes" / "ep10_chicken.py")
    print(f"{tl.duration:.1f}s, {tl.nf} frames")
    for name, tt in (("Ten", tl.t_ten), ("hundred", tl.at("hundred:")), ("thousand", tl.at("thousand.")),
                     ("10k", tl.at("thousand.", 1)), ("Sierpinski", tl.t_name), ("middle", tl.t_middle),
                     ("Four", tl.t_four + 0.05), ("square", tl.t_square), ("pull", tl.t_pull)):
        f = min(int(tt * FPS), tl.nf - 1)
        print(f"  {name:10s} {tt:5.2f}s: {tl.run_at(f)} {tl.hops_at(f):,} hops  SPEED x{tl.speed(f):,.0f}")
