# -*- coding: utf-8 -*-
"""Inspect rendered pages for item card selectors."""
import pathlib
import re

D = pathlib.Path("raw/probe_prov")

# Capital: find relic item links
t = (D / "rendered_capital_collection.html").read_text(encoding="utf-8", errors="ignore")
print("== CAPITAL", len(t))
hs = re.findall(r'href="([^"]+)"', t)
from collections import Counter
pref = Counter()
for h in hs:
    m = re.match(r"([^?]*?)/*$", h.split("#")[0])
    pref[h.rsplit("/", 1)[0] if "/" in h else h] += 1
for p, c in pref.most_common(12):
    print("  ", c, p[:90])
# look for likely detail patterns
cand = sorted(set(h for h in hs if re.search(r"(detail|zp|relic|cangpin|antique|wu|pin)", h, re.I)))
for h in cand[:15]:
    print("  CAND", h)

# Hunan rendered: item cards?
t2 = (D / "rendered_hunan_guobao.html").read_text(encoding="utf-8", errors="ignore")
print("== HUNAN", len(t2))
# find img cards / data urls
imgs = re.findall(r'<img[^>]+src="([^"]+)"[^>]*>', t2)
for s in imgs[:10]:
    print("  IMG", s[:110])
# any div with title-ish class
for m in re.finditer(r'<(?:div|li|a)[^>]+class="([^"]*)"[^>]*>\s*<img', t2):
    print("  CARDCLASS", m.group(1))
