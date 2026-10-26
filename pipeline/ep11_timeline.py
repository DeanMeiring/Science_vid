"""Experiment 11's timeline, shared by the Blender render and the compose step so they always agree.

Four codes (pipeline/codes.py), each on its own field, cut on words:
  "spiral"   RLLLLRRRLLL:  one slow step at a time while Joe explains the rule, then racing from "eleven"
             through "Chaos" to 300,000 steps on "spiral";
  "square"   LRRRRRLLR:    racing to 200,000 on "square";
  "triangle" RRLLLRLLLRRR: to 15,000 on "walks", 100,000 on "behind";
  "highway"  RRLRLLRLRR:   to 232,645 (where the highway starts) on "steps...", 350,000 on "highway".
Then still: on "Same" the camera shows the four fields side by side (a 2 x 2 block), and after "carrots"
it pulls back over the whole farm (pipeline/farm_overview.build_upto10).
"""
import json, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import FPS, ROOT, load_episode
import codes as CD

LEAD = 0.3          # the voice starts this long after the picture (he's already walking)
TAIL = 4.2          # picture after the last word (the pull back over the whole farm)
SLOW = 1.6          # steps per second while slow: SPEED x1
FIELDS = (("spiral", "RLLLLRRRLLL", 300_000), ("square", "LRRRRRLLR", 200_000),
          ("triangle", "RRLLLRLLLRRR", 100_000), ("highway", "RRLRLLRLRR", 350_000))
HIGHWAY_FROM = 232_645       # pipeline/codes.py: RRLRLLRLRR's highway starts here (repeats every 936 steps)

class Timeline:
    def __init__(self, ep_path):
        self.ep = load_episode(ep_path)
        self.dir = ROOT / "renders" / Path(ep_path).stem
        self.words = json.loads((self.dir / "words.json").read_text())
        self.duration = self.words[-1]["t1"] + LEAD + TAIL
        self.nf = int(self.duration * FPS)
        self.code = {name: code for name, code, _ in FIELDS}
        self.log = {name: CD.log(code, steps) for name, code, steps in FIELDS}
        # each field's box (relative to its start), and where its start goes: a 2 x 2 block round (0, 0)
        self.box = {}
        for name, lg in self.log.items():
            xs = np.r_[lg["cx"], lg["px"]]; ys = np.r_[lg["cy"], lg["py"]]
            self.box[name] = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
        q = max(max(b[2] - b[0], b[3] - b[1]) for b in self.box.values()) + 40       # one quadrant
        self.quad = q
        self.origin = {}
        for (name, _, _), (qx, qy) in zip(FIELDS, ((-1, -1), (0, -1), (-1, 0), (0, 0))):
            b = self.box[name]
            self.origin[name] = (qx * q + q // 2 - (b[0] + b[2]) // 2, qy * q + q // 2 - (b[1] + b[3]) // 2)
        W = self.at
        self.t_spiral, self.t_square, self.t_tri, self.t_hw = 0.0, W("This", 1), W("This", 2), W("And")
        self.t_same, self.t_pull = W("Same"), W("carrots.") + 0.4
        self.reveal = {"spiral": W("spiral."), "square": W("square.", 1), "triangle": W("triangle"), "highway": W("highway.")}
        self.scenes = [   # (field, start, end, keys: (time, steps done, mode to the next key))
            ("spiral", 0.0, self.t_square,
             [(0.3, 0, "lin"), (W("eleven"), 14, "exp"), (W("then", 1), 20_000, "exp"), (W("spiral."), 300_000, "hold")]),
            ("square", self.t_square, self.t_tri, [(self.t_square + 0.15, 0, "exp"), (W("square.", 1), 200_000, "hold")]),
            ("triangle", self.t_tri, self.t_hw,
             [(self.t_tri + 0.15, 0, "exp"), (W("walks"), 15_000, "exp"), (W("behind"), 100_000, "hold")]),
            ("highway", self.t_hw, self.duration,
             [(self.t_hw + 0.15, 0, "exp"), (W("steps..."), HIGHWAY_FROM, "lin"), (W("highway.") + 0.5, 350_000, "hold")]),
        ]
        t = np.arange(self.nf) / FPS
        self.scene = np.zeros(self.nf, int); self.sched = np.zeros(self.nf)
        for i, (field, t0, t1, k) in enumerate(self.scenes):
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
        self.rate[cut] = 0; self.rate[np.r_[cut[1:], False]] = 0     # no speed spike at the cuts

    def at(self, word, nth=0):
        """Video time at which `word` (as written in the script) starts."""
        key = lambda w: w.lower().strip(".,:;!?'\"")
        hits = [o["t0"] for o in self.words if key(o["w"]) == key(word)]
        if len(hits) <= nth: raise KeyError(f"{word!r} isn't in the narration")
        return hits[nth] + LEAD

    def field_at(self, f):
        return self.scenes[self.scene[min(f, self.nf - 1)]][0]

    def steps_at(self, f):
        return int(self.sched[min(f, self.nf - 1)])

    def speed(self, f):
        """SPEED xn for the counter (0 while slow or still)."""
        return self.rate[min(f, self.nf - 1)] / SLOW

if __name__ == "__main__":
    tl = Timeline(sys.argv[1] if len(sys.argv) > 1 else ROOT / "episodes" / "ep11_codes.py")
    print(f"{tl.duration:.1f}s, {tl.nf} frames; quadrant {tl.quad} squares")
    for name, b in tl.box.items(): print(f"  {name:9s} box {b[2] - b[0] + 1} x {b[3] - b[1] + 1}, start at {tl.origin[name]}")
    for name, tt in (("eleven", tl.at("eleven")), ("Chaos", tl.at("Chaos...")), *tl.reveal.items(), ("walks", tl.at("walks")),
                     ("steps...", tl.at("steps...")), ("Same", tl.t_same), ("pull", tl.t_pull)):
        f = min(int(tt * FPS), tl.nf - 1)
        print(f"  {name:9s} {tt:5.2f}s: {tl.field_at(f)} step {tl.steps_at(f):,}  SPEED x{tl.speed(f):,.0f}")
