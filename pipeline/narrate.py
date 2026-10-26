"""Voice an episode's NARRATION as one flowing track, so Dean can hear it before anything is animated.

Usage: .venv/Scripts/python pipeline/narrate.py episodes/ep03_sheep.py
Writes renders/<episode>/narration_flow.wav (the whole script in one go) and
narration_beats.wav (each beat voiced on its own, joined with short natural pauses).

Episode 2's voice step made every sentence separately and padded it with silence, which
sounded choppy (Dean). Here the voice runs on; the animation follows it afterwards.
"""
import subprocess, sys, wave
from pathlib import Path
import numpy as np

if not sys.flags.utf8_mode:   # pocket_tts reads its config in the locale charset on Windows and breaks
    sys.exit(subprocess.call([sys.executable, "-X", "utf8", *sys.argv]))

import torch
torch.set_num_threads(4)   # keep the laptop usable
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, load_episode, load_env
from tts import FARMER_JOE, Voice

BEAT_GAP = 0.35            # pause between beats in the "beats" version

def trim(a, sr):
    """Cut leading/trailing silence, keeping a hair of air."""
    k = int(0.02 * sr)
    e = np.sqrt(np.convolve(a ** 2, np.ones(k) / k, "same"))
    on = np.nonzero(e > max(1e-4, e.max() * 0.05))[0]
    return a[max(0, on[0] - int(0.05 * sr)):on[-1] + int(0.12 * sr)] if len(on) else a

def write(path, a, sr):
    a = a / (np.abs(a).max() + 1e-9) * 0.9
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((np.clip(a, -1, 1) * 32767).astype("<i2").tobytes())

def main():
    ep_path = Path(sys.argv[1]); ep = load_episode(ep_path); load_env()
    out = ROOT / "renders" / ep_path.stem; out.mkdir(parents=True, exist_ok=True)
    voice = Voice(getattr(ep, "VOICE", FARMER_JOE)); sr = voice.sample_rate
    spoken = [say or caption for _, caption, say in ep.NARRATION]
    flow = trim(voice.say(" ".join(spoken)), sr)                      # the whole script in one go
    write(out / "narration_flow.wav", flow, sr)
    gap = np.zeros(int(BEAT_GAP * sr), np.float32)
    beats = np.concatenate([np.concatenate([trim(voice.say(t), sr), gap]) for t in spoken])[:-len(gap)]
    write(out / "narration_beats.wav", beats, sr)
    words = sum(len(t.split()) for t in spoken)
    print(f"flow:  {len(flow) / sr:.1f}s  ({words / (len(flow) / sr):.1f} words/s)")
    print(f"beats: {len(beats) / sr:.1f}s")
    print("->", out)

if __name__ == "__main__":
    main()
