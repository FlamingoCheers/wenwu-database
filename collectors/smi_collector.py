# -*- coding: utf-8 -*-
"""Smithsonian National Museum of Asian Art (Freer|Sackler) collector.

Uses the official Open Access API (api.si.edu, CC0 metadata + images).
Requires SI_API_KEY via env var or raw/si_key.txt.

Query strategy: the API has no field filtering, so we page through
full-text queries and keep rows with unitCode == NMAA. Pages are cached
under raw/smi/search_<start>.json so interrupted runs resume without
re-hitting the API.
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
from collectors.dynasty_util import COARSE_RANGES, map_category, map_dynasty, map_tags  # noqa: E402

API = "https://api.si.edu/openaccess/api/v1.0/search"
UNIT = "NMAA"
OUT_DIR = os.path.join("data", "relics")
RAW_DIR = os.path.join("raw", "smi")

TAG_RE = re.compile(r"<[^>]+>")
CN_RE = re.compile(r"china|chinese", re.I)
CN_DYNASTIES = {"商", "西周", "东周", "春秋", "战国", "秦", "汉", "三国", "西晋", "东晋", "南北朝", "隋", "唐",
                "五代十国", "北宋", "宋", "南宋", "辽", "西夏", "金", "元", "明", "清", "近代", "新石器时代"}


def is_china_related(ft, ist):
    place = " ".join(str(x.get("content", "")) for x in ft.get("place", []))
    topic = " ".join(str(x.get("content", "")) for x in ft.get("topic", []))
    culture = " ".join(str(x.get("content", "")) for x in ft.get("culture", []))
    period = " ".join(str(x.get("content", "")) for x in ft.get("date", []))
    if CN_RE.search(place) or CN_RE.search(topic) or CN_RE.search(culture):
        return True
    dyn, _c = map_dynasty(period, culture)
    return dyn in CN_DYNASTIES

CAT_RULES = [
    (("painting", "scroll", "calligraphy", "album leaf", "on silk", "on paper", "fan"), "书画"),
    (("jade", "nephrite"), "玉器"),
    (("bronze", "brass"), "青铜器"),
    (("porcelain", "ceramic", "stoneware", "earthenware", "terracotta", "pottery", "clay"), "瓷器"),
    (("lacquer",), "漆器"),
    (("silk", "textile", "embroider", "tapestry", "robe", "fabric"), "织绣"),
    (("gold", "silver", "gilt"), "金银器"),
    (("glass",), "玻璃器"),
    (("bamboo", "wood", "ivory", "rhinoceros horn"), "竹木牙角"),
    (("coin", "money", "currency"), "钱币"),
    (("oracle bone",), "甲骨"),
    (("stele", "rubbing", "inscription"), "碑帖拓本"),
    (("brush", "inkstone", "ink cake"), "文房用具"),
    (("buddha", "bodhisattva", "guanyin", "luohan", "deity"), "宗教造像"),
    (("sculpture", "figure", "statue"), "雕塑"),
    (("stone", "marble", "limestone", "relief"), "雕塑"),
]


def load_key():
    k = os.environ.get("SI_API_KEY")
    if k:
        return k.strip()
    p = os.path.join("raw", "si_key.txt")
    if os.path.exists(p):
        return open(p, encoding="utf-8").read().strip()
    raise SystemExit("SI_API_KEY missing: set env or raw/si_key.txt")


def get_json(url, tries=5):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "wenwu-database research collector"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001
            wait = 3 * (i + 1)
            print(f"    retry {i + 1}/{tries} {repr(e)[:90]} -> wait {wait}s", flush=True)
            time.sleep(wait)
    return None


def parse_years(text):
    """Parse SI date strings like 'ca. 3300-2250 BCE', 'ca. 1300 BCE', '18th century'."""
    if not text:
        return None
    t = str(text)
    bc = bool(re.search(r"B\.?C\.?E?\b", t))
    nums = [int(n.replace(",", "")) for n in re.findall(r"\d{1,5}", t)]
    if re.search(r"(\d{1,2})(st|nd|rd|th)\s+century", t, re.I):
        c = int(re.search(r"(\d{1,2})(st|nd|rd|th)\s+century", t, re.I).group(1))
        lo, hi = (c - 1) * 100 + 1, c * 100
        return (-hi, -lo) if bc else (lo, hi)
    if not nums:
        return None
    nums = [(-n if bc else n) for n in nums]
    lo = min(nums)
    hi = max(nums)
    if hi == lo:
        hi = lo + 99
    return (lo, hi)


def pick_category(text):
    low = text.lower()
    for keys, cat in CAT_RULES:
        if any(k in low for k in keys):
            return cat
    cat, _conf = map_category(text)
    return cat


def build_relic(row):
    c = row.get("content", {}) or {}
    dnr = c.get("descriptiveNonRepeating", {}) or {}
    ft = c.get("freetext", {}) or {}
    ist = c.get("indexedStructured", {}) or {}

    def labels(group):
        return " | ".join(str(x.get("content", "")).strip() for x in ft.get(group, []) if x.get("content"))

    record_id = dnr.get("record_ID") or ""
    link = dnr.get("record_link") or ""
    if not record_id:
        return None
    title_raw = (dnr.get("title") or {}).get("content") or row.get("title") or record_id
    title = TAG_RE.sub("", title_raw).strip()

    media = ((dnr.get("online_media") or {}).get("media")) or []
    images = []
    for m in media:
        if m.get("type") == "Images" and (m.get("usage") or {}).get("access", "").upper() == "CC0":
            u = m.get("content")
            if u:
                images.append({"url": u})

    date_lbl = labels("date")
    period_lbl = labels("Period") or date_lbl
    if not period_lbl:
        period_lbl = " | ".join(str(x) for x in ist.get("date", [])[:2])
    medium = labels("physicalDescription")
    origin = labels("place")
    culture = labels("culture")
    provenance = labels("Provenance")
    object_type = labels("objectType")
    credit = labels("creditLine")
    accession = labels("identifier")

    year_range = parse_years(date_lbl) or parse_years("|".join(str(x) for x in ist.get("date", [])))
    dynasty, conf = map_dynasty(period_lbl, title, culture, begin=year_range[0] if year_range else None,
                                end=year_range[1] if year_range else None)
    if dynasty == "不详" and year_range:
        era_low = str(period_lbl or "").lower()
        if re.search(r"period of division|six dynasties|wei jin|northern and southern", era_low) or (216 <= year_range[0] <= 420 and year_range[1] <= 594):
            dynasty = "南北朝"
        else:
            for name, lo, hi in COARSE_RANGES:
                if year_range[0] >= lo - 30 and year_range[1] <= hi + 30:
                    dynasty = name
                    break

    category = pick_category(" | ".join(filter(None, [title, object_type, medium])))

    desc_parts = []
    if period_lbl:
        desc_parts.append(str(period_lbl).replace("|", "，"))
    if medium:
        desc_parts.append(" | ".join(x.strip() for x in medium.split("|")))
    summary = "。".join(desc_parts) if desc_parts else ""
    if provenance:
        summary = (summary + "。Provenance: " + provenance)[:400] if summary else ("Provenance: " + provenance)[:400]
    summary = summary[:400] or None

    rel = {
        "relic_id": "SMI-" + re.sub(r"[^A-Za-z0-9._-]+", "_", record_id),
        "name": title,
        "aliases": [],
        "dynasty": dynasty,
        "dynasty_confidence": conf,
        "year_range": list(year_range) if year_range else None,
        "category": category,
        "material": medium or None,
        "dimensions": medium if ("cm" in medium or "in" in medium) else None,
        "excavated_from": "",
        "summary": summary,
        "history": "",
        "interpretation": [],
        "collection": {
            "museum": "史密森尼国家亚洲艺术博物馆",
            "region": "北美洲",
            "inventory_no": accession or record_id,
        },
        "images": [{"url": im["url"], "license": "CC0",
                    "credit": "National Museum of Asian Art, Smithsonian Institution"} for im in images],
        "source_url": link,
        "license": "CC0",
        "tags": map_tags(title, medium, labels("topic"), object_type),
        "related": [],
        "raw_ref": "raw/smi/search_*.json",
        "needs_review": (dynasty == "不详") or (not images),
        "fetched_at": time.strftime("%Y-%m-%d"),
        "updated_at": time.strftime("%Y-%m-%d"),
    }
    return rel


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=100, help="max records to WRITE this run (0=all)")
    ap.add_argument("--sleep", type=float, default=0.6)
    ap.add_argument("--max-pages", type=int, default=0, help="0 = walk until rowCount exhausted")
    ap.add_argument("--query", default="China")
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--out-dir", default=OUT_DIR)
    ap.add_argument("--raw-dir", default=RAW_DIR)
    ap.add_argument("--no-china-filter", action="store_true")
    args = ap.parse_args()

    key = load_key()
    os.makedirs(args.out_dir, exist_ok=True)
    os.makedirs(args.raw_dir, exist_ok=True)
    reject_log = open(os.path.join(args.raw_dir, "non_china_skipped.jsonl"), "a", encoding="utf-8")

    written = 0
    skipped = 0
    start = args.start
    while True:
        cache = os.path.join(args.raw_dir, "search_%s_%d.json" % (hashlib.md5(args.query.encode()).hexdigest()[:8], start))
        if os.path.exists(cache):
            data = json.load(open(cache, encoding="utf-8"))
        else:
            q = urllib.parse.quote(args.query)
            url = f"{API}?api_key={key}&q={q}&rows=100&start={start}"
            data = get_json(url)
            if not data:
                print(f"page {start} failed after retries, stopping")
                break
            with open(cache, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
            time.sleep(args.sleep)

        resp = data.get("response", {}) or {}
        rows = resp.get("rows", []) or []
        total = resp.get("rowCount", 0)
        nmaa = [r for r in rows if r.get("unitCode") == UNIT and r.get("type") == "edanmdm"]
        print(f"page {start}: rows={len(rows)} NMAA={len(nmaa)} kept={written} skipped_noncn={skipped} (query total {total})", flush=True)

        for row in nmaa:
            if not args.no_china_filter:
                ft = row.get("content", {}).get("freetext", {}) or {}
                ist = row.get("content", {}).get("indexedStructured", {}) or {}
                if not is_china_related(ft, ist):
                    skipped += 1
                    reject_log.write(json.dumps({"id": row.get("id"), "url": row.get("url"),
                                                 "title": TAG_RE.sub("", row.get("title", ""))},
                                                ensure_ascii=False) + "\n")
                    continue
            rel = build_relic(row)
            if not rel:
                continue
            path = os.path.join(args.out_dir, rel["id"] + ".json")
            if os.path.exists(path):
                continue
            with open(path, "w", encoding="utf-8") as f:
                json.dump(rel, f, ensure_ascii=False, indent=1)
            written += 1
            if args.limit and written >= args.limit:
                print(f"limit {args.limit} reached, stopping")
                print(json.dumps(rel, ensure_ascii=False)[:400])
                return

        start += 100
        if rows and start >= total:
            print(f"query exhausted at start={start} (total {total})")
            break
        if args.max_pages and start >= args.start + args.max_pages * 100:
            print(f"max pages reached")
            break


if __name__ == "__main__":
    main()
