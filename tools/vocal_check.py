"""Đo bản cover vocal so với giọng gốc (chỉ là bộ lọc; tai Duy quyết).
Dùng (.venv_tx):  python tools/vocal_check.py <giong_goc.wav> <ban1.flac> [<ban2> ...]

  dung_not = % khung (cả hai cùng đang hát) có cao độ lệch <= 50 cent (bỏ qua chênh quãng tám) -> giữ giai điệu
  phu      = khung có hát ở bản mới / khung có hát ở bản gốc (thấp = bỏ câu, cao nhiều = hát thêm/ngân bậy)
  lech_tb  = độ lệch trung vị (cent) trên các khung cùng hát
  tam      = nốt trung vị của bản mới (nam ~C4; nữ hát cao 1 quãng tám ~C5) và quang8 = chênh quãng tám trung vị so với gốc
Cover của ACE khoá độ dài theo nguồn nên so thẳng theo thời gian.
"""
import json, sys
from pathlib import Path

import librosa
import numpy as np

SR, HOP = 16000, 320


def f0(path):
    y, _ = librosa.load(path, sr=SR, mono=True)
    f, v, _ = librosa.pyin(y, fmin=70, fmax=900, sr=SR, hop_length=HOP, frame_length=1280)
    return np.where(v, f, np.nan)


def main():
    src = f0(sys.argv[1])
    for p in sys.argv[2:]:
        c = f0(p)
        n = min(len(src), len(c))
        a, b = src[:n], c[:n]
        both = ~np.isnan(a) & ~np.isnan(b)
        cents = 1200 * np.log2(b[both] / a[both])
        cents = (cents + 600) % 1200 - 600
        out = {"file": Path(p).name, "dung_not": round(float(np.mean(np.abs(cents) <= 50)) * 100, 1) if both.any() else 0,
               "phu": round(float(np.sum(~np.isnan(b)) / max(1, np.sum(~np.isnan(a)))), 2),
               "lech_tb": round(float(np.median(np.abs(cents))), 0) if both.any() else None,
               "tam": librosa.hz_to_note(float(np.nanmedian(b))) if np.any(~np.isnan(b)) else None,
               "quang8": round(float(np.median(1200 * np.log2(b[both] / a[both]))) / 1200, 2) if both.any() else None}
        print(json.dumps(out, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
