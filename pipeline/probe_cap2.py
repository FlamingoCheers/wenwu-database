# -*- coding: utf-8 -*-
"""Scan rendered Capital page for API endpoints / NUXT data."""
import pathlib
import re

t = (pathlib.Path("raw/probe_prov") / "rendered_capital_collection.html").read_text(encoding="utf-8", errors="ignore")
hits = set(re.findall(r'"([^"]*(?:api|\.json|collection)[^"]*)"', t))
for h in sorted(hits)[:30]:
    print(ascii(h[:110]))
print("---NUXT---")
m = re.search(r"__NUXT_DATA__[^>]*>(.{0,600})", t, re.S)
if m:
    print(ascii(m.group(1)[:550]))
