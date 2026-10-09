"""[HARNESS_SPAIN bản chép riêng, không dùng chung với harness/ cũ]
Chạy workflow 'bản new' (SheetSage2 -> ABC -> YuE2) trong LAB ComfyUI (bản sao, cổng 8288, tunnel PC 28288).
KHÔNG BAO GIỜ nói chuyện với ComfyUI chính (:8188 / tunnel 18188). Duy 2026-10-04: không đụng tool chính.

  python tools/lab_comfy.py abc  <audio> [--mode melody|full] [--out abc.txt]
  python tools/lab_comfy.py gen  <audio> --style FILE_or_TEXT [--abc abc.txt] [--lyrics TEXT] [--seed N]
                                   [--max-duration S] [--cfg 1.0] [--name NAME] [--out-dir DIR]
  python tools/lab_comfy.py show <template.json>     # in ra lệnh nạp workflow lên giao diện lab (để Duy xem)

Cần lab đang chạy: ssh -L 28288:127.0.0.1:8288 ezycloudx-admin@100.120.64.51 "powershell -File lab_comfy_start.ps1"
"""
import argparse, json, sys, time, urllib.request, uuid
from pathlib import Path

H = Path(__file__).resolve().parent
PORT = int(__import__("os").environ.get("HS_LAB_PORT", "28288"))   # chỉ cổng lab. Đừng đổi sang 18188/8188 (run.py chặn)
BASE = f"http://127.0.0.1:{PORT}"
MIN_FREE_VRAM_MB = 3000   # lab giữ model đã nạp trong VRAM; --reserve-vram 5 đã chừa chỗ cho người khác


def _get(path, timeout=60):
    return json.loads(urllib.request.urlopen(BASE + path, timeout=timeout).read())


def _post(path, payload):
    req = urllib.request.Request(BASE + path, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req, timeout=60).read())


def check_lab():
    try:
        s = _get("/system_stats", 10)
    except Exception:
        sys.exit("Lab chưa chạy (không thấy cổng 28288). Chạy lab_comfy_start.ps1 trên máy ảo kèm tunnel.")
    argv = " ".join(s["system"].get("argv", []))
    if "claude_lab" not in argv or "8288" not in argv:
        sys.exit(f"Đây KHÔNG phải ComfyUI lab (argv: {argv}). Dừng để không đụng tool chính.")
    free = s["devices"][0]["vram_free"] // 2**20
    if free < MIN_FREE_VRAM_MB:
        sys.exit(f"GPU đang bận (còn trống {free} MB < {MIN_FREE_VRAM_MB}). Máy ảo dùng chung: chờ rồi chạy lại.")
    return free


def upload(path: Path, name: str, kind="input"):
    b = uuid.uuid4().hex
    body = (f'--{b}\r\nContent-Disposition: form-data; name="image"; filename="{name}"\r\nContent-Type: application/octet-stream\r\n\r\n').encode() + path.read_bytes() + \
           (f'\r\n--{b}\r\nContent-Disposition: form-data; name="type"\r\n\r\n{kind}\r\n--{b}\r\nContent-Disposition: form-data; name="overwrite"\r\n\r\ntrue\r\n--{b}--\r\n').encode()
    req = urllib.request.Request(BASE + "/upload/image", data=body, headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    return json.loads(urllib.request.urlopen(req, timeout=600).read())["name"]


def run(wf, timeout=3000):
    # không gửi client_id: ComfyUI phát tiến độ cho MỌI tab đang mở -> Duy xem được thanh tiến độ + node đang chạy trên giao diện lab
    pid = _post("/prompt", {"prompt": wf})["prompt_id"]
    t0 = time.time()
    while True:
        time.sleep(3)
        h = _get(f"/history/{pid}")
        if pid in h:
            break
        if time.time() - t0 > timeout:
            sys.exit("quá thời gian chờ")
    st = h[pid]["status"]
    if st.get("status_str") != "success":
        print(json.dumps(st, ensure_ascii=False)[:3000])
        sys.exit("ComfyUI lab báo lỗi")
    return h[pid]["outputs"], round(time.time() - t0)


def abc_graph(audio_name, mode):
    return {
        "2": {"class_type": "LoadAudio", "inputs": {"audio": audio_name}},
        "3": {"class_type": "AudioEncoderLoader", "inputs": {"audio_encoder_name": "sheetsage2_bf16.safetensors"}},
        "4": {"class_type": "SheetSage2AudioToABC", "inputs": {"audio_encoder": ["3", 0], "audio": ["2", 0], "mode": mode}},
        "12": {"class_type": "PreviewAny", "inputs": {"source": ["4", 0]}},
    }


def gen_graph(audio_name, style, lyrics, abc, seed, max_duration, cfg, prefix, mode="melody", ckpt="yue2_3b_bf16.safetensors"):
    g = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": ckpt}},
        "5": {"class_type": "YuE2GenerateMusic", "inputs": {
            "clip": ["1", 1], "style": style, "lyrics": lyrics, "abc": abc, "seed": seed, "mode": mode,
            "max_duration": max_duration, "temperature": 1.0, "top_p": 0.95, "top_k": 100, "repetition_penalty": 1.2, "cfg_scale": cfg}},
        "6": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["5", 0]}},
        "7": {"class_type": "EmptyYuE2LatentAudio", "inputs": {"seconds": ["5", 1], "batch_size": 1}},
        "8": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "positive": ["5", 0], "negative": ["6", 0], "latent_image": ["7", 0],
                                                   "seed": seed, "steps": 32, "cfg": 1.0, "sampler_name": "dpm_2", "scheduler": "sgm_uniform", "denoise": 1.0}},
        "11": {"class_type": "VAELoader", "inputs": {"vae_name": "yue2_vae_fp32.safetensors"}},
        "9": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["8", 0], "vae": ["11", 0]}},
        "10": {"class_type": "SaveAudioAdvanced", "inputs": {"audio": ["9", 0], "filename_prefix": f"audio/{prefix}", "format": "flac"}},
    }
    return g


