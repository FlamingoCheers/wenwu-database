# -*- coding: utf-8 -*-
"""Apply sub-agent verdicts: foreign-origin deletions + Han-era reclassification.

Usage: python pipeline/apply_f_verdicts.py [--apply]
"""
import json, pathlib, sys

ROOT = pathlib.Path(".")
LOW_IDS = {"NPM-24655", "NPM-26052"}

def main(apply):
    deleted, kept = [], 0
    vp = ROOT / "raw/llm_clean/F_foreign_verdict.jsonl"
    for line in vp.read_text(encoding="utf-8").splitlines():
        v = json.loads(line)
        if v["verdict"] != "delete":
            kept += 1
            continue
        p = ROOT / f"data/relics/{v['id']}.json"
        if p.exists():
            print(f"DEL  {v['id']}  {v['origin']} | {v['reason']}")
            deleted.append(v["id"])
            if apply:
                p.unlink()
        else:
            print(f"GONE {v['id']}")
    print(f"foreign: delete={len(deleted)} keep={kept}")

    changed = 0
    hp = ROOT / "raw/llm_clean/F_han_verdict.jsonl"
    for line in hp.read_text(encoding="utf-8").splitlines():
        v = json.loads(line)
        p = ROOT / f"data/relics/{v['id']}.json"
        if not p.exists():
            print(f"SKIP(deleted) {v['id']}")
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        old = (d.get("dynasty"), d.get("year_range"))
        new = (v["dynasty"], v["year_range"])
        if old == new:
            continue
        print(f"ERA {v['id']}: {old[0]}{old[1]} -> {new[0]}{new[1]} | {v.get('reason','')}")
        changed += 1
        if not apply:
            continue
        d["dynasty"], d["year_range"] = new
        d["updated_at"] = "2026-09-22"
        if v["id"] in LOW_IDS or v.get("confidence") == "low":
            d["needs_review"] = True
        p.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"han-era changed={changed}")
    if apply:
        print(f"APPLIED: -{len(deleted)} relics, {changed} era fixes")

if __name__ == "__main__":
    main("--apply" in sys.argv)
