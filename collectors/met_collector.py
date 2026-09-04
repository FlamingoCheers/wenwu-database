import argparse
import json
import re
import sys
import time
import urllib.request
import urllib.error
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "raw" / "met"
RELICS_DIR = ROOT / "data" / "relics"
API = "https://collectionapi.metmuseum.org/public/collection/v1"
HEADERS = {"User-Agent": "wenwu-database/0.1 (open-source aggregation of open-access museum data)"}
ASIAN_ART_DEPT = 6
TODAY = date.today().isoformat()

DYNASTY_MAP = [
    (re.compile(r"shang", re.I), "商"),
    (re.compile(r"xia\b", re.I), "夏"),
    (re.compile(r"neolithic", re.I), "新石器时代"),
    (re.compile(r"han", re.I), "汉"),
    (re.compile(r"three kingdoms", re.I), "三国"),
    (re.compile(r"six dynasties|northern and southern", re.I), "南北朝"),
    (re.compile(r"sui", re.I), "隋"),
    (re.compile(r"tang", re.I), "唐"),
    (re.compile(r"five dynasties", re.I), "五代十国"),
    (re.compile(r"liao", re.I), "辽"),
    (re.compile(r"western xia", re.I), "西夏"),
    (re.compile(r"song", re.I), "宋"),
    (re.compile(r"yuan", re.I), "元"),
    (re.compile(r"ming", re.I), "明"),
    (re.compile(r"qing", re.I), "清"),
    (re.compile(r"republic", re.I), "近代"),
]

COARSE_RANGES = [
    ("新石器时代", -10000, -2070), ("夏", -2070, -1600), ("商", -1600, -1046),
    ("西周", -1046, -771), ("东周", -771, -256), ("秦", -221, -207),
    ("汉", -202, 220), ("三国", 220, 280), ("西晋", 265, 316), ("东晋", 317, 420),
    ("南北朝", 420, 589), ("隋", 581, 618), ("唐", 618, 907), ("五代十国", 907, 979),
    ("北宋", 960, 1127), ("南宋", 1127, 1279), ("辽", 916, 1125), ("金", 1115, 1234),
    ("西夏", 1038, 1227), ("元", 1271, 1368), ("明", 1368, 1644), ("清", 1644, 1911),
]

DYNASTY_AMBIGUOUS = {
    "jin": lambda b: "金" if b >= 1115 else "西晋",
    "zhou": lambda b: "西周" if b < -771 else "东周",
    "song": lambda b: "南宋" if b >= 1127 else "北宋",
}

CATEGORY_ALIASES = []

def load_category_aliases():
    vocab = json.loads((ROOT / "data" / "vocab" / "categories.json").read_text(encoding="utf-8"))
    for cat in vocab["categories"]:
        for alias in cat["aliases"]:
            CATEGORY_ALIASES.append((alias.strip().lower(), cat["key"]))
    CATEGORY_ALIASES.sort(key=lambda x: -len(x[0]))

def map_category(medium):
    if not medium:
        return "杂器"
    m = medium.lower()
    for alias, key in CATEGORY_ALIASES:
        if alias in m:
            return key
    return "杂器"

def map_dynasty(obj):
    dyn_text = obj.get("objectDynasty") or ""
    begin = obj.get("objectBeginDate")
    for pattern, key in DYNASTY_MAP:
        if pattern.search(dyn_text):
            return key, "high"
    for token, resolver in DYNASTY_AMBIGUOUS.items():
        if re.search(rf"\b{token}\b", dyn_text, re.I) and begin:
            return resolver(begin), "medium"
    if begin is not None and obj.get("objectEndDate") is not None:
        for key, lo, hi in COARSE_RANGES:
            if begin >= lo and obj["objectEndDate"] <= hi + 30:
                return key, "medium"
    return "不详", "low"

