# -*- coding: utf-8 -*-
"""Fetch one Hunan guobao detail page and dump field structure."""
import re
import time
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"}

url = "https://www.hnmuseum.com/zh-hans/content/%E5%A4%A7-%E7%A6%BE-%E4%BA%BA-%E9%9D%A2-%E7%BA%B9-%E6%96%B9-%E9%BC%8E"
req = urllib.request.Request(url, headers=UA)
t = urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "replace")
print("len", len(t))

# main content region
m = re.search(r'<div class="region region-content">(.*?)</article>', t, re.S) or re.search(r"<article.*?>(.*)</article>", t, re.S)
seg = m.group(1) if m else t
flat = re.sub(r"<[^>]+>", "|", seg)
flat = re.sub(r"\|+", "|", flat)
flat = re.sub(r"\s+", " ", flat)
i = flat.find("大禾")
print("FLAT:", ascii(flat[max(0, i - 60):i + 900]))

img = re.findall(r'src="(https://www\.hnmuseum\.com/sites/default/files/[^"]+)"', t)
print("IMGS:", [u.rsplit("/", 1)[-1][:40] for u in img[:4]])
