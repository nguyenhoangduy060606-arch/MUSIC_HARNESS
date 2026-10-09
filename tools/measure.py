"""Đo âm thanh cho harness_spain (chạy bằng env 'tx': librosa, soundfile, pyworld). Chỉ in JSON. Chỉ là bộ lọc (R8).
  facts   <inst.wav> <vocals.wav> <out.json>
  ref     <inst.wav> <semis> <ratio> <out.wav>            beat gốc đã dời cung/đổi tốc độ = "lưới chuẩn" của cả bài
  beatrow <ref.wav> <aligned.wav> <raw.flac> <sections.json>
  vocalrow <src_vocal.wav> <clean.wav>
  introrow <ref.wav> <aligned_intro.wav> <t_end>   độ trùng nốt mở đầu với bản gốc (top-2 nốt/khung 0.6 s → t_end)
  splicet  <ref.wav> <t_target>                    giờ của phách (bản gốc) gần nhất, không quá t_target
"""
import json
import sys

import librosa
import numpy as np
import soundfile as sf

SR = 22050


def mono(p, sr=SR):
    y, s = sf.read(p, always_2d=True)
    y = y.mean(1)
    return librosa.resample(y, orig_sr=s, target_sr=sr) if s != sr else y


def first_onset(y):
    """Giờ của nốt đầu tiên nghe thấy (bỏ tiếng nhỏ hơn đỉnh 35 dB)."""
    rms = librosa.feature.rms(y=y[:SR * 10], hop_length=256)[0]
    db = 20 * np.log10(rms + 1e-9)
    on = librosa.onset.onset_detect(y=y[:SR * 10], sr=SR, hop_length=256, units="frames")
    for f in on:
        if db[min(f + 2, len(db) - 1)] > db.max() - 35:
            return float(f * 256 / SR)
    return None


def chroma_cos(x, r):
    A = librosa.feature.chroma_cqt(y=x, sr=SR, hop_length=1024)
    B = librosa.feature.chroma_cqt(y=r, sr=SR, hop_length=1024)
    n = min(A.shape[1], B.shape[1])
    return float(np.mean(np.sum(A[:, :n] * B[:, :n], 0) / (np.linalg.norm(A[:, :n], axis=0) * np.linalg.norm(B[:, :n], axis=0) + 1e-9)))


def onset_corr(x, r):
    a = librosa.onset.onset_strength(y=x, sr=SR, hop_length=256)
    b = librosa.onset.onset_strength(y=r, sr=SR, hop_length=256)
    n = min(len(a), len(b)); a, b = a[:n], b[:n]
    L = int(0.15 * SR / 256)
    return max(float(np.corrcoef(a[max(0, l):n + min(0, l)], b[max(0, -l):n - max(0, l)])[0, 1]) for l in range(-L, L + 1, 2))


def spec_sim(y, r, a, b):
    S = np.log1p(np.abs(librosa.stft(y[int(a * SR):int(b * SR)], n_fft=2048, hop_length=2048)))
    R = np.log1p(np.abs(librosa.stft(r[int(a * SR):int(b * SR)], n_fft=2048, hop_length=2048)))
    n = min(S.shape[1], R.shape[1])
    return float(np.corrcoef(S[:, :n].ravel(), R[:, :n].ravel())[0, 1])


def flat_hf(y):
    S = np.abs(librosa.stft(y, n_fft=2048, hop_length=512)); f = librosa.fft_frequencies(sr=SR, n_fft=2048)
    band = S[(f > 4000) & (f < 10000)]; rms = np.sqrt((S ** 2).mean(0)); loud = rms > np.percentile(rms, 50)
    fl = np.exp(np.mean(np.log(band + 1e-10), 0)) / (band.mean(0) + 1e-10)
    return float(fl[loud].mean())


def fine_tempo(y, lo=85.0, hi=115.0):
    H = 64
    e = librosa.onset.onset_strength(y=y, sr=SR, hop_length=H); fps = SR / H; t = np.arange(len(e)) / fps
    best = (0, 0)
    for bpm in np.arange(lo, hi, 0.02):
        per = 60 / bpm
        z = np.abs(np.sum(e * np.exp(2j * np.pi * (t % per) / per)))
        if z > best[0]:
            best = (z, bpm)
    return float(best[1])


