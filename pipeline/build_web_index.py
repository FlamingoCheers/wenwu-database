# -*- coding: utf-8 -*-
"""构建检索前端索引：data/relics/*.json -> web/data/index.json(.gz)

纯 stdlib。字段裁剪 + 分面统计（搜索 blob 由前端现拼，减小索引体积）。
产出两份：gz（浏览器 DecompressionStream 解压）与明文（兜底）。
web/data/ 已 gitignore，由 Pages 部署时现构建。
"""
import gzip
import json
import pathlib
import sys
from datetime import date

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "web" / "data"

# 朝代展示顺序（canonical order），数据中的短键直接匹配
DYN_ORDER = ["新石器时代", "夏", "商", "西周", "春秋", "战国", "秦", "汉", "三国",
             "两晋", "南北朝", "隋", "唐", "五代十国", "宋", "辽", "西夏", "金",
             "元", "明", "清", "民国", "现代", "不详"]
MUSEUM_SHORT = {"MET": "Met", "CLE": "CLE"}


def build():
    items = []
    museums = {}
    dyn_counts, cat_counts = {}, {}

    for f in sorted((ROOT / "data" / "relics").glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            print("skip %s: %s" % (f.name, e), file=sys.stderr)
            continue
        imgs = [i for i in d.get("images", []) if i.get("url")]
        col = d.get("collection", {}) or {}
        rid = d.get("relic_id", "")
        code = rid.split("-", 1)[0]
        mu = col.get("museum") or code
        museums[code] = mu
        dyn = d.get("dynasty") or "不详"
        cat = d.get("category") or "其他"
        yr = d.get("year_range") or [None, None]
        tags = (d.get("tags") or [])[:4]
        aliases = (d.get("aliases") or [])[:3]
        it = {
            "id": rid,
            "name": d.get("name") or "",
            "alias": "、".join(aliases),
            "dyn": dyn,
            "y0": yr[0],
            "y1": yr[1],
            "cat": cat,
            "mat": d.get("material") or "",
            "dim": (d.get("dimensions") or "")[:60],
            "mu": mu,
            "code": code,
            "inv": col.get("inventory_no") or "",
            "desc": (d.get("summary") or "")[:110],
            "img": imgs[0]["url"] if imgs else "",
            "url": d.get("source_url") or "",
            "lic": "%s · %s" % (d.get("license", ""), col.get("museum") or ""),
            "tags": tags,
        }
        items.append(it)
        dyn_counts[dyn] = dyn_counts.get(dyn, 0) + 1
        cat_counts[cat] = cat_counts.get(cat, 0) + 1

    def facet_order(counts, order):
        known = [(k, counts[k]) for k in order if k in counts]
        extra = sorted((k, c) for k, c in counts.items() if k not in order)
        return [{"k": k, "c": c} for k, c in known + extra]

    index = {
        "v": 1,
        "generated": str(date.today()),
        "total": len(items),
        "museums": museums,
        "facets": {
            "dynasties": facet_order(dyn_counts, DYN_ORDER),
            "cats": [{"k": k, "c": c} for k, c in
                     sorted(cat_counts.items(), key=lambda kv: -kv[1])],
        },
        "items": items,
    }

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(index, ensure_ascii=False, separators=(",", ":"))
    (OUT_DIR / "index.json").write_text(raw, encoding="utf-8")
    with open(OUT_DIR / "index.json.gz", "wb") as fh:
        fh.write(gzip.compress(raw.encode("utf-8"), 9))
    kb = len(raw.encode("utf-8")) / 1024
    kbgz = (OUT_DIR / "index.json.gz").stat().st_size / 1024
    print("total=%d museums=%d dynasties=%d categories=%d" %
          (len(items), len(museums), len(dyn_counts), len(cat_counts)))
    print("index.json %.0f KB / gz %.0f KB -> %s" % (kb, kbgz, OUT_DIR))


if __name__ == "__main__":
    build()
