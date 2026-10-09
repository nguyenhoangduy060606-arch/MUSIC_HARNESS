# Project Spain — MAPPING VÒNG 4 (bản cuối, làm luôn) — 2026-10-07

Theo nhận xét của bên yêu cầu (người nghe norteño thường xuyên), Duy chuyển lời:
1. **Rè nhẹ** cả bài (hoặc chỉ bản `3_len_nua_cung_sierreno`). Duy đoán là tiếng lắc hạt.
2. Muốn có **accordion** (đàn kéo).
3. **Giọng mượt hơn, hay hơn**. Được phép cho hát lại khác đi.

Workflow cố định: **beat = model MỚI** (SheetSage2 → bản nốt → YuE2), **giọng = model CŨ** (ACE). Không tự viết nốt.
Ký hiệu: **[ĐO]** máy đo · **[ĐOÁN]** suy luận · **[?]** chưa biết.

---

## 1. Tiếng "rè" nằm ở đâu — đo hôm nay

| Phần | Số đo | So với gốc | Kết luận |
|---|---|---|---|
| **Giọng ACE** | ở chỗ ca sĩ **không hát**, nền xì còn −24 đến −28 dB | giọng gốc: −43 đến −48 dB | **Có lớp xì thường trực, to hơn gốc ~20 dB** [ĐO]. Đây là nguồn rè số 1. |
| Giọng ACE "lên nửa cung" (V3) | dải cao 0.69% / 4.15%, độ "sạn" 0.60 / 0.69 | xuống nửa cung (V2): 0.25% / 3.32% | **V3 xì nhiều nhất**, khớp với lời chê bản `3_len` [ĐO] |
| Đổi cách chạy ACE (8 → 32 bước, độ bám 0.3–0.8) | nền vẫn −28.5 dB | | **Không chữa được bằng cài đặt ACE** [ĐO]. Lớp xì do chính đầu ra của ACE. |
| **Bản trộn** | đỉnh chạm trần 0.036–0.086% thời gian, độ "thở" 11.6 dB | gốc: 0.003% (No Pude), 17.7 dB | **Nén quá to** (mình master −9.5 LUFS) [ĐO] → bè tiếng, dễ rè ở chỗ to |
| Beat ACE (lắc hạt?) | số cú lắc/gõ dải cao 3.1–3.4 mỗi giây | gốc 3.45 | **Lắc hạt không dày hơn gốc** [ĐO], nhưng dải cao của beat "sạn" hơn (0.70 so với 0.61) |

→ Rè = **(1) xì nền của giọng ACE + (2) master quá to**, cộng một phần từ (3) dải cao của beat ACE. Lắc hạt có thể góp phần nhưng không phải chính [ĐOÁN].

## 2. Kế hoạch — 3 phần, chạy luôn

### A. Beat mới = YuE2 (model mới), accordion bắt buộc
1. SheetSage2 chép nốt từ **beat tách gốc** (chỉ lấy nốt, không lấy âm thanh).
2. Máy chỉnh bản nốt: xuống nửa cung, tốc độ = số đo thật × 0.96 (khớp giọng), bỏ phần giai điệu hát, nối nốt ngắn để bản nốt không quá thưa.
3. YuE2 chơi beat, lời tả nhạc cụ ghi rõ **accordion là đàn chính** (dạo đầu, câu chèn, dạo giữa) + bajo sexto + bass + trống nhẹ, **không lắc hạt**.
4. Lượt 1: mỗi bài 6 bản (3 seed × 2 kiểu tả). Máy lọc theo bảng dưới. Giữ 3 bản tốt nhất làm gói nghe beat (dạo đầu trước).

| Cổng lọc beat | Ngưỡng |
|---|---|
| Có accordion (máy nghe nhạc cụ) | bắt buộc ở dạo đầu |
| Không tự hát | giọng ≤ 15% |
| Khớp nhịp giọng | lệch ≤ 40 ms mọi đoạn 20 s (sau khi căn) |
| Đủ dài | ≥ 90% bài |
| Không dính full | âm thanh giống gốc ≤ 0.60 mọi đoạn |
| Không rè | dải cao không "sạn" hơn beat gốc |