def cmd_facts(inst, voc, out):
    yi, yv = mono(inst), mono(voc)
    bpm = fine_tempo(yi)
    _, bt = librosa.beat.beat_track(y=yi, sr=SR, units="time", start_bpm=bpm)
    i = np.arange(len(bt)); p = np.polyfit(i, bt, 1); dev = np.abs(bt - np.polyval(p, i)) * 1000
    # bố cục theo giọng hát: tỷ lệ khung có tiếng mỗi 3 s
    r = librosa.feature.rms(y=yv, hop_length=512)[0]; act = 20 * np.log10(r + 1e-9) > -40
    w = int(3 * SR / 512); n = len(act) // w; a = np.array([act[k * w:(k + 1) * w].mean() for k in range(n)])
    first = int(np.argmax(a > 0.3)) * 3.0
    last = (len(a) - 1 - int(np.argmax(a[::-1] > 0.3))) * 3.0 + 3.0
    # khoảng lặng giữa bài dài nhất (dạo giữa)
    best, cur0 = (0, 0, 0), None
    for k in range(int(first / 3) + 6, len(a)):
        if a[k] < 0.25:
            cur0 = k if cur0 is None else cur0
        elif cur0 is not None:
            if (k - cur0) > best[0]:
                best = (k - cur0, cur0 * 3.0, k * 3.0)
            cur0 = None
    gap0, gap1 = (best[1], best[2]) if best[0] >= 3 else (None, None)
    sec = {"intro": [0.0, max(2.0, first - 1)]}
    if gap0:
        sec.update({"loi1": [first + 3, gap0 - 3], "giua": [gap0 + 1, gap1 - 1], "loi2": [gap1 + 3, last - 3]})
    else:
        sec.update({"loi1": [first + 3, last - 3]})
    res = {"bpm": round(bpm, 2), "tempo_dev_ms": round(float(np.percentile(dev, 90))), "inst_dur_s": round(len(yi) / SR, 2),
           "voc_dur_s": round(len(yv) / SR, 2), "first_onset_s": first_onset(yi), "voice_first_s": first, "voice_last_s": last,
           "gap": [gap0, gap1], "sections": sec}
    json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False))


def cmd_ref(inst, semis, ratio, out):
    y, sr = sf.read(inst, always_2d=True); semis, ratio = float(semis), float(ratio)
    ch = []
    for c in range(y.shape[1]):
        x = y[:, c]
        if ratio != 1.0:
            x = librosa.effects.time_stretch(x, rate=ratio)
        if semis != 0:
            x = librosa.effects.pitch_shift(x, sr=sr, n_steps=semis, res_type="soxr_hq")
        ch.append(x)
    sf.write(out, np.stack(ch, 1), sr, subtype="PCM_24")
    print(json.dumps({"out": out, "semis": semis, "ratio": ratio}))


def start_lock(r, y, t0=0.4, win=6.0):
    """Lệch giờ (ms) và độ khớp tiếng gõ của 6 s đầu so với bản gốc: bắt lỗi 'vài giây đầu' bị lệch cả phách."""
    a = librosa.onset.onset_strength(y=r, sr=SR, hop_length=128); b = librosa.onset.onset_strength(y=y, sr=SR, hop_length=128)
    a, b = (a - a.mean()) / (a.std() + 1e-9), (b - b.mean()) / (b.std() + 1e-9); fps = SR / 128
    s, w, L = int(t0 * fps), int(win * fps), int(0.8 * fps)
    x = a[s:s + w]
    sc = {l: float(np.dot(x, b[s + l:s + l + w])) / len(x) for l in range(-L, L + 1) if 0 <= s + l and s + l + w <= len(b)}
    l = max(sc, key=sc.get)
    return int(l / fps * 1000), round(sc[l], 3)


def cmd_beatrow(ref, aligned, raw, sections):
    sec = json.load(open(sections, encoding="utf-8"))
    r, y, yr = mono(ref), mono(aligned), mono(raw)
    sims = {k: round(spec_sim(y, r, a, b), 2) for k, (a, b) in sec.items() if b - a > 5}
    ia = (0.0, min(18.0, sec["intro"][1] + 1))
    xi, ri = y[:int(ia[1] * SR)], r[:int(ia[1] * SR)]
    f_b, f_r = first_onset(y), first_onset(r)
    sl, sc_ = start_lock(r, y)
    res = {"start_lag_ms": abs(sl), "start_corr": sc_, "sims": sims, "sim_orig_max": max(sims.values()) if sims else None, "dur_ratio": round(len(yr) / len(r), 3),
           "flat_hf": round(flat_hf(y), 3), "flat_hf_ref": round(flat_hf(r), 3),
           "intro_chroma": round(chroma_cos(xi, ri), 3), "intro_onset": round(onset_corr(xi, ri), 3),
           "intro_first_onset_dev_s": None if (f_b is None or f_r is None) else round(abs(f_b - f_r), 3),
           "first_onset_beat_s": f_b, "first_onset_ref_s": f_r}
    print(json.dumps(res, ensure_ascii=False))


