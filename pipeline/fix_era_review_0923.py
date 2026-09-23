# -*- coding: utf-8 -*-
"""Era review fixes 2026-09-23 (dry-run by default).

Sections:
  A. user-named items -> exact eras
  B. NPM album leaves (唐宋名蹟/集繪 冊) -> era token after 冊
  C. SXHM 东周 coins -> 春秋/战国 by name
  D. dynasty=不详 + year_range -> derive via COARSE_RANGES overlap
  (E. material violations -> sub-agent, separate)

Usage: python pipeline/fix_era_review_0923.py [--apply] [--only A|B|C|D]
"""
import glob, json, pathlib, re, sys
from collections import Counter

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "collectors"))
from dynasty_util import COARSE_RANGES  # noqa: E402

RANGES = {k: (lo, hi) for k, lo, hi in COARSE_RANGES}
ERA = {"商": [-1600, -1046], "汉": [-202, 220], "战国": [-475, -221], "春秋": [-770, -476],
       "唐": [618, 907], "五代十国": [907, 979], "宋": [960, 1279], "元": [1271, 1368],
       "明": [1368, 1644], "清": [1644, 1911], "近代": [1912, 1949]}

# ---- A. named fixes: (substring, dynasty, exact_name_or_None, extra) ----
NAMED = [
    ("龙首玉觿", "商", None, None), ("龙纹玉璧", "汉", None, None),
    ("水晶镂雕三螭花果纹瓶", "清", None, None), ("玉荷花螃蟹纹砚", "清", None, None),
    ("玉梳", "商", "玉梳", None), ("青花莲池鸳鸯纹碗", "明", None, None),
    ("青花仙人图筒式炉", "明", None, None), ("五彩张天师驱五毒图盘", "明", None, None),
    ("鱼子绿釉菊瓣式茶壶", "清", None, None), ("仿汝釉弦纹尊", "清", None, None),
    ("空竹", "清", None, "历史影像"), ("青花缠枝莲花纹盘", "明", None, None),
    ("彩绘木雕观音菩萨头像", "宋", None, None), ("粉彩凤穿花纹双联瓶", "清", None, None),
    ("玛瑙梅瓣式碗", "宋", None, None), ("玉镂空喜字簪", "清", None, None),
    ("仿宋官窑兽耳瓶", "清", None, None), ("斗彩婴戏纹杯", "明", None, None),
    ("青花婴戏纹碗", "明", None, "all"), ("青花阿拉伯文折沿盘", "明", None, None),
    ("青花八仙人物纹葫芦瓶", "明", None, None), ("茶叶末釉贯耳壶", "清", None, None),
    ("龙形玉佩", "宋", None, None), ("玉凤纹方盒", "明", None, None),
    ("玉镂雕牡丹纹花熏", "清", None, None), ("宣德霁蓝盘", "明", None, None),
    ("骠国乐", "明", None, None), ("淳于棼", "明", None, None),
    ("莺莺传", "明", None, None), ("风炉、茶鍑", "五代十国", None, None),
    ("茶瓶", "五代十国", "茶瓶", None), ("茶臼", "五代十国", "茶臼", None),
    ("渣斗", "五代十国", "渣斗", None), ("北宋铜钱、铁钱", "宋", None, None),
    ("定窑划花萱草葵瓣口碗", "宋", None, None), ("宝庆四明志", "宋", None, None),
    ("西厢记诸宫调", "明", None, None), ("明瓒诗后题卷", "宋", None, None),
    ("建阳窑褐釉碗", "宋", None, None), ("飞天", "宋", "飞天", None),
]

TRAD = str.maketrans("蹟繢畫錦繪東漢戰國晉遼寶紀", "迹绩画锦绘东汉战国晋辽宝纪")
LEAD = sorted(["新石器时代", "五代十国", "南北朝", "北魏", "西夏", "西周", "东周", "春秋", "战国",
               "三国", "西汉", "东汉", "西晋", "东晋", "北宋", "南宋", "民国", "近代", "史前",
               "商", "周", "秦", "汉", "隋", "唐", "五代", "辽", "宋", "金", "元", "明", "清"],
              key=len, reverse=True)


def load_all():
    for f in glob.glob("data/relics/*.json"):
        p = pathlib.Path(f)
        yield p, json.loads(p.read_text(encoding="utf-8"))


