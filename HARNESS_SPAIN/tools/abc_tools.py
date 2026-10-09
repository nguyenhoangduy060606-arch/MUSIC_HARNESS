"""Đọc bản nhạc ABC (SheetSage2) thành danh sách nốt có thời gian. Chỉ dùng thư viện chuẩn."""
import re

FLATS = "BEADGCF"
SHARPS = "FCGDAEB"
MAJ = {"C": 0, "G": 1, "D": 2, "A": 3, "E": 4, "B": 5, "F#": 6, "F": -1, "Bb": -2, "Eb": -3, "Ab": -4, "Db": -5, "Gb": -6, "Cb": -7, "C#": 7}
MIN = {"Eb": -6, "D#": 6, "A": 0, "E": 1, "B": 2, "F#": 3, "C#": 4, "G#": 5, "D": -1, "G": -2, "C": -3, "F": -4, "Bb": -5}


def parse_abc(text, with_cursor=False):
    """-> list[(start_s, end_s, midi)] cho mọi giọng (mỗi giọng có con trỏ thời gian riêng). with_cursor=True -> (danh sách, {giọng: giây con trỏ})."""
    L = 1 / 16; qn = 1 / 4; bpm = 64.0; meter = 1.0
    key = {}
    notes, cursor, voice = [], {}, "default"
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("%"):
            continue
        m = re.match(r"^([A-Za-z]):\s*(.*)$", line)
        if m:
            f, v = m.group(1), m.group(2)
            if f == "L":
                a, b = v.split("/"); L = int(a) / int(b)
            elif f == "Q":
                mm = re.match(r"(\d+)/(\d+)=(\d+)", v.replace(" ", ""))
                if mm:
                    qn = int(mm.group(1)) / int(mm.group(2)); bpm = float(mm.group(3))
            elif f == "M":
                a, b = v.split("/"); meter = int(a) / int(b)
            elif f == "K":
                mm = re.match(r"([A-G][b#]?)(m|min|minor)?", v.strip())
                n = (MIN if mm.group(2) else MAJ).get(mm.group(1), 0) if mm else 0
                key = {x: -1 for x in FLATS[:-n]} if n < 0 else {x: 1 for x in SHARPS[:n]}
            elif f == "V":
                voice = v.split()[0]
            continue
        sec_per_whole = (60.0 / bpm) / qn            # giây cho một nốt tròn (1/1)
        bar_len = meter * sec_per_whole
        t = cursor.get(voice, 0.0)
        acc = {}
        i, s = 0, re.sub(r'"[^"]*"|![^!]*!', "", line)
        while i < len(s):
            c = s[i]
            if c in "|:[]":
                if c == "|":
                    acc = {}
                i += 1; continue
            mz = re.match(r"([Zz])(\d*)(?:/(\d*))?", s[i:])
            if mz and c in "Zz":
                n = int(mz.group(2) or 1)
                if c == "Z":
                    t += n * bar_len
                else:
                    d = n * L if mz.group(3) is None else n * L / int(mz.group(3) or 2)
                    t += d * sec_per_whole
                i += mz.end(); continue
            mn = re.match(r"(\^{1,2}|_{1,2}|=)?([A-Ga-g])([,']*)(\d*)(?:/(\d*))?(-)?", s[i:])
            if mn:
                a, ch, oc, num, den, tie = mn.groups()
                base = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}[ch.upper()]
                midi = 60 + base + (12 if ch.islower() else 0) + 12 * oc.count("'") - 12 * oc.count(",")
                name = ch.upper()
                if a:
                    acc[name] = {"^": 1, "^^": 2, "_": -1, "__": -2, "=": 0}[a]
                midi += acc.get(name, key.get(name, 0))
                d = int(num or 1) * L
                if den is not None:
                    d = d / int(den or 2)
                dur = d * sec_per_whole
                if notes and notes[-1][3] == voice and notes[-1][5] and abs(notes[-1][1] - t) < 1e-6 and notes[-1][2] == midi:
                    notes[-1][1] = t + dur; notes[-1][5] = bool(tie)
                else:
                    notes.append([t, t + dur, midi, voice, None, bool(tie)])
                t += dur
                i += mn.end(); continue
            i += 1
        cursor[voice] = t
    res = [(a, b, m) for a, b, m, *_ in notes]
    return (res, cursor) if with_cursor else res


def abc_end(text):
    """Giây kết thúc nốt cuối cùng của mọi giọng."""
    notes = parse_abc(text)
    return max(b for _, b, _ in notes) if notes else 0.0


