# -*- coding: utf-8 -*-
"""Provincial museum probe (runs on GitHub Actions).

Goals, politely (3s sleep, browser UA, few requests per site):
  1. Reachability: shanxi / zhejiang / hubei / tianjin (tianjin DNS failed locally).
  2. Capital Museum: collect _nuxt chunk URLs recursively (entry -> dynamic imports),
     grep JS for API endpoint paths (m.canalmuseum.org.cn).
  3. Hunan de.hnmuseum.com: same bundle-grep for its API.
Output: raw/probe2/report.json + raw HTML/JS samples; workflow uploads artifact.
"""
import json
import pathlib
import re
import time
import urllib.request

OUT = pathlib.Path("raw/probe2")
OUT.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
      "Accept-Language": "zh-CN,zh;q=0.9"}
report = {}


def get(url, timeout=25, save=None):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read()
    if save:
        (OUT / save).write_bytes(raw)
    return raw.decode("utf-8", "replace")


def probe(name, fn):
    try:
        report[name] = fn()
    except Exception as e:
        report[name] = {"error": repr(e)[:200]}
    print(name, "->", json.dumps(report[name], ensure_ascii=False)[:220])
    time.sleep(3)


def reach(url, tag):
    def fn():
        t = get(url, save=f"{tag}.html")
        hrefs = sorted(set(re.findall(r'href="([^"]+)"', t)))
        srcs = sorted(set(re.findall(r'src="([^"]+\.js[^"]*)"', t)))
        return {"len": len(t), "title": (re.search(r"<title>([^<]*)", t) or [None, "?"])[1],
                "href_sample": [h for h in hrefs if not h.startswith(("#", "javascript"))][:15],
                "js": srcs[:15]}
    return fn


def bundle_grep(entry_url, tag, patterns, max_bundles=12, depth=1):
    """Fetch entry html/js, recursively grep bundles for endpoint-ish strings."""
    seen = {}
    queue = [(entry_url, 0)]
    hits = set()
    idx = 0
    while queue and len(seen) < max_bundles:
        url, d = queue.pop(0)
        if url in seen:
            continue
        try:
            body = get(url, save=f"{tag}_js{idx}.txt")
        except Exception as e:
            seen[url] = f"ERR {e!r:.60}"
            continue
        seen[url] = len(body)
        idx += 1
        for pat in patterns:
            for m in re.findall(pat, body):
                if isinstance(m, tuple):
                    m = m[0]
                if m and len(m) < 120:
                    hits.add(m)
        if d < depth:
            queue += [(u, d + 1) for u in sorted(set(re.findall(r'["\'](/[^"\']+\.js)["\']', body)))[:10]]
        time.sleep(2.5)
    return {"fetched": len(seen), "hits": sorted(hits)[:40]}


ENDPOINT_PAT = [
    r'["\']((?:/[a-zA-Z0-9_\-./]+)?/(?:api|prod-api|gateway|interface)[a-zA-Z0-9_\-./]*)["\']',
    r'["\']([a-zA-Z0-9_\-./]*(?:collection|relic|cangpin|antique|collect|List|list|detail)[a-zA-Z0-9_\-./]*)["\']',
    r'https?://[a-zA-Z0-9.\-]+\.(?:org|cn|com|net)[a-zA-Z0-9_\-./]*(?:api|collection)[a-zA-Z0-9_\-./]*',
]


def capital():
    t = get("https://www.capitalmuseum.org.cn/collection", save="capital.html")
    entry = sorted(set(re.findall(r'src="(/_nuxt/[^"]+\.js)"', t)))
    hits = set()
    for e in entry[:3]:
        r = bundle_grep("https://www.capitalmuseum.org.cn" + e, "cap", ENDPOINT_PAT, max_bundles=10)
        hits |= set(r["hits"])
    # find relic detail hrefs too
    ids = sorted(set(re.findall(r'/collection/([0-9a-f]{32})', t)))
    return {"entry": entry, "endpoint_hits": sorted(hits)[:40], "detail_ids_on_page": ids[:12]}


def hunan_de():
    t = get("https://de.hnmuseum.com/collection/", save="hunan_de.html")
    srcs = sorted(set(re.findall(r'(?:src=|href=)["\']?([^"\']+\.js[^"\']*)', t)))
    full = [s if s.startswith("http") else "https://de.hnmuseum.com" + ("" if s.startswith("/") else "/") + s for s in srcs]
    hits = set()
    for u in full[:3]:
        r = bundle_grep(u, "hun", ENDPOINT_PAT, max_bundles=8)
        hits |= set(r["hits"])
    return {"js": srcs[:12], "endpoint_hits": sorted(hits)[:40]}


probe("shanxi", reach("https://www.shanximuseum.com/sx/collection/collection.html", "shanxi"))
probe("zhejiang", reach("https://www.zhejiangmuseum.com/", "zhejiang"))
probe("hubei", reach("https://www.hbww.org/", "hubei"))
probe("tianjin", reach("https://tjbwg.com/", "tianjin"))
probe("tianjin_www", reach("https://www.tjbwg.com/", "tianjin_www"))
probe("capital", capital)
probe("hunan_de", hunan_de)

(OUT / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
print("report written")
