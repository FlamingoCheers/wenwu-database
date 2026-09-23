# -*- coding: utf-8 -*-
"""Capital Museum probe round 2 (Actions): m.canalmuseum reachability + deeper bundle grep."""
import json
import pathlib
import re
import time
import urllib.request

OUT = pathlib.Path("raw/probe3")
OUT.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36",
      "Accept-Language": "zh-CN,zh;q=0.9", "Referer": "https://www.capitalmuseum.org.cn/collection"}
report = {}


def get(url, timeout=25, save=None):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    if save:
        (OUT / save).write_bytes(raw)
    return raw.decode("utf-8", "replace")


# 1) is the API host reachable at all?
for u in ("https://m.canalmuseum.org.cn/", "https://m.canalmuseum.org.cn/prod-api/"):
    try:
        body = get(u, save=f"canal_{u.count('/')}.html")
        report[f"reach {u}"] = {"len": len(body), "head": body[:200]}
    except Exception as e:
        report[f"reach {u}"] = {"error": repr(e)[:150]}
    time.sleep(3)
    print("reach", u, json.dumps(report[f"reach {u}"], ensure_ascii=False)[:200])

# 2) deeper bundle crawl from the collection page entry chunks
patterns = [
    r'https?://m\.canalmuseum\.org\.cn[a-zA-Z0-9_\-./]*',
    r'["\'](/(?:prod-)?api/[a-zA-Z0-9_\-./]+)["\']',
    r'["\']([a-zA-Z0-9_\-./]*(?:Collection|collection)[a-zA-Z0-9_\-]*/[a-zA-Z0-9_\-./]+)["\']',
    r'baseURL[^,;]{0,80}',
    r'["\']([a-zA-Z0-9_\-./]+\.(?:json|do|action))["\']',
]
seen = set()
hits = set()
queue = []
t0 = get("https://www.capitalmuseum.org.cn/collection", save="cap.html")
queue += ["https://www.capitalmuseum.org.cn" + u for u in sorted(set(re.findall(r'src="(/_nuxt/[^"]+\.js)"', t0)))]
# dynamic import chunk names listed inside entry bundles
idx = 0
while queue and len(seen) < 24:
    url = queue.pop(0)
    if url in seen:
        continue
    seen.add(url)
    try:
        body = get(url, save=f"cap_js{idx}.txt")
    except Exception as e:
        report[f"js {url}"] = repr(e)[:80]
        continue
    idx += 1
    for pat in patterns:
        for m in re.findall(pat, body):
            if isinstance(m, tuple):
                m = next((x for x in m if x), None)
            if m and len(m) < 130:
                hits.add(m)
    queue += ["https://www.capitalmuseum.org.cn" + u for u in sorted(set(re.findall(r'["\'](/_nuxt/[a-zA-Z0-9_.\-]+\.js)["\']', body))) if u not in seen]
    time.sleep(2.5)

report["bundles_fetched"] = len(seen)
report["hits"] = sorted(hits)[:60]
(OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
print("HITS:")
for h in sorted(hits)[:60]:
    print("  ", h)
