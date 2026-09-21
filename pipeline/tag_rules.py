# -*- coding: utf-8 -*-
"""C 阶段：标签补全编排器（规则预打标 + LLM 兜底）

子命令:
  tag     规则预打标：扫全库无标签藏品，按中英文关键词规则写 tags（词表校验，上限5个）
          日志 raw/llm_clean/tag_rules_applied.json
  prep    规则打标后仍无标签的 -> raw/llm_clean/C_tags_todo.jsonl（供子 Agent）
  merge   合并 C_result_*.jsonl {id,tags[]} -> 词表校验 -> C_apply.json + C_reject.json
  apply   写回 tags（仅当现无标签），日志 apply_C_journal.json
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RELICS = ROOT / "data" / "relics"
LC = ROOT / "raw" / "llm_clean"
sys.path.insert(0, str(ROOT / "collectors"))
from dynasty_util import map_tags  # 英文规则复用

TAGS_VOCAB = ROOT / "data" / "vocab" / "tags.json"

# 中文关键词 -> 标签（词表内）。顺序：具体在前，宽泛在后。
CN_TAG_RULES = [
    (r"佛|菩萨|觀音|观音|罗汉|羅漢|释迦|釋迦|弥勒|彌勒|唐卡|坛城|坛層|曼荼罗", ["佛教", "神话宗教"]),
    (r"天尊|八仙|老子|道德经|道教|雷公|妈祖|关帝", ["道教", "神话宗教"]),
    (r"爵|觚|斝|卣|罍|盉|觥|尊", ["酒文化", "礼制"]),
    (r"鼎|簋|鬲|甗|簠|盨|俎|彝", ["礼制", "食器"]),
    (r"剑|刀|戈|矛|戟|镞|弩|盔|甲胄|铠", ["兵器", "战争"]),
    (r"通宝|重宝|元宝|五铢|布币|刀币|钱币|金币|银币|铜钱|钱范", ["货币金融"]),
    (r"香炉|香薰|香熏|薰炉|熏炉|香插|香囊|香盒|香宝子", ["香文化"]),
    (r"鼻烟壶", ["日常生活"]),
    (r"笔筒|笔洗|笔架|笔山|笔掭|笔舔|墨床|砚|镇纸|臂搁|水丞|水注|印盒|笔杆|笔管", ["文房", "文字书写"]),
    (r"玺|印章|印", ["玺印封泥", "文字书写"]),
    (r"拓本|碑刻|墓志", ["文字书写", "书法艺术"]),
    (r"法书|行书|楷书|草书|隶书|篆书|书跋|题跋|临帖", ["书法艺术", "文字书写"]),
    (r"山水|江山|溪山|山居|江帆", ["山水"]),
    (r"花鸟|翎毛", ["植物", "动物"]),
    (r"墨竹|兰竹|竹石|梅|兰|菊|牡丹|莲|荷|葡萄|瓜果|石榴|葫芦|灵芝|花卉|花果|嘉禾|松", ["植物"]),
    (r"龙|凤|麒麟|瑞兽|辟邪|天禄|貔貅|甪端", ["祥瑞纹样"]),
    (r"驼|象|鹿|虎|鹤|雁|鸭|鹅|鱼|狮|犬|猫|兔|鹰|鹦鹉|蟋蟀|雀|燕|鹊|马|牛|羊|猴|鸡|狗|猪|蛇|蛙|蝉|蝙蝠|异兽", ["动物"]),
    (r"俑", ["明器", "丧葬"]),
    (r"陶仓|陶楼|陶灶|陶屋|陶井|陶狗|陶鸡", ["明器"]),
    (r"墓", ["丧葬"]),
    (r"甲骨|卜辞|卜骨|卜甲", ["占卜", "文字书写"]),
    (r"琮|璧|璜|圭|璋", ["礼制"]),
    (r"袍|衣|衫|裙|袄|褂|帔|氅|冠|帽|朝服|龙袍", ["服饰"]),
    (r"缂丝|织绣|绣|锦|缎|绸|纱|罗|绢", ["纺织", "服饰"]),
    (r"簪|钗|笄|步摇|镯|戒指|耳坠|项饰", ["首饰", "妆饰"]),
    (r"梳", ["梳篦", "妆饰"]),
    (r"带钩", ["带钩", "妆饰"]),
    (r"车|轿|舆", ["出行", "车马"]),
    (r"舟|船|舫", ["出行", "舟船"]),
    (r"灯|烛台", ["照明"]),
    (r"椅|凳|桌|案|柜|橱|屏风|床|榻|多宝格|香几|条案", ["家具"]),
    (r"瑟|琵琶|笙|箫|笛|埙|编钟|镈|鼓", ["音乐舞蹈"]),
    (r"棋|骰|双陆|投壶|叶戏", ["博戏", "游戏"]),
    (r"犁|锄|镰|耒耜|耧", ["农耕"]),
    (r"天文|历法|日晷|浑仪|简仪|星图", ["天文历法"]),
    (r"药炉|药盒|药匙|药罐|铜人|经络", ["医药"]),
]


def vocab_tags():
    v = json.loads(TAGS_VOCAB.read_text(encoding="utf-8"))
    out = set()
    for g in v["groups"]:
        out.update(g["tags"])
    return out


def rule_tags(r):
    text = " ".join(filter(None, [r.get("name"), r.get("category"), r.get("summary"),
                                  r.get("material"), r.get("dynasty")]))
    hits = []
    for pat, tags in CN_TAG_RULES:
        if re.search(pat, text):
            hits.extend(tags)
    hits.extend(map_tags(text))
    seen, out = set(), []
    for t in hits:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out[:5]


def iter_untagged():
    for f in sorted(RELICS.glob("*.json")):
        r = json.loads(f.read_text(encoding="utf-8"))
        if not r.get("tags"):
            yield f, r


def cmd_tag():
    LC.mkdir(parents=True, exist_ok=True)
    valid = vocab_tags()
    journal, by_pre, still = {}, {}, {}
    for f, r in iter_untagged():
        rid = r.get("relic_id", f.stem)
        pre = rid.split("-")[0]
        tags = [t for t in rule_tags(r) if t in valid]
        if not tags:
            still[pre] = still.get(pre, 0) + 1
            continue
        r["tags"] = tags
        f.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
        journal[rid] = tags
        by_pre[pre] = by_pre.get(pre, 0) + 1
    (LC / "tag_rules_applied.json").write_text(json.dumps(journal, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"规则打标 {len(journal)} 件 {by_pre}；剩余无标签 {still}（共 {sum(still.values())}）")


def cmd_prep():
    rows = []
    for f, r in iter_untagged():
        rows.append({
            "id": r.get("relic_id", f.stem),
            "name": r.get("name") or "",
            "category": r.get("category") or "",
            "dynasty": r.get("dynasty") or "",
            "material": (r.get("material") or "")[:100],
            "summary": (r.get("summary") or "")[:120],
            "museum": (r.get("collection") or {}).get("museum", ""),
        })
    with (LC / "C_tags_todo.jsonl").open("w", encoding="utf-8") as w:
        for row in rows:
            w.write(json.dumps(row, ensure_ascii=False) + "\n")
    by = {}
    for row in rows:
        pre = row["id"].split("-")[0]
        by[pre] = by.get(pre, 0) + 1
    print(f"C_tags_todo.jsonl: {len(rows)} rows {by}")


def cmd_merge():
    valid = vocab_tags()
    results = {}
    for f in sorted(LC.glob("C_result_*.jsonl")):
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except json.JSONDecodeError:
                print(f"  [warn] 非 JSON 行忽略: {f.name}")
                continue
            if d.get("id"):
                results[d["id"]] = d
    todo = [json.loads(l) for l in (LC / "C_tags_todo.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    apply_list, bad = [], []
    for t in todo:
        d = results.get(t["id"])
        if not d:
            bad.append({"id": t["id"], "why": "missing"})
            continue
        tags = [x for x in (d.get("tags") or []) if isinstance(x, str) and x in valid]
        if not tags:
            bad.append({"id": t["id"], "why": "no_valid_tags", "raw": d.get("tags")})
            continue
        apply_list.append({"id": t["id"], "tags": tags[:5]})
    (LC / "C_apply.json").write_text(json.dumps(apply_list, ensure_ascii=False, indent=1), encoding="utf-8")
    (LC / "C_reject.json").write_text(json.dumps(bad, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"结果 {len(results)} / 任务 {len(todo)} | 待应用 {len(apply_list)} | 拒绝 {len(bad)}")
    if bad:
        print("  拒绝样例:", bad[:5])


def cmd_apply():
    apply_list = json.loads((LC / "C_apply.json").read_text(encoding="utf-8"))
    journal = []
    for row in apply_list:
        p = RELICS / (row["id"] + ".json")
        r = json.loads(p.read_text(encoding="utf-8"))
        if r.get("tags"):
            continue  # 已有标签（如规则阶段已覆盖），不覆盖
        r["tags"] = row["tags"]
        journal.append({"id": row["id"], "tags": row["tags"]})
        p.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
    (LC / "apply_C_journal.json").write_text(json.dumps(journal, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"已打标 {len(journal)} 件，日志 -> apply_C_journal.json")


if __name__ == "__main__":
    cmd = sys.argv[1]
    {"tag": cmd_tag, "prep": cmd_prep, "merge": cmd_merge, "apply": cmd_apply}[cmd]()
