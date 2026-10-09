"""Đưa giọng gốc về ĐÚNG GIỜ của một bản khác (vd beat Suno) rồi dời cung. Bản ra còn tiếng "máy" của WORLD: đưa qua ACE cover (k 0.1) để hát lại tự nhiên.
Dùng (.venv_tx, cần pyworld):
  python tools/vocal_warp.py <giong_goc.wav> <giong_khuon.wav> <ra.wav> [--semis -0.5] [--end 178]
- <giong_goc>: giọng muốn dùng (vd giọng ca sĩ gốc). <giong_khuon>: giọng đã khớp beat đích (vd giọng Suno), chỉ để lấy GIỜ từng chữ.
- DTW (chroma + MFCC) cho đường ghép giờ; làm trơn; WORLD (f0, phổ, độ khàn) nội suy theo đường đó -> chữ nào ở giờ nào của khuôn thì giọng gốc hát chữ đó ở giờ đó.
- --semis: dời cung (nửa cung, có thể lẻ). --end: giây cuối của khuôn (cắt đuôi + fade 0.5 s), mặc định hết khuôn.
In JSON: độ lệch trung vị giữa đường ghép và các mốc chữ (nếu có --anchors file JSON [[t_goc, t_khuon], ...]).
"""
import argparse
import json

import librosa
import numpy as np
import pyworld as pw
import soundfile as sf
from scipy.ndimage import median_filter, uniform_filter1d

SR = 22050
HOP = 512


def mono(p, sr):
    y, s = sf.read(p, always_2d=True)
    y = y.mean(1)
    return librosa.resample(y, orig_sr=s, target_sr=sr) if s != sr else y


def feats(y):
    c = librosa.feature.chroma_cqt(y=y, sr=SR, hop_length=HOP)
    m = librosa.feature.mfcc(y=y, sr=SR, n_mfcc=13, hop_length=HOP)[1:]
    m = (m - m.mean(1, keepdims=True)) / (m.std(1, keepdims=True) + 1e-6)
    return np.vstack([c / (np.linalg.norm(c, axis=0, keepdims=True) + 1e-9) * 2.0, m * 0.35])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("mold"); ap.add_argument("out")
    ap.add_argument("--semis", type=float, default=0.0)
    ap.add_argument("--end", type=float, default=None)
    ap.add_argument("--anchors", default=None)
    a = ap.parse_args()

    ys, ym = mono(a.src, SR), mono(a.mold, SR)
    D, wp = librosa.sequence.dtw(X=feats(ys), Y=feats(ym), metric="cosine", global_constraints=True, band_rad=0.15)
    wp = wp[::-1]
    t_src, t_mold = wp[:, 0] * HOP / SR, wp[:, 1] * HOP / SR
    # với mỗi giờ khuôn: giờ nguồn trung vị; rồi làm trơn (0.4 s) để không giật
    grid = np.arange(0, len(ym) / SR, 0.005)
    uq = np.unique(wp[:, 1])
    tm = uq * HOP / SR
    ts = np.array([np.median(t_src[wp[:, 1] == u]) for u in uq])
    ts = np.maximum.accumulate(median_filter(ts, size=9, mode="nearest"))
    ts = uniform_filter1d(ts, 15, mode="nearest")
    ts = np.maximum.accumulate(ts)
    src_at = np.interp(grid, tm, ts)
    end = a.end or grid[-1]
    grid_n = int(end / 0.005)
    src_at = src_at[:grid_n]

    # WORLD trên giọng gốc (44.1 kHz nếu có)
    x, sr0 = sf.read(a.src, always_2d=True)
    x = x.mean(1).astype(np.float64)
    FP = 5.0
    f0, t = pw.dio(x, sr0, frame_period=FP)
    f0 = pw.stonemask(x, f0, t, sr0)
    sp = pw.cheaptrick(x, f0, t, sr0)
    ap_ = pw.d4c(x, f0, t, sr0)
    fi = np.clip(src_at / (FP / 1000.0), 0, len(t) - 1)
    i0 = np.floor(fi).astype(int); i1 = np.minimum(i0 + 1, len(t) - 1); w = (fi - i0)[:, None]
    sp_n = sp[i0] * (1 - w) + sp[i1] * w
    ap_n = ap_[i0] * (1 - w) + ap_[i1] * w
    v0, v1 = f0[i0] > 0, f0[i1] > 0
    f0_n = np.where(v0 & v1, np.exp(np.log(np.maximum(f0[i0], 1)) * (1 - w[:, 0]) + np.log(np.maximum(f0[i1], 1)) * w[:, 0]), np.where(w[:, 0] < 0.5, f0[i0], f0[i1]))
    f0_n = f0_n * 2 ** (a.semis / 12.0)
    y = pw.synthesize(np.ascontiguousarray(f0_n), np.ascontiguousarray(sp_n), np.ascontiguousarray(ap_n), sr0, FP)
    fade = int(0.5 * sr0)
    y[-fade:] *= np.linspace(1, 0, fade)
    y = y / (np.abs(y).max() + 1e-9) * 0.9
    sf.write(a.out, np.stack([y, y], 1), sr0, subtype="PCM_24")

    rep = {"out": a.out, "dur_s": round(len(y) / sr0, 1), "semis": a.semis,
           "ritmo_trung_vi": round(float(np.median(np.diff(src_at) / 0.005)), 3)}
    if a.anchors:
        pairs = json.load(open(a.anchors))
        err = [float(np.interp(tg, tm, ts) - tgs) for tg, tgs in [(m, s) for s, m in pairs]]
        rep["lech_moc_chu_giay_trung_vi"] = round(float(np.median(np.abs(err))), 2)
        rep["lech_moc_chu_max"] = round(float(np.max(np.abs(err))), 2)
        rep["moc_lech_hon_0.5s"] = [[round(m, 1), round(e, 1)] for (s_, m), e in zip(pairs, err) if abs(e) > 0.5][:20]
    print(json.dumps(rep, ensure_ascii=False, default=float))


if __name__ == "__main__":
    main()
