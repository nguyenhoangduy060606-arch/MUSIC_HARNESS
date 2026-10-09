"""Whisper (large-v3-turbo, OFFLINE trong cache VM) chép lời KÈM GIỜ TỪNG TỪ. Chạy bằng venv lab:
python whisper_words.py <vocal.wav> <out.json> [lang=es]   -> [{"w": "...", "t0": s, "t1": s}, ...]"""
import json, os, sys
os.environ["HF_HUB_OFFLINE"] = "1"
sys.modules["torchcodec"] = None
import soundfile as sf, torch
from math import gcd
from scipy.signal import resample_poly
from transformers import pipeline
x, sr = sf.read(sys.argv[1], dtype="float32", always_2d=True)
g = gcd(sr, 16000); y = resample_poly(x.mean(1), 16000 // g, sr // g).astype("float32")
asr = pipeline("automatic-speech-recognition", model="openai/whisper-large-v3-turbo", torch_dtype=torch.float16, device="cuda")
r = asr({"raw": y, "sampling_rate": 16000}, return_timestamps="word", chunk_length_s=30,
        generate_kwargs={"language": sys.argv[3] if len(sys.argv) > 3 else "es", "task": "transcribe"})
out = [{"w": c["text"].strip(), "t0": c["timestamp"][0], "t1": c["timestamp"][1]} for c in r["chunks"]]
json.dump(out, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False)
print("words", len(out))
