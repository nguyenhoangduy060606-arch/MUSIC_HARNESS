# HARNESS_SPAIN — đọc file này đầu tiên (dành cho mọi LLM: Codex, Claude, ...)

Bạn đang làm **cover bài có lời** (norteño) cho Duy. Duy không biết lý thuyết nhạc, nghe bằng tai (Audacity). **Nói tiếng Việt, từ đơn giản, ngắn gọn, sơ đồ trước.**

## 3 điều bắt buộc
1. **Chỉ hành động qua `python run.py ...`.** Không tự chạy tool lẻ, không sửa `songs/*/state.json`, `config/*.json` bằng tay.
2. **Đọc `RULES.md` trước khi làm** (15 luật, có mã R1..R15). Vi phạm luật = dừng và báo Duy.
3. **Máy chỉ là bộ lọc, tai Duy quyết.** Không bao giờ viết "beat hay / ổn / đạt" chỉ vì số đo đẹp. Gắn nhãn [ĐO] / [ĐOÁN] / [?].

## Vòng làm việc (lặp)
```
python run.py status <bai>      # đang ở đâu
python run.py next   <bai>      # việc tiếp theo (1 dòng)
python run.py auto   <bai>      # chạy tự động tới khi gặp: cổng người (HG) / bị chặn / xong
python run.py human  <bai> HG1 pass|fail --pick beat_2 --note "..."   # chỉ ghi lời Duy nói
```
Gặp **BLOCKED** hoặc **HUMAN** → dừng, báo Duy bằng 5 dòng: đang ở bước nào / đã thử gì / số đo / vấn đề / cần Duy làm gì.

## Skills (chọn theo tình huống — chi tiết `skills/INDEX.md`)
| Khi | Skill |
|---|---|
| bài mới | `cover-run` |
| Duy/bên yêu cầu nói có lỗi | `fix` → `python run.py fix <bài> <triệu_chứng>` |
| báo kết quả / gói nghe | `listen-pack` |
| Duy vừa khen/chê | `calibrate` |
| lab, GPU, khóa, tunnel | `lab-ops` |
| lời chuẩn | `lyrics` |
| trước khi báo "xong" | `review` |
| mở phiên mới / đổi LLM | `handoff` |

## Bản đồ thư mục
`config/` luật số (workflow, gates, fixes, styles, đường dẫn) · `skills/` 8 skill · `tools/` công cụ (chép riêng, không dùng chung harness cũ) · `vm/` script chạy trên máy ảo · `memory/` bài học + hiệu chuẩn tai Duy · `songs/<bai>/` mọi thứ của một bài.
Sơ đồ đầy đủ: `README.md`.
