# -*- coding: utf-8 -*-
"""哈佛（HAM）朝代与年份重扫：用官方 period 字段回源修正。

背景：harv_collector 早前把 period 的 BCE 年份丢了负号并写反顺序（如 1600~600），
导致大量 dynasty=不详 / year_range 倒序。官方详情页 period 字段本身带有正确年份。

数据源：raw/harv/*.json 采集缓存（5569 条，含 period/dated），离线重扫，不再打 API。

用法: python pipeline/ham_resweep.py          # dry-run（输出统计与未匹配 period）
      python pipeline/ham_resweep.py --apply
"""
import json, os, re, io, sys, glob
from collections import Counter
from datetime import date

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RD = os.path.join(ROOT, "data", "relics")
RAW = os.path.join(ROOT, "raw", "harv")
TODAY = str(date.today())
APPLY = "--apply" in sys.argv

VOCAB = json.load(open(os.path.join(ROOT, "data", "vocab", "dynasties.json"), encoding="utf-8"))
VALID = {d["key"] for d in VOCAB["dynasties"]}

# period 关键词 -> 词表朝代（按顺序优先匹配，越具体越靠前）
KEY_DYN = [
    (r"Neolithic|Liangzhu|Majiayao|Dawenkou|Longshan|Yangshao|Hongshan|Qijia|Siba|Xindian|Machang|Banshan|Qingliangang|Shijiahe|Qujialing|Zhongyuan", "新石器时代"),
    (r"Shang", "商"),
    (r"Western Zhou", "西周"),
    (r"Eastern Zhou", "东周"),
    (r"Spring and Autumn", "春秋"),
    (r"Warring States", "战国"),
    (r"Qin dynasty", "秦"),
    (r"Western Han", "西汉"),
    (r"Eastern Han", "东汉"),
    (r"Han dynasty", "汉"),
    (r"Three Kingdoms", "三国"),
    (r"Western Jin", "西晋"),
    (r"Eastern Jin", "东晋"),
    (r"Northern Wei|Eastern Wei|Western Wei|Northern Qi|Northern Zhou|Northern and Southern", "南北朝"),
    (r"Sui", "隋"),
    (r"Tang dynasty|Tang\b", "唐"),
    (r"Five Dynasties", "五代十国"),
    (r"Northern Song", "北宋"),
    (r"Southern Song", "南宋"),
    (r"Song dynasty", "宋"),
    (r"Liao dynasty|Khitan", "辽"),
    (r"Xixia|Tangut", "西夏"),
    (r"Yuan", "元"),
    (r"Ming", "明"),
    (r"Qing", "清"),
    (r"Qianlong|Kangxi|Yongzheng|Jiaqing|Daoguang|Xianfeng|Tongzhi|Guangxu|Xuantong", "清"),
    (r"Republican|Republic|Minguo", "近代"),
    (r"Modern|contemporary", "现当代"),
    (r"\bLiao\b", "辽"),
    (r"Six Dynasties", "南北朝"),
    (r"Erlitou", "夏"),
]

# 日本时期：藏品为日本制作/摹本，套用中国朝代会失真，跳过朝代推断只报备
JP = re.compile(r"Edo|Heian|Meiji|Taisho|Showa|Nara|Kamakura|Muromachi|Momoyama|Jomon|Yayoi|Kofun", re.I)

YR = re.compile(r"(?:c\.\s*)?(\d{3,4})\s*(BCE|CE|BC|AD)?\s*(?:-|–|—|to)\s*(?:c\.\s*)?(\d{1,4})\s*(BCE|CE|BC|AD)?", re.I)
CENT = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)\s+cent", re.I)
YEAR1 = re.compile(r"\b(1[0-9]{3}|20[0-9]{2})\b")
BCE_RE = re.compile(r"\b(BCE|BC)\b", re.I)
CE_RE = re.compile(r"\b(CE|AD)\b", re.I)


def _sign(yr, text):
    """整段只出现 BCE/BC（无 CE/AD）时，区间整体取负。"""
    if BCE_RE.search(text) and not CE_RE.search(text):
        return [-yr[1], -yr[0]]
    return yr


