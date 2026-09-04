import argparse
import json
import re
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dynasty_util as du

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "relics"
CACHE_DIR = ROOT / "raw" / "cle"
API = "https://openaccess-api.clevelandart.org/api/artworks/"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) wenwu-database/0.1"}
PAGE_SIZE = 1000
MUSEUM = "克利夫兰艺术博物馆"
TODAY = date.today().isoformat()


def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.load(resp)
        except Exception as exc:
            if attempt == 2:
                raise
            print(f"  retry {attempt + 1} after error: {exc}")
            time.sleep(5 * (attempt + 1))


def clean_acc(acc):
    return re.sub(r"[^\w-]", "-", str(acc))


def strip_html(text):
    return re.sub(r"<[^>]+>", "", text or "").strip()


def map_record(r):
    cultures = r.get("culture") or []
    if isinstance(cultures, str):
        cultures = [cultures]
    culture_text = ", ".join(cultures)
    begin = r.get("creation_date_earliest")
    end = r.get("creation_date_latest")
    dynasty, confidence = du.map_dynasty(
        culture_text, r.get("period") or "", r.get("collection") or "",
        begin=begin, end=end,
    )
    technique = r.get("technique") or ""
    category = du.map_category(" ".join(filter(None, [r.get("type"), technique, r.get("collection")])))
    summary = (r.get("description") or r.get("tombstone") or r.get("did_you_know") or "")
    summary = strip_html(summary)[:300]
    if not summary:
        summary = strip_html(r.get("tombstone"))
    credit = "The Cleveland Museum of Art, CC0"
    images = []
    img = r.get("images") or {}
    for size in ("web", "print"):
        u = (img.get(size) or {}).get("url")
        if u:
            images.append({"url": u, "license": "CC0", "credit": credit})
    for alt in (r.get("alternate_images") or [])[:2]:
        u = (alt.get("web") or {}).get("url")
        if u:
            images.append({"url": u, "license": "CC0", "credit": credit})
    if not images:
        return None
    name = (r.get("title") or "").strip() or "未命名"
    aliases = []
    orig = (r.get("title_in_original_language") or "").strip()
    if orig:
        aliases.append(orig)
    tags = du.map_tags(name, r.get("tombstone") or "", r.get("type") or "", technique, culture_text)
    return {
        "relic_id": f"CLE-{clean_acc(r.get('accession_number'))}",
        "name": name,
        "aliases": aliases,
        "dynasty": dynasty,
        "dynasty_confidence": confidence,
        "year_range": [begin, end] if begin is not None and end is not None else [None, None],
        "category": category,
        "material": technique,
        "dimensions": (r.get("measurements") or "").strip(),
        "excavated_from": strip_html(r.get("find_spot") or ""),
        "collection": {
            "museum": MUSEUM,
            "region": "北美洲",
            "inventory_no": r.get("accession_number") or "",
        },
        "summary": summary,
        "history": "",
        "interpretation": [],
        "images": images,
        "source_url": r.get("url") or f"https://clevelandart.org/art/{r.get('accession_number')}",
        "license": "CC0",
        "tags": tags,
        "related": [],
        "raw_ref": "",
        "needs_review": dynasty == "不详",
        "fetched_at": TODAY,
        "updated_at": TODAY,
    }


def main():
    ap = argparse.ArgumentParser(description="克利夫兰艺术博物馆 Open Access 采集器（CC0）")
    ap.add_argument("--limit", type=int, default=0, help="最多入库件数，0=全部")
    ap.add_argument("--sleep", type=float, default=1.5, help="分页请求间隔秒")
    ap.add_argument("--force", action="store_true", help="已存在也重新映射入库")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    first = fetch(f"{API}?cc0=1&has_image=1&culture=China&limit={PAGE_SIZE}&skip=0")
    total = first["info"]["total"]
    print(f"远端总数（中国文物 CC0 有图）: {total}")

    records = list(first["data"])
    for skip in range(PAGE_SIZE, total, PAGE_SIZE):
        cache = CACHE_DIR / f"page_{skip}.json"
        if cache.exists():
            records.extend(json.load(cache.open(encoding="utf-8"))["data"])
            print(f"缓存命中: {cache.name}")
        else:
            print(f"拉取 {skip}+{PAGE_SIZE} ...")
            page = fetch(f"{API}?cc0=1&has_image=1&culture=China&limit={PAGE_SIZE}&skip={skip}")
            cache.write_text(json.dumps(page, ensure_ascii=False), encoding="utf-8")
            records.extend(page["data"])
            time.sleep(args.sleep)

    written = skipped = noimg = 0
    for i, r in enumerate(records, 1):
        if args.limit and written >= args.limit:
            break
        relic = map_record(r)
        if relic is None:
            noimg += 1
            continue
        page_skip = ((i - 1) // PAGE_SIZE) * PAGE_SIZE
        relic["raw_ref"] = f"raw/cle/page_{page_skip}.json"
        out = OUT_DIR / f"{relic['relic_id']}.json"
        if out.exists() and not args.force:
            skipped += 1
            continue
        out.write_text(json.dumps(relic, ensure_ascii=False, indent=1), encoding="utf-8")
        written += 1
        if i % 500 == 0:
            print(f"进度 {i}/{len(records)}  入库 {written}  跳过 {skipped}", flush=True)

    print(f"完成: 新入库 {written} / 跳过已存在 {skipped} / 无可用图片 {noimg} / 记录总数 {len(records)}")


if __name__ == "__main__":
    main()
