"""Căn beat YuE2 vào lưới phách của beat gốc (để giọng hát đặt lên không lệch). Chỉ cắt-ghép ở đầu cụm phách, KHÔNG kéo giãn/méo âm.
Dùng (.venv_tx): python tools/beat_align.py <beat_goc_cung_toc_do.wav> <beat_yue2.flac> <ra.wav> [--group 8]
Cách làm: so 2 bản theo nốt (chroma) + tiếng gõ (onset) bằng DTW -> biết giây t của bản gốc ứng với giây nào của bản YuE2;
chia bản gốc thành cụm `group` phách; mỗi cụm lấy đúng đoạn YuE2 tương ứng, đặt vào đúng giờ của bản gốc, nối mềm 20 ms ngay trước phách.
In ra: độ lệch trước/sau theo từng 20 s (ms), độ nhảy lớn nhất ở chỗ nối (ms).
"""
import argparse
import json

import librosa
import numpy as np
import soundfile as sf

SR_A = 22050
HOP = 512


def load(path, sr):
    y, s = sf.read(path, always_2d=True)
    y = y.T
    if s != sr:
        y = librosa.resample(y, orig_sr=s, target_sr=sr)
    return y


def feats(m):
    c = librosa.feature.chroma_cqt(y=m, sr=SR_A, hop_length=HOP)
    o = librosa.onset.onset_strength(y=m, sr=SR_A, hop_length=HOP)[None, :]
    o = o / (o.max() + 1e-9)
    n = min(c.shape[1], o.shape[1])
    return np.vstack([c[:, :n], 2.0 * o[:, :n]])


def lag_report(a, b, fps, win=20.0):
    """Độ lệch theo từng cửa sổ: tương quan tiếng gõ, lag trong ±300 ms."""
    out = []
    w = int(win * fps)
    L = int(0.3 * fps)
    for s in range(0, min(len(a), len(b)) - w, w):
        x = a[s:s + w]
        best = max(range(-L, L + 1), key=lambda l: float(np.dot(x, b[s + l:s + l + w])) if 0 <= s + l and s + l + w <= len(b) else -1e9)
        out.append(int(best / fps * 1000))
    return out


