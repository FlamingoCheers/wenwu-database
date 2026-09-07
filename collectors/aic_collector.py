# -*- coding: utf-8 -*-
"""芝加哥艺术馆(AIC)采集器——A类 API 直连。

数据源: https://api.artic.edu/api/v1/artworks/search
- ES term 过滤只能单字段 → query[term][place_of_origin]=china (小写!)
- 分页拉全量摘要(fields 一次带全), 本地筛 is_public_domain + image_id
- IIIF 图片: https://www.artic.edu/iiif/2/{image_id}/full/843,/0/default.jpg (CC0)
- 朝代: date_start/date_end 数字直接给 du.map_dynasty(begin, end)
- 分页缓存 raw/aic/page_{N}.json, 断点续跑(已入库跳过)
用法: python aic_collector.py [--limit N] [--sleep 秒] [--force]
"""
import argparse
import json
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dynasty_util as du

ROOT = Path(__file__).resolve().parent.parent
RELICS_DIR = ROOT / "data" / "relics"
RAW_DIR = ROOT / "raw" / "aic"
API = "https://api.artic.edu/api/v1/artworks/search"
HEADERS = {"User-Agent": "wenwu-database/0.1 (open-source aggregation of open-access museum data)"}
MUSEUM = "芝加哥艺术馆"
MUS_CODE = "AIC"
TODAY = date.today().isoformat()
PAGE_SIZE = 100

# search fields: 一次带全所需字段
FIELDS = ",".join([
    "id", "title", "place_of_origin", "is_public_domain", "image_id",
    "date_start", "date_end", "medium_display", "dimensions", "credit_line",
    "classification_title", "style_titles", "inscriptions", "description",
    "alt_text", "api_link",
])

# 关键词→本库类别(优先级序, 对 medium_display 与 classification_title 做包含扫描)
KW_CATEGORY = [
    (["porcelain", "stoneware", "qingbai", "celadon", "ceramic"], "瓷器"),
    (["earthenware", "pottery", "terracotta"], "陶器"),
    (["jade", "nephrite"], "玉器"),
    (["bronze"], "青铜器"),
    (["gold", "silver", "gilt"], "金银器"),
    (["lacquer"], "漆器"),
    (["embroidery", "textile", "kesi", "tapestry", "silk"], "织绣"),
    (["glass"], "玻璃器"),
    (["ivory", "bamboo", "wood carving"], "竹木牙角"),
    (["handscroll", "hanging scroll", "album leaf", "album", "calligraphy", "woodcut",
      "fan painting", "ink and color", "ink on paper", "printing"], "书画"),
    (["marble", "limestone", "sandstone", "shale", "quartzite", "stone", "sculpture"], "雕塑"),
]


def map_category(*texts):
    blob = " ".join(t.lower() for t in texts if t)
    for kws, cat in KW_CATEGORY:
        for kw in kws:
            if kw in blob:
                return cat
    return "杂器"


BUDDHIST_KWS = ("buddha", "bodhisattva", "guanyin", "luohan", "arhat",
                "buddhis", "maitreya", "avalokiteshvara", "avalokitesvara")


def fetch(url, timeout=30):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def summarize(rec):
    bits = []
    if rec.get("medium_display"):
        bits.append(rec["medium_display"].strip())
    if rec.get("dimensions"):
        bits.append(" ".join(rec["dimensions"].split()))
    if rec.get("credit_line"):
        bits.append(rec["credit_line"].strip())
    return "。".join([b for b in bits if b]) or None


