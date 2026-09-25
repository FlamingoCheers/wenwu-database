"""V&A (Victoria and Albert Museum) collector.

Source: https://api.vam.ac.uk (official open API, no key required).
Scope: objects with production place China (+ major Chinese production
centres) and existing imagery. Full metadata via per-object detail endpoint.

CLI:
    python collectors/va_collector.py --limit 0 --sleep 0.25 --workers 4
"""
import io
import json
import os
import sys
import threading
import time
import urllib.request
from queue import Queue

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from collectors.dynasty_util import map_dynasty, map_category  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RE_DIR = os.path.join(ROOT, "data", "relics")
RAW_DIR = os.path.join(ROOT, "raw", "va")
BASE = "https://api.vam.ac.uk/v2"
UA = "wenwu-database/1.0 (open-data aggregation; https://github.com/FlamingoCheers/wenwu-database)"

PLACE_IDS = ["x29398", "x32230", "x32464", "x32780"]  # China, Jingdezhen, Guangzhou, Beijing

CAT_MAP = {"ceramics": "瓷器", "metalwork": "青铜器", "sculpture": "雕塑", "painting": "书画",
           "calligraphy": "书画", "jade": "玉器", "textiles": "织绣", "furniture": "竹木牙角",
           "glass": "玻璃器", "bamboo": "竹木牙角", "east asia": "杂器"}

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

_lock = threading.Lock()
_stats = {"ok": 0, "skip": 0, "noimg": 0, "err": 0}


