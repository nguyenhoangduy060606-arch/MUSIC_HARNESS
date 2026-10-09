"""Các bước (handler) của harness_spain. Mỗi handler nhận ctx, trả về:
  {"metrics": {...}}                       -> một bộ số (intake, abc)
  {"rows": [{"name":..., "metrics":{...}, "score": x}, ...]}   -> nhiều ứng viên (beat_gate, vocal_gate, mix)
  {} (không cổng)                          -> render/pack/memory
Handler KHÔNG tự quyết đạt/không: run.py chấm theo config/gates.json (R8, R10).
Chạy bằng python hệ thống (chỉ thư viện chuẩn); đo âm thanh gọi tools/measure.py bằng env 'tx'.
"""
import json
import re
import shutil
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import hs_common as C
from abc_tools import abc_end, legato_fill, parse_abc, transpose_abc

T = Path(__file__).resolve().parent
STYLES = C.jload(C.CFG / "styles.json")
WF = C.jload(C.CFG / "workflow.json")

NAMES_DOWN = {"C": "B", "Db": "C", "D": "Db", "Eb": "D", "E": "Eb", "F": "E", "Gb": "F", "G": "Gb", "Ab": "G", "A": "Ab", "Bb": "A", "B": "Bb"}
LET = "CDEFGAB"


def key_down(key):
    k = re.match(r"([A-G][b#]?)", key).group(1)
    k = {"C#": "Db", "D#": "Eb", "F#": "Gb", "G#": "Ab", "A#": "Bb"}.get(k, k)
    new = NAMES_DOWN[k]
    return new, (LET.index(new[0]) - LET.index(k[0]))


def ctx_paths(ctx):
    d = ctx["dir"]
    return {k: d / v for k, v in {
        "inst": f"in/{ctx['song']['id']}_inst.wav", "vocals": "in/vocals.wav", "orig": "in/orig.mp3", "lyr": "in/lyrics_ace.txt", "facts": "in/facts.json",
        "ref_beat": "ref/ref_beat.wav", "ref_voc": "ref/ref_vocal.wav", "sections": "ref/sections.json"}.items()}


def run_tx(script, *args):
    return C.run([C.py("tx"), T / script, *args])


# ------------------------------------------------------------------ intake
def intake(ctx):
    d, song, P = ctx["dir"], ctx["song"], ctx_paths(ctx)
    inp, plan = song["inputs"], song["plan"]
    ok = all(Path(inp[k]).exists() for k in ("original_mp3", "stem_inst", "stem_vocals", "lyrics_txt"))
    if not ok:
        return {"metrics": {"files_ok": 0, "lyrics_lines": 0, "stem_len_diff_s": 99, "tempo_dev_ms": 999}}
    (d / "in").mkdir(parents=True, exist_ok=True); (d / "ref").mkdir(exist_ok=True)
    shutil.copy(inp["original_mp3"], P["orig"]); shutil.copy(inp["stem_inst"], P["inst"]); shutil.copy(inp["stem_vocals"], P["vocals"])
    shutil.copy(inp["lyrics_txt"], d / "in" / "lyrics_goc.txt")
    C.run([C.sys.executable, T / "lyrics_clean.py", d / "in" / "lyrics_goc.txt"])          # R6: không in lời; script chỉ in số liệu
    txt = P["lyr"].read_text(encoding="utf-8").strip().splitlines()
    if not any(l.strip() == "[Intro]" for l in txt):
        txt = ["[Intro]", ""] + txt
    if not any(l.strip() == "[Outro]" for l in txt):
        txt += ["", "[Outro]"]
    P["lyr"].write_text("\n".join(txt) + "\n", encoding="utf-8")
    n_lines = len([l for l in txt if l.strip() and not l.startswith("[")])
    run_tx("measure.py", "facts", P["inst"], P["vocals"], P["facts"])
    f = C.jload(P["facts"])
    semis, ratio = plan["shift_semis"], plan["tempo_ratio"]
    C.jsave(P["sections"], {k: [round(a / ratio, 2), round(b / ratio, 2)] for k, (a, b) in f["sections"].items()})   # giờ trên lưới chuẩn (đã đổi tốc độ)
    run_tx("measure.py", "ref", P["inst"], semis, ratio, P["ref_beat"])
    run_tx("measure.py", "ref", P["vocals"], semis, ratio, P["ref_voc"])
    C.say(d, f"Nhận bài xong: {f['bpm']} phách/phút, giọng vào {f['voice_first_s']} s, dạo giữa {f['gap']}, {n_lines} dòng lời (không in). Lưới chuẩn: dời {semis} nửa cung, tốc độ x{ratio}.")
    return {"metrics": {"files_ok": 1, "lyrics_lines": n_lines, "stem_len_diff_s": round(abs(f["inst_dur_s"] - f["voc_dur_s"]), 2), "tempo_dev_ms": f["tempo_dev_ms"]}}


