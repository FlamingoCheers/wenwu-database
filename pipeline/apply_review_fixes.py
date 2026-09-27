# -*- coding: utf-8 -*-
"""应用 2026-09-27 人工复核清单（用户点名的逐条校正）。

用法: python pipeline/apply_review_fixes.py          # dry-run
      python pipeline/apply_review_fixes.py --apply

规则:
 - 改 dynasty / category（用户判定，dynasty_confidence=manual）
 - year_range: 若现有区间不落在目标朝代区间内则覆盖为该朝代区间，否则保留（更精确者优先）
 - needs_review: 复核后仅保留 desc_ai 造成的标记
 - 删除 4 件韩国 NPM 记录
"""
import json, os, io, sys, glob
from datetime import date

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RD = os.path.join(ROOT, "data", "relics")
TODAY = str(date.today())

# 朝代 -> 年份区间（取自受控词表）
VOCAB = json.load(open(os.path.join(ROOT, "data", "vocab", "dynasties.json"), encoding="utf-8"))
RANGE = {d["key"]: d.get("range") for d in VOCAB["dynasties"]}

APPLY = "--apply" in sys.argv

# (relic_id, dynasty或None, category或None)
FIX_ID = [
    ("CLE-1940-597", "明", None),
    ("NPM-15471", "宋", None),
    ("NPM-17394", "宋", None),
    ("NPM-17833", "元", None),
    ("NPM-24482", "元", None),
    ("NPM-24585", "辽", None),
    ("NPM-24586", "辽", None),
    ("NPM-24588", "辽", None),
    ("NPM-24591", "辽", None),
    ("NPM-3816", "宋", None),
    ("NPM-42918", "辽", None),
    ("NPM-42978", "辽", None),
    ("NPM-42984", "辽", None),
    ("NPM-43032", "辽", None),
    ("NPM-43384", "宋", None),
    ("NPM-43439", "辽", None),
    ("NPM-43507", "辽", None),
    ("NPM-5124", "宋", None),
    ("NPM-56785", "辽", None),
    ("NPM-57615", "辽", None),
    ("SMI-fsg_FSC-W-23", "战国", None),
    ("HAM-10916", "现当代", None),          # 十竹斋笺谱（1952 年刊行）
    ("HAM-1429", "现当代", None),
    ("HAM-143022", "现当代", None),
    ("HAM-147442", "商", None),
    ("HAM-148608", "商", None),
    ("HAM-149541", "夏", None),
    ("HAM-149551", "夏", None),
    ("HAM-149552", "夏", None),
    ("HAM-174175", "商", None),
    ("HAM-178614", "商", None),
    ("HAM-182445", "夏", None),
    ("HAM-196998", "夏", None),
    ("HAM-198532", "现当代", None),
    ("HAM-198858", "现当代", None),
    ("HAM-199379", "现当代", None),
    ("HAM-199752", "现当代", None),
    ("HAM-201303", "现当代", None),
    ("HAM-202703", "现当代", None),
    ("HAM-203004", "现当代", None),
    ("HAM-204482", "西周", None),
    ("HAM-204525", "西周", None),
    ("HAM-204526", "西周", None),
    ("HAM-204606", "西周", None),
    ("HAM-204743", "西周", None),
    ("HAM-204866", "西周", None),
    ("HAM-204869", "西周", None),
    ("HAM-204870", "西周", None),
    ("HAM-204902", "西周", None),
    ("HAM-204852", "西周", None),
    ("HAM-204874", "西周", None),
    ("HAM-204882", "战国", None),
    ("HAM-204883", "西周", None),
    ("HAM-204901", "西周", None),
    ("HAM-204911", "西周", None),
    ("HAM-204914", "西周", None),
    ("HAM-204917", "西周", None),
    ("HAM-204921", "西周", None),
    ("HAM-204934", "西周", None),
    ("HAM-204935", "西周", None),
    ("HAM-204939", "西周", None),
    ("HAM-204946", "西周", None),
    ("HAM-204948", "西周", None),
    ("HAM-204951", "西周", None),
]

