# Chạy ComfyUI LAB (bản sao) cổng 8288. KHÔNG dùng cổng 8188 (tool chính). Thư mục input/output/temp/user riêng.
# Chạy bằng: ssh -L 28288:127.0.0.1:8288 ezycloudx-admin@100.120.64.51 "powershell -NoProfile -ExecutionPolicy Bypass -File lab_comfy_start.ps1"
$lab = 'C:\claude_lab'
Set-Location "$lab\comfy\ComfyUI"
& "$lab\venv\Scripts\python.exe" main.py --port 8288 --listen 127.0.0.1 `
    --input-directory "$lab\inputs" --output-directory "$lab\outputs" --temp-directory "$lab\tmp" --user-directory "$lab\user" `
    --fp32-vae --reserve-vram 5 --disable-auto-launch 2>&1 | Tee-Object -FilePath "$lab\logs\comfy_lab.log"
