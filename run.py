#!/usr/bin/env python
"""HARNESS_SPAIN — bộ điều khiển (máy trạng thái + vòng lặp + cổng). Chỉ dùng thư viện chuẩn Python.
  python run.py init   <bai> --orig X.mp3 --inst X.wav --vocals X.wav --lyrics X.txt [--semis -1] [--ratio 1.0] [--gate-sim 0.62]
  python run.py status [<bai>]            python run.py next <bai>          python run.py exec <bai>     (một bước)
  python run.py auto   <bai>              (tự chạy tới khi gặp cổng người / bị chặn / xong)
  python run.py human  <bai> HG1|HG2 pass|fail [--pick TEN] [--note "..."] [--redo beat|vocal]
  python run.py fix    <bai> <trieu_chung> [--note ".."]     (xem config/fixes.json)      python run.py redo <bai> <buoc>
  python run.py gates  <bai> [buoc]       python run.py gate-set <buoc> <gate_id> <gia_tri> --why "..." --duy-ok
  python run.py lab up|down|status        python run.py check-guard "<chuoi>"
Luật: RULES.md. Không sửa state.json/config bằng tay (R10).
"""
import argparse
import inspect
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tools"))
import hs_common as C  # noqa: E402

WF = C.jload(C.CFG / "workflow.json")
STAGES = WF["stages"]
IDX = {s["id"]: i for i, s in enumerate(STAGES)}
LADDER_OF = {"beat_render": "beat", "beat_gate": "beat", "vocal_render": "vocal", "vocal_gate": "vocal"}


# ---------------------------------------------------------------- trạng thái
def sdir(sid):
    return C.SONGS / sid


def load_state(sid):
    p = sdir(sid) / "state.json"
    if not p.exists():
        raise SystemExit(f"chưa có bài '{sid}'. Chạy: python run.py init {sid} --orig ... --inst ... --vocals ... --lyrics ...")
    return C.jload(p)


def save_state(sid, st):
    C.jsave(sdir(sid) / "state.json", st)


def ctx_of(sid, st):
    return {"dir": sdir(sid), "song": C.jload(sdir(sid) / "song.json"), "state": st}


