import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RELICS_DIR = ROOT / "data" / "relics"
REPORT = ROOT / "raw" / "_dedupe_report.json"


def norm_name(name):
    return re.sub(r"[\s,.;:·、''\"\"()（）\-]+", "", (name or "").lower())


def fingerprint(relic):
    col = relic.get("collection") or {}
    museum = col.get("museum") if isinstance(col, dict) else str(col)
    inv = (col.get("inventory_no") or "") if isinstance(col, dict) else ""
    return f"{museum}|{inv.strip().lower()}"


def name_fingerprint(relic):
    col = relic.get("collection") or {}
    museum = col.get("museum") if isinstance(col, dict) else str(col)
    return f"{museum}|{norm_name(relic.get('name'))}"


def year_overlap(a, b, slack=60):
    ya, yb = relic_year(a), relic_year(b)
    if ya is None or yb is None:
        return False
    return not (ya[1] + slack < yb[0] or yb[1] + slack < ya[0])


def relic_year(relic):
    yr = relic.get("year_range")
    if isinstance(yr, dict):
        yr = [yr.get("begin"), yr.get("end")]
    if not yr or len(yr) != 2 or yr[0] is None or yr[1] is None:
        return None
    return yr


def main():
    ap = argparse.ArgumentParser(description="去重指纹检查：馆内馆藏号重复 + 同名疑重")
    ap.add_argument("--apply", action="store_true", help="删除同馆同馆藏号的重复文件（保留 relic_id 最小者）")
    args = ap.parse_args()

    relics = {}
    for path in sorted(RELICS_DIR.glob("*.json")):
        try:
            relics[path] = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            print(f"解析失败 {path.name}: {exc}")

    exact_groups = {}
    name_groups = {}
    for path, relic in relics.items():
        exact_groups.setdefault(fingerprint(relic), []).append(path)
        if relic.get("name"):
            name_groups.setdefault(name_fingerprint(relic), []).append(path)

    dup_inv = []
    for fp, paths in exact_groups.items():
        if len(paths) > 1:
            keep = min(paths, key=lambda p: p.name)
            dup_inv.append({
                "fingerprint": fp,
                "keep": keep.name,
                "duplicates": sorted(p.name for p in paths if p is not keep),
            })

    sus_name = []
    for fp, paths in name_groups.items():
        if len(paths) > 1:
            pairs = []
            for i, a in enumerate(paths):
                for b in paths[i + 1:]:
                    if year_overlap(relics[a], relics[b]):
                        pairs.append(sorted([a.name, b.name]))
            if pairs:
                sus_name.append({"name_fp": fp, "pairs": pairs})

    report = {
        "total_files": len(relics),
        "exact_inventory_duplicates": dup_inv,
        "same_name_overlap_year_suspects": sus_name,
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"文件总数 {len(relics)}  同馆同馆藏号组 {len(dup_inv)}  同名同年疑重组 {len(sus_name)}")
    for d in dup_inv[:20]:
        print(f"  [馆藏号重复] {d['fingerprint']}  保留 {d['keep']}  删 {d['duplicates']}")

    if args.apply and dup_inv:
        removed = 0
        for d in dup_inv:
            for name in d["duplicates"]:
                (RELICS_DIR / name).unlink()
                removed += 1
        print(f"已删除重复文件 {removed} 个")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
