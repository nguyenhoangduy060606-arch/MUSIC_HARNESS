---
name: lab-ops
description: Vận hành máy ảo lab (ComfyUI :8288 + ACE) an toàn dùng chung GPU: bật, kiểm, giải phóng, tắt, xử lý khóa và lỗi tunnel. Dùng khi stage cần lab hoặc lab báo lỗi.
---

# lab-ops

**Luật:** R1 không đụng tool thật (`C:\EZAISinger`, `C:\EZAISONG`, `:8188`) — `run.py` chặn; R2 một việc một lúc, kiểm GPU trước, tắt lab khi xong.

| Việc | Lệnh |
|---|---|
| Xem trạng thái + GPU + khóa | `python run.py lab status` |
| Bật lab (tự kiểm GPU trống ≥ 6000 MB) | `python run.py lab up` (các stage tự gọi) |
| Tắt lab + đóng tunnel | `python run.py lab down` — **luôn làm khi xong việc** |
| Lab báo bận (`songs/.lab.lock`) | chờ; chỉ xóa khóa khi chắc không còn tiến trình của mình (`python run.py lab status`) |
| GPU chung hết chỗ | DỪNG, báo Duy (có người khác dùng VM); không ép |
| Lỗi tunnel / lab không lên 200 s | `lab down` rồi `lab up`; vẫn lỗi → báo Duy kèm `songs/<bài>/NHAT_KY.md` |

## Cần nhớ
- ACE (giọng) chạy bằng venv riêng trên VM, không cần ComfyUI; trước khi chạy ACE harness gọi `/free` để nhả VRAM của YuE2.
- Lệnh PowerShell trên VM: viết thành file `.ps1`, `scp`, rồi `ssh ... -File` (hàm `vm_ps1` đã làm); đừng nhồi lệnh trong dấu nháy.
- Không tải model mới, không xóa/di chuyển dữ liệu của Duy (R12).
