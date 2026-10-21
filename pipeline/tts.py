"""Text to speech for the narration, with any voice we use, by name.

A voice spec is "<engine>:<voice>":
  pocket:george                        Kyutai Pocket TTS preset (CC-BY-4.0 for VCTK voices, CC0 for Voice-Zero)
  kokoro:am_michael                    Kokoro (Apache-2.0)
  kokoro:am_michael*0.68+am_santa*0.32 a blend of Kokoro voices (weights are normalised)

Farmer Joe's voice (Oct 2026, Dean's pick): a blend of Kokoro michael and santa.
Run Python with -X utf8 on Windows (pocket_tts reads its config in the locale charset otherwise).
"""
import numpy as np

FARMER_JOE = "kokoro:am_michael*0.68+am_santa*0.32"

CREDITS = {
    "pocket": "Narration voice: Kyutai Pocket TTS, voice from the VCTK corpus (CC-BY-4.0).",
    "kokoro": "Narration voice: Kokoro TTS (Apache-2.0).",
}


class Voice:
    def __init__(self, spec: str):
        self.spec = spec
        self.engine, _, name = spec.partition(":")
        if self.engine == "pocket":
            from pocket_tts import TTSModel
            self.model = TTSModel.load_model()
            self.state = self.model.get_state_for_audio_prompt(name)
            self.sample_rate = self.model.sample_rate
        elif self.engine == "kokoro":
            from kokoro import KPipeline
            self.pipe = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M")
            parts = []
            for p in name.split("+"):
                v, _, w = p.partition("*")
                parts.append((self.pipe.load_single_voice(v.strip()), float(w or 1)))
            total = sum(w for _, w in parts)
            self.pack = sum(t * (w / total) for t, w in parts)
            self.sample_rate = 24000
        else:
            raise ValueError(f"unknown voice engine in {spec!r}")

    @property
    def credit(self) -> str:
        return CREDITS[self.engine]

    def say(self, text: str) -> np.ndarray:
        """Mono float32 audio at self.sample_rate."""
        if self.engine == "pocket":
            return self.model.generate_audio(self.state, text).detach().cpu().numpy().reshape(-1)
        return np.concatenate([a.numpy() for _, _, a in self.pipe(text, voice=self.pack, speed=1.0)]).astype(np.float32)
