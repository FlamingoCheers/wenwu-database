"""One-off: fix NPM century-misparsed year_range (e.g. [11,12] from 西元11至12世紀).

Converts to real years, then re-derives dynasty only when the current dynasty's
own coarse range does NOT overlap the corrected range (never worsens).
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from collectors import dynasty_util as du

ROOT = Path(__file__).resolve().parent.parent

RANGES = {k: (lo, hi) for k, lo, hi in du.COARSE_RANGES}
RANGES.update({
    "春秋": (-770, -476), "战国": (-475, -221), "三国": (220, 280),
    "近代": (1912, 1949),
})
ALIAS = {"宋": "宋", "东周": "东周"}


def overlaps(cur, lo, hi):
    r = RANGES.get(cur)
    if r is None:
        return False
    a, b = r
    return a <= hi and lo <= b


def main():
    fixed_year, fixed_dyn, kept = 0, 0, 0
    before_dyn = {}
    for f in sorted((ROOT / "data" / "relics").glob("NPM-*.json")):
        r = json.loads(f.read_text(encoding="utf-8"))
        yr = r.get("year_range")
        if not (isinstance(yr, list) and len(yr) == 2
                and all(isinstance(x, int) for x in yr)
                and 0 < yr[0] <= yr[1] <= 20):
            continue
        cur = r.get("dynasty")
        before_dyn[cur] = before_dyn.get(cur, 0) + 1
        a, b = yr
        begin, end = (a - 1) * 100 + 1, b * 100
        r["year_range"] = [begin, end]
        fixed_year += 1
        new_dyn, conf = du.map_dynasty(begin=begin, end=end)
        if new_dyn != "不详" and not overlaps(cur, begin, end):
            r["dynasty"] = new_dyn
            r["dynasty_confidence"] = conf
            fixed_dyn += 1
        else:
            kept += 1
        f.write_text(json.dumps(r, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"year_range fixed: {fixed_year}")
    print(f"dynasty overwritten: {fixed_dyn}, kept (overlap): {kept}")
    print("before dynasty distribution:", json.dumps(before_dyn, ensure_ascii=False))
    after = {}
    for f in sorted((ROOT / "data" / "relics").glob("NPM-*.json")):
        pass
    # recount 汉 among the fixed set is implicit; validate separately


if __name__ == "__main__":
    main()
