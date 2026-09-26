# -*- coding: utf-8 -*-
"""HAM records -> standard schema (collection{museum,region,inventory_no}, material)."""
import glob
import io
import json
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

n = 0
for f in glob.glob("data/relics/HAM-*.json"):
    r = json.load(open(f, encoding="utf-8"))
    if "collection" in r:
        continue
    r["collection"] = {
        "museum": "哈佛艺术博物馆",
        "region": "北美洲",
        "inventory_no": r.get("inventory_no") or "",
    }
    r["material"] = r.pop("medium", None) or ""
    r.pop("museum", None)
    r.pop("region", None)
    r.pop("inventory_no", None)
    json.dump(r, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    n += 1
print("migrated:", n)