def parse_years(text):
    """从 period/dated 文本解析年份区间。

    处理三种写法：
      "1050-771 BCE"  右端带纪元、左端省略 -> 整段同纪元（双向继承）
      "206 BCE-9 CE"  跨纪元
      "Qianlong period, 1736-95"  右端缩写 -> 补左端世纪前缀
    另支持 "17th-18th century" 与单年 "2005"。
    """
    if not text:
        return None
    t = text.replace(",", "")
    m = YR.search(t)
    if m:
        a = int(m.group(1))
        era_a = (m.group(2) or "").upper()
        bs = m.group(3)
        era_b = (m.group(4) or "").upper()
        # 右端缩写补齐：1736-95 -> 1795
        b = int(bs)
        if len(bs) == 2 and len(m.group(1)) == 4:
            b = int(m.group(1)[:2] + bs)
        # 任一端带纪元标记则整段继承（另一端未标时）
        if era_a and not era_b:
            era_b = era_a
        elif era_b and not era_a:
            era_a = era_b
        if not era_a and not era_b:
            return _sign([min(a, b), max(a, b)], t)
        a_signed = -a if era_a in ("BCE", "BC") else a
        b_signed = -b if era_b in ("BCE", "BC") else b
        return [min(a_signed, b_signed), max(a_signed, b_signed)]
    cents = [int(x) for x in CENT.findall(t)]
    if cents:
        a, b = min(cents), max(cents)
        return _sign([(a - 1) * 100 + 1, b * 100], t)
    m = YEAR1.search(t)
    if m:
        y = int(m.group(1))
        return [y, y]
    return None


TO_SPLIT = re.compile(r"\s+to\s+", re.I)


def dynasty_of(period):
    """取 period 中的朝代。

    "A (x-y) to B (m-n) dynasty" 这类跨朝代写法取起始朝代 A，
    否则按具体子类优先（如 "Zhou dynasty, Warring States period" 取战国）。
    """
    m = TO_SPLIT.search(period)
    if m:
        head = period[:m.start()]
        for pat, dyn in KEY_DYN:
            if re.search(pat, head, re.I):
                return dyn
        return None      # 起始段无朝代词 -> 交由年份重叠回退，不要误取后半段
    for pat, dyn in KEY_DYN:
        if re.search(pat, period, re.I):
            return dyn
    return None


# 词表区间，用于"未归类 period"按年份最长重叠回推定朝代
RANGES = [(d["key"], d["range"][0], d["range"][1])
          for d in VOCAB["dynasties"] if d.get("range") and d["range"][0] is not None]
RANGE_MAP = {k: v for k, v in
             ((d["key"], d["range"]) for d in VOCAB["dynasties"]) if v}


def dyn_by_overlap(yr):
    """按年份与朝代区间的最长重叠回推（与 infer_dynasty 同策略）。"""
    if not yr:
        return None
    lo, hi = min(yr), max(yr)
    best, best_len = None, 0
    for key, a, b in RANGES:
        ov = min(hi, b) - max(lo, a)
        if ov >= 0:            # 单点区间（如 [2000,2000]）也算 1 年重叠
            ov += 1
        if ov > best_len:
            best, best_len = key, ov
    return best


# 1) 读缓存建立 id -> (period, dated)
cache = {}
for f in sorted(glob.glob(os.path.join(RAW, "*.json"))):
    try:
        d = json.load(open(f, encoding="utf-8"))
    except Exception:
        continue
    for r in d.get("records", []):
        cache[str(r.get("id"))] = ((r.get("period") or "").strip(), (r.get("dated") or "").strip())
print("缓存记录: %d" % len(cache))

MANUAL = set()  # 用户 2026-09-27 点名判定的条目，保持人工值
for p in glob.glob(os.path.join(RD, "HAM-*.json")):
    try:
        r = json.load(open(p, encoding="utf-8"))
    except Exception:
        continue
    if r.get("dynasty_confidence") == "manual":
        MANUAL.add(r["relic_id"])