# ------------------------------------------------------------------ abc
def abc(ctx):
    d, song, P = ctx["dir"], ctx["song"], ctx_paths(ctx)
    plan, f = song["plan"], C.jload(P["facts"])
    (d / "abc").mkdir(exist_ok=True)
    src = d / "abc" / "stem_full.abc"
    C.lab_up(d)
    with C.LabLock():
        C.run([C.sys.executable, T / "lab_comfy.py", "abc", P["inst"], "--mode", "full", "--out", src])
    text = src.read_text(encoding="utf-8")
    m = re.search(r"^K:\s*([A-G][b#]?)", text, re.M)
    key = m.group(1) if m else "C"
    plan = {**plan, "shift_semis": int(plan["shift_semis"])}
    assert plan["shift_semis"] == -1, "v1 chỉ hỗ trợ dời xuống 1 nửa cung (-1); muốn khác phải mở rộng key_down()"
    new_key, steps = key_down(key)
    q = round(f["bpm"] * plan["tempo_ratio"])
    base = transpose_abc(text, steps, plan["shift_semis"], new_key, bpm=q)
    a0, b0 = parse_abc(text), parse_abc(base)
    assert len(a0) == len(b0) and all(y[2] - x[2] == plan["shift_semis"] for x, y in zip(a0, b0)), "dời cung làm lệch nốt"
    out = {}
    for variant, gap in (("full", 0.5), ("full_dense", 1.0)):
        t2 = legato_fill(base, voice="Ins", max_gap=gap)[0]
        a2 = parse_abc(t2)
        assert len(a2) == len(a0), "nối nốt làm đổi số nốt (R4)"
        (d / "abc" / f"prep_{variant}.abc").write_text(t2, encoding="utf-8")
        out[variant] = {"notes": len(a2), "end_s": round(abc_end(t2), 1)}
        try:   # dạo đầu riêng: cắt bản nốt ngay trước dòng '% ' thứ hai (đầu bài, trước đoạn lời); nốt giữ nguyên (R4), chỉ ngắn lại
            lines = t2.splitlines(); marks = [i for i, l in enumerate(lines) if l.startswith("% ")]
            cut = chr(10).join(lines[:marks[1]]) + chr(10)
            ia, fa = parse_abc(cut), [n for n in a2 if n[0] < abc_end(cut) - 0.01]
            assert len(ia) == len(fa) and all(abs(x[0] - y[0]) < 1e-6 and x[2] == y[2] for x, y in zip(ia, fa)), "nốt dạo đầu bị đổi"
            (d / "abc" / f"prep_intro_{variant}.abc").write_text(cut, encoding="utf-8")
            out[variant]["intro_end_s"] = round(abc_end(cut), 2)
        except Exception as e:   # noqa: BLE001
            C.say(d, f"   (không cắt được dạo đầu riêng: {str(e)[:80]}; bỏ qua ứng viên intro)")
    f.update({"intro_end_s": out["full"].get("intro_end_s"), "key_src": key, "key_new": new_key, "q": q, "keyscale": f"{new_key} major"})
    C.jsave(P["facts"], f)
    first = min(x[0] for x in a0)
    dur = abc_end(base)
    C.say(d, f"Chép nốt xong: cung {key} → {new_key}, Q={q}, {len(a0)} nốt ({round(len(a0) / dur, 2)} nốt/s). Nốt đầu ở {round(first, 2)} s, tiếng đầu thật ở {f['first_onset_s']} s.")
    return {"metrics": {"notes_per_s": round(len(a0) / dur, 2), "abc_dur_ratio": round(dur / (f["inst_dur_s"] / plan["tempo_ratio"]), 3),
                        "first_note_gap_s": round(abs(first - (f["first_onset_s"] or 0)), 2)}}


# ------------------------------------------------------------------ beat
def _ladder_entry(ctx, lad_name, rnd):
    e = dict(WF["ladders"][lad_name][rnd])
    e.update(ctx["state"].get(f"patch_{lad_name}") or {})      # gợi ý theo lỗi của vòng trước (run.py ghi)
    return e


