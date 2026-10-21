"""Say the same narration in several free AI voices, so Dean can pick one.

Usage: .venv/Scripts/python voice/samples.py            -> renders/voice_samples/*.wav
       .venv/Scripts/python voice/samples.py --farmer   -> renders/voice_samples/farmer/*.wav (deep / older male voices)

Kokoro (Apache-2.0) and Kyutai Pocket TTS preset voices (CC-BY-4.0), both on CPU.
Numbers are spelled out for the voice; captions keep digits.
"""
import os, subprocess, sys, time, wave
from pathlib import Path

if not sys.flags.utf8_mode:   # pocket_tts reads its config in the locale charset on Windows and breaks
    sys.exit(subprocess.call([sys.executable, "-X", "utf8", *sys.argv]))
import numpy as np
import torch

torch.set_num_threads(4)   # keep the laptop usable
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "renders" / "voice_samples"
OUT.mkdir(parents=True, exist_ok=True)
for line in (ROOT / ".env").read_text().splitlines() if (ROOT / ".env").exists() else []:
    k, _, v = line.partition("=")
    if k.strip() and v.strip(): os.environ.setdefault(k.strip(), v.strip())

TEXT = ("Experiment number one. Put a farmer on a field of grass. "
        "On grass, he turns right and digs it into dirt. "
        "On dirt, he turns left, and the grass grows back. "
        "For thousands of steps, it's just a mess. "
        "Until step nine thousand, nine hundred and seventy-seven.")

KOKORO = [("af_heart", "a"), ("am_michael", "a"), ("bf_emma", "b"), ("bm_george", "b")]
POCKET = ["alba", "george", "jane", "michael"]

# --farmer: natural deep / older male voices for Farmer Joe (no pitch tricks)
FARMER_TEXT = ("Well howdy. Meet Farmer Joe. He's standing on a field of grass. "
               "On grass, he turns right. On dirt, he turns left. "
               "That's it. Two rules. Now let's speed it up.")
FARMER_KOKORO = [("am_santa", "a"), ("am_onyx", "a"), ("am_fenrir", "a"), ("am_puck", "a"), ("am_eric", "a"),
                 ("am_michael", "a")]
FARMER_POCKET = ["bill_boerst", "peter_yearsley", "stuart_bell", "marius", "javert", "paul"]

def write(path, audio, sr):
    pcm = np.clip(np.asarray(audio, np.float32).reshape(-1), -1, 1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
        w.writeframes((pcm * 32767).astype("<i2").tobytes())

only = set(a for a in sys.argv[1:] if not a.startswith("--"))
if "--farmer" in sys.argv:
    TEXT, KOKORO, POCKET = FARMER_TEXT, FARMER_KOKORO, FARMER_POCKET
    OUT = OUT / "farmer"; OUT.mkdir(parents=True, exist_ok=True)
from kokoro import KPipeline
pipes = {}
for voice, lang in KOKORO:
    if only and voice not in only: continue
    t0 = time.time()
    pipes.setdefault(lang, KPipeline(lang_code=lang, repo_id="hexgrad/Kokoro-82M"))
    audio = np.concatenate([a.numpy() for _, _, a in pipes[lang](TEXT, voice=voice, speed=1.0)])
    write(OUT / f"kokoro_{voice}.wav", audio, 24000)
    print(f"kokoro {voice}: {len(audio) / 24000:.1f}s audio in {time.time() - t0:.1f}s", flush=True)

from pocket_tts import TTSModel
model = TTSModel.load_model()
for voice in POCKET:
    if only and voice not in only: continue
    t0 = time.time()
    state = model.get_state_for_audio_prompt(voice)
    audio = model.generate_audio(state, TEXT).detach().cpu().numpy()
    write(OUT / f"pocket_{voice}.wav", audio, model.sample_rate)
    print(f"pocket {voice}: {audio.size / model.sample_rate:.1f}s audio in {time.time() - t0:.1f}s", flush=True)