def cmd_vocalrow(src, clean):
    ys, yc = mono(src), mono(clean)
    S = np.abs(librosa.stft(yc, n_fft=2048, hop_length=512)); rms = np.sqrt((S ** 2).mean(0))
    floor = float(20 * np.log10(np.percentile(rms, 5) / (np.percentile(rms, 95) + 1e-12)))
    H = 220
    a = librosa.onset.onset_strength(y=ys, sr=SR, hop_length=H); b = librosa.onset.onset_strength(y=yc, sr=SR, hop_length=H)
    a, b = (a - a.mean()) / (a.std() + 1e-9), (b - b.mean()) / (b.std() + 1e-9)
    fps = SR / H; w = int(10 * fps); L = int(1.0 * fps); lags = []
    for s in range(0, min(len(a), len(b)) - w, w):
        x = a[s:s + w]
        if np.std(x) < 0.3:
            continue
        sc = {l: float(np.dot(x, b[s + l:s + l + w])) / w for l in range(-L, L + 1) if 0 <= s + l and s + l + w <= len(b)}
        l = max(sc, key=sc.get)
        if sc[l] > 0.3:
            lags.append(abs(l / fps * 1000))
    print(json.dumps({"floor_db": round(floor, 1), "lag_ms": round(float(np.median(lags))) if lags else None}))


def _chroma(y):
    C = librosa.feature.chroma_cqt(y=y, sr=SR, hop_length=1024)
    return C / (C.max(0, keepdims=True) + 1e-9)


def cmd_introrow(ref, aligned, t_end):
    t_end = float(t_end); r, y = _chroma(mono(ref)), _chroma(mono(aligned))
    i0, i1 = int(0.6 * SR / 1024), int(t_end * SR / 1024); ok = n = 0
    for i in range(i0, min(i1, r.shape[1], y.shape[1])):
        top = np.argsort(-r[:, i])[:2]
        ok += any(np.argmax(y[:, j]) in top for j in range(max(0, i - 1), min(y.shape[1], i + 2))); n += 1
    a, b = y[:, i0:i1], r[:, i0:i1]; m = min(a.shape[1], b.shape[1]); a, b = a[:, :m], b[:, :m]
    cos = float(np.mean(np.sum(a * b, 0) / (np.linalg.norm(a, axis=0) * np.linalg.norm(b, axis=0) + 1e-9)))
    print(json.dumps({"intro_match": round(ok / max(1, n), 3), "intro_cos": round(cos, 3),
                      "intro_first_onset_dev_s": None if first_onset(mono(aligned)) is None or first_onset(mono(ref)) is None else round(abs(first_onset(mono(aligned)) - first_onset(mono(ref))), 3)}))


def cmd_introalign(ref, src, out, t_end):
    """Căn MỘT dạo đầu ngắn vào bản gốc bằng MỘT độ lệch chung (không cắt-ghép): chọn lệch (−1..+2 s) có tiếng gõ + nốt khớp nhất.
    Dạo đầu YuE2 tự nhất quán nhịp, chỉ lệch pha so với gốc (hay lệch 1 phách), nên một độ lệch chung là đủ và không gây nhảy."""
    t_end = float(t_end); H = 512
    r, y_all = mono(ref), mono(src)
    def feats(y):
        o = librosa.onset.onset_strength(y=y, sr=SR, hop_length=H); o = (o - o.mean()) / (o.std() + 1e-9)
        c = librosa.feature.chroma_cqt(y=y, sr=SR, hop_length=H); c = c / (np.linalg.norm(c, axis=0, keepdims=True) + 1e-9)
        return o, c
    o_r, c_r = feats(r); o_s, c_s = feats(y_all)
    f0, f1 = int(0.4 * SR / H), int(min(t_end, len(r) / SR) * SR / H)
    best = (-9.0, 0)
    for off in range(-int(1.0 * SR / H), int(2.0 * SR / H)):
        a0, a1 = f0 + off, f1 + off
        if a0 < 0 or a1 > min(len(o_s), c_s.shape[1]):
            continue
        sc = float(np.mean(o_r[f0:f1] * o_s[a0:a1])) + float(np.mean(np.sum(c_r[:, f0:f1] * c_s[:, a0:a1], 0)))
        if sc > best[0]:
            best = (sc, off)
    off_s = best[1] * H / SR
    x, sr = sf.read(src, always_2d=True); n_ref = int(len(r) / SR * sr); sh = int(round(off_s * sr))
    z = x[sh:] if sh >= 0 else np.concatenate([np.zeros((-sh, x.shape[1])), x])
    z = z[:n_ref] if len(z) >= n_ref else np.concatenate([z, np.zeros((n_ref - len(z), x.shape[1]))])
    sf.write(out, z, sr, subtype="PCM_24")
    cmd_introrow(ref, out, str(t_end))
    print(json.dumps({"intro_off_s": round(off_s, 3), "intro_score": round(best[0], 3)}))


