# Test Suno — No Pude Enamorarme Más: phân tích + 2 bài thử (2026-10-07)

Nguồn: `project spain/suno no pude/` (Duy tách sẵn: `audio [music].mp3` = beat, `audio [vocals].mp3` = giọng).
Ký hiệu: **[ĐO]** máy đo · **[ĐOÁN]** suy luận · **[?]** chưa biết.
Mình hiểu "đăng lên báo tác quyền" là bản Suno đã đăng và bị báo bản quyền, nhưng Duy chưa nói là **loại nào** (melody hay full): xin Duy bổ sung ở cuối.

## 1. Bản Suno làm gì (so với bài gốc)

| | Bài gốc | Suno | |
|---|---|---|---|
| Cung | Bb trưởng | **Bb trưởng** | giống [ĐO] |
| Tốc độ | 99.9 phách/phút, đều | **98.4**, đều cả bài (chậm hơn 1.5%) | [ĐO] |
| Dài | 3:30 (giọng hát hết ~3:21) | **3:21** (giọng hát hết ~2:57) | [ĐO] |
| Bố cục | dạo đầu → lời → dạo giữa → lời → kết | **cùng khung**: giọng vào 0:18, dạo giữa ~1:36–1:54; **bỏ đoạn kết** (bridge + outro) | [ĐO] |
| Tầm giọng | nam, giữa D4 | **nam, giữa D4** (cùng tầm) | [ĐO] |
| Giọng giống ca sĩ gốc | | **0.85** (cùng ca sĩ giữa 2 bài của ông: 0.91) | [ĐO] "khác hoàn toàn" đúng ở màu giọng, nhưng cùng loại giọng |
| Lời | | hát **rõ đúng lời chuẩn** (độ sai 0.08) | [ĐO] |

**Beat Suno:**
- Nốt/hợp âm **giống bản gốc** (0.86–0.89 sau khi căn), nhưng âm thanh bản thu khác (**0.43–0.55**): đúng chất "bản thu mới, nhạc cũ". Bản chép nốt dày 2.4 nốt/giây (gốc 2.2). [ĐO]
- Căn vào beat gốc phải bù **23 lần hụt/thừa phách** → Suno không chép từng ô nhịp của bản gốc, tự tạo lại phần chèn. [ĐO]
- Nhạc cụ (máy nghe): **accordion 40% + sax 40% + trống bộ 17%**. [ĐO, máy cũng đo bản gốc ra "kèn" nên chỉ tham khảo]
- Bản **sáng và "sạn" hơn** gốc: dải 6–14 kHz chiếm **5.0%** (gốc 1.1%), độ nhám dải 4–10 kHz 0.73 (gốc 0.61). [ĐO]
- Sạch giọng: không còn tiếng hát lọt trong beat. Giọng đã tách cũng sạch (nền −66 dB). [ĐO]

**Nhận xét:** Suno cho một **bản thu mới, cùng cung, cùng khung bài, nhịp đều**, giọng nam cùng tầm. Mức giống bản thu gốc 0.43–0.55 nằm trong khoảng "chỉ dính melody" mình đã đo ở vòng 3 (0.48–0.62).

## 2. Mình làm gì

| | Cách làm |
|---|---|
| Beat "ta" giống beat Suno | SheetSage2 chép nốt **beat Suno** → hạ 1 nửa cung (cung A) → YuE2 chơi lại bằng accordion/sax/trống/bajo sexto. 9 bản (3 kiểu × 3 seed) → lọc → chọn 2. Căn vào lưới phách Suno. |
| Giọng "ta" lên beat Suno | Giọng ca sĩ gốc (bản tách của Duy) → **kéo về đúng giờ từng chữ của giọng Suno** (DTW + WORLD) → hạ 1 nửa cung → ACE hát lại (k 0.1) với lời chuẩn (bỏ đoạn kết Suno không hát). Lệch giờ với giọng Suno: ≤ 60 ms [ĐO]. |
| Giọng phụ (tham khảo) | ACE hát lại thẳng từ **giọng Suno** (hạ 1 nửa cung): giống giọng Suno 0.91, giống ca sĩ gốc 0.85. |
| Làm sạch + trộn | như vòng 4: giọng bỏ xì nền, master −14 LUFS. |

## 3. Số đo các bản giọng

| Bản giọng | Giống ca sĩ gốc | Giống giọng Suno | Độ sai lời | Nốt đúng so với nguồn |
|---|---|---|---|---|
| **V1** (ca sĩ gốc kéo về giờ Suno) **A seed 7** ← dùng | **0.92** | 0.86 | 0.39 | 74% |
| V1 B seed 42 | 0.92 | 0.85 | 0.41 | 74% |
| V1 A seed 42 | 0.92 | 0.85 | 0.85 (có đoạn lặp) | 74% |
| V2 (hát lại từ giọng Suno) A seed 7 | 0.85 | **0.91** | **0.07** | 79% |

V1 sai lời nhiều hơn vòng 4 (0.21–0.29) vì nguồn đã qua WORLD (méo nhẹ); V2 rõ lời nhất vì nguồn Suno rõ.

## 4. Số đo các bản beat "ta" (so với beat Suno / so với bản thu gốc, 4 đoạn: dạo đầu / lời 1 / dạo giữa / lời 2)

| Bản | accordion / sax % | khớp nhịp | hụt phách | giống Suno | giống bản gốc |
|---|---|---|---|---|---|
| **cl_s2** ← bản 2 | 82 / 18 | 0.64 (23 ms) | 0 | 0.52 / 0.53 / 0.52 / 0.51 | 0.50 / 0.49 / 0.48 / 0.46 |
| **su_s7** ← bản 3 (đủ accordion + sax như Suno) | 50 / 49 | 0.52 (23 ms) | 3 | 0.39 / 0.46 / 0.47 / 0.45 | 0.41 / 0.48 / 0.49 / 0.51 |
| 7 bản còn lại | | | | loại: hụt phách 3–12 lần hoặc khớp nhịp kém hoặc giống bản gốc quá 0.6 | |

(So sánh: beat Suno thật giống bản gốc 0.43–0.55.) Tức beat "ta" **giống beat Suno về nốt/khung** (cùng bản nốt) và **cách bản thu gốc xa tương đương Suno**.

## 5. Gói nghe: `project spain/NGHE/suno_test/`
Xem `LISTEN.md` trong đó. Bản đăng −14 LUFS: `ban_giao_-14LUFS/`.

## 6. Duy bổ sung
- Loại báo bản quyền của bản Suno: ___ (melody / full / phần nào của bài?)
- Nghe xong: beat "ta" có giống beat Suno về cảm giác không? Giọng V1 có "gần giống" như ý không?
