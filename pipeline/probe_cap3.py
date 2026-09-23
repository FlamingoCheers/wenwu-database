# -*- coding: utf-8 -*-
"""Extract Capital Museum apiBase and try the collection list endpoint (2 polite probes)."""
import json
import pathlib
import re
import time
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
      "Referer": "https://www.capitalmuseum.org.cn/collection"}

t = (pathlib.Path("raw/probe_prov") / "rendered_capital_collection.html").read_text(encoding="utf-8", errors="ignore")
m = re.search(r"apiBase:'([^']+)'", t)
print("apiBase:", m.group(1) if m else "NOT FOUND")
base = m.group(1) if m else ""

# collectionlist context
i = t.find("collectionlist")
print("ctx:", ascii(t[max(0, i - 200):i + 120].replace("\n", " ")) if i >= 0 else "-")

if base:
    for path in ("/collectionlist", "/api/collectionlist", "/collection/list"):
        url = base.rstrip("/") + path
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=20) as r:
                body = r.read(2000).decode("utf-8", "replace")
            print("GET", url, "->", r.status, ascii(body[:200]))
        except Exception as e:
            print("GET", url, "ERR", repr(e)[:90])
        time.sleep(2.5)