def to_relic(rec):
    title = (rec.get("title") or "未命名").strip()
    inv = str(rec.get("id"))
    year = None
    if rec.get("date_start") is not None:
        year = rec["date_start"]
    sty = rec.get("style_titles") or []
    cls = (rec.get("classification_title") or "").lower()
    dyn, conf = du.map_dynasty(" ".join(sty), title,
                               begin=rec.get("date_start"), end=rec.get("date_end"))
    if dyn == "不详" and rec.get("date_end") is not None:
        dyn, conf = du.map_dynasty(" ".join(sty), title,
                                   begin=rec.get("date_end"), end=rec.get("date_end"))
    category = map_category(rec.get("medium_display"), rec.get("classification_title"),
                            " ".join(sty), title)
    # 宗教造像: 雕塑/杂器 + 佛教题材
    low = title.lower()
    if category in ("雕塑", "杂器") and any(k in low for k in BUDDHIST_KWS):
        category = "宗教造像"
    tags = du.map_tags(title, " ".join(sty), cls, rec.get("medium_display") or "", rec.get("inscriptions") or "")
    images = []
    if rec.get("image_id"):
        images.append({
            "url": f"https://www.artic.edu/iiif/2/{rec['image_id']}/full/843,/0/default.jpg",
            "license": "CC0",
            "credit": f"{MUSEUM} {rec.get('credit_line') or ''}".strip(),
        })
    return {
        "relic_id": f"{MUS_CODE}-{inv}",
        "name": title,
        "aliases": [],
        "dynasty": dyn,
        "dynasty_confidence": conf,
        "year_range": [rec.get("date_start"), rec.get("date_end")] if rec.get("date_start") is not None else None,
        "category": category,
        "material": (rec.get("medium_display") or None),
        "dimensions": (" ".join(rec["dimensions"].split()) if rec.get("dimensions") else None),
        "excavated_from": "",
        "summary": summarize(rec),
        "history": (rec.get("description") or ""),
        "interpretation": [],
        "collection": {
            "museum": MUSEUM,
            "region": "北美洲",
            "inventory_no": inv,
        },
        "images": images,
        "source_url": f"https://www.artic.edu/artworks/{inv}",
        "license": "CC0",
        "tags": tags,
        "related": [],
        "raw_ref": f"raw/aic/page_*.json (id={inv})",
        "needs_review": dyn == "不详" or not images,
        "fetched_at": TODAY,
        "updated_at": TODAY,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="最多入库 N 件(0=全量)")
    ap.add_argument("--sleep", type=float, default=0.15)
    ap.add_argument("--force", action="store_true", help="重抓已存在记录")
    args = ap.parse_args()

    RELICS_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    # 第一页拿 total
    q = urllib.parse.urlencode({"query[term][place_of_origin]": "china",
                                "fields": FIELDS, "limit": PAGE_SIZE, "page": 1})
    p1 = fetch(f"{API}?{q}")
    total = p1["pagination"]["total"]
    pages = p1["pagination"]["total_pages"]
    print(f"AIC 中国藏品 total={total} pages={pages}")

    added = skipped = failed = 0
    for page in range(1, pages + 1):
        cache = RAW_DIR / f"page_{page}.json"
        if cache.exists():
            data = json.loads(cache.read_text(encoding="utf-8"))
        else:
            q = urllib.parse.urlencode({"query[term][place_of_origin]": "china",
                                        "fields": FIELDS, "limit": PAGE_SIZE, "page": page})
            try:
                data = fetch(f"{API}?{q}")
            except Exception as e:
                print(f"  page {page} 请求失败: {e}")
                failed += 1
                continue
            cache.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            time.sleep(args.sleep)

        for rec in data.get("data", []):
            if not rec.get("is_public_domain") or not rec.get("image_id"):
                skipped += 1
                continue
            out = RELICS_DIR / f"{MUS_CODE}-{rec['id']}.json"
            if out.exists() and not args.force:
                continue
            try:
                relic = to_relic(rec)
                out.write_text(json.dumps(relic, ensure_ascii=False, indent=1), encoding="utf-8")
                added += 1
            except Exception as e:
                failed += 1
                print(f"  {rec.get('id')} 失败: {e}")
        if args.limit and added >= args.limit:
            break
        print(f"  page {page}/{pages} 累计入库 {added} 跳过 {skipped} 失败 {failed}")

    print(f"完成：入库 {added}  跳过 {skipped}  失败 {failed}")


if __name__ == "__main__":
    main()
