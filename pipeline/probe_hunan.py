# -*- coding: utf-8 -*-
"""Probe Hunan Museum static list pages (guangcang_gauobao pagination + zhuti_shoucang)."""
import re
import time
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
      "Accept-Language": "zh-CN,zh;q=0.9"}


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode("utf-8", "replace")


def show(tag, t):
    print(tag, "len", len(t))
    # candidate item links
    hs = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>\s*(?:<[^>]+>\s*)*([^<]{2,50})', t)
    cand = [(h, n.strip()) for h, n in hs if re.search(r"(detail|cang|gauobao|shoucang|pin|wu)", h) and not h.startswith(("http", "/en", "/fr", "/ja", "/ko"))]
    for h, n in cand[:8]:
        print("   ", h, "|", ascii(n[:20]))
    pages = re.findall(r"[?&]page=(\d+)", t)
    print("   page links:", sorted(set(pages))[:12], "max:", max(pages) if pages else "-")


for tag, url in (
    ("guobao p1", "https://www.hnmuseum.com/zh-hans/guangcang_gauobao"),
    ("guobao p2", "https://www.hnmuseum.com/zh-hans/guangcang_gauobao?s=/zh-hans/guangcang_gauobao&page=2"),
    ("zhuti p1", "https://www.hnmuseum.com/zh-hans/zhuti_shoucang"),
):
    try:
        show(tag, get(url))
    except Exception as e:
        print(tag, "ERR", repr(e)[:100])
    time.sleep(2.5)