def api_get(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            return json.load(urllib.request.urlopen(req, timeout=40))
        except Exception as e:
            if i == retries - 1:
                raise
            time.sleep(2 * (i + 1))


def cache_get(path, url):
    if os.path.exists(path):
        return json.load(open(path, encoding="utf-8"))
    d = api_get(url)
    json.dump(d, open(path, "w", encoding="utf-8"), ensure_ascii=False)
    time.sleep(0.15)
    return d


YEAR_BUCKETS = [(-6000, 999), (1000, 1699), (1700, 1799), (1800, 2100)]


def list_pages(items, base_url, cache_prefix, total):
    page = 1
    while True:
        path = os.path.join(RAW_DIR, "%s_%d.json" % (cache_prefix, page))
        url = "%s&page=%d" % (base_url, page)
        try:
            d = cache_get(path, url)
        except Exception as e:
            print("list stop %s p%d: %s" % (cache_prefix, page, e), flush=True)
            return
        recs = d.get("records", [])
        for r in recs:
            oid = r.get("systemNumber")
            if oid:
                items[oid] = r
        got = d.get("info", {}).get("record_count", 0)
        if page % 20 == 0:
            print("  %s page %d (%d/%s)" % (cache_prefix, page, len(items), total), flush=True)
        if page * 100 >= got or not recs:
            return
        page += 1


def list_place(place_id):
    items = {}
    base = "%s/objects/search?id_place=%s&images_exist=true&page_size=100" % (BASE, place_id)
    head_path = os.path.join(RAW_DIR, "search_%s_1.json" % place_id)
    url0 = base + "&page=1"
    d = cache_get(head_path, url0) if os.path.exists(head_path) else api_get(url0)
    total = d.get("info", {}).get("record_count", 0)
    for oid, r in enumerate([]):
        pass
    for r in (d.get("records") or []):
        oid = r.get("systemNumber")
        if oid:
            items[oid] = r
    if total <= 9500:
        page = 2
        while page * 100 <= total + 99:
            path = os.path.join(RAW_DIR, "search_%s_%d.json" % (place_id, page))
            try:
                d = cache_get(path, base + "&page=%d" % page)
            except Exception as e:
                print("list stop %s p%d: %s" % (place_id, page, e), flush=True)
                break
            recs = d.get("records", [])
            for r in recs:
                oid = r.get("systemNumber")
                if oid:
                    items[oid] = r
            if not recs:
                break
            page += 1
    else:
        # ES deep-pagination cap (~10k): split by year_made buckets
        for lo, hi in YEAR_BUCKETS:
            prefix = "search_%s_%d_%d" % (place_id, lo, hi)
            sub_url = "%s&year_made_from=%d&year_made_to=%d" % (base, lo, hi)
            try:
                d1 = api_get(sub_url + "&page=1")
            except Exception as e:
                print("bucket %d-%d ERR %s" % (lo, hi, e), flush=True)
                continue
            sub_total = d1.get("info", {}).get("record_count", 0)
            for r in (d1.get("records") or []):
                oid = r.get("systemNumber")
                if oid:
                    items[oid] = r
            if sub_total > 100:
                d1["info"] = {"record_count": sub_total}
                json.dump(d1, open(os.path.join(RAW_DIR, "%s_1.json" % prefix), "w", encoding="utf-8"), ensure_ascii=False)
                list_pages(items, sub_url, prefix, sub_total)
            print("  bucket %d-%d -> %d" % (lo, hi, sub_total), flush=True)
    return items


def parse_detail(rec, srec):
    oid = rec.get("systemNumber", "")
    titles = rec.get("titles") or []
    name = (titles[0].get("title") if titles and titles[0].get("title") else "") \
        or (srec.get("_primaryTitle") or "") or rec.get("objectType") or "Untitled"
    dates = rec.get("productionDates") or []
    era_bits = []
    begin = end = None
    for dd in dates:
        d0 = dd.get("date") or {}
        t = (d0.get("text") or "").strip()
        if t:
            era_bits.append(t)
        if isinstance(d0.get("earliest"), int):
            begin = d0["earliest"] if begin is None else min(begin, d0["earliest"])
        if isinstance(d0.get("latest"), int):
            end = d0["latest"] if end is None else max(end, d0["latest"])
    if not era_bits and srec.get("_primaryDate"):
        era_bits.append(srec["_primaryDate"])
    styles = " ".join(s.get("text", "") for s in (rec.get("styles") or []))
    period_lbl = " ".join(era_bits)
    dyn, _ = map_dynasty(period_lbl, styles, name, begin=begin, end=end)
    year_range = [begin, end] if begin is not None and end is not None else None

    cat_txt = " ".join(c.get("text", "") for c in (rec.get("categories") or []))
    obj_type = rec.get("objectType") or srec.get("objectType") or ""
    cat = None
    low = (cat_txt + " " + obj_type).lower()
    for key, zh in CAT_MAP.items():
        if key in low:
            cat = zh
            break
    if not cat:
        cat = map_category(cat_txt or obj_type) or "杂器"

    mats = "; ".join(m.get("text", "") for m in (rec.get("materials") or []) if m.get("text")) or None
    dims = rec.get("dimensionsNote") or None
    if not dims:
        bits = []
        for d0 in (rec.get("dimensions") or [])[:4]:
            if d0.get("value") and d0.get("unit"):
                bits.append("%s %s %s" % (d0.get("dimension", ""), d0["value"], d0["unit"]))
        dims = "; ".join(bits) or None

    desc = rec.get("summaryDescription") or rec.get("briefDescription") or ""
    if isinstance(desc, list):
        desc = " ".join(d.get("text", "") for d in desc if isinstance(d, dict))
    desc = (desc or "").strip()
    if len(desc) >= 20:
        summary = desc[:300]
    else:
        summary = "维多利亚与艾尔伯特博物馆藏中国文物：%s，%s%s。藏品号 %s。" % (
            name, (period_lbl + "，") if period_lbl else "", obj_type,
            rec.get("accessionNumber") or srec.get("accessionNumber") or "-")
        if mats:
            summary += "材质：%s。" % mats

    imgs = []
    for imgid in (rec.get("images") or [])[:3]:
        imgs.append({
            "url": "https://framemark.vam.ac.uk/collections/%s/full/!800,800/0/default.jpg" % imgid,
            "license": "V&A Open Access API",
            "credit": "© Victoria and Albert Museum, London",
        })
    return name, dyn, year_range, cat, mats, dims, summary, imgs


def worker(q, sleep):
    while True:
        item = q.get()
        if item is None:
            return
        oid, srec = item
        out = os.path.join(RE_DIR, "VA-%s.json" % oid)
        try:
            with _lock:
                if os.path.exists(out):
                    _stats["skip"] += 1
                    continue
            rec = cache_get(os.path.join(RAW_DIR, "detail_%s.json" % oid),
                            "%s/museumobject/%s" % (BASE, oid))
            if isinstance(rec, dict) and "record" in rec and "systemNumber" not in rec:
                rec = rec["record"]
            name, dyn, yr, cat, mats, dims, summary, imgs = parse_detail(rec, srec)
            if not imgs:
                _stats["noimg"] += 1
                if _stats["noimg"] % 50 == 0:
                    print("noimg=%d" % _stats["noimg"], flush=True)
                continue
            relic = {
                "relic_id": "VA-" + oid,
                "name": name,
                "aliases": [],
                "dynasty": dyn,
                "year_range": yr,
                "category": cat,
                "material": mats,
                "dimensions": dims,
                "excavated_from": None,
                "summary": summary,
                "history": None,
                "interpretation": None,
                "collection": {
                    "museum": "维多利亚与艾尔伯特博物馆",
                    "region": "欧洲",
                    "inventory_no": rec.get("accessionNumber") or srec.get("accessionNumber"),
                },
                "images": imgs,
                "source_url": "https://collections.vam.ac.uk/item/%s" % oid,
                "license": "V&A Open Access API",
                "tags": [],
                "related": [],
                "raw_ref": None,
                "needs_review": dyn == "不详",
                "fetched_at": time.strftime("%Y-%m-%d"),
                "updated_at": time.strftime("%Y-%m-%d"),
            }
            with _lock:
                open(out, "w", encoding="utf-8").write(json.dumps(relic, ensure_ascii=False, indent=1))
                _stats["ok"] += 1
                if _stats["ok"] % 100 == 0:
                    print("progress ok=%d skip=%d noimg=%d err=%d" % (
                        _stats["ok"], _stats["skip"], _stats["noimg"], _stats["err"]), flush=True)
            time.sleep(sleep)
        except Exception as e:
            with _lock:
                _stats["err"] += 1
                if _stats["err"] <= 5:
                    print("ERR %s: %s" % (oid, e), flush=True)
        finally:
            q.task_done()


def main():
    args = sys.argv[1:]
    limit = int(args[args.index("--limit") + 1]) if "--limit" in args else 0
    sleep = float(args[args.index("--sleep") + 1]) if "--sleep" in args else 0.25
    workers_n = int(args[args.index("--workers") + 1]) if "--workers" in args else 4
    os.makedirs(RAW_DIR, exist_ok=True)

    all_items = {}
    for pid in PLACE_IDS:
        got = list_place(pid)
        print("place %s -> %d" % (pid, len(got)), flush=True)
        all_items.update(got)
    print("unique objects:", len(all_items), flush=True)

    q = Queue()
    n = 0
    for oid, srec in sorted(all_items.items()):
        if limit and n >= limit + _stats["skip"]:
            break
        q.put((oid, srec))
        n += 1
    threads = []
    for _ in range(workers_n):
        t = threading.Thread(target=worker, args=(q, sleep), daemon=True)
        t.start()
        threads.append(t)
    q.join()
    for _ in threads:
        q.put(None)
    print("DONE ok=%d skip=%d noimg=%d err=%d" % (_stats["ok"], _stats["skip"], _stats["noimg"], _stats["err"]))


if __name__ == "__main__":
    main()
