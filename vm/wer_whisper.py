"""Độ rõ lời: Whisper nghe bản vocal rồi so với lời gốc (WER, 0 = đúng hết). python wer_whisper.py <lyrics.txt> <a.flac> ...  (WER_LANG=es cho tiếng Tây Ban Nha; mặc định en)"""
import os, re, sys, unicodedata
LANG = os.environ.get("WER_LANG", "en")
os.environ["HF_HUB_OFFLINE"] = "1"; sys.modules["torchcodec"] = None
import soundfile as sf, torch
from math import gcd
from scipy.signal import resample_poly
from transformers import pipeline
asr = pipeline("automatic-speech-recognition", model="openai/whisper-large-v3-turbo", torch_dtype=torch.float16, device="cuda")
deacc = lambda s: "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))
norm = lambda s: re.sub(r"[^a-z' ]", " ", deacc(re.sub(r"\[[^\]]*\]", " ", s.lower()))).split()
ref = norm(open(sys.argv[1], encoding="utf-8").read())
def wer(r, h):
    d = list(range(len(h) + 1))
    for i in range(1, len(r) + 1):
        p, d[0] = d[0], i
        for j in range(1, len(h) + 1):
            p, d[j] = d[j], min(d[j] + 1, d[j - 1] + 1, p + (r[i - 1] != h[j - 1]))
    return d[len(h)] / len(r)
for f in sys.argv[2:]:
    x, sr = sf.read(f, dtype="float32", always_2d=True); g = gcd(sr, 16000)
    y = resample_poly(x.mean(1), 16000 // g, sr // g).astype("float32")
    t = asr({"raw": y, "sampling_rate": 16000}, return_timestamps=True, chunk_length_s=30, generate_kwargs={"language": LANG, "task": "transcribe"})["text"]
    print(os.path.basename(f), "WER", round(wer(ref, norm(t)), 2), "| số từ nghe được", len(norm(t)), "/", len(ref), flush=True)
