# BÀI HỌC HARNESS_SPAIN — gốc: phiên 2026-10-07 (Project Spain vòng 4 + test Suno). Duy bổ sung mục D. run.py ghi thêm cuối file.

Ký hiệu: [ĐO] máy đo · [DUY] Duy nói · [LỖI] mình làm sai và sửa · [?] chưa chắc.

## A. Quy trình / luật Duy nhắc lại
1. [DUY] Bài có lời: **beat = model MỚI (SheetSage2 → ABC → YuE2), giọng = model CŨ (ACE)**. Vòng 3 làm beat bằng ACE là sai quy trình.
2. [DUY] **Không tự viết bản phối bằng nốt** ("không chắc tự đánh lại hay được"): chỉ biến đổi bản nốt chép bằng máy (cung, tốc độ, bỏ bè hát, nối nốt ngắn), rồi cho YuE2 đánh nhiều seed/kiểu cho đến khi tai Duy nói ổn.
3. [DUY] Gửi Duy **gói chỉ-beat trước** (nghe dạo đầu trước), gói đủ bài sau.
4. [DUY] Cơ chế Content ID (thông tin đối tác): giống beat **hoặc** giọng → báo **melody**; giống cả hai, hoặc 1 trong 2 > 80% → báo **full**. Mốc nội bộ mình dùng: beat giống bản thu gốc (log-phổ, `beat_doan.py`) ≤ 0.60 (NP) / 0.62 (PR). Thước của mình ≠ máy YouTube.
5. [DUY] Bên yêu cầu (người nghe norteño thường xuyên) soi kỹ: **rè**, **thiếu accordion**, giọng chưa mượt. Accordion là chữ ký bắt buộc của beat.
6. Lời chuẩn: Duy gửi file .txt → `songs/<s>/01_analysis/lyrics_goc.txt` → `lyrics_clean.py` → `lyrics_ace.txt` (không in lời ra chat). Thêm nhãn [Intro]/[Bridge]/[Outro] cho đoạn không hát.

## B. Kỹ thuật đã đo
7. [ĐO] "Rè" = (a) giọng ACE có **lớp xì nền** −24..−28 dB ở chỗ không hát (gốc −43..−48), đổi bước/độ bám của ACE không hết; (b) **master −9.5 LUFS** làm đỉnh chạm trần nhiều gấp 10–30 lần gốc. Sửa: `vocal_clean.py` (cổng theo giọng nguồn + lọc phổ, nền → −66..−75 dB) và `mix_v4.py` (−14 LUFS, không đẩy 3 kHz).
8. [ĐO] YuE2 giữ nhịp đều trong 1 bản nhưng **lệch ±1% theo seed** và có seed **hụt/thừa phách** (0–35 lần). `beat_align.py`: ghép phách bằng DTW + cắt-ghép mỗi 4 phách, không kéo méo. Cổng: hụt phách ≤ 2, tản ≤ 60 ms.
9. [ĐO] Chép nốt từ **beat tách** (mode full, Vocal = nghỉ + hợp âm) → YuE2 ra accordion 40–98%, giọng 0–5%. Bản nốt dày ≥ 1.3 nốt/giây là đủ. Phần "giọng" của CLAP đo beat gốc ra "kèn" (accordion 14.5%) → không tin CLAP tuyệt đối.
10. [ĐO] Tỷ lệ bản beat qua cổng: ~25–50%. Cần chạy 6–12 bản/bài.
11. [ĐO] Đưa giọng ca sĩ gốc về **giờ của một bản khác** (vd Suno): `vocal_warp.py` (DTW chroma+MFCC → WORLD) rồi ACE hát lại → lệch ≤ 60 ms, giống ca sĩ gốc 0.92. Nguồn qua WORLD làm tăng sai lời (0.2 → 0.4).
12. [ĐO] Test Suno: xem `project spain/PHAN_TICH_SUNO.md`. Suno = cùng cung Bb, nhịp đều 98.4, cùng bố cục, bỏ đoạn kết, giọng nam cùng tầm (giống gốc 0.85), beat sáng và sạn hơn (6–14 kHz 5.0% vs 1.1%), giống bản thu gốc 0.43–0.55.
13. Whisper hay **ảo giác/lặp** ở đoạn dạo giữa (122 từ trong 30 s): không tin số từ, chỉ tin khi so với lời chuẩn.

