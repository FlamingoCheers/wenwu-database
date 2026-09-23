# -*- coding: utf-8 -*-
"""Extract Hunan guobao item card structure."""
import re
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"}
req = urllib.request.Request("https://www.hnmuseum.com/zh-hans/guangcang_gauobao", headers=UA)
t = urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "replace")

items = re.findall(r'<a href="(/zh-hans/content/[^"]+)"[^>]*>(.*?)</a>', t, re.S)
print("items:", len(items))
for h, inner in items[:6]:
    inner_flat = re.sub(r"\s+", " ", inner)
    print(h)
    print("   inner:", ascii(inner_flat[:160]))
