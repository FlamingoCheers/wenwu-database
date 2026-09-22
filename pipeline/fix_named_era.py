# -*- coding: utf-8 -*-
"""Apply user-named fixes from the 2026-09-22 review (dry-run by default).

Usage: python pipeline/fix_named_era.py [--apply]
"""
import glob, json, pathlib, sys

FIXES = [
    # id, dynasty, year_range, category, reason
    ("NMC-23972", "近代", [1840, 1911], "历史影像", "用户:晚清照片 夏季露天的私塾课堂"),
    ("NPM-14616", "近代", [1912, 1949], "历史影像", "用户:历代名绘册为书册扫描件算照片,官网无年代写近代"),
    ("NPM-17828", "宋", [960, 1644], None, "用户:仿良渚蚩尤玉环为宋至明仿古品,跨代取起始朝代"),
    ("NMC-24227", "近代", [1840, 1949], "历史影像", "用户:近代照片 送殡队伍中的僧众"),
    ("NMC-26318", "南宋", [1127, 1279], None, "用户:孙子兵法南宋刊本"),
    ("NPM-17281", "宋", [960, 1279], None, "用户:快雪堂法帖归宋(春秋帖标题误判春秋)"),
    ("NPM-26368", "宋", [960, 1279], None, "用户:快雪堂帖归宋(春秋帖标题误判春秋)"),
    ("NMC-24411", "近代", [1840, 1911], None, "用户:枭首示众图为晚清照片"),
    ("NMC-25367", "唐", [618, 907], None, "用户:米继芬墓志拓片为唐代"),
    ("AIC-192727", "商", [-1300, -1000], None, "用户:Oracle Bones 原页13-11BCE误登记为公元年,实为商"),
    ("MET-72639", "清", [1644, 1911], None, "用户:Figure in a Landscape=清张风行吟图轴"),
    ("NPM-47716", "元", [1271, 1368], None, "用户:伊斯兰铜回文钵应为元代"),
]

def main(apply):
    for rid, dyn, yr, cat, why in FIXES:
        p = pathlib.Path(f"data/relics/{rid}.json")
        if not p.exists():
            print(f"MISS  {rid} (file gone)")
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        old = (d.get("dynasty"), d.get("year_range"), d.get("category"))
        print(f"{'SET' if apply else 'DRY'} {rid}: {old} -> ({dyn},{yr},{cat or d.get('category')}) | {why}")
        if not apply:
            continue
        d["dynasty"] = dyn
        d["year_range"] = yr
        if cat:
            d["category"] = cat
        d["updated_at"] = "2026-09-22"
        p.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    if apply:
        print("applied", len(FIXES))

if __name__ == "__main__":
    main("--apply" in sys.argv)
