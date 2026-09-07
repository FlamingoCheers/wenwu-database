import argparse
import json
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
import urllib.request
import urllib.error
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dynasty_util as du

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw" / "met"
RELICS_DIR = ROOT / "data" / "relics"
API = "https://collectionapi.metmuseum.org/public/collection/v1"
HEADERS = {"User-Agent": "wenwu-database/0.1 (open-source aggregation of open-access museum data)"}
ASIAN_ART_DEPT = 6
TODAY = date.today().isoformat()


def map_dynasty(obj):
    return du.map_dynasty(
        obj.get("objectDynasty") or "",
        begin=obj.get("objectBeginDate"),
        end=obj.get("objectEndDate"),
    )


def map_category(medium):
    return du.map_category(medium)

def map_tags(obj, category):
    text = " ".join(filter(None, [obj.get("title"), obj.get("objectName"), obj.get("medium")]))
    for tag in obj.get("tags") or []:
        text += " " + str(tag.get("name", ""))
    tags = du.map_tags(text)
    if category == "钱币":
        tags.append("货币金融")
    seen, out = set(), []
    for t in tags:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out

def http_get_json(url, retries=3):
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as exc:
            if attempt == retries - 1:
                raise
            time.sleep(2 * (attempt + 1))

def to_record(obj):
    dynasty, confidence = map_dynasty(obj)
    category = map_category(obj.get("medium"))
    begin = obj.get("objectBeginDate")
    end = obj.get("objectEndDate")
    year_range = [begin, end] if begin is not None and end is not None else [None, None]
    primary = obj.get("primaryImage") or ""
    images = []
    if primary and obj.get("isPublicDomain"):
        images.append({
            "url": primary,
            "license": "CC0",
            "credit": "The Metropolitan Museum of Art, CC0",
        })
    summary_parts = [p for p in [obj.get("objectName"), obj.get("culture"), obj.get("period")] if p]
    record = {
        "relic_id": f"MET-{obj['objectID']}",
        "name": (obj.get("title") or "").strip() or "未命名",
        "aliases": [],
        "dynasty": dynasty,
        "dynasty_confidence": confidence,
        "year_range": year_range,
        "category": category,
        "material": obj.get("medium") or "",
        "dimensions": (obj.get("dimensions") or "").strip(),
        "excavated_from": "",
        "collection": {
            "museum": "大都会艺术博物馆",
            "region": "北美洲",
            "inventory_no": obj.get("accessionNumber") or "",
        },
        "summary": "。".join(summary_parts)[:300],
        "history": "",
        "interpretation": [],
        "images": images,
        "source_url": obj.get("objectURL") or f"https://www.metmuseum.org/art/collection/search/{obj['objectID']}",
        "license": "CC0",
        "tags": map_tags(obj, category),
        "related": [],
        "raw_ref": f"raw/met/{obj['objectID']}.json",
        "needs_review": dynasty == "不详" or not images,
        "fetched_at": TODAY,
        "updated_at": TODAY,
    }
    return record

def main():
    parser = argparse.ArgumentParser(description="Met Open Access 采集器（亚洲艺术部，CC0）")
    parser.add_argument("--limit", type=int, default=0, help="本次处理对象数上限（含跳过），0=全量")
    parser.add_argument("--sleep", type=float, default=0.05, help="请求间隔秒数（每线程）")
    parser.add_argument("--workers", type=int, default=6, help="并发线程数")
    parser.add_argument("--force", action="store_true", help="覆盖已存在的记录")
    parser.add_argument("--remap", action="store_true", help="仅用本地 raw 缓存重映射已入库记录（不联网）")
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    RELICS_DIR.mkdir(parents=True, exist_ok=True)

    if args.remap:
        ok = failed = 0
        failures = []
        for out_path in sorted(RELICS_DIR.glob("MET-*.json")):
            oid = out_path.stem.removeprefix("MET-")
            raw_path = RAW_DIR / f"{oid}.json"
            try:
                if not raw_path.exists():
                    print(f"缺 raw 缓存: {raw_path.name}", flush=True)
                    failed += 1
                    continue
                obj = json.loads(raw_path.read_text(encoding="utf-8"))
                record = to_record(obj)
                if not record["images"]:
                    failed += 1
                    failures.append({"objectID": oid, "error": "no images"})
                    continue
                out_path.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
                ok += 1
            except Exception as exc:
                failed += 1
                failures.append({"objectID": oid, "error": str(exc)})
        if failures:
            (RAW_DIR / "_failures.json").write_text(json.dumps(failures, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"重映射完成: {ok}  失败 {failed}")
        return 0 if failed == 0 else 1

    listing = http_get_json(f"{API}/objects?departmentIds={ASIAN_ART_DEPT}")
    ids = listing.get("objectIDs") or []
    print(f"亚洲艺术部候选 {listing.get('total', len(ids))} 件", flush=True)

    ok = skipped = failed = 0
    failures = []
    skip_file = RAW_DIR / "_skipped.json"
    skip_set = set(json.loads(skip_file.read_text(encoding="utf-8"))) if skip_file.exists() else set()
    skip_new = []
    todo = []
    for oid in ids:
        if oid in skip_set:
            skipped += 1
            continue
        if (RELICS_DIR / f"MET-{oid}.json").exists() and not args.force:
            skipped += 1
            continue
        todo.append(oid)
    print(f"待处理 {len(todo)}  已跳过 {skipped}", flush=True)

    def work(oid):
        raw_path = RAW_DIR / f"{oid}.json"
        try:
            if raw_path.exists():
                obj = json.loads(raw_path.read_text(encoding="utf-8"))
            else:
                obj = http_get_json(f"{API}/objects/{oid}")
                raw_path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
                time.sleep(args.sleep)
            if not obj.get("isPublicDomain"):
                return ("skip", oid, None)
            cul = (obj.get("culture") or "").lower()
            if "china" not in cul:
                return ("skip", oid, None)
            record = to_record(obj)
            if not record["images"]:
                return ("skip", oid, None)
            (RELICS_DIR / f"MET-{oid}.json").write_text(
                json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
            return ("ok", oid, None)
        except Exception as exc:
            return ("fail", oid, str(exc))

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = [ex.submit(work, oid) for oid in todo]
        done_n = 0
        for fut in as_completed(futures):
            status, oid, err = fut.result()
            done_n += 1
            if status == "ok":
                ok += 1
            elif status == "skip":
                skip_new.append(oid)
                skipped += 1
            else:
                failed += 1
                failures.append({"objectID": oid, "error": err})
            if done_n % 200 == 0:
                print(f"进度 {done_n}/{len(todo)}  入库 {ok}  跳过 {skipped}  失败 {failed}", flush=True)
            if args.limit and done_n >= args.limit:
                for f2 in futures:
                    f2.cancel()
                break

    if skip_new:
        skip_set.update(skip_new)
        skip_file.write_text(json.dumps(sorted(skip_set)), encoding="utf-8")

    if failures:
        (RAW_DIR / "_failures.json").write_text(json.dumps(failures, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"完成：入库 {ok}  跳过 {skipped}  失败 {failed}")
    return 0 if failed == 0 or ok > 0 else 1

if __name__ == "__main__":
    sys.exit(main())
