# -*- coding: utf-8 -*-
"""Fetch one Henan detail page + list page to design the collector."""
import pathlib, re, urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
RAW = pathlib.Path("raw/probe_prov")

t = (RAW / "r2_河南博物院_藏品精粹.html").read_text(encoding="utf-8")
links = list(dict.fromkeys(re.findall(r'href="([^"]*(?:detail|view|art|item|relic)[^"]*)"', t, re.I)))
print("sample links:", links[:6])

url = links[0]
if url.startswith("//"):
    url = "http:" + url
elif url.startswith("/"):
    url = "http://www.chnmus.net" + url
print("fetch:", url)
req = urllib.request.Request(url, headers=UA)
d = urllib.request.urlopen(req, timeout=18).read().decode("utf-8", "ignore")
(RAW / "hn_detail_sample.html").write_text(d, encoding="utf-8")
print("len", len(d))
body = re.sub(r"<script.*?</script>|<style.*?</style>", "", d, flags=re.S)
text = re.sub(r"<[^>]+>", " ", body)
text = re.sub(r"\s+", " ", text)
i = text.find("年代")
if i < 0:
    i = text.find("时代")
print("TEXT:", text[max(0, i - 150):i + 500])
