# MUSIC_HARNESS

Bản mã nguồn và dữ liệu của `project spain`, chụp ngày 09/10/2026.

**182 file gốc, 716,431 byte** được giữ nguyên nội dung.
Không bao gồm nhạc, video hoặc RAR theo yêu cầu của Duy.

## Nội dung

- `HARNESS_SPAIN/`: mã Python, cấu hình, skills, bộ nhớ, dữ liệu và trạng thái bài, nhật ký.
- `LAB/`: cấu hình job, báo cáo đo và nhật ký thử nghiệm.
- `NGHE/`: hướng dẫn nghe và danh sách `.lof`; các file âm thanh được tham chiếu không có trong repo.
- `MAPPING.md`, `MAPPING_BEAT_V4.md`, `PHAN_TICH_SUNO.md`: tài liệu phân tích.
- `DATA_MANIFEST.json`: danh sách, dung lượng và SHA-256 của toàn bộ 182 file gốc đã đưa vào.

## Sử dụng

Đọc `HARNESS_SPAIN/README.md`, `AGENTS.md` và `RULES.md` để hiểu harness.
`songs/*/state.json` là trạng thái lưu từ máy gốc, không phải một lần chạy mới đã xác minh.
Các đường dẫn âm thanh trong cấu hình, trạng thái và danh sách nghe vẫn trỏ tới
file trên máy gốc. Repo này không phải bản sao lưu có đầy đủ âm thanh.

`HARNESS_SPAIN/config/paths.json` dùng Python env bên ngoài thư mục dự án
và một máy ảo lab. Các env, model và VM đó không được đóng gói ở đây.
Muốn chạy trên máy khác cần thiết lập lại đường dẫn, môi trường và cung cấp âm thanh đầu vào.
Pipeline âm nhạc không được chạy trong lần kiểm tra/upload này.