def _active(v):
    r = librosa.feature.rms(y=v, hop_length=512)[0]; db = 20 * np.log10(r + 1e-9)
    return db > db.max() - 40


def _rms_db(y, mask):
    fr = librosa.feature.rms(y=y, hop_length=512)[0][:len(mask)]
    m = mask[:len(fr)]
    return float(20 * np.log10(np.sqrt(np.mean(fr[m] ** 2)) + 1e-9))


def cmd_balance(vocals, inst):
    """Giọng − beat (dB RMS) ở các khung có giọng: mức cân bằng của BẢN GỐC, để bản mình trộn cho giống."""
    v, b = mono(vocals), mono(inst); n = min(len(v), len(b)); v, b = v[:n], b[:n]
    m = _active(v)
    print(json.dumps({"bal_db": round(_rms_db(v, m) - _rms_db(b, m), 2)}))


def _lagwin(a_env, b_env, s, w, L):
    x = a_env[s:s + w]
    sc = {k: float(np.dot(x, b_env[s + k:s + k + w])) / w for k in range(-L, L + 1) if 0 <= s + k and s + k + w <= len(b_env)}
    k = max(sc, key=sc.get)
    return k, sc[k]


def cmd_joinfit(main, intro, out, t0):
    """Khớp pha dạo đầu với beat chính TRƯỚC chỗ ghép (lỗi 'vào nhạc không khớp'): đo độ lệch theo cửa sổ 4 s, khớp đường thẳng
    lệch(t)=a+b·t (a = lệch đầu, b = lệch tốc độ, thường <1%), rồi dời + co giãn dạo đầu theo đường đó. Chỉ chỉnh <= ±0.6 s và <= ±2%."""
    t0 = float(t0); H = 128; fps = SR / H
    m, y = mono(main), mono(intro)
    def env(z):
        o = librosa.onset.onset_strength(y=z, sr=SR, hop_length=H); return (o - o.mean()) / (o.std() + 1e-9)
    A, B = env(m), env(y)
    pts = []
    for c in np.arange(3.0, t0 - 1.0, 1.5):
        k, sc = _lagwin(A, B, int((c - 2) * fps), int(4 * fps), int(0.6 * fps))
        if sc > 0.25:
            pts.append((c, k / fps, sc))
    if len(pts) < 3:
        print(json.dumps({"ok": False, "why": "ít cửa sổ tin cậy", "n": len(pts)})); return
    t = np.array([p_[0] for p_ in pts]); l = np.array([p_[1] for p_ in pts]); w = np.array([p_[2] for p_ in pts])
    keep = np.ones(len(t), bool)
    for _ in range(3):
        b_, a_ = np.polyfit(t[keep], l[keep], 1, w=w[keep])
        res = np.abs(l - (a_ + b_ * t)); keep = res < max(0.08, np.percentile(res, 70))
    a_, b_ = float(np.clip(a_, -0.6, 0.6)), float(np.clip(b_, -0.02, 0.02))
    x, sr = sf.read(intro, always_2d=True); n = len(x); tt = np.arange(n) / sr
    src_t = tt + a_ + b_ * tt                                  # nội dung dạo đầu cần đọc ở giờ này để khớp beat chính
    out_ch = [np.interp(src_t, tt, x[:, c], left=0.0, right=0.0) for c in range(x.shape[1])]
    z = np.stack(out_ch, 1)
    sf.write(out, z, sr, subtype="PCM_24")
    y2 = mono(out); B2 = env(y2); after = []
    for c in np.arange(3.0, t0 - 1.0, 3.0):
        k, sc = _lagwin(A, B2, int((c - 2) * fps), int(4 * fps), int(0.6 * fps)); after.append(int(k / fps * 1000))
    before = [int(round(v * 1000)) for v in l[::2]]
    print(json.dumps({"ok": True, "a_ms": round(a_ * 1000), "b_pct": round(b_ * 100, 2), "n": len(pts), "lech_truoc_ms": before, "lech_sau_ms": after}))


def cmd_splicet(ref, t_target):
    y = mono(ref); _, bt = librosa.beat.beat_track(y=y, sr=SR, units="time", tightness=400)
    ok = [t for t in bt if t <= float(t_target)]
    print(json.dumps({"t": round(float(ok[-1]) if ok else float(bt[0]), 3)}))


if __name__ == "__main__":
    c, a = sys.argv[1], sys.argv[2:]
    {"facts": cmd_facts, "ref": cmd_ref, "beatrow": cmd_beatrow, "vocalrow": cmd_vocalrow, "introrow": cmd_introrow, "introalign": cmd_introalign, "balance": cmd_balance, "joinfit": cmd_joinfit, "splicet": cmd_splicet}[c](*a)
