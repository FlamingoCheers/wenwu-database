# -*- coding: utf-8 -*-
"""Locate records named by the user; print id/name/dynasty/years/category/summary."""
import glob, json, pathlib, re, sys

QUERIES = [
    "私塾", "雪景", "蚩尤", "送殡", "孙子", "孫子", "快雪堂", "枭首", "米继芬",
    "Pillar from Tomb", "Oracle Bones", "Figure in a Landscape", "回文钵",
]
FOREIGN = re.compile(
    r"日本|犍陀羅|犍陀罗|喀什米爾|喀什米尔|古加拉特|巴基斯坦|波斯|薩珊|萨珊|"
    r"埃及|希臘|希腊|羅馬|罗马|歐洲|欧洲|伊斯蘭|伊斯兰|平安時代|平安时代")

hits, foreign = [], []
for f in glob.glob("data/relics/*.json"):
    d = json.loads(pathlib.Path(f).read_text(encoding="utf-8"))
    name = d.get("name") or ""
    text = name + " " + (d.get("desc") or d.get("summary") or "")
    for q in QUERIES:
        if q in text:
            hits.append((f, d))
            break
    if FOREIGN.search(text):
        foreign.append((f, d))

def row(f, d):
    s = (d.get("summary") or "").replace("\n", " ")[:50]
    return (f"{pathlib.Path(f).stem} | {d.get('dynasty')} {d.get('year_range')} "
            f"| {d.get('category')} | {name60(d)} | {s}")

def name60(d):
    return (d.get("name") or "")[:60]

print("== NAMED ITEMS ==")
for f, d in sorted(hits):
    print(row(f, d))
print(f"\n== FOREIGN-ORIGIN CANDIDATES ({len(foreign)}) ==")
for f, d in sorted(foreign, key=lambda x: pathlib.Path(x[0]).stem):
    print(row(f, d))
