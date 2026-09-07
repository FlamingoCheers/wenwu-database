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

# 中文朝代词分两级:
# STRONG——仅用于短字段(≤12字, 如博物馆卡片上的年代标注栏), 允许单字朝代名,
#          对高危单字加负向断言(鎏金/黄金/公元/纪元/说明/西夏等误伤源)。
# WEAK——用于任意长度文本, 只认"朝代+代/朝/初/末"及复合词(清宫/大唐/民国等)。
CH_DYN_STRONG = [
    (re.compile(r"旧石器|新石器|仰韶|龙山|良渚|红山|马家窑|齐家|二里头"), "新石器时代"),
    (re.compile(r"西夏"), "西夏"),
    (re.compile(r"[东西]周"), "东周"),
    (re.compile(r"(?<!西)夏"), "夏"),
    (re.compile(r"商"), "商"),
    (re.compile(r"(?<![东西])周"), "东周"),
    (re.compile(r"春秋"), "春秋"),
    (re.compile(r"战国"), "战国"),
    (re.compile(r"秦"), "秦"),
    (re.compile(r"(?<!字)汉"), "汉"),
    (re.compile(r"三国"), "三国"),
    (re.compile(r"(?<![东西])晋"), "东晋"),
    (re.compile(r"南北朝|北魏|东魏|西魏|北齐|北周"), "南北朝"),
    (re.compile(r"隋"), "隋"),
    (re.compile(r"唐"), "唐"),
    (re.compile(r"五代"), "五代十国"),
    (re.compile(r"辽"), "辽"),
    (re.compile(r"(?<!鎏|黄|错|贴|紫)金"), "金"),
    (re.compile(r"(?<!公|纪|美|日|多|单|综)元"), "元"),
    (re.compile(r"(?<!证|说|黎|说)明"), "明"),
    (re.compile(r"(?<!满)清"), "清"),
    (re.compile(r"民国|近现代|现当代|当代|现代|近代"), "近代"),
]

CH_DYN_WEAK = [
    (re.compile(r"旧石器时代|新石器时代|仰韶文化|龙山文化|良渚文化|红山文化|马家窑|齐家文化|二里头"), "新石器时代"),
    (re.compile(r"西夏"), "西夏"),
    (re.compile(r"夏代|夏朝|夏家店"), "夏"),
    (re.compile(r"商代|商朝|殷商|商晚期|商早期"), "商"),
    (re.compile(r"西周|东周|周代|周朝"), "东周"),
    (re.compile(r"春秋"), "春秋"),
    (re.compile(r"战国"), "战国"),
    (re.compile(r"秦代|秦朝|大秦"), "秦"),
    (re.compile(r"汉代|汉朝|西汉|东汉|两汉|汉墓"), "汉"),
    (re.compile(r"三国|魏晋"), "三国"),
    (re.compile(r"西晋|东晋|两晋|晋代"), "东晋"),
    (re.compile(r"南北朝|北魏|东魏|西魏|北齐|北周"), "南北朝"),
    (re.compile(r"隋代|隋朝"), "隋"),
    (re.compile(r"唐代|唐朝|大唐|盛唐|晚唐|初唐|中唐|唐三彩"), "唐"),
    (re.compile(r"五代十国|五代"), "五代十国"),
    (re.compile(r"辽代|辽朝|契丹"), "辽"),
    (re.compile(r"金代|金朝|女真"), "金"),
    (re.compile(r"元代|元朝|蒙元"), "元"),
    (re.compile(r"明代|明朝|明初|明末|大明|明式"), "明"),
    (re.compile(r"清代|清朝|清初|清末|大清|清宫|清式|康雍乾"), "清"),
    (re.compile(r"民国|共和国|近现代|现当代|当代|现代|近代"), "近代"),
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
    # 中文两级: 短字段(年代栏/名称)可用单字朝代词, 长文本仅认带后缀复合词
    short = len(joined) <= 12
    for table in ([CH_DYN_STRONG, CH_DYN_WEAK] if short else [CH_DYN_WEAK]):
        for pattern, key in table:
            if pattern.search(joined):
                return key, "medium"
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
