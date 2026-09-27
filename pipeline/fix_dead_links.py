# -*- coding: utf-8 -*-
"""清理失效链接（2026-09-27 复核）。

1) NMC 4 件：图片链接实测 404（页面链接 200 正常，仅图失效）
   —— © 馆按合规立场只存信息与跳转链接，清空 images，保留 source_url。
2) NPM 2 件：source_url 的 dep 字母与藏品类别不符（dep 迁移遗留）
   —— 按该类别在全库中的 dep 众数修正：书画 -> P，青铜器 -> U。

用法: python pipeline/fix_dead_links.py [--apply]
"""
import json, os, io, sys, re
from datetime import date

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RD = os.path.join(ROOT, "data", "relics")
TODAY = str(date.today())
APPLY = "--apply" in sys.argv

DEAD_IMG = ["NMC-24787", "NMC-27712", "NMC-27722", "NMC-27745"]
DEP_FIX = {"NPM-5124": "P", "NPM-24475": "U"}   # 书画->P，青铜器->U

for rid in DEAD_IMG:
    p = os.path.join(RD, rid + ".json")
    r = json.load(open(p, encoding="utf-8"))
    old = [(i.get("url") or "")[-28:] for i in (r.get("images") or [])]
    print("清图 %-12s %-26s 移除 %d 张: %s" % (rid, (r.get("name") or "")[:24], len(old), old))
    if APPLY:
        r["images"] = []
        r["updated_at"] = TODAY
        with open(p, "w", encoding="utf-8") as f:
            json.dump(r, f, ensure_ascii=False, indent=1)
            f.write("\n")

for rid, dep in DEP_FIX.items():
    p = os.path.join(RD, rid + ".json")
    r = json.load(open(p, encoding="utf-8"))
    u = r.get("source_url") or ""
    new = re.sub(r"([?&]dep=)[A-Za-z]", r"\g<1>" + dep, u, count=1)
    print("dep 修正 %-11s %-10s %s -> %s" % (rid, r.get("category"), u, new))
    if APPLY:
        r["source_url"] = new
        r["updated_at"] = TODAY
        with open(p, "w", encoding="utf-8") as f:
            json.dump(r, f, ensure_ascii=False, indent=1)
            f.write("\n")

print("\n模式:", "APPLY" if APPLY else "DRY-RUN")
