# SKILLS của HARNESS_SPAIN — khi nào dùng skill nào

Mỗi skill là một thư mục `skills/<tên>/SKILL.md` (đầu file có `name`, `description` để LLM tự chọn). Skill KHÔNG thay `RULES.md`: luật luôn thắng.

| Tình huống | Skill |
|---|---|
| Có bài mới (mp3 + 2 stem + lời) cần cover từ đầu | `cover-run` |
| Duy/bên yêu cầu nói **có lỗi** (rè, vào nhạc lệch, beat to, giọng không rõ, intro sai, sax sạn, BLOCKED...) | `fix` |
| Cần **báo kết quả** cho Duy / dựng gói nghe | `listen-pack` |
| Duy vừa **khen/chê** (ghi lại để máy học tai Duy) | `calibrate` |
| Bật/tắt lab, kiểm GPU, khóa lab, lỗi tunnel | `lab-ops` |
| Duy gửi **lời chuẩn** (.txt), hoặc lời bị lỗi | `lyrics` |
| Sắp báo "xong" / trước cổng người | `review` |
| Mở phiên mới / đổi LLM / tiếp tục việc dở | `handoff` |
