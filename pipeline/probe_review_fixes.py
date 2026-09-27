# -*- coding: utf-8 -*-
"""按用户校对清单探查：按名称/id 定位现有记录，打印当前值（只读，不改数据）。"""
import json, glob, os, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RD = os.path.join(ROOT, "data", "relics")

names = [
    "毛泽东会见来华的美国总统理查德·尼克松",
    "五铢",
    "教会学校的穷学生",
    "广州夏葛女子医学院外景",
    "宁波女子师范学校的学生正在上课",
    "北京贝满女中的学生队伍",
    "1929年8月妇女联合会代表在天安门前演讲时的情景",
    "科尔沁亲王阿穆尔灵圭的长子辅国公和希格10岁时的留影",
    "梓宫灵车在前门站进入专列时的情景",
    "山东邮区济南邮务管理局",
    "1861年湖北汉口脚力行门前等待工作的搬运工人",
    "1895年中国南方的轿子与抬轿夫",
    "京张铁路康庄停车场景象",
    "京张铁路门头沟车站",
    "新宁铁路员工与机车的合影",
    "火车初通北京城",
    "济南津浦路上的跨桥",
    "汉粤川铁路线使用的巴尔德温大机车",
    "1917年汉粤川铁路线上的岳州停车场及机车房",
    "甘肃凉州府的露天书店",
    "筛茶叶",
    "上海城隍庙附近的茶铺",
    "卖编制篾器的小贩",
    "广东街头卖水果的路边小贩",
    "到市场去卖鹅的小贩",
    "1920年时的山西保晋公司阳泉铁厂",
    "华俄道胜银行天津分行",
    "新民储蓄银行营业部客户接待处内景",
    "北平骑巡队",
    "1908年中国会审员关炯之与德国副总领事会审刑事案件",
    "绰号为“小霸王”的绑匪张世魁",
    "押解绑架“人票”的土匪途经北平南新华街",
    "后金内秘书院大学士范文程接管八孤山子弟读书事奏稿",
    "周有光撰写的《汉字改革概论》日文版",
    "点眉纹双耳彩陶罐",
    "四系彩陶碟形器",
    "粉白地暗花双龙戏球纹宣纸",
    "九龙壁",
    "潮州窑青白釉释迦牟尼像",
    "官窑套盒",
    "景德镇窑青花双凤纹玉壶春瓶",
    "五彩瑞兽纹葵瓣式觚",
    "“天兴七年”金币",
    "永通万国",
]

ids = [
    "CLE-1940-597", "NPM-15471", "NPM-17394", "NPM-17833", "NPM-24475",
    "NPM-24482", "NPM-24585", "NPM-24586", "NPM-24588", "NPM-24591",
    "NPM-24652", "NPM-24653", "NPM-24654", "NPM-24655",
    "NPM-3816", "NPM-42918", "NPM-42978", "NPM-42984", "NPM-43032",
    "NPM-43384", "NPM-43439", "NPM-43507", "NPM-5124", "NPM-56785", "NPM-57615",
    "SMI-fsg_FSC-W-23",
    "HAM-1429", "HAM-143022", "HAM-147442", "HAM-148608", "HAM-149541",
    "HAM-149551", "HAM-149552", "HAM-174175", "HAM-178614", "HAM-182445",
    "HAM-196998", "HAM-198532", "HAM-198858", "HAM-199379", "HAM-199752",
    "HAM-201303", "HAM-202703", "HAM-203004", "HAM-204482", "HAM-204525",
    "HAM-204526", "HAM-204606", "HAM-204743", "HAM-204866", "HAM-204869",
    "HAM-204870", "HAM-204902", "HAM-204852", "HAM-204874", "HAM-204882",
    "HAM-204883", "HAM-204901", "HAM-204911", "HAM-204914", "HAM-204917",
    "HAM-204921", "HAM-204934", "HAM-204935", "HAM-204939", "HAM-204946",
    "HAM-204948", "HAM-204951",
]


def load(rid):
    p = os.path.join(RD, rid + ".json")
    if not os.path.exists(p):
        return None
    return json.load(open(p, encoding="utf-8"))


def brief(r):
    if r is None:
        return "MISSING"
    col = r.get("collection") or {}
    yr = r.get("year_range") or []
    return "%s | dyn=%s cat=%s yr=%s | %s | %s" % (
        r.get("relic_id"), r.get("dynasty"), r.get("category"),
        "%s~%s" % (yr[0], yr[1]) if len(yr) == 2 else "-",
        col.get("museum"), (r.get("source_url") or "")[:70])


print("=== 词表 dynasties ===")
V = os.path.join(ROOT, "data", "vocab")
dyn = json.load(open(os.path.join(V, "dynasties.json"), encoding="utf-8"))["dynasties"]
print([d["key"] for d in dyn])
print("现当代 in vocab:", any(d["key"] == "现当代" for d in dyn))

print("\n=== 按名称定位 ===")
idx = {}
for p in glob.glob(os.path.join(RD, "*.json")):
    try:
        r = json.load(open(p, encoding="utf-8"))
    except Exception:
        continue
    idx.setdefault((r.get("name") or "").strip(), []).append(r.get("relic_id"))

for n in names:
    hit = idx.get(n)
    if hit is None:
        cand = [k for k in idx if n in k or k in n]
        print("[?] %-46s 无精确匹配; 候选=%s" % (n, cand[:4]))
        continue
    for rid in hit:
        print("[%s] %s -> %s" % (n, rid, brief(load(rid))))

print("\n=== 按 id 定位 ===")
for rid in ids:
    print("%-18s %s" % (rid, brief(load(rid))))
