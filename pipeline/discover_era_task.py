# -*- coding: utf-8 -*-
"""Discovery for the 2026-09-23 era review task.

1) locate user-named items by name substring
2) count SXHM 东周 coins
3) count material-era impossibilities (青花 pre-Yuan, 粉彩 pre-Qing, ...)
4) count dynasty=不详 with year_range
"""
import glob, json, pathlib, re
from collections import Counter

NAMED = ["龙首玉觿", "龙纹玉璧", "水晶镂雕三螭", "玉荷花螃蟹", "玉梳", "青花莲池鸳鸯纹碗",
         "青花仙人图筒式炉", "五彩张天师驱五毒", "鱼子绿釉菊瓣", "仿汝釉弦纹尊",
         "空竹", "青花缠枝莲花纹盘", "彩绘木雕观音菩萨头像", "粉彩凤穿花纹双联瓶",
         "玛瑙梅瓣式碗", "玉镂空喜字簪", "仿宋官窑兽耳瓶", "斗彩婴戏纹杯", "青花婴戏纹碗",
         "青花阿拉伯文折沿盘", "青花八仙人物纹葫芦瓶", "茶叶末釉贯耳壶", "龙形玉佩",
         "玉凤纹方盒", "玉镂雕牡丹纹花熏", "宣德霁蓝盘", "骠国乐", "淳于棼", "莺莺传",
         "风炉", "茶瓶", "茶臼", "渣斗", "北宋铜钱", "定窑划花萱草葵瓣口碗", "宝庆四明志",
         "西厢记诸宫调", "明瓒诗后题卷", "建阳窑褐釉碗", "飞天"]

named_hits = {k: [] for k in NAMED}
dzb_coins, mat_viol, buxiang_yr, album = [], [], [], []
MAT_RULES = [  # (keyword in name, earliest feasible dynasty by DYN order index)
    ("青花", "元"), ("釉里红", "元"), ("粉彩", "清"), ("珐琅彩", "清"),
    ("斗彩", "明"), ("五彩", "明"), ("广彩", "清"), ("素三彩", "明"),
    ("洋彩", "清"), ("矾红", "明"),
]
DYN_ORDER = ["新石器时代", "夏", "商", "西周", "东周", "春秋", "战国", "秦", "汉", "三国",
             "西晋", "东晋", "南北朝", "隋", "唐", "五代十国", "北宋", "宋", "南宋", "辽",
             "西夏", "金", "元", "明", "清", "近代"]
RANK = {d: i for i, d in enumerate(DYN_ORDER)}
ALBUM_RE = re.compile(r"^(唐宋名[蹟繢彙]|唐宋元[畫繪]集錦|唐宋元明集繪|宋元明名[繪蹟]|畫廊集錦|[A-Za-z]*法帖|快雪堂[法]?帖)\s*　?\s*冊?\s*　\s*(新石器时代|夏|商|西周|東周|春秋|戰國|战国|秦|漢|三國|晉|唐|五代|北宋|南宋|遼|金|元|明|清|民國|宋|辽)")

for f in glob.glob("data/relics/*.json"):
    d = json.loads(pathlib.Path(f).read_text(encoding="utf-8"))
    rid = pathlib.Path(f).stem
    name = d.get("name") or ""
    dyn = d.get("dynasty")
    yr = d.get("year_range")
    for k in NAMED:
        if k in name:
            named_hits[k].append((rid, name[:36], dyn, yr))
    if "SXHM" in rid and dyn == "东周" and d.get("category") == "钱币":
        dzb_coins.append((rid, name, yr))
    if dyn and dyn in RANK:
        for kw, floor in MAT_RULES:
            if kw in name and RANK[dyn] < RANK[floor]:
                mat_viol.append((rid, name[:36], dyn, yr, kw))
    if dyn == "不详" and yr and isinstance(yr[0], (int, float)):
        buxiang_yr.append((rid, name[:30], yr))
    if ALBUM_RE.match(name):
        album.append((rid, name[:40], dyn))

print("== named items found ==")
for k, v in named_hits.items():
    tag = "OK" if len(v) == 1 else ("MULTI" if len(v) > 1 else "MISS")
    if tag != "OK":
        print(f"{tag} {k}: {v[:3]}")
print("unique-ok:", sum(1 for v in named_hits.values() if len(v) == 1), "/", len(NAMED))
print("== SXHM 东周 coins:", len(dzb_coins))
print(Counter(n for _, n, _ in dzb_coins).most_common(12))
print("== material violations:", len(mat_viol))
for r in mat_viol[:12]:
    print("  ", r)
print("== 不详 with year_range:", len(buxiang_yr))
print("== album-leaf pattern matches:", len(album))
for r in album[:8]:
    print("  ", r)
