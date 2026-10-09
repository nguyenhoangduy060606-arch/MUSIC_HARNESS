---
name: review
description: Kiểm độc lập trước khi báo 'xong' hoặc trước cổng người: soi luật R1,R2,R4,R6,R10,R14 và tính nhất quán cấu hình. Dùng cuối mỗi chặng.
---

# review — đừng tự chấm bài của mình

Chạy theo thứ tự, mọi dòng phải **ĐẠT** mới được báo Duy:
```
python run.py selftest          # harness còn nguyên (cấu hình, R1, cổng chấm đúng, mã băm ngưỡng)
python run.py review <bài>      # R10 ngưỡng, R14 nhật ký, R1 tool thật, R6 lời, R2 khóa lab, R4 bản nốt, hồ sơ cổng
python run.py gates <bài>       # xem số từng bản (dấu * = cổng đang hiệu chuẩn)
```
- LỖI R10 → có người sửa `config/gates.json` ngoài `gate-set`: hoàn tác, báo Duy.
- LỖI R4 → bản nốt bị đổi ngoài dời cung: dừng, báo Duy, không dùng bản đó.
- LỖI R6 → lời lọt vào log: xóa dòng, báo Duy.
- LỖI R2 → khóa lab bị bỏ quên: `lab status` rồi xử lý theo `lab-ops`.
Sau đó mới dùng `listen-pack`. `auto` tự chạy `review` khi dừng.

**Hạn chế (nói thật):** `review` chỉ kiểm được luật có thể đo. R3, R5, R7–R9, R12, R13, R15 vẫn do người đọc kiểm. Đừng coi "review đạt" là "bài hay".