def fetch(fn, dst: Path):
    q = f"/view?filename={urllib.request.quote(fn['filename'])}&subfolder={urllib.request.quote(fn.get('subfolder', ''))}&type={fn['type']}"
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(urllib.request.urlopen(BASE + q, timeout=600).read())


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    a1 = sub.add_parser("abc"); a1.add_argument("audio"); a1.add_argument("--mode", default="melody"); a1.add_argument("--out")
    a2 = sub.add_parser("gen"); a2.add_argument("audio"); a2.add_argument("--style", required=True)
    a2.add_argument("--abc"); a2.add_argument("--lyrics", default="[Intro]\n[Verse]\n[Chorus]\n[Bridge]\n[Outro]")
    a2.add_argument("--seed", type=int, default=1406623896); a2.add_argument("--max-duration", type=float, default=280.0)
    a2.add_argument("--cfg", type=float, default=1.0); a2.add_argument("--name"); a2.add_argument("--out-dir", required=True)
    a2.add_argument("--ckpt", default="yue2_3b_bf16.safetensors"); a2.add_argument("--mode", default="melody")
    a3 = sub.add_parser("show"); a3.add_argument("template")
    a = ap.parse_args()

    if a.cmd == "show":
        print("Mở http://127.0.0.1:28288 trong trình duyệt, rồi chạy trong console: "
              "app.loadApiJson(" + json.dumps(json.loads(Path(a.template).read_text(encoding='utf-8')), ensure_ascii=False)[:200] + "...)")
        return

    free = check_lab()
    print(f"lab OK, VRAM trống {free} MB", flush=True)
    audio = Path(a.audio)
    up = upload(audio, audio.name)

    if a.cmd == "abc":
        outs, secs = run(abc_graph(up, a.mode))
        texts = outs.get("12", {}).get("text", [])
        txt = "\n\n%%%% --- part ---\n\n".join(texts) if isinstance(texts, list) else str(texts)
        out = Path(a.out) if a.out else sys.exit("thiếu --out (harness_spain không ghi ra ngoài thư mục bài)")
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(txt, encoding="utf-8")
        print(json.dumps({"abc_file": str(out), "parts": len(texts) if isinstance(texts, list) else 1, "chars": len(txt), "secs": secs}))
        return

    style = Path(a.style).read_text(encoding="utf-8") if Path(a.style).exists() else a.style
    abc = Path(a.abc).read_text(encoding="utf-8") if a.abc else ""
    name = a.name or f"{audio.stem.replace(' ', '')}_s{a.seed}"
    wf = gen_graph(up, style, a.lyrics, abc, a.seed, a.max_duration, a.cfg, f"lab-{name}", mode=a.mode, ckpt=a.ckpt)
    outs, secs = run(wf)
    fn = None
    for o in outs.values():
        for k in ("audio", "images"):
            for f in o.get(k, []):
                fn = f
    dst = Path(a.out_dir) / f"{name}.flac"
    fetch(fn, dst)
    print(json.dumps({"flac": str(dst), "secs": secs}))


if __name__ == "__main__":
    main()
