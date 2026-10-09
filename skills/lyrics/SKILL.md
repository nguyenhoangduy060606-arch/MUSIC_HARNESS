---
name: lyrics
description: Xử lý lời chuẩn Duy gửi (.txt) cho ACE hát lại; kiểm lời đã đúng chưa mà không in lời ra chat. Dùng khi nhận lời mới hoặc giọng hát sai chữ.
---

# lyrics — lời đi bằng file, không bao giờ vào chat (R6)

1. Duy gửi `.txt` (có thể kèm nhãn `[Verse]`, quảng cáo "You might also like"...). Đưa vào `init --lyrics <file>`; stage `intake` tự chạy `tools/lyrics_clean.py` → `in/lyrics_ace.txt`, thêm `[Intro]`/`[Outro]` nếu thiếu.
2. **Chỉ in số liệu:** số dòng, số đoạn, độ sai lời (WER). Không dán, không tóm tắt, không trích câu nào.
3. Độ sai lời cao (cổng `wer` ≤ 0.45): xem `python run.py gates <bài> vocal`. Nguyên nhân hay gặp: nguồn giọng méo, kiểu giọng A (sáng) → dùng `fix <bài> giong_khong_ro`.
4. Bài mà bản cover bỏ đoạn (như Suno bỏ đoạn kết): cắt lời tương ứng bằng cách sửa file lời trong `in/` rồi `redo vocal_gate` — hỏi Duy trước.
5. `review` kiểm tự động: log/state không chứa 5 từ liền của lời. Nếu `review` báo R6 lỗi → xóa dòng log vi phạm và báo Duy.
