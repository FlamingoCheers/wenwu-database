"""陕西历史博物馆藏品目录采集器。

数据源：www.sxhm.com 公开藏品目录 Excel（/down/news/{470..504}.html 为直链下载）。
本地策略（用户确认）：只入库钱币类（文件 id=499）的"品种"——同名称藏品聚合为
一条记录，其余类别多为无图目录行，不入库。Excel 需先下载到 --src 目录。

用法：
    python collectors/sxhm_collector.py                # 从默认目录读 499.xlsx 入库
    python collectors/sxhm_collector.py --dry-run      # 只统计不写文件
"""
import argparse
import json
import re
import sys
from collections import OrderedDict
from datetime import date
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "data" / "relics"
DEFAULT_SRC = Path(r"C:\Users\ADMINI~1\AppData\Local\Temp\opencode\sxhm")

FILE_ID = 499
SOURCE_URL = f"https://www.sxhm.com/down/news/{FILE_ID}.html"
MUSEUM = "陕西历史博物馆"
LICENSE = f"©{MUSEUM}"

EMPTY = {"", "<空>", None}
HEADER = ("文物编号", "名称", "原名", "年代1", "具体年代", "文物类别",
          "具体尺寸", "质量范围", "具体质量", "质量单位")

# 年代1 里的世纪/特殊写法 → (受控朝代, 年份区间)
ERA_DYNASTY = {
    "公元2世纪": ("汉", [101, 200]),
    "公元3世纪": ("三国", [201, 300]),
    "公元5世纪": ("东晋", [401, 500]),
    "公元6世纪": ("南北朝", [501, 600]),
    "公元7世纪": ("唐", [601, 700]),
    "公元8世纪": ("唐", [701, 800]),
    "公元12世纪": ("宋", [1101, 1200]),
    "公元13世纪": ("南宋", [1201, 1300]),
    "公元14世纪": ("元", [1301, 1400]),
    "公元15世纪": ("明", [1401, 1500]),
    "公元17世纪": ("清", [1601, 1700]),
    "公元18世纪": ("清", [1701, 1800]),
    "公元19世纪": ("清", [1801, 1900]),
    "公元20世纪": ("近代", [1901, 2000]),
    "公元前19世纪": ("夏", [-1900, -1801]),
    "公元前2世纪": ("汉", [-200, -101]),
    "五代十国": ("五代十国", None),
    "南北朝": ("南北朝", None),
    "三国": ("三国", None),
    "新石器时代": ("新石器时代", None),
    "周": ("东周", None),
    "东晋十六国": ("东晋", None),
    "中华民国(1912~1949)": ("近代", [1912, 1949]),
    "中华人民共和国(1949年10月1日成立)": ("近代", [1949, 1949]),
}

# 唐代“开元通宝”铜钱 → 简单前缀朝代 + 括注年份
ERA_RE = re.compile(r"^([^（(\d]+?)\s*(?:[（(]\s*(前)?(\d+)\s*[~～]\s*(前)?(\d+)\s*[）)])?$")

# 从名称推断材质
MATERIAL_RE = re.compile(r"铜|银|金|铁|纸|镍|铅|铝|锡|贝")


def parse_era(text):
    """'唐(618~907)' → ('唐', [618, 907])；'汉' → ('汉', None)。"""
    if text in EMPTY:
        return "不详", None
    t = str(text).strip()
    if t in ERA_DYNASTY:
        return ERA_DYNASTY[t]
    m = ERA_RE.match(t)
    if not m:
        return "不详", None
    dyn = m.group(1).strip()
    b_pre, b, e_pre, e = m.group(2), m.group(3), m.group(4), m.group(5)
    rng = None
    if b and e:
        begin = -int(b) if b_pre else int(b)
        end = -int(e) if e_pre else int(e)
        if begin <= end:
            rng = [begin, end]
    return dyn, rng


def clean(v):
    return None if v in EMPTY else str(v).strip()


