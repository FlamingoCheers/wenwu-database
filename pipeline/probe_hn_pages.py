# -*- coding: utf-8 -*-
"""Probe HN pageIndex pagination on all 5 columns (polite, 1 page each)."""
import re
import time
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
      "Referer": "https://www.chnmus.net/"}


def get(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


for col in ("treasure", "boutique", "centralPlains", "digital", "appraise"):
    url = f"https://www.chnmus.net/ch/collection/{col}/index.html?pageIndex=2"
    try:
        t = get(url)
        items = re.findall(r'href="[^"]*content/redirect\?id=(\d+)"[^>]*>.*?<div class="cp-title">([^<]*)</div>',
                           t, re.S)
        # also last page hint
        pages = re.findall(r'pageIndex=(\d+)', t)
        print(col, "p2 items:", len(items), "max pageIndex seen:", max(pages) if pages else "-", ascii(items[:2]))
    except Exception as e:
        print(col, "ERR", repr(e)[:100])
    time.sleep(2.5)