TAG_RULES = [
    (re.compile(r"mirror", re.I), ["铜镜", "日常生活"]),
    (re.compile(r"\bsword|dagger|blade|axe|halberd|arrowhead|armor", re.I), ["战争", "兵器"]),
    (re.compile(r"coin|currency", re.I), ["货币金融"]),
    (re.compile(r"buddha|bodhisattva|buddhist|guanyin", re.I), ["佛教", "神话宗教"]),
    (re.compile(r"daoist|laozi|immortal", re.I), ["道教", "神话宗教"]),
    (re.compile(r"funerar|tomb|mingqi|burial", re.I), ["丧葬", "明器"]),
    (re.compile(r"\bjar|bowl|dish|plate|cup|ewer|pitcher|vessel", re.I), ["食器"]),
    (re.compile(r"wine|hu\b|zun|jue\b|gu\b|you\b|he\b|gang\b", re.I), ["酒文化", "礼制"]),
    (re.compile(r"ritual|altar", re.I), ["礼制", "祭祀"]),
    (re.compile(r"comb|hairpin|belt hook", re.I), ["妆饰"]),
    (re.compile(r"seal\b|stamp", re.I), ["玺印封泥", "文字书写"]),
    (re.compile(r"snuff bottle", re.I), ["日常生活"]),
    (re.compile(r"landscape", re.I), ["山水"]),
    (re.compile(r"dragon|phoenix|qilin", re.I), ["祥瑞纹样"]),
    (re.compile(r"figurine|figure of a", re.I), ["日常生活"]),
    (re.compile(r"teapot|tea bowl|cup stand", re.I), ["茶文化"]),
    (re.compile(r"censer|incense burner", re.I), ["香文化"]),
    (re.compile(r"astronom|zodiac", re.I), ["天文历法", "生肖"]),
    (re.compile(r"horse|camel", re.I), ["动物", "出行"]),
    (re.compile(r"bird|duck|goose", re.I), ["动物"]),
    (re.compile(r"flower|peony|lotus|plum", re.I), ["植物"]),
]

def map_tags(obj, category):
    text = " ".join(filter(None, [obj.get("title"), obj.get("objectName"), obj.get("medium")]))
    for tag in obj.get("tags") or []:
        text += " " + str(tag.get("name", ""))
    tags = []
    for pattern, hits in TAG_RULES:
        if pattern.search(text):
            tags.extend(hits)
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
    parser.add_argument("--limit", type=int, default=0, help="成功入库目标数量，0=全量")
    parser.add_argument("--sleep", type=float, default=0.12, help="请求间隔秒数")
    parser.add_argument("--force", action="store_true", help="覆盖已存在的记录")
    args = parser.parse_args()

    load_category_aliases()
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    RELICS_DIR.mkdir(parents=True, exist_ok=True)

    listing = http_get_json(f"{API}/objects?departmentIds={ASIAN_ART_DEPT}")
    ids = listing.get("objectIDs") or []
    print(f"亚洲艺术部候选 {listing.get('total', len(ids))} 件", flush=True)

    ok = skipped = failed = 0
    failures = []
    skip_file = RAW_DIR / "_skipped.json"
    skip_set = set(json.loads(skip_file.read_text(encoding="utf-8"))) if skip_file.exists() else set()
    skip_new = []
    for i, oid in enumerate(ids, 1):
        if args.limit and ok >= args.limit:
            break
        out_path = RELICS_DIR / f"MET-{oid}.json"
        if out_path.exists() and not args.force:
            skipped += 1
            continue
        if oid in skip_set:
            skipped += 1
            continue
        try:
            raw_path = RAW_DIR / f"{oid}.json"
            if raw_path.exists():
                obj = json.loads(raw_path.read_text(encoding="utf-8"))
            else:
                obj = http_get_json(f"{API}/objects/{oid}")
                raw_path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
                time.sleep(args.sleep)
            if not obj.get("isPublicDomain"):
                skip_new.append(oid)
                skipped += 1
                continue
            record = to_record(obj)
            if not record["images"]:
                skip_new.append(oid)
                skipped += 1
                continue
            out_path.write_text(json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
            ok += 1
        except Exception as exc:
            failed += 1
            failures.append({"objectID": oid, "error": str(exc)})
        if i % 100 == 0:
            print(f"进度 {i}/{len(ids)}  入库 {ok}  跳过 {skipped}  失败 {failed}", flush=True)

    if skip_new:
        skip_set.update(skip_new)
        skip_file.write_text(json.dumps(sorted(skip_set)), encoding="utf-8")

    if failures:
        (RAW_DIR / "_failures.json").write_text(json.dumps(failures, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"完成：入库 {ok}  跳过 {skipped}  失败 {failed}")
    return 0 if failed == 0 or ok > 0 else 1

if __name__ == "__main__":
    sys.exit(main())