def read_rows(xlsx_path):
    wb = openpyxl.load_workbook(xlsx_path, read_only=True)
    ws = wb["Sheet1"] if "Sheet1" in wb.sheetnames else wb[wb.sheetnames[0]]
    rows = []
    for i, row in enumerate(ws.iter_rows(values_only=True)):
        if i == 0:
            continue
        if not row or clean(row[1]) is None:
            continue
        rows.append(row)
    wb.close()
    return rows


def collect(src_dir, dry_run=False):
    src = Path(src_dir) / f"{FILE_ID}.xlsx"
    if not src.exists():
        sys.exit(f"缺少数据文件: {src}（请先从 {SOURCE_URL} 下载）")
    rows = read_rows(src)

    groups = OrderedDict()
    for row in rows:
        era_raw = clean(row[3])
        name = clean(row[1])
        if name in (None, ""):
            continue
        dyn, rng = parse_era(era_raw)
        key = (dyn, rng and tuple(rng), name)
        g = groups.setdefault(key, {"name": name, "dyn": dyn, "rng": rng,
                                    "era_raw": era_raw, "count": 0, "first": None})
        g["count"] += 1
        if g["first"] is None:
            g["first"] = [clean(c) for c in row]

    coins = [g for g in groups.values()]
    print(f"钱币目录行 {len(rows)} → 品种 {len(coins)}")
    if dry_run:
        return

    # 全量重写 SXHM 记录（品种聚合随目录更新可能变化）
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    removed = 0
    for old in OUT_DIR.glob("SXHM-*.json"):
        old.unlink()
        removed += 1
    if removed:
        print(f"清理旧记录 {removed} 条")

    today = date.today().isoformat()
    seen_ids = set()
    written = 0
    for g in coins:
        first = g["first"]
        inv = first[0] or f"VAR{written:05d}"
        rid = f"SXHM-{inv}"
        n = 2
        while rid in seen_ids:
            rid = f"SXHM-{inv}-{n}"
            n += 1
        seen_ids.add(rid)

        name = g["name"]
        material = MATERIAL_RE.search(name)
        era_txt = g["dyn"] + (f"（{g['rng'][0]}–{g['rng'][1]} 年）" if g["rng"] else "时期")
        summary = (f"{name}，{era_txt}。{MUSEUM}藏中国历代钱币。馆方公开目录中该名称品种共登记 "
                   f"{g['count']} 件，本条为同名称品种汇总记录（代表藏品编号 {inv}）。")

        rec = {
            "relic_id": rid,
            "name": name,
            "aliases": [first[2]] if first[2] and first[2] != name else [],
            "dynasty": g["dyn"],
            "year_range": list(g["rng"]) if g["rng"] else None,
            "category": "钱币",
            "material": material.group(0) if material else None,
            "dimensions": first[6],
            "excavated_from": "",
            "collection": {
                "museum": MUSEUM,
                "region": "中国大陆",
                "inventory_no": inv,
            },
            "summary": summary,
            "history": "",
            "interpretation": [],
            "images": [],
            "source_url": SOURCE_URL,
            "license": LICENSE,
            "tags": [],
            "related": [],
            "raw_ref": f"raw/sxhm/{FILE_ID}.xlsx",
            "needs_review": False,
            "fetched_at": today,
            "updated_at": today,
        }
        (OUT_DIR / f"{rid}.json").write_text(
            json.dumps(rec, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        written += 1
    print(f"入库 {written} 条 → {OUT_DIR}")


def main():
    ap = argparse.ArgumentParser(description="陕西历史博物馆钱币品种入库")
    ap.add_argument("--src", default=str(DEFAULT_SRC), help="存放 {FILE_ID}.xlsx 的目录")
    ap.add_argument("--dry-run", action="store_true", help="只统计不写文件")
    args = ap.parse_args()
    collect(args.src, args.dry_run)


if __name__ == "__main__":
    main()
