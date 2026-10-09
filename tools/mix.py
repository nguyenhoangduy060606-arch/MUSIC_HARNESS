"""Ghép giọng gốc (đã tách) lên beat mới, tự căn nhịp, xử lý giọng, master, đo lỗi.

Dùng:
  python mix.py --vocal V.wav --beat NEW_BEAT.wav --ref-beat ORIGINAL_BEAT.wav
                --vocal-offset-ms 8.3 --out OUT_BASENAME [--vocal-db 1.0] [--lufs -10]
--vocal-offset-ms: độ trễ của beat gốc so với bài gốc (đo bằng align_check.py).
In ra JSON báo cáo QC.
"""
import argparse
import json
import subprocess

import librosa
import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from pedalboard import (Compressor, Distortion, Gain, HighpassFilter, HighShelfFilter,
                        Limiter, LowShelfFilter, PeakFilter, Pedalboard, Reverb)
from scipy.signal import resample_poly

SR = 44100


def load(path):
    y, sr = sf.read(path, always_2d=True)
    if sr != SR:
        y = resample_poly(y, SR, sr, axis=0)
    if y.shape[1] == 1:
        y = np.repeat(y, 2, axis=1)
    return y[:, :2].astype(np.float32)


def onset_env(y_stereo):
    mono = librosa.to_mono(y_stereo.T)
    return librosa.onset.onset_strength(y=mono, sr=SR, hop_length=256)


def xcorr_lag(a, b, max_lag):
    """Lag (frames) maximizing corr(a[t+lag], b[t])."""
    a = (a - a.mean()) / (a.std() + 1e-9)
    b = (b - b.mean()) / (b.std() + 1e-9)
    best, best_lag = -1e9, 0
    for lag in range(-max_lag, max_lag + 1):
        if lag >= 0:
            x, y = a[lag:], b[:len(b) - lag] if lag else b
        else:
            x, y = a[:lag], b[-lag:]
        n = min(len(x), len(y))
        c = float(np.dot(x[:n], y[:n]) / n)
        if c > best:
            best, best_lag = c, lag
    return best_lag, best


def timing_report(new_beat, ref_beat):
    hop_ms = 256 / SR * 1000
    ea, eb = onset_env(new_beat), onset_env(ref_beat)
    lag, corr = xcorr_lag(ea, eb, max_lag=int(200 / hop_ms))
    win = int(20000 / hop_ms)
    drift = []
    for s in range(0, min(len(ea), len(eb)) - win, win):
        l, c = xcorr_lag(ea[s:s + win], eb[s:s + win], max_lag=int(150 / hop_ms))
        drift.append({"t_s": round(s * hop_ms / 1000), "lag_ms": round(float(l * hop_ms), 1), "corr": round(float(c), 2)})
    return round(float(lag * hop_ms), 1), round(float(corr), 2), drift


def shift(y, ms):
    n = int(round(ms / 1000 * SR))
    if n > 0:
        return np.concatenate([np.zeros((n, 2), np.float32), y])
    if n < 0:
        return y[-n:]
    return y


def true_peak_limit(x, ceiling_db=-1.0, lookahead_ms=3.0, release_ms=80.0, block=64):
    """Lookahead limiter dựa trên đỉnh oversample 4x (true peak)."""
    from scipy.ndimage import minimum_filter1d
    ceiling = 10 ** (ceiling_db / 20)
    up = np.abs(resample_poly(x, 4, 1, axis=0)).max(axis=1)
    n = len(x)
    up = np.pad(up, (0, max(0, 4 * n - len(up))))[:4 * n]
    peak = up.reshape(n, 4).max(axis=1)
    gain = np.minimum(1.0, ceiling / (peak + 1e-12))
    nb = int(np.ceil(n / block))
    g = np.pad(gain, (0, nb * block - n), constant_values=1.0).reshape(nb, block).min(axis=1)
    la = max(1, int(lookahead_ms / 1000 * SR / block))
    g = minimum_filter1d(g, size=2 * la + 1)
    coef = 1 - np.exp(-block / (release_ms / 1000 * SR))
    out = np.empty_like(g)
    prev = 1.0
    for i, gi in enumerate(g):
        prev = min(gi, prev + (1 - prev) * coef)
        out[i] = prev
    centers = (np.arange(nb) + 0.5) * block
    gs = np.interp(np.arange(n), centers, out)
    return (x * gs[:, None]).astype(np.float32)


def lufs(y):
    return pyln.Meter(SR).integrated_loudness(y.astype(np.float64))


