# -*- coding: utf-8 -*-
"""Met trickle fetcher: single-thread, gentle pacing.

Evidence: bulk route showed Met's collection API enforces a short-burst quota
(~150-200 rapid requests then 403s; recovers within minutes). A 1 req/20s
probe passed 24/25 (the miss was a dead 404 id). So: crawl sequentially at
~1 req/2s, back off long on 403, permanently skip 404 ids, keep raw-cache
checkpoints so any run resumes where the last stopped.

Resume model:
  raw/met/{oid}.json   fetched object cache (checkpoint)
  raw/met/_skipped.json permanently skipped ids (non-PD / non-China / 404)
  data/relics/MET-{oid}.json final records
"""
import argparse
import json
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import met_bulk as mb
import met_collector as mc

TODAY = date.today().isoformat()
RAW_DIR = mc.RAW_DIR
RELICS_DIR = mc.RELICS_DIR


def fetch(oid):
    """Return cached-or-fresh object dict, or None if permanently unavailable."""
    raw_path = RAW_DIR / f"{oid}.json"
    if raw_path.exists():
        return json.loads(raw_path.read_text(encoding="utf-8"))
    for attempt in range(8):
        try:
            req = urllib_request(oid)
            return json.loads(req)
        except Exception as exc:
            code = getattr(exc, "code", None)
            if code == 404:
                print(f"  oid={oid} 404 dead id -> permanent skip", flush=True)
                return "404"
            wait = 180 * (attempt + 1) if code == 403 else 60
            print(f"  oid={oid} {type(exc).__name__} {code or ''} -> sleep {wait}s", flush=True)
            time.sleep(wait)
    return None


def urllib_request(oid):
    import urllib.request
    req = urllib.request.Request(
        f"{mc.API}/objects/{oid}", headers=mc.HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8")


def main():
    parser = argparse.ArgumentParser(description="Met 滴流采集（单线程，家宽友好）")
    parser.add_argument("--pace", type=float, default=2.0, help="请求间隔秒")
    parser.add_argument("--max-minutes", type=float, default=330, help="本次最长运行分钟数")
    parser.add_argument("--refresh-csv", action="store_true", help="强制重新下载 CSV")
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    RELICS_DIR.mkdir(parents=True, exist_ok=True)
    mb.download_csv(force=args.refresh_csv)
    ids = mb.load_china_pd_ids()
    print(f"bulk 过滤命中: {len(ids)}", flush=True)

    skip_file = RAW_DIR / "_skipped.json"
    skip_set = set(json.loads(skip_file.read_text(encoding="utf-8"))) if skip_file.exists() else set()
    todo = [i for i in ids if i not in skip_set and not (RELICS_DIR / f"MET-{i}.json").exists()]
    print(f"待处理 {len(todo)}（跳过集 {len(skip_set)}）", flush=True)

    deadline = time.time() + args.max_minutes * 60
    ok = skipped = noimg = dead = 0
    skip_new = []
    consec_403 = 0
    t_start = time.time()

    for n, oid in enumerate(todo, 1):
        if time.time() > deadline:
            print(f"到达 {args.max_minutes} 分钟时限，优雅退出", flush=True)
            break
        obj = fetch(oid)
        if obj == "404":
            dead += 1
            skip_new.append(oid)
            skip_set.add(oid)
            continue
        if obj is None:
            continue  # gave up after backoffs; raw cache still absent, retried next run
        raw_path = RAW_DIR / f"{oid}.json"
        if not raw_path.exists():
            raw_path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
            time.sleep(args.pace)
        if not obj.get("isPublicDomain"):
            skip_new.append(oid)
            skip_set.add(oid)
            skipped += 1
            continue
        cul = (obj.get("culture") or "").lower()
        if "china" not in cul:
            skip_new.append(oid)
            skip_set.add(oid)
            skipped += 1
            continue
        record = mc.to_record(obj)
        if not record["images"]:
            noimg += 1
            continue
        (RELICS_DIR / f"MET-{oid}.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
        ok += 1
        consec_403 = 0
        if n % 100 == 0:
            rate = n / max(1e-9, (time.time() - t_start)) * 60
            eta = (len(todo) - n) / max(rate, 1e-9) / 60
            print(f"进度 {n}/{len(todo)}  入库 {ok}  跳过 {skipped}  死ID {dead}  无图 {noimg}  ({rate:.0f}件/分, ETA {eta:.1f}h)", flush=True)

    if skip_new:
        skip_file.write_text(json.dumps(sorted(skip_set)), encoding="utf-8")
    print(f"完成：入库 {ok}  跳过 {skipped}  死ID {dead}  无图 {noimg}  剩余 {len(todo)-n}", flush=True)


if __name__ == "__main__":
    main()
