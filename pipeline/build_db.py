import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RELICS_DIR = ROOT / "data" / "relics"
DB_PATH = ROOT / "sqlite" / "relics.db"

SCHEMA = """
DROP TABLE IF EXISTS relics;
CREATE TABLE relics (
    relic_id     TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    aliases_json TEXT,
    dynasty      TEXT,
    dynasty_confidence TEXT,
    year_start   INTEGER,
    year_end     INTEGER,
    category     TEXT,
    material     TEXT,
    dimensions   TEXT,
    excavated_from TEXT,
    museum       TEXT,
    region       TEXT,
    inventory_no TEXT,
    summary      TEXT,
    source_url   TEXT,
    license      TEXT,
    tags_json    TEXT,
    images_json  TEXT,
    related_json TEXT,
    needs_review INTEGER DEFAULT 0,
    fetched_at   TEXT
);
DROP TABLE IF EXISTS relics_fts;
CREATE VIRTUAL TABLE relics_fts USING fts5(
    name, dynasty, museum, summary, tags_json,
    content='relics', content_rowid='rowid', tokenize='trigram'
);
CREATE INDEX idx_relics_category ON relics(category);
CREATE INDEX idx_relics_dynasty ON relics(dynasty);
CREATE INDEX idx_relics_museum ON relics(museum);
"""

def main():
    parser = argparse.ArgumentParser(description="构建 SQLite 快照（供前端与 Agent 检索）")
    parser.add_argument("--db", default=str(DB_PATH))
    args = parser.parse_args()

    files = sorted(RELICS_DIR.glob("*.json"))
    if not files:
        print("data/relics/ 下没有数据，先运行采集器")
        return 1

    Path(args.db).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(args.db)
    conn.executescript(SCHEMA)

    skipped = 0
    for path in files:
        try:
            r = json.loads(path.read_text(encoding="utf-8"))
            col = r.get("collection", {})
            conn.execute(
                "INSERT INTO relics VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    r["relic_id"], r.get("name", ""), json.dumps(r.get("aliases", []), ensure_ascii=False),
                    r.get("dynasty", "不详"), r.get("dynasty_confidence", "low"),
                    (r.get("year_range") or [None, None])[0], (r.get("year_range") or [None, None])[1],
                    r.get("category", "杂器"), r.get("material", ""), r.get("dimensions", ""),
                    r.get("excavated_from", ""), col.get("museum", ""), col.get("region", ""),
                    col.get("inventory_no", ""), r.get("summary", ""), r.get("source_url", ""),
                    r.get("license", ""), json.dumps(r.get("tags", []), ensure_ascii=False),
                    json.dumps(r.get("images", []), ensure_ascii=False),
                    json.dumps(r.get("related", []), ensure_ascii=False),
                    1 if r.get("needs_review") else 0, r.get("fetched_at", ""),
                ),
            )
        except Exception as exc:
            skipped += 1
            print(f"跳过 {path.name}: {exc}")

    conn.execute("INSERT INTO relics_fts(relics_fts) VALUES('rebuild')")
    conn.commit()

    total = conn.execute("SELECT COUNT(*) FROM relics").fetchone()[0]
    print(f"入库 {total} 条，失败跳过 {skipped} 条 → {args.db}")
    print("\n按类别：")
    for row in conn.execute("SELECT category, COUNT(*) FROM relics GROUP BY category ORDER BY 2 DESC LIMIT 10"):
        print(f"  {row[0]}: {row[1]}")
    print("\n按朝代：")
    for row in conn.execute("SELECT dynasty, COUNT(*) FROM relics GROUP BY dynasty ORDER BY 2 DESC LIMIT 10"):
        print(f"  {row[0]}: {row[1]}")
    conn.close()
    return 0

if __name__ == "__main__":
    sys.exit(main())