def sec_a(apply):
    done = Counter()
    for k, dyn, exact, extra in NAMED:
        cands = []
        for p, d in load_all():
            name = d.get("name") or ""
            ok = (name == exact) if exact else (k in name)
            if ok:
                cands.append((p, d))
        if not cands:
            print(f"A-MISS {k}")
            continue
        for p, d in cands:
            if d.get("dynasty") == dyn and not extra:
                done[k] += 0
                continue
            yr = ERA.get(dyn)
            print(f"A {'SET' if apply else 'DRY'} {p.stem} [{d.get('dynasty')}]->[{dyn}] {name}")
            if apply:
                d["dynasty"], d["year_range"] = dyn, list(yr)
                if extra == "历史影像":
                    d["category"] = "历史影像"
                d["updated_at"] = "2026-09-23"
                p.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            done[k] += 1
    print("A done:", sum(done.values()), "items")


def sec_b(apply):
    n = 0
    for p, d in load_all():
        name = d.get("name") or ""
        if "　冊　" not in name and " 冊 " not in name:
            continue
        m = re.search(r"[　\s]冊[　\s](新石器時代|商|西周|東周|春秋|戰國|秦|漢|三國|西晉|東晉|南北朝|北魏|隋|唐|五代|北宋|南宋|遼|宋|金|元|明|清|民國)", name)
        if not m:
            continue
        dyn = m.group(1).translate(TRAD)
        dyn = {"五代": "五代十国", "東周": "东周", "戰國": "战国", "漢": "汉"}.get(dyn, dyn)
        if d.get("dynasty") == dyn:
            continue
        yr = ERA.get(dyn) or ([RANGES[dyn][0], RANGES[dyn][1]] if dyn in RANGES else None)
        print(f"B {'SET' if apply else 'DRY'} {p.stem} [{d.get('dynasty')}]->[{dyn}] {name[:34]}")
        if apply:
            d["dynasty"], d["year_range"] = dyn, list(yr) if yr else d.get("year_range")
            d["updated_at"] = "2026-09-23"
            p.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        n += 1
    print("B done:", n)


def sec_c(apply):
    n = 0
    for p, d in load_all():
        if not p.stem.startswith("SXHM") or d.get("dynasty") != "东周" or d.get("category") != "钱币":
            continue
        name = d.get("name") or ""
        dyn = "战国" if "战国" in name else ("春秋" if "春秋" in name else None)
        if not dyn:
            print(f"C-KEEP {p.stem} {name[:30]}")
            continue
        if d.get("dynasty") == dyn:
            continue
        print(f"C {'SET' if apply else 'DRY'} {p.stem} 东周->{dyn} {name[:30]}")
        if apply:
            d["dynasty"] = dyn
            d["year_range"] = list(ERA[dyn])
            d["updated_at"] = "2026-09-23"
            p.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        n += 1
    print("C done:", n)


def best_dyn(lo, hi):
    """Dynasty with max overlap; tie-break: earlier dynasty containing start."""
    best, best_ov = None, 0
    for k, (a, b) in RANGES.items():
        ov = min(hi, b) - max(lo, a) + 1
        if ov > best_ov:
            best, best_ov = k, ov
    return best, best_ov, (hi - lo + 1)


def sec_d(apply):
    n = ambiguous = 0
    dist = Counter()
    for p, d in load_all():
        if d.get("dynasty") != "不详":
            continue
        yr = d.get("year_range")
        if not yr or not isinstance(yr[0], (int, float)):
            continue
        lo, hi = int(yr[0]), int(yr[1])
        dyn, ov, span = best_dyn(lo, hi)
        if not dyn or ov <= 0:
            continue
        # span covers >2 dynasties without a clear majority -> keep, report
        if ov < 0.5 * span and span - ov > 400:
            ambiguous += 1
            print(f"D-AMB {p.stem} {yr} -> {dyn}(ov {ov}/{span}) {(d.get('name') or '')[:24]}")
            continue
        print(f"D {'SET' if apply else 'DRY'} {p.stem} {yr}->{dyn} ({ov}/{span}) {(d.get('name') or '')[:24]}")
        dist[dyn] += 1
        if apply:
            d["dynasty"] = dyn
            d["updated_at"] = "2026-09-23"
            p.write_text(json.dumps(d, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        n += 1
    print("D done:", n, "ambiguous kept:", ambiguous, dict(dist.most_common(10)))


if __name__ == "__main__":
    apply = "--apply" in sys.argv
    only = None
    for a in sys.argv[1:]:
        if a.startswith("--only"):
            only = a.split("=")[1]
    for s in "ABCD":
        if only and s != only:
            continue
        print(f"======== section {s} ========")
        {"A": sec_a, "B": sec_b, "C": sec_c, "D": sec_d}[s](apply)
