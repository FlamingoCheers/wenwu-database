# -*- coding: utf-8 -*-
"""Probe Capital Museum + Hunan Museum list structures (few polite requests)."""
import re
import sys
import time
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
      "Accept-Language": "zh-CN,zh;q=0.9"}


def get(url, timeout=25):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def links(html, pat):
    return re.findall(pat, html)


def main():
    out = []
    # 1) Capital Museum collection hub
    try:
        t = get("https://www.capitalmuseum.org.cn/collection.htm")
        out.append(("capital /collection.htm len", len(t)))
        hrefs = sorted(set(re.findall(r'href="([^"]+)"', t)))
        out.append(("capital hrefs sample", [h for h in hrefs if any(k in h for k in ("zp", "collection", "cang", "digital", "list"))][:20]))
    except Exception as e:
        out.append(("capital ERR", repr(e)[:120]))
    time.sleep(2)
    # 2) Hunan guangcang_gauobao page 2 (pagination form?)
    try:
        t = get("https://www.hnmuseum.com/deht/zl/jbgl_index_2.shtml")
        out.append(("hunan jbgl p2 len", len(t)))
        items = re.findall(r'<a[^>]+href="([^"]+)"[^>]*>([^<]{2,40})</a>', t)
        out.append(("hunan p2 items", [i for i in items if "shtml" in i[0]][:10]))
    except Exception as e:
        out.append(("hunan ERR", repr(e)[:120]))
    for k, v in out:
        print(k, "=>", ascii(v) if isinstance(v, str) else v)


if __name__ == "__main__":
    sys.exit(main())
