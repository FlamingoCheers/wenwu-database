# -*- coding: utf-8 -*-
"""Harvest Henan Museum list pages (all columns) via headless Edge.

Writes data/meta/hn_lists.json: {col: [[oid, name], ...]}
Politeness: 5 columns, sequential, scroll-driven (no API digging).
"""
import json, pathlib, re, time
from playwright.sync_api import sync_playwright

COLS = {
    "treasure": "https://www.chnmus.net/ch/collection/treasure/index.html",
    "boutique": "https://www.chnmus.net/ch/collection/boutique/index.html",
    "centralPlains": "https://www.chnmus.net/ch/collection/centralPlains/index.html",
    "digital": "https://www.chnmus.net/ch/collection/digital/index.html",
    "appraise": "https://www.chnmus.net/ch/collection/appraise/index.html",
}
OUT = pathlib.Path("data/meta/hn_lists.json")
OUT.parent.mkdir(parents=True, exist_ok=True)
CAP = 600

def harvest(pg, url):
    pg.goto(url, timeout=45000, wait_until="domcontentloaded")
    pg.wait_for_timeout(4000)
    seen, stable = {}, 0
    for _ in range(40):
        boxes = pg.locator('a[href*="content/redirect?id="]')
        n = boxes.count()
        for i in range(n):
            try:
                href = boxes.nth(i).get_attribute("href") or ""
                m = re.search(r"[?&]id=(\d+)", href)
                if not m:
                    continue
                oid = m.group(1)
                if oid not in seen:
                    t = boxes.nth(i).inner_text(timeout=2000)
                    t = re.sub(r"\s+", " ", t).strip()
                    seen[oid] = t
            except Exception:
                continue
        # try load-more / scroll
        clicked = False
        for sel in ["text=加载更多", "text=点击加载更多", "text=查看更多", ".load-more", "[class*=more]"]:
            try:
                loc = pg.locator(sel).first
                if loc.is_visible(timeout=800):
                    loc.scroll_into_view_if_needed(timeout=2000)
                    loc.click(timeout=2000)
                    clicked = True
                    pg.wait_for_timeout(2500)
                    break
            except Exception:
                continue
        pg.mouse.wheel(0, 20000)
        pg.wait_for_timeout(1800)
        if len(seen) >= CAP:
            break
        if len(seen) == stable and not clicked:
            stable += 1
            if stable >= 3:
                break
        else:
            stable = len(seen)
    return seen

lists = {}
with sync_playwright() as p:
    b = p.chromium.launch(headless=True, channel="msedge")
    pg = b.new_page(user_agent="Mozilla/5.0")
    for col, url in COLS.items():
        t0 = time.time()
        lists[col] = harvest(pg, url)
        print(col, len(lists[col]), f"{time.time()-t0:.0f}s")
        pg.wait_for_timeout(3000)
    b.close()

OUT.write_text(json.dumps(lists, ensure_ascii=False, indent=1), encoding="utf-8")
total = sum(len(v) for v in lists.values())
print("TOTAL", total, "->", OUT)
