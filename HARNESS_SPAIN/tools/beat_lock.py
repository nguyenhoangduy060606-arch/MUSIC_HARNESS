"""Beat mới có khớp nhịp với nguồn không (để đặt giọng lên mà không lệch). Chỉ là bộ lọc.
Dùng (.venv_tx): python tools/beat_lock.py <nguon_beat.wav> <beat1.flac> [beat2 ...]
corr0 = tương quan nhịp gõ tại độ lệch 0 (khớp tốt > 0.3; < 0.1 = không khớp), lag = độ lệch tốt nhất (ms), iqr = độ tản của lệch từng phách (ms; khớp tốt < 60)."""
import sys, numpy as np, soundfile as sf, librosa
def load(p):
    y, sr = sf.read(p); y = y.mean(1) if y.ndim > 1 else y
    return librosa.resample(y, orig_sr=sr, target_sr=22050)
def env(y):
    e = librosa.onset.onset_strength(y=y, sr=22050, hop_length=110); return (e - e.mean()) / (e.std() + 1e-9)
ys = load(sys.argv[1]); b = env(ys); _, bb = librosa.beat.beat_track(y=ys, sr=22050, units="time")
for p in sys.argv[2:]:
    y = load(p); a = env(y); m = min(len(a), len(b))
    c = [float(np.mean(a[max(0, l):m + min(0, l)] * b[max(0, -l):m - max(0, l)])) for l in range(-60, 61)]
    _, ba = librosa.beat.beat_track(y=y, sr=22050, units="time")
    d = np.array([(x - bb[np.argmin(abs(bb - x))]) * 1000 for x in ba])
    print(p.replace("\\", "/").split("/")[-1], "corr0", round(c[60], 2), "lag", (int(np.argmax(c)) - 60) * 5, "iqr", round(float(np.percentile(d, 75) - np.percentile(d, 25))), flush=True)
