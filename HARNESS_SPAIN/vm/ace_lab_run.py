"""Engine OLD (ACE-Step 1.5) trong LAB. Chạy trên VM bằng venv LAB:
  C:\\claude_lab\\ace\\venv\\Scripts\\python.exe ace_lab_run.py jobs.json
Nạp model giống app (xl-turbo, INT8, offload CPU, FlashAttn; xem engine-old/worker/ez_worker.py), một lần cho cả danh sách job.
jobs: [{"name": "...", "params": {GenerationParams...}}]  -> C:\\claude_lab\\outputs\\ace\\<name>.flac
Không đụng tool chính: code/model/venv đều là bản chép trong C:\\claude_lab\\ace.
"""
import json, os, sys, time, shutil
from pathlib import Path

LAB = Path(r"C:\claude_lab\ace")
ROOT = LAB / "ACE-Step-1.5"
OUT = Path(r"C:\claude_lab\outputs\ace")
assert "claude_lab" in sys.executable.lower(), f"phải chạy bằng venv lab, không phải {sys.executable}"
OUT.mkdir(parents=True, exist_ok=True)
JOBS = Path(sys.argv[1]).resolve()
os.chdir(ROOT)


def log(m):
    print(f"[{time.strftime('%H:%M:%S')}] {m}", flush=True)


from acestep.handler import AceStepHandler  # noqa: E402
from acestep.inference import GenerationConfig, GenerationParams, generate_music  # noqa: E402
import dataclasses  # noqa: E402

jobs = json.loads(JOBS.read_text(encoding="utf-8"))
need_lm = any(j["params"].get("thinking") for j in jobs)
log("nạp DiT acestep-v15-xl-turbo (INT8, offload CPU, FlashAttn)")
dit = AceStepHandler()
kq = dit.initialize_service(project_root=str(ROOT), config_path="acestep-v15-xl-turbo", device="cuda", offload_to_cpu=True,
                            quantization="int8_weight_only", use_flash_attention=True)
if isinstance(kq, tuple) and len(kq) == 2 and kq[1] is False:
    sys.exit(f"nạp DiT lỗi: {kq[0]}")
llm = None
if need_lm:
    from acestep.llm_inference import LLMHandler
    llm = LLMHandler()
    llm.initialize(checkpoint_dir=str(ROOT / "checkpoints"), lm_model_path="acestep-5Hz-lm-1.7B", backend="pt", device="cuda", offload_to_cpu=True)
log("model sẵn sàng")

PF = {f.name for f in dataclasses.fields(GenerationParams)}
for j in jobs:
    t0 = time.time()
    p = {k: v for k, v in j["params"].items() if k in PF}
    params = GenerationParams(**p)
    cfg = GenerationConfig(batch_size=1, use_random_seed=False, seeds=[int(p.get("seed", 42))], audio_format="flac")
    tmp = OUT / f"_tmp_{j['name']}"
    tmp.mkdir(exist_ok=True)
    log(f"BẮT ĐẦU {j['name']}: task {p.get('task_type')} | a={p.get('audio_cover_strength')} k={p.get('cover_noise_strength')} | seed {p.get('seed')}")
    r = generate_music(dit, llm, params, cfg, save_dir=str(tmp))
    if not getattr(r, "success", False):
        log(f"LỖI {j['name']}: {getattr(r, 'error', '')}")
        continue
    src = Path(r.audios[0]["path"])
    dst = OUT / f"{j['name']}.flac"
    shutil.move(str(src), dst)
    shutil.rmtree(tmp, ignore_errors=True)
    log(f"XONG {j['name']} sau {time.time() - t0:.0f} s -> {dst}")
log("HẾT")
