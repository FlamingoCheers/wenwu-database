"""全库朝代审计与修正。

背景: 旧版 map_dynasty 按词表顺序扫描, 品名内画家名(夏珪/李唐/唐寅/沈周/金农…)
的朝代字抢先命中, 造成 NPM-1337「宋夏珪山居留客圖」被标为 夏 之类错误。

检查项:
1. NPM: 品名首词朝代(繁->简) vs 存储 dynasty; 存储为更细朝代(北宋/西汉)视为兼容。
2. 全库: 画家名碰撞黑名单命中报告。
3. NMC: dynasty 属先秦(夏/商/西周/东周)全列, 人工/子Agent 复核; 过嫁妆系列直接定为 近代+历史影像。

用法: python pipeline/audit_dynasty.py [--apply]   # 默认 dry-run
报告: raw/_dynasty_audit.json
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "collectors"))
import dynasty_util as du  # noqa: E402

TRAD = str.maketrans({"東": "东", "漢": "汉", "戰": "战", "國": "国",
                      "晉": "晋", "遼": "辽", "時": "时"})

# 最长优先: 多字朝代在前, 避免单字抢先; 金(?!剛|刚) 排除金刚萨埵等佛教名
LEAD_RE = re.compile(
    r"^(新石器时代|魏晋南北朝|五代十国|南北朝|西夏|西周|东周|春秋|战国"
    r"|西汉|东汉|北宋|南宋|民国|近代|商|秦|汉|隋|唐|五代|辽|宋|金(?!剛|刚)|元|明|清|周)")

# 存储值与首词值兼容(存储更细不算错)
COMPAT = {
    "宋": {"宋", "北宋", "南宋"},
    "汉": {"汉", "西汉", "东汉"},
    "东周": {"东周", "西周", "春秋", "战国"},
    "五代十国": {"五代十国", "五代"},
    "南北朝": {"南北朝", "东晋", "西晋"},
    "南宋": {"宋", "南宋"}, "北宋": {"宋", "北宋"},
    "西汉": {"汉", "西汉"}, "东汉": {"汉", "东汉"},
    "西周": {"西周", "东周"}, "春秋": {"东周", "春秋"}, "战国": {"东周", "战国"},
}

# 画家名 -> 朝代字碰撞(黑名单命中且存储=该朝代即疑似污染)
PAINTER_DYN = {
    "夏珪": "夏", "夏圭": "夏", "夏昶": "夏", "周虎": "东周",
    "李唐": "唐", "唐寅": "唐", "唐棣": "唐", "唐岱": "唐",
    "宋旭": "宋", "宋珏": "宋",
    "沈周": "东周", "周臣": "东周", "周昉": "东周", "周文矩": "东周", "周朗": "东周",
    "金农": "金", "金廷标": "金",
}

COARSE = {k: (lo, hi) for k, lo, hi in du.COARSE_RANGES}

# 名称中的词组碰撞源: 存储朝代字实际来自这些词而非年代
COLLISION = {
    "金": ["嵌金", "金剛", "金刚", "金明", "黃金", "黄金", "鎏金", "錯金",
           "错金", "紫金", "貼金", "贴金", "金漆", "泥金", "金星"],
    "夏": ["夏山", "夏日", "夏景", "華夏", "华夏"],
    "周": ["周易"],
    "商": ["商岩", "商山", "商旅"],
    "唐": ["唐十八"],
}


def load_all():
    out = []
    for f in sorted((ROOT / "data" / "relics").glob("*.json")):
        out.append((f, json.loads(f.read_text(encoding="utf-8"))))
    return out


def main(apply: bool):
    records = load_all()
    fixes, flagged, report = [], [], []
    guozhuang = []
    MODERN_RE = re.compile(r"民国|民國|合影|留影|照片|19\d\d年")
    for path, r in records:
        rid, name = r["relic_id"], r.get("name") or ""
        pre = rid.split("-")[0]
        stored = r.get("dynasty")
        lead_m = LEAD_RE.match(name.translate(TRAD))
        lead = lead_m.group(1) if lead_m else None
        if lead == "五代":
            lead = "五代十国"
        entry = {"id": rid, "name": name, "stored": stored, "lead": lead}

        # NMC/NMC 现代照片类: 民国/合影/19xx年 字样却被标先秦朝代 -> 近代+历史影像
        if pre == "NMC" and stored in {"夏", "商", "西周", "东周", "春秋", "战国", "秦", "汉"} \
                and MODERN_RE.search(name):
            entry["reason"] = "NMC 名称含现代照片特征却标先秦"
            entry["fix"] = "近代"
            entry["reclass"] = "历史影像"
            fixes.append(entry)
            continue
        # 过嫁妆/婚嫁系列: 婚俗历史照片
        if "过嫁妆" in name or "婚嫁" in name:
            guozhuang.append({**entry, "reason": "婚俗历史照片系列"})

        if pre == "NPM" and lead:
            if stored in (None, "", "不详"):
                entry["reason"] = "存储不详, 按品名首词补"
                entry["fix"] = lead
                fixes.append(entry)
            else:
                painter = next((p for p in PAINTER_DYN if p in name), None)
                if painter and stored == PAINTER_DYN[painter]:
                    entry["reason"] = f"画家名碰撞({painter})"
                    entry["fix"] = lead
                    fixes.append(entry)
                elif stored in COLLISION and any(c in name for c in COLLISION[stored]):
                    entry["reason"] = f"词组碰撞({next(c for c in COLLISION[stored] if c in name)})"
                    entry["fix"] = lead
                    fixes.append(entry)
                elif stored not in COMPAT.get(lead, {lead}):
                    # 不确定(如 漢元通寶=五代钱, 宋元名绘册内五代页): 只报告
                    report.append({**entry, "reason": "存储与首词不符, 保守不改"})
        elif pre != "NPM" and any(p in name for p in PAINTER_DYN):
            flagged.append({**entry, "reason": "画家名黑名单(非NPM, 仅报告)"})

        if pre == "NMC" and stored in {"夏", "商", "西周", "东周"}:
            flagged.append({**entry, "reason": "NMC先秦朝代, 需人工复核"})

    print(f"=== 待修正 {len(fixes)} ===")
    for e in fixes:
        print(f"{e['id']}  {e['stored']} -> {e.get('fix')}  [{e['reason']}]  {e['name'][:40]}")
    print(f"=== 保守不改(报告) {len(report)} ===")
    for e in report:
        print(f"{e['id']}  stored={e['stored']} lead={e['lead']}  {e['name'][:40]}")
    print(f"=== 仅报告 {len(flagged)} ===")
    for e in flagged:
        print(f"{e['id']}  stored={e['stored']}  [{e['reason']}]  {e['name'][:40]}")
    print(f"=== 过嫁妆/婚嫁系列 {len(guozhuang)} ===")
    for e in guozhuang:
        print(f"{e['id']}  stored={e['stored']}  {e['name'][:40]}")

    (ROOT / "raw").mkdir(exist_ok=True)
    (ROOT / "raw" / "_dynasty_audit.json").write_text(
        json.dumps({"fixes": fixes, "report": report, "flagged": flagged,
                    "guozhuang": guozhuang},
                   ensure_ascii=False, indent=1), encoding="utf-8")

    if not apply:
        print("dry-run, 未写入; 加 --apply 生效")
        return

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    n = 0
    for e in fixes:
        path = ROOT / "data" / "relics" / f"{e['id']}.json"
        r = json.loads(path.read_text(encoding="utf-8"))
        r["dynasty"] = e["fix"]
        r["dynasty_confidence"] = "high"
        lo_new = COARSE.get(e["fix"])
        if lo_new:
            lo, hi = lo_new
            if r.get("year_range") is None:
                r["year_range"] = [lo, hi]
            else:
                # 旧朝代区间整体落在旧朝代粗区间内 = 当年粗兜底的产物, 一并纠正
                old = COARSE.get(e["stored"])
                yr = r["year_range"]
                if old and yr[0] >= old[0] and yr[1] <= old[1]:
                    r["year_range"] = [lo, hi]
        r["updated_at"] = now
        path.write_text(json.dumps(r, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        n += 1
    # 过嫁妆系列: 近代 + 历史影像
    for e in guozhuang:
        path = ROOT / "data" / "relics" / f"{e['id']}.json"
        r = json.loads(path.read_text(encoding="utf-8"))
        r["dynasty"] = "近代"
        r["year_range"] = r.get("year_range") or [1912, 1949]
        r["category"] = "历史影像"
        r["updated_at"] = now
        path.write_text(json.dumps(r, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        n += 1
    print(f"applied: {n} records")


if __name__ == "__main__":
    main(apply="--apply" in sys.argv)
