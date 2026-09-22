# -*- coding: utf-8 -*-
"""Build sub-agent task files: foreign-origin review + Han-era mislabel sweep."""
import glob, json, pathlib, re

OUT = pathlib.Path("raw/llm_clean")
OUT.mkdir(parents=True, exist_ok=True)

FOREIGN_RE = re.compile(
    r"日本|犍陀羅|犍陀罗|喀什米爾|喀什米尔|古加拉特|巴基斯坦|波斯|薩珊|萨珊|"
    r"埃及|希臘|希腊|羅馬|罗马|歐洲|欧洲|伊斯蘭|伊斯兰|平安時代|平安时代|痕都斯坦|跡都斯垣|痕都斯垣")

# --- 1) foreign-origin candidates ---
foreign = []
for f in glob.glob("data/relics/*.json"):
    d = json.loads(pathlib.Path(f).read_text(encoding="utf-8"))
    text = (d.get("name") or "") + " " + (d.get("desc") or "") + " " + (d.get("summary") or "")
    if FOREIGN_RE.search(text):
        foreign.append({
            "id": pathlib.Path(f).stem,
            "name": d.get("name"),
            "dynasty": d.get("dynasty"),
            "category": d.get("category"),
            "summary": (d.get("summary") or "")[:150],
        })
with open(OUT / "F_foreign_todo.jsonl", "w", encoding="utf-8") as w:
    for r in foreign:
        w.write(json.dumps(r, ensure_ascii=False) + "\n")

# --- 2) Han-era mislabel candidates: dynasty=汉 but evidence says later ---
han = []
for f in glob.glob("data/relics/*.json"):
    d = json.loads(pathlib.Path(f).read_text(encoding="utf-8"))
    if d.get("dynasty") != "汉":
        continue
    yr = d.get("year_range")
    name = d.get("name") or ""
    # a) years say 400+ AD (Han ended 220) -> impossible
    bad_year = bool(yr and isinstance(yr[0], (int, float)) and yr[0] > 400)
    # b) name leads with a later-era token (宋/元/明/清/南宋/北宋/明/清/金/辽...) or contains 法帖/冊拓 signals
    m = re.match(r"^(宋|北宋|南宋|元|明|清|金|遼|辽|民國|民国|五代)", name)
    bad_name = bool(m)
    if bad_year or bad_name:
        han.append({
            "id": pathlib.Path(f).stem,
            "museum": pathlib.Path(f).stem.split("-")[0],
            "name": name,
            "year_range": yr,
            "category": d.get("category"),
            "why": "year>400" if bad_year else "name-leads:" + m.group(1),
            "summary": (d.get("summary") or "")[:120],
        })
with open(OUT / "F_han_todo.jsonl", "w", encoding="utf-8") as w:
    for r in han:
        w.write(json.dumps(r, ensure_ascii=False) + "\n")

from collections import Counter
print("foreign:", len(foreign), Counter(r["id"].split("-")[0] for r in foreign))
print("han-candidates:", len(han), Counter(r["museum"] for r in han))
print("han why:", Counter(r["why"].split(":")[0] for r in han))
