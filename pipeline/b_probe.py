# -*- coding: utf-8 -*-
"""B 阶段预检 v2：全库重算 thin 名单 + NMC/NPM raw 可用性（只读）。"""
import json, os, re, glob, random

thin = {"MET": [], "NPM": [], "NMC": [], "CLE": [], "AIC": []}
for p in glob.glob("data/relics/*.json"):
    rid = os.path.basename(p)[:-5]
    pre = rid.split("-")[0]
    if pre not in thin:
        continue
    d = json.load(open(p, encoding="utf-8"))
    s = (d.get("summary") or "").strip()
    if len(s) < 20:
        thin[pre].append((rid, s))

for k, v in thin.items():
    print(k, len(v))

# NMC thin: raw html 有无说明段落
nmc = [r for r, _ in thin["NMC"]]
ok, none_raw = 0, 0
for rid in nmc[:20]:
    p = f"raw/nmc/detail_{rid.split('-')[1]}.html"
    if not os.path.exists(p):
        none_raw += 1
        continue
    h = open(p, encoding="utf-8", errors="ignore").read()
    paras = [x.strip() for x in re.findall(r"<p[^>]*>([^<]{15,400})</p>", h)]
    paras = [x for x in paras if not re.match(r"^(版权|京ICP|地址|电话|邮编|扫描)", x)]
    if paras:
        ok += 1
print(f"NMC thin 前20: raw有段落 {ok}, 无raw {none_raw}")

# NPM thin: 全部无 summary 还是有短的
npm = thin["NPM"]
null_cnt = sum(1 for _, s in npm if not s)
print(f"NPM thin {len(npm)}: summary为null {null_cnt}, 短文本 {len(npm)-null_cnt}")
for rid, s in random.Random(7).sample(npm, 4):
    print(" ", rid, repr(s[:40]))

# MET thin: 随机看3条现有 summary
met = thin["MET"]
for rid, s in random.Random(3).sample(met, 3):
    print(" ", rid, repr(s[:50]))
