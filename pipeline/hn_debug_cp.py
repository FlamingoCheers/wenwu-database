# -*- coding: utf-8 -*-
"""Debug: dump centralPlains rendered markup to find item selectors."""
import pathlib, re
from playwright.sync_api import sync_playwright

out = pathlib.Path("raw/probe_prov")
with sync_playwright() as p:
    b = p.chromium.launch(headless=True, channel="msedge")
    pg = b.new_page(user_agent="Mozilla/5.0")
    pg.goto("https://www.chnmus.net/ch/collection/centralPlains/index.html",
            timeout=45000, wait_until="domcontentloaded")
    pg.wait_for_timeout(8000)
    html = pg.content()
    (out / "hn_cp_rendered.html").write_text(html, encoding="utf-8")
    print("len", len(html))
    b.close()

ids = re.findall(r'id=(\d{15,})', html)
print("snowflake ids:", len(set(ids)), list(dict.fromkeys(ids))[:5])
for m in list(re.finditer(r'id=\d{15,}', html))[:2]:
    s = max(0, m.start() - 350)
    print("---", re.sub(r"\s+", " ", html[s:m.start() + 250])[:520])
