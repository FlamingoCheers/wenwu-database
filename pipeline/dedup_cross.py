import json
import os
import re
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from pipeline.audit_dynasty import TRAD  # noqa: E402

RE_DIR = r"E:\codingProject\52-文物数据库\data\relics"
PUNCT = re.compile(r"[\s·・（）()\[\]【】〔〕《》〈〉「」『』“”\"'、，,。.：:；;！!？?－—\-~～×xX×*＊]+")


def norm(name):
    t = PUNCT.sub("", str(name or "")).lower()
    return "".join(TRAD.get(ch, ch) for ch in t)


def main():
    groups = defaultdict(list)
    total = 0
    for fn in os.listdir(RE_DIR):
        if not fn.endswith(".json"):
            continue
        d = json.load(open(os.path.join(RE_DIR, fn), encoding="utf-8"))
        total += 1
        nm = norm(d.get("name") or (d.get("collection") or {}).get("inventory_no") or "")
        if len(nm) < 2:
            continue
        groups[nm].append({"id": d.get("relic_id") or d.get("id"), "m": d["collection"]["museum"],
                           "cat": d.get("category"), "dyn": d.get("dynasty"), "name": d.get("name")})
    cross = {k: v for k, v in groups.items() if len({x["m"] for x in v}) >= 2}
    cat_c = Counter()
    pair_c = Counter()
    for k, v in cross.items():
        cats = {x["cat"] for x in v}
        cat_c["|".join(sorted(cats))] += 1
        mus = sorted({x["m"] for x in v})
        for i in range(len(mus)):
            for j in range(i + 1, len(mus)):
                pair_c[(mus[i], mus[j])] += 1
    sizes = Counter(len(v) for v in cross.values())
    msize = Counter(len({x["m"] for x in v}) for v in cross.values())
    print("total_relics=%d norm_groups=%d cross_museum_groups=%d" % (total, len(groups), len(cross)))
    print("group_size_dist", dict(sorted(sizes.items())))
    print("museum_count_dist", dict(sorted(msize.items())))
    print("top_pairs:")
    for (a, b), c in pair_c.most_common(12):
        print("  %4d %s <-> %s" % (c, a, b))
    print("top_cat_mix:", cat_c.most_common(10))
    ex = sorted(cross.items(), key=lambda kv: -len({x["m"] for x in kv[1]}))[:25]
    print("samples:")
    for k, v in ex:
        print("  %s | %s | %s" % (k, sorted({x["m"] for x in v}), v[0]["name"]))
    out = r"E:\codingProject\52-文物数据库\raw\_dedup_report.json"
    json.dump({"groups": {k: v for k, v in cross.items()}}, open(out, "w", encoding="utf-8"), ensure_ascii=False)
    print("saved", out)


if __name__ == "__main__":
    main()
