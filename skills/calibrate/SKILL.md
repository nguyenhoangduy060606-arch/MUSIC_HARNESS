---
name: calibrate
description: Ghi lời khen/chê của Duy (và bên yêu cầu) cùng số đo vào bộ nhớ hiệu chuẩn để máy học tai Duy; quyết định khi nào một cổng 'chỉ báo cáo' được nâng thành 'cứng'.
---

# calibrate — dạy máy nghe bằng tai Duy

**Vì sao:** máy hiện KHÔNG phân biệt được intro Duy chê với intro Duy khen (chroma, nốt, nhịp gõ đều ngang nhau). Mỗi lời Duy là một nhãn quý.

## Mỗi khi Duy nói gì về nghe
1. Ghi bằng lệnh đúng chỗ: `python run.py human <bài> HG1|HG2 pass|fail --pick ... --intro ... --note "<nguyên văn>"` (tự ghi `memory/calibration.json` + `memory/lessons.md` kèm số đo của mọi bản trong vòng đó).
2. Lời Duy ngoài cổng (nhận xét thêm): thêm tay một dòng `memory/lessons.md` dạng `- <ngày> [<bài>] <nguyên văn lời Duy>`.
3. Nếu Duy nói **tên bản + khen/chê**: ghi cả hai nhóm (khen / chê) để so số.

## Nâng cổng `report` → `hard` (R8, R10)
Chỉ khi có ≥ 2 bài và con số **tách được** nhóm khen với nhóm chê (không chồng lấn), rồi Duy đồng ý:
`python run.py gate-set beat <gate_id> <giá_trị> --why "<bằng chứng>" --duy-ok`
Không có `--duy-ok` thì lệnh từ chối. Không tự đổi ngưỡng để bản "đạt".

## Cổng đang chờ hiệu chuẩn (đến 2026-10-08)
`intro_chroma`, `intro_onset`, `intro_first_onset_dev_s`, `start_lag_ms`, `start_corr`, `bal_vs_orig`, `abc_first_note_gap_s`. Số liệu so sánh nằm ở `memory/calibration.json`. Mốc ban đầu: bản Duy khen (b1_am_s7 + i1_am_s22/21/23) có `intro_match` 0.65–0.72; chưa đủ để kết luận.
