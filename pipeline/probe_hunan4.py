# -*- coding: utf-8 -*-
"""Dump markup around Hunan guobao item images."""
import pathlib
import re

t = (pathlib.Path("raw/probe_prov") / "rendered_hunan_guobao.html").read_text(encoding="utf-8", errors="ignore")
i = t.find("大禾人面纹方鼎")
print("title-idx:", i)
if i < 0:
    # decode from url
    m = re.search(r"src=\"([^\"]*%E5%A4%A7%E7%A6%BE[^\"]*)\"", t)
    print("img:", m.group(1) if m else None)
    i = m.start() if m else 0
seg = t[max(0, i - 700):i + 700]
print(re.sub(r"\s+", " ", seg)[:1400])
