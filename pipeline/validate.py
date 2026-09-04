import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RELICS_DIR = ROOT / "data" / "relics"
REPORT = ROOT / "raw" / "_validation_report.json"

REQUIRED = ["relic_id", "name", "dynasty", "category", "collection", "source_url", "license", "fetched_at"]

def load_vocab():
    vocab_dir = ROOT / "data" / "vocab"
    dynasties = {d["key"] for d in json.loads((vocab_dir / "dynasties.json").read_text(encoding="utf-8"))["dynasties"]}
    categories = {c["key"] for c in json.loads((vocab_dir / "categories.json").read_text(encoding="utf-8"))["categories"]}
    regions = set(json.loads((vocab_dir / "regions.json").read_text(encoding="utf-8"))["regions"])
    return dynasties, categories, regions

def validate(path, dynasties, categories, regions):
    errors = []
    try:
        r = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"JSON 解析失败: {exc}"], None
    for field in REQUIRED:
        if field not in r or r[field] in ("", None):
            errors.append(f"缺少必填字段 {field}")
    if r.get("category") not in categories:
        errors.append(f"category 不在受控词表: {r.get('category')}")
    if r.get("dynasty") not in dynasties:
        errors.append(f"dynasty 不在受控词表: {r.get('dynasty')}")
    col = r.get("collection", {})
    if col.get("region") not in regions:
        errors.append(f"region 不在受控词表: {col.get('region')}")
    if not col.get("museum"):
        errors.append("collection.museum 为空")
    for i, img in enumerate(r.get("images", [])):
        if not img.get("url"):
            errors.append(f"images[{i}] 缺 url")
        if not img.get("license") or not img.get("credit"):
            errors.append(f"images[{i}] 缺 license/credit（来源标注是硬要求）")
    if not r.get("images"):
        errors.append("无图片")
    if r.get("year_range") and len(r["year_range"]) != 2:
        errors.append("year_range 长度异常")
    return errors, r

def main():
    dynasties, categories, regions = load_vocab()
    files = sorted(RELICS_DIR.glob("*.json"))
    bad = {}
    no_image = 0
    review = 0
    dyn_counter = Counter()
    cat_counter = Counter()
    museum_counter = Counter()
    for path in files:
        errors, r = validate(path, dynasties, categories, regions)
        if errors:
            bad[path.name] = errors
            continue
        if r is None:
            continue
        if not r.get("images"):
            no_image += 1
        if r.get("needs_review"):
            review += 1
        dyn_counter[r.get("dynasty", "?")] += 1
        cat_counter[r.get("category", "?")] += 1
        museum_counter[r.get("collection", {}).get("museum", "?")] += 1

    report = {
        "total": len(files),
        "valid": len(files) - len(bad),
        "invalid": len(bad),
        "needs_review": review,
        "by_dynasty": dict(dyn_counter.most_common()),
        "by_category": dict(cat_counter.most_common()),
        "by_museum": dict(museum_counter.most_common()),
        "errors": bad,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"总计 {report['total']}  合格 {report['valid']}  不合格 {report['invalid']}  待人工复核 {review}")
    if bad:
        sample = list(bad.items())[:10]
        for name, errs in sample:
            print(f"  {name}: {'; '.join(errs)}")
        print(f"  ...完整报告见 {REPORT}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
