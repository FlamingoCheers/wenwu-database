# -*- coding: utf-8 -*-
"""Hunan detail: strip style/script then locate description fields."""
import re
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"}
url = "https://www.hnmuseum.com/zh-hans/content/%E5%A4%A7-%E7%A6%BE-%E4%BA%BA-%E9%9D%A2-%E7%BA%B9-%E6%96%B9-%E9%BC%8E"
req = urllib.request.Request(url, headers=UA)
t = urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "replace")
t = re.sub(r"<(style|script)[^>]*>.*?</\1>", " ", t, flags=re.S)

for kw in ("年代", "时代", "质地", "尺寸", "来源", "藏品介绍", "说明", "商代"):
    for m in re.finditer(kw, t):
        s = max(0, m.start() - 120)
        seg = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t[s:m.start() + 260]))
        print(kw, "=>", ascii(seg[:220]))
        break
