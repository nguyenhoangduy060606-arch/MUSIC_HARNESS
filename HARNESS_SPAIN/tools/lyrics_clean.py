r"""Dọn lời Duy dán (định dạng trang lời bài hát) thành lời cho YuE2/ACE. KHÔNG in lời ra màn hình (bản quyền), chỉ in số liệu.
Dùng: python tools/lyrics_clean.py songs/<bai>/01_analysis/lyrics_goc.txt   -> lyrics_ace.txt cùng thư mục
Làm: bỏ khối quảng cáo "You might also like" + tên bài/ca sĩ đi kèm; [Chorus: Tên ca sĩ] -> [Chorus]; sửa nhãn gõ lỗi ([ơntro] -> [Intro]);
bỏ phần bè/ad-lib trong ngoặc tròn (một giọng hát chính); bỏ dấu \ thừa; gộp dòng trống.
"""
import re, sys
from pathlib import Path

FIX = {"ơntro": "Intro", "intro": "Intro"}
src = Path(sys.argv[1])
lines, skip_ad = [], False
for raw in src.read_text(encoding="utf-8").splitlines():
    l = raw.strip().lstrip("﻿").strip("\\").strip()
    l = re.sub(r"^[^\[]*?(\[)", r"\1", l) if re.match(r"(?i)^(test|ơ)", l) else l   # tiền tố như "test4[ơ[Chorus..."
    if re.match(r"(?i)^you might also like", l):
        skip_ad = True; continue
    if skip_ad:
        if l.startswith("["):
            skip_ad = False
        else:
            continue
    if re.match(r"(?i)^(intro|outro|verse|chorus|bridge)[^\]]*\]$", l):   # nhãn thiếu dấu "[" (vd "intro]")
        l = "[" + l
    m = re.match(r"^\[+\s*([^\]:]+?)\s*(?::[^\]]*)?\]+\s*(.*)$", l)
    if m:
        tag = FIX.get(m.group(1).strip().lower(), m.group(1).strip())
        lines += ["", f"[{tag}]"]
        l = m.group(2).strip()
        if not l:
            continue
    l = re.sub(r"\s*\([^)]*\)", "", l).strip().rstrip("]").strip()
    if l:
        lines.append(l)
text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip() + "\n"
out = src.with_name("lyrics_ace.txt")
out.write_text(text, encoding="utf-8")
tags = re.findall(r"^\[([^\]]+)\]", text, re.M)
print(f"{out}: {sum(1 for x in text.splitlines() if x and not x.startswith('['))} dòng lời, {len(tags)} đoạn: {', '.join(tags)}")
