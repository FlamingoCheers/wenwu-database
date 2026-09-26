import json, glob, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
APPLY = "--apply" in sys.argv

n = {"applied": 0, "year_only": 0, "none": 0}
for vf in sorted(glob.glob("raw/llm_clean/E_era_v_*.jsonl")):
    for line in open(vf, encoding="utf-8"):
        v = json.loads(line)
        d = v.get("dynasty") or "不详"
        yr = v.get("year")
        if d == "不详" and not yr:
            n["none"] += 1
            continue
        p = f"data/relics/{v['id']}.json"
        r = json.load(open(p, encoding="utf-8"))
        changed = False
        if d != "不详" and r.get("dynasty") == "不详":
            r["dynasty"] = d
            r["dynasty_confidence"] = "low"
            r["needs_review"] = True
            changed = True
            n["applied"] += 1
        if yr and not r.get("year_range"):
            r["year_range"] = yr
            changed = True
            n["year_only"] += 1
        if changed and APPLY:
            r["updated_at"] = __import__("datetime").datetime.now().isoformat(timespec="seconds")
            json.dump(r, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

print(n)
