# -*- coding: utf-8 -*-
"""中国国家博物馆采集器——B类降级为静态HTML解析。

侦察结论(2026-09-07):
- 馆藏精品列表 https://www.chnmuseum.cn/zp/zpml/ 是纯静态分页:
  首页 index.shtml, 之后 index_1540_{N}.shtml, 共 112 页 × 12 件 ≈ 1344 件
- 卡片: <a href="./.../tYYYYMMDD_ID.shtml"><img src=缩略图 alt=名称>
  + <p class="clear_name">年代</p> —— 仅首页带年代, 分页页年代为空
- 详情页: <title>名称_...</title>; 正文一段专家撰文+撰文人; 大图在
  data-src='./P0201....jpg' 属性(gallery 放大图); 无结构化年代/质地字段
- 图床无防盗链(direct GET 200)
策略: 年代=卡片年代(有则用)+描述关键词推断, 否则"不详"+needs_review,
      留给 LLM 审核阶段补全。图片只存 URL 不入库(防仓库膨胀)。
license: 国博图文版权归馆藏机构, 本库如实标注"©中国国家博物馆"。
用法: python nmc_collector.py [--limit N] [--sleep 秒] [--pages N]
"""
import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dynasty_util as du

ROOT = Path(__file__).resolve().parent.parent
RELICS_DIR = ROOT / "data" / "relics"
RAW_DIR = ROOT / "raw" / "nmc"
BASE = "https://www.chnmuseum.cn"
LIST_URL = BASE + "/zp/zpml/"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) wenwu-database/0.1"}
MUSEUM = "中国国家博物馆"
MUS_CODE = "NMC"
TODAY = date.today().isoformat()

# 中文类别关键词(有序扫描, 靠前优先; 鹰形"陶"鼎类靠陶器分支前置保护)
CATEGORY_KWS = [
    ("宗教造像", ["佛", "菩萨", "观音", "罗汉", "天王像", "造像塔"]),
    ("书画", ["书卷", "画卷", "立轴", "手卷", "册页", "帖", "书法", "碑帖", "年画"]),
    ("陶器", ["陶", "彩陶", "唐三彩", "俑", "瓦当", "砖雕"]),
    ("瓷器", ["瓷", "青花", "釉里红", "斗彩", "五彩", "粉彩", "珐琅彩", "单色釉", "窑变", "越窑", "定窑", "汝窑", "钧窑", "官窑", "哥窑"]),
    ("青铜器", ["青铜", "铜器", "铜镜", "铜鼓", "鼎", "尊", "簋", "爵", "觚", "卣", "斝", "罍", "编钟", "戈", "矛", "剑", "镞", "带钩"]),
    ("钱币", ["空首布", "布币", "刀币", "铜钱", "通宝", "元宝", "银锭", "货币", "钱范"]),
    ("玉器", ["玉", "璜", "璧", "琮", "玦", "玉佩", "玛瑙", "水晶", "绿松石", "翡翠", "琥珀", "宝石"]),
    ("玻璃器", ["玻璃", "琉璃"]),
    ("漆器", ["漆器", "漆盘", "漆盒"]),
    ("金银器", ["金银", "金器", "银器", "鎏金", "金杯", "银盘"]),
    ("织绣", ["织锦", "刺绣", "缂丝", "绫", "绢", "锦"]),
    ("竹木牙角", ["竹雕", "竹刻", "木雕", "牙雕", "犀角", "角雕", "桦皮"]),
    ("文房用具", ["笔架", "笔筒", "砚", "镇纸", "墨床", "臂搁", "笔洗", "印章", "玺"]),
    ("雕塑", ["石雕", "石刻", "雕像"]),
]


def map_category(name, desc=""):
    # 名称优先: 名称命中即定类, 防止描述里的工艺/典故词劫持
    for blob in (name or "", desc or ""):
        if not blob:
            continue
        for cat, kws in CATEGORY_KWS:
            for kw in kws:
                if kw in blob:
                    return cat
    return "杂器"


def http_get(url, timeout=30):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", errors="replace")


def parse_list(html):
    """卡片 → [{href, name, era, thumb}]"""
    out = []
    for m in re.finditer(r'<a href="(\./[^"]+?\.shtml)"[^>]*>.*?<img src="(\./[^"]+?\.jpg)"\s+alt="([^"]*)"', html, re.S):
        href, thumb, alt = m.groups()
        # clear_name 紧随其后(或在前), 独立匹配
        tail = html[m.end():m.end() + 400]
        em = re.search(r'class="clear_name">([^<]+)<', tail)
        era = em.group(1).strip() if em else ""
        out.append({"href": href, "thumb": thumb, "name": alt.strip(), "era": era})
    return out


