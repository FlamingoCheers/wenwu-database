# -*- coding: utf-8 -*-
"""法帖重断代：按「刻帖/拓本的时代」而非「书法家的时代」。

用户规则（2026-09-27 复核）：所有的法帖按照法帖的时代写朝代，不按照书法家的时代写朝代。
三希堂法帖 -> 清（乾隆十二年 1747 始刻，十五年 1750 成）。

用法: python pipeline/fix_fatie_dynasty.py          # dry-run
      python pipeline/fix_fatie_dynasty.py --apply
"""
import json, os, re, io, sys, glob
from datetime import date

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RD = os.path.join(ROOT, "data", "relics")
TODAY = str(date.today())
APPLY = "--apply" in sys.argv

VOCAB = json.load(open(os.path.join(ROOT, "data", "vocab", "dynasties.json"), encoding="utf-8"))
RANGE = {d["key"]: d.get("range") for d in VOCAB["dynasties"]}

# (名称关键字, 朝代, 精确年份区间或None) —— 按顺序匹配，先命中先应用
RULES = [
    ("三希堂", "清", [1747, 1750]),      # 御刻三希堂石渠宝笈法帖：乾隆十二年始刻，十五年成
    ("墨妙軒", "清", None),              # 乾隆御刻墨妙轩法帖
    ("垂裕閣", "清", None),              # 清嘉庆间刻
    ("平遠山房", "清", None),            # 清嘉庆间李廷敬辑刻
    ("經訓堂", "清", None),              # 清乾隆间毕沅辑刻
    ("快雪堂", "清", None),              # 明末清初冯铨辑、刘光旸刻，成于清初
    ("停雲館", "明", None),              # 明文徵明父子辑刻
    ("寶賢堂", "明", None),              # 明拓宝贤堂集古法帖
    ("至道御書", "宋", None),            # 宋拓至道御书法帖
    ("褚遂良", "宋", None),              # 宋拓褚遂良法帖
    ("淳化閣", "宋", None),              # 淳化阁帖：北宋淳化三年(992)始刻
]

changed = 0
unmatched = []
stat = {}

for p in sorted(glob.glob(os.path.join(RD, "*.json"))):
    try:
        r = json.load(open(p, encoding="utf-8"))
    except Exception:
        continue
    n = r.get("name") or ""
    if "法帖" not in n:
        continue
    hit = None
    for kw, dyn, yr in RULES:
        if kw in n:
            hit = (kw, dyn, yr)
            break
    if not hit:
        unmatched.append((r["relic_id"], n))
        continue
    kw, dyn, yr = hit
    tgt_yr = yr or RANGE.get(dyn)
    old_d, old_y = r.get("dynasty"), r.get("year_range")
    if old_d == dyn and old_y == list(tgt_yr):
        continue
    stat.setdefault("%s -> %s" % (old_d, dyn), 0)
    stat["%s -> %s" % (old_d, dyn)] += 1
    r["dynasty"] = dyn
    r["year_range"] = list(tgt_yr)
    r["dynasty_confidence"] = "inferred"
    r["updated_at"] = TODAY
    changed += 1
    if changed <= 8:
        print("  %-12s %-46s %s -> %s %s" % (
            r["relic_id"], n[:44], old_d, dyn, tgt_yr))
    if APPLY:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(r, f, ensure_ascii=False, indent=1)
            f.write("\n")

print("\n断代统计:")
for k, v in sorted(stat.items(), key=lambda kv: -kv[1]):
    print("  %-16s %d" % (k, v))
print("未匹配规则的法帖: %d" % len(unmatched))
for rid, n in unmatched[:10]:
    print("   ", rid, n[:50])
print("\n合计改动 %d 条  模式: %s" % (changed, "APPLY" if APPLY else "DRY-RUN"))
