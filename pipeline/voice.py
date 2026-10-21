"""Narrate an episode in its voice and work out the timing of every line.

Usage: .venv/Scripts/python pipeline/voice.py episodes/ep01_farm.py
Writes renders/<episode>/voice/NN.wav, voice.wav (the whole track) and timing.json.

The voice is the episode's VOICE (a pipeline/tts.py spec); without one it's Farmer Joe's
blend of Kokoro michael and santa. Changing the voice redoes every line.

A line's spoken text can also be a list of (text, pause after in seconds) pieces, for comic
timing: [("Whoa!", 1.3), ("I'm okay.", 1.4), ("Hat's okay too.", 0)]. The caption's words are
shared out over the pieces in order (so the caption should have the same words).

Each line's real length sets how long the simulation spends on it. Caption words are
spread over the spoken part of the line by word length (a Whisper alignment can
replace this later, as in CLIPPER's longform_beats).
"""
import hashlib, json, os, subprocess, sys, wave
from pathlib import Path
import numpy as np

if not sys.flags.utf8_mode:   # pocket_tts reads its config in the locale charset on Windows and breaks
    sys.exit(subprocess.call([sys.executable, "-X", "utf8", *sys.argv]))

import torch
torch.set_num_threads(4)   # keep the laptop usable
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, load_episode, load_env
from tts import FARMER_JOE, Voice

SR_OUT = 48000
LEAD = 0.4                 # silence before the first line
GAP = 0.45                 # pause after each line
MIN_DUR = {"single": 3.2, "land": 3.0, "trip": 4.5}

def voiced_span(a, sr):
    """Start/end (s) of the part above the noise floor, so word timings ignore silence."""
    k = int(0.02 * sr)
    e = np.sqrt(np.convolve(a ** 2, np.ones(k) / k, "same"))
    on = np.nonzero(e > max(1e-4, e.max() * 0.05))[0]
    return (on[0] / sr, on[-1] / sr) if len(on) else (0.0, len(a) / sr)

def speech_spans(a, sr, n, min_gap=0.5):
    """The n spoken pieces of a line: split it at its n-1 longest silences (each >= min_gap s)."""
    if n == 1: return [voiced_span(a, sr)]
    k = int(0.02 * sr)
    e = np.sqrt(np.convolve(a ** 2, np.ones(k) / k, "same")); on = e > max(1e-4, e.max() * 0.05)
    idx = np.nonzero(on)[0]
    gaps = [(idx[j + 1] - idx[j], idx[j], idx[j + 1]) for j in range(len(idx) - 1) if idx[j + 1] - idx[j] > min_gap * sr]
    cut = sorted(sorted(gaps, reverse=True)[:n - 1], key=lambda g: g[1])
    bounds = [idx[0]] + sum(([g[1], g[2]] for g in cut), []) + [idx[-1]]
    return [(bounds[2 * j] / sr, bounds[2 * j + 1] / sr) for j in range(len(bounds) // 2)]

def main():
    ep_path = Path(sys.argv[1]); ep = load_episode(ep_path)
    load_env()
    out = ROOT / "renders" / ep_path.stem; (out / "voice").mkdir(parents=True, exist_ok=True)
    spec = getattr(ep, "VOICE", FARMER_JOE)
    old = json.loads((out / "timing.json").read_text()) if (out / "timing.json").exists() else {}
    was = old.get("voice")
    if was and ":" not in was: was = "pocket:" + was      # older timing files named only the preset
    if was not in (None, spec):   # another voice made these lines: start over
        for f in (out / "voice").glob("*.wav"): f.unlink()
    voice = Voice(spec)
    sr = voice.sample_rate
    lines, clips, t = [], [], LEAD
    for i, (caption, say, mode, target) in enumerate(ep.SCRIPT):
        pieces = say if isinstance(say, (list, tuple)) else [(say or caption, 0.0)]
        # named by what's said, so adding or removing a line never reuses the wrong recording
        key = hashlib.sha1(repr((spec, pieces)).encode()).hexdigest()[:10]
        wav = out / "voice" / f"{i:02d}_{key}.wav"
        legacy = out / "voice" / f"{i:02d}.wav"     # older runs named lines by number only
        if not wav.exists() and legacy.exists() and i < len(old.get("lines", [])) \
                and old["lines"][i]["text"] == caption and not isinstance(say, (list, tuple)):
            legacy.rename(wav)
        for stale in (out / "voice").glob(f"{i:02d}_*.wav"):
            if stale != wav: stale.unlink()
        if not wav.exists():   # re-runs only redo missing lines (delete a file to redo it)
            parts = []
            for text, pause in pieces:
                a = voice.say(text)
                s0, s1 = voiced_span(a, sr)
                parts += [a[max(0, int((s0 - 0.05) * sr)):int((s1 + 0.12) * sr)], np.zeros(int(pause * sr), np.float32)]
            a = np.concatenate(parts)
            with wave.open(str(wav), "wb") as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
                w.writeframes((np.clip(a, -1, 1) * 32767).astype("<i2").tobytes())
            print(f"line {i}: {len(a) / sr:.1f}s  {caption}", flush=True)
        with wave.open(str(wav)) as w:
            sr = w.getframerate()
            a = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32767
        speech = len(a) / sr
        dur = max(speech, MIN_DUR.get(mode, 0))
        words = caption.split()
        # where each piece is spoken (pieces are separated by silences)
        spans = speech_spans(a, sr, len(pieces))
        counts = [len(str(text).split()) for text, _ in pieces]
        if len(pieces) == 1 or sum(counts) != len(words) or len(spans) != len(pieces):
            spans, counts = [voiced_span(a, sr)], [len(words)]
        starts, ends, i = [], [], 0
        for (s0, s1), n in zip(spans, counts):
            ws = words[i:i + n]; i += n
            wt = np.array([len(w.strip(".,:?'!")) + 2.5 for w in ws], float)
            e = t + s0 + np.cumsum(wt) / wt.sum() * (s1 - s0)
            starts += [t + s0] + list(e[:-1]); ends += list(e)
        lines.append(dict(text=caption, mode=mode, target=target, t0=t, t1=t + dur + GAP, speech=speech,
                          words=[[w, float(a_), float(b_)] for w, a_, b_ in zip(words, starts, ends)]))
        clips.append((t, a))
        t += dur + GAP
    dur = t + 1.6
    lines[-1]["t1"] = dur
    for f in (out / "voice").glob("*.wav"):        # recordings no line uses any more
        if not any(f.name.startswith(f"{i:02d}_") for i in range(len(ep.SCRIPT))) or "_" not in f.stem:
            f.unlink()
    # the whole voice track at 48 kHz
    track = np.zeros(int(dur * SR_OUT) + SR_OUT, np.float32)
    for t0, a in clips:
        a48 = np.interp(np.arange(int(len(a) * SR_OUT / sr)) * sr / SR_OUT, np.arange(len(a)), a)
        o = int(t0 * SR_OUT); track[o:o + len(a48)] += a48
    with wave.open(str(out / "voice.wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR_OUT)
        w.writeframes((np.clip(track, -1, 1) * 32767).astype("<i2").tobytes())
    (out / "timing.json").write_text(json.dumps(dict(duration=dur, voice=spec, credit=voice.credit, lines=lines), indent=1))
    print(f"timing: {dur:.1f}s, {len(lines)} lines -> {out / 'timing.json'}")

if __name__ == "__main__":
    main()
