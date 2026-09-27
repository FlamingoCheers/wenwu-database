# -*- coding: utf-8 -*-
"""探查：法帖种类与朝代分布、图册条目、HAM period/dated 值域（只读）。"""
import json, glob, os, re, io, sys
from collections import Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RD = os.path.join(ROOT, "data", "relics")

fatie = []
tuce = []
for p in glob.glob(os.path.join(RD, "*.json")):
    try:
        r = json.load(open(p, encoding="utf-8"))
    except Exception:
        continue
    n = r.get("name") or ""
    if "法帖" in n:
        fatie.append(r)
    if "圖冊" in n or "图册" in n or "畫冊" in n or "画册" in n:
        tuce.append(r)

print("=== 法帖 %d 条 ===" % len(fatie))
kind = Counter()
for r in fatie:
    m = re.match(r"^(.*?法帖)", r.get("name") or "")
    kind[m.group(1) if m else "?"] += 1
for k, v in kind.most_common(30):
    print("  %-30s %d" % (k, v))
print("--- 法帖当前 dynasty 分布 ---", Counter(r.get("dynasty") for r in fatie).most_common())
print("--- 法帖 year_range 样例 ---")
for r in fatie[:5]:
    print("   ", r.get("relic_id"), r.get("year_range"), "|", (r.get("name") or "")[:40])

print("\n=== 图册 %d 条 ===" % len(tuce))
mus = Counter((r.get("collection") or {}).get("museum") for r in tuce)
print("  按馆:", mus.most_common())
print("  朝代分布:", Counter(r.get("dynasty") for r in tuce).most_common())
seen = set()
for r in tuce:
    n = (r.get("name") or "")
    key = re.sub(r"[（(].*", "", n)
    if key in seen:
        continue
    seen.add(key)
    print("   ", r.get("relic_id"), "|", n[:40], "| dyn=", r.get("dynasty"),
          "| yr=", r.get("year_range"))

print("\n=== HAM period 值域（缓存） ===")
per = Counter()
dated_sample = []
for f in sorted(glob.glob(os.path.join(ROOT, "raw", "harv", "*.json"))):
    d = json.load(open(f, encoding="utf-8"))
    for r in d.get("records", []):
        per[(r.get("period") or "").strip()] += 1
        if len(dated_sample) < 25:
            dated_sample.append((r.get("id"), r.get("period"), r.get("dated")))
for k, v in per.most_common(60):
    print("  %-46s %d" % (k, v))
print("\n--- dated 样例 ---")
for x in dated_sample:
    print("   id=%s period=%r dated=%r" % x)
