"""Đặc trưng dòng nhạc (Latin / regional mexicano) bằng CLAP + đo nhịp 2 hay 3. Chỉ là máy đo gần đúng, tai Duy quyết.
Chạy bằng python của Seed-VC (có torch + transformers):
  harness/tools/seed-vc/.venv/Scripts/python.exe tools/clap_check.py out.json file1 [file2 ...]
Mỗi file: % trung bình từng nhạc cụ (softmax trên nhóm nhạc cụ), % từng kiểu nhịp/điệu (softmax riêng), nhịp/phút,
và "nhịp 2 hay 3" (độ mạnh lặp lại của nhấn ở chu kỳ 2 phách so với 3 phách).
"""
import json
import sys

import librosa
import numpy as np
import torch
from transformers import ClapModel, ClapProcessor

INSTR = {
    "accordion": "a button accordion playing melody and fills",
    "bajo_sexto": "a bajo sexto, a twelve-string Mexican guitar strumming chords",
    "ac_guitar": "a nylon acoustic guitar",
    "elec_bass": "an electric bass guitar",
    "upright_bass": "an upright double bass tololoche",
    "drum_kit": "a drum kit with snare and hi-hat",
    "tuba_brass": "a tuba and brass band",
    "trumpets": "mariachi trumpets",
    "violin": "violins",
    "piano": "a piano",
    "synth": "an electronic synthesizer",
    "elec_guitar": "an electric guitar",
    "sax": "an alto saxophone playing a melody",
    "requinto": "a requinto guitar playing fast melodic lines",
    "voice_male": "a man singing in Spanish",
    "voice_duet": "two male voices singing in harmony",
}
STYLE = {
    "norteno": "norteño music from northern Mexico with accordion and bajo sexto",
    "ranchera": "a Mexican ranchera",
    "corrido": "a Mexican corrido",
    "polka": "a fast two-step polka rhythm",
    "waltz": "a waltz in three-four time",
    "bolero": "a slow romantic bolero",
    "cumbia": "a cumbia rhythm",
    "banda": "Mexican banda music with brass and tuba",
    "mariachi": "mariachi music",
    "sierreno": "sierreño music with requinto guitar and bajo sexto, no drums",
    "pop_ballad": "a pop ballad",
    "rock": "rock music",
}
SR = 48000
WIN, HOP = 10, 15


def meter(path):
    y, sr = librosa.load(path, sr=22050, mono=True)
    env = librosa.onset.onset_strength(y=y, sr=sr)
    tempo, beats = librosa.beat.beat_track(onset_envelope=env, sr=sr)
    bs = librosa.util.sync(env[None], beats, aggregate=np.max)[0]
    bs = (bs - bs.mean()) / (bs.std() + 1e-9)
    ac = {k: float(np.mean(bs[:-k] * bs[k:])) for k in (2, 3, 4)}
    return float(np.atleast_1d(tempo)[0]), ac


def main():
    out, files = sys.argv[1], sys.argv[2:]
    proc = ClapProcessor.from_pretrained("laion/clap-htsat-unfused")
    model = ClapModel.from_pretrained("laion/clap-htsat-unfused").eval()
    res = {}
    with torch.no_grad():
        te = {}
        for name, lab in (("instr", INSTR), ("style", STYLE)):
            t = proc(text=list(lab.values()), return_tensors="pt", padding=True)
            te[name] = torch.nn.functional.normalize(model.get_text_features(**t), dim=-1)
        for f in files:
            y, _ = librosa.load(f, sr=SR, mono=True)
            wins = [y[s:s + WIN * SR] for s in range(0, max(1, len(y) - WIN * SR), HOP * SR)]
            a = proc(audios=wins, sampling_rate=SR, return_tensors="pt")
            ae = torch.nn.functional.normalize(model.get_audio_features(**a), dim=-1)
            r = {}
            for name, lab in (("instr", INSTR), ("style", STYLE)):
                p = (ae @ te[name].T * 100).softmax(-1).mean(0).numpy()
                r[name] = {k: round(float(v) * 100, 1) for k, v in sorted(zip(lab, p), key=lambda x: -x[1])}
            bpm, ac = meter(f)
            r["bpm"], r["accent_period_corr"] = round(bpm, 1), {k: round(v, 3) for k, v in ac.items()}
            res[f] = r
            print(f.split("/")[-1].split("\\")[-1], json.dumps(r, ensure_ascii=False))
    open(out, "w", encoding="utf-8").write(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
