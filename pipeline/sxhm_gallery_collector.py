# -*- coding: utf-8 -*-
"""SXHM gallery highlights collector.

Fetches /collections/detail/{oid}.html pages (server-rendered), extracts
name/era/intro, writes data/relics/SXHM-J{oid:06d}.json. Politeness: 2s sleep,
single-threaded, ~30 requests total. Cache: raw/sxhm/detail/{oid}.html
"""
import json, pathlib, re, sys, time, urllib.request

ROOT = pathlib.Path(".")
RAW = ROOT / "raw/sxhm/detail"
RAW.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
TODAY = "2026-09-22"

sys.path.insert(0, str(ROOT / "collectors"))
from dynasty_util import COARSE_RANGES, map_category, map_tags  # noqa: E402

DYN_FIX = {"五代": "五代十国", "史前": "新石器时代", "民国": "近代"}
LEAD_DYN = ["新石器时代", "西周", "东周", "春秋", "战国", "五代", "西汉", "东汉", "北宋",
            "南宋", "西夏", "商", "周", "秦", "汉", "三国", "晋", "南北朝", "北魏", "隋",
            "唐", "辽", "宋", "金", "元", "明", "清", "民国", "近代"]
FOREIGN_RE = re.compile(r"日本|朝鲜|宽永|波斯|萨珊|东罗马|犍陀|喀什")


def dyn_range(dyn):
    for k, lo, hi in COARSE_RANGES:
        if k == dyn or (dyn and len(k) >= 2 and dyn.startswith(k)):
            return [lo, hi]
    return None


def collect_ids():
    ids = set()
    for fn in ["sxhm_collection_rendered.html", "sxhm_result.html"]:
        p = pathlib.Path(rf"C:\Users\ADMINI~1\AppData\Local\Temp\opencode\{fn}")
        if p.exists():
            ids |= set(re.findall(r"/collections/detail/(\d+)\.html", p.read_text(encoding="utf-8")))
    return sorted(ids, key=int)


def fetch(oid):
    dst = RAW / f"{oid}.html"
    if dst.exists():
        return dst.read_text(encoding="utf-8")
    req = urllib.request.Request(f"https://www.sxhm.com/collections/detail/{oid}.html", headers=UA)
    t = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")
    dst.write_text(t, encoding="utf-8")
    time.sleep(2)
    return t


def parse(t, oid):
    m = re.search(r'<div class="tit">\s*<div class="t">\s*(.*?)</div>', t, re.S)
    name = re.sub(r"<[^>]+>|\s+", "", m.group(1)) if m else ""
    era = ""
    m = re.search(r"时期：([^<]+)<", t)
    if m:
        era = m.group(1).strip()
    if not era:
        for k in LEAD_DYN:
            if name.startswith(k):
                era = k
                break
    intro = ""
    m = re.search(r'藏品介绍</div>\s*<div class="c">\s*<div class="scroll-mod">\s*<div class="p">(.*?)</div>', t, re.S)
    if m:
        intro = re.sub(r"<[^>]+>", "", m.group(1)).strip()
    if not intro:
        m = re.search(r'<meta name="description" content="([^"]+)"', t)
        if m:
            intro = m.group(1).strip()
    if not era:
        for k in LEAD_DYN:
            if (len(k) >= 2 and k in intro[:200]) or f"{k}代" in intro[:200]:
                era = k
                break
    return name, era, intro


def main(apply):
    ids = collect_ids()
    print("ids:", len(ids))
    built = skipped = 0
    for oid in ids:
        rid = f"SXHM-J{int(oid):06d}"
        out = ROOT / f"data/relics/{rid}.json"
        if out.exists():
            skipped += 1
            continue
        t = fetch(oid)
        name, era, intro = parse(t, oid)
        if not name or FOREIGN_RE.search(name):
            print(f"SKIP {oid}: {'foreign' if name else 'no name'} | {name}")
            continue
        if len(intro) < 20:
            print(f"SKIP {oid}: thin intro ({len(intro)}) | {name}")
            continue
        dyn = DYN_FIX.get(era, era) or "不详"
        yr = dyn_range(dyn)
        rec = {
            "relic_id": rid,
            "name": name,
            "aliases": [],
            "dynasty": dyn,
            "year_range": yr,
            "category": map_category(name),
            "material": "",
            "dimensions": "",
            "excavated_from": "",
            "collection": {
                "museum": "陕西历史博物馆",
                "region": "中国大陆",
                "inventory_no": oid,
            },
            "summary": (intro[:300] or f"{name}，{era}。陕西历史博物馆馆藏精品。") ,
            "history": intro,
            "interpretation": [],
            "images": [],
            "source_url": f"https://www.sxhm.com/collections/detail/{oid}.html",
            "license": "©陕西历史博物馆",
            "tags": map_tags(name)[:5],
            "related": [],
            "raw_ref": f"raw/sxhm/detail/{oid}.html",
            "needs_review": False,
            "fetched_at": TODAY,
        }
        print(f"ADD {rid} | {dyn} | {name} | intro {len(intro)}")
        if apply:
            out.write_text(json.dumps(rec, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        built += 1
    print(f"built={built} skipped={skipped} apply={apply}")


if __name__ == "__main__":
    main("--apply" in sys.argv)
