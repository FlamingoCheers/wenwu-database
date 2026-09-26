# -*- coding: utf-8 -*-
"""Break down needs_review population by cause and museum."""
import glob
import io
import json
import os
import sys
import collections

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

causes = collections.Counter()
by_museum = collections.defaultdict(collections.Counter)
samples = collections.defaultdict(list)

for f in glob.glob("data/relics/*.json"):
    r = json.load(open(f, encoding="utf-8"))
    if not r.get("needs_review"):
        continue
    rid = r.get("relic_id", "")
    pre = rid.split("-")[0]
    d = r.get("dynasty")
    tags = []
    if r.get("desc_ai"):
        tags.append("desc_ai")
    if d == "不详":
        tags.append("dyn不详")
    if not r.get("images"):
        tags.append("无图")
    if r.get("dynasty_confidence") == "low":
        tags.append("dyn_low")
    summ = r.get("summary") or ""
    if len(summ) < 20:
        tags.append("summary短")
    key = "+".join(tags) if tags else "仅标记无明细"
    causes[key] += 1
    by_museum[pre][key] += 1
    if len(samples[key]) < 2:
        samples[key].append(rid + " " + (r.get("name") or "")[:20])

print("total needs_review:", sum(causes.values()))
print()
for k, v in causes.most_common(20):
    print("%6d  %-30s  e.g. %s" % (v, k, " | ".join(samples[k])[:80]))
print()
for pre in sorted(by_museum, key=lambda x: -sum(by_museum[x].values())):
    tot = sum(by_museum[pre].values())
    top = by_museum[pre].most_common(3)
    print("%-5s %6d   %s" % (pre, tot, top))
