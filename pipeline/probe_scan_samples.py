# -*- coding: utf-8 -*-
"""Analyze saved probe samples: find list/detail link patterns per museum."""
import pathlib
import re

D = pathlib.Path("raw/probe_prov")

for f in sorted(D.iterdir()):
    n = f.name
    if not n.startswith("r2_"):
        continue
    try:
        t = f.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        print(n, "ERR", repr(e)[:60])
        continue
    hs = re.findall(r'href="([^"]+)"', t)
    cand = [h for h in hs if re.search(r"(relic|cang|detail|antique|collection|cp_|zp|collection|guancang)", h)]
    print(ascii(n), len(t), "hrefs:", len(hs), "cand:", len(set(cand)))
    for h in sorted(set(cand))[:10]:
        print("   ", h)
