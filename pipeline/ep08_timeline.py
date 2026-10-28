"""Experiment 8's timeline (what grows if you plant it?), shared by the render and the compose step.

Five scenes, cut together, pinned to words in the narration (words.json from pipeline/align.py):
  mustard  Joe plants a seed ("If you plant"), a time-lapse grows it chest-high by "season."
  apple    Joe plants an apple seed, a time-lapse grows the tree (green apples) by "same apple."
  both     two seeds in one hole; a thought bubble of a mustard-apple, crossed out; two plants come up
  tyre     Joe plants the rusty tyre, sits in his deck chair; two years go by (two winters) on "wait two
           years"; "nothing."; weeds pop up on "Weeds."
  law      Pasteur's swan-neck flask on a little table by the chair; then the whole farm from "I'm".
"""
import json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from common import FPS, ROOT, load_episode

LEAD = 0.3          # the voice starts this long after the picture
TAIL = 1.8          # picture after the last word

class Timeline:
    def __init__(self, ep_path):
        self.ep = load_episode(ep_path)
        self.dir = ROOT / "renders" / Path(ep_path).stem
        self.words = json.loads((self.dir / "words.json").read_text(encoding="utf-8"))
        self.duration = self.words[-1]["t1"] + LEAD + TAIL
        self.nf = int(self.duration * FPS)
        W = self.at
        # scene starts (cuts) and key moments
        self.s_mustard, self.s_apple, self.s_both = 0.0, W("If", 1) - 0.15, W("Plant", 2) - 0.15   # "Plant them together"
        self.s_tyre, self.s_law, self.s_end = W("And", 1) - 0.15, W("Scientists") - 0.15, W("I'm") - 0.1
        self.grow_mustard = (W("you", 1), W("season."))              # "you get mustard ... one season."
        self.grow_apple = (W("you", 3), W("same") + 0.1)              # "you get an apple tree ... same"
        self.bubble = (W("you", 4) - 0.2, W("They're") - 0.1)        # "you will not get a mustard-apple"
        self.grow_both = (W("They're"), W("family.") + 0.3)
        self.plant_tyre = (W("plant", 3) - 0.2, W("tyre,") + 0.2)
        self.wait = (W("wait"), W("nothing.") - 0.1)                   # two years go by
        self.weeds = W("Weeds.")
        self.pasteur = W("Louis")
        self.t_still = W("still")

    def at(self, word, nth=0):
        """Video time at which `word` (as written in the script) starts."""
        key = lambda w: w.lower().strip(".,:;!?'\"")
        hits = [o["t0"] for o in self.words if key(o["w"]) == key(word)]
        if len(hits) <= nth: raise KeyError(f"{word!r} isn't in the narration")
        return hits[nth] + LEAD

if __name__ == "__main__":
    tl = Timeline(sys.argv[1] if len(sys.argv) > 1 else ROOT / "episodes" / "ep08_plant.py")
    print(f"{tl.duration:.1f}s, {tl.nf} frames")
    for k in ("s_apple", "s_both", "s_tyre", "s_law", "s_end", "grow_mustard", "grow_apple", "bubble", "grow_both",
              "plant_tyre", "wait", "weeds", "pasteur", "t_still"):
        v = getattr(tl, k); print(f"  {k:13s}", tuple(round(x, 2) for x in v) if isinstance(v, tuple) else round(v, 2))
