"""Đóng gói nghe vòng 4 Spain: chuẩn TARGET LUFS (mặc định -14) (đỉnh <= -1 dBTP), mp3 320k, nghe.lof cho Audacity. Chạy bằng .venv.
python tools/pack.py <thu_muc_ra> <ten_ra>=<file_vao> [...]"""
import sys, subprocess, os
from pathlib import Path
import numpy as np, soundfile as sf
sys.path.insert(0, str(Path(__file__).resolve().parent))
from mix import load, lufs, true_peak_db, SR
FF = os.environ.get("FF", "ffmpeg")
T = float(os.environ.get("TARGET", "-14"))  # cùng một mức cho cả thư mục để so công bằng
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
names = []
for spec in sys.argv[2:]:
    name, src = spec.split("=", 1)
    y = load(src); y = y * 10 ** ((T - lufs(y)) / 20)
    tp = true_peak_db(y)
    if tp > -1: y = y * 10 ** ((-1 - tp) / 20)
    w = out / (name + ".wav"); sf.write(w, y, SR, subtype="PCM_16")
    subprocess.run([FF, "-v", "error", "-y", "-i", str(w), "-b:a", "320k", str(out / (name + ".mp3"))], check=True); w.unlink()
    names.append(name + ".mp3"); print(name, round(lufs(y), 1), "LUFS")
(out / "nghe.lof").write_text("".join(f'file "{n}"\n' for n in names), encoding="utf-8")