## C. Lỗi mình đã gặp (để khỏi lặp)
14. [LỖI] "nửa cung" của Duy = **1 semitone** (A vs Bb), mình có lúc dùng nhầm −0.5. Hỏi/ghi rõ.
15. [LỖI] Gọi `nhat_ky.py` mà không đặt `LAB_OUT` thì dòng nhật ký rơi vào `game/skyrim/LAB/NHAT_KY.md` (đã xoá tay 1 dòng). Luôn đặt `LAB_OUT="project spain/LAB"`.
16. [LỖI] Ghi nhầm đơn vị "chạm trần" (%, ×100) trong mapping, đã sửa. Kiểm lại đơn vị trước khi báo.
17. Chạy lệnh VM: viết file `.ps1` rồi `scp` + `ssh -File`, đừng nhồi lệnh trong dấu nháy (hỏng `$`/`&`). Đặt tên script đo khác `re.py` (trùng thư viện Python).
18. Lab: kiểm GPU trước, `/free` sau mỗi lượt YuE2 rồi mới chạy ACE, tắt lab bằng cách dừng tiến trình có `main.py --port 8288`.

## D. Duy bổ sung (điền sau)
- Báo bản quyền của bản Suno: loại ___ ; phần nào ___ .
- Nhận xét tai của Duy / bên yêu cầu về vòng 4: ___
- Bài học khác Duy muốn ghi: ___

## E. Thêm sau phản hồi của Duy (2026-10-07, cuối phiên)
19. [DUY] Bản vòng 4 (3 bản) **đánh lỗi ở dạo đầu**; bản cover beat theo cách Suno **hay**; bản "kiểu Suno" được xếp là **bản phụ**, bản chính vẫn là quy trình mới.
20. [LỖI] Mình không nhận ra lỗi intro vì không có cổng riêng cho intro; mọi số là trung bình cả bài. [ĐO] Các số riêng intro (chroma 0.80–0.85 vs 0.79–0.86; khớp chuỗi nốt 0.73–0.82 vs 0.65–0.75; nhịp gõ 0.34–0.38 vs 0.35–0.41) **không tách** bản Duy chê với bản Duy khen → máy hiện không đo được "intro lỗi" mà Duy nghe. Luật mới: intro do tai Duy quyết (HG1, nghe 25 s đầu trước).
21. [ĐO] Điểm khác có thật giữa bản chê và bản khen: nguồn bản nốt (beat tách từ bản gốc vs beat sạch của Suno), tốc độ (chậm 4% vs tự nhiên), và bản chê mở đầu gần như im lặng, nốt đầu lệch 0.28–0.51 s so với tiếng đầu của gốc. [ĐOÁN] chưa biết cái nào gây lỗi → thử A/B ở bài Prisión.

- 2026-10-07 [harness] cổng start_lag_ms thêm làm 'hard' rồi hạ về 'report' ngay trước khi chấm bản nào (đo cho thấy xcorr nhầm đỉnh 1 phách; sửa thử đầu bài: tốt 2/6, xấu 1/6, nên TẮT). Tự ghi nhận vì R10; Duy không yêu cầu.

## F. Chạy thật Prisión (2026-10-07, harness lần đầu)
22. [ĐO] Prisión @ tốc độ TỰ NHIÊN (ratio 1.0, học từ Suno): 6/9 beat có 6 s đầu lệch ≤ 11 ms so với bản gốc; No Pude vòng 4 @ chậm 4% (ratio 0.96): 5/6 beat lệch ~620 ms (1 phách). Gợi ý mạnh: chậm 4% làm hỏng khớp đầu bài. [?] chưa chứng minh nhân quả (khác bài).
23. [ĐO] Cả 2 bài: bản nốt SheetSage đặt nốt đầu trễ 0.6–0.67 s so với tiếng đầu thật; dạo đầu YuE2 vì vậy lệch 0.3–0.7 s → căn bằng MỘT độ lệch chung (introalign), không cắt-ghép từng nhóm phách (đã thử cắt-ghép: chọn nhầm đỉnh 1 phách, tốt 2/6 xấu 1/6, TẮT).
24. [ĐO] Tỷ lệ qua cổng beat Prisión vòng 1: 2/9 (chủ yếu hụt/thừa phách của YuE2). Dạo đầu riêng (đoạn ngắn): 5/12 qua lọc nhẹ (accordion ≥ 40%).
25. [LỖI] R11 ngăn đúng một vòng lặp vô ích khi mã lỗi (semitone float); cần lệnh `unblock` có ghi lý do. [LỖI] Mình thêm cổng start_lag làm "hard" rồi hạ về "report" khi chưa chấm bản nào (ghi ở trên).
26. [ĐO] Máy không phân biệt được intro bản Duy chê/khen (chroma, nốt, nhịp gõ, lift bám bản nốt đều ngang nhau). Chỉ có tai Duy → HG1 đặt intro lên đầu.

