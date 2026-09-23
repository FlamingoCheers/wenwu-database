# -*- coding: utf-8 -*-
"""Grep Capital Museum Nuxt bundles for the collection API path (static files, browser-equivalent)."""
import re
import time
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36"}

page = open("raw/probe_prov/rendered_capital_collection.html", encoding="utf-8", errors="ignore").read()
bundles = sorted(set(re.findall(r'src="(/_nuxt/[^"]+\.js)"', page)))
print("bundles:", len(bundles))

for b in bundles[:8]:
    url = "https://www.capitalmuseum.org.cn" + b
    try:
        req = urllib.request.Request(url, headers=UA)
        js = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "replace")
        hits = set(re.findall(r'["\']([^"\']*(?:collection|list|detail)[^"\']*)["\']', js))
        api = [h for h in hits if h.startswith(("/", "http")) and len(h) < 80]
        if api:
            print(b, len(js))
            for h in sorted(api)[:10]:
                print("   ", h)
    except Exception as e:
        print(b, "ERR", repr(e)[:70])
    time.sleep(1.5)
