# -*- coding: utf-8 -*-
"""needs_review triage, rule pass.

Buckets:
  A. dynasty recovery from name/era_text tokens (suffix-guarded, collision-safe)
  B. century/range text -> year_range (dynasty stays 不详)
Then recompute needs_review:
  flag = desc_ai OR (conf==low AND dynasty!=不详) OR (dynasty==不详 AND no year_range)

Usage: python pipeline/nr_triage.py [--apply]
Report: raw/_nr_triage.json
"""
import argparse
import glob
import io
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from collectors.dynasty_util import COARSE_RANGES  # noqa: E402

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# (regex, dynasty, coarse_key)  — CN requires 代/朝/文化/reign suffix; EN requires dynasty|period
TOKENS = [
    (r"明代(?:早期|中期|晚期)?|明初|明末", "明"),
    (r"清代(?:早期|中期|晚期)?|清初|清末", "清"),
    (r"宋代", "宋"), (r"唐代", "唐"), (r"元代", "元"), (r"汉代", "汉"), (r"隋代", "隋"),
    (r"辽代", "辽"), (r"金代", "金"), (r"商代", "商"),
    (r"西周", "西周"), (r"东周", "东周"), (r"春秋", "春秋"), (r"战国", "战国"),
    (r"北宋", "北宋"), (r"南宋", "南宋"), (r"五代", "五代十国"),
    (r"新石器|红山文化|良渚文化|龙山文化|仰韶|齐家文化|大汶口", "新石器时代"),
    (r"二里头", "夏"),
    (r"民国", "近代"),
    (r"康熙|雍正|乾隆|嘉庆|道光|咸丰|同治|光绪|宣统", "清"),
    (r"永乐|宣德|成化|弘治|正德|嘉靖|隆庆|万历|泰昌|天启|崇祯", "明"),
    (r"\bMing\s+(?:dynasty|period)", "明"), (r"\bQing\s+(?:dynasty|period)", "清"),
    (r"\bSong\s+(?:dynasty|period)", "宋"), (r"\bTang\s+(?:dynasty|period)", "唐"),
    (r"\bYuan\s+(?:dynasty|period)", "元"), (r"\bHan\s+(?:dynasty|period)", "汉"),
    (r"\bSui\s+(?:dynasty|period)", "隋"), (r"\bLiao\s+(?:dynasty|period)", "辽"),
    (r"\bJin\s+(?:dynasty|period)", "金"), (r"\bShang\s+(?:dynasty|period)", "商"),
    (r"\bZhou\s+(?:dynasty|period)", "东周"),
    (r"\bWestern\s+Zhou\b", "西周"), (r"\bEastern\s+Zhou\b", "东周"),
    (r"\bWarring\s+States\b", "战国"), (r"\bSpring\s+and\s+Autumn\b", "春秋"),
    (r"\bSix\s+Dynasties\b", "南北朝"), (r"\bNorthern\s+and\s+Southern\s+Dynasties\b", "南北朝"),
    (r"\bNeolithic\b", "新石器时代"),
    (r"\bRepublican\s+(?:period|era)", "近代"),
    (r"\bKangxi\b|\bYongzheng\b|\bQianlong\b|\bJiaqing\b|\bDaoguang\b|\bXianfeng\b|\bTongzhi\b|\bGuangxu\b|\bXuantong\b", "清"),
    (r"\bYongle\b|\bXuande\b|\bChenghua\b|\bHongzhi\b|\bZhengde\b|\bJiajing\b|\bWanli\b|\bTianqi\b|\bChongzhen\b", "明"),
]
COARSE = {name: (lo, hi) for name, lo, hi in COARSE_RANGES}

RANGE_Y = re.compile(r"(?:ca\.?|c\.)?\s*(\d{3,4})\s*[-–—]\s*(\d{3,4})\s*(BCE|BC)?", re.I)
CENT_SINGLE = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)\s+century(?:\s*(BCE|BC))?", re.I)
CENT_SPAN = re.compile(r"\b(\d{1,2})(?:st|nd|rd|th)[-–](?:to\s+)?(\d{1,2})(?:st|nd|rd|th)\s+century(?:\s*(BCE|BC))?", re.I)
SINGLE_Y = re.compile(r"(?:ca\.?|c\.)?\s*(\d{1,4})\s*(BCE|BC|CE|AD)?\b", re.I)
DATED_Y = re.compile(r"\bdated\s+(?:c\.\s*)?(\d{3,4})\b", re.I)
CA_RANGE = re.compile(r"\b(?:ca\.?|c\.)\s*(\d{3,4})\s*[-–—]\s*(\d{3,4})\b", re.I)


