# -*- coding: utf-8 -*-
"""Backfill HAM records: needs_review flag + year_range from era_text."""
import glob
import io
import json
import re
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

BCE = re.compile(r"BCE", re.I)
RANGE = re.compile(r"(-?\d+)\s*[-–]\s*(-?\d+)")
SINGLE = re.compile(r"(-?\d{1,4})s?\s*(BCE|CE)?", re.I)


def years_from_era(txt):
    if not txt:
        return None
    m = RANGE.search(txt)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        if abs(a) < 10000 and abs(b) < 10000:
            if BCE.search(txt):
                a, b = -abs(a), -abs(b)
            if a <= b:
                return [a, b]
    m = SINGLE.search(txt)
    if m:
        y = int(m.group(1))
        if abs(y) < 10000:
            if BCE.search(txt):
                y = -abs(y)
            return [y, y]
    return None


n_flag = n_year = 0
for f in glob.glob("data/relics/HAM-*.json"):
    r = json.load(open(f, encoding="utf-8"))
    ch = False
    want = r.get("dynasty") == "不详"
    if bool(r.get("needs_review")) != want:
        r["needs_review"] = want
        ch = True
        n_flag += 1
    if not r.get("year_range"):
        ys = years_from_era(r.get("era_text"))
        if ys:
            r["year_range"] = ys
            ch = True
            n_year += 1
    if ch:
        json.dump(r, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("flagged:", n_flag, "years:", n_year)
