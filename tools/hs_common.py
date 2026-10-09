"""Hàm dùng chung của harness_spain (chỉ thư viện chuẩn Python). Luật R1 (chặn tool thật), R2 (lab, khóa), R14 (nhật ký)."""
import glob
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CFG = ROOT / "config"
SONGS = ROOT / "songs"
MEM = ROOT / "memory"
LOCK = SONGS / ".lab.lock"
TUNNEL_PID = SONGS / ".tunnel.pid"
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def jload(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def jsave(p, d):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(d, ensure_ascii=False, indent=1, default=float), encoding="utf-8")


PATHS = jload(CFG / "paths.json")


def say(song_dir, msg):
    """R14: một dòng nhật ký tiếng Việt cho Duy xem trực tiếp."""
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    if song_dir:
        Path(song_dir).mkdir(parents=True, exist_ok=True)
        with open(Path(song_dir) / "NHAT_KY.md", "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    print(line, flush=True)


def guard(*things):
    """R1: từ chối mọi lệnh/đường dẫn chạm tool thật."""
    blob = " ".join(str(t) for t in things)
    for bad in PATHS["deny_substrings"]:
        if bad.lower() in blob.lower():
            raise SystemExit(f"R1 CHẶN: '{bad}' là tool thật của công ty, harness không được đụng. Lệnh: {blob[:200]}")


def py(name):
    p = os.path.expanduser(PATHS["py"][name])
    if not Path(p).exists():
        raise SystemExit(f"thiếu Python env '{name}': {p}")
    return p


def ffmpeg():
    g = glob.glob(os.path.expanduser(PATHS["ffmpeg_glob"]))
    return g[0] if g else "ffmpeg"


def run(cmd, check=True, **kw):
    guard(*cmd)
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1", **kw.pop("env", {})}
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True, encoding="utf-8", errors="replace", env=env, **kw)
    if check and r.returncode != 0:
        raise RuntimeError(f"lệnh lỗi ({r.returncode}): {' '.join(str(c) for c in cmd)[:200]}\n{(r.stdout[-600:] + r.stderr[-600:]).strip()}")
    return r


def last_json(text):
    for ln in reversed(text.splitlines()):
        ln = ln.strip()
        if ln.startswith("{") and ln.endswith("}"):
            return json.loads(ln)
    raise RuntimeError("không thấy JSON trong đầu ra: " + text[-300:])


# ---------- máy ảo + lab ----------
def _ssh_base():
    v = PATHS["vm"]
    return ["ssh", "-i", os.path.expanduser(v["key"]), "-o", "ConnectTimeout=15"], v["ssh"]


def vm_ps1(script_text, tag="job"):
    """Chạy một đoạn PowerShell trên VM bằng file .ps1 (không nhồi lệnh trong dấu nháy). Trả về stdout đã lọc cảnh báo ssh."""
    v = PATHS["vm"]; guard(script_text)
    tmp = ROOT / "songs" / f"_{tag}.ps1"; tmp.parent.mkdir(exist_ok=True); tmp.write_text(script_text, encoding="utf-8")
    key = os.path.expanduser(v["key"])
    subprocess.run(["scp", "-q", "-i", key, str(tmp), f"{v['ssh']}:{tag}.ps1"], capture_output=True)
    base, host = _ssh_base()
    r = subprocess.run(base + [host, f"powershell -NoProfile -ExecutionPolicy Bypass -File {tag}.ps1"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    tmp.unlink(missing_ok=True)
    return "\n".join(l for l in r.stdout.splitlines() if not any(k in l.lower() for k in ("post-quantum", "store now", "openssh.com", "upgraded")))


def scp_to(local, remote):
    guard(remote)
    subprocess.run(["scp", "-q", "-i", os.path.expanduser(PATHS["vm"]["key"]), str(local), f"{PATHS['vm']['ssh']}:{remote}"], capture_output=True, check=True)


def scp_from(remote, local):
    guard(remote); Path(local).parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["scp", "-q", "-i", os.path.expanduser(PATHS["vm"]["key"]), f"{PATHS['vm']['ssh']}:{remote}", str(local)], capture_output=True, check=True)


def gpu_used_mb():
    out = vm_ps1("nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader,nounits", "gpu").strip().split(",")
    return int(out[0]), int(out[1])


def lab_alive():
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{PATHS['vm']['tunnel_port']}/system_stats", timeout=4)
        return True
    except Exception:
        return False


def lab_up(song_dir=None):
    """R2: kiểm GPU, bật ComfyUI lab :8288 qua tunnel 28288."""
    if lab_alive():
        return
    used, total = gpu_used_mb()
    if total - used < PATHS["min_free_gpu_mb"]:
        raise SystemExit(f"R2 DỪNG: GPU chung chỉ còn {total - used} MB trống (cần ≥ {PATHS['min_free_gpu_mb']}). Báo Duy.")
    v = PATHS["vm"]; base, host = _ssh_base()
    cmd = base + ["-L", f"{v['tunnel_port']}:127.0.0.1:{v['lab_port']}", host, f"powershell -NoProfile -ExecutionPolicy Bypass -File {v['start_script']}"]
    guard(*cmd)
    p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    TUNNEL_PID.write_text(str(p.pid))
    for _ in range(40):
        time.sleep(5)
        if lab_alive():
            say(song_dir, "Lab đã bật (ComfyUI :8288 qua tunnel 28288).")
            return
    raise SystemExit("lab không lên sau 200 s")


def lab_free():
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{PATHS['vm']['tunnel_port']}/free", data=json.dumps({"unload_models": True, "free_memory": True}).encode(),
                                     headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=15)
    except Exception:
        pass


def lab_down(song_dir=None):
    """R2: tắt lab (chỉ tiến trình có 'main.py --port 8288') và đóng tunnel."""
    vm_ps1("Get-CimInstance Win32_Process -Filter \"name='python.exe'\" | Where-Object { $_.CommandLine -like '*main.py --port 8288*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }", "labdown")
    if TUNNEL_PID.exists():
        try:
            subprocess.run(["taskkill", "/F", "/PID", TUNNEL_PID.read_text().strip()], capture_output=True)
        except Exception:
            pass
        TUNNEL_PID.unlink(missing_ok=True)
    say(song_dir, "Lab đã tắt.")


class LabLock:
    """R2: một việc một lúc."""
    def __enter__(self):
        if LOCK.exists() and time.time() - LOCK.stat().st_mtime < 3 * 3600:
            raise SystemExit(f"R2: lab đang bận ({LOCK.read_text()[:80]}). Chờ hoặc xóa {LOCK} nếu chắc chắn không còn việc.")
        LOCK.write_text(f"pid {os.getpid()} {time.strftime('%H:%M:%S')}")
        return self

    def __exit__(self, *a):
        LOCK.unlink(missing_ok=True)
