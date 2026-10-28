"""Word timings for a narration track: Whisper hears the audio, then each script word gets the
time it was spoken (like CLIPPER's longform_beats). Also the misread check.

Usage: .venv/Scripts/python pipeline/align.py episodes/ep03_sheep.py [narration_flow.wav]
Writes renders/<episode>/words.json: [{"w": caption word, "beat": cue, "t0": s, "t1": s}, ...]
"""
import difflib, json, re, sys, wave
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, load_episode

def load16k(p):
    """faster-whisper's own audio reader trips over this PyAV version, so feed it samples."""
    with wave.open(str(p)) as w:
        sr = w.getframerate(); a = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32767
    n = int(len(a) * 16000 / sr)
    return np.interp(np.arange(n) * sr / 16000, np.arange(len(a)), a).astype(np.float32)

NUM = {"1921": "nineteen twenty one", "3": "three"}

# Only for episodes with ALIGN_SPELL_NUMBERS = True (from Experiment 12), so older timings stay as they were:
# Whisper writes numbers as digits ("23", "50,617", "50.6%", "30th"); spell both sides out the same way.
ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen " \
       "seventeen eighteen nineteen".split()
TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()
def spell_int(n):
    if n < 20: return ONES[n]
    if n < 100: return TENS[n // 10] + ("" if n % 10 == 0 else " " + ONES[n % 10])
    for size, name in ((10 ** 6, "million"), (1000, "thousand"), (100, "hundred")):
        if n >= size:
            return spell_int(n // size) + " " + name + ("" if n % size == 0 else " " + spell_int(n % size))
ORD = {"one": "first", "two": "second", "three": "third", "five": "fifth", "eight": "eighth", "nine": "ninth",
       "twelve": "twelfth"}
def spell_number(m):
    whole, frac, ordinal, pct = m.group(1).replace(",", ""), m.group(2), m.group(3), m.group(4)
    s = spell_int(int(whole))
    if frac: s += " point " + " ".join(ONES[int(d)] for d in frac[1:])
    if ordinal:
        *head, last = s.split()
        last = ORD.get(last) or (last[:-1] + "ieth" if last.endswith("y") else last + "th")
        s = " ".join(head + [last])
    return " " + s + (" percent" if pct else "") + " "
NUMBER = re.compile(r"(\d[\d,]*)(\.\d+)?(st|nd|rd|th)?(%)?")
SPELL = False                       # set from the episode in main()

def norm(w):
    w = w.lower().replace("ó", "o").replace("-", " ")
    if SPELL: w = NUMBER.sub(spell_number, w)
    w = re.sub(r"[^a-z0-9' ]", "", w).strip("'")
    return NUM.get(w, w)

def main():
    global SPELL
    ep_path = Path(sys.argv[1]); ep = load_episode(ep_path)
    SPELL = bool(getattr(ep, "ALIGN_SPELL_NUMBERS", False))
    d = ROOT / "renders" / ep_path.stem
    audio = d / (sys.argv[2] if len(sys.argv) > 2 else "narration_flow.wav")
    from faster_whisper import WhisperModel
    m = WhisperModel("base.en", device="cpu", compute_type="int8", cpu_threads=4)
    segs, _ = m.transcribe(load16k(audio), word_timestamps=True, language="en")
    heard = [(norm(w.word), w.start, w.end) for s in segs for w in s.words]
    heard_flat = [(p, a, b) for h, a, b in heard for p in (h.split() or [h])]
    # script words, each with its beat; numbers expand to how they're said
    script = []
    for cue, caption, _say in ep.NARRATION:
        for w in caption.split():
            script.append((w, cue, norm(w).split() or [""]))
    flat = [(i, p) for i, (_, _, ps) in enumerate(script) for p in ps]
    sm = difflib.SequenceMatcher(None, [p for _, p in flat], [h for h, _, _ in heard_flat], autojunk=False)
    t = {}
    for a, b, n in sm.get_matching_blocks():
        for k in range(n):
            i = flat[a + k][0]; _, s0, s1 = heard_flat[b + k]
            t.setdefault(i, [s0, s1]); t[i][1] = s1
    # words Whisper misheard: spread between their matched neighbours
    known = sorted(t)
    out = []
    for i, (w, cue, _) in enumerate(script):
        if i not in t:
            prev = max([k for k in known if k < i], default=None); nxt = min([k for k in known if k > i], default=None)
            a = t[prev][1] if prev is not None else 0.0; b = t[nxt][0] if nxt is not None else a + 0.4
            gap = [k for k in range(len(script)) if (prev is None or k > prev) and (nxt is None or k < nxt)]
            j = gap.index(i); step = (b - a) / len(gap)
            t[i] = [a + j * step, a + (j + 1) * step]
        out.append({"w": w, "beat": cue, "t0": round(float(t[i][0]), 3), "t1": round(float(t[i][1]), 3)})
    (d / "words.json").write_text(json.dumps(out, indent=0))
    missed = len(script) - len([i for i in range(len(script)) if i in dict.fromkeys(known)])
    print(f"{len(out)} words timed, {missed} filled in between neighbours (misheard) -> {d / 'words.json'}")
    beats = {}
    for o in out: beats.setdefault(o["beat"], [o["t0"], o["t1"]]); beats[o["beat"]][1] = o["t1"]
    for k, (a, b) in beats.items(): print(f"  {k:8s} {a:6.2f} -> {b:6.2f}")

if __name__ == "__main__":
    main()