def hist(st, msg):
    st.setdefault("history", []).append(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {msg}")


# ---------------------------------------------------------------- cổng
def _val(v, plan):
    if isinstance(v, str) and v.startswith("song."):
        return plan[v[5:]]
    return v


def _cmp(x, op, v):
    if x is None:
        return False
    if op == "<=":
        return x <= v
    if op == ">=":
        return x >= v
    if op == "==":
        return x == v
    if op == "between":
        return v[0] <= x <= v[1]
    raise ValueError(op)


def evaluate(gate_list, metrics, plan):
    """Trả về (đạt_cứng, [kết quả từng cổng]); cổng 'report' không loại bản, 'stage' để dành cho cả vòng."""
    res, ok = [], True
    for g in gate_list:
        if g["mode"] == "stage":
            continue
        v = _val(g["value"], plan)
        x = metrics.get(g["metric"])
        passed = _cmp(x, g["op"], v)
        res.append({"id": g["id"], "mode": g["mode"], "x": x, "op": g["op"], "v": v, "pass": passed, "provisional": g.get("provisional", False)})
        if g["mode"] == "hard" and not passed:
            ok = False
    return ok, res


def judge(stage_id, gate_key, out, ctx, rnd):
    """Chấm kết quả handler theo config/gates.json. Trả về (stage_ok, picks, summary)."""
    gates = C.jload(C.CFG / "gates.json")[gate_key]
    plan = ctx["song"]["plan"]
    gdir = ctx["dir"] / "gates"; gdir.mkdir(exist_ok=True)
    if "metrics" in out:
        ok, res = evaluate(gates, out["metrics"], plan)
        C.jsave(gdir / f"{stage_id}_r{rnd + 1}.json", {"metrics": out["metrics"], "results": res, "ok": ok})
        fails = [r["id"] for r in res if r["mode"] == "hard" and not r["pass"]]
        return ok, [], ("; ".join(f"{r['id']}={r['x']}" for r in res if not r["pass"] and r["mode"] == "hard") or "đạt")
    rows = out["rows"]
    for r in rows:
        r["passed"], r["results"] = evaluate(gates, r["metrics"], plan)
        r["fails"] = [x["id"] for x in r["results"] if x["mode"] == "hard" and not x["pass"]]
    rows.sort(key=lambda r: (-int(r["passed"]), -r["score"]))
    n_pass = sum(r["passed"] for r in rows)
    stage_gates = [g for g in C.jload(C.CFG / "gates.json")[gate_key] if g["mode"] == "stage"]
    stage_ok = n_pass >= 1 if not stage_gates else all(_cmp(n_pass, g["op"], _val(g["value"], plan)) for g in stage_gates)
    picks = [r["name"] for r in rows if r["passed"]]
    C.jsave(gdir / f"{stage_id}_latest.json", {"round": rnd + 1, "n_pass": n_pass, "n_total": len(rows), "stage_ok": stage_ok, "rows": rows})
    top = "; ".join(f"{r['name']}: {'ĐẠT' if r['passed'] else 'loại (' + ','.join(r['fails']) + ')'}" for r in rows[:12])
    return stage_ok, picks, f"{n_pass}/{len(rows)} bản đạt. {top}"


# ---------------------------------------------------------------- lệnh
def cmd_init(a):
    d = sdir(a.bai)
    if (d / "state.json").exists():
        raise SystemExit("bài đã có. Muốn làm lại phải xóa songs/<bai>/ (xin Duy) — R12 không xóa dữ liệu.")
    d.mkdir(parents=True, exist_ok=True)
    song = {"id": a.bai, "title": a.title or a.bai,
            "inputs": {"original_mp3": a.orig, "stem_inst": a.inst, "stem_vocals": a.vocals, "lyrics_txt": a.lyrics},
            "reference": {"suno_beat": a.suno_beat, "suno_vocals": a.suno_vocals},
            "plan": {"shift_semis": int(a.semis) if a.semis == int(a.semis) else a.semis, "tempo_ratio": a.ratio, "gate_sim": a.gate_sim, "vocal_end_s": None, "mix": {"bal_offset_db": 0.0, "duck_db": 1.0}, "clean_hf": 4}}
    C.jsave(d / "song.json", song)
    st = {"stage": "intake", "status": {s["id"]: "pending" for s in STAGES}, "attempts": {}, "round_beat": 0, "round_vocal": 0, "pick_beat": None, "human": {}, "history": []}
    hist(st, "init")
    save_state(a.bai, st)
    C.say(d, f"Khởi tạo bài {a.bai}. Chưa chạy gì.")
    cmd_status(argparse.Namespace(bai=a.bai))


def cmd_status(a):
    if not a.bai:
        bs = [p.name for p in C.SONGS.iterdir() if p.is_dir() and not p.name.startswith("_")] if C.SONGS.exists() else []
        print("Bài:", ", ".join(bs) or "(chưa có)")
        return
    st = load_state(a.bai)
    mark = {"passed": "✔", "pending": "·", "blocked": "■", "failed": "✘", "waiting": "◆"}
    print(f"== {a.bai} ==  vòng beat {st['round_beat'] + 1}/{len(WF['ladders']['beat'])}, vòng giọng {st['round_vocal'] + 1}/{len(WF['ladders']['vocal'])}")
    for s in STAGES:
        cur = "▶" if s["id"] == st["stage"] else " "
        extra = f" (thử {st['attempts'].get(s['id'], 0)}/{s.get('max_attempts', '-')})" if s["kind"] == "auto" and st["attempts"].get(s["id"]) else ""
        print(f" {cur}{mark.get(st['status'][s['id']], '?')} {s['id']:13s} {'[NGƯỜI]' if s['kind'] == 'human' else '       '} {s['title']}{extra}")
    if st.get("pick_beat"):
        print("  beat Duy chọn:", st["pick_beat"])
    cmd_next(argparse.Namespace(bai=a.bai))


def cmd_next(a):
    st = load_state(a.bai); s = STAGES[IDX[st["stage"]]] if st["stage"] in IDX else None
    if st["stage"] == "done":
        print("NEXT: XONG. Báo Duy kết quả.")
    elif st["status"].get(st["stage"]) == "blocked":
        print("NEXT: BLOCKED —", st.get("blocked_reason", "?"), "→ báo Duy 5 dòng (bước/đã thử/số đo/vấn đề/cần gì).")
    elif s["kind"] == "human":
        print(f"NEXT: HUMAN {s['id']} — {s['ask']}\n      Sau khi Duy trả lời: python run.py human {a.bai} {s['id']} pass|fail --pick ... --note \"...\"")
    else:
        print(f"NEXT: python run.py exec {a.bai}    # {s['title']}")


def _advance(st, frm):
    st["status"][frm] = "passed"
    i = IDX[frm] + 1
    if i >= len(STAGES):
        st["stage"] = "done"
    else:
        st["stage"] = STAGES[i]["id"]
        st["status"][st["stage"]] = "pending"


def _hint_patch(sid, st, lad):
    """Vòng sau không chạy mù: lỗi phổ biến nhất của vòng trước quyết định thay đổi (config/workflow.json -> hints)."""
    f = sdir(sid) / "gates" / f"{lad}_gate_latest.json"
    if not f.exists():
        return {}
    cnt = {}
    for r in C.jload(f)["rows"]:
        for x in r.get("fails", []):
            cnt[x] = cnt.get(x, 0) + 1
    hints = WF.get("hints", {}).get(lad, {}); patch = {}
    metric_of = {g["id"]: g["metric"] for g in C.jload(C.CFG / "gates.json")[lad]}
    for gid, _ in sorted(cnt.items(), key=lambda kv: -kv[1]):
        for key in (gid, metric_of.get(gid)):
            if key in hints:
                patch.update({k: v for k, v in hints[key].items() if k not in patch})
    return patch


def _fail_or_block(sid, st, s, reason):
    """R11: hết lượt → BLOCKED. Có on_fail_goto → sang vòng mới của thang (ladder)."""
    d = sdir(sid); lad = LADDER_OF.get(s["id"])
    if s.get("on_fail_goto") and lad:
        key = f"round_{lad}"
        st[key] += 1
        st[f"patch_{lad}"] = _hint_patch(sid, st, lad)
        if st[f"patch_{lad}"]:
            C.say(d, f"   gợi ý theo lỗi → vòng sau đổi: {st[f'patch_{lad}']}")
        if st[key] >= len(WF["ladders"][lad]):
            st["status"][s["id"]] = "blocked"; st["blocked_reason"] = f"hết {len(WF['ladders'][lad])} vòng '{lad}' mà chưa đủ bản đạt. {reason}"
            C.say(d, "BLOCKED: " + st["blocked_reason"]); return
        st["stage"] = s["on_fail_goto"]; st["status"][s["id"]] = "failed"
        C.say(d, f"Chưa đủ bản đạt ({reason}). Sang vòng {st[key] + 1} của thang '{lad}'.")
        return
    n = st["attempts"].get(s["id"], 0)
    if n >= s.get("max_attempts", 1):
        st["status"][s["id"]] = "blocked"; st["blocked_reason"] = f"{s['id']} không đạt sau {n} lần. {reason}"; C.say(d, "BLOCKED: " + st["blocked_reason"])
    else:
        st["status"][s["id"]] = "failed"; C.say(d, f"{s['id']} chưa đạt ({reason}). Thử lại ({n}/{s.get('max_attempts', 1)}).")


def gates_ok():
    import hashlib
    return hashlib.sha256((C.CFG / "gates.json").read_bytes()).hexdigest() == (C.CFG / "gates.sha").read_text().strip()


def cmd_exec(a):
    import stages as ST
    sid = a.bai; st = load_state(sid); d = sdir(sid)
    if not gates_ok():
        raise SystemExit("R10 CHẶN: config/gates.json đã bị sửa ngoài `run.py gate-set` (mã băm không khớp). Hoàn tác hoặc xin Duy đồng ý rồi dùng gate-set.")
    if st["stage"] == "done" or st["status"].get(st["stage"]) == "blocked":
        return cmd_next(a)
    s = STAGES[IDX[st["stage"]]]
    if s["kind"] == "human":
        return cmd_next(a)
    lad = LADDER_OF.get(s["id"]); rnd = st[f"round_{lad}"] if lad else 0
    st["attempts"][s["id"]] = st["attempts"].get(s["id"], 0) + 1
    fn, needs_lab, on_pass = ST.HANDLERS[s["id"]]
    C.say(d, f"▶ {s['id']} — {s['title']}" + (f" (vòng {rnd + 1})" if lad else ""))
    ctx = ctx_of(sid, st)
    try:
        out = fn(ctx, rnd) if len(inspect.signature(fn).parameters) == 2 else fn(ctx)
    except SystemExit as e:
        st["status"][s["id"]] = "blocked"; st["blocked_reason"] = str(e); hist(st, f"{s['id']} dừng: {e}"); save_state(sid, st); C.say(d, f"DỪNG: {e}"); return
    except Exception as e:  # noqa: BLE001
        st["status"][s["id"]] = "failed"; hist(st, f"{s['id']} lỗi: {e}")
        if st["attempts"][s["id"]] >= s.get("max_attempts", 1) + 1:
            st["status"][s["id"]] = "blocked"; st["blocked_reason"] = f"lỗi chạy {s['id']}: {str(e)[:300]}"
        save_state(sid, st); C.say(d, f"LỖI {s['id']}: {str(e)[:400]}"); return
    if s.get("gates"):
        ok, picks, summ = judge(s["id"], s["gates"], out, ctx, rnd)
        C.say(d, f"   cổng {s['gates']}: {'ĐẠT' if ok else 'CHƯA ĐẠT'} — {summ}")
        # lưới an toàn đã định trước: vòng cuối của thang, còn ≥1 bản đạt thì cho Duy xét (ghi rõ trong nhật ký)
        if not ok and "rows" in out and lad and rnd + 1 >= len(WF["ladders"][lad]) and any(r["passed"] for r in out["rows"]):
            ok, picks = True, [r["name"] for r in out["rows"] if r["passed"]]
            C.say(d, "   (vòng cuối: còn ít bản đạt, vẫn trình Duy xét — ghi nhận trong lịch sử)"); hist(st, "fallback vòng cuối thang")
        if ok:
            if on_pass:
                on_pass(ctx, picks)
            st.pop(f"patch_{lad}", None) if lad else None
            hist(st, f"{s['id']} đạt: {summ[:200]}"); _advance(st, s["id"])
        else:
            hist(st, f"{s['id']} chưa đạt: {summ[:200]}"); _fail_or_block(sid, st, s, summ[:200])
    else:
        hist(st, f"{s['id']} xong"); _advance(st, s["id"])
    save_state(sid, st)


def cmd_auto(a):
    for _ in range(a.max_steps):
        st = load_state(a.bai)
        if st["stage"] == "done" or STAGES[IDX[st["stage"]]]["kind"] == "human" or st["status"].get(st["stage"]) == "blocked":
            break
        cmd_exec(a)
    st = load_state(a.bai)
    if st["status"].get(st["stage"]) in ("pending", "blocked", "waiting") or st["stage"] == "done":
        print("--- review độc lập ---"); cmd_review(a)
    cmd_status(a)


def _calib(sid, st, hg, verdict, pick, note, redo):
    p = C.MEM / "calibration.json"
    cal = C.jload(p) if p.exists() else []
    rows = []
    latest = sdir(sid) / "gates" / ("beat_gate_latest.json" if hg == "HG1" else "vocal_gate_latest.json")
    if latest.exists():
        rows = [{"name": r["name"], "passed": r["passed"], "metrics": r["metrics"]} for r in C.jload(latest)["rows"]]
    cal.append({"date": time.strftime("%Y-%m-%d %H:%M"), "song": sid, "gate": hg, "verdict": verdict, "pick": pick, "intro": st.get("pick_intro"), "redo": redo, "note": note,
                "rows": rows, "_use": "Đối chiếu số đo với tai Duy: cổng 'provisional' chỉ được nâng thành 'hard' khi tách được bản Duy khen/chê (R8)."})
    C.jsave(p, cal)
    with open(C.MEM / "lessons.md", "a", encoding="utf-8") as fh:
        fh.write(f"\n- {time.strftime('%Y-%m-%d')} [{sid}] {hg} {verdict}" + (f" pick={pick}" if pick else "") + (f" — Duy: {note}" if note else "") + "\n")


def cmd_human(a):
    sid = a.bai; st = load_state(sid); d = sdir(sid)
    if st["stage"] != a.hg:
        raise SystemExit(f"đang ở bước {st['stage']}, chưa tới {a.hg}")
    s = STAGES[IDX[a.hg]]
    _calib(sid, st, a.hg, a.verdict, a.pick, a.note, a.redo)
    st["human"][a.hg] = {"verdict": a.verdict, "pick": a.pick, "note": a.note, "at": time.strftime("%Y-%m-%d %H:%M")}
    C.say(d, f"TAI DUY {a.hg}: {a.verdict}" + (f", chọn {a.pick}" if a.pick else "") + (f" — {a.note}" if a.note else ""))
    if a.verdict == "pass":
        if a.hg == "HG1":
            names = [r["name"] for r in C.jload(d / "gates" / "beat_gate_latest.json")["rows"]]
            if a.pick not in names:
                raise SystemExit(f"--pick phải là một trong: {names}")
            st["pick_beat"] = a.pick
            if a.intro:
                inames = [r["name"] for r in C.jload(d / "gates" / "intro_latest.json")["rows"]]
                if a.intro not in inames:
                    raise SystemExit(f"--intro phải là một trong: {inames}")
            st["pick_intro"] = a.intro
        hist(st, f"{a.hg} pass {a.pick or ''}"); _advance(st, a.hg)
    else:
        redo = a.redo or ("beat" if a.hg == "HG1" else "vocal")
        lad = "beat" if redo == "beat" else "vocal"
        st[f"round_{lad}"] += 1
        goto = "beat_render" if redo == "beat" else "vocal_render"
        if st[f"round_{lad}"] >= len(WF["ladders"][lad]):
            st["status"][a.hg] = "blocked"; st["blocked_reason"] = f"Duy chê và đã hết vòng '{lad}'. Cần Duy cho hướng mới."
        else:
            st["status"][a.hg] = "failed"; st["stage"] = goto; st["status"][goto] = "pending"
        hist(st, f"{a.hg} fail → {goto}: {a.note}")
    save_state(sid, st)
    cmd_status(a)


def cmd_unblock(a):
    """Mở khóa BLOCKED sau khi đã sửa nguyên nhân (R11). Ghi lý do vào lịch sử + nhật ký; không đặt lại vòng/ngưỡng."""
    st = load_state(a.bai); cur = st["stage"]
    if st["status"].get(cur) != "blocked":
        raise SystemExit("bước hiện tại không bị chặn")
    st["status"][cur] = "pending"; st["attempts"][cur] = 0; st.pop("blocked_reason", None)
    hist(st, f"unblock {cur}: {a.why}"); save_state(a.bai, st); C.say(sdir(a.bai), f"MỞ KHÓA {cur}: {a.why}")


def cmd_intros(a):
    """Tại cổng HG1: render thêm ứng viên DẠO ĐẦU riêng (nhanh) khi Duy chê dạo đầu; không làm lại cả beat."""
    import stages as ST
    st = load_state(a.bai)
    if st["stage"] != "HG1":
        raise SystemExit("chỉ dùng khi đang ở cổng HG1 (đã có gói nghe beat)")
    if not gates_ok():
        raise SystemExit("R10 CHẶN: ngưỡng bị sửa ngoài gate-set")
    seeds = tuple(int(x) for x in a.seeds.split(","))
    ST.intro_round(ctx_of(a.bai, st), seeds=seeds)
    hist(st, f"vòng dạo đầu {st.get('intro_round')} seeds {seeds}"); save_state(a.bai, st); cmd_status(a)


def _archive(sid):
    """R12: chép bản đã duyệt sang NGHE/_da_duyet_<giờ>/ trước khi sửa (không xóa/ghi đè dữ liệu của Duy)."""
    import shutil
    d = sdir(sid); dst = d / "NGHE" / f"_da_duyet_{time.strftime('%m%d_%H%M')}"
    for src in (d / "NGHE" / "2_ca_bai", d / "NGHE" / "ban_giao_-14LUFS"):
        if src.exists():
            shutil.copytree(src, dst / src.name, dirs_exist_ok=True)
    return dst


def _redo(sid, stage_id):
    import stages as ST
    st = load_state(sid); s = STAGES[IDX[stage_id]]; ctx = ctx_of(sid, st)
    fn, _, on_pass = ST.HANDLERS[stage_id]
    lad = LADDER_OF.get(stage_id); rnd = st[f"round_{lad}"] if lad else 0
    # vòng đã chạy xong của bước đó (render/gate dùng vòng hiện tại; sau khi qua cổng vòng không tăng)
    C.say(sdir(sid), f"↻ làm lại {stage_id} (sửa lỗi)")
    out = fn(ctx, rnd) if len(inspect.signature(fn).parameters) == 2 else fn(ctx)
    if s.get("gates"):
        ok, picks, summ = judge(stage_id, s["gates"], out, ctx, rnd)
        C.say(sdir(sid), f"   cổng {s['gates']}: {'ĐẠT' if ok else 'CHƯA ĐẠT'} — {summ}")
        if ok and on_pass:
            on_pass(ctx, picks)
    save_state(sid, st)


def _plan_set(sid, path, val):
    p = sdir(sid) / "song.json"; song = C.jload(p); node = song["plan"]
    keys = path.split(".")
    for k in keys[:-1]:
        node = node.setdefault(k, {})
    cur = node.get(keys[-1], 0.0 if val[0] in "+-" else None)
    node[keys[-1]] = (float(cur) + float(val)) if val[0] in "+-" else (float(val[1:]) if val[0] == "=" else val)
    C.jsave(p, song); return keys[-1], node[keys[-1]]


def cmd_redo(a):
    _redo(a.bai, a.stage)


def cmd_fix(a):
    """Sửa theo triệu chứng (config/fixes.json). Luôn chép bản đã duyệt đi trước; không đổi ngưỡng cổng (R10)."""
    fx = C.jload(C.CFG / "fixes.json")
    if a.trieu_chung not in fx or a.trieu_chung.startswith("_"):
        raise SystemExit("triệu chứng có: " + ", ".join(k for k in fx if not k.startswith("_")))
    f = fx[a.trieu_chung]; sid = a.bai; d = sdir(sid)
    C.say(d, f"SỬA LỖI '{a.trieu_chung}': {f['mo_ta']}" + (f" — Duy: {a.note}" if a.note else ""))
    if a.trieu_chung == "vao_nhac_lech" or f.get("do") == "joincheck":
        pass   # finalize_beat tự đo + khớp pha và in kết quả vào nhật ký
    if any(k in act for act in f["lam"] for k in ("redo", "goto")):
        print("đã chép bản cũ sang:", _archive(sid))
    for act in f["lam"]:
        if "plan" in act:
            for k, v in act["plan"].items():
                C.say(d, "   đổi tham số bài: %s → %s" % _plan_set(sid, k, v))
        if "redo" in act:
            for sg in act["redo"]:
                _redo(sid, sg)
        if "patch" in act:
            st = load_state(sid)
            for lad, pt in act["patch"].items():
                st[f"patch_{lad}"] = {**(st.get(f"patch_{lad}") or {}), **pt}
            save_state(sid, st); C.say(d, f"   vòng sau đổi: {act['patch']}")
        if "goto" in act:
            st = load_state(sid); tgt = act["goto"]
            for k, v in act.items():
                if k.startswith("round_"):
                    lad = k.split("_", 1)[1]
                    st[k] += int(v)
                    if st[k] >= len(WF["ladders"][lad]):
                        st["status"][STAGES[IDX[tgt]]["id"]] = "blocked"; st["stage"] = tgt
                        st["blocked_reason"] = f"hết thang vòng '{lad}' khi sửa '{a.trieu_chung}': cần Duy cho hướng mới"
                        save_state(sid, st); C.say(d, "BLOCKED: " + st["blocked_reason"]); return
            for s_ in STAGES[IDX[tgt]:]:
                st["status"][s_["id"]] = "pending"
            st["stage"] = tgt; hist(st, f"fix {a.trieu_chung} → {tgt}"); save_state(sid, st)
            C.say(d, f"   quay về {tgt}; chạy `python run.py auto {sid}` để làm tiếp")
        if "intros" in act:
            import stages as ST
            st = load_state(sid); st["stage"] = "HG1"; st["status"]["HG1"] = "pending"; save_state(sid, st)
            cmd_intros(argparse.Namespace(bai=sid, seeds=act["intros"]["seeds"]))
        if "huong_dan" in act:
            print(act["huong_dan"])
    print("xong. Gói nghe mới:", d / "NGHE")


def cmd_gates(a):
    d = sdir(a.bai)
    for f in sorted((d / "gates").glob(f"{a.buoc or ''}*latest.json")):
        j = C.jload(f)
        if "n_pass" not in j:
            print(f"--- {f.name}: dạo đầu riêng (vòng {j['round']}): " + ", ".join(f"{r['name']}{'✔' if r['passed'] else '✘'}" for r in j["rows"])); continue
        print(f"--- {f.name}: {j['n_pass']}/{j['n_total']} đạt (vòng {j['round']})")
        for r in j["rows"]:
            print(f" {'ĐẠT ' if r['passed'] else 'loại'} {r['name']:22s} " + " ".join(f"{x['id']}={x['x']}{'*' if x['provisional'] else ''}{'' if x['pass'] else '✘'}" for x in r["results"]))
    print("(* = cổng đang hiệu chuẩn, chỉ báo cáo)")


def cmd_gate_set(a):
    if not a.duy_ok:
        raise SystemExit("R10: đổi ngưỡng cần Duy đồng ý. Thêm --duy-ok sau khi Duy nói OK, kèm --why.")
    p = C.CFG / "gates.json"; g = C.jload(p); hit = 0
    for gate in g[a.buoc]:
        if gate["id"] == a.gate_id:
            old = gate["value"]; gate["value"] = json.loads(a.value) if a.value[0] in "[-0123456789" else a.value; hit += 1
            with open(C.MEM / "lessons.md", "a", encoding="utf-8") as fh:
                fh.write(f"\n- {time.strftime('%Y-%m-%d')} ĐỔI NGƯỠNG {a.buoc}.{a.gate_id}: {old} → {gate['value']} (Duy OK). Lý do: {a.why}\n")
    if not hit:
        raise SystemExit("không thấy cổng")
    C.jsave(p, g)
    import hashlib
    (C.CFG / "gates.sha").write_text(hashlib.sha256(p.read_bytes()).hexdigest())
    print("đã đổi + ghi memory/lessons.md + cập nhật mã băm")


def cmd_review(a):
    """Người kiểm độc lập: soi đầu ra có vi phạm luật không (R1,R2,R4,R6,R10,R14). Không sửa gì."""
    import re
    d = sdir(a.bai); st = load_state(a.bai); res = []

    def chk(code, ok, msg):
        res.append((code, ok, msg)); print(f" {'ĐẠT ' if ok else 'LỖI '} {code}: {msg}")
    chk("R10", gates_ok(), "ngưỡng cổng không bị sửa ngoài gate-set")
    log = (d / "NHAT_KY.md").read_text(encoding="utf-8") if (d / "NHAT_KY.md").exists() else ""
    chk("R14", bool(log.strip()), f"có nhật ký ({len(log.splitlines())} dòng)")
    chk("R1", not any(b.lower() in (log + json.dumps(st)).lower() for b in C.PATHS["deny_substrings"]), "log/state không nhắc tới tool thật")
    lyr = d / "in" / "lyrics_ace.txt"
    if lyr.exists():
        words = [w for w in re.findall(r"\w+", lyr.read_text(encoding="utf-8").lower())]
        grams = {" ".join(words[i:i + 5]) for i in range(len(words) - 4)}
        blob = " ".join(re.findall(r"\w+", (log + json.dumps(st, ensure_ascii=False)).lower()))
        chk("R6", not any(g in blob for g in grams), "log/state không chứa 5 từ liền của lời bài")
    chk("R2", not C.LOCK.exists(), "không có khóa lab bị bỏ quên")
    fa, pa = d / "abc" / "stem_full.abc", d / "abc" / "prep_full.abc"
    if fa.exists() and pa.exists():
        from abc_tools import parse_abc
        x, y = parse_abc(fa.read_text(encoding="utf-8")), parse_abc(pa.read_text(encoding="utf-8"))
        sh = ctx_of(a.bai, st)["song"]["plan"]["shift_semis"]
        chk("R4", len(x) == len(y) and all(q[2] - p_[2] == sh for p_, q in zip(x, y)), f"bản nốt chỉ bị dời cung {sh:+g}, không thêm/bớt/đổi nốt ({len(x)} nốt)")
    for s_ in STAGES:
        if st["status"].get(s_["id"]) == "passed" and s_.get("gates"):
            chk("cổng", any((d / "gates").glob(f"{s_['id']}*")), f"{s_['id']}: có hồ sơ chấm cổng")
    bad = [c for c, ok, _ in res if not ok]
    print("KẾT LUẬN:", "ĐẠT" if not bad else "CÓ LỖI " + ",".join(bad))
    return not bad


def cmd_selftest(a):
    """Kiểm tra chính harness (hồi quy): cấu hình nhất quán, bảo vệ R1, chấm cổng đúng, khóa R10."""
    import stages as ST
    ok = True

    def chk(name, cond):
        nonlocal ok; ok &= bool(cond); print(f" {'ĐẠT ' if cond else 'LỖI '} {name}")
    gj = C.jload(C.CFG / "gates.json")
    chk("mọi bước tự động có handler", all(s["id"] in ST.HANDLERS for s in STAGES if s["kind"] == "auto"))
    chk("mọi khóa cổng tồn tại", all((s.get("gates") in gj) for s in STAGES if s.get("gates")))
    chk("thang vòng không rỗng", all(len(v) > 0 for v in WF["ladders"].values()))
    chk("on_fail_goto trỏ đúng bước", all(s["on_fail_goto"] in IDX for s in STAGES if s.get("on_fail_goto")))
    chk("mã băm ngưỡng khớp", gates_ok())
    try:
        C.guard("C:/EZAISinger/x"); chk("R1 chặn đường dẫn tool thật", False)
    except SystemExit:
        chk("R1 chặn đường dẫn tool thật", True)
    try:
        C.guard("http://127.0.0.1:8188/queue"); chk("R1 chặn cổng 8188", False)
    except SystemExit:
        chk("R1 chặn cổng 8188", True)
    plan = {"gate_sim": 0.62}
    good = {"voice_pct": 2, "accordion_pct": 80, "lock_corr": .5, "lock_iqr_ms": 23, "skips": 0, "dur_ratio": 1.0, "sim_orig_max": .55, "start_lag_ms": 40}
    chk("cổng beat: bản tốt đạt", evaluate(gj["beat"], good, plan)[0])
    chk("cổng beat: thiếu accordion bị loại", not evaluate(gj["beat"], {**good, "accordion_pct": 10}, plan)[0])
    chk("cổng beat: giống bản gốc 0.73 (mức dính full) bị loại", not evaluate(gj["beat"], {**good, "sim_orig_max": .73}, plan)[0])
    chk("cổng beat: hụt phách 5 bị loại", not evaluate(gj["beat"], {**good, "skips": 5}, plan)[0])
    chk("cổng intro (provisional) không loại bản", evaluate(gj["beat"], {**good, "intro_chroma": 0.1}, plan)[0])
    chk("cổng giọng: xì −25 dB (ACE thô) bị loại", not evaluate(gj["vocal"], {"floor_db": -25, "notes_pct": 80, "wer": .2, "spk_sim": .9, "lag_ms": 30}, plan)[0])
    chk("cổng trộn: −9.5 LUFS (vòng 3) bị loại", not evaluate(gj["mix"], {"lufs": -9.5, "true_peak": -1, "near_peak_pct": .04, "crest_db": 11}, plan)[0])
    sk = sorted(x for x in (ROOT / "skills").iterdir() if x.is_dir())
    chk(f"{len(sk)} skill đều có SKILL.md với name + description", all((x / "SKILL.md").exists() and re.match(r"---\nname: %s\ndescription: .+\n---" % re.escape(x.name), (x / "SKILL.md").read_text(encoding="utf-8")) for x in sk))
    chk("INDEX.md và AGENTS.md nhắc mọi skill", all(x.name in (ROOT / "skills" / "INDEX.md").read_text(encoding="utf-8") and x.name in (ROOT / "AGENTS.md").read_text(encoding="utf-8") for x in sk))
    fx = C.jload(C.CFG / "fixes.json"); okf = True
    for k, v in fx.items():
        if k.startswith("_"):
            continue
        for act in v["lam"]:
            for sg in act.get("redo", []):
                okf &= sg in IDX
            if "goto" in act:
                okf &= act["goto"] in IDX
    chk("fixes.json chỉ trỏ tới bước có thật", okf)
    chk("mọi triệu chứng trong fixes.json có trong skill fix", all(k in (ROOT / "skills" / "fix" / "SKILL.md").read_text(encoding="utf-8") for k in fx if not k.startswith("_")))
    print("KẾT LUẬN:", "ĐẠT" if ok else "CÓ LỖI")
    return ok


def cmd_lab(a):
    if a.what == "up":
        C.lab_up(None)
    elif a.what == "down":
        C.lab_down(None)
    else:
        used, total = C.gpu_used_mb()
        print(f"lab {'ĐANG CHẠY' if C.lab_alive() else 'tắt'}; GPU {used}/{total} MB; khóa: {C.LOCK.exists()}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest="cmd", required=True)
    i = sp.add_parser("init"); i.add_argument("bai"); i.add_argument("--title"); i.add_argument("--orig", required=True); i.add_argument("--inst", required=True)
    i.add_argument("--vocals", required=True); i.add_argument("--lyrics", required=True); i.add_argument("--semis", type=float, default=-1)
    i.add_argument("--ratio", type=float, default=1.0); i.add_argument("--gate-sim", type=float, default=0.62)
    i.add_argument("--suno-beat"); i.add_argument("--suno-vocals"); i.set_defaults(f=cmd_init)
    for n, f in (("status", cmd_status), ("next", cmd_next), ("exec", cmd_exec), ("auto", cmd_auto)):
        x = sp.add_parser(n); x.add_argument("bai", nargs="?"); x.set_defaults(f=f)
        if n == "auto":
            x.add_argument("--max-steps", type=int, default=40)
    h = sp.add_parser("human"); h.add_argument("bai"); h.add_argument("hg", choices=["HG1", "HG2"]); h.add_argument("verdict", choices=["pass", "fail"])
    h.add_argument("--pick"); h.add_argument("--intro"); h.add_argument("--note", default=""); h.add_argument("--redo", choices=["beat", "vocal"]); h.set_defaults(f=cmd_human)
    g = sp.add_parser("gates"); g.add_argument("bai"); g.add_argument("buoc", nargs="?"); g.set_defaults(f=cmd_gates)
    gs = sp.add_parser("gate-set"); gs.add_argument("buoc"); gs.add_argument("gate_id"); gs.add_argument("value"); gs.add_argument("--why", required=True)
    gs.add_argument("--duy-ok", action="store_true"); gs.set_defaults(f=cmd_gate_set)
    it = sp.add_parser("intros"); it.add_argument("bai"); it.add_argument("--seeds", default="21,22,23,24"); it.set_defaults(f=cmd_intros)
    rd = sp.add_parser("redo"); rd.add_argument("bai"); rd.add_argument("stage", choices=["finalize_beat", "mix", "pack", "vocal_gate", "beat_gate"]); rd.set_defaults(f=cmd_redo)
    fxp = sp.add_parser("fix"); fxp.add_argument("bai"); fxp.add_argument("trieu_chung"); fxp.add_argument("--note", default=""); fxp.set_defaults(f=cmd_fix)
    ub = sp.add_parser("unblock"); ub.add_argument("bai"); ub.add_argument("--why", required=True); ub.set_defaults(f=cmd_unblock)
    rv = sp.add_parser("review"); rv.add_argument("bai"); rv.set_defaults(f=cmd_review)
    stt = sp.add_parser("selftest"); stt.set_defaults(f=cmd_selftest)
    lb = sp.add_parser("lab"); lb.add_argument("what", choices=["up", "down", "status"]); lb.set_defaults(f=cmd_lab)
    cg = sp.add_parser("check-guard"); cg.add_argument("text"); cg.set_defaults(f=lambda a: (C.guard(a.text), print("an toàn (không chạm tool thật)")))
    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