def parse_detail(html):
    """详情页 → {name, desc, images[]}"""
    d = {}
    tm = re.search(r"<title>([^_<]+)_", html)
    if tm:
        d["name"] = tm.group(1).strip()
    # 正文描述: 去标签后找含撰文括号的长中文段
    text = re.sub(r"<script.*?</script>", "", html, flags=re.S)
    text = re.sub(r"<style.*?</style>", "", text, flags=re.S)
    body = re.sub(r"<[^>]+>", "|", text)
    best = ""
    for seg in body.split("|"):
        seg = seg.strip()
        if len(seg) >= 30 and re.search(r"[\u4e00-\u9fff]", seg) and "版权所有" not in seg and "友情链接" not in seg:
            if len(seg) > len(best):
                best = seg
    # 去掉末尾撰文人 "(张燕燕)"
    d["desc"] = re.sub(r"[（(][\u4e00-\u9fff]{2,4}[)）]\s*$", "", best).strip()
    d["author"] = ""
    am = re.search(r"[（(]([\u4e00-\u9fff]{2,4})[)）]\s*$", best)
    if am:
        d["author"] = am.group(1)
    imgs = re.findall(r"data-src='(\./[^']+?\.jpg)'", html)
    if not imgs:
        imgs = re.findall(r'data-src="(\./[^"]+?\.jpg)"', html)
    d["images"] = [urllib.parse.urljoin(LIST_URL, u) for u in imgs]
    return d


def era_to_dynasty(era, name, desc):
    blob = " ".join(x for x in [era, name, desc] if x)
    if era:
        key, conf = du.map_dynasty(era)
        if key != "不详":
            return key, conf
    key, conf = du.map_dynasty(name, desc)
    if key != "不详":
        return key, "low"
    return "不详", "low"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=50, help="入库目标件数")
    ap.add_argument("--sleep", type=float, default=1.5, help="请求间隔秒")
    ap.add_argument("--pages", type=int, default=0, help="最多翻页数(0=不限)")
    args = ap.parse_args()

    RELICS_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    added = dup = fail = 0
    page = 1
    while added < args.limit:
        # 列表页
        if page == 1:
            list_url, cache = LIST_URL, RAW_DIR / "list_1.html"
        else:
            list_url = f"{LIST_URL}index_1540_{page}.shtml"
            cache = RAW_DIR / f"list_{page}.html"
        try:
            if cache.exists():
                html = cache.read_text(encoding="utf-8", errors="replace")
            else:
                html = http_get(list_url)
                cache.write_text(html, encoding="utf-8")
                time.sleep(args.sleep)
        except Exception as e:
            print(f"列表页 {page} 失败: {e}")
            fail += 1
            break
        cards = parse_list(html)
        if not cards:
            print(f"列表页 {page} 无卡片, 结束")
            break
        for c in cards:
            if added >= args.limit:
                break
            dm = re.search(r"t\d{8}_(\d+)\.shtml", c["href"])
            if not dm:
                continue
            oid = dm.group(1)
            out = RELICS_DIR / f"{MUS_CODE}-{oid}.json"
            if out.exists():
                dup += 1
                continue
            detail_url = urllib.parse.urljoin(list_url, c["href"])
            try:
                dcache = RAW_DIR / f"detail_{oid}.html"
                if dcache.exists():
                    dhtml = dcache.read_text(encoding="utf-8", errors="replace")
                else:
                    dhtml = http_get(detail_url)
                    dcache.write_text(dhtml, encoding="utf-8")
                    time.sleep(args.sleep)
                d = parse_detail(dhtml)
            except Exception as e:
                print(f"  详情 {oid} 失败: {e}")
                fail += 1
                continue
            name = d.get("name") or c["name"] or "未命名"
            desc = d.get("desc") or ""
            dyn, conf = era_to_dynasty(c["era"], name, desc)
            images = [{"url": u, "license": "©中国国家博物馆", "credit": MUSEUM}
                      for u in d.get("images", [])][:2]
            if not images and c["thumb"]:
                images = [{"url": urllib.parse.urljoin(list_url, c["thumb"]),
                           "license": "©中国国家博物馆", "credit": MUSEUM}]
            relic = {
                "relic_id": f"{MUS_CODE}-{oid}",
                "name": name,
                "aliases": [],
                "dynasty": dyn,
                "dynasty_confidence": conf,
                "year_range": None,
                "category": map_category(name, desc),
                "material": None,
                "dimensions": None,
                "excavated_from": "",
                "collection": {
                    "museum": MUSEUM,
                    "region": "中国大陆",
                    "inventory_no": "",
                },
                "summary": desc[:300] or None,
                "history": "",
                "interpretation": [],
                "images": images,
                "source_url": detail_url,
                "license": "©中国国家博物馆",
                "tags": du.map_tags(name, desc),
                "related": [],
                "raw_ref": f"raw/nmc/detail_{oid}.html",
                "needs_review": dyn == "不详" or not images,
                "fetched_at": TODAY,
                "updated_at": TODAY,
            }
            out.write_text(json.dumps(relic, ensure_ascii=False, indent=1), encoding="utf-8")
            added += 1
            if added % 10 == 0:
                print(f"  已入库 {added} (页 {page})", flush=True)
            time.sleep(args.sleep)
        page += 1
        if args.pages and page > args.pages:
            break
    print(f"完成：入库 {added}  已存在 {dup}  失败 {fail}")


if __name__ == "__main__":
    main()
