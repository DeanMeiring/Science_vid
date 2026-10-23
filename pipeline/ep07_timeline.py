"""Experiment 7's timeline, shared by the Blender render and the compose step so they always agree.

Every straw is a straw of the simulation (pipeline/hay.py, seed 1), in order: the count on screen, the
gold ones and pi's estimate are the simulation's. They arrive in stages that get faster and bigger
(Dean, 23 Oct), pinned to words in the narration (words.json from pipeline/align.py):
  hand     three throws by Joe: landing on "gold." (1), "not gold." (2) and "wide." (3)
  quicker  "Now: faster": Joe throws quicker and quicker, 10 straws by "Ten"
  blur     blurry-fast Joe, after he's said "2.5" (10 straws): 100 by "2.99"
  barrow   a wheelbarrow tips: 1,000 by "3.03"
  tractor  the tractor's trailer tips: 10,000 by "3.13"
  combine  a combine harvester drives past spewing straw: 100,000 by "3.14!"
Each straw lands on the planks (that's where it counts), lies there a moment, then hops onto the heap.
"""
import json, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import FPS, ROOT, load_episode
import hay as HY

LEAD = 0.3          # the voice starts this long after the picture
TAIL = 1.8          # picture after the last word
FLY = {"hand": 1.1, "quicker": 0.8, "blur": 0.5, "barrow": 0.6, "tractor": 0.7, "combine": 0.7}   # seconds in the air
LIE = 0.6           # seconds a straw lies on the planks (flashing) before it hops onto the heap

class Timeline:
    def __init__(self, ep_path):
        self.ep = ep = load_episode(ep_path)
        self.dir = ROOT / "renders" / Path(ep_path).stem
        self.words = json.loads((self.dir / "words.json").read_text(encoding="utf-8"))
        self.duration = self.words[-1]["t1"] + LEAD + TAIL
        self.nf = int(self.duration * FPS)
        W = self.at
        self.t_gold, self.t_notgold, self.t_wide = W("gold."), W("gold.", 1), W("wide.")
        self.t_faster, self.t_ten, self.t_299 = W("Now:"), W("Ten"), W("2.99.")
        self.t_303, self.t_ten_k, self.t_313, self.t_314 = W("3.03."), W("Ten", 1), W("3.13."), W("3.14!")
        self.t_daisy, self.t_mountain, self.t_buffon, self.t_see = W("Not", 1), W("I", 1), W("guy"), W("See")   # "Not the pie", "I did not plan"
        n = ep.STRAWS["n"]
        d = HY.drop(ep.STRAWS["seed"], n)
        # The script says the 2nd throw is "not gold", but the run's first three straws all cross. The
        # straws are independent, so showing one of the two pale ones among the first ten second changes
        # no count Joe says (10 straws still have 8 gold: 2.5); self.order is the order they're shown in.
        order = np.arange(n); pale = int(np.nonzero(~d["cross"][:10])[0][0])
        order[[1, pale]] = order[[pale, 1]]
        self.order = order; self.d = d
        self.cross = d["cross"][order]
        # landing time of every straw, stage by stage (straw k is the k-th straw of the simulation)
        land, stage = [], []
        def add(t0, t1, count, name, power=1.0):
            u = (np.arange(count) + 1) / count
            land.extend(t0 + (t1 - t0) * u ** power); stage.extend([name] * count)
        add(self.t_gold - 0.1, self.t_gold - 0.1, 1, "hand")
        land[-1] = self.t_gold - 0.1
        land.append(self.t_notgold - 0.1); stage.append("hand")
        land.append(self.t_wide - 0.1); stage.append("hand")
        add(self.t_faster + 1.2, self.t_ten - 0.1, 7, "quicker", 0.6)              # 4..10, quicker and quicker
        self.t_25 = W("2.5.")
        add(self.t_25 + 0.45, self.t_299 - 0.1, 90, "blur", 1.6)                  # 11..100, once he's said "2.5"
        add(self.t_299 + 1.0, self.t_303 - 0.1, 900, "barrow", 0.5)                # the wheelbarrow tips
        add(self.t_303 + 1.1, self.t_313 - 0.1, 9000, "tractor", 0.5)              # the trailer tips
        add(self.t_313 + 0.9, self.t_314 - 0.05, n - 10000, "combine", 1.4)        # the combine, faster and faster
        self.land = np.array(land); self.stage = np.array(stage)
        assert len(self.land) == n and (np.diff(self.land) >= -1e-9).all()
        fly = np.array([FLY[s] for s in self.stage])
        self.release = self.land - fly
        self.to_heap = self.land + LIE
        # the stages' windows (for the machines and Joe)
        self.win = {s: (float(self.release[self.stage == s].min()), float(self.land[self.stage == s].max())) for s in FLY}

    def at(self, word, nth=0):
        """Video time at which `word` (as written in the script) starts."""
        key = lambda w: w.lower().strip(".,:;!?'\"")
        hits = [o["t0"] for o in self.words if key(o["w"]) == key(word)]
        if len(hits) <= nth: raise KeyError(f"{word!r} isn't in the narration")
        return hits[nth] + LEAD

    def counted(self, tt):
        """Straws landed (and so counted) by time tt, and how many of them are gold."""
        k = int(np.searchsorted(self.land, tt, "right"))
        return k, int(self.cross[:k].sum())

    def on_heap(self, tt):
        return int(np.searchsorted(self.to_heap, tt, "right"))

if __name__ == "__main__":
    tl = Timeline(sys.argv[1] if len(sys.argv) > 1 else ROOT / "episodes" / "ep07_pi.py")
    print(f"{tl.duration:.1f}s, {tl.nf} frames")
    for name, tt in (("gold", tl.t_gold), ("not gold", tl.t_notgold), ("wide", tl.t_wide), ("Ten", tl.t_ten), ("2.99", tl.t_299),
                     ("3.03", tl.t_303), ("3.13", tl.t_313), ("3.14", tl.t_314)):
        k, g = tl.counted(tt + 0.05)
        print(f"  {name:9s} {tt:5.2f}s: {k:>7,} straws, {g:>6,} gold" + (f" -> pi ~ {2 * k / g:.2f}" if g else ""))
    for s, (a, b) in tl.win.items(): print(f"  {s:8s} {a:5.2f} - {b:5.2f}s")