# (name, dynasty或None, category或None)  —— 按名称精确匹配，可多条
FIX_NAME = [
    ("毛泽东会见来华的美国总统理查德·尼克松", "现当代", "历史影像"),
    ("五铢", None, "钱币"),
    ("教会学校的穷学生", "清", "历史影像"),
    ("广州夏葛女子医学院外景", "近代", "历史影像"),
    ("宁波女子师范学校的学生正在上课", "近代", "历史影像"),
    ("北京贝满女中的学生队伍", "近代", "历史影像"),
    ("1929年8月妇女联合会代表在天安门前演讲时的情景", "现当代", "历史影像"),
    ("科尔沁亲王阿穆尔灵圭的长子辅国公和希格10岁时的留影", "清", "历史影像"),
    ("梓宫灵车在前门站进入专列时的情景", "清", "历史影像"),
    ("山东邮区济南邮务管理局", None, "历史影像"),
    ("1861年湖北汉口脚力行门前等待工作的搬运工人", None, "历史影像"),
    ("1895年中国南方的轿子与抬轿夫", None, "历史影像"),
    ("京张铁路康庄停车场景象", "清", None),
    ("京张铁路门头沟车站", "清", None),
    ("新宁铁路员工与机车的合影", "清", None),
    ("火车初通北京城", "清", None),
    ("济南津浦路上的跨桥", None, "历史影像"),
    ("汉粤川铁路线使用的巴尔德温大机车", "清", None),
    ("1917年汉粤川铁路线上的岳州停车场及机车房", "近代", None),
    ("甘肃凉州府的露天书店", "清", None),
    ("筛茶叶", "清", None),
    ("上海城隍庙附近的茶铺", "清", None),
    ("卖编制篾器的小贩", "清", None),
    ("广东街头卖水果的路边小贩", "清", None),
    ("到市场去卖鹅的小贩", "清", None),
    ("1920年时的山西保晋公司阳泉铁厂", "现当代", "历史影像"),
    ("华俄道胜银行天津分行", "近代", None),
    ("新民储蓄银行营业部客户接待处内景", "清", None),
    ("北平骑巡队", "清", "历史影像"),
    ("1908年中国会审员关炯之与德国副总领事会审刑事案件", "清", "历史影像"),
    ("绰号为“小霸王”的绑匪张世魁", "清", None),
    ("押解绑架“人票”的土匪途经北平南新华街", "清", None),
    ("周有光撰写的《汉字改革概论》日文版", "现当代", None),
    ("点眉纹双耳彩陶罐", "新石器时代", None),
    ("四系彩陶碟形器", "新石器时代", None),
    ("粉白地暗花双龙戏球纹宣纸", "清", None),
    ("九龙壁", "现当代", None),
    ("潮州窑青白釉释迦牟尼像", "宋", None),
    ("“天兴七年”金币", "南北朝", "钱币"),
    ("永通万国", None, "钱币"),
]

DELETE = ["NPM-24652", "NPM-24653", "NPM-24654", "NPM-24655"]  # 韩国藏品，非中国文物


def load(rid):
    p = os.path.join(RD, rid + ".json")
    return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None