def years_from_summary(txt):
    if not txt:
        return None
    m = DATED_Y.search(txt)
    if m:
        return [int(m.group(1)), int(m.group(1))]
    m = CA_RANGE.search(txt)
    if m:
        return [int(m.group(1)), int(m.group(2))]
    m = CENT_SPAN.search(txt)
    if m:
        c1, c2 = int(m.group(1)), int(m.group(2))
        return [(c1 - 1) * 100 + 1, c2 * 100]
    m = CENT_SINGLE.search(txt)
    if m:
        c = int(m.group(1))
        return [(c - 1) * 100 + 1, c * 100]
    return None


def dyn_from_tokens(txt):
    best = None  # (pos, -len, dynasty)
    for pat, dyn in TOKENS:
        m = re.search(pat, txt)
        if m and (best is None or (m.start(), -(m.end() - m.start())) < (best[0], best[1])):
            best = (m.start(), -(m.end() - m.start()), dyn)
    return best[2] if best else None


def years_from_era(txt):
    if not txt:
        return None
    m = CENT_SPAN.search(txt)
    if m:
        c1, c2 = int(m.group(1)), int(m.group(2))
        if m.group(3):
            return [-c2 * 100, -(c1 - 1) * 100]
        return [(c1 - 1) * 100 + 1, c2 * 100]
    m = CENT_SINGLE.search(txt)
    if m:
        c = int(m.group(1))
        if m.group(2):
            return [-c * 100, -(c - 1) * 100 + 1]
        return [(c - 1) * 100 + 1, c * 100]
    m = RANGE_Y.search(txt)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        if abs(a) < 10000 and abs(b) < 10000:
            if m.group(3):
                a, b = -abs(a), -abs(b)
            if a <= b:
                return [a, b]
    m = SINGLE_Y.search(txt)
    if m:
        y = int(m.group(1))
        if 0 < abs(y) < 2100 or (m.group(2) and abs(y) < 10000):
            if m.group(2) in ("BCE", "BC"):
                y = -abs(y)
            return [y, y]
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    stat = {"dyn_recovered": 0, "year_mapped": 0, "flag_cleared": 0, "still_flagged": 0,
            "untouched": 0, "by_museum": {}}
    for f in glob.glob("data/relics/*.json"):
        r = json.load(open(f, encoding="utf-8"))
        if not r.get("needs_review"):
            continue
        rid = r.get("relic_id", "")
        pre = rid.split("-")[0]
        stat["by_museum"].setdefault(pre, {"dyn_recovered": 0, "year_mapped": 0, "cleared": 0, "kept": 0})
        changed = False

        if r.get("dynasty") == "不详":
            text = " ".join([r.get("name") or "", r.get("era_text") or "", r.get("summary") or ""])
            d = dyn_from_tokens(text)
            if d and d in COARSE:
                r["dynasty"] = d
                r["dynasty_confidence"] = "medium"
                if not r.get("year_range"):
                    r["year_range"] = list(COARSE[d])
                stat["dyn_recovered"] += 1
                stat["by_museum"][pre]["dyn_recovered"] += 1
                changed = True
        if r.get("year_range") is None and (r.get("dynasty") == "不详" or not r.get("year_range")):
            ys = years_from_era(r.get("era_text")) or years_from_summary(r.get("summary"))
            if ys and -12000 < ys[0] < 2100:
                r["year_range"] = ys
                stat["year_mapped"] += 1
                stat["by_museum"][pre]["year_mapped"] += 1
                changed = True

        desc_ai = bool(r.get("desc_ai"))
        conf = r.get("dynasty_confidence")
        flag = desc_ai or (conf == "low" and r.get("dynasty") != "不详")
        if not flag:
            stat["flag_cleared"] += 1
            stat["by_museum"][pre]["cleared"] += 1
        else:
            stat["still_flagged"] += 1
            stat["by_museum"][pre]["kept"] += 1
        if bool(r.get("needs_review")) != flag:
            r["needs_review"] = flag
            changed = True
        if changed and args.apply:
            r["updated_at"] = time.strftime("%Y-%m-%d")
            json.dump(r, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    print(json.dumps(stat, ensure_ascii=False, indent=1))
    if args.apply:
        os.makedirs("raw", exist_ok=True)
        json.dump(stat, open("raw/_nr_triage.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
