"""Experiment 4's timeline, shared by the Blender render and the compose step so they always agree.

Every move of the record run (pipeline/farmers.py; Joe moves, then Daisy, and so on), pinned to
words in the narration (words.json from pipeline/align.py):
  one slow move at a time while Joe explains the rules, then racing: 100 rounds on "hundred",
  1,000 on "thousand", round 1,181 (they meet) on "meet"; the rewind at a steady speed to round
  2,362 on "2,362"; a pause (wrong spots); the upside-down replay from "again" to round 4,724 on
  "perfect"; then still, and the zoom out over the whole farm from "Thanks".
"""
import json, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import FPS, ROOT, load_episode
import farmers as FM

LEAD = 0.3          # the voice starts this long after the picture (they're already moving)
TAIL = 1.8          # picture after the last word
SLOW = 1.85         # moves per second while slow: SPEED x1

class Timeline:
    def __init__(self, ep_path):
        self.ep = load_episode(ep_path)
        self.dir = ROOT / "renders" / Path(ep_path).stem
        self.words = json.loads((self.dir / "words.json").read_text())
        self.duration = self.words[-1]["t1"] + LEAD + TAIL
        self.nf = int(self.duration * FPS)
        # every move: (farmer 0 Joe / 1 Daisy, square, dug?, (x, y, d) before, (x, y, d) after); origin = Joe's start
        self.moves = []
        ants = [list(a) for a in FM.RECORD]; dirt = set()
        for r in range(4724):
            for k, a in enumerate(ants):
                x, y, d = a; dug = (x, y) not in dirt
                d = (d + 1) % 4 if dug else (d - 1) % 4
                dirt.add((x, y)) if dug else dirt.discard((x, y))
                before = (x, y, a[2]); a[:] = [x + FM.DX[d], y + FM.DY[d], d]
                self.moves.append((k, (x, y), dug, before, tuple(a)))
        assert not dirt and [tuple(a) for a in ants] == list(FM.RECORD), "the run should end exactly where it started"
        T = len(self.moves); H = T // 2
        W = self.at
        self.t_meet, self.t_clean, self.t_again, self.t_home = W("meet,"), W("2,362:"), W("again,"), W("perfect")
        self.t_slow_end = W("way.") + 0.5
        self.t_thanks, self.t_next = W("Thanks"), W("Next")
        k = [(0.2, 0, "lin"), (self.t_slow_end, 20, "lin"), (W("turns.", 2), 26, "exp"), (W("hundred"), 200, "exp"),
             (W("thousand."), 2000, "exp"), (self.t_meet, H // 2, "lin"), (self.t_clean, H, "hold"),
             (self.t_again, H, "lin"), (self.t_home, T, "hold")]
        t = np.arange(self.nf) / FPS
        s = np.zeros(self.nf)
        for (ta, ma, mode), (tb, mb, _) in zip(k, k[1:]):
            m = (t >= ta) & (t < tb); u = (t[m] - ta) / (tb - ta)
            if mode == "lin": s[m] = ma + (mb - ma) * u
            elif mode == "exp": s[m] = np.expm1(np.log1p(ma) + (np.log1p(mb) - np.log1p(ma)) * u)
            else: s[m] = ma
        s[t >= k[-1][0]] = T
        self.sched = np.maximum.accumulate(s)              # moves done (fraction = the move in progress)
        self.rate = np.gradient(self.sched) * FPS           # moves per second

    def at(self, word, nth=0):
        """Video time at which `word` (as written in the script) starts."""
        key = lambda w: w.lower().strip(".,:;!?'\"")
        hits = [o["t0"] for o in self.words if key(o["w"]) == key(word)]
        if len(hits) <= nth: raise KeyError(f"{word!r} isn't in the narration")
        return hits[nth] + LEAD

    def speed(self, f):
        """SPEED xn for the counter (0 while slow or still)."""
        return self.rate[min(f, self.nf - 1)] / SLOW

if __name__ == "__main__":
    tl = Timeline(sys.argv[1] if len(sys.argv) > 1 else ROOT / "episodes" / "ep04_farmers.py")
    print(f"{tl.duration:.1f}s, {tl.nf} frames, {len(tl.moves)} moves")
    for name, tt in (("slow end", tl.t_slow_end), ("meet", tl.t_meet), ("2,362", tl.t_clean), ("again", tl.t_again),
                     ("perfect", tl.t_home), ("Thanks", tl.t_thanks)):
        f = min(int(tt * FPS), tl.nf - 1)
        print(f"  {name:9s} {tt:5.2f}s: round {int(tl.sched[f]) // 2:,}  SPEED x{tl.speed(f):,.0f}")
    print(f"  fastest: SPEED x{tl.rate.max() / SLOW:,.0f}")