def _keysig(v):
    mm = re.match(r"([A-G][b#]?)(m|min|minor)?", v.strip())
    n = (MIN if mm.group(2) else MAJ).get(mm.group(1), 0) if mm else 0
    return {x: -1 for x in FLATS[:-n]} if n < 0 else {x: 1 for x in SHARPS[:n]}


def _shift_chord(sym, semis, ktgt):
    """Dịch tên hợp âm trong ngoặc kép ("Dm", "A#maj7/C##") đi `semis` nửa cung (cả bè bass sau dấu /). Không phải hợp âm -> giữ nguyên."""
    flats = any(v < 0 for v in ktgt.values())
    names = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"] if flats else ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    pc = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}

    def root(m):
        v = pc[m.group(1)] + sum({"#": 1, "b": -1}[x] for x in m.group(2))
        return names[(v + semis) % 12]
    if not re.match(r"^[A-G][#b]*", sym):
        return sym
    return re.sub(r"(?:(?<=^)|(?<=/))([A-G])([#b]*)", root, sym)


def transpose_abc(text, steps, semis, new_key, bpm=None):
    """Dịch giọng bản ABC: mỗi nốt lên `steps` bậc chữ cái và `semis` nửa cung (vd Gm -> Fm: steps=-1, semis=-2),
    đổi K: sang `new_key`, Q: sang `bpm` nếu có. Giai điệu giữ nguyên hình dáng (mọi quãng y hệt), chỉ đổi cao độ chung + tốc độ."""
    LET = "CDEFGAB"; NAT = [0, 2, 4, 5, 7, 9, 11]
    ksrc, ktgt = {}, _keysig(new_key)
    out = []
    for raw in text.splitlines():
        line = raw.strip()
        m = re.match(r"^([A-Za-z]):\s*(.*)$", line)
        if not line or line.startswith("%") or m:
            if m and m.group(1) == "K":
                ksrc = _keysig(m.group(2)); raw = f"K:{new_key}"
            elif m and m.group(1) == "Q" and bpm:
                raw = re.sub(r"=\s*\d+", f"={bpm}", raw)
            out.append(raw); continue
        res, i, bsrc, btgt = [], 0, {}, {}
        while i < len(raw):
            c = raw[i]
            if c == '"' or c == "!":
                j = raw.index(c, i + 1) + 1
                res.append('"' + _shift_chord(raw[i + 1:j - 1], semis, ktgt) + '"' if c == '"' else raw[i:j]); i = j; continue
            if c == "|":
                bsrc, btgt = {}, {}
            mz = re.match(r"[Zz]\d*(?:/\d*)?", raw[i:]) if c in "Zz" else None
            if mz:
                res.append(mz.group(0)); i += mz.end(); continue
            mn = re.match(r"(\^{1,2}|_{1,2}|=)?([A-Ga-g])([,']*)", raw[i:])
            if not mn:
                res.append(c); i += 1; continue
            a, ch, oc = mn.groups()
            L = ch.upper()
            if a:
                bsrc[L] = {"^": 1, "^^": 2, "_": -1, "__": -2, "=": 0}[a]
            alt = bsrc.get(L, ksrc.get(L, 0))
            octv = 4 + (1 if ch.islower() else 0) + oc.count("'") - oc.count(",")
            midi = 12 * (octv + 1) + NAT[LET.index(L)] + alt + semis
            li = LET.index(L) + steps
            octv2, li2 = octv + li // 7, li % 7
            L2 = LET[li2]
            alt2 = midi - (12 * (octv2 + 1) + NAT[li2])
            assert -2 <= alt2 <= 2, (raw, i)
            acc = ""
            if alt2 != btgt.get(L2, ktgt.get(L2, 0)):
                acc = {1: "^", 2: "^^", -1: "_", -2: "__", 0: "="}[alt2]; btgt[L2] = alt2
            nm = L2 if octv2 <= 4 else L2.lower()
            marks = "," * (4 - octv2) if octv2 < 4 else "'" * (octv2 - 5) if octv2 > 5 else ""
            res.append(acc + nm + marks); i += mn.end()
        out.append("".join(res))
    return "\n".join(out) + "\n"


def drop_voice(text, voice="Vocal"):
    """Bỏ hẳn một bè khỏi ABC (dòng khai báo V: và mọi khối của bè đó). Dùng để thử: bỏ bè 'Vocal' trống có làm YuE2 bớt hát không."""
    out, skip = [], False
    for raw in text.splitlines():
        m = re.match(r"^V:\s*(\S+)", raw.strip())
        if m:
            skip = m.group(1) == voice
            if skip:
                continue
        elif skip and (raw.strip().startswith("%") or re.match(r"^[A-Za-z]:", raw.strip())):
            skip = False
        if not skip:
            out.append(raw)
    return "\n".join(out) + "\n"


