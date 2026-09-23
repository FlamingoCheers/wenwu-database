# -*- coding: utf-8 -*-
"""Capital Museum probe round 3: real browser load + XHR capture (1 page load, polite)."""
import json
import pathlib

from playwright.sync_api import sync_playwright

OUT = pathlib.Path("raw/probe4")
OUT.mkdir(parents=True, exist_ok=True)
captured = []

with sync_playwright() as pw:
    b = pw.chromium.launch(headless=True)
    pg = b.new_page(viewport={"width": 1380, "height": 900})

    def on_response(resp):
        u = resp.url
        if "canalmuseum" in u or ("/api" in u and "capitalmuseum" in u):
            body = ""
            try:
                body = resp.text()[:1500]
            except Exception:
                pass
            captured.append({"url": u, "status": resp.status,
                             "method": resp.request.method,
                             "post": resp.request.post_data,
                             "body_head": body})

    pg.on("response", on_response)
    pg.goto("https://www.capitalmuseum.org.cn/collection", wait_until="networkidle", timeout=60000)
    pg.wait_for_timeout(6000)
    # click through pagination once if present (still same page, client-side)
    try:
        pg.mouse.wheel(0, 3000)
        pg.wait_for_timeout(4000)
    except Exception:
        pass
    b.close()

(OUT / "xhr.json").write_text(json.dumps(captured, ensure_ascii=False, indent=1), encoding="utf-8")
print("captured:", len(captured))
for c in captured[:12]:
    print(json.dumps(c, ensure_ascii=False)[:280])
