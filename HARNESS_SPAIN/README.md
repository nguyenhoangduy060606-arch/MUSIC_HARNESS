# HARNESS_SPAIN — quy trình cover bài có lời (norteño), tách riêng, cứng, có vòng lặp

Dành cho LLM thực thi (Codex...) + Duy. LLM chỉ chạm hệ thống qua `python run.py`. Luật: `RULES.md`. Vào việc: `AGENTS.md`.

## Sơ đồ một bài

```
 INPUT (Duy đưa)            bài gốc .mp3 │ beat tách .wav │ giọng tách .wav │ lời chuẩn .txt
                                         │   (tùy chọn: stem Suno của bài = mốc/bản phụ)
                                         ▼  python run.py init <bài> ...
 ┌───────────── VÒNG TỰ ĐỘNG  (python run.py auto <bài>) ─────────────────────────────┐
 │ 1 intake       đo nhịp/cung/bố cục + dọn lời + dựng "lưới chuẩn" (dời 1 nửa cung)  │
 │ 2 abc          SheetSage2 chép nốt beat gốc  →  máy dời cung/Q/nối nốt (R4)        │
 │ 3 beat_render  YuE2: 3 kiểu × 3 seed                                               │
 │ 4 beat_gate    căn phách + lọc máy ──── chưa đủ 2 bản đạt ──► vòng sau (tối đa 3)  │
 └───────────────────────────────────┬──────────────────────────────────────────────┘
                                     ▼
              ◆ HG1  TAI DUY: nghe beat, DẠO ĐẦU 25 s TRƯỚC ─── chê ──► beat vòng mới
                                     ▼ chọn 1 beat (--pick)
 ┌───────────── VÒNG TỰ ĐỘNG ───────────────────────────────────────────────────────┐
 │ 5 vocal_render ACE hát lại (lời chuẩn) trên giờ của beat                           │
 │ 6 vocal_gate   bỏ xì + đo (nốt, lời, giống ca sĩ, lệch giờ) ── không đạt ► vòng sau│
 │ 7 mix          beat + giọng, master −14 LUFS                                       │
 │ 8 pack         gói nghe Audacity (.lof) + bản giao                                 │
 └───────────────────────────────────┬──────────────────────────────────────────────┘
                                     ▼
              ◆ HG2  TAI DUY + bên yêu cầu + Duy upload thử Content ID
                                     ▼ ổn
                         9 memory: ghi bài học + hiệu chuẩn tai Duy
```

## Vòng sửa lỗi (khi Duy/bên yêu cầu chê)
```
 lời chê ─► skill `fix` ─► python run.py fix <bài> <triệu_chứng> ─► (chép bản cũ vào NGHE/_da_duyet_*)
        ─► làm lại đúng bước liên quan (mix / ghép dạo đầu / giọng / beat vòng mới) ─► review ─► gói nghe mới ─► Duy nghe lại
 triệu chứng chưa có ─► đo trước ─► thêm 1 dòng vào config/fixes.json + skills/fix ─► harness học thêm
```
Bảng triệu chứng: `config/fixes.json` (vao_nhac_lech, beat_to, giong_nho, re_xi, giong_khong_ro, giong_gat, intro_sai, sax_san, beat_hut_phach, thieu_accordion, bi_chan).

## Cái làm nó "cứng"
| | Cách |
|---|---|
| **Luật** | `RULES.md` 15 luật (R1–R15). Vài luật do code ép: R1 chặn tool thật, R2 khóa lab 1 việc, R11 giới hạn lượt, R10 đổi ngưỡng cần `--duy-ok`. |
| **Vòng lặp** | `config/workflow.json`: mỗi bước có cổng + số lượt tối đa. Không đạt → thang vòng (ladder) đã định sẵn (seed → kiểu → bản nốt dày). Hết thang → **BLOCKED**, báo Duy. |
| **Cổng máy** | `config/gates.json`: `hard` (loại bản hỏng), `report` (chỉ ghi số, chưa tin), `stage` (cả vòng). |
| **Cổng người** | HG1 (beat) và HG2 (cả bài). Máy không qua được. Lời Duy ghi vào `memory/calibration.json` kèm số đo → sau vài bài mới biết số nào tin được (R8, R9). |
| **Trạng thái** | `songs/<bài>/state.json` do `run.py` ghi; LLM không sửa tay. Nhật ký tiếng Việt: `songs/<bài>/NHAT_KY.md`. |
| **Cô lập** | Code/luật/bộ nhớ/trạng thái nằm riêng trong thư mục này. Chỉ dùng chung 3 Python env (chỉ-đọc, `config/paths.json`) và máy ảo lab. |

