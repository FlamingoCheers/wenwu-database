import json, glob, re, sys, io, os

sys.path.insert(0, "apply" if os.path.isdir("apply") else ".")
from collectors.dynasty_util import map_dynasty, COARSE_RANGES

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
APPLY = "--apply" in sys.argv

CENT_SPAN = re.compile(r"(\d{1,2})(?:st|nd|rd|th)\s*(?:to|[-–—]|and)\s*(\d{1,2})(?:st|nd|rd|th)\s+cent", re.I)
CENT_HALF = re.compile(r"(early|mid[- ]|late)\s+(\d{1,2})(?:st|nd|rd|th)\s+cent", re.I)
CENT_SINGLE = re.compile(r"(\d{1,2})(?:st|nd|rd|th)\s+cent", re.I)
CENT_CN_SPAN = re.compile(r"([一二三四五六七八九十]{1,3})十?[一二三四五六七八九十]?至([一二三四五六七八九十]{1,3})十?[一二三四五六七八九十]?世纪")
CA_RANGE = re.compile(r"(?:ca\.?|c\.)\s*(\d{3,4})\s*[-–—]\s*(\d{3,4})", re.I)
CA_SINGLE = re.compile(r"(?:ca\.?|c\.)\s*(\d{4})\b", re.I)
DECADE = re.compile(r"(?<!\d)(\d{3})0s(?![\d年])")
YEAR_SOLO = re.compile(r"(?<!\d)(1[89]\d{2}|20[01]\d)(?!\d)")
DATED = re.compile(r"\bdated\s+(?:(\d{1,2})\s+)?(?:[A-Z][a-z]+\s+)?(\d{4})\b")
SITE_TOKENS = (
    (re.compile(r"半坡|仰韶|龍山|龙山|紅山|红山|大汶口|馬家窯|马家窑|齊家|齐家|屈家嶺|屈家岭|石峁|陶寺"), "新石器时代"),
    (re.compile(r"二里頭|二里头"), "夏"),
    (re.compile(r"殷墟|殷商"), "商"),
)
REIGN = {
    "Qianlong": "清", "Kien-lung": "清", "Kianlong": "清", "Kangxi": "清", "K'ang-hsi": "清",
    "Yongzheng": "清", "Yung-cheng": "清", "Shunzhi": "清", "Shun-chih": "清",
    "Jiaqing": "清", "Kia-ch'ing": "清", "Daoguang": "清", "Tao-kuang": "清",
    "Xianfeng": "清", "Hsien-feng": "清", "Tongzhi": "清", "T'ung-chih": "清",
    "Guangxu": "清", "Kuang-hsu": "清", "Kuang-hsü": "清", "Xuantong": "清", "Hsuan-t'ung": "清",
    "Hongwu": "明", "Hung-wu": "明", "Yongle": "明", "Yung-lo": "明", "Hongxi": "明",
    "Xuande": "明", "Hsuan-te": "明", "Zhengde": "明", "Cheng-te": "明", "Jiajing": "明",
    "Chia-ching": "明", "Longqing": "明", "Wanli": "明", "Wan-li": "明", "Taichang": "明",
    "Tianqi": "明", "T'ien-ch'i": "明", "Chongzhen": "明", "Ch'ung-chen": "明",
    "Chunxi": "南宋", "淳熙": "南宋", "庆元": "南宋", "嘉泰": "南宋", "开禧": "南宋", "嘉定": "南宋",
    "绍定": "南宋", "端平": "南宋", "嘉熙": "南宋", "淳佑": "南宋", "宝佑": "南宋", "开庆": "南宋",
    "景定": "南宋", "咸淳": "南宋", "建隆": "北宋", "景德": "北宋", "祥符": "北宋", "庆历": "北宋",
    "熙宁": "北宋", "元丰": "北宋", "元佑": "北宋", "绍圣": "北宋", "崇宁": "北宋", "宣和": "北宋",
    "政和": "北宋", "靖康": "北宋", "天监": "南北朝", "大同": "南北朝", "太清": "南北朝",
    "天嘉": "南北朝", "太建": "南北朝", "天统": "南北朝", "武平": "南北朝",
    "天聪": "清", "崇德": "清",
}
REIGN_RE = re.compile(
    "(" + "|".join(sorted((re.escape(k) for k in REIGN), key=len, reverse=True)) + ")")
BARE_DYN = re.compile(r"\b(Ming|Qing|Song|Yuan|Tang|Han|Liao|Sui|Zhou|Shang|Five Dynasties)\b")

