# -*- coding: utf-8 -*-
"""抽查 HAM 重扫结果：打印 period 原文与落库后的 dynasty/year_range。"""
import json, glob, os, io, sys
from collections import Counter

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RD = os.path.join(ROOT, "data", "relics")

raw = {}
for f in glob.glob(os.path.join(ROOT, "raw", "harv", "*.json")):
    d = json.load(open(f, encoding="utf-8"))
    for r in d.get("records", []):
        raw[str(r.get("id"))] = r

SPOT = ["HAM-204866", "HAM-204882", "HAM-147442", "HAM-149541", "HAM-182445",
        "HAM-1429", "HAM-198532", "HAM-201934", "HAM-370456", "HAM-146433",
        "HAM-202913", "HAM-204639", "HAM-173147", "HAM-10916", "HAM-201303"]

print("=== 用户点名 / 关键条目抽查 ===")
for rid in SPOT:
    p = os.path.join(RD, rid + ".json")
    if not os.path.exists(p):
        print(rid, "MISSING")
        continue
    r = json.load(open(p, encoding="utf-8"))
    oid = rid.split("-", 1)[1]
    src = raw.get(oid, {})
    print("%-13s dyn=%-8s yr=%-18s conf=%-8s | period=%s" % (
        rid, r.get("dynasty"), r.get("year_range"), r.get("dynasty_confidence"),
        (src.get("period") or "-")[:46]))

print("\n=== 全库 HAM 朝代分布 ===")
c = Counter()
bad = []
for p in glob.glob(os.path.join(RD, "HAM-*.json")):
    r = json.load(open(p, encoding="utf-8"))
    c[r.get("dynasty")] += 1
    yr = r.get("year_range")
    if yr and len(yr) == 2 and yr[0] is not None and yr[0] > yr[1]:
        bad.append(r["relic_id"])
for k, v in c.most_common():
    print("  %-8s %d" % (k, v))
print("倒序年份残留: %d" % len(bad), bad[:5])

print("\n=== 年份越界检查（年份与朝代区间完全无交集）===")
V = {d["key"]: d.get("range") for d in json.load(
    open(os.path.join(ROOT, "data", "vocab", "dynasties.json"), encoding="utf-8"))["dynasties"]}
odd = []
for p in glob.glob(os.path.join(RD, "HAM-*.json")):
    r = json.load(open(p, encoding="utf-8"))
    rng = V.get(r.get("dynasty"))
    yr = r.get("year_range")
    if not rng or rng[0] is None or not yr or yr[0] is None:
        continue
    if max(yr) < rng[0] or min(yr) > rng[1]:
        odd.append((r["relic_id"], r.get("dynasty"), yr, rng))
print("越界: %d 条" % len(odd))
for x in odd[:12]:
    print("   ", x)
