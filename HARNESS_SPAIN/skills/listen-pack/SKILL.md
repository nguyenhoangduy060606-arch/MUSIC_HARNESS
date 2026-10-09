---
name: listen-pack
description: Báo kết quả cho Duy và dựng/giải thích gói nghe (Audacity). Dùng mỗi khi tới cổng người HG1/HG2 hoặc khi sửa xong và có bản mới.
---

# listen-pack — báo Duy ngắn, sơ đồ trước

Duy không biết lý thuyết nhạc, nghe bằng tai trong Audacity, **ghét dài dòng**. Mẫu báo:

1. **Sơ đồ 5–8 dòng** (đã làm gì, đang ở đâu) — dùng `python run.py status <bài>`.
2. **Nghe ở đâu** (đường dẫn thư mục, thứ tự file, giây cần nghe — dạo đầu 0:00–0:25 trước).
3. **Số đo chính** (3–6 số, nhãn [ĐO]); nói rõ máy chỉ lọc, không nói "hay".
4. **Chưa chắc** (nhãn [ĐOÁN]/[?]); không hứa Content ID.
5. **Một câu hỏi** Duy cần trả lời (chọn bản nào / chỗ nào lỗi).

## Gói nghe do harness dựng
- HG1: `songs/<bài>/NGHE/1_beat/` — `0_beat_goc`, `b*` (cả beat), `i*` (dạo đầu riêng); `dao_dau_25s/nghe.lof` (25 s đầu của mọi file), `nghe.lof`, `LISTEN.md`. Cùng độ to −19 LUFS.
- HG2: `songs/<bài>/NGHE/2_ca_bai/` — `0_ban_goc`, `1_giong_*`, `2_giong_*` (cùng −17 LUFS); `ban_giao_-14LUFS/` (bản đăng).
- Bản cũ trước khi sửa: `NGHE/_da_duyet_<giờ>/`.

## Cấm
In lời bài (R6) · viết "hoàn hảo/ổn/đạt" thay Duy (R8) · gửi hơn 4 file một vòng · báo khi `review` chưa đạt.
