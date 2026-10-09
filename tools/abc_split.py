"""Cắt bản nốt ABC (SheetSage2) thành các đoạn theo vạch '% verse / % interlude ...' để cover từng đoạn (bài rất dài hoặc đổi nhạc cụ liên tục, ví dụ The Return of the King).
Mang theo giọng (K:) và nhịp (M:) đang có ở đầu mỗi đoạn. MÁY KIỂM: nốt của từng đoạn (dời về 0) phải đúng bằng nốt của bản đầy đủ trong khoảng đó; hai bè phải khớp thời gian tại chỗ cắt.
  split_sections(text, target_s=150, min_tail_s=60) -> [(abc_text, start_s, end_s)]
"""
import re
import re
from abc_tools import parse_abc

NL = chr(10)


def split_sections(text, target_s=150.0, min_tail_s=60.0):
    lines = text.splitlines()
    first = next(i for i, l in enumerate(lines) if l.startswith("% "))
    header, body = lines[:first], lines[first:]
    # chỗ cắt hợp lệ: dòng 'V:' hoặc '% ' mà hai bè cùng giờ (con trỏ chênh < 0.05 s)
    cuts = [0]
    for i in range(1, len(body)):
        if body[i].startswith("V:") or body[i].startswith("% "):
            _, ct = parse_abc(NL.join(header + body[:i]) + NL, with_cursor=True)
            v = list(ct.values())
            prev = [l.strip() for l in body[max(0, i - 6):i] if l.strip() and not re.match(r"^([A-Za-z]:|%)", l.strip())]
            tied = any(re.search(r"-\|?$", l) for l in prev[-3:])   # nốt nối '-' ở cuối dòng: không cắt giữa nốt ngân
            if v and max(v) - min(v) < 0.05 and not tied:
                cuts.append(i)
    chunks = [body[a:b] for a, b in zip(cuts, cuts[1:] + [len(body)])]
    # trạng thái ở đầu mỗi chunk: giọng K, nhịp M, con trỏ thời gian từng bè
    key = next(l for l in header if l.startswith("K:"))
    meter = next((l for l in header if l.startswith("M:")), "M:4/4")
    state, acc = [], list(header)
    for ch in chunks:
        notes, cur_t = parse_abc("\n".join(acc) + "\n", with_cursor=True)
        state.append((key, meter, cur_t))
        acc += ch
        for l in ch:
            if l.startswith("K:"): key = l.strip()
            if l.startswith("M:"): meter = l.strip()
    full, _ = parse_abc("\n".join(header + body) + "\n", with_cursor=True)
    # chọn chỗ cắt: gom chunk đến khi >= target
    bounds, start_i = [], 0
    for i in range(1, len(chunks) + 1):
        t_end = max(state[i][2].values()) if i < len(chunks) else max(parse_abc("\n".join(header + body) + "\n", with_cursor=True)[1].values())
        t_start = max(state[start_i][2].values()) if state[start_i][2] else 0.0
        if t_end - t_start >= target_s or i == len(chunks):
            bounds.append((start_i, i)); start_i = i
    if len(bounds) > 1:
        a, b = bounds[-1]
        t_len = (max(state[b][2].values()) if b < len(chunks) else max(parse_abc("\n".join(header + body) + "\n", with_cursor=True)[1].values())) - max(state[a][2].values())
        if t_len < min_tail_s:
            bounds[-2] = (bounds[-2][0], b); bounds.pop()
    out = []
    for a, b in bounds:
        k, m, cur_t = state[a]
        vals = list(cur_t.values())
        if vals and max(vals) - min(vals) > 0.05:
            raise SystemExit(f"hai bè lệch giờ {max(vals)-min(vals):.2f}s tại chỗ cắt chunk {a}: dừng")
        t0 = max(vals) if vals else 0.0
        hdr = [k if l.startswith("K:") else (m if l.startswith("M:") else l) for l in header]
        seg = "\n".join(hdr + [l for ch in chunks[a:b] for l in ch]) + "\n"
        t1 = max(parse_abc("\n".join(header + [l for ch in chunks[:b] for l in ch]) + "\n", with_cursor=True)[1].values())
        sn = sorted((round(x + t0, 2), mi) for x, y, mi in parse_abc(seg))
        fn = sorted((round(x, 2), mi) for x, y, mi in full if t0 - 0.005 <= x < t1 - 0.005)
        if len(sn) != len(fn) or any(abs(p[0] - q[0]) > 0.03 or p[1] != q[1] for p, q in zip(sn, fn)):
            raise SystemExit(f"đoạn {a}-{b}: nốt đoạn KHÁC bản đầy đủ ({len(sn)} vs {len(fn)} nốt): dừng")
        out.append((seg, t0, t1))
    return out


if __name__ == "__main__":
    import sys
    src = open(sys.argv[1], encoding="utf-8").read()
    for i, (s, a, b) in enumerate(split_sections(src, float(sys.argv[2]) if len(sys.argv) > 2 else 150), 1):
        print(i, round(a, 1), round(b, 1), len(parse_abc(s)), "nốt")
