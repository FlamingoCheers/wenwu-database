# -*- coding: utf-8 -*-
"""Harvard Art Museums collector.

API: https://api.harvardartmuseums.org/object (key required, full record on list calls).
Culture/period filters are broken server-side, so recall = union of q= term searches
with hasimage=1. Records are complete on the list call; no detail phase needed.

Usage:
  python collectors/harv_collector.py --limit 0 --sleep 0.3
Key: raw/harvard_key.txt (or env HARVARD_API_KEY in Actions).
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from collectors.dynasty_util import map_dynasty, map_category  # noqa: E402

UA = {"User-Agent": "Mozilla/5.0 (compatible; wenwu-database/1.0)"}
BASE = "https://api.harvardartmuseums.org/object"
FIELDS = ("id,objectnumber,title,dated,beginyear,endyear,period,culture,classification,"
          "medium,technique,dimensions,division,credits,primaryimageurl,images,description,"
          "imagepermissionlevel,seeAlso")
# ES field-syntax query: full recall of Chinese-culture records with images
TERMS = ["culture:Chinese"]
CAT_MAP = [
    (r"painting|drawing|print|calligraphy|album|scroll", "书画"),
    (r"photograph", "历史影像"),
    (r"ceramic|porcelain|stoneware|earthenware|terracotta|pottery|clay", "瓷器"),
    (r"jade|nephrite", "玉器"),
    (r"bronze|metalwork|metal|silver|gold|gilt", "青铜器"),
    (r"sculpture|statue|figure", "雕塑"),
    (r"textile|silk|embroidery|robe", "织绣"),
    (r"glass", "玻璃器"),
    (r"lacquer", "漆器"),
    (r"bamboo|wood|ivory|rhinoceros", "竹木牙角"),
    (r"coin|currency|money", "钱币"),
    (r"oracle", "甲骨"),
    (r"rubbing|stele", "碑帖拓本"),
    (r"buddha|bodhisattva|guanyin|luohan|deity", "宗教造像"),
]


def classify(cl, name, medium):
    txt = " ".join([cl or "", name or "", medium or ""])
    for pat, cat in CAT_MAP:
        if re.search(pat, txt, re.I):
            return cat
    return None


def years_from_era(txt):
    if not txt:
        return None
    m = re.search(r"(-?\d+)\s*[-–]\s*(-?\d+)", txt)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        if abs(a) < 10000 and abs(b) < 10000 and a <= b:
            if re.search(r"BCE", txt, re.I):
                a, b = -abs(a), -abs(b)
            return [a, b]
    m = re.search(r"(-?\d{1,4})s?\s*(BCE|CE)?", txt, re.I)
    if m:
        y = int(m.group(1))
        if abs(y) < 10000:
            if re.search(r"BCE", txt, re.I):
                y = -abs(y)
            return [y, y]
    return None


def parse_years(r):
    b, e = r.get("beginyear"), r.get("endyear")
    if isinstance(b, int) and isinstance(e, int) and b <= e and abs(b) < 10000 and abs(e) < 10000:
        return [b, e]
    return None


def short_summ(desc, medium, dated, culture):
    if desc and len(desc) >= 20:
        return desc[:500]
    bits = [b for b in [culture, dated, medium] if b]
    return "哈佛艺术博物馆著录：" + "；".join(bits) if bits else None


def build(r):
    if (r.get("culture") or "") != "Chinese":
        return None
    img = r.get("primaryimageurl")
    if r.get("imagepermissionlevel") not in (0, None) or not img:
        return None
    img = re.sub(r"[?&]width=\d+", "", img) + "?width=800"
    name = (r.get("title") or r.get("objectnumber") or "").strip()
    if not name:
        return None
    dyn, conf = map_dynasty(r.get("period") or "", r.get("dated") or "", name,
                            begin=parse_years(r)[0] if parse_years(r) else None,
                            end=parse_years(r)[1] if parse_years(r) else None)
    cat = classify(r.get("classification"), name, r.get("medium")) or map_category(name) or "杂器"
    return {
        "relic_id": "HAM-%s" % r["id"],
        "name": name,
        "aliases": [],
        "dynasty": dyn,
        "dynasty_confidence": conf,
        "year_range": parse_years(r) or years_from_era(r.get("dated")),
        "category": cat,
        "material": r.get("medium") or "",
        "dimensions": r.get("dimensions"),
        "era_text": r.get("dated"),
        "summary": short_summ(r.get("description"), r.get("medium"), r.get("dated"), r.get("culture")),
        "history": "",
        "interpretation": [],
        "collection": {
            "museum": "哈佛艺术博物馆",
            "region": "北美洲",
            "inventory_no": r.get("objectnumber") or "",
        },
        "images": [{"url": img, "license": "Harvard Art Museums 开放影像", "credit": "© President and Fellows of Harvard College"}],
        "source_url": "https://harvardartmuseums.org/collections/object/%s" % r["id"],
        "license": "Harvard Art Museums 开放影像",
        "needs_review": dyn == "不详",
        "fetched_at": time.strftime("%Y-%m-%d"),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="0=all")
    ap.add_argument("--sleep", type=float, default=0.3)
    ap.add_argument("--terms", default="")
    ap.add_argument("--raw-dir", default="raw/harv")
    ap.add_argument("--out-dir", default="data/relics")
    args = ap.parse_args()

    key = os.environ.get("HARVARD_API_KEY") or open("raw/harvard_key.txt").read().strip()
    os.makedirs(args.raw_dir, exist_ok=True)
    os.makedirs(args.out_dir, exist_ok=True)

    terms = [t for t in (args.terms.split(",") if args.terms else TERMS) if t]
    seen, kept, noimg = set(), 0, 0
    for term in terms:
        page = 1
        while True:
            cache = os.path.join(args.raw_dir, "list_%s_%d.json" % (hashlib.md5(term.encode()).hexdigest()[:8], page))
            if os.path.exists(cache):
                data = json.load(open(cache, encoding="utf-8"))
            else:
                q = urllib.parse.urlencode({"apikey": key, "q": term, "hasimage": 1, "size": 100,
                                            "page": page, "fields": FIELDS})
                try:
                    data = json.loads(urllib.request.urlopen(urllib.request.Request(BASE + "?" + q, headers=UA), timeout=40).read().decode("utf-8"))
                except Exception as ex:
                    print("FETCH ERR %s p%d: %s" % (term, page, ex))
                    time.sleep(5)
                    continue
                json.dump(data, open(cache, "w", encoding="utf-8"), ensure_ascii=False)
                time.sleep(args.sleep)
            info = data.get("info", {})
            recs = data.get("records") or []
            for r in recs:
                if r["id"] in seen:
                    continue
                seen.add(r["id"])
                rel = build(r)
                if rel is None:
                    noimg += 1
                    continue
                if args.limit and kept >= args.limit:
                    print("LIMIT reached")
                    return
                path = os.path.join(args.out_dir, "%s.json" % rel["relic_id"])
                if not os.path.exists(path):
                    json.dump(rel, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
                kept += 1
                if kept % 50 == 0:
                    print("term[%s] p%d seen=%d kept=%d noimg=%d" % (term, page, len(seen), kept, noimg))
            if page >= info.get("pages", 1) or not recs:
                print("term[%s] done: pages=%d total=%d seen=%d kept=%d noimg=%d" % (term, info.get("pages"), info.get("totalrecords"), len(seen), kept, noimg))
                break
            page += 1
    print("ALL DONE seen=%d kept=%d noimg=%d" % (len(seen), kept, noimg))


if __name__ == "__main__":
    main()