### B. Giọng hát lại = ACE (model cũ), mượt hơn
1. **Chọn cung: xuống nửa cung, chậm 4% (V2) cho cả 2 bài.** Lý do [ĐO]: V3 xì nhiều nhất, và bản bị chê rè là V3. Beat theo đúng cung này.
2. ACE hát lại từ giọng gốc đã dời cung (cách vòng 3, đã chỉ dính melody). Thêm 2 kiểu tả giọng để nghe so: *như vòng 3* và *mượt, ấm, legato, ít gắt*. Mỗi kiểu 2 seed.
3. **Làm sạch xì** (khâu trộn): ở chỗ ca sĩ gốc không hát (máy biết chính xác từ giọng gốc) thì hạ nhỏ giọng ACE. Chỗ đang hát thì lọc xì nhẹ, giảm chữ "s" chói. Cổng: **nền ≤ −40 dB** (gần gốc).
4. **Lời:** hiện có lời máy chép (Whisper, đã sửa tay), nằm trong `songs/es_no_pude/01_analysis/lyrics_ace.txt` và `songs/es_prision/01_analysis/lyrics_ace.txt`. File lời chuẩn `lyrics_goc.txt` **chưa có**. Duy dán lời chuẩn vào `songs/<bài>/01_analysis/lyrics_goc.txt` (mỗi bài một file) thì mình hát lại giọng thêm 1 lượt, mất ~5 phút. Mình không in lời ra chat.

### C. Trộn lại
- Master **−14 LUFS** (mức YouTube dùng) thay cho −9.5. Đỉnh −1 dB. Độ "thở" ≥ 14 dB (gốc 17.7).
- Beat: cắt bớt dải cao chói. Giọng: nén nhẹ, vang ấm vừa phải.
- Cổng: đỉnh chạm trần ≤ 0.01% thời gian, không méo.

## 3. Thứ tự chạy (lab, 1 việc 1 lúc)
1. Mở ComfyUI lab → SheetSage chép nốt 2 bài → YuE2 12 bản beat (~30 phút) → tắt ComfyUI.
2. ACE hát lại 8 bản giọng (~15 phút).
3. Lọc beat + giọng → trộn 2–3 bản tốt nhất mỗi bài.
4. Gói nghe `project spain/NGHE/vong4/<bài>/`:
   - `0_ban_goc`
   - `beat_1..3` (chỉ beat, nghe dạo đầu 0:00–0:25)
   - `full_1..2` (beat + giọng mới)
   - kèm `.lof` cho Audacity, `LISTEN.md`
5. Duy và bên yêu cầu nghe → chưa ổn thì chạy lượt 2 theo nhận xét.

Theo dõi trực tiếp: `project spain/LAB/NHAT_KY.md`.

## 4. Rủi ro nói trước
- [?] Xuống nửa cung có làm YuE2 mất chất norteño không: lần trước hạ 1 cung + chậm 10% thì mất [ĐO]. Lượt 1 đo ngay. Nếu mất: thử beat ở cung V3 (khi đó giọng cũng chuyển V3 + làm sạch xì).
- [?] YuE2 có bỏ được lắc hạt khi dặn không: YuE2 nghe lời tả nhạc cụ khá lỏng [ĐO Skyrim/Witcher].
- [?] Khớp nhịp: bài gốc giữ nhịp đều, YuE2 giữ tốc độ bản nốt [ĐO]. Bản nào trôi lung tung thì loại.
- Content ID: giọng vẫn từ giọng gốc dời cung (như vòng 3, đã chỉ dính melody). Beat YuE2 là bản thu mới hoàn toàn. Duy upload test mới là kết luận.
