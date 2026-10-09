---
name: fix
description: Sửa lỗi cho bài cover theo triệu chứng Duy hoặc bên yêu cầu nói (rè, vào nhạc lệch, beat to, giọng không rõ, intro sai, sax sạn, mất nhịp, thiếu accordion, BLOCKED). Dùng bất cứ khi nào có lời chê.
---

# fix — nghe triệu chứng → chẩn đoán đã đo → sửa bằng lệnh

**Quy trình:** (1) hỏi lại triệu chứng nếu chưa rõ (giây nào, nghe sai kiểu gì) → (2) tìm dòng bên dưới → (3) chạy `python run.py fix <bài> <triệu_chứng> --note "<nguyên văn lời Duy>"` → (4) `review` → (5) `listen-pack` báo Duy bản mới (bản cũ đã tự chép vào `NGHE/_da_duyet_*`) → (6) `calibrate`.
**Cấm:** nới ngưỡng cổng cho bản "đạt" (R10); tự viết nốt (R4); mẹo đánh lừa máy dò (R5); xóa bản cũ (R12).

| Duy nói | Triệu chứng | Nguyên nhân đã ĐO | Lệnh |
|---|---|---|---|
| "vào nhạc không khớp beat" | `vao_nhac_lech` | dạo đầu ghép lệch pha 100–270 ms + trôi 1% so với beat chính; đã sửa bằng `joinfit` | `fix <bài> vao_nhac_lech` |
| "beat to / lấn giọng" | `beat_to` | giọng−beat −6.4 dB vs gốc −4.4 dB (Prisión) | `fix <bài> beat_to` (+1.5 dB giọng, hạ beat 1 dB thêm) |
| "giọng nhỏ / chìm" | `giong_nho` | | `fix <bài> giong_nho` |
| "rè / xì" | `re_xi` | xì nền giọng ACE (−25 dB vs gốc −45) + master quá to | `fix <bài> re_xi` (lọc mạnh hơn, trộn lại) |
| "giọng không rõ chữ" | `giong_khong_ro` | sai lời cao (kiểu A 0.59–2.7) | `fix <bài> giong_khong_ro` (kiểu B, vòng giọng mới) |
| "giọng gắt / chói" | `giong_gat` | | `fix <bài> giong_gat` |
| "vài giây đầu khác bản gốc / đánh lỗi" | `intro_sai` | bản nốt đặt nốt đầu trễ ~0.6 s; chậm 4% lệch 1 phách 6 s đầu | `fix <bài> intro_sai` (render thêm dạo đầu; quay lại HG1) |
| "đàn sax có sạn" | `sax_san` | kiểu có sax kém đều hơn kiểu `am` | `fix <bài> sax_san` (chỉ kiểu `am`, vòng beat mới) |
| "beat lúc nhanh lúc chậm / mất nhịp" | `beat_hut_phach` | YuE2 hụt/thừa phách | `fix <bài> beat_hut_phach` (bản nốt dày hơn) |
| "không nghe ra accordion" | `thieu_accordion` | | `fix <bài> thieu_accordion` |
| bước bị BLOCKED | `bi_chan` | | đọc `state.blocked_reason`; lỗi mã → sửa rồi `unblock --why`; hết thang vòng → báo Duy |

## Triệu chứng KHÔNG có trong bảng
1. Đừng đoán. Đo trước (xem `tools/measure.py`: `start_lock`, `balance`, `joinfit`; `python run.py gates <bài>`).
2. Cho Duy 5 dòng: bước nào / đã thử gì / số đo / nghi ngờ [ĐOÁN] / cần Duy nghe cái gì.
3. Khi tìm ra nguyên nhân: thêm một dòng vào `config/fixes.json` (triệu chứng → hành động) và vào bảng trên, ghi `memory/lessons.md`. Đó là cách harness học.

## Hành động có sẵn trong `fixes.json`
`plan` (đổi tham số bài: `mix.bal_offset_db`, `mix.duck_db`, `clean_hf`) · `redo` (làm lại `finalize_beat|mix|pack|vocal_gate|beat_gate`) · `goto` (quay về bước + sang vòng sau của thang) · `patch` (đổi thang vòng kế) · `intros`.