def true_peak_db(y):
    up = resample_poly(y, 4, 1, axis=0)
    return 20 * np.log10(np.max(np.abs(up)) + 1e-12)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vocal", required=True)
    ap.add_argument("--beat", required=True)
    ap.add_argument("--ref-beat", required=True)
    ap.add_argument("--vocal-offset-ms", type=float, default=0.0)
    ap.add_argument("--vocal-db", type=float, default=1.0, help="vocal LUFS minus beat LUFS")
    ap.add_argument("--lufs", type=float, default=-9.5)
    ap.add_argument("--style", choices=["rock", "acoustic", "pop"], default="rock",
                    help="rock: giọng hơi gắt; acoustic: giọng mộc, vang hơn")
    ap.add_argument("--out", required=True)
    ap.add_argument("--ffmpeg", default="ffmpeg")
    a = ap.parse_args()

    vocal, beat, ref = load(a.vocal), load(a.beat), load(a.ref_beat)

    # 1) căn nhịp: beat mới so với beat gốc, rồi cộng độ trễ beat gốc so với bài gốc
    beat_lag_ms, beat_corr, drift = timing_report(beat, ref)
    vocal = shift(vocal, a.vocal_offset_ms + beat_lag_ms)

    n = max(len(vocal), len(beat))
    vocal = np.pad(vocal, ((0, n - len(vocal)), (0, 0)))
    beat = np.pad(beat, ((0, n - len(beat)), (0, 0)))

    # 2) xử lý giọng cho chất trap rock: sạch, chắc, hơi gắt nhẹ
    vchain = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=110),
        PeakFilter(cutoff_frequency_hz=300, gain_db=-2.0, q=1.0),
        Compressor(threshold_db=-22, ratio=3.5, attack_ms=4, release_ms=90),
        PeakFilter(cutoff_frequency_hz=3200, gain_db=2.0, q=0.9),
        HighShelfFilter(cutoff_frequency_hz=9000, gain_db=1.0),
    ])
    v = vchain(vocal.T, SR).T
    if a.style == "rock":
        grit = Pedalboard([HighpassFilter(cutoff_frequency_hz=600), Distortion(drive_db=10), Gain(-18)])(vocal.T, SR).T
        v = v + grit  # parallel saturation, rất nhẹ
    room = 0.28 if a.style == "rock" else 0.4
    verb = Pedalboard([Reverb(room_size=room, damping=0.6, wet_level=1.0, dry_level=0.0, width=0.9),
                       HighpassFilter(cutoff_frequency_hz=300)])(v.T, SR).T
    v = v + (0.07 if a.style == "rock" else 0.1) * verb

    # 3) beat: nhường chỗ cho giọng ở dải 1.5–4 kHz
    bchain = Pedalboard([
        PeakFilter(cutoff_frequency_hz=2500, gain_db=-2.5, q=0.8),
        LowShelfFilter(cutoff_frequency_hz=80, gain_db=0.5),
    ])
    b = bchain(beat.T, SR).T

    # 4) cân bằng giọng/beat theo loudness
    lb, lv = lufs(b), lufs(v)
    v = v * (10 ** ((lb + a.vocal_db - lv) / 20))
    mix = v + b

    # 5) master
    mix = Pedalboard([Compressor(threshold_db=-14, ratio=2.0, attack_ms=20, release_ms=150)])(mix.T, SR).T
    pre = mix
    gain_db = a.lufs - lufs(pre)
    for _ in range(3):  # limiter làm tụt loudness một chút -> bù lại tối đa 3 lần
        mix = true_peak_limit(pre * (10 ** (gain_db / 20)), ceiling_db=-1.0)
        miss = a.lufs - lufs(mix)
        if abs(miss) < 0.2:
            break
        gain_db += miss
    if true_peak_db(mix) > -1.0:
        mix = mix * (10 ** ((-1.0 - true_peak_db(mix)) / 20))

    wav = a.out + ".wav"
    sf.write(wav, mix, SR, subtype="PCM_24")
    subprocess.run([a.ffmpeg, "-v", "error", "-y", "-i", wav, "-b:a", "320k", a.out + ".mp3"], check=True)

    report = {
        "out": a.out + ".mp3",
        "beat_offset_vs_source_ms": beat_lag_ms,
        "beat_rhythm_similarity": beat_corr,
        "drift_max_ms": max((abs(d["lag_ms"]) for d in drift), default=0.0),
        "drift": drift,
        "lufs": round(lufs(mix), 2),
        "true_peak_dbtp": round(true_peak_db(mix), 2),
        "clipped_samples": int(np.sum(np.abs(mix) >= 0.999)),
        "vocal_minus_beat_lufs": a.vocal_db,
    }
    print(json.dumps(report, ensure_ascii=False, default=float))


if __name__ == "__main__":
    main()
