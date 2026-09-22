"""QA 复核结果应用: D_qa_result_{a,b}.jsonl -> data/relics. 只应用 confidence!=low 且非 SKIP."""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "collectors"))
import dynasty_util as du  # noqa: E402

COARSE = {k: (lo, hi) for k, lo, hi in du.COARSE_RANGES}
SKIP = {"NPM-15318", "NPM-1752"}  # 金星砚(证据不充分)、准提咒镜(low) 维持原判
now = datetime.now(timezone.utc).isoformat(timespec="seconds")

applied = []
for part in ("a", "b"):
    for line in (ROOT / "raw" / "llm_clean" / f"D_qa_result_{part}.jsonl").read_text(encoding="utf-8").splitlines():
        e = json.loads(line)
        if e["confidence"] == "low" or e["id"] in SKIP:
            continue
        p = ROOT / "data" / "relics" / f"{e['id']}.json"
        r = json.loads(p.read_text(encoding="utf-8"))
        if r["dynasty"] == e["dynasty"]:
            continue
        r["dynasty"] = e["dynasty"]
        r["dynasty_confidence"] = e["confidence"]
        yr = COARSE.get(e["dynasty"])
        if yr:
            cur = r.get("year_range")
            # 现区间缺失, 或明显是先秦粗兜底残留而新朝代在秦以后 -> 换成新朝代粗区间
            if cur is None or cur[0] < -2000:
                r["year_range"] = list(yr)
        r["updated_at"] = now
        p.write_text(json.dumps(r, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        applied.append((e["id"], r["name"][:22], e["dynasty"]))

print("applied", len(applied))
for a in applied:
    print(*a)
