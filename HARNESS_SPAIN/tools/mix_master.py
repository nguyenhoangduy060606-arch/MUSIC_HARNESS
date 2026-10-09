"""Trộn vòng 4 Spain: beat YuE2 (đã căn bằng beat_align.py) + giọng ACE (đã làm sạch bằng vocal_clean.py). Không tự dời giờ: cả hai đã cùng lưới của bài gốc.
Khác mix.py: master -14 LUFS (không ép to -9.5 -> hết bè/rè ở chỗ to), giọng mượt (không đẩy 3 kHz, giảm chói 5 kHz / 9 kHz), beat bớt dải cao "sạn".
Dùng (.venv): python tools/mix_master.py --vocal V.wav --beat B.wav --out OUT [--vocal-db 1.5] [--lufs -14] [--ffmpeg ffmpeg]
"""
import argparse
import json
import subprocess

import numpy as np
import soundfile as sf
from pedalboard import Compressor, HighpassFilter, HighShelfFilter, PeakFilter, Pedalboard, Reverb

from mix import load, lufs, true_peak_db, true_peak_limit, SR


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vocal", required=True); ap.add_argument("--beat", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--vocal-db", type=float, default=1.5, help="giọng to hơn beat bao nhiêu LU")
    ap.add_argument("--lufs", type=float, default=-14.0)
    ap.add_argument("--target-bal", type=float, default=None, help="giọng − beat (dB RMS, khung có giọng) muốn đạt = mức của bản gốc; có thì bỏ qua --vocal-db")
    ap.add_argument("--duck-db", type=float, default=0.0, help="hạ beat bấy nhiêu dB khi có giọng (mượt 30/250 ms)")
    ap.add_argument("--ffmpeg", default="ffmpeg")
    a = ap.parse_args()

    vocal, beat = load(a.vocal), load(a.beat)
    n = max(len(vocal), len(beat))
    vocal = np.pad(vocal, ((0, n - len(vocal)), (0, 0)))
    beat = np.pad(beat, ((0, n - len(beat)), (0, 0)))

    v = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=90),
        PeakFilter(cutoff_frequency_hz=300, gain_db=-1.5, q=1.0),
        Compressor(threshold_db=-20, ratio=2.5, attack_ms=8, release_ms=120),
        PeakFilter(cutoff_frequency_hz=2500, gain_db=1.0, q=0.8),
        PeakFilter(cutoff_frequency_hz=5200, gain_db=-1.5, q=2.0),
        HighShelfFilter(cutoff_frequency_hz=9000, gain_db=-1.5),
    ])(vocal.T, SR).T
    verb = Pedalboard([Reverb(room_size=0.4, damping=0.65, wet_level=1.0, dry_level=0.0, width=0.9),
                       HighpassFilter(cutoff_frequency_hz=300)])(v.T, SR).T
    v = v + 0.12 * verb

    b = Pedalboard([
        HighpassFilter(cutoff_frequency_hz=30),
        PeakFilter(cutoff_frequency_hz=2500, gain_db=-2.0, q=0.8),
        HighShelfFilter(cutoff_frequency_hz=9000, gain_db=-2.0),
    ])(beat.T, SR).T

    import librosa
    from scipy.ndimage import uniform_filter1d
    hop = 512
    vm = v.mean(1); rv = librosa.feature.rms(y=vm, frame_length=2048, hop_length=hop)[0]; dbv = 20 * np.log10(rv + 1e-9)
    act = dbv > dbv.max() - 40
    def rms_act(x):
        fr = librosa.feature.rms(y=x.mean(1), frame_length=2048, hop_length=hop)[0][:len(act)]
        return 20 * np.log10(np.sqrt(np.mean(fr[act[:len(fr)]] ** 2)) + 1e-9)
    if a.target_bal is not None:
        v = v * (10 ** ((a.target_bal + rms_act(b) - rms_act(v)) / 20))
    else:
        v = v * (10 ** ((lufs(b) + a.vocal_db - lufs(v)) / 20))
    if a.duck_db > 0:
        g = np.where(act, -a.duck_db, 0.0).astype(float)
        g = uniform_filter1d(g, 3); g = np.minimum(g, uniform_filter1d(g, 12))      # vào nhanh ~30 ms, nhả chậm ~250 ms
        g = np.repeat(g, hop)[:len(b)]; g = np.pad(g, (0, max(0, len(b) - len(g))), constant_values=0.0)
        b = b * (10 ** (g / 20))[:, None]
    bal_out = round(float(rms_act(v) - rms_act(b)), 2)
    mix = Pedalboard([Compressor(threshold_db=-16, ratio=1.5, attack_ms=30, release_ms=200)])((v + b).T, SR).T
    gain_db = a.lufs - lufs(mix)
    pre = mix
    for _ in range(3):
        mix = true_peak_limit(pre * (10 ** (gain_db / 20)), ceiling_db=-1.0)
        miss = a.lufs - lufs(mix)
        if abs(miss) < 0.2:
            break
        gain_db += miss
    if true_peak_db(mix) > -1.0:
        mix = mix * (10 ** ((-1.0 - true_peak_db(mix)) / 20))
    sf.write(a.out + ".wav", mix, SR, subtype="PCM_24")
    subprocess.run([a.ffmpeg, "-v", "error", "-y", "-i", a.out + ".wav", "-b:a", "320k", a.out + ".mp3"], check=True)
    y = mix.mean(1)
    print(json.dumps({"out": a.out + ".mp3", "lufs": round(lufs(mix), 2), "true_peak": round(true_peak_db(mix), 2),
                      "gan_tran_pct": round(float(np.mean(np.abs(y) > 0.89 * np.abs(y).max()) * 100), 3),
                      "do_tho_db": round(float(20 * np.log10(np.abs(y).max() / np.sqrt(np.mean(y ** 2)))), 1), "bal_db": bal_out}, ensure_ascii=False, default=float))


if __name__ == "__main__":
    main()
