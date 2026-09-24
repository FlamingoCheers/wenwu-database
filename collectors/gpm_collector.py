import io
import json
import os
import re
import sys
import time
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from collectors.dynasty_util import map_dynasty, map_category  # noqa: E402
from pipeline.dedup_cross import norm  # noqa: E402

BASE = "https://digicol.dpm.org.cn"
RE_DIR = r"E:\codingProject\52-文物数据库\data\relics"
KW_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "meta", "gpm_keywords.json")

CAT_MAP = {"绘画": "书画", "法书": "书画", "书法": "书画", "碑帖": "碑帖拓本", "陶瓷": "瓷器",
           "玉器": "玉器", "青铜器": "青铜器", "金银器": "金银器", "珐琅": "杂器", "漆器": "漆器",
           "织绣": "织绣", "雕塑": "雕塑", "雕刻工艺": "雕塑", "钟表仪器": "杂器",
           "生活用具": "杂器", "武备仪仗": "杂器", "宗教文物": "宗教造像", "帝后玺册": "文房用具",
           "古籍文献": "杂器", "古建藏品": "建筑构件", "其他工艺": "杂器",
           "其他文物": "杂器"}
SKIP_CATS = {"外国文物"}

JS_CARDS = """() => Array.from(document.querySelectorAll('.waterfall-item .img-container')).map(c => ({
  id: (c.id || '').replace('cultural-', ''),
  name: c.getAttribute('cultural-name') || '',
  number: c.getAttribute('cultural-number') || '',
  category: c.getAttribute('cultural-category') || '',
  dynasty: c.getAttribute('cultural-dynasty') || ''
}))"""


def harvest_keyword(pg, kw, sleep):
    url = BASE + "/list?k=" + urllib.parse.quote(kw)
    pg.goto(url, timeout=60000)
    try:
        pg.wait_for_selector(".waterfall-item .img-container", timeout=20000)
    except Exception:
        return []
    out = {}
    pages = 0
    while True:
        pg.wait_for_timeout(2500)
        cards = pg.evaluate(JS_CARDS)
        before = len(out)
        for c in cards:
            if c["id"] and c["name"]:
                out[c["id"]] = c
        pager = pg.query_selector(".page-next:not([disabled]), .pagination .next:not(.disabled), [class*=next]:not(.disabled)")
        clicked = False
        if pager and len(out) > before:
            try:
                pager.click()
                clicked = True
                pages += 1
                time.sleep(sleep)
            except Exception:
                pass
        if not clicked or pages > 8:
            break
        time.sleep(sleep)
        try:
            pg.wait_for_selector(".waterfall-item .img-container", timeout=15000)
        except Exception:
            break
    return list(out.values())


def main():
    limit = 0
    args = sys.argv[1:]
    if "--limit" in args:
        limit = int(args[args.index("--limit") + 1])
    kws = json.load(open(KW_FILE, encoding="utf-8"))
    npm_norm = set()
    for fn in os.listdir(RE_DIR):
        if fn.startswith("NPM-") and fn.endswith(".json"):
            d = json.load(open(os.path.join(RE_DIR, fn), encoding="utf-8"))
            npm_norm.add((norm(d.get("name")), d.get("category")))
    seen_ids = set()
    for fn in os.listdir(RE_DIR):
        if fn.startswith("GPM-") and fn.endswith(".json"):
            seen_ids.add(fn[4:-5])
    skipped = []
    made = 0
    state_path = r"E:\codingProject\52-文物数据库\raw\_gpm_kw_done.json"
    state = {}
    if os.path.exists(state_path):
        state = json.load(open(state_path, encoding="utf-8"))
    empty_streak = 0
    empty_marks = []
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        try:
            b = p.chromium.launch(channel="msedge", headless=True)
        except Exception:
            b = p.chromium.launch(headless=True)
        pg = b.new_page(viewport={"width": 1440, "height": 900})
        for kw in kws:
            if kw in state:
                continue
            cards = harvest_keyword(pg, kw, 2.0)
            for c in cards:
                if c["id"] in seen_ids:
                    continue
                if c["category"] in SKIP_CATS:
                    skipped.append({"kw": kw, "name": c["name"], "reason": "foreign-category"})
                    continue
                nm = norm(c["name"])
                cat = CAT_MAP.get(c["category"]) or map_category(c["category"]) or "杂器"
                if (nm, cat) in npm_norm:
                    skipped.append({"kw": kw, "name": c["name"], "reason": "npm-same-name"})
                    continue
                dyn, _ = map_dynasty(c["dynasty"], c["name"])
                rec = {
                    "relic_id": "GPM-" + c["id"],
                    "name": c["name"],
                    "aliases": [],
                    "dynasty": dyn,
                    "year_range": None,
                    "category": cat,
                    "material": None,
                    "dimensions": None,
                    "excavated_from": None,
                    "summary": "故宫博物院数字文物库著录：%s，%s%s，藏品编号 %s。" % (
                        c["name"], c["dynasty"] or "", c["category"] or "", c["number"]),
                    "history": None,
                    "interpretation": None,
                    "collection": {
                        "museum": "故宫博物院",
                        "region": "中国",
                        "inventory_no": c["number"] or None,
                    },
                    "images": [],
                    "source_url": BASE + "/cultural/detail?id=" + c["id"],
                    "license": "©故宫博物院",
                    "tags": [],
                    "related": [],
                    "raw_ref": None,
                    "needs_review": dyn == "不详",
                    "fetched_at": time.strftime("%Y-%m-%d"),
                    "updated_at": time.strftime("%Y-%m-%d"),
                }
                open(os.path.join(RE_DIR, rec["relic_id"] + ".json"), "w", encoding="utf-8").write(
                    json.dumps(rec, ensure_ascii=False, indent=1))
                seen_ids.add(c["id"])
                made += 1
            print(kw, "cards=%d made=%d total=%d skipped=%d" % (len(cards), made, made, len(skipped)), flush=True)
            state[kw] = len(cards)
            if cards:
                empty_marks = []
                empty_streak = 0
            else:
                empty_marks.append(kw)
                empty_streak += 1
                if empty_streak >= 6:
                    for k in empty_marks:
                        state.pop(k, None)
                    json.dump(state, open(state_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
                    print("ABORT: %d consecutive empty results, likely rate-limited. State saved." % empty_streak, flush=True)
                    break
            json.dump(state, open(state_path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            time.sleep(4.0)
        b.close()
    json.dump(skipped, open(r"E:\codingProject\52-文物数据库\raw\_gpm_skipped.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("DONE made=%d skipped=%d" % (made, len(skipped)))


if __name__ == "__main__":
    main()
