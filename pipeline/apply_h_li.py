import json, glob, re, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

vocab = json.load(open("data/vocab/tags.json", encoding="utf-8"))
ok_tags = set()
for grp in vocab.get("groups", []):
    ok_tags.update(grp.get("tags", []))

APPLY = "--apply" in sys.argv

changes = 0

# 1) 显式判定（5 个 verdict 分片，只应用 action==fix 的行）
for vf in sorted(glob.glob("raw/llm_clean/H_li_verdict_*.jsonl")):
    for line in open(vf, encoding="utf-8"):
        v = json.loads(line)
        if v.get("action") != "fix":
            continue
        tags = [t for t in v.get("tags", []) if t in ok_tags]
        p = f"data/relics/{v['id']}.json"
        r = json.load(open(p, encoding="utf-8"))
        if r.get("tags") != tags:
            print("fix", v["id"], r.get("tags"), "->", tags)
            if APPLY:
                r["tags"] = tags
                r["updated_at"] = __import__("datetime").datetime.now().isoformat(timespec="seconds")
                json.dump(r, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
            changes += 1

# 2) 全局模式规则（源自抽查发现的系统性误标）
WATER = re.compile(r"水盂|水盛|水注|笔洗|砚|鎮紙|镇纸|水丞|Water\s+(Coupe|Pot|Dropper)|Ink\s+(pallet|pot|stone)", re.I)
JEWEL = re.compile(r"坠饰|佩饰|项圈|簪|钗|耳坠|佩璜")
for p in glob.glob("data/relics/*.json"):
    r = json.load(open(p, encoding="utf-8"))
    tags = r.get("tags") or []
    name = r.get("name") or ""
    new = list(tags)
    if "文字书写" in new and "文房" not in new and WATER.search(name):
        new.remove("文字书写")
        new.append("文房")
    if "服饰" in new and "首饰" not in new and JEWEL.search(name):
        new.remove("服饰")
        new.append("首饰")
    if new != tags:
        print("rule", r["relic_id"], tags, "->", new)
        if APPLY:
            r["tags"] = new
            r["updated_at"] = __import__("datetime").datetime.now().isoformat(timespec="seconds")
            json.dump(r, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        changes += 1

print("total changes:", changes, "(APPLY)" if APPLY else "(DRY)")
