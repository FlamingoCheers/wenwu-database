"""Rewrite NPM source_url dep letters from a fresh oid->dep mapping.

Usage:
    python pipeline/fix_npm_dep.py raw/npm_repair/pairs.json [--apply]

Without --apply, prints a report only. Rewrites source_url in
data/relics/NPM-*.json when the mapping dep differs from the stored one.
"""
import glob
import json
import re
import sys

PAIRS_FILE = sys.argv[1] if len(sys.argv) > 1 else "raw/npm_repair/pairs.json"
APPLY = "--apply" in sys.argv

pairs = json.load(open(PAIRS_FILE, encoding="utf-8"))
print(f"mapping: {len(pairs)} oids")

changed, unchanged, missing = 0, 0, []
sample = []
for f in glob.glob("data/relics/NPM-*.json"):
    rec = json.load(open(f, encoding="utf-8"))
    oid = rec["relic_id"].split("-", 1)[1]
    url = rec.get("source_url") or ""
    m = re.search(r"Detail/(\d+)\?dep=([A-Z])", url)
    if not m:
        missing.append(rec["relic_id"])
        continue
    cur = m.group(2)
    new = pairs.get(oid)
    if new is None:
        missing.append(rec["relic_id"])
        continue
    if new == cur:
        unchanged += 1
        continue
    changed += 1
    if len(sample) < 8:
        sample.append((rec["relic_id"], rec.get("name", "")[:24], cur, new))
    if APPLY:
        rec["source_url"] = re.sub(
            r"(Detail/\d+\?dep=)[A-Z]", r"\g<1>" + new, url)
        rec["updated_at"] = __import__("datetime").date.today().isoformat()
        with open(f, "w", encoding="utf-8") as fh:
            json.dump(rec, fh, ensure_ascii=False, indent=1)

print(f"changed={changed} unchanged={unchanged} missing_from_mapping={len(missing)}")
for s in sample:
    print("  ", s)
if missing:
    print("missing sample:", missing[:8])
if not APPLY:
    print("(dry-run; rerun with --apply to write)")
