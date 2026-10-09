"""Độ giống giọng (người nói) so với giọng gốc: cosine embedding Resemblyzer, 0..1 (cùng người thường > 0.85). Chỉ là bộ lọc.
Chạy trên VM bằng venv có resemblyzer (C:/claude_work/vocal/soulx):  python spk_sim.py <giong_goc.wav> <a.flac> [<b> ...]
Chỉ lấy các đoạn có hát (preprocess_wav cắt lặng). Bản có nhạc nền sẽ cho số thấp hơn thật: so bản a cappella là chuẩn nhất."""
import sys
import numpy as np
from resemblyzer import VoiceEncoder, preprocess_wav
enc = VoiceEncoder(device="cuda")
ref = enc.embed_utterance(preprocess_wav(sys.argv[1]))
for f in sys.argv[2:]:
    e = enc.embed_utterance(preprocess_wav(f))
    print(f.replace("\\", "/").split("/")[-1], "giong_giong_goc", round(float(np.dot(ref, e) / np.linalg.norm(ref) / np.linalg.norm(e)), 3), flush=True)
