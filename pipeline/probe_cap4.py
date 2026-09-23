# -*- coding: utf-8 -*-
"""Find Capital apiBase value (escaped forms) + parse embedded collection list from NUXT payload."""
import json
import pathlib
import re

t = (pathlib.Path("raw/probe_prov") / "rendered_capital_collection.html").read_text(encoding="utf-8", errors="ignore")
for m in re.finditer(r"apiBase[^,}]{0,120}", t):
    print("A:", ascii(m.group(0)[:140]))

# NUXT_DATA payload
m = re.search(r'id="__NUXT_DATA__"[^>]*>(.*?)</script>', t, re.S)
if m:
    try:
        data = json.loads(m.group(1))
        # flatten: find strings that look like relic ids (32 hex)
        hexes = [x for x in data if isinstance(x, str) and re.fullmatch(r"[0-9a-f]{32}", x)]
        print("hex ids:", len(hexes), hexes[:6])
        # find names near ids: strings of len 2-30 containing 器|瓷|铜|玉 etc
        names = [x for x in data if isinstance(x, str) and 2 <= len(x) <= 30 and re.search(r"[器瓷铜玉金漆佛炉尊瓶洗盒]", x)]
        print("name-ish:", len(names), ascii(names[:10]))
    except Exception as e:
        print("json ERR", repr(e)[:80])
