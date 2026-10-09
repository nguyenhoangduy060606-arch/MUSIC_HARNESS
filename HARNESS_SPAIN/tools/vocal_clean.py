"""Làm sạch lớp xì nền của giọng ACE (đo 2026-10-07: chỗ không hát còn -24..-28 dB, giọng gốc -43..-48 dB).
Dùng (.venv): python tools/vocal_clean.py <giong_ace.flac> <giong_nguon_cung_gio.wav> <ra.wav> [do_loc_tren_4kHz=1.5]
1) Biết chính xác chỗ ca sĩ hát từ giọng nguồn (cùng giờ với bản ACE, tự đo độ lệch) -> chỗ không hát hạ 30 dB (mở/đóng mềm, giữ hơi thở 0.2 s).
2) Chỗ đang hát: lọc xì nhẹ theo phổ (mẫu xì lấy ở chỗ không hát), có sàn -14 dB để giọng không bị "nước".
In ra: độ lệch nguồn/ACE (ms), nền trước/sau (dB, cùng cách đo với bảng chẩn đoán).
"""
import json
import sys

import librosa
import numpy as np
import soundfile as sf
from scipy.ndimage import maximum_filter1d, uniform_filter1d


def floor_db(y):
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=512))
    rms = np.sqrt((S ** 2).mean(0))
    return round(float(20 * np.log10(np.percentile(rms, 5) / (np.percentile(rms, 95) + 1e-12))), 1)


def main():
    ace_p, src_p, out_p = sys.argv[1:4]
    hf = float(sys.argv[4]) if len(sys.argv) > 4 else 1.5  # độ lọc xì dải trên 4 kHz (1.5 = như dải dưới)
    y, sr = sf.read(ace_p, always_2d=True); y = y.T
    s, ss = sf.read(src_p, always_2d=True); s = s.mean(1)
    s = librosa.resample(s, orig_sr=ss, target_sr=sr) if ss != sr else s
    m = y.mean(0)

    hop = int(0.01 * sr)
    def env(x):
        return np.sqrt(uniform_filter1d(x ** 2, hop)[::hop] + 1e-12)
    ea, es = env(m), env(s)
    n = min(len(ea), len(es))
    la, ls = np.log(ea[:n]), np.log(es[:n])
    la, ls = (la - la.mean()) / la.std(), (ls - ls.mean()) / ls.std()
    lags = range(-30, 31)
    lag = max(lags, key=lambda l: float(np.mean(la[max(0, l):n + min(0, l)] * ls[max(0, -l):n - max(0, l)])))
    # giọng nguồn dời theo ACE
    es = np.roll(es, lag)

    db = 20 * np.log10(es / es.max())
    thr = np.percentile(db[db > -80], 90) - 28
    active = db > thr
    active = maximum_filter1d(active.astype(float), size=31) > 0  # giữ ±0.15 s quanh chỗ hát (hơi thở, lệch nhỏ)
    g_db = np.where(active, 0.0, -30.0)
    g_db = uniform_filter1d(g_db, 5)  # mở/đóng ~50 ms
    g = 10 ** (np.repeat(g_db, hop)[:y.shape[1]] / 20)
    g = np.pad(g, (0, max(0, y.shape[1] - len(g))), constant_values=g[-1])

    # lọc xì theo phổ
    N_FFT, H = 2048, 512
    out = []
    act_f = np.repeat(active, hop)[::H]
    for ch in y:
        X = librosa.stft(ch, n_fft=N_FFT, hop_length=H)
        A = np.abs(X)
        af = act_f[:A.shape[1]]
        af = np.pad(af, (0, A.shape[1] - len(af)), constant_values=False)
        noise = np.median(A[:, ~af], axis=1, keepdims=True) if (~af).sum() > 50 else np.percentile(A, 10, axis=1, keepdims=True)
        fr = librosa.fft_frequencies(sr=sr, n_fft=N_FFT)[:, None]
        alpha = np.where(fr > 4000, hf, 1.5)
        mask = np.clip(1 - alpha * noise / (A + 1e-9), np.where(fr > 4000, 0.12, 0.2), 1.0)
        mask = uniform_filter1d(uniform_filter1d(mask, 3, axis=1), 3, axis=0)
        z = librosa.istft(X * mask, hop_length=H, length=len(ch))
        out.append(z * g[:len(z)])
    out = np.array(out)
    sf.write(out_p, out.T, sr, subtype="PCM_24")
    print(json.dumps({"out": out_p, "lech_nguon_ace_ms": lag * 10, "nen_truoc_db": floor_db(m), "nen_sau_db": floor_db(out.mean(0)),
                      "ty_le_cho_hat": round(float(active.mean()), 2)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
