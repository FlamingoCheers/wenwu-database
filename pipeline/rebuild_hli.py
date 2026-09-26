import json, glob, os, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

jp = "raw/llm_clean/apply_C_journal.json"
journal = json.load(open(jp, encoding="utf-8"))
ids = journal.get("applied") if isinstance(journal, dict) else journal
print("journal applied:", len(ids))

vocab = json.load(open("data/vocab/tags.json", encoding="utf-8"))
ok_tags = set()
for grp in vocab.get("groups", []):
    ok_tags.update(grp.get("tags", []))

cache = {}
def load(rid):
    if rid not in cache:
        p = f"data/relics/{rid}.json"
        cache[rid] = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else None
    return cache[rid]

present = []
badvocab = []
for ent in ids:
    rid = ent.get("id") if isinstance(ent, dict) else ent
    r = load(rid)
    if r is None:
        continue
    present.append(rid)
    for t in r.get("tags") or []:
        if t not in ok_tags:
            badvocab.append((rid, t))

print("still present:", len(present))
print("vocab violations:", len(badvocab))

import re
need = []
for rid in present:
    r = load(rid)
    name = r.get("name") or ""
    summ = r.get("summary") or ""
    tags = r.get("tags") or []
    # 样本：标签与名称/摘要无明显对应关系的记录（低上下文标签）
    joined = name + summ
    if not any(t in joined for t in tags):
        need.append({
            "id": rid,
            "name": name,
            "dynasty": r.get("dynasty"),
            "category": r.get("category"),
            "tags": tags,
            "summary": summ[:160],
        })

print("low-context tag samples:", len(need))
with open("raw/llm_clean/H_li_todo.jsonl", "w", encoding="utf-8") as f:
    for it in need:
        f.write(json.dumps(it, ensure_ascii=False) + "\n")
print("wrote raw/llm_clean/H_li_todo.jsonl")
