"""Experiment 12's timeline, shared by the Blender render and the compose step so they always agree.

One herd of 23 cows stands on the field from the first frame: herd 1 of the seeded 23-cow run
(pipeline/birthdays.py). Their tags show "?" until "birthdays", then herd 1's dates. Cut on words:
  hook/model/maths  wide on the herd; on "22" / "23:" the exact-probability cards (compose);
  "This"            the camera moves in on cows 8 and 13 (already a pair: no cow arrives to make it);
  "But"             back wide; herds 2, 3, 4 one at a time (new tags each), then the tally races to
                    100,000 herds, landing on "had" (50,617 with a match);
  "23" (2nd)        lines between pairs build up to 253 by "possible";
  "cake"            in on Joe while cakes pile up; after "flour." the pull back over the whole farm.
"""
import json, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import FPS, ROOT, load_episode
import birthdays as BD

LEAD = 0.3          # the voice starts this long after the picture
TAIL = 4.2          # picture after the last word (the pull back over the whole farm)
HERD = 23
PAIR = (7, 12)      # 0-based: cows 8 and 13 share 30 Aug in herd 1 (checked in __main__)

class Timeline:
    def __init__(self, ep_path):
        self.ep = load_episode(ep_path)
        self.dir = ROOT / "renders" / Path(ep_path).stem
        self.words = json.loads((self.dir / "words.json").read_text())
        self.duration = self.words[-1]["t1"] + LEAD + TAIL
        self.nf = int(self.duration * FPS)
        sim = BD.simulate(HERD)
        self.days = BD.herds(HERD)                      # (100,000, 23) birthdays, the same stream as the tally
        self.running = sim["running"]                   # herds with a match among the first k + 1
        self.hits, self.trials = sim["hits"], sim["trials"]
        W = self.at
        self.t_tags = W("birthdays")
        self.t_card22, self.t_card23 = W("22"), W("23")
        self.t_pair, self.t_test, self.t_land = W("This"), W("But"), W("had")
        self.t_rate = W("50.6%")
        self.t_why, self.t_lines, self.t_253 = W("Why"), W("23", 1), W("possible")
        self.t_cake, self.t_flour = W("cake"), W("flour.")
        self.t_pull = self.t_flour + 0.4
        # herds done (float), herd 1 from the start
        t = np.arange(self.nf) / FPS
        keys = [(0.0, 1, "hold"), (self.t_test, 1, "lin"), (W("herds.", 1) + 0.2, 4, "exp"), (self.t_land, self.trials, "hold")]
        s = np.ones(self.nf)
        for (ta, ma, mode), (tb, mb, _) in zip(keys, keys[1:]):
            w = (t >= ta) & (t < tb); u = (t[w] - ta) / (tb - ta)
            if mode == "lin": s[w] = ma + (mb - ma) * u
            elif mode == "exp": s[w] = np.expm1(np.log1p(ma) + (np.log1p(mb) - np.log1p(ma)) * u)
            else: s[w] = ma
        s[t >= keys[-1][0]] = keys[-1][1]
        self.sched = np.maximum.accumulate(s)
        self.rate = np.gradient(self.sched) * FPS        # herds per second
        # pair lines drawn so far
        u = np.clip((t - self.t_lines) / (self.t_253 - self.t_lines), 0, 1)
        self.lines = np.where(t >= self.t_lines, np.round(253 * u ** 1.5), 0).astype(int)
        self.lines[t >= self.t_cake] = 0
        # cakes in the pile
        self.cakes = np.clip((t - self.t_cake) / (self.t_flour - self.t_cake), 0, 1)

    def at(self, word, nth=0):
        """Video time at which `word` (as written in the script) starts."""
        key = lambda w: w.lower().strip(".,:;!?'\"")
        hits = [o["t0"] for o in self.words if key(o["w"]) == key(word)]
        if len(hits) <= nth: raise KeyError(f"{word!r} isn't in the narration")
        return hits[nth] + LEAD

    def herd_at(self, f):
        """Which herd is on screen (1-based) and how many of herds 1..h had a match."""
        h = max(1, min(self.trials, int(self.sched[min(f, self.nf - 1)])))
        return h, int(self.running[h - 1])

    def shot(self, f):
        """Camera shot: wide / pair / joe / pull."""
        tt = f / FPS
        if tt >= self.t_pull: return "pull"
        if tt >= self.t_cake - 0.4: return "joe"
        if self.t_pair <= tt < self.t_test: return "pair"
        return "wide"

if __name__ == "__main__":
    tl = Timeline(sys.argv[1] if len(sys.argv) > 1 else ROOT / "episodes" / "ep12_birthdays.py")
    print(f"{tl.duration:.1f}s, {tl.nf} frames")
    pairs = BD.matches(tl.days[0])
    assert pairs == [PAIR], pairs
    print(f"herd 1: cows {PAIR[0] + 1} & {PAIR[1] + 1} on {BD.date(tl.days[0][PAIR[0]])}; no other pair")
    for name in ("t_tags", "t_card22", "t_card23", "t_pair", "t_test", "t_land", "t_rate", "t_lines", "t_253", "t_cake",
                 "t_flour", "t_pull"):
        tt = getattr(tl, name); f = min(int(tt * FPS), tl.nf - 1); h, m = tl.herd_at(f)
        print(f"  {name:9s} {tt:5.2f}s  {tl.shot(f):5s} herd {h:>7,}  matches {m:>6,}  lines {tl.lines[f]:3d}")
    f = tl.nf - 1; h, m = tl.herd_at(f)
    assert (h, m) == (100_000, 50_617), (h, m)
    print(f"end: {m:,} of {h:,} herds = {m / h:.2%}")