def onset_env(m):
    e = librosa.onset.onset_strength(y=m, sr=SR_A, hop_length=128)
    return (e - e.mean()) / (e.std() + 1e-9)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ref"); ap.add_argument("src"); ap.add_argument("out")
    ap.add_argument("--group", type=int, default=4, help="số phách mỗi cụm")
    ap.add_argument("--xfade-ms", type=float, default=20.0)
    a = ap.parse_args()

    sr = sf.info(a.src).samplerate
    src = load(a.src, sr)
    ref_m = load(a.ref, SR_A).mean(0)
    src_m = librosa.resample(src.mean(0), orig_sr=sr, target_sr=SR_A)

    F_ref, F_src = feats(ref_m), feats(src_m)
    D, wp = librosa.sequence.dtw(X=F_ref, Y=F_src, metric="cosine", global_constraints=True, band_rad=0.1)
    wp = wp[::-1]
    t_ref = wp[:, 0] * HOP / SR_A
    t_src = wp[:, 1] * HOP / SR_A
    # hàm giờ-gốc -> giờ-YuE2 (lấy trung vị cho mỗi khung gốc, rồi làm trơn)
    uniq = np.unique(wp[:, 0])
    tr = uniq * HOP / SR_A
    ts = np.array([np.median(t_src[wp[:, 0] == u]) for u in uniq])
    # YuE2 giữ tốc độ bản nốt -> giờ YuE2 ~ a + b*giờ gốc. Khớp thẳng (bỏ điểm nhiễu), rồi chỉ sửa phần lệch ỔN ĐỊNH (lọc trung vị 10 s:
    # giữ được bước nhảy khi YuE2 thêm/bớt ô nhịp, bỏ các cú nhảy nhầm sang ô nhịp bên cạnh của DTW)
    keep = np.ones(len(tr), bool)
    for _ in range(4):
        b_, a_ = np.polyfit(tr[keep], ts[keep], 1)
        res = ts - (a_ + b_ * tr)
        keep = np.abs(res - np.median(res[keep])) < 0.25
    from scipy.ndimage import median_filter
    win = int(10.0 * SR_A / HOP) | 1
    r_med = median_filter(res, size=win, mode="nearest")
    ts_s = a_ + b_ * tr + r_med
    f = lambda t: float(np.interp(t, tr, ts_s))  # noqa: E731

    _, beats = librosa.beat.beat_track(y=ref_m, sr=SR_A, units="time", start_bpm=96, tightness=400)
    _, sbeats = librosa.beat.beat_track(y=src_m, sr=SR_A, units="time", start_bpm=96, tightness=400)
    per = float(np.median(np.diff(sbeats)))
    # ghép phách: phách gốc thứ i <-> phách YuE2 thứ i+k; k là số nguyên, chỉ đổi khi YuE2 thật sự hụt/thừa phách (lọc trung vị ~20 s)
    from scipy.ndimage import median_filter as _mf
    kk = np.array([int(np.argmin(np.abs(sbeats - f(t)))) - i for i, t in enumerate(beats)])
    kk = _mf(kk, size=33, mode="nearest")
    def src_beat(i):
        j = i + int(kk[min(i, len(kk) - 1)])
        return float(sbeats[j]) if 0 <= j < len(sbeats) else f(beats[min(i, len(beats) - 1)])
    pre = 0.03  # nối ngay trước phách để tiếng gõ không bị cắt
    idx = list(range(a.group, len(beats), a.group))
    cuts = [0.0] + [beats[i] - pre for i in idx]
    src_at = [max(0.0, src_beat(0) - beats[0])] + [src_beat(i) - pre for i in idx]
    ref_len = len(ref_m) / SR_A
    cuts.append(ref_len)

    # --- Tinh chỉnh vài nhóm phách ĐẦU BÀI (lỗi "vài giây đầu nghe như đánh sai"): bản nốt SheetSage thường đặt nốt đầu trễ ~1 phách,
    # nên thử dời điểm lấy mẫu của từng nhóm đầu trong ±1 phách, chọn chỗ tiếng gõ khớp bản gốc nhất (cắt-ghép, không kéo méo).
    e_r, e_s = onset_env(ref_m), onset_env(src_m); fps_e = SR_A / 128
    per = float(np.median(np.diff(sbeats)))
    refine = []
    for g in range(0):   # TẮT: tinh chỉnh đầu bài chưa đáng tin (chọn nhầm đỉnh 1 phách), xem lessons
        t0, t1 = cuts[g], cuts[g + 1]
        ar_ = e_r[int(t0 * fps_e):int(t1 * fps_e)]
        if len(ar_) < 20:
            refine.append(0); continue
        best = (-9.0, 0.0)
        for dlt in np.arange(-per * 1.1, per * 1.1, 0.01):
            s0 = src_at[g] + dlt
            if s0 < 0:
                continue
            bs_ = e_s[int(s0 * fps_e):int(s0 * fps_e) + len(ar_)]
            if len(bs_) < len(ar_):
                continue
            c = float(np.dot(ar_, bs_) / len(ar_))
            if c > best[0]:
                best = (c, float(dlt))
        src_at[g] += best[1]; refine.append(round(best[1] * 1000))
    n_doi_k = int(np.sum(np.diff(kk) != 0))

    xf = int(a.xfade_ms / 1000 * sr)
    out = np.zeros((src.shape[0], int(ref_len * sr) + xf + 1))
    jumps = []
    for i in range(len(cuts) - 1):
        t0, t1 = cuts[i], cuts[i + 1]
        s0 = max(0, int(src_at[i] * sr))
        n = int((t1 - t0) * sr) + xf
        seg = src[:, s0:s0 + n]
        if seg.shape[1] < n:
            seg = np.pad(seg, ((0, 0), (0, n - seg.shape[1])))
        if i > 0:
            ramp = np.linspace(0, 1, xf)
            seg[:, :xf] *= ramp
            out[:, int(t0 * sr):int(t0 * sr) + xf] *= (1 - ramp)
            prev_end = src_at[i - 1] + (t0 - cuts[i - 1])
            jumps.append(round((src_at[i] - prev_end) * 1000))
        o0 = int(t0 * sr)
        out[:, o0:o0 + n] += seg[:, :out.shape[1] - o0] if o0 + n > out.shape[1] else seg
    out = out[:, :int(ref_len * sr)]
    sf.write(a.out, out.T, sr, subtype="PCM_24")

    fps = SR_A / 128
    e_ref = onset_env(ref_m)
    before = lag_report(e_ref, onset_env(src_m), fps)
    after = lag_report(e_ref, onset_env(librosa.resample(out.mean(0), orig_sr=sr, target_sr=SR_A)), fps)
    print(json.dumps({"out": a.out, "lech_truoc_ms": before, "lech_sau_ms": after,
                      "lech_sau_max_ms": max(abs(x) for x in after) if after else None,
                      "nhay_cho_noi_max_ms": max((abs(j) for j in jumps), default=0), "nhay_cho_noi_p90_ms": int(np.percentile(np.abs(jumps), 90)) if jumps else 0, "so_cho_noi": len(jumps), "so_lan_yue2_hut_thua_phach": n_doi_k, "tinh_chinh_dau_bai_ms": refine,
                      "ti_le_toc_do": round(float(b_), 5), "lech_dau_s": round(float(a_), 3)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