def save(r):
    p = os.path.join(RD, r["relic_id"] + ".json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump(r, f, ensure_ascii=False, indent=1)
        f.write("\n")


CONFLICT = []


def fit_year(r, dyn):
    """朝代与 year_range 一致性。

    现有区间与朝代区间**完全无交集**才用朝代区间覆盖（源数据明显错）；
    有交集则保留源数据（更精确，且避免抹掉名称中的具体年份证据）。
    """
    rng = RANGE.get(dyn)
    if not rng or rng[0] is None:
        return False
    yr = r.get("year_range")
    if not yr or len(yr) != 2 or yr[0] is None or yr[1] is None:
        r["year_range"] = list(rng)
        return True
    lo, hi = min(yr), max(yr)
    if yr[0] > yr[1]:
        r["year_range"] = [lo, hi]
        return True
    if hi < rng[0] or lo > rng[1]:
        r["year_range"] = list(rng)
        return True
    if lo < rng[0] or hi > rng[1]:
        CONFLICT.append((r["relic_id"], r.get("name"), dyn, [lo, hi], list(rng)))
    return False


def apply_one(r, dyn, cat, yr_override=None, keep_year=False):
    ch = []
    if dyn and r.get("dynasty") != dyn:
        ch.append("dynasty: %s -> %s" % (r.get("dynasty"), dyn))
        r["dynasty"] = dyn
        r["dynasty_confidence"] = "manual"
        if keep_year:
            pass
        elif yr_override:
            r["year_range"] = list(yr_override)
            ch.append("year_range -> %s (指定)" % yr_override)
        elif fit_year(r, dyn):
            ch.append("year_range -> %s" % r["year_range"])
    if cat and r.get("category") != cat:
        ch.append("category: %s -> %s" % (r.get("category"), cat))
        r["category"] = cat
    if ch:
        r["needs_review"] = bool(r.get("desc_ai"))
        r["updated_at"] = TODAY
    return ch


changed, missing, noop = 0, [], []

# 需要连同年份一并指定的条目：(rid, year_range)
YR_OVERRIDE = {
    # 克利夫兰原标 17 世纪(1600-1699)，用户判定为明，改用明代区间
    "CLE-1940-597": [1368, 1644],
}
# 保留源年份不动：名称自带具体年份，与所标朝代存在冲突，留待人工确认
YR_KEEP = {"NMC-24373", "NMC-24098"}

for rid, dyn, cat in FIX_ID:
    r = load(rid)
    if r is None:
        missing.append(rid)
        continue
    # HAM 年份存在 BCE 解析 bug（如 1600~600 倒序），统一由 ham_resweep 用 period 重算
    keep = rid.startswith("HAM-")
    ch = apply_one(r, dyn, cat, YR_OVERRIDE.get(rid), keep_year=keep)
    if ch:
        changed += 1
        print("[id] %-18s %s" % (rid, "; ".join(ch)))
        if APPLY:
            save(r)
    else:
        noop.append(rid)

name_idx = {}
for p in glob.glob(os.path.join(RD, "*.json")):
    try:
        r = json.load(open(p, encoding="utf-8"))
    except Exception:
        continue
    name_idx.setdefault((r.get("name") or "").strip(), []).append(r["relic_id"])

for nm, dyn, cat in FIX_NAME:
    rids = name_idx.get(nm)
    if not rids:
        missing.append("name:" + nm)
        continue
    for rid in rids:
        r = load(rid)
        ch = apply_one(r, dyn, cat, keep_year=rid in YR_KEEP)
        if ch:
            changed += 1
            print("[name] %-18s %-30s %s" % (rid, nm[:28], "; ".join(ch)))
            if APPLY:
                save(r)
        else:
            noop.append(rid)

print("\n删除（韩国藏品）:", DELETE)
if APPLY:
    for rid in DELETE:
        p = os.path.join(RD, rid + ".json")
        if os.path.exists(p):
            os.remove(p)
            print("  deleted", rid)
        else:
            print("  missing", rid)

if CONFLICT:
    print("\n[提示] 朝代与源年份部分冲突（已保留源年份，供人工确认）:")
    for rid, nm, dyn, yr, rng in CONFLICT:
        print("  %-16s %-34s dyn=%-6s 源年份=%s 朝代区间=%s" % (rid, (nm or "")[:32], dyn, yr, rng))

print("\n合计改动 %d 条; 无变化 %d; 未找到 %s" % (changed, len(noop), missing))
print("模式:", "APPLY" if APPLY else "DRY-RUN")
