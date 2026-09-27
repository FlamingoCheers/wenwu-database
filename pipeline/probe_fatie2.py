# -*- coding: utf-8 -*-
"""探查：各类法帖名称样例 + 一条法帖完整字段 + NPM 图册全量核对（只读）。"""
import json, glob, os, re, io, sys
from collections import Counter, defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RD = os.path.join(ROOT, "data", "relics")

by_kind = defaultdict(list)
sample_full = None
tuce_npm = []
for p in glob.glob(os.path.join(RD, "*.json")):
    try:
        r = json.load(open(p, encoding="utf-8"))
    except Exception:
        continue
    n = r.get("name") or ""
    if "法帖" in n:
        m = re.match(r"^(.*?法帖)", n)
        k = m.group(1) if m else "?"
        by_kind[k].append(r)
        if k.startswith("三希堂") and sample_full is None:
            sample_full = r
    if ("圖冊" in n or "画册" in n or "畫冊" in n) and (r.get("relic_id") or "").startswith("NPM"):
        tuce_npm.append(r)

print("=== 各类法帖名称样例（每类 3 条） ===")
for k in sorted(by_kind, key=lambda x: -len(by_kind[x])):
    print("\n[%s] %d 条" % (k, len(by_kind[k])))
    for r in by_kind[k][:3]:
        print("    %-12s dyn=%-4s yr=%-16s | %s" % (
            r.get("relic_id"), r.get("dynasty"), r.get("year_range"),
            (r.get("name") or "")[:52]))

print("\n=== 一条三希堂法帖的完整字段 ===")
print(json.dumps(sample_full, ensure_ascii=False, indent=1)[:1600])

print("\n=== NPM 图册 %d 条（核对画家时代） ===" % len(tuce_npm))
for r in sorted(tuce_npm, key=lambda x: x.get("relic_id")):
    n = r.get("name") or ""
    m = re.search(r"冊\s*([唐宋元明清]|五代|北宋|南宋)?", n)
    print("  %-12s dyn=%-6s yr=%-16s | %s" % (
        r.get("relic_id"), r.get("dynasty"), r.get("year_range"), n[:50]))
