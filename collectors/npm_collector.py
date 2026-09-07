"""National Palace Museum (Taipei) collector.

Data source: https://digitalarchive.npm.gov.tw/opendata  (open data search)
License: per-object CC0 1.0 or CC BY 4.0 (badge on detail page).
Network note: unreachable from mainland; designed to run on GitHub Actions
ubuntu runners. All parsing helpers are pure functions testable locally
against cached raw pages.

Usage:
  python collectors/npm_collector.py --dynasty 宋 --limit 0
  python collectors/npm_collector.py --dynasty all          # every dynasty axis
  python collectors/npm_collector.py --dynasty 明 --pages 3 # dry slice
"""
import html
import json
import os
import re
import sys
import time
import urllib.request
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dynasty_util as du  # noqa: E402

BASE = "https://digitalarchive.npm.gov.tw"
SEARCH_URL = BASE + "/opendata/Pub/Search"
UA = {"User-Agent": "Mozilla/5.0 (wenwu-database open-data collector)"}

# radio values from the search page: "begin~end~label"
DYN_AXIS = [
    ("新石器時代", -7000, -2000),
    ("商", -1600, -1046),
    ("西周", -1100, -800),
    ("春秋", -800, -500),
    ("戰國", -500, -300),
    ("秦", -221, -207),
    ("西漢", -206, 8),
    ("東漢", 25, 220),
    ("魏晉南北朝", 220, 589),
    ("隋", 581, 618),
    ("唐", 618, 907),
    ("五代", 907, 960),
    ("遼", 907, 1125),
    ("宋", 960, 1279),
    ("金", 1115, 1234),
    ("元", 1271, 1368),
    ("明", 1368, 1644),
    ("清", 1644, 1911),
    ("民國", 1911, 9999),
]

CATEGORY_MAP = {
    "銅器": "青铜器",
    "陶瓷器": "瓷器",
    "玉器": "玉器",
    "琺瑯器": "杂器",
    "雕刻": "雕塑",
    "漆器": "漆器",
    "錢幣": "钱币",
    "文具": "文房用具",
    "雜項": "杂器",
    "織品": "织绣",
    "絲繡": "织绣",
    "繪畫": "书画",
    "法書": "书画",
    "法帖": "书画",
    "拓片": "书画",
    "成扇": "书画",
    "其他": "杂器",
}

DETAIL_RE = re.compile(r'href="(/opendata/Pub/Detail/(\d+)\?dep=([A-Z]))&amp;mode=full"')
PAGECOUNT_RE = re.compile(r'"PageCount":(\d+)')
TR_RE = re.compile(r"<tr>\s*<td>\s*([^<]{1,14})</td>\s*<td>(.*?)</td>", re.S)
IMG_RE = re.compile(r'data-image="(/opendata/Image/GetImage\?[^"]+)"')
CAPTION_RE = re.compile(r'<img[^>]+alt="([^"]{2,40})"[^>]+(?:data-image|src)="/opendata/Image/GetImage')