def cn2int(s):
    m = {"一":1,"二":2,"三":3,"四":4,"五":5,"六":6,"七":7,"八":8,"九":9,"十":10}
    if s == "十":
        return 10
    if len(s) == 2 and s[0] == "十":
        return 10 + m[s[1]]
    if len(s) == 2 and s[1] == "十":
        return m[s[0]] * 10
    if len(s) == 3 and "十" in s:
        a, b = s.split("十")
        return m[a] * 10 + m[b]
    return m.get(s, 0)

def years_from_text(txt):
    if not txt:
        return None
    m = CENT_SPAN.search(txt)
    if m:
        c1, c2 = int(m.group(1)), int(m.group(2))
        if 1 <= c1 <= c2 <= 21:
            return [(c1 - 1) * 100 + 1, c2 * 100]
    m = CENT_CN_SPAN.search(txt)
    if m:
        c1, c2 = cn2int(m.group(1)), cn2int(m.group(2))
        if 1 <= c1 <= c2 <= 21:
            return [(c1 - 1) * 100 + 1, c2 * 100]
    m = CENT_HALF.search(txt)
    if m:
        c = int(m.group(2))
        if 1 <= c <= 21:
            lo = (c - 1) * 100 + 1
            if m.group(1).startswith("early"):
                return [lo, lo + 39]
            if m.group(1).startswith("mid"):
                return [lo + 30, lo + 69]
            return [lo + 60, lo + 99]
    m = CENT_SINGLE.search(txt)
    if m:
        c = int(m.group(1))
        if 1 <= c <= 21:
            return [(c - 1) * 100 + 1, c * 100]
    m = CA_RANGE.search(txt)
    if m:
        return [int(m.group(1)), int(m.group(2))]
    m = DATED.search(txt)
    if m:
        return [int(m.group(2)), int(m.group(2))]
    m = DECADE.search(txt)
    if m:
        d = int(m.group(1)) * 10
        return [d, d + 9]
    m = CA_SINGLE.search(txt)
    if m:
        return [int(m.group(1)), int(m.group(1))]
    m = YEAR_SOLO.search(txt)
    if m:
        return [int(m.group(1)), int(m.group(1))]
    return None

def coarse_for(y0, y1):
    cands = []
    for name, lo, hi in COARSE_RANGES:
        if y0 == y1:
            if lo <= y0 <= hi:
                cands.append((hi - lo, name))
        else:
            ov = min(y1, hi) - max(y0, lo)
            if ov > 0:
                cands.append((ov, name))
    if not cands:
        return "不详"
    if y0 == y1:
        cands.sort()
        return cands[0][1]
    return max(cands, key=lambda t: t[0])[1]

stat = {"dyn": 0, "year": 0, "dyn_via_year": 0, "left": 0}
left_by = {}
for f in glob.glob("data/relics/*.json"):
    r = json.load(open(f, encoding="utf-8"))
    if r.get("dynasty") != "不详":
        continue
    rid = r["relic_id"]
    pre = rid.split("-")[0]
    text = " ".join([r.get("era_text") or "", r.get("summary") or "", r.get("name") or ""])
    d, conf = map_dynasty(text)
    if d == "不详":
        m = BARE_DYN.search(text)
        if m:
            d = m.group(1)
            d = {"Five Dynasties": "五代十国"}.get(d, d)
            conf = "medium"
    if d == "不详":
        for pat, name in SITE_TOKENS:
            if pat.search(text):
                d, conf = name, "medium"
                break
    if d == "不详":
        m = REIGN_RE.search(text)
        if m:
            d, conf = REIGN[m.group(1)], "medium"
    changed = False
    if d != "不详":
        r["dynasty"] = d
        r["dynasty_confidence"] = "medium"
        if not r.get("year_range"):
            for name, lo, hi in COARSE_RANGES:
                if name == d:
                    r["year_range"] = [lo, hi]
                    break
        stat["dyn"] += 1
        changed = True
    else:
        ys = years_from_text(text)
        if ys and -12000 < ys[0] < 2100:
            r["year_range"] = ys
            dd = coarse_for(ys[0], ys[1])
            if dd != "不详":
                r["dynasty"] = dd
                r["dynasty_confidence"] = "low"
                stat["dyn_via_year"] += 1
            stat["year"] += 1
            changed = True
    if changed:
        r["needs_review"] = bool(r.get("desc_ai")) or r.get("dynasty_confidence") == "low"
        r["updated_at"] = __import__("datetime").datetime.now().isoformat(timespec="seconds")
        if APPLY:
            json.dump(r, open(f, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    else:
        stat["left"] += 1
        left_by[pre] = left_by.get(pre, 0) + 1

print(json.dumps(stat, ensure_ascii=False))
print("left by museum:", left_by)
