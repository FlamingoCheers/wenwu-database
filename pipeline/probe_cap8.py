# -*- coding: utf-8 -*-
"""Full parse of Capital collection NUXT_DATA payload (offline)."""
import json
import pathlib
import re

t = pathlib.Path("raw/probe_prov/rendered_capital_collection.html").read_text(encoding="utf-8", errors="ignore")
m = re.search(r'id="__NUXT_DATA__"[^>]*>(.*?)</script>', t, re.S)
data = json.loads(m.group(1))
strs = [x for x in data if isinstance(x, str)]
print("strings:", len(strs))

hexes = [x for x in strs if re.fullmatch(r"[0-9a-f]{32}", x)]
print("hex ids:", len(set(hexes)))

names = [x for x in strs if re.fullmatch(r"[\u4e00-\u9fffA-Za-z0-9、（）()·\-—·～~]{2,40}", x) and re.search(r"[\u4e00-\u9fff]", x)]
print("cjk-ish strings:", len(names))
for s in names[:40]:
    print("  ", s)
