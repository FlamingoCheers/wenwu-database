# -*- coding: utf-8 -*-
"""全库质量审计：分类疑误 + 描述缺失盘点 -> raw/_quality_audit.json

只读扫描 data/relics/*.json，不修改任何记录。产出：
- 分类疑误清单：名称强关键词指向 A 类、记录标 B 类（疑似，非定论，供 LLM 复核）
- 描述薄弱清单：summary 过短 / history、interpretation、tags 空
- 按馆汇总 needs_review
"""
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RELICS_DIR = ROOT / "data" / "relics"
REPORT = ROOT / "raw" / "_quality_audit.json"

# 名称强关键词 -> 应属类别（只在记录类别与之不同时记为疑误）
KEYWORD_CAT = [
    (r"通宝|重宝|元宝|五铢|布币|刀币|钱范|贝币", "钱币"),
    (r"瓷", "瓷器"),
    (r"陶|唐三彩|瓦当", "陶器"),
    (r"玉|珉|璜|璧|琮|璋|珮", "玉器"),
    (r"漆|剔红|剔黑|螺钿", "漆器"),
    (r"绣|锦|缎|绸|纱|罗|绢|毡|氅", "织绣"),
    (r"玻璃|琉璃|料器", "玻璃器"),
    (r"砚|墨锭|镇纸|笔洗|笔架|印泥", "文房用具"),
    (r"拓本|碑刻|墓志", "碑帖拓本"),
    (r"甲骨|卜辞|卜骨", "甲骨"),
    (r"瓦|砖|构件|斗拱|鸱吻", "建筑构件"),
]
# 青铜器与金银器的词有歧义（鎏金铜佛、银盒可能属杂器），单独列、置信低
SOFT_KEYWORD_CAT = [
    (r"鼎|簋|爵|觚|尊|卣|斝|觥|簠|盨|敦|壶|盘|匜|钟|镜|炉", "青铜器"),
    (r"金杯|金盏|金碗|金壶|银盒|银盘|银杯|金饰|银饰|簪|钗|镯", "金银器"),
    (r"佛|菩萨|罗汉|造像|造像碑", "宗教造像"),
]

THIN_SUMMARY = 20  # 少于该字数视为薄弱


def name_cat_suspect(name, cat):
    for pat, want in KEYWORD_CAT:
        if re.search(pat, name) and cat != want:
            return want, "strong"
    for pat, want in SOFT_KEYWORD_CAT:
        if re.search(pat, name) and cat != want:
            return want, "soft"
    return None, None


def main():
    files = sorted(RELICS_DIR.glob("*.json"))
    cat_suspects = []          # {id, name, cat, expect, level}
    thin = []                  # 描述薄弱
    per_museum = defaultdict(Counter)
    dyn_empty = Counter()

    for f in files:
        try:
            r = json.loads(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        rid = r.get("relic_id", f.stem)
        code = rid.split("-", 1)[0]
        cat = r.get("category") or ""
        name = r.get("name") or ""
        expect, level = name_cat_suspect(name, cat)
        if expect:
            cat_suspects.append({"id": rid, "name": name[:40], "cat": cat,
                                 "expect": expect, "level": level})
        s = len((r.get("summary") or "").strip())
        h = len((r.get("history") or "").strip())
        itp = len(r.get("interpretation") or [])
        tags = len(r.get("tags") or [])
        noimg = not (r.get("images") or [])
        if s < THIN_SUMMARY:
            thin.append({"id": rid, "mu": code, "name": name[:30],
                         "summary": s, "history": h, "interp": itp, "tags": tags})
        per_museum[code]["n"] += 1
        if s < THIN_SUMMARY:
            per_museum[code]["thin_summary"] += 1
        if h == 0:
            per_museum[code]["no_history"] += 1
        if itp == 0:
            per_museum[code]["no_interp"] += 1
        if tags == 0:
            per_museum[code]["no_tags"] += 1
        if noimg:
            per_museum[code]["no_image"] += 1
        if r.get("needs_review"):
            per_museum[code]["needs_review"] += 1
        if not r.get("dynasty") or r.get("dynasty") == "不详":
            dyn_empty[code] += 1

    strong = [c for c in cat_suspects if c["level"] == "strong"]
    report = {
        "total": len(files),
        "category_suspects": {"strong": len(strong), "soft": len(cat_suspects) - len(strong),
                              "samples": cat_suspects[:200]},
        "thin_summary_count": len(thin),
        "thin_summary_samples": thin[:200],
        "by_museum": {k: dict(v) for k, v in sorted(per_museum.items())},
        "dynasty_empty": dict(dyn_empty),
    }
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"总计 {len(files)} 件")
    print(f"分类疑误：强线索 {len(strong)} 件，弱线索 {len(cat_suspects)-len(strong)} 件")
    print(f"描述薄弱（summary<{THIN_SUMMARY}字）：{len(thin)} 件")
    for mu, c in sorted(per_museum.items()):
        print(f"  [{mu}] n={c['n']} thin={c['thin_summary']} no_history={c['no_history']} "
              f"no_interp={c['no_interp']} no_tags={c['no_tags']} no_image={c['no_image']} review={c['needs_review']}")
    print(f"报告: {REPORT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
