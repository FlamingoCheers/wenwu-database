import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from collectors.dynasty_util import COARSE_RANGES

ROOT = Path(__file__).resolve().parent.parent
RELICS = ROOT / "data" / "relics"
RES = [ROOT / "raw" / "llm_clean" / "G_gpm_dyn_result_01.jsonl",
       ROOT / "raw" / "llm_clean" / "G_gpm_dyn_result_02.jsonl"]

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

applied = kept_low = missing = 0
for rp in RES:
    for line in rp.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        v = json.loads(line)
        if v.get("confidence") == "low" or v.get("dynasty") == "不详":
            kept_low += 1
            continue
        fp = RELICS / (v["id"] + ".json")
        if not fp.exists():
            missing += 1
            continue
        d = json.loads(fp.read_text(encoding="utf-8"))
        d["dynasty"] = v["dynasty"]
        if not d.get("year_range"):
            for name, lo, hi in COARSE_RANGES:
                if name == v["dynasty"]:
                    d["year_range"] = [lo, hi]
                    break
        d["needs_review"] = False
        d["updated_at"] = "2026-09-25"
        fp.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
        applied += 1

print("applied=%d kept_low=%d missing=%d" % (applied, kept_low, missing))
