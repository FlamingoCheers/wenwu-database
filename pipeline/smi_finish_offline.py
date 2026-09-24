import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from collectors.smi_collector import build_relic, is_china_related

OUT = r"E:\codingProject\52-文物数据库\data\relics"
LOG = r"E:\codingProject\52-文物数据库\raw\smi\non_china_skipped.jsonl"
import glob

seen_rows = set()
kept = dup = rejected = 0
for f in sorted(glob.glob(r"E:\codingProject\52-文物数据库\raw\smi\search_9c05ed27_*.json")):
    d = json.load(open(f, encoding="utf-8"))
    for row in d.get("response", {}).get("rows", []):
        if row.get("type") != "edanmdm" or row.get("unitCode") != "NMAA":
            continue
        rid = row.get("url", "")
        if rid in seen_rows:
            dup += 1
            continue
        seen_rows.add(rid)
        ft = row.get("content", {}).get("freetext", {})
        ist = row.get("content", {}).get("indexedStructured", {})
        if not is_china_related(ft, ist):
            rejected += 1
            with open(LOG, "a", encoding="utf-8") as fh:
                fh.write(json.dumps({"id": rid, "title": row.get("title", "")[:80]}, ensure_ascii=False) + "\n")
            continue
        relic = build_relic(row)
        if not relic:
            continue
        p = os.path.join(OUT, relic["id"] + ".json")
        if os.path.exists(p):
            dup += 1
            continue
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(relic, fh, ensure_ascii=False, indent=1)
        kept += 1
print("unique_nmaa_rows=%d kept_new=%d dup_or_existing=%d rejected_noncn=%d" % (len(seen_rows), kept, dup, rejected))
