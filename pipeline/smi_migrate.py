import glob
import json
import time

TODAY = time.strftime("%Y-%m-%d")
for f in glob.glob(r"E:\codingProject\52-文物数据库\data\relics\SMI-*.json"):
    d = json.load(open(f, encoding="utf-8"))
    if "relic_id" in d:
        continue
    rid = d.get("id", "")
    acc = d.get("accession") or rid.replace("SMI-", "")
    summary = d.get("summary") or ""
    prov = d.get("provenance")
    if prov:
        summary = (summary + "。Provenance: " + prov)[:400]
    nd = {
        "relic_id": rid,
        "name": d.get("name_en") or d.get("name_zh") or rid,
        "aliases": [],
        "dynasty": d.get("dynasty"),
        "dynasty_confidence": d.get("dynasty_confidence"),
        "year_range": d.get("year_range"),
        "category": d.get("category"),
        "material": (d.get("dimensions") if d.get("dimensions") else None) or None,
        "dimensions": d.get("dimensions"),
        "excavated_from": "",
        "summary": summary or None,
        "history": "",
        "interpretation": [],
        "collection": {
            "museum": "史密森尼国家亚洲艺术博物馆",
            "region": "北美洲",
            "inventory_no": acc,
        },
        "images": [{"url": im["url"] if isinstance(im, dict) else im,
                    "license": "CC0",
                    "credit": "National Museum of Asian Art, Smithsonian Institution"}
                   for im in (d.get("images") or [])],
        "source_url": d.get("source_url"),
        "license": "CC0",
        "tags": d.get("tags") or [],
        "related": [],
        "raw_ref": "raw/smi/search_*.json",
        "needs_review": d.get("needs_review", False),
        "fetched_at": TODAY,
        "updated_at": TODAY,
    }
    json.dump(nd, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("migrated")
