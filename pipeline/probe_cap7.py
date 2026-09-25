# -*- coding: utf-8 -*-
"""Scan capital rendered page: detail links + pagination markup."""
import pathlib
import re

t = pathlib.Path("raw/probe_prov/rendered_capital_collection.html").read_text(encoding="utf-8", errors="ignore")
ids = re.findall(r"/collection/([0-9a-f]{32})", t)
print("detail links:", len(ids), sorted(set(ids))[:6])
for m in re.finditer(r"pagination|pageno|pageNo|pageNum|下一页|page=", t):
    s = max(0, m.start() - 100)
    seg = re.sub(r"\s+", " ", t[s:m.start() + 140])
    print("PG:", ascii(seg[:200]))