def beat_render(ctx, rnd):
    d, P = ctx["dir"], ctx_paths(ctx)
    lad = _ladder_entry(ctx, "beat", rnd)
    out = d / "beat" / f"r{rnd + 1}"; out.mkdir(parents=True, exist_ok=True)
    abcf = d / "abc" / f"prep_{lad['abc']}.abc"
    intro_abc = d / "abc" / f"prep_intro_{lad['abc']}.abc"
    mx = round(abc_end(abcf.read_text(encoding="utf-8")) + 8)
    jobs = [(s, sd) for s in lad["styles"] for sd in lad["seeds"]]
    cfg = lad.get("cfg", 1.0)
    C.lab_up(d)
    with C.LabLock():
        for i, (s, sd) in enumerate(jobs, 1):
            name = f"b{rnd + 1}_{s}_s{sd}"
            C.say(d, f"[{i}/{len(jobs)}] YuE2 đánh beat {name} (kiểu {s}, seed {sd}, cfg {cfg}) ~2 phút")
            r = C.run([C.sys.executable, T / "lab_comfy.py", "gen", P["inst"], "--style", STYLES["beat"][s], "--abc", abcf, "--lyrics", STYLES["beat_lyrics"],
                       "--seed", sd, "--max-duration", mx, "--cfg", cfg, "--name", name, "--out-dir", out], check=False)
            if not (out / f"{name}.flac").exists():
                C.say(d, f"    LỖI {name}: {(r.stdout[-200:] + r.stderr[-200:]).strip()}")
        if intro_abc.exists():     # ứng viên DẠO ĐẦU riêng: đoạn ngắn nên YuE2 bám nốt tốt hơn, và Duy nghe/chọn riêng
            mi = round(abc_end(intro_abc.read_text(encoding="utf-8")) + 5)
            for i, (s, sd) in enumerate(jobs, 1):
                name = f"i{rnd + 1}_{s}_s{sd}"
                C.say(d, f"[intro {i}/{len(jobs)}] YuE2 đánh dạo đầu {name} (~{mi} s, nhanh)")
                C.run([C.sys.executable, T / "lab_comfy.py", "gen", P["inst"], "--style", STYLES["beat"][s], "--abc", intro_abc, "--lyrics", "[Intro]\n",
                       "--seed", sd, "--max-duration", mi, "--cfg", cfg, "--name", name, "--out-dir", out], check=False)
        C.lab_free()
    return {}


def beat_gate(ctx, rnd):
    d, P = ctx["dir"], ctx_paths(ctx)
    src = d / "beat" / f"r{rnd + 1}"
    files = sorted(src.glob("b*_s*.flac")); ifiles = sorted(src.glob("i*_s*.flac"))
    al = d / "beat" / "aligned"; al.mkdir(exist_ok=True)
    cl = d / "beat" / f"_clap_r{rnd + 1}.json"
    C.run([C.py("clap"), T / "clap_check.py", cl, *files, *ifiles])
    clap = {Path(k).name: v for k, v in C.jload(cl).items()}
    f = C.jload(P["facts"]); ratio = ctx["song"]["plan"]["tempo_ratio"]
    intro_end = (f.get("intro_end_s") or f["voice_first_s"]) / ratio

    def one(fl):
        n = fl.stem; out = al / f"{n}.wav"
        a = C.last_json(run_tx("beat_align.py", P["ref_beat"], fl, out).stdout)
        lk = C.run([C.py("tx"), T / "beat_lock.py", P["ref_beat"], out]).stdout
        m = re.search(r"corr0 ([-\d.]+) lag (-?\d+) iqr (\d+)", lk)
        br = C.last_json(run_tx("measure.py", "beatrow", P["ref_beat"], out, fl, P["sections"]).stdout)
        ins = clap.get(fl.name, {}).get("instr", {})
        met = {"voice_pct": round(ins.get("voice_male", 0) + ins.get("voice_duet", 0), 1), "accordion_pct": ins.get("accordion", 0), "sax_pct": ins.get("sax", 0),
               "lock_corr": float(m.group(1)) if m else 0, "lock_iqr_ms": int(m.group(3)) if m else 999, "skips": a.get("so_lan_yue2_hut_thua_phach", 99), **br}
        sc = met["lock_corr"] + met["accordion_pct"] / 100 - 0.1 * met["skips"] - (met["sim_orig_max"] or 1) * 0.5
        return {"name": n, "metrics": met, "score": round(sc, 3)}

    def one_intro(fl):
        n = fl.stem; out = al / f"{n}.wav"
        txt = run_tx("measure.py", "introalign", P["ref_beat"], fl, out, intro_end).stdout
        ir = {}
        for ln in txt.splitlines():
            if ln.strip().startswith("{"):
                ir.update(json.loads(ln))
        ins = clap.get(fl.name, {}).get("instr", {})
        met = {"voice_pct": round(ins.get("voice_male", 0) + ins.get("voice_duet", 0), 1), "accordion_pct": ins.get("accordion", 0), **ir}
        ok = met["voice_pct"] <= 15 and met["accordion_pct"] >= 40
        return {"name": n, "metrics": met, "score": met["intro_match"] + met["intro_cos"], "passed": ok}
    with ThreadPoolExecutor(3) as ex:
        rows = list(ex.map(one, files)); irows = list(ex.map(one_intro, ifiles))
    irows.sort(key=lambda r: (-int(r["passed"]), -r["score"]))
    C.jsave(d / "gates" / "intro_latest.json", {"round": rnd + 1, "intro_end_s": intro_end, "rows": irows})
    return {"rows": rows}


