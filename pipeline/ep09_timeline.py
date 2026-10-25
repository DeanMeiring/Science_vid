"""Experiment 9's timeline, shared by the Blender render and the compose step so they always agree.

Three runs (pipeline/helpers.py, pipeline/farmers.py), everyone taking turns, cut on words:
  A "four":  Joe, Daisy, the cow and the pig (THREE_HELPERS), one slow move at a time while Joe asks
             and explains the rule;
  B "pair":  Joe and Daisy (Experiment 4's RECORD run), racing home in a blink on "With one helper";
  C "three": Joe, the cow and Daisy (TWO_HELPERS): Daisy walks off on "first", the cow on "cow",
             Joe on "me", then they keep going while the 3,000 tries are counted;
  D "four" again, from where A stopped: the pig on "pig", racing from "More" to round 1,632 on
             "thirty-two" (all grass, everybody home), then still while Joe sums up; after "keeping the
             pig" the camera pulls back over the whole farm (pipeline/farm_overview.build_upto8).
"""
import json, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import FPS, ROOT, load_episode
import farmers as FM
import helpers as HP

LEAD = 0.3          # the voice starts this long after the picture (they're already moving)
TAIL = 4.2          # picture after the last word (the pull back over the whole farm)
SLOW = 1.85         # moves per second while slow: SPEED x1

# who's who in each run, by farmer index
CAST = {"four": ("joe", "daisy", "cow", "pig"), "pair": ("joe", "daisy"), "three": ("joe", "cow", "daisy")}
STARTS = {"four": HP.THREE_HELPERS, "pair": FM.RECORD, "three": HP.TWO_HELPERS}
ROUNDS = {"four": 1632, "pair": 4724, "three": 6400}

def moves_of(starts, rounds):
    """Every move: (farmer, square, dug?, (x, y, d) before, (x, y, d) after); origin = Joe's start."""
    out = []; ants = [list(a) for a in starts]; dirt = set()
    for _ in range(rounds):
        for k, a in enumerate(ants):
            x, y, d = a; dug = (x, y) not in dirt
            d = (d + 1) % 4 if dug else (d - 1) % 4
            dirt.add((x, y)) if dug else dirt.discard((x, y))
            before = (x, y, a[2]); a[:] = [x + FM.DX[d], y + FM.DY[d], d]
            out.append((k, (x, y), dug, before, tuple(a)))
    return out, dirt, ants

class Timeline:
    def __init__(self, ep_path):
        self.ep = load_episode(ep_path)
        self.dir = ROOT / "renders" / Path(ep_path).stem
        self.words = json.loads((self.dir / "words.json").read_text())
        self.duration = self.words[-1]["t1"] + LEAD + TAIL
        self.nf = int(self.duration * FPS)
        self.moves = {}
        for run in CAST:
            mv, dirt, ants = moves_of(STARTS[run], ROUNDS[run]); self.moves[run] = mv
            if run != "three":
                assert not dirt and [tuple(a) for a in ants] == list(STARTS[run]), f"{run} should end exactly home"
        W = self.at
        n4, n2, n3 = (len(CAST[r]) for r in ("four", "pair", "three"))
        self.t_one, self.t_two, self.t_third = W("With"), W("So"), W("So", 1)
        self.t_pig, self.t_more, self.t_home = W("pig."), W("More"), W("thirty-two.")
        self.t_sum, self.t_but, self.t_end = W("Twenty-four"), W("But"), self.duration
        self.t_pull = W("pig.", 1) + 0.6                 # then the camera pulls back over the whole farm
        self.t_left = {"daisy": W("first."), "cow": W("cow."), "joe": W("me.")}
        a_slow = 15                                       # moves done in scene A (all slow)
        self.scenes = [   # (run, start, end, keys: (time, moves done, mode to the next key))
            ("four", 0.0, self.t_one, [(0.2, 0, "lin"), (self.t_one, a_slow, "hold")]),
            ("pair", self.t_one, self.t_two, [(self.t_one, 0, "exp"), (W("ten."), 2 * 4724, "hold")]),
            ("three", self.t_two, self.t_third,
             [(self.t_two + 0.2, 0, "exp"), (self.t_left["daisy"], n3 * 1158, "lin"), (self.t_left["cow"], n3 * 3215, "lin"),
              (self.t_left["joe"], n3 * 5751, "lin"), (self.t_third, n3 * ROUNDS["three"], "hold")]),
            ("four", self.t_third, self.duration,
             [(self.t_third, a_slow, "lin"), (self.t_more, a_slow + 4, "exp"), (self.t_home, n4 * 1632, "hold")]),
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
        self.rate[np.r_[False, np.diff(self.scene) != 0]] = 0       # no speed spike at the cuts
        self.rate[np.r_[np.diff(self.scene) != 0, False]] = 0

    def at(self, word, nth=0):
        """Video time at which `word` (as written in the script) starts."""
        key = lambda w: w.lower().strip(".,:;!?'\"")
        hits = [o["t0"] for o in self.words if key(o["w"]) == key(word)]
        if len(hits) <= nth: raise KeyError(f"{word!r} isn't in the narration")
        return hits[nth] + LEAD

    def run_at(self, f):
        f = min(f, self.nf - 1)
        return self.scenes[self.scene[f]][0]

    def round_at(self, f):
        f = min(f, self.nf - 1)
        return int(self.sched[f]) // len(CAST[self.run_at(f)])

    def speed(self, f):
        """SPEED xn for the counter (0 while slow or still)."""
        return self.rate[min(f, self.nf - 1)] / SLOW

if __name__ == "__main__":
    tl = Timeline(sys.argv[1] if len(sys.argv) > 1 else ROOT / "episodes" / "ep09_helpers.py")
    print(f"{tl.duration:.1f}s, {tl.nf} frames; moves: " + ", ".join(f"{r} {len(m):,}" for r, m in tl.moves.items()))
    for name, tt in (("one", tl.t_one), ("Daisy off", tl.t_left["daisy"]), ("cow off", tl.t_left["cow"]),
                     ("Joe off", tl.t_left["joe"]), ("third", tl.t_third), ("More", tl.t_more), ("home", tl.t_home)):
        f = min(int(tt * FPS), tl.nf - 1)
        print(f"  {name:9s} {tt:5.2f}s: {tl.run_at(f)} round {tl.round_at(f):,}  SPEED x{tl.speed(f):,.0f}")
    print(f"  fastest: SPEED x{tl.rate.max() / SLOW:,.0f}")
