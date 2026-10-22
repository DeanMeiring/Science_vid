"""Experiment 5's timeline, shared by the Blender render and the compose step so they always agree.

Joe's walk (pipeline/crops.py), pinned to words in the narration (words.json from pipeline/align.py):
  one slow step at a time while Joe explains the rules; a quick messy run ("just a mess"); slowing
  down so he walks back onto his first square, facing up, exactly on "image!" (step 500, a mirror
  moment); landing on step 1,000 on "mirror." and 10,012 on "again." (both mirror moments); then
  racing to 100,044 by "times." showing only mirror moments, so every frame is a true mirror image;
  then still, with the camera rising over the crop circle.
"""
import json, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import FPS, N, ROOT, load_episode
import crops as CR

LEAD = 0.3          # the voice starts this long after the picture (Joe is already walking)
TAIL = 1.8          # picture after the last word
SLOW = 1.6          # steps per second while slow: SPEED x1

class Timeline:
    def __init__(self, ep_path):
        self.ep = ep = load_episode(ep_path)
        self.dir = ROOT / "renders" / Path(ep_path).stem
        self.words = json.loads((self.dir / "words.json").read_text())
        self.duration = self.words[-1]["t1"] + LEAD + TAIL
        self.nf = int(self.duration * FPS)
        END = ep.STEPS
        _, self.hist = CR.run(END + 1, size=N)               # x, y, facing after each step (start: N//2, N//2, up)
        c = N // 2
        self.mirrors = np.nonzero((self.hist[:, 0] == c) & (self.hist[:, 1] == c) & (self.hist[:, 2] == 0))[0][1:]
        W = self.at
        self.t_rules_end, self.t_reveal = W("crop."), W("image!")
        self.t_1k, self.t_10k = W("mirror", 1), W("again.", 2)
        self.t_race, self.t_race_end = W("By"), W("times.")
        self.t_circle, self.t_next = W("circle!"), W("Next")
        k = [(0.2, 0, "lin"), (self.t_rules_end, 16, "exp"), (W("mess."), 150, "land"), (self.t_reveal, 500, "hold"),
             (W("thousand") - 0.1, 500, "land"), (self.t_1k, 1000, "hold"), (W("Ten"), 1000, "land"), (self.t_10k, 10012, "hold"),
             (self.t_race, 10012, "exp"), (self.t_race_end, END, "hold")]
        for s in (500, 1000, 10012, END): assert s in set(self.mirrors.tolist()), f"step {s} isn't a mirror moment"
        self.landings = [(self.t_reveal, 500), (self.t_1k, 1000), (self.t_10k, 10012), (self.t_race_end, END)]
        t = np.arange(self.nf) / FPS
        s = np.zeros(self.nf)
        for (ta, ma, mode), (tb, mb, _) in zip(k, k[1:]):
            m = (t >= ta) & (t < tb); u = (t[m] - ta) / (tb - ta)
            if mode == "lin": s[m] = ma + (mb - ma) * u
            elif mode == "exp": s[m] = np.expm1(np.log1p(ma) + (np.log1p(mb) - np.log1p(ma)) * u)
            elif mode == "land":                             # fast, then braking into the target step
                s[m] = np.expm1(np.log1p(mb) - (np.log1p(mb) - np.log1p(ma)) * (1 - u) ** 2.5)
            else: s[m] = ma
        s[t >= k[-1][0]] = END
        self.sched = np.maximum.accumulate(s)
        self.rate = np.gradient(self.sched) * FPS            # steps per second
        # while racing, show only mirror moments (every frame a true mirror image)
        self.snap = (t >= self.t_race) & (t < self.t_race_end) & (self.rate > FPS * 3)
        fl = np.floor(self.sched).astype(int)
        latest = self.mirrors[np.maximum(np.searchsorted(self.mirrors, fl, "right") - 1, 0)]
        self.shown = np.where(self.snap, latest, fl)

    def at(self, word, nth=0):
        """Video time at which `word` (as written in the script) starts."""
        key = lambda w: w.lower().strip(".,:;!?'\"")
        hits = [o["t0"] for o in self.words if key(o["w"]) == key(word)]
        if len(hits) <= nth: raise KeyError(f"{word!r} isn't in the narration")
        return hits[nth] + LEAD

    def mirror_count(self, step):
        return int(np.searchsorted(self.mirrors, step, "right"))

    def speed(self, f):
        return self.rate[min(f, self.nf - 1)] / SLOW

if __name__ == "__main__":
    tl = Timeline(sys.argv[1] if len(sys.argv) > 1 else ROOT / "episodes" / "ep05_crops.py")
    print(f"{tl.duration:.1f}s, {tl.nf} frames")
    for tt, st in tl.landings:
        f = min(int(round(tt * FPS)), tl.nf - 1)
        print(f"  {tt:5.2f}s: shows step {tl.shown[f]:,} (want {st:,}), mirror #{tl.mirror_count(st)}")
    for name, tt in (("rules end", tl.t_rules_end), ("race", tl.t_race + 1.0)):
        f = int(tt * FPS); print(f"  {name} {tt:.2f}s: step {tl.shown[f]:,} SPEED x{tl.speed(f):,.0f}")
    print(f"  fastest SPEED x{tl.rate.max() / SLOW:,.0f}")
