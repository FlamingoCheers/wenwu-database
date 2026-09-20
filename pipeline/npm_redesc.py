# -*- coding: utf-8 -*-
"""B2: NPM 回源重提取（零网络，跑在 Actions 缓存之上）

从 raw/npm/detail_*.html 重新解析表格字段：
- 說明 -> relic.summary（原 summary < 20 字时，截 300）
- 質材/材質 -> relic.material（原为空时）
只取「說明」字段：題跋/銘刻等折叠面板会混入 UI 残渣（expand_more 图标文字），
已验证不可用。含 UI 噪音的解析结果一律拒收。
不动其他字段。输出统计。

用法:
  python pipeline/npm_redesc.py --dry-run   # 只报告
  python pipeline/npm_redesc.py             # 写回 data/relics
"""
import argparse
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "collectors"))
import npm_collector as nc  # noqa: E402

RAW = ROOT / "raw" / "npm"
RELICS = ROOT / "data" / "relics"
TEXT_KEYS = ["說明"]
MATERIAL_KEYS = ["質材", "材質"]
NOISE_RE = re.compile(r"expand_more|expand_less|^\s*$")


def clean_text(text):
    lines = [ln.strip() for ln in (text or "").split("\n")]
    lines = [ln for ln in lines if ln and not NOISE_RE.search(ln)]
    return "\n".join(lines).strip()


def all_fields(html_text):
    fields = {}
    for k, v in nc.TR_RE.findall(html_text):
        k = nc._clean(k)
        if k and k not in fields:
            fields[k] = nc._clean(v)
    return fields


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-summary", type=int, default=300)
    args = ap.parse_args()

    stats = {"pages": 0, "relics": 0, "sum_filled": 0, "mat_filled": 0,
             "still_thin": 0, "no_relic": 0}
    changed = []
    for p in sorted(RAW.glob("detail_*.html")):
        stats["pages"] += 1
        oid = p.stem.split("_")[1]
        rid = f"NPM-{oid}"
        rp = RELICS / f"{rid}.json"
        if not rp.exists():
            stats["no_relic"] += 1
            continue
        r = json.loads(rp.read_text(encoding="utf-8"))
        stats["relics"] += 1
        fields = all_fields(p.read_text(encoding="utf-8", errors="replace"))

        new_summary = None
        if len((r.get("summary") or "").strip()) < 20:
            parts = [clean_text(fields.get(k, "")) for k in TEXT_KEYS]
            parts = [x for x in parts if len(x) >= 10]
            if parts:
                new_summary = "\n".join(parts)[: args.max_summary]
        new_material = None
        if not (r.get("material") or "").strip():
            for k in MATERIAL_KEYS:
                if fields.get(k):
                    new_material = fields[k][:200]
                    break

        if new_summary:
            stats["sum_filled"] += 1
        else:
            stats["still_thin"] += 1
        if new_material:
            stats["mat_filled"] += 1
        if new_summary or new_material:
            changed.append(rid)
            if not args.dry_run:
                if new_summary:
                    r["summary"] = new_summary
                if new_material:
                    r["material"] = new_material
                r["updated_at"] = date.today().isoformat()
                rp.write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")

    print(json.dumps(stats, ensure_ascii=False))
    print(f"待写入 {len(changed)} 件" + ("（dry-run 未写入）" if args.dry_run else ""))
    if changed[:5]:
        print("样例:", changed[:5])


if __name__ == "__main__":
    main()
