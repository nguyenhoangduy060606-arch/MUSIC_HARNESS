---
name: cover-run
description: Chạy trọn một bài cover có lời (norteño) bằng HARNESS_SPAIN, từ file đầu vào tới gói nghe cuối. Dùng khi có bài mới.
---

# cover-run — một bài từ đầu tới cuối

**Đầu vào Duy phải đưa (thiếu thì hỏi, đừng đoán):** bài gốc `.mp3`, beat đã tách `.wav`, giọng đã tách `.wav`, lời chuẩn `.txt`.
**Mặc định rút từ bài đã làm tốt:** dời **1 nửa cung xuống**, tốc độ **tự nhiên (ratio 1.0)** (chậm 4% làm lệch 6 s đầu), kiểu beat ưu tiên **`am`** (accordion ấm, không sax).

## Sơ đồ
```
init → [auto] intake → abc → beat_render(9 bản) → beat_gate
     → [auto] intros (render thêm dạo đầu riêng, ~4 phút)
     → ◆ HG1 (Duy nghe: chọn beat + dạo đầu)
     → [auto] finalize_beat (khớp pha + ghép) → vocal_render → vocal_gate → mix → pack
     → ◆ HG2 (Duy nghe cả bài, upload thử) → memory
```

## Các bước
1. `python run.py init <bài> --orig X.mp3 --inst beat.wav --vocals voc.wav --lyrics loi.txt` (mặc định `--semis -1 --ratio 1.0`).
2. `python run.py auto <bài>` — dừng khi gặp HG1 hoặc BLOCKED. Đừng chạy tool lẻ.
3. Khi tới HG1 mà chưa có dạo đầu riêng: `python run.py intros <bài> --seeds 21,22,23,24`.
4. Dùng skill `listen-pack` báo Duy. **Chờ Duy.** Không tự chọn beat thay Duy.
5. Duy trả lời → `python run.py human <bài> HG1 pass --pick <beat> --intro <dạo_đầu> --note "<nguyên văn lời Duy>"` rồi `python run.py auto <bài>`.
6. Tới HG2: skill `listen-pack`, chờ Duy; ghi `human ... HG2 pass|fail`.
7. Có lỗi Duy nói → skill `fix`. Mọi lời Duy → skill `calibrate`.

## Luôn nhớ
- Beat = YuE2 (R3), giọng = ACE (R3); không tự viết nốt (R4); không in lời (R6).
- Trước khi báo "xong": skill `review`.
- Lab: `lab-ops`. Tắt lab khi xong (R2).