def post_json(url, body, timeout=60):
    req = urllib.request.Request(
        url, data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={**UA, "Content-Type": "application/json",
                 "Referer": BASE + "/opendata"}, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def get_html(url, timeout=60):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def parse_list(html_text):
    """Return (detail_hrefs, page_count) from a Search response page."""
    seen, items = set(), []
    for href, oid, dep in DETAIL_RE.findall(html_text):
        if oid not in seen:
            seen.add(oid)
            items.append(f"/opendata/Pub/Detail/{oid}?dep={dep}&mode=full")
    m = PAGECOUNT_RE.search(html_text)
    return items, (int(m.group(1)) if m else None)


def _clean(td_html):
    t = re.sub(r"<br\s*/?>", "\n", td_html)
    t = re.sub(r"<[^>]+>", "", t)
    return re.sub(r"[ \t\r]+", " ", html.unescape(t)).strip()


def parse_detail(html_text):
    """Parse a Detail page into a dict of raw fields."""
    fields = {}
    for k, v in TR_RE.findall(html_text):
        k = _clean(k)
        if k and k not in fields:
            fields[k] = _clean(v)
    images = []
    for url in IMG_RE.findall(html_text):
        images.append(BASE + url.replace("&amp;", "&"))
    caps = CAPTION_RE.findall(html_text)
    license_ = None
    if "CC0.svg" in html_text:
        license_ = "CC0 1.0"
    elif "CC_BY_4.0.svg" in html_text:
        license_ = "CC BY 4.0"
    return {
        "inv": fields.get("文物統一編號"),
        "name_zh": (fields.get("品名") or "").split("\n")[0].strip(),
        "name_en": next((ln.strip() for ln in (fields.get("品名") or "").split("\n")[1:]
                         if re.search(r"[A-Za-z]{3,}", ln)), None),
        "category_raw": fields.get("分類"),
        "era": (fields.get("時代") or "").split("\n")[0].strip(),
        "years": (fields.get("時代") or ""),
        "dimensions": fields.get("尺寸"),
        "desc": fields.get("說明"),
        "images": images,
        "captions": caps,
        "license": license_,
    }


def map_category(raw, name, desc):
    if raw in CATEGORY_MAP:
        cat = CATEGORY_MAP[raw]
        if cat == "瓷器" and re.search(r"陶|瓦|磚", name or ""):
            return "陶器"
        return cat
    return du.map_category(name, desc or "")


def build_relic(detail_path, oid, dep, fetched):
    with open(detail_path, encoding="utf-8", errors="replace") as f:
        raw_html = f.read()
    d = parse_detail(raw_html)
    if not d["name_zh"]:
        return None
    begin = end = None
    m = re.search(r"西元\s*(-?\d+)\s*[-~至]\s*(-?\d+)", d["years"])
    if m:
        begin, end = int(m.group(1)), int(m.group(2))
    dynasty, conf = du.map_dynasty(d["era"], d["name_zh"], begin=begin, end=end)
    if dynasty == "不详" and begin is not None:
        dynasty, conf = du.map_dynasty(begin=begin, end=end)
    cat = map_category(d["category_raw"], d["name_zh"], d["desc"])
    images = []
    for u in d["images"][:2]:
        images.append({
            "url": u,
            "license": d["license"] or "CC BY 4.0",
            "credit": "國立故宮博物院 (National Palace Museum)",
        })
    needs_review = (dynasty == "不详") or (not images) or (d["license"] is None)
    return {
        "relic_id": f"NPM-{oid}",
        "name": d["name_zh"],
        "aliases": [d["name_en"]] if d["name_en"] else [],
        "dynasty": dynasty,
        "dynasty_confidence": conf,
        "year_range": [begin, end] if begin is not None else None,
        "category": cat,
        "material": None,
        "dimensions": d["dimensions"],
        "excavated_from": "",
        "collection": {
            "museum": "台北故宫博物院",
            "region": "中国台湾",
            "inventory_no": d["inv"] or f"NPM-{oid}",
        },
        "summary": (d["desc"] or "")[:300] or None,
        "history": "",
        "interpretation": [],
        "images": images,
        "source_url": f"{BASE}/opendata/Pub/Detail/{oid}?dep={dep}&mode=full",
        "license": d["license"] or "CC BY 4.0",
        "tags": du.map_tags(d["name_zh"], d["desc"] or ""),
        "related": [],
        "raw_ref": f"raw/npm/detail_{oid}.html",
        "needs_review": needs_review,
        "fetched_at": fetched,
        "updated_at": fetched,
    }


def crawl(dynasty_key, limit, pages, sleep, out_dir):
    axis = DYN_AXIS if dynasty_key == "all" else [
        a for a in DYN_AXIS if a[0] == dynasty_key]
    if not axis:
        print(f"unknown dynasty: {dynasty_key}; options: all | " +
              "|".join(a[0] for a in DYN_AXIS))
        return
    fetched = date.today().isoformat()
    stats = {"in": 0, "skip": 0, "fail": 0}
    for label, lo, hi in axis:
        year_display = f"{lo}~{hi}~{label}"
        print(f"== axis {label} ({lo}~{hi}) ==")
        page, page_count, done = 1, None, False
        while not done:
            list_cache = os.path.join(out_dir, f"list_{label}_{page}.html")
            if os.path.exists(list_cache):
                with open(list_cache, encoding="utf-8", errors="replace") as f:
                    page_html = f.read()
            else:
                body = {"RegisterType": None, "IndexYear": None,
                        "WestBeginYear": lo, "WestEndYear": hi,
                        "YearDisplay": year_display, "SearchContent": None,
                        "RegisterTypeEng": None,
                        "PageInfo": {"PageIndex": page, "PageSize": 50,
                                     "PageCount": 0}}
                try:
                    page_html = post_json(SEARCH_URL, body)
                except Exception as e:
                    print(f"  list p{page} error: {e}")
                    stats["fail"] += 1
                    break
                with open(list_cache, "w", encoding="utf-8") as f:
                    f.write(page_html)
                time.sleep(sleep)
            items, page_count = parse_list(page_html)
            print(f"  page {page}/{page_count} -> {len(items)} items")
            if not items:
                break
            for href in items:
                oid = re.search(r"/Detail/(\d+)", href).group(1)
                dep = re.search(r"dep=([A-Z])", href).group(1)
                out_path = os.path.join("data", "relics", f"NPM-{oid}.json")
                if os.path.exists(out_path):
                    stats["skip"] += 1
                    continue
                detail_cache = os.path.join(out_dir, f"detail_{oid}.html")
                if not os.path.exists(detail_cache):
                    try:
                        detail_html = get_html(BASE + href.replace("&amp;", "&"))
                        with open(detail_cache, "w", encoding="utf-8") as f:
                            f.write(detail_html)
                        time.sleep(sleep)
                    except Exception as e:
                        print(f"  detail {oid} error: {e}")
                        stats["fail"] += 1
                        continue
                relic = build_relic(detail_cache, oid, dep, fetched)
                if relic is None:
                    stats["skip"] += 1
                    continue
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(relic, f, ensure_ascii=False, indent=1)
                stats["in"] += 1
                if limit and stats["in"] >= limit:
                    done = True
                    break
            if done or (page_count and page >= page_count) or \
                    (pages and page >= pages):
                break
            page += 1
    print(f"done: in={stats['in']} skip={stats['skip']} fail={stats['fail']}")


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--dynasty", default="宋",
                    help="axis label (e.g. 宋/明) or 'all'")
    ap.add_argument("--limit", type=int, default=0,
                    help="max items to ingest this run (0 = unlimited)")
    ap.add_argument("--pages", type=int, default=0,
                    help="max list pages per axis (0 = all)")
    ap.add_argument("--sleep", type=float, default=0.5)
    ap.add_argument("--out", default="raw/npm")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    crawl(args.dynasty, args.limit, args.pages, args.sleep, args.out)


if __name__ == "__main__":
    main()