print("用户点名（manual）条目: %d，重扫时保留其朝代" % len(MANUAL))

changed_d = changed_y = 0
no_period = 0
unmatched = Counter()
samples = {}
japanese = []
fixed_age = []

for p in sorted(glob.glob(os.path.join(RD, "HAM-*.json"))):
    try:
        r = json.load(open(p, encoding="utf-8"))
    except Exception:
        continue
    rid = r["relic_id"]
    oid = rid.split("-", 1)[1]
    period, dated = cache.get(oid, (None, None))
    if period is None:
        no_period += 1
        continue
    dyn = None
    if period:
        if JP.search(period):
            japanese.append((rid, (r.get("name") or "")[:36], period, r.get("dynasty")))
        else:
            dyn = dynasty_of(period)
            yr_tmp = parse_years(period) or parse_years(dated or "")
            if dyn is None:
                dyn = dyn_by_overlap(yr_tmp)      # 回退：按年份最长重叠
                unmatched[period] += 1
                samples.setdefault(period, rid)
    yr = parse_years(period) if period else None
    if yr is None and dated:
        yr = parse_years(dated)
        # dated 常只写 "2nd century" 而省略 BCE；若所属朝代整体在公元前且年份被解析为正，则翻转
        if yr and yr[0] > 0 and dyn:
            rng = next((v for k, v in ((d["key"], d["range"]) for d in VOCAB["dynasties"])
                        if k == dyn), None)
            if rng and rng[0] is not None and rng[1] <= 0 and not re.search(r"\b(CE|AD)\b", dated, re.I):
                yr = [-yr[1], -yr[0]]

    # 年份与朝代区间完全无交集、且年份已入晚清以后：以具体年份为准改判朝代
    # （典型情形：period 为空而 dated 为 20 世纪，旧采集器据题名误判为宋/明/唐等）
    eff = dyn or r.get("dynasty")
    if eff and yr and yr[0] > 1840:
        rng = RANGE_MAP.get(eff)
        if rng and rng[0] is not None and (max(yr) < rng[0] or min(yr) > rng[1]):
            alt = dyn_by_overlap(yr)
            if alt and alt != eff:
                fixed_age.append((rid, eff, alt, yr))
                dyn = None if rid in MANUAL else alt

    dirty = False
    old_d, old_y = r.get("dynasty"), r.get("year_range")
    if dyn and dyn in VALID and rid not in MANUAL and old_d != dyn:
        r["dynasty"] = dyn
        r["dynasty_confidence"] = "source"
        changed_d += 1
        dirty = True
    if yr:
        cur = r.get("year_range")
        # 现存的倒序/丢负号年份一律以源 period 为准覆盖
        if cur != yr:
            r["year_range"] = yr
            changed_y += 1
            dirty = True
    if dirty:
        r["needs_review"] = bool(r.get("desc_ai"))
        r["updated_at"] = TODAY
        if APPLY:
            with open(p, "w", encoding="utf-8") as f:
                json.dump(r, f, ensure_ascii=False, indent=1)
                f.write("\n")

print("\n改动：朝代 %d 条，年份 %d 条；缓存缺失 %d 条" % (changed_d, changed_y, no_period))
print("\n按年份重叠回推定朝代的 period（%d 种）:" % len(unmatched))
for per, c in unmatched.most_common(40):
    print("  %-4d %-58s 例:%s" % (c, per[:56], samples[per]))
print("\n日本时期藏品（跳过朝代推断，仅报备）: %d" % len(japanese))
for rid, nm, per, cur in japanese:
    print("  %-14s %-38s period=%-28s 现朝代=%s" % (rid, nm, per[:26], cur))
print("\n年份与朝代矛盾、已按年份改判（%d 条）:" % len(fixed_age))
for rid, od, nd, yr in fixed_age[:20]:
    print("  %-14s %s -> %s  yr=%s" % (rid, od, nd, yr))
print("\n模式:", "APPLY" if APPLY else "DRY-RUN")
