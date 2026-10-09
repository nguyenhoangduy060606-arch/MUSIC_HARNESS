---
name: handoff
description: Mở phiên mới, đổi LLM (Codex/Claude) hoặc tiếp tục việc dở: đọc đúng thứ tự, biết đang ở đâu, không làm lại việc đã xong. Dùng ở đầu mọi phiên.
---

# handoff — 5 phút để vào việc

Đọc theo thứ tự (ngắn → dài), dừng khi đủ:
1. `AGENTS.md` (3 điều bắt buộc, bản đồ) → `RULES.md` (R1–R15).
2. `python run.py status` (bài nào), rồi `python run.py status <bài>` và `python run.py next <bài>` — **đây là sự thật về tiến độ**, không dựa vào trí nhớ hay tin nhắn cũ.
3. `songs/<bài>/NHAT_KY.md` (20 dòng cuối) — việc vừa làm, lỗi vừa gặp.
4. `memory/lessons.md` (mục mới nhất) và `memory/calibration.json` (lời Duy).
5. `skills/INDEX.md` — chọn skill theo tình huống.

## Việc đầu tiên
- Đang ở cổng người (HG) → dùng `listen-pack`, **chờ Duy**; không chạy tiếp.
- BLOCKED → `fix` (mục `bi_chan`).
- Đang chạy dở (`status` có ▶ bước tự động) → `python run.py auto <bài>`.
- Lab còn bật mà không việc → `lab down` (R2).

## Kết phiên
`review` → cập nhật `memory/lessons.md` (mục "Duy bổ sung" để trống cho Duy) → `lab down` → báo Duy bằng sơ đồ ngắn.
Môi trường dùng chung (chỉ đọc): 3 Python env trong `config/paths.json`, máy ảo lab. Nếu thiếu, báo Duy, đừng cài lại.
