# -*- coding: utf-8 -*-
"""Round 2: precise collection-page probes."""
import pathlib, re, time, urllib.request

RAW = pathlib.Path("raw/probe_prov")
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

TARGETS = {
    "河南博物院_藏品精粹": "http://www.chnmus.net/ch/collection/boutique/index.html",
    "河南博物院_中原藏珍": "http://www.chnmus.net/ch/collection/centralPlains/index.html",
    "湖南_馆藏国宝": "https://www.hnmuseum.com/zh-hans/guangcang_gauobao",
    "湖南_藏品数据库": "https://de.hnmuseum.com/collection/",
    "山西_藏品列表": "https://www.shanximuseum.com/sx/collection/collection.html",
    "上海_典藏精品": "https://www.shanghaimuseum.net/frontend/pg/collection/antique",
    "上海_数字文物库": "https://www.shanghaimuseum.net/frontend/pg/lib1/index",
    "首都博物馆_典藏": "https://www.capitalmuseum.org.cn/collection",
    "浙江省博物馆": "https://www.zhejiangmuseum.com/",
    "湖北省博物馆": "https://www.hbww.org/",
    "天津博物馆": "https://www.tjbwg.com/",
}

def get(url, timeout=18):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8", "ignore")

for name, url in TARGETS.items():
    try:
        t = get(url)
        details = len(set(re.findall(r'href="([^"]*(?:detail|view|art|item|relic|ww|pg/collection)[^"]*)"', t, re.I)))
        imgs = len(re.findall(r"<img", t))
        titles = re.findall(r'title="([^"]{4,30})"', t)[:6]
        print(f"{name}: len={len(t)} details={details} imgs={imgs} js={len(t)<15000} titles={titles}")
        (RAW / f"r2_{name}.html").write_text(t, encoding="utf-8")
    except Exception as e:
        print(f"{name}: ERR {repr(e)[:100]}")
    time.sleep(2)
