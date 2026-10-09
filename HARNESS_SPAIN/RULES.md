# RULES — luật cứng (mã R để trích dẫn). Sửa luật chỉ khi Duy đồng ý, ghi vào memory/lessons.md.

| Mã | Luật |
|---|---|
| R1 | **Không đụng tool thật**: `C:\EZAISinger`, `C:\EZAISONG`, ComfyUI `:8188`/`18188`. Chỉ đọc file. (`run.py` chặn đường dẫn/cổng này.) |
| R2 | Mọi thí nghiệm chạy ở **lab** `C:\claude_lab` (ComfyUI `:8288` qua tunnel `28288`). **Một việc một lúc** (khóa `songs/.lab.lock`). Kiểm GPU trước, giải phóng sau mỗi lượt, **tắt lab khi xong**. |
| R3 | **Beat = model MỚI** (SheetSage2 → bản nốt ABC → YuE2). **Giọng = model CŨ** (ACE cover). Không đảo. |
| R4 | **Không tự viết nốt.** Bản nốt chỉ được biến đổi bằng máy (dời cung, tốc độ, bỏ bè hát, nối nốt ngắn, sửa lỗi chép cho đúng bản gốc). |
| R5 | **Không mẹo đánh lừa máy dò** (thêm nhiễu, méo tiếng, kéo giãn lặt vặt). Chỉ đổi âm nhạc thật: cung, nhạc cụ, cách chơi. |
| R6 | **Không in lời bài hát ra chat/log.** Lời chỉ đi qua file; chỉ in số liệu (số dòng, độ sai). |
| R7 | **Cổng người (HG)**: beat phải qua tai Duy (dạo đầu trước) rồi mới làm giọng; bản cuối qua tai Duy rồi mới "xong". Máy không thay được cổng người. |
| R8 | **Số đo ≠ chất lượng.** Cổng máy chỉ loại bản hỏng. Cổng đang hiệu chuẩn (`provisional`) chỉ **báo cáo**, không loại, tới khi tai Duy xác nhận số đó phân biệt được tốt/dở. |
| R9 | Mỗi lời Duy nói (khen/chê/lý do) → ghi `memory/calibration.json` + `memory/lessons.md` **ngay**. |
| R10 | **Không sửa ngưỡng giữa chừng** để cho bản "đạt". Đổi ngưỡng chỉ qua `run.py gate-set` kèm lý do + Duy đồng ý. |
| R11 | **Giới hạn thử**: mỗi bước tối đa `max_attempts` lượt; hết lượt → BLOCKED, báo Duy. Không lặp vô hạn. |
| R12 | **Cô lập**: không import/sửa `harness/` cũ. Python env dùng chung chỉ-đọc (khai ở `config/paths.json`). Không xóa/di chuyển dữ liệu của Duy; mọi đầu ra nằm trong `songs/<bai>/`. |
| R13 | Đơn vị luôn ghi rõ: **"nửa cung" = 1 semitone** (Bb→A); LUFS, dB, %, giây. Số tỷ lệ ghi 0–1 hay % thì nói rõ. |
| R14 | Mọi hành động ghi vào `songs/<bai>/NHAT_KY.md` (tiếng Việt, 1 dòng/việc). Duy theo dõi trực tiếp file này. |
| R15 | Báo cáo cho Duy: **sơ đồ/bảng ngắn trước**, không dài dòng; nói thật phần chưa biết; không hứa Content ID (Duy tự upload thử). |
