# -*- coding: utf-8 -*-
"""Re-derive VA dynasty/year from cached details: feed description text into
map_dynasty and fall back to century/range regexes for year_range."""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from collectors.dynasty_util import map_dynasty, COARSE_RANGES

RE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "relics")
RAW_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "raw", "va")

CEN_RE = re.compile(r"(\d{1,2})(?:st|nd|rd|th)\s+century", re.I)
RANGE_RE = re.compile(r"(\d{3,4})\s*[-\u2013]\s*(\d{3,4})")
BC_RE = re.compile(r"(\d{3,4})\s*BC", re.I)


def year_from_text(txt):
    m = RANGE_RE.search(txt)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        if 800 <= a < b <= 2100:
            return [a, b]
    m = CEN_RE.search(txt)
    if m:
        n = int(m.group(1))
        return [(n - 1) * 100 + 1, n * 100]
    return None


def derive(rec, srec):
    dates = rec.get("productionDates") or []
    era_bits = []
    begin = end = None
    for dd in dates:
        d0 = dd.get("date") or {}
        t = (d0.get("text") or "").strip()
        if t:
            era_bits.append(t)
        if isinstance(d0.get("earliest"), int):
            begin = d0["earliest"] if begin is None else min(begin, d0["earliest"])
        if isinstance(d0.get("latest"), int):
            end = d0["latest"] if end is None else max(end, d0["latest"])
    if not era_bits and srec.get("_primaryDate"):
        era_bits.append(srec["_primaryDate"])
    period_lbl = " ".join(era_bits)
    styles = " ".join(s.get("text", "") for s in (rec.get("styles") or []))
    desc = rec.get("summaryDescription") or rec.get("briefDescription") or ""
    if isinstance(desc, list):
        desc = " ".join(d.get("text", "") for d in desc if isinstance(d, dict))
    desc = (desc or "").strip()
    name = (rec.get("titles") or [{}])[0].get("title") or srec.get("_primaryTitle") or rec.get("objectType") or ""
    dyn, conf = map_dynasty(period_lbl, styles, name, desc[:200], begin=begin, end=end)
    yr = [begin, end] if begin is not None and end is not None else None
    if yr is None:
        yr = year_from_text(period_lbl + " " + desc[:200])
    if dyn == "不详" and yr:
        for zh, lo, hi in COARSE_RANGES:
            if yr[0] >= lo and yr[1] <= hi:
                dyn = zh
                break
    return dyn, yr, period_lbl


def main():
    n = ch = 0
    import glob
    for f in glob.glob(os.path.join(RE_DIR, "VA-*.json")):
        rel = json.load(open(f, encoding="utf-8"))
        oid = rel["relic_id"][3:]
        pf = os.path.join(RAW_DIR, "detail_%s.json" % oid)
        if not os.path.exists(pf):
            continue
        rec = json.load(open(pf, encoding="utf-8"))
        if isinstance(rec, dict) and "record" in rec:
            rec = rec["record"]
        dyn, yr, _ = derive(rec, {})
        n += 1
        if dyn != rel["dynasty"] or yr != rel.get("year_range"):
            rel["dynasty"] = dyn
            rel["year_range"] = yr
            rel["needs_review"] = dyn == "不详"
            rel["updated_at"] = "2026-09-28"
            json.dump(rel, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            ch += 1
    print("checked %d, changed %d" % (n, ch))


if __name__ == "__main__":
    main()
