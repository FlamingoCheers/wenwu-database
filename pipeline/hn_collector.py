# -*- coding: utf-8 -*-
"""Henan Museum collector: static detail fetch from curated lists.

List source: data/meta/hn_lists.json (harvested via playwright, committed).
Details: server-rendered attributes (name/type/era); description not published.
Politeness: single-thread, --sleep default 2.0, cap per run.
Output: data/relics/HN-{oid}.json (caches raw/hn/detail_{oid}.html)
"""
import argparse, json, pathlib, re, sys, time, urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
RAW = ROOT / "raw/hn"
LISTS = ROOT / "data/meta/hn_lists.json"
UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
BASE = "https://www.chnmus.net"
TODAY = time.strftime("%Y-%m-%d")
# 联合特展的合作馆介绍页（国博/故宫/上博…）不是藏品，直接跳过
INST_RE = re.compile(r"(博物馆|博物院|纪念馆|美术馆)$|(国家博物馆|故宫博物院)$")

sys.path.insert(0, str(ROOT / "collectors"))
from dynasty_util import map_dynasty, map_tags  # noqa: E402

CAT_MAP = {
    "瓷器": "瓷器", "陶器": "陶器", "青铜": "青铜器", "玉": "玉器", "玉石": "玉器",
    "金银": "金银器", "书法": "书画", "绘画": "书画", "壁画": "书画", "拓本": "碑帖拓本",
    "雕塑": "雕塑", "造像": "宗教造像", "骨器": "甲骨", "甲骨": "甲骨", "钱币": "钱币",
    "货币": "钱币", "漆器": "漆器", "织绣": "织绣", "服饰": "织绣", "玻璃": "玻璃器",
    "珐琅": "珐琅", "家具": "家具", "石刻": "石刻", "砖瓦": "建筑构件", "杂项": "杂器",
    "其他": "杂器",
}


def fetch(oid, sleep):
    dst = RAW / f"detail_{oid}.html"
    if dst.exists():
        return dst.read_text(encoding="utf-8")
    url = f"{BASE}/ch/collection/boutique/details.html?id={oid}"
    req = urllib.request.Request(url, headers=UA)
    t = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")
    RAW.mkdir(parents=True, exist_ok=True)
    dst.write_text(t, encoding="utf-8")
    time.sleep(sleep)
    return t


def parse(t):
    m = re.search(r"<title>\s*([^_<]+?)\s*[-_＿]", t)
    name = m.group(1).strip() if m else ""
    attrs = {}
    for m in re.finditer(r'attribute-item[^>]*>\s*([^:：]+)[:：]\s*([^<]+)<', t):
        attrs[m.group(1).strip()] = re.sub(r"\s+", " ", m.group(2)).strip()
    era = attrs.get("年代") or attrs.get("时代") or attrs.get("所处时代") or attrs.get("时期") or ""
    cat = attrs.get("类型") or ""
    dims = attrs.get("器物规格") or attrs.get("规格") or ""
    exc = "；".join(v for k, v in attrs.items() if k.startswith("出土"))
    return name, cat, era, dims, exc, attrs


NAME_RULES = [("壁画", "书画"), ("金简", "金银器"), ("汝窑", "瓷器"), ("钧窑", "瓷器"),
              ("官窑", "瓷器"), ("定窑", "瓷器"), ("哥窑", "瓷器"), ("瓷", "瓷器"),
              ("釉", "瓷器"), ("青铜", "青铜器"), ("鼎", "青铜器"), ("簋", "青铜器"),
              ("爵", "青铜器"), ("卣", "青铜器"), ("盉", "青铜器"), ("匜", "青铜器"),
              ("罍", "青铜器"), ("尊", "青铜器"), ("方壶", "青铜器"), ("玉", "玉器"),
              ("骨笛", "杂器"), ("简", "杂器")]


def map_cat(cat, name):
    for k, v in CAT_MAP.items():
        if cat and k in cat:
            return v
    for k, v in NAME_RULES:
        if k in name:
            return v
    from dynasty_util import map_category
    return map_category(name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--sleep", type=float, default=2.0)
    ap.add_argument("--col", default=None, help="restrict to one column")
    args = ap.parse_args()

    lists = json.loads(LISTS.read_text(encoding="utf-8"))
    jobs = []
    for col, items in lists.items():
        if args.col and col != args.col:
            continue
        for oid, name in items.items():
            jobs.append((oid, name, col))
    done = added = skipped = 0
    for oid, name, col in jobs:
        if added >= args.limit:
            break
        out = ROOT / f"data/relics/HN-{oid}.json"
        if out.exists():
            skipped += 1
            continue
        t = fetch(oid, args.sleep)
        dname, cat, era, dims, exc, attrs = parse(t)
        name = dname or name
        if not name:
            print(f"SKIP {oid}: no name")
            continue
        if INST_RE.search(name.strip()):
            print(f"SKIP {oid}: institution page | {name}")
            skipped += 1
            continue
        dyn, conf = map_dynasty(era, name)
        desc_keys = ("说明", "介绍", "描述", "注")
        extra = "；".join(v for k, v in attrs.items() if any(x in k for x in desc_keys) and len(v) > 20)
        rec = {
            "relic_id": f"HN-{oid}",
            "name": name,
            "aliases": [],
            "dynasty": dyn,
            "year_range": None,
            "category": map_cat(cat, name),
            "material": "",
            "dimensions": dims,
            "excavated_from": exc,
            "collection": {"museum": "河南博物院", "region": "中国大陆", "inventory_no": oid},
            "summary": extra[:300] if extra else
                       (f"{name}，{era or dyn}。河南博物院{col}栏目著录。" if era else
                        f"{name}，河南博物院{col}栏目著录。"),
            "history": extra,
            "interpretation": [],
            "images": [],
            "source_url": f"{BASE}/ch/collection/boutique/details.html?id={oid}",
            "license": "©河南博物院",
            "tags": map_tags(name)[:5],
            "related": [],
            "raw_ref": f"raw/hn/detail_{oid}.html",
            "needs_review": False,
            "fetched_at": TODAY,
        }
        print(f"ADD HN-{oid} [{dyn}/{rec['category']}/{era or '-'}] {name} (from {col})")
        out.write_text(json.dumps(rec, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        added += 1
        done += 1
    print(f"added={added} skipped(existing)={skipped}")


if __name__ == "__main__":
    main()
