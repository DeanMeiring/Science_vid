"""Make a narration sound cartoony: shift pitch and formants (the "size" of the speaker).

Usage: .venv/Scripts/python voice/cartoon.py in.wav [preset ...]   -> renders/voice_samples/cartoon_<preset>.wav
       .venv/Scripts/python voice/cartoon.py --samples              Episode 1's first lines in every preset,
                                                                     plus CARTOON_VOICES.mp3 to compare them
Uses ffmpeg's rubberband filter (good-quality pitch shifting) and runs in a second or two.
Works on any voice: george now, or a clone of Dean's own voice later.
"""
import subprocess, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "pipeline"))
from common import ROOT, ffmpeg

# semitones: pitch shift; formant: "shifted" moves the voice's resonances with the pitch (sounds like a
# smaller / bigger person: the cartoon effect), "preserved" keeps them (just higher / lower);
# tempo: speed without changing pitch
PRESETS = {
    "plain":       dict(semitones=0, formant="preserved", tempo=1.0),
    "toon_light":  dict(semitones=2, formant="shifted", tempo=1.04),    # subtle: still a narrator, a bit animated
    "chipper":     dict(semitones=4, formant="shifted", tempo=1.07),    # bright, bouncy cartoon character
    "little_joe":  dict(semitones=6, formant="shifted", tempo=1.08),    # small, squeaky (chipmunk-ish)
    "big_farmer":  dict(semitones=-3, formant="shifted", tempo=0.97),   # big, gruff, friendly farmer
}

def cartoon(src, dst, semitones=0, formant="shifted", tempo=1.0):
    pitch = 2 ** (semitones / 12)
    af = (f"rubberband=pitch={pitch:.5f}:tempo={tempo:.4f}:formant={formant}:pitchq=quality:transients=smooth,"
          "loudnorm=I=-16:TP=-1.5:LRA=11")
    subprocess.run([ffmpeg(), "-y", "-loglevel", "error", "-i", str(src), "-af", af, "-ar", "48000", str(dst)],
                   check=True)

def samples():
    out = ROOT / "renders" / "voice_samples"; out.mkdir(parents=True, exist_ok=True)
    src = ROOT / "renders" / "ep01_farm" / "voice.wav"
    clip = out / "_ep01_start.wav"     # the first ~16 s: intro and the rules
    subprocess.run([ffmpeg(), "-y", "-loglevel", "error", "-i", str(src), "-t", "16", str(clip)], check=True)
    files = []
    for name, p in PRESETS.items():
        dst = out / f"cartoon_{name}.wav"; cartoon(clip, dst, **p); files.append(dst)
        print("made", dst.name, flush=True)
    # all of them back to back, with a short pause between
    ins = sum((["-i", str(f)] for f in files), [])
    fl = "".join(f"[{i}]apad=pad_dur=1.0[a{i}];" for i in range(len(files)))
    fl += "".join(f"[a{i}]" for i in range(len(files))) + f"concat=n={len(files)}:v=0:a=1"
    subprocess.run([ffmpeg(), "-y", "-loglevel", "error", *ins, "-filter_complex", fl, "-b:a", "160k",
                    str(out / "CARTOON_VOICES.mp3")], check=True)
    clip.unlink()
    print("made CARTOON_VOICES.mp3:", " -> ".join(PRESETS))

if __name__ == "__main__":
    if sys.argv[1:2] == ["--samples"]:
        samples()
    else:
        src = Path(sys.argv[1])
        for name in sys.argv[2:] or list(PRESETS):
            dst = ROOT / "renders" / "voice_samples" / f"cartoon_{name}.wav"
            dst.parent.mkdir(parents=True, exist_ok=True)
            cartoon(src, dst, **PRESETS[name]); print("made", dst)
