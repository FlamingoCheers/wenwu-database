# -*- coding: utf-8 -*-
"""Probe 10 provincial/municipal museum sites for collection sections.

Politeness: 2-3 requests per site max, single-threaded, 2s between requests,
15s timeouts, failures tolerated and reported. Saves sample HTML under
raw/probe_prov/ and prints a compact report.
"""
import json, pathlib, re, time, urllib.request

ROOT = pathlib.Path(".")
RAW = ROOT / "raw/probe_prov"
RAW.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

SITES = {
    "湖南博物院": "https://www.hnmuseum.com/",
    "辽宁省博物馆": "https://www.lnmuseum.com.cn/",
    "南京博物院": "https://www.njmuseum.com/",
    "山西博物院": "https://www.shanximuseum.com/",
    "浙江省博物馆": "https://www.zhejiangmuseum.com/",
    "天津博物馆": "https://www.tjbwg.com/",
    "河南博物院": "http://www.chnmus.net/",
    "湖北省博物馆": "https://www.hbww.org/",
    "上海博物馆": "https://www.shanghaimuseum.net/",
    "首都博物馆": "https://www.capitalmuseum.org.cn/",
}
NAV_RE = re.compile(
    r'<a[^>]*href="([^"]*)"[^>]*>\s*([^<]{2,16})\s*</a>', re.S)
KEY = re.compile(r"藏|典藏|精品|文物|collection|Collection|Collections")

report = {}


def get(url, timeout=15):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "ignore")


for name, home in SITES.items():
    rep = {"home": home}
    try:
        t = get(home)
        rep["home_len"] = len(t)
        links = []
        for m in NAV_RE.finditer(t):
            href, txt = m.group(1).strip(), re.sub(r"\s+", "", m.group(2))
            if KEY.search(txt) and href not in ("#", "javascript:void(0);", ""):
                links.append((href, txt))
        seen, uniq = set(), []
        for h, txt in links:
            if h not in seen:
                seen.add(h)
                uniq.append((h, txt))
        rep["nav"] = uniq[:8]
        # fetch the most promising collection page
        pick = None
        for h, txt in uniq:
            if ("藏" in txt or "collection" in h.lower()) and not h.startswith("http"):
                pick = h
                break
        for h, txt in uniq:
            if not pick and h.startswith("http") and ("藏" in txt):
                pick = h
                break
        if pick:
            url = pick if pick.startswith("http") else home.rstrip("/") + pick
            rep["collection_url"] = url
            try:
                c = get(url)
                rep["coll_len"] = len(c)
                (RAW / f"{name}.html").write_text(c, encoding="utf-8")
                # static item signals
                rep["detail_links"] = len(set(re.findall(
                    r'href="([^"]*(?:detail|collection|c/?\d+|view|ww|wuwu|relic)[^"]*)"', c, re.I)))
                rep["imgs"] = len(re.findall(r"<img", c))
                rep["js_suspicion"] = "ListItem" in c or "__NEXT" in c or "vue" in c.lower() or len(c) < 15000
            except Exception as e:
                rep["coll_err"] = repr(e)[:90]
        time.sleep(2)
    except Exception as e:
        rep["home_err"] = repr(e)[:90]
    report[name] = rep
    print(name, "->", json.dumps({k: v for k, v in rep.items() if k != "nav"},
                                 ensure_ascii=False)[:220])
    if rep.get("nav"):
        print("   nav:", rep["nav"][:6])

(ROOT / "raw/probe_prov/report.json").write_text(
    json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
print("saved raw/probe_prov/report.json")