- 2026-10-08 [prision] HG1 pass pick=b1_am_s7 — Duy: Duy: i1_am_s22, i1_am_s23, i1_am_s21 và b1_am_s7 là 3-4 bản hoàn hảo nhất (đều, mượt). b1_cl_s7 cũng ok nhưng có sạn nhỏ ở đoạn tiến đàn sax, chưa đều mượt bằng. Duyệt phần beat.

## G. Duyệt beat Prisión (2026-10-08) và chạy tiếp
27. [DUY] Hoàn hảo nhất: dạo đầu riêng i1_am_s22 / s23 / s21 và beat b1_am_s7 (đều, mượt); b1_cl_s7 ok nhưng đàn sax còn sạn nhỏ (chưa đều mượt). → Kiểu "am" (accordion ấm, bajo sexto, trống nhẹ, KHÔNG sax) thắng kiểu "cl"/"su" có sax ở Prisión. [DUY→gợi ý] Sax là chỗ sạn: với bài kế tiếp ưu tiên "am" trước.
28. [ĐO] Thứ tự bản Duy chọn trùng thứ hạng của điểm "trùng nốt mở đầu" trong nhóm dạo đầu (s22 0.717 > s21 0.662 > s23 0.649, đều ≥ 0.64); nhóm bị loại (accordion < 40%) Duy không nghe. Mới 1 bài, chưa đủ để nâng thành cổng cứng.
29. [ĐO] Chuỗi finalize→vocal→mix→pack chạy một mạch không lỗi: giọng B (mượt) qua cổng, A (sáng) rớt vì sai lời (0.59, 2.74); nền xì −70..−71 dB; master −14.0 LUFS, chạm trần 0–0.001%, độ thở 15.7–16.2 dB; ghép dạo đầu tại 20.875 s sạch (không gai, không nhảy mức).
30. [LỖI nhỏ] pack cắt tên file 40 ký tự làm 2 bản trùng tên nhìn giống nhau; đã đổi thành 1_giong_<kiểu>_<seed>.

- 2026-10-08 [prision] HG2 pass pick=1_giong_v1_B_s42 — Duy: Duy: giọng nghe rõ, giọng hay, beat hay. Content ID chỉ dính MELODY (chấp nhận). Lỗi nhỏ: đoạn VÀO NHẠC hơi không khớp beat, có thể do beat hơi to.

## 2026-10-08 — prision (tự động ghi)
- vòng beat dùng: 1, vòng giọng: 1
- beat được Duy chọn: b1_am_s7
- lời Duy: xem memory/calibration.json (mục song=prision)
- Duy bổ sung bài học vào đây: ___

## H. Duyệt Prisión + sửa lỗi + hoàn thiện (2026-10-08)
31. [DUY] Prisión: giọng nghe rõ, giọng hay, beat hay; Content ID chỉ dính MELODY (chấp nhận). Lỗi nhỏ: đoạn vào nhạc hơi không khớp beat, có thể beat hơi to. → Duyệt.
32. [ĐO] Chẩn đoán lỗi vào nhạc: (a) dạo đầu ghép (render riêng, căn bằng 1 độ lệch chung) vẫn lệch pha so với bản gốc +267/−104 ms ở 10–20 s và trôi ~1% so với beat chính, nên có cú nhảy pha ngay chỗ ghép ~20.9 s; (b) cân bằng giọng−beat −6.4 dB so với −4.4 dB của bản gốc → beat to hơn gốc 2 dB. [Đúng với lời Duy.] Cách sửa: `joinfit` (khớp pha + co giãn ≤2% dạo đầu theo beat chính trước khi ghép), `mix_master --target-bal` (trộn đúng mức cân bằng của bản gốc) + hạ beat 1 dB khi có giọng. Kết quả: lệch 10–20 s còn +11/0 ms.
33. [ĐO] Giờ vào của giọng so với phách: không đo được ở bản gốc bằng ngưỡng RMS (rò tiếng từ bước tách); bỏ phép đo này.
34. Harness hoàn thiện: 8 skill (`skills/`), `fix` (bảng `config/fixes.json`, 11 triệu chứng), `redo`, `unblock`, `review`, `selftest` 18 phép, khóa ngưỡng bằng mã băm, vòng dạo đầu riêng (`intros`), gợi ý theo lỗi cho vòng sau.
35. [Chưa làm / thành thật] Bản phụ kiểu Suno chưa tự động; hiệu chuẩn mới có 4 mục; R3,R5,R7-R9,R12,R13,R15 vẫn là chữ; chưa có "agent thứ hai" đọc lại kết quả.
