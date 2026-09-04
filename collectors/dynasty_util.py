import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

DYNASTY_MAP = [
    (re.compile(r"\bshang\b", re.I), "商"),
    (re.compile(r"\bxia\b", re.I), "夏"),
    (re.compile(r"\bneolithic\b|\byangshao\b|\blongshan\b|\bliangzhu\b|\bhongshan\b|\bmajiayao\b|\bqijia\b|\berlitou\b", re.I), "新石器时代"),
    (re.compile(r"\bhan\b", re.I), "汉"),
    (re.compile(r"\bthree kingdoms\b", re.I), "三国"),
    (re.compile(r"\bsix dynasties\b|\bnorthern and southern\b|\bnorthern wei\b|\beastern wei\b|\bwestern wei\b|\bnorthern qi\b|\bnorthern zhou\b", re.I), "南北朝"),
    (re.compile(r"\bsui\b", re.I), "隋"),
    (re.compile(r"\btang\b", re.I), "唐"),
    (re.compile(r"\bfive dynasties\b", re.I), "五代十国"),
    (re.compile(r"\bliao\b", re.I), "辽"),
    (re.compile(r"\bwestern xia\b", re.I), "西夏"),
    (re.compile(r"\bsong\b", re.I), "宋"),
    (re.compile(r"\byuan\b", re.I), "元"),
    (re.compile(r"\bming\b", re.I), "明"),
    (re.compile(r"\bqing\b", re.I), "清"),
    (re.compile(r"\brepublic\b|\bmodern\b|\bcontemporary\b", re.I), "近代"),
]

DYNASTY_AMBIGUOUS = {
    "jin": lambda b: "金" if (b or 0) >= 1115 else "西晋",
    "zhou": lambda b: "西周" if (b or 0) < -771 else "东周",
    "song": lambda b: "南宋" if (b or 0) >= 1127 else "北宋",
}

COARSE_RANGES = [
    ("新石器时代", -10000, -2070), ("夏", -2070, -1600), ("商", -1600, -1046),
    ("西周", -1046, -771), ("东周", -771, -256), ("秦", -221, -207),
    ("汉", -202, 220), ("三国", 220, 280), ("西晋", 265, 316), ("东晋", 317, 420),
    ("南北朝", 420, 589), ("隋", 581, 618), ("唐", 618, 907), ("五代十国", 907, 979),
    ("北宋", 960, 1127), ("南宋", 1127, 1279), ("辽", 916, 1125), ("金", 1115, 1234),
    ("西夏", 1038, 1227), ("元", 1271, 1368), ("明", 1368, 1644), ("清", 1644, 1911),
]

CATEGORY_ALIASES = []
_LOADED = False

TAG_RULES = [
    (re.compile(r"mirror", re.I), ["铜镜", "日常生活"]),
    (re.compile(r"\bsword|dagger|blade|axe|halberd|arrowhead|armor|helm", re.I), ["战争", "兵器"]),
    (re.compile(r"coin|currency|money", re.I), ["货币金融"]),
    (re.compile(r"buddha|bodhisattva|buddhist|guanyin|arhat|luohan", re.I), ["佛教", "神话宗教"]),
    (re.compile(r"daoist|laozi|immortal|jade emperor", re.I), ["道教", "神话宗教"]),
    (re.compile(r"funerar|tomb|mingqi|burial|coffin", re.I), ["丧葬", "明器"]),
    (re.compile(r"\bjar|bowl|dish|plate|cup|ewer|pitcher|vessel|beaker|stemcup", re.I), ["食器"]),
    (re.compile(r"wine|zun|jue\b|gu\b|you\b|lei\b|he\b|gang\b|hu\b|guan\b", re.I), ["酒文化", "礼制"]),
    (re.compile(r"ritual|altar", re.I), ["礼制", "祭祀"]),
    (re.compile(r"incense burner|censer", re.I), ["香文化"]),
    (re.compile(r"figurine|figure of a", re.I), ["日常生活"]),
    (re.compile(r"comb|hairpin|belt hook|buckle", re.I), ["妆饰"]),
    (re.compile(r"seal\b|stamp|impres", re.I), ["玺印封泥", "文字书写"]),
    (re.compile(r"snuff bottle", re.I), ["日常生活"]),
    (re.compile(r"landscape|mountain|river", re.I), ["山水"]),
    (re.compile(r"dragon|phoenix|qilin|auspicious", re.I), ["祥瑞纹样"]),
    (re.compile(r"teapot|tea bowl|cup stand|tea", re.I), ["茶文化"]),
    (re.compile(r"astronom|zodiac|calendric", re.I), ["天文历法", "生肖"]),
    (re.compile(r"horse|camel|elephant|tiger|dragon|bird|duck|goose|crane|fish|deer|lion|dog|cat|monkey|ram|ox|pig", re.I), ["动物"]),
    (re.compile(r"flower|peony|lotus|plum|chrysanthemum|bamboo|pine", re.I), ["植物"]),
    (re.compile(r"saddle|stirrup|carriage|chariot|boat", re.I), ["出行"]),
    (re.compile(r"textile|robe|fragment.*silk|silk.*fragment", re.I), ["服饰"]),
    (re.compile(r"game|chess|dice|gambl", re.I), ["游戏", "博戏"]),
    (re.compile(r"lamp|lighter|candle", re.I), ["照明"]),
    (re.compile(r"bed|table|chair|stand|cabinet|screen", re.I), ["家具"]),
    (re.compile(r"brush washer|brush rest|ink stone|inkstone|ink cake|paperweight|water dropper|brush", re.I), ["文房", "文字书写"]),
]


def load_category_aliases():
    global _LOADED
    if _LOADED:
        return
    vocab = json.loads((ROOT / "data" / "vocab" / "categories.json").read_text(encoding="utf-8"))
    for cat in vocab["categories"]:
        for alias in cat["aliases"]:
            CATEGORY_ALIASES.append((alias.strip().lower(), cat["key"]))
    CATEGORY_ALIASES.sort(key=lambda x: -len(x[0]))
    _LOADED = True


def map_category(*texts):
    load_category_aliases()
    m = " ".join(t for t in texts if t).lower()
    if not m:
        return "杂器"
    for alias, key in CATEGORY_ALIASES:
        if alias in m:
            return key
    return "杂器"


def map_dynasty(*texts, begin=None, end=None):
    joined = " ".join(t for t in texts if t)
    for pattern, key in DYNASTY_MAP:
        if pattern.search(joined):
            return key, "high"
    for token, resolver in DYNASTY_AMBIGUOUS.items():
        if re.search(rf"\b{token}\b", joined, re.I) and begin is not None:
            return resolver(begin), "medium"
    if begin is not None:
        if end is not None:
            for key, lo, hi in COARSE_RANGES:
                if lo <= begin and end <= hi + 30:
                    return key, "medium"
        else:
            for key, lo, hi in reversed(COARSE_RANGES):
                if lo <= begin:
                    return key, "medium"
    return "不详", "low"


def map_tags(*texts):
    text = " ".join(t for t in texts if t)
    tags = []
    for pattern, hits in TAG_RULES:
        if pattern.search(text):
            tags.extend(hits)
    seen, out = set(), []
    for t in tags:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out
