"""Narrate an episode in its voice and work out the timing of every line.

Usage: .venv/Scripts/python pipeline/voice.py episodes/ep01_farm.py
Writes renders/<episode>/voice/NN.wav, voice.wav (the whole track) and timing.json.

The voice is the episode's VOICE (a pipeline/tts.py spec); without one it's Farmer Joe's
blend of Kokoro michael and santa. Changing the voice redoes every line.

Each line's real length sets how long the simulation spends on it. Caption words are
spread over the spoken part of the line by word length (a Whisper alignment can
replace this later, as in CLIPPER's longform_beats).
"""
import json, os, subprocess, sys, wave
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
MIN_DUR = {"single": 3.2, "land": 3.0}

def voiced_span(a, sr):
    """Start/end (s) of the part above the noise floor, so word timings ignore silence."""
    k = int(0.02 * sr)
    e = np.sqrt(np.convolve(a ** 2, np.ones(k) / k, "same"))
    on = np.nonzero(e > max(1e-4, e.max() * 0.05))[0]
    return (on[0] / sr, on[-1] / sr) if len(on) else (0.0, len(a) / sr)

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
        wav = out / "voice" / f"{i:02d}.wav"
        if not wav.exists():   # re-runs only redo missing lines (delete a file to redo it)
            a = voice.say(say or caption)
            s0, s1 = voiced_span(a, sr)
            a = a[max(0, int((s0 - 0.05) * sr)):int((s1 + 0.12) * sr)]
            with wave.open(str(wav), "wb") as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
                w.writeframes((np.clip(a, -1, 1) * 32767).astype("<i2").tobytes())
            print(f"line {i}: {len(a) / sr:.1f}s  {caption}", flush=True)
        with wave.open(str(wav)) as w:
            sr = w.getframerate()
            a = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32767
        speech = len(a) / sr
        dur = max(speech, MIN_DUR.get(mode, 0))
        s0, s1 = voiced_span(a, sr)
        words = caption.split()
        wt = np.array([len(w.strip(".,:?'")) + 2.5 for w in words], float)
        ends = t + s0 + np.cumsum(wt) / wt.sum() * (s1 - s0)
        starts = np.concatenate([[t + s0], ends[:-1]])
        lines.append(dict(text=caption, mode=mode, target=target, t0=t, t1=t + dur + GAP, speech=speech,
                          words=[[w, float(a_), float(b_)] for w, a_, b_ in zip(words, starts, ends)]))
        clips.append((t, a))
        t += dur + GAP
    dur = t + 1.6
    lines[-1]["t1"] = dur
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
