# -*- coding: utf-8 -*-
"""Dump all hrefs + card markup from Hunan guobao list page."""
import re
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"}
req = urllib.request.Request("https://www.hnmuseum.com/zh-hans/guangcang_gauobao", headers=UA)
t = urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "replace")

hs = re.findall(r'href="([^"]+)"', t)
from collections import Counter
pref = Counter(h.split("?")[0].rsplit("/", 1)[0] if "/" in h else h for h in hs)
print("href prefixes:")
for p, c in pref.most_common(15):
    print("  ", c, p)

# find item-card-ish segments
for m in re.finditer(r'class="[^"]*(?:item|card|box|list)[^"]*"', t):
    s = max(0, m.start() - 80)
    seg = t[m.start():m.start() + 260].replace("\n", " ")
    print("---", seg[:300])
    if m.start() > 12000:
        break
