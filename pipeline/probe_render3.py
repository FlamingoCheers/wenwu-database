# -*- coding: utf-8 -*-
"""Render JS-heavy museum list pages via playwright/Edge, dump HTML for offline selector analysis.

Museums: hunan guobao, capital /collection, shanxi collection. Polite: one page each, waits for network idle.
"""
import pathlib
import time

from playwright.sync_api import sync_playwright

OUT = pathlib.Path("raw/probe_prov")
TARGETS = [
    ("hunan_guobao", "https://www.hnmuseum.com/zh-hans/guangcang_gauobao"),
    ("capital_collection", "https://www.capitalmuseum.org.cn/collection"),
    ("shanxi_collection", "https://www.shanximuseum.com/sx/collection/collection.html"),
]

with sync_playwright() as pw:
    browser = pw.chromium.launch(channel="msedge", headless=True)
    pg = browser.new_page(viewport={"width": 1380, "height": 900})
    for tag, url in TARGETS:
        try:
            pg.goto(url, wait_until="networkidle", timeout=45000)
            time.sleep(3)
            pg.mouse.wheel(0, 4000)
            time.sleep(2)
            html = pg.content()
            (OUT / f"rendered_{tag}.html").write_text(html, encoding="utf-8")
            print(tag, "saved", len(html))
        except Exception as e:
            print(tag, "ERR", repr(e)[:120])
        time.sleep(3)
    browser.close()