def beat_on_pass(ctx, picks):
    """Gói nghe #1: chỉ beat + ứng viên dạo đầu riêng, kèm đoạn 25 s đầu. Dạo đầu nghe trước (R7)."""
    d, P = ctx["dir"], ctx_paths(ctx)
    pk = d / "NGHE" / "1_beat"; shutil.rmtree(pk, ignore_errors=True)
    irows = [r for r in C.jload(d / "gates" / "intro_latest.json")["rows"] if r["passed"]][:3]
    specs = [f"0_beat_goc={P['ref_beat']}"] + [f"{n}={d / 'beat' / 'aligned' / (n + '.wav')}" for n in picks[:3]]
    ispecs = [f"{r['name']}={d / 'beat' / 'aligned' / (r['name'] + '.wav')}" for r in irows]
    C.run([C.py("mix"), T / "pack.py", pk, *specs, *ispecs], env={"TARGET": "-19", "FF": C.ffmpeg()})
    (pk / "dao_dau_25s").mkdir(exist_ok=True)
    for mp3 in sorted(pk.glob("*.mp3")):
        C.run([C.ffmpeg(), "-v", "error", "-y", "-i", mp3, "-t", "25", pk / "dao_dau_25s" / mp3.name])
    (pk / "dao_dau_25s" / "nghe.lof").write_text("".join(f'file "{m.name}"\n' for m in sorted((pk / "dao_dau_25s").glob("*.mp3"))), encoding="utf-8")
    rows = {r["name"]: r for r in C.jload(d / "gates" / "beat_gate_latest.json")["rows"]}
    md = ["# Nghe beat (cùng độ to −19 LUFS) — NGHE DẠO ĐẦU TRƯỚC", "",
          "Mở `dao_dau_25s/nghe.lof` (25 s đầu của mọi file) rồi `nghe.lof` (cả beat). `0_beat_goc` = bản gốc (đã dời cung).", "",
          "- Beat chính: `b*` (cả bài). **Dạo đầu riêng**: `i*` (chỉ phần mở đầu, YuE2 bám nốt tốt hơn vì đoạn ngắn).",
          "- Duy cho biết: chọn 1 beat chính (`--pick`) + 1 dạo đầu nếu thích hơn (`--intro`), hoặc chê + nói giây nào/nghe sai kiểu gì (`--note`).",
          "- Máy chỉ lọc; số bên dưới KHÔNG nói beat hay.", "",
          "| beat | accordion % | sax % | khớp nhịp | hụt phách | giống bản thu gốc (max) |", "|---|---|---|---|---|---|"]
    for n in picks[:3]:
        m = rows[n]["metrics"]
        md.append(f"| {n} | {m['accordion_pct']} | {m['sax_pct']} | {m['lock_corr']} ({m['lock_iqr_ms']} ms) | {m['skips']} | {m['sim_orig_max']} |")
    md += ["", "| dạo đầu | accordion % | trùng nốt mở đầu với gốc | cos |", "|---|---|---|---|"]
    for r in irows:
        m = r["metrics"]; md.append(f"| {r['name']} | {m['accordion_pct']} | {m['intro_match']} | {m['intro_cos']} |")
    (pk / "LISTEN.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    C.say(d, f"Gói nghe beat: {pk} ({len(picks[:3])} beat + {len(irows)} dạo đầu riêng). Chờ tai Duy (HG1).")


def finalize_beat(ctx):
    """Ghép dạo đầu Duy chọn vào beat Duy chọn, tại phách của lưới chuẩn gần giờ giọng vào (cả hai đã căn cùng lưới)."""
    d, st, P = ctx["dir"], ctx["state"], ctx_paths(ctx)
    beat = d / "beat" / "aligned" / f"{st['pick_beat']}.wav"
    if not st.get("pick_intro"):
        st["final_beat"] = st["pick_beat"]; C.say(d, "Không chọn dạo đầu riêng: dùng nguyên beat đã chọn."); return {}
    intro = d / "beat" / "aligned" / f"{st['pick_intro']}.wav"
    f = C.jload(P["facts"]); ratio = ctx["song"]["plan"]["tempo_ratio"]
    t_target = (f.get("intro_end_s") or f["voice_first_s"]) / ratio - 0.3
    T0 = C.last_json(run_tx("measure.py", "splicet", P["ref_beat"], t_target).stdout)["t"]
    fin = d / "beat" / "final"; fin.mkdir(exist_ok=True)
    name = f"{st['pick_beat']}+{st['pick_intro']}"; X = 0.25
    jf = d / "beat" / "aligned" / f"{st['pick_intro']}__join.wav"       # khớp pha dạo đầu với beat chính trước chỗ ghép
    j = C.last_json(run_tx("measure.py", "joinfit", beat, intro, jf, T0).stdout)
    if j.get("ok"):
        intro = jf; C.say(d, f"   khớp pha dạo đầu với beat chính: dời {j['a_ms']} ms, co giãn {j['b_pct']}%; lệch trước {j['lech_truoc_ms']} → sau {j['lech_sau_ms']} ms")
    else:
        C.say(d, f"   (không khớp pha được: {j.get('why')}; giữ dạo đầu như đã căn)")
    st["join"] = j
    flt = f"[0:a]atrim=0:{T0 + X},asetpts=PTS-STARTPTS[a];[1:a]atrim={T0},asetpts=PTS-STARTPTS[b];[a][b]acrossfade=d={X}"
    C.run([C.ffmpeg(), "-v", "error", "-y", "-i", intro, "-i", beat, "-filter_complex", flt, "-ar", "44100", fin / f"{name}.wav"])
    st["final_beat"] = f"final/{name}"
    C.say(d, f"Ghép dạo đầu {st['pick_intro']} vào {st['pick_beat']} tại {T0} s (phách), nối mềm {X} s.")
    return {}


# ------------------------------------------------------------------ vocal
def _acejob(ctx, name, cap, acs, seed, vm_src):
    f, song = C.jload(ctx_paths(ctx)["facts"]), ctx["song"]
    lyr = ctx_paths(ctx)["lyr"].read_text(encoding="utf-8")
    return {"name": name, "params": {"task_type": "cover", "shift": 3.0, "infer_method": "ode", "sampler_mode": "dpmpp_2m", "inference_steps": 8, "latent_rescale": 0.8,
            "thinking": False, "use_cot_metas": False, "use_cot_caption": False, "use_cot_language": False, "timesignature": "4", "duration": -1,
            "keyscale": f["keyscale"], "bpm": f["q"], "src_audio": vm_src, "instrumental": False, "vocal_language": "es", "lyrics": lyr,
            "caption": STYLES["vocal"][cap], "audio_cover_strength": acs, "cover_noise_strength": 0.1, "seed": seed}}


def vocal_render(ctx, rnd):
    d, P, V = ctx["dir"], ctx_paths(ctx), C.PATHS["vm"]
    lad = _ladder_entry(ctx, "vocal", rnd)
    sid = ctx["song"]["id"]; inp = f"{V['inputs']}/{sid}"
    C.vm_ps1(f"New-Item -ItemType Directory -Force {inp} | Out-Null", "mk")
    C.scp_to(P["ref_voc"], f"{inp}/ref_vocal.wav")
    jobs = [_acejob(ctx, f"{sid}_v{rnd + 1}_{c}_s{sd}", c, lad["acs"], sd, f"{inp}/ref_vocal.wav") for c in lad["captions"] for sd in lad["seeds"]]
    jf = d / "vocal" / f"jobs_r{rnd + 1}.json"; C.jsave(jf, jobs)
    C.scp_to(jf, f"{V['ace_run']}/jobs_{sid}_r{rnd + 1}.json")
    C.scp_to(T.parent / "vm" / "ace_lab_run.py", f"{V['ace_run']}/ace_lab_run.py")
    C.lab_free()
    with C.LabLock():
        C.say(d, f"ACE hát lại {len(jobs)} bản (~20 giây/bản)")
        C.vm_ps1(f"$env:PYTHONUTF8='1'; cd {V['ace_run']}; & {V['ace_py']} ace_lab_run.py jobs_{sid}_r{rnd + 1}.json 2>&1 | Select-String 'XONG|LỖI|Error|Traceback'", "ace")
    out = d / "vocal" / f"r{rnd + 1}" / "raw"; out.mkdir(parents=True, exist_ok=True)
    for j in jobs:
        C.scp_from(f"{V['outputs']}/{j['name']}.flac", out / f"{j['name']}.flac")
    return {}


def vocal_gate(ctx, rnd):
    d, P, V = ctx["dir"], ctx_paths(ctx), C.PATHS["vm"]
    sid = ctx["song"]["id"]
    raw = sorted((d / "vocal" / f"r{rnd + 1}" / "raw").glob("*.flac"))
    cdir = d / "vocal" / f"r{rnd + 1}" / "clean"; cdir.mkdir(exist_ok=True)
    rows = {}
    for f in raw:
        out = cdir / f"{f.stem}.wav"
        C.run([C.py("mix"), T / "vocal_clean.py", f, P["ref_voc"], out, str(ctx["song"]["plan"].get("clean_hf", 4))])
        vr = C.last_json(run_tx("measure.py", "vocalrow", P["ref_voc"], out).stdout)
        vc = C.last_json(C.run([C.py("tx"), T / "vocal_check.py", P["ref_voc"], out]).stdout)
        rows[f.stem] = {"floor_db": vr["floor_db"], "lag_ms": vr["lag_ms"] if vr["lag_ms"] is not None else 999, "notes_pct": vc["dung_not"]}
    # đo trên VM: giống ca sĩ gốc + độ sai lời (R6: không in lời)
    inp = f"{V['inputs']}/{sid}/clean"; C.vm_ps1(f"New-Item -ItemType Directory -Force {inp} | Out-Null", "mk")
    C.scp_to(P["vocals"], f"{V['inputs']}/{sid}/orig_vocals.wav"); C.scp_to(P["lyr"], f"{V['inputs']}/{sid}/lyrics.txt")
    for f in cdir.glob("*.wav"):
        C.scp_to(f, f"{inp}/{f.name}")
    for nm, local in (("spk_sim.py", T.parent / "vm" / "spk_sim.py"), ("wer_whisper.py", T.parent / "vm" / "wer_whisper.py")):
        C.scp_to(local, f"{V['inputs']}/{sid}/{nm}")
    C.lab_free()
    with C.LabLock():
        txt = C.vm_ps1(f"""$env:PYTHONUTF8='1'; $d='{V['inputs']}/{sid}'; cd $d
$cl=(Get-ChildItem ($d+'/clean/*.wav')).FullName
& {V['spk_py']} spk_sim.py orig_vocals.wav $cl 2>&1 | Select-String 'giong_giong_goc'
$env:WER_LANG='es'; cd {V['ace_run']}
& {V['ace_py']} wer_whisper.py ($d+'/lyrics.txt') $cl 2>&1 | Select-String 'WER'""", "meas")
    for ln in txt.splitlines():
        m = re.match(r"(\S+)\.wav giong_giong_goc ([\d.]+)", ln.strip())
        if m and m.group(1) in rows:
            rows[m.group(1)]["spk_sim"] = float(m.group(2))
        m = re.match(r"(\S+)\.wav WER ([\d.]+)", ln.strip())
        if m and m.group(1) in rows:
            rows[m.group(1)]["wer"] = float(m.group(2))
    out = []
    for n, m in rows.items():
        m.setdefault("spk_sim", 0); m.setdefault("wer", 9)
        out.append({"name": n, "metrics": m, "score": round(m["spk_sim"] - 0.3 * min(m["wer"], 2) + m["notes_pct"] / 400, 3)})
    return {"rows": out}


# ------------------------------------------------------------------ mix / pack / memory
def mix(ctx, rnd):
    d, st, P = ctx["dir"], ctx["state"], ctx_paths(ctx)
    fb = st.get("final_beat") or st["pick_beat"]
    beat = d / "beat" / ("aligned" if "/" not in fb else "") / f"{fb}.wav"
    vrows = C.jload(d / "gates" / "vocal_gate_latest.json")
    voc = [r["name"] for r in vrows["rows"] if r.get("passed")][:2]
    rr = int(re.search(r"_v(\d+)_", voc[0]).group(1))
    (d / "mix").mkdir(exist_ok=True); rows = []
    for v in voc:
        out = d / "mix" / f"{fb.replace('/', '_')}__{v}"
        mx = ctx["song"]["plan"].get("mix", {})
        bal = C.last_json(run_tx("measure.py", "balance", P["vocals"], P["inst"]).stdout)["bal_db"]      # cân bằng giọng/beat của BẢN GỐC
        j = C.last_json(C.run([C.py("mix"), T / "mix_master.py", "--ffmpeg", C.ffmpeg(), "--vocal", d / "vocal" / f"r{rr}" / "clean" / f"{v}.wav", "--beat", beat, "--out", out,
                               "--target-bal", bal + mx.get("bal_offset_db", 0.0), "--duck-db", mx.get("duck_db", 1.0)]).stdout)
        rows.append({"name": out.name, "metrics": {"lufs": j["lufs"], "true_peak": j["true_peak"], "near_peak_pct": j["gan_tran_pct"], "crest_db": j["do_tho_db"],
                                                   "bal_db": j["bal_db"], "bal_goc_db": bal, "bal_err_db": round(abs(j["bal_db"] - mx.get("duck_db", 1.0) - bal - mx.get("bal_offset_db", 0.0)), 2)}, "score": j["do_tho_db"]})
    return {"rows": rows}


def pack(ctx, rnd):
    d, P = ctx["dir"], ctx_paths(ctx)
    pk = d / "NGHE" / "2_ca_bai"; shutil.rmtree(pk, ignore_errors=True)
    mixes = sorted((d / "mix").glob("*.wav"))
    specs = [f"0_ban_goc={P['orig']}"] + [f"{i + 1}_giong_{m.stem.split('__')[-1].replace(ctx['song']['id'] + '_', '')}={m}" for i, m in enumerate(mixes)]
    C.run([C.py("mix"), T / "pack.py", pk, *specs], env={"TARGET": "-17", "FF": C.ffmpeg()})
    gd = d / "NGHE" / "ban_giao_-14LUFS"; gd.mkdir(parents=True, exist_ok=True)
    for m in (d / "mix").glob("*.mp3"):
        shutil.copy(m, gd / m.name)
    (pk / "LISTEN.md").write_text("# Nghe cả bài (cùng độ to −17 LUFS)\n\n0_ban_goc = bài gốc. Các bản còn lại = beat đã duyệt + giọng hát lại. Bản đăng −14 LUFS: ../ban_giao_-14LUFS/\n"
                                  "Duy/bên yêu cầu cho biết: rè không? accordion đủ không? giọng mượt không? Content ID?\n", encoding="utf-8")
    C.say(d, f"Gói nghe cả bài: {pk}. Chờ tai Duy (HG2).")
    return {}


def memory(ctx, rnd):
    d, st = ctx["dir"], ctx["state"]
    note = (f"\n## {time.strftime('%Y-%m-%d')} — {ctx['song']['id']} (tự động ghi)\n- vòng beat dùng: {st.get('round_beat', 0) + 1}, vòng giọng: {st.get('round_vocal', 0) + 1}\n"
            f"- beat được Duy chọn: {st.get('pick_beat')}\n- lời Duy: xem memory/calibration.json (mục song={ctx['song']['id']})\n- Duy bổ sung bài học vào đây: ___\n")
    with open(C.MEM / "lessons.md", "a", encoding="utf-8") as fh:
        fh.write(note)
    C.say(d, "Đã ghi bài học + hiệu chuẩn.")
    return {}


# ------------------------------------------------------------------ vòng DẠO ĐẦU riêng (chạy tại cổng người HG1, nhanh ~25 s/bản)
def _cut_intro_abc(ctx):
    d = ctx["dir"]; made = {}
    for variant in ("full", "full_dense"):
        src = d / "abc" / f"prep_{variant}.abc"
        if not src.exists():
            continue
        t2 = src.read_text(encoding="utf-8"); lines = t2.splitlines(); marks = [i for i, l in enumerate(lines) if l.startswith("% ")]
        if len(marks) < 2:
            continue
        cut = chr(10).join(lines[:marks[1]]) + chr(10)
        a2, ia = parse_abc(t2), parse_abc(cut)
        fa = [n for n in a2 if n[0] < abc_end(cut) - 0.01]
        assert len(ia) == len(fa) and all(abs(x[0] - y[0]) < 1e-6 and x[2] == y[2] for x, y in zip(ia, fa)), "nốt dạo đầu bị đổi (R4)"
        (d / "abc" / f"prep_intro_{variant}.abc").write_text(cut, encoding="utf-8"); made[variant] = round(abc_end(cut), 2)
    return made


def intro_round(ctx, seeds=(21, 22, 23, 24), styles=("cl", "am", "su"), variant="full"):
    """Render thêm nhiều ứng viên dạo đầu (đoạn ngắn), căn bằng 1 độ lệch chung, chấm nhẹ, dựng lại gói nghe HG1."""
    d, st, P = ctx["dir"], ctx["state"], ctx_paths(ctx)
    made = _cut_intro_abc(ctx)
    if variant not in made:
        raise SystemExit("không cắt được bản nốt dạo đầu (thiếu mốc '% ' trong ABC)")
    f = C.jload(P["facts"]); f["intro_end_s"] = made[variant]; C.jsave(P["facts"], f)
    ratio = ctx["song"]["plan"]["tempo_ratio"]; intro_end = made[variant] / ratio
    rn = st.get("intro_round", 0) + 1; st["intro_round"] = rn
    out = d / "beat" / "intro" / f"r{rn}"; out.mkdir(parents=True, exist_ok=True)
    ia = d / "abc" / f"prep_intro_{variant}.abc"; mi = round(abc_end(ia.read_text(encoding="utf-8")) + 5)
    jobs = [(s_, sd) for s_ in styles for sd in seeds]
    C.lab_up(d)
    with C.LabLock():
        for i, (s_, sd) in enumerate(jobs, 1):
            name = f"i{rn}_{s_}_s{sd}"
            C.say(d, f"[intro {i}/{len(jobs)}] YuE2 đánh dạo đầu {name} (~{mi} s)")
            C.run([C.sys.executable, T / "lab_comfy.py", "gen", P["inst"], "--style", STYLES["beat"][s_], "--abc", ia, "--lyrics", "[Intro]\n",
                   "--seed", sd, "--max-duration", mi, "--cfg", 1.0, "--name", name, "--out-dir", out], check=False)
        C.lab_free()
    files = sorted(out.glob("i*_s*.flac"))
    cl = d / "beat" / f"_clap_intro_r{rn}.json"
    C.run([C.py("clap"), T / "clap_check.py", cl, *files])
    clap = {Path(k).name: v for k, v in C.jload(cl).items()}
    al = d / "beat" / "aligned"; al.mkdir(exist_ok=True)

    def one_intro(fl):
        n = fl.stem; o = al / f"{n}.wav"
        txt = run_tx("measure.py", "introalign", P["ref_beat"], fl, o, intro_end).stdout
        ir = {}
        for ln in txt.splitlines():
            if ln.strip().startswith("{"):
                ir.update(json.loads(ln))
        ins = clap.get(fl.name, {}).get("instr", {})
        met = {"voice_pct": round(ins.get("voice_male", 0) + ins.get("voice_duet", 0), 1), "accordion_pct": ins.get("accordion", 0), **ir}
        return {"name": n, "metrics": met, "score": met["intro_match"] + met["intro_cos"], "passed": met["voice_pct"] <= 15 and met["accordion_pct"] >= 40}
    with ThreadPoolExecutor(3) as ex:
        rows = list(ex.map(one_intro, files))
    prev = C.jload(d / "gates" / "intro_latest.json")["rows"] if (d / "gates" / "intro_latest.json").exists() else []
    allrows = [r for r in prev if r["name"] not in {x["name"] for x in rows}] + rows
    allrows.sort(key=lambda r: (-int(r["passed"]), -r["score"]))
    C.jsave(d / "gates" / "intro_latest.json", {"round": rn, "intro_end_s": intro_end, "rows": allrows})
    picks = [r["name"] for r in C.jload(d / "gates" / "beat_gate_latest.json")["rows"] if r["passed"]]
    beat_on_pass(ctx, picks)
    C.say(d, f"Vòng dạo đầu {rn} xong: {sum(r['passed'] for r in rows)}/{len(rows)} bản qua lọc nhẹ. Gói nghe đã dựng lại.")


# bảng tra cho run.py: (hàm, cần_lab, on_pass)
HANDLERS = {
    "intake": (intake, False, None), "abc": (abc, True, None),
    "beat_render": (beat_render, True, None), "beat_gate": (beat_gate, False, beat_on_pass), "finalize_beat": (finalize_beat, False, None),
    "vocal_render": (vocal_render, True, None), "vocal_gate": (vocal_gate, True, None),
    "mix": (mix, False, None), "pack": (pack, False, None), "memory": (memory, False, None),
}