def vary_melody(text, amount, seed=0, voice="Vocal", max_len=None):
    """Biến tấu nhẹ giai điệu (giảm giống bản gốc, vẫn nhận ra bài): trong bè `voice`, mỗi nốt NGẮN (không nối '-', độ dài <= max_len
    đơn vị L, mặc định = 1 phách đen) có xác suất `amount` bị dời lên/xuống 1 bậc trong thang âm của bài (bỏ dấu hoá riêng -> theo hoá biểu).
    Nốt đầu và cuối mỗi dòng nhạc giữ nguyên (khung câu). Trả về (abc_mới, số_nốt_đổi)."""
    import random
    rnd = random.Random(seed)
    LET = "CDEFGAB"
    out, cur, L, changed = [], None, 1 / 16, 0
    for raw in text.splitlines():
        s = raw.strip()
        mv = re.match(r"^V:\s*(\S+)", s)
        mh = re.match(r"^([A-Za-z]):\s*(.*)$", s)
        if mv:
            cur = mv.group(1)
        if mh and mh.group(1) == "L":
            a, b = mh.group(2).split("/"); L = int(a) / int(b)
        if mv or mh or not s or s.startswith("%") or cur != voice:
            out.append(raw); continue
        lim = max_len or round((1 / 4) / L)
        notes = list(re.finditer(r"(\^{1,2}|_{1,2}|=)?([A-Ga-g])([,']*)(\d*)(?:/(\d*))?(-)?", raw))
        # bỏ các khớp nằm trong "hợp âm" hoặc !trang trí!
        spans = [m.span() for m in re.finditer(r'"[^"]*"|![^!]*!', raw)]
        notes = [m for m in notes if not any(a <= m.start() < b for a, b in spans)]
        res, last = [], 0
        for i, m in enumerate(notes):
            acc, ch, oc, num, den, tie = m.groups()
            dur = int(num or 1) / (int(den or 2) if den is not None else 1)
            prev_tie = i > 0 and notes[i - 1].group(6)
            if 0 < i < len(notes) - 1 and not tie and not prev_tie and dur <= lim and rnd.random() < amount:
                li = LET.index(ch.upper()) + rnd.choice((-1, 1))
                octv = (1 if ch.islower() else 0) + oc.count("'") - oc.count(",") + li // 7
                L2 = LET[li % 7]
                nm = (L2.lower() if octv >= 1 else L2) + ("'" * (octv - 1) if octv > 1 else "," * (-octv) if octv < 0 else "")
                res.append(raw[last:m.start()] + nm + (num or "") + (f"/{den}" if den is not None else ""))
                last = m.end() - (1 if tie else 0); changed += 1
        res.append(raw[last:])
        out.append("".join(res))
    return "\n".join(out) + "\n", changed


def merge_voices(text, src="Vocal", dst="Ins"):
    """Gộp mọi nốt của bè `src` vào bè `dst` (bè `src` còn toàn dấu lặng), theo từng ô nhịp. Dùng khi giai điệu nằm ở bè 'Vocal' làm YuE2 hát:
    chuyển sang bè nhạc cụ. Chỗ hai bè cùng có nốt trong một ô thì giữ `dst` (đếm vào `lost`). Trả về (abc_mới, số_ô_gộp, số_ô_mất)."""
    head, body, cur = [], {src: [], dst: []}, None
    in_head = True
    for raw in text.splitlines():
        s = raw.strip()
        mv = re.match(r"^V:\s*(\S+)", s)
        if in_head and not mv and not re.match(r"^K:", s) and not s.startswith("%") or (in_head and mv and "clef" in s) or (in_head and s.startswith("K:")):
            head.append(raw)
            if s.startswith("K:"):
                in_head = False
            continue
        if s.startswith("%") or not s:
            continue
        if mv:
            cur = mv.group(1); continue
        if re.match(r"^[A-Za-z]:", s):
            body[cur].append(("hdr", s))   # M:/L:... xuất hiện ở cả hai bè cùng vị trí; ta chỉ lấy bản ở bè `dst`
            continue
        bars = [b for b in s.split("|") if b.strip() != ""]
        for b in bars:
            mz = re.fullmatch(r"\s*Z(\d*)\s*", b)
            if mz:
                body[cur] += [("bar", "Z")] * int(mz.group(1) or 1)
            else:
                body[cur].append(("bar", b.strip()))
    # hdr phải xuất hiện ở cả hai bè: ta đã thêm vào cả hai, nên hai danh sách cùng cấu trúc về hdr; kiểm số ô
    ns = sum(1 for k, _ in body[src] if k == "bar"); nd = sum(1 for k, _ in body[dst] if k == "bar")
    assert ns == nd, f"hai bè lệch số ô: {ns} vs {nd}"
    hasnote = lambda b: re.search(r"[A-Ga-g]", re.sub(r'"[^"]*"|![^!]*!', "", b)) is not None
    merged, lost, moved = [], 0, 0
    sb = [x for x in body[src] if x[0] == "bar"]; db = [x for x in body[dst] if x[0] == "bar"]
    i = 0
    for item in body[dst]:
        if item[0] == "hdr":
            merged.append(item); continue
        s_, d_ = sb[i][1], db[i][1]; i += 1
        if hasnote(s_) and not hasnote(d_):
            merged.append(("bar", s_)); moved += 1
        else:
            if hasnote(s_) and hasnote(d_):
                lost += 1
            merged.append(("bar", d_))
    out = list(head)
    chunk = []
    def flush(chunk):
        if not chunk:
            return
        n = len(chunk)
        out.append(f"V: {src}"); out.append("|".join(["Z"] * n) + "|" if n > 1 else "Z|")
        out.append(f"V: {dst}"); out.append("|".join(b for _, b in chunk) + "|")
    for item in merged:
        if item[0] == "hdr":
            flush(chunk); chunk = []
            out.append(f"V: {src}"); out.append(item[1]); out.append(f"V: {dst}"); out.append(item[1])
        else:
            chunk.append(item)
            if len(chunk) == 4:
                flush(chunk); chunk = []
    flush(chunk)
    return "\n".join(out) + "\n", moved, lost


