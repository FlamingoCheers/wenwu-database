# -*- coding: utf-8 -*-
"""LLM 数据清理编排器（子 Agent 方案的本地配套）

子命令:
  prep A      重新扫描全库分类疑误 -> raw/llm_clean/A_classify_todo.jsonl（全量）
  merge A     合并 raw/llm_clean/A_result_*.jsonl -> 校验词表/置信度 -> A_apply.json + A_lowconf.json
  apply A     把 A_apply.json 写回 data/relics/*.json（改 category；low confidence -> needs_review=true）
              附带回滚日志 raw/llm_clean/apply_A_journal.json
  prep B      扫描全库 summary<20字 -> B_desc_todo.jsonl（MET/NMC 附 raw 事实字段供 LLM 兜底；NPM 标 mode=actions 留给回源）
  merge B     合并 B_result_*.jsonl {id,summary} -> 长度/质量校验 -> B_apply.json
  apply B     写回 summary（仅当现有过短），置 desc_ai=true + needs_review=true，日志 apply_B_journal.json
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RELICS = ROOT / "data" / "relics"
LC = ROOT / "raw" / "llm_clean"
VOCAB = ROOT / "data" / "vocab" / "categories.json"

KEYWORD_CAT = [
    (r"通宝|重宝|元宝|五铢|布币|刀币|钱范|贝币", "钱币"),
    (r"瓷", "瓷器"),
    (r"陶|唐三彩|瓦当", "陶器"),
    (r"玉|珉|璜|璧|琮|璋|珮", "玉器"),
    (r"漆|剔红|剔黑|螺钿", "漆器"),
    (r"绣|锦|缎|绸|纱|罗|绢|毡|氅", "织绣"),
    (r"玻璃|琉璃|料器", "玻璃器"),
    (r"砚|墨锭|镇纸|笔洗|笔架|印泥", "文房用具"),
    (r"拓本|碑刻|墓志", "碑帖拓本"),
    (r"甲骨|卜辞|卜骨", "甲骨"),
    (r"瓦|砖|构件|斗拱|鸱吻", "建筑构件"),
]
SOFT_KEYWORD_CAT = [
    (r"鼎|簋|爵|觚|尊|卣|斝|觥|簠|盨|敦|壶|盘|匜|钟|镜|炉", "青铜器"),
    (r"金杯|金盏|金碗|金壶|银盒|银盘|银杯|金饰|银饰|簪|钗|镯", "金银器"),
    (r"佛|菩萨|罗汉|造像|造像碑", "宗教造像"),
]


def vocab_cats():
    return {c["key"] for c in json.loads(VOCAB.read_text(encoding="utf-8"))["categories"]}


def scan_suspects():
    out = []
    for f in sorted(RELICS.glob("*.json")):
        r = json.loads(f.read_text(encoding="utf-8"))
        cat = r.get("category") or ""
        name = r.get("name") or ""
        expect, level = None, None
        for pat, want in KEYWORD_CAT:
            if re.search(pat, name) and cat != want:
                expect, level = want, "strong"
                break
        if not expect:
            for pat, want in SOFT_KEYWORD_CAT:
                if re.search(pat, name) and cat != want:
                    expect, level = want, "soft"
                    break
        if expect:
            out.append({
                "id": r.get("relic_id", f.stem), "name": name, "cur_cat": cat,
                "expect": expect, "level": level, "material": r.get("material") or "",
                "dynasty": r.get("dynasty") or "", "summary": (r.get("summary") or "")[:160],
            })
    return out


def cmd_prep(task):
    if task == "A":
        LC.mkdir(parents=True, exist_ok=True)
        rows = scan_suspects()
        with (LC / "A_classify_todo.jsonl").open("w", encoding="utf-8") as w:
            for row in rows:
                w.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"A_classify_todo.jsonl: {len(rows)} rows")
        return
    assert task == "B"
    LC.mkdir(parents=True, exist_ok=True)
    rows, skipped_npm = [], 0
    for f in sorted(RELICS.glob("*.json")):
        r = json.loads(f.read_text(encoding="utf-8"))
        s = (r.get("summary") or "").strip()
        if len(s) >= 20:
            continue
        rid = r.get("relic_id", f.stem)
        pre = rid.split("-")[0]
        if pre == "NPM":
            skipped_npm += 1  # 留给 Actions 回源 job
            continue
        row = {
            "id": rid,
            "name": r.get("name") or "",
            "category": r.get("category") or "",
            "dynasty": r.get("dynasty") or "",
            "material": (r.get("material") or "")[:200],
            "dimensions": (r.get("dimensions") or "")[:200],
            "cur_summary": s,
            "museum": (r.get("collection") or {}).get("museum", ""),
        }
        if pre == "MET":
            rawp = ROOT / "raw" / "met" / f"{rid.split('-')[1]}.json"
            facts = {}
            if rawp.exists():
                d = json.loads(rawp.read_text(encoding="utf-8"))
                facts = {
                    "title": d.get("title") or "",
                    "medium": (d.get("medium") or "").replace("\r\n", "; ")[:200],
                    "objectDate": d.get("objectDate") or "",
                    "culture": d.get("culture") or "",
                    "creditLine": d.get("creditLine") or "",
                    "classification": d.get("classification") or "",
                    "tags": [t.get("term") for t in (d.get("tags") or []) if t.get("term")][:8],
                }
            row["facts"] = facts
            row["mode"] = "met"
        else:
            row["mode"] = "nmc"
        rows.append(row)
    with (LC / "B_desc_todo.jsonl").open("w", encoding="utf-8") as w:
        for row in rows:
            w.write(json.dumps(row, ensure_ascii=False) + "\n")
    by = {}
    for row in rows:
        by[row["mode"]] = by.get(row["mode"], 0) + 1
    print(f"B_desc_todo.jsonl: {len(rows)} rows {by}（NPM 跳过 {skipped_npm} 件留待回源）")


def merge_a():
    cats = vocab_cats()
    results = {}
    for f in sorted(LC.glob("A_result_*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                print(f"  [warn] 非 JSON 行忽略: {f.name}")
                continue
            if d.get("id"):
                results[d["id"]] = d
    todo = [json.loads(l) for l in (LC / "A_classify_todo.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    apply_list, lowconf, missing, badcat = [], [], [], []
    for t in todo:
        d = results.get(t["id"])
        if not d:
            missing.append(t["id"])
            continue
        final = (d.get("final_cat") or "").strip()
        if final not in cats:
            badcat.append({"id": t["id"], "final_cat": final})
            continue
        if final == t["cur_cat"]:
            continue
        conf = d.get("confidence", "low")
        row = {"id": t["id"], "from": t["cur_cat"], "to": final, "confidence": conf,
               "reason": (d.get("reason") or "")[:120]}
        (lowconf if conf == "low" else apply_list).append(row)
    (LC / "A_apply.json").write_text(json.dumps(apply_list, ensure_ascii=False, indent=1), encoding="utf-8")
    (LC / "A_lowconf.json").write_text(json.dumps(lowconf, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"结果 {len(results)} / 任务 {len(todo)} | 待应用 {len(apply_list)} | 低置信保留原类 {len(lowconf)} | "
          f"缺失 {len(missing)} | 词表外 {len(badcat)}")
    if missing:
        print("  缺失样例:", missing[:8])


def merge_b():
    # ---- B ----
    results = {}
    for f in sorted(LC.glob("B_result_*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                print(f"  [warn] 非 JSON 行忽略: {f.name}")
                continue
            if d.get("id"):
                results[d["id"]] = d
    todo = [json.loads(l) for l in (LC / "B_desc_todo.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    apply_list, bad = [], []
    for t in todo:
        d = results.get(t["id"])
        if not d:
            bad.append({"id": t["id"], "why": "missing"})
            continue
        txt = (d.get("summary") or "").strip()
        if len(txt) < 15:
            bad.append({"id": t["id"], "why": f"too_short:{len(txt)}"})
            continue
        if len(txt) > 400:
            txt = txt[:400]
        if txt == t.get("cur_summary"):
            bad.append({"id": t["id"], "why": "unchanged"})
            continue
        apply_list.append({"id": t["id"], "summary": txt, "confidence": d.get("confidence", "medium")})
    (LC / "B_apply.json").write_text(json.dumps(apply_list, ensure_ascii=False, indent=1), encoding="utf-8")
    (LC / "B_reject.json").write_text(json.dumps(bad, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"结果 {len(results)} / 任务 {len(todo)} | 待应用 {len(apply_list)} | 拒绝 {len(bad)}")
    if bad:
        print("  拒绝样例:", bad[:5])


def cmd_apply(task):
    assert task == "A"
    apply_list = json.loads((LC / "A_apply.json").read_text(encoding="utf-8"))
    lowconf = json.loads((LC / "A_lowconf.json").read_text(encoding="utf-8"))
    journal = []
    changed = 0
    for row in apply_list:
        p = RELICS / (row["id"] + ".json")
        r = json.loads(p.read_text(encoding="utf-8"))
        old = r.get("category")
        r["category"] = row["to"]
        if r.get("dynasty") in (None, "", "不详"):
            r["needs_review"] = True
        journal.append({"id": row["id"], "field": "category", "was": old, "now": row["to"]})
        p.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
        changed += 1
    review_added = 0
    for row in lowconf:
        p = RELICS / (row["id"] + ".json")
        r = json.loads(p.read_text(encoding="utf-8"))
        if not r.get("needs_review"):
            r["needs_review"] = True
            p.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
            journal.append({"id": row["id"], "field": "needs_review", "was": False, "now": True})
            review_added += 1
    (LC / "apply_A_journal.json").write_text(json.dumps(journal, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"已改分类 {changed} 件，低置信标 review {review_added} 件，日志 {len(journal)} 条 -> apply_A_journal.json")


def cmd_apply_b():
    apply_list = json.loads((LC / "B_apply.json").read_text(encoding="utf-8"))
    journal = []
    changed = 0
    for row in apply_list:
        p = RELICS / (row["id"] + ".json")
        r = json.loads(p.read_text(encoding="utf-8"))
        if len((r.get("summary") or "").strip()) >= 20:
            continue  # 已被回源等步骤补全，不覆盖
        old = r.get("summary")
        r["summary"] = row["summary"]
        r["desc_ai"] = True
        r["needs_review"] = True
        journal.append({"id": row["id"], "field": "summary", "was": old, "now": row["summary"][:60]})
        p.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
        changed += 1
    (LC / "apply_B_journal.json").write_text(json.dumps(journal, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"已补描述 {changed} 件（desc_ai+needs_review），日志 {len(journal)} 条 -> apply_B_journal.json")


if __name__ == "__main__":
    cmd, task = sys.argv[1], sys.argv[2]
    if cmd == "apply" and task == "B":
        cmd_apply_b()
    elif cmd == "merge" and task == "B":
        merge_b()
    elif cmd == "merge" and task == "A":
        merge_a()
    else:
        {"prep": cmd_prep, "apply": cmd_apply}[cmd](task)