## Cổng máy hiện có (số cụ thể trong `config/gates.json`)
- **Beat (cứng):** giọng ≤ 15% · accordion ≥ 40% · khớp nhịp (tương quan ≥ 0.30, tản ≤ 60 ms) · hụt phách ≤ 2 · đủ dài ≥ 90% · giống bản thu gốc ≤ 0.62 · cả vòng ≥ 2 bản đạt.
- **Beat (báo cáo, chưa tin):** 4 số riêng cho **dạo đầu** (chroma, nhịp gõ, lệch nốt đầu). Lý do chưa tin: đo 2026-10-07, các số này **không tách được** beat Duy chê (v4) với beat Duy khen (Suno-based). Intro vì vậy do **tai Duy** quyết (HG1).
- **Giọng (cứng):** nền xì ≤ −60 dB · nốt đúng ≥ 70% · sai lời ≤ 0.45 · giống ca sĩ gốc ≥ 0.88 · lệch giờ ≤ 80 ms.
- **Trộn (cứng):** −14 ± 0.5 LUFS · đỉnh ≤ −1 dB · chạm trần ≤ 0.01% · độ "thở" ≥ 14 dB.

## So với chuẩn harness của cộng đồng (agent harness)
| Thành phần chuẩn | Ở đây | Còn yếu |
|---|---|---|
| Quy tắc ngắn cho LLM (`AGENTS.md` = bản đồ, không phải sách) | `AGENTS.md` 25 dòng + `RULES.md` | |
| Vòng lặp tới khi đạt (kiểu "Ralph loop") | `run.py auto`: bước → cổng → thử lại / vòng mới / BLOCKED | thang vòng mới chỉ có gợi ý viết tay (`workflow.json › hints`), chưa tự học |
| Rào chắn do **mã** ép, không chỉ chữ | R1 (tool thật), R2 (khóa lab), R10 (mã băm ngưỡng), R11 (giới hạn lượt) | R3, R5, R7–R9, R12, R13, R15 vẫn là chữ |
| Người kiểm độc lập (không để chính nó tự chấm) | `run.py review` (R1,R2,R4,R6,R10,R14) + `selftest` 14 phép | chưa có "agent thứ hai" đọc lại kết quả |
| Bộ nhớ qua các phiên | `state.json`, `memory/` (bài học + hiệu chuẩn tai Duy) | hiệu chuẩn mới có 3 mục |
| Tiêu chí nghiệm thu khách quan | cổng máy (cứng) | **âm nhạc không có test tự động**: chấp nhận cuối = tai Duy (HG1/HG2). Mọi cổng "intro" đang chỉ báo cáo |

## Trạng thái kiểm thử (2026-10-07, đã chạy thật trên Prisión)
| Phần | |
|---|---|
| intake → abc → beat_render → beat_gate → vòng dạo đầu riêng → `review` | **đã chạy thật** trên `songs/prision` (9 beat + 12 dạo đầu), dừng ở HG1 chờ tai Duy |
| finalize_beat · vocal_render · vocal_gate · mix · pack | **đã chạy thật** (2026-10-08) sau khi Duy duyệt beat; đang chờ tai Duy ở HG2. `memory` chưa chạy (chờ HG2) |
| `selftest` | 18 phép đạt (gồm 8 skill + bảng sửa lỗi) |
| `fix vao_nhac_lech` (sửa thật trên Prisión) | **đã chạy**: lệch dạo đầu so với gốc 267/−104 ms → 11/0 ms; cân bằng giọng−beat theo bản gốc; đang chờ tai Duy nghe lại |
| Bản phụ "kiểu Suno" (cần stem Suno của bài) | Prisión không có Suno → bỏ; No Pude làm tay (`../PHAN_TICH_SUNO.md`) |

Lỗi gặp khi chạy thật (đã sửa, ghi `memory/lessons.md`): semitone là số thực làm hỏng chỉ số (R11 chặn đúng sau 4 lần, `unblock` mở lại); tên file `*_latest.json` sai; biến trùng tên trong `beat_align`.
`songs/np_fixture/` là bài thử cũ của harness (dữ liệu No Pude), không phải đầu ra giao Duy.

## Lệnh nhanh
```
python run.py init prision --orig X.mp3 --inst beat.wav --vocals voc.wav --lyrics loi.txt [--semis -1] [--ratio 1.0]
python run.py auto prision                       # chạy tới cổng người / bị chặn (tự chạy `review` khi dừng)
python run.py intros prision --seeds 31,32,33   # tại HG1: Duy chê dạo đầu → render thêm ứng viên dạo đầu (nhanh), không làm lại cả beat
python run.py human prision HG1 pass --pick b1_cl_s7 --intro i1_am_s22 --note "..."
python run.py status|gates|review prision   |   python run.py selftest   |   python run.py unblock prision --why "..."
python run.py lab status|up|down
```
