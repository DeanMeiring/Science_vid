"""Experiment 6's timeline, shared by the Blender render and the compose step so they always agree.

Pinned to words in the narration (words.json from pipeline/align.py):
  Daisy trots up to barn 1 by "one."; Joe opens barn 3 on "goat." (a goat); "Should Daisy switch?";
  during "Fifty-fifty" the camera rises over the barns to the lots behind and the 1,000 games
  (pipeline/barns.py) start: a few slowly, then racing, done on "339."; back to the barns
  on "Her"; barn 2 opens on "showed" (the tractor: switching would have won); letters rain down on
  "1990"; a wide shot on "Even"; the whole farm from "Next".
"""
import json, sys
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import FPS, ROOT, load_episode
import barns as BG

LEAD = 0.3          # the voice starts this long after the picture (Daisy is already trotting)
TAIL = 1.8          # picture after the last word

class Timeline:
    def __init__(self, ep_path):
        self.ep = ep = load_episode(ep_path)
        self.dir = ROOT / "renders" / Path(ep_path).stem
        self.words = json.loads((self.dir / "words.json").read_text(encoding="utf-8"))
        self.duration = self.words[-1]["t1"] + LEAD + TAIL
        self.nf = int(self.duration * FPS)
        W = self.at
        self.t_tractor, self.t_pick, self.t_goat = W("tractor."), W("one.", 1), W("goat.")    # not "One has my..."
        self.t_switch, self.t_fifty = W("switch?"), W("Fifty-fifty.")
        self.t_play, self.t_339, self.t_661, self.t_23 = W("Let's"), W("339."), W("661!"), W("two", 1)
        self.t_her, self.t_showed = W("Her"), W("showed")
        self.t_1990, self.t_even, self.t_sim = W("1990,"), W("Even"), W("simulation.")
        self.t_next = W("Next")
        self.g = BG.games(ep.GAMES["seed"], ep.GAMES["n"])
        self.stay_win = self.g["pick"] == self.g["prize"]
        n = ep.GAMES["n"]
        t = np.arange(self.nf) / FPS
        a, b = self.t_fifty + 0.6, self.t_339 - 0.05               # the games: 5 slowly, then racing; done on "339."
        mid = a + 0.45 * (b - a)
        p = np.where(t < a, 0, np.where(t < mid, (t - a) / (mid - a) * 5,
                     np.expm1(np.log1p(5) + (np.log1p(n) - np.log1p(5)) * np.clip((t - mid) / (b - mid), 0, 1))))
        p[t >= b] = n
        self.played = np.round(np.minimum(p, n), 6)
        self.t_games_end = b

    def at(self, word, nth=0):
        """Video time at which `word` (as written in the script) starts."""
        key = lambda w: w.lower().strip(".,:;!?'\"")
        hits = [o["t0"] for o in self.words if key(o["w"]) == key(word)]
        if len(hits) <= nth: raise KeyError(f"{word!r} isn't in the narration")
        return hits[nth] + LEAD

    def won(self, f):
        n = int(np.floor(self.played[min(f, self.nf - 1)] + 1e-9))
        s = int(self.stay_win[:n].sum()); return dict(played=n, stay=s, switch=n - s)

if __name__ == "__main__":
    tl = Timeline(sys.argv[1] if len(sys.argv) > 1 else ROOT / "episodes" / "ep06_barns.py")
    print(f"{tl.duration:.1f}s, {tl.nf} frames")
    for name, tt in (("pick", tl.t_pick), ("goat", tl.t_goat), ("play", tl.t_play), ("339", tl.t_339), ("661", tl.t_661),
                     ("two of three", tl.t_23), ("Her", tl.t_her), ("showed", tl.t_showed), ("1990", tl.t_1990), ("Next", tl.t_next)):
        print(f"  {name:13s} {tt:5.2f}s  games {tl.won(int(tt * FPS))}")
