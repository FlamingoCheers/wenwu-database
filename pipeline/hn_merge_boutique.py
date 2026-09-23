# -*- coding: utf-8 -*-
"""Merge HN boutique pageIndex 1..N items into data/meta/hn_lists.json (static, polite)."""
import json
import pathlib
import re
import time
import urllib.request

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126 Safari/537.36",
      "Referer": "https://www.chnmus.net/"}
ITEM = re.compile(r'href="[^"]*content/redirect\?id=(\d+)"[^>]*>.*?<div class="cp-title">([^<]*)</div>', re.S)
LISTP = pathlib.Path("data/meta/hn_lists.json")


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode("utf-8", "replace")


def main():
    data = json.loads(LISTP.read_text(encoding="utf-8"))
    merged = dict(data.get("boutique", {}))
    added = 0
    for page in range(1, 6):
        url = f"https://www.chnmus.net/ch/collection/boutique/index.html?pageIndex={page}"
        t = get(url)
        for oid, name in ITEM.findall(t):
            name = name.strip()
            if oid not in merged:
                merged[oid] = name
                added += 1
        print("page", page, "cum", len(merged), "new", added)
        time.sleep(2.5)
    data["boutique"] = merged
    LISTP.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    total = sum(len(v) for v in data.values())
    print("total list size", total)


if __name__ == "__main__":
    main()