def legato_fill(text, voice="Ins", max_gap=0.5):
    """Làm bản nốt 'liền' hơn: dấu lặng ngắn (z, tối đa `max_gap` nốt tròn = 2 phách) ngay sau một nốt được nối vào nốt đó bằng dấu nối (cùng cao độ).
    Chuỗi cao độ và thời điểm vào của từng nốt GIỮ NGUYÊN, chỉ có nốt ngân dài hơn. Lặng cả ô (Z) giữ nguyên. Mục đích: bài rất thưa làm YuE2 hát/cụt;
    bản nốt liền hơn cho model ít 'chỗ trống' để bịa. Trả về (abc_mới, số_chỗ_nối)."""
    out, cur, L, filled = [], None, 1 / 16, 0
    last_idx, last_pitch = None, None
    # Dấu tạm thời (^ _ =) chỉ có hiệu lực trong ô nhịp: nốt nối sang ô sau phải mang cùng cao độ.
    # Chỉ cho nối qua vạch nhịp khi nốt KHÔNG chịu dấu tạm thời nào trong ô (viết lại y nguyên vẫn đúng cao độ, không làm đổi nốt khác).
    bar_acc, last_safe = set(), False
    pat = re.compile(r"""("[^"]*"|![^!]*!)|([Zz])(\d*)(?:/(\d*))?|((?:\^{1,2}|_{1,2}|=)?[A-Ga-g][,']*)(\d*)(?:/(\d*))?(-)?|(\|)|(.)""")
    for raw in text.splitlines():
        s = raw.strip()
        mv = re.match(r"^V:\s*(\S+)", s)
        mh = re.match(r"^([A-Za-z]):\s*(.*)$", s)
        if mv:
            cur = mv.group(1); last_idx = last_pitch = None
        if mh and mh.group(1) == "L":
            a, b = mh.group(2).split("/"); L = int(a) / int(b)
        if mv or mh or not s or s.startswith("%") or cur != voice:
            out.append(raw); continue
        res, last_idx = [], None
        bar_acc = set()
        for m in pat.finditer(raw):
            deco, zc, zn, zd, pitch, num, den, tie, bar, other = m.groups()
            if bar:
                if last_idx is not None and not last_safe:
                    last_idx = None
                bar_acc = set()
                res.append(bar); continue
            if deco is not None:
                res.append(deco)
            elif zc:
                if zc == "z":
                    n = int(zn or 1); d = (n * L) if zd is None else n * L / int(zd or 2)
                    if last_idx is not None and d <= max_gap + 1e-9:
                        if not res[last_idx].endswith("-"):
                            res[last_idx] += "-"
                        res.append(last_pitch + (zn or "") + (f"/{zd}" if zd is not None else ""))
                        last_idx = len(res) - 1; filled += 1
                        continue
                last_idx = None; res.append(m.group(0))
            elif pitch:
                res.append(m.group(0))
                base = pitch.lstrip("^_=")
                if base != pitch:
                    bar_acc.add(base)
                last_safe = base == pitch and base not in bar_acc
                last_idx, last_pitch = (None, None) if tie else (len(res) - 1, pitch)
            else:
                res.append(m.group(0))
        out.append("".join(res))
    return "\n".join(out) + "\n", filled
