# -*- coding: utf-8 -*-
"""Try Capital/Canal museum collectionlist API (few polite probes)."""
import json
import time
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
      "Content-Type": "application/json",
      "Referer": "https://www.capitalmuseum.org.cn/collection",
      "Origin": "https://www.capitalmuseum.org.cn"}
BASE = "https://m.canalmuseum.org.cn"

bodies = [
    ("/prod-api/collectionlist", {"page": 1, "pageSize": 10}),
    ("/api/collectionlist", {"pageNo": 1, "pageSize": 10}),
    ("/collectionlist", {"page": 1}),
]
for path, body in bodies:
    url = BASE + path
    for method in ("POST", "GET"):
        try:
            if method == "POST":
                req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=UA, method="POST")
            else:
                req = urllib.request.Request(url + "?page=1&pageSize=10", headers=UA)
            with urllib.request.urlopen(req, timeout=15) as r:
                print(method, url, r.status, ascii(r.read(300).decode("utf-8", "replace")[:280]))
                break
        except Exception as e:
            print(method, url, "ERR", repr(e)[:80])
        time.sleep(2)
