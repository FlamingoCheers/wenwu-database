# -*- coding: utf-8 -*-
"""Met bulk CSV route: filter official openaccess dump, then fetch details only
for the China public-domain subset.

Why: collectionapi rate-limits datacenter IPs hard (a 15k-object run saw 99.4%
failures); the bulk CSV comes from GitHub's own CDN and survives on runners.
This cuts per-run object requests from ~37k to the China/PD subset (~6k).

Resilience: 429 -> Retry-After/60s backoff; 5xx -> stepped backoff; a run of
consecutive failures trips a circuit breaker instead of spinning for hours.
"""
import argparse
import csv
import io
import json
import sys
import time
import urllib.request
import urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import met_collector as mc

CSV_URL = "https://media.githubusercontent.com/media/metmuseum/openaccess/master/MetObjects.csv"
TODAY = date.today().isoformat()
RAW_DIR = mc.RAW_DIR
RELICS_DIR = mc.RELICS_DIR
CSV_PATH = RAW_DIR / "MetObjects.csv"
LFS_MARK = b"version https://git-lfs.github.com/spec/v1"


def download_csv(force=False):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if (CSV_PATH.exists() and CSV_PATH.stat().st_size > 50 * 1024 * 1024
            and not force and not CSV_PATH.open("rb").read(len(LFS_MARK)) == LFS_MARK):
        print(f"bulk CSV cached: {CSV_PATH} ({CSV_PATH.stat().st_size // 1048576} MB)", flush=True)
        return
    print("downloading MetObjects.csv (LFS media URL) ...", flush=True)
    req = urllib.request.Request(CSV_URL, headers=mc.HEADERS)
    tmp = CSV_PATH.with_suffix(".part")
    with urllib.request.urlopen(req, timeout=900) as resp, open(tmp, "wb") as f:
        total = 0
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            total += len(chunk)
            if total % (20 << 20) < (1 << 20):
                print(f"  {total // 1048576} MB", flush=True)
    tmp.rename(CSV_PATH)
    head = CSV_PATH.open("rb").read(len(LFS_MARK))
    if head == LFS_MARK or total < 50 * 1024 * 1024:
        CSV_PATH.unlink(missing_ok=True)
        raise SystemExit(f"downloaded file is not the real CSV ({total} bytes, head={head[:40]!r})")
    print(f"done: {total // 1048576} MB", flush=True)


def load_china_pd_ids():
    """Filter Asian Art + public domain + culture contains 'china'."""
    ids = []
    with open(CSV_PATH, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        cols = reader.fieldnames or []
        need = ["Object ID", "Is Public Domain", "Department", "Culture"]
        missing = [c for c in need if c not in cols]
        if missing:
            raise SystemExit(f"CSV columns missing {missing}; got: {cols[:12]} ...")
        for row in reader:
            if row["Department"] != "Asian Art":
                continue
            if row["Is Public Domain"] != "True":
                continue
            if "china" in (row["Culture"] or "").lower():
                ids.append(int(row["Object ID"]))
    return sorted(set(ids))


def get_json(url, retries=8):
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=mc.HEADERS)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            last = exc
            if exc.code == 429:
                wait = 90.0
                ra = exc.headers.get("Retry-After") if exc.headers else None
                if ra:
                    try:
                        wait = max(wait, float(ra))
                    except ValueError:
                        pass
                print(f"  429 rate-limited, sleeping {wait:.0f}s", flush=True)
                time.sleep(wait)
                continue
            if exc.code in (500, 502, 503, 504):
                time.sleep(min(60, 5 * (attempt + 1)))
                continue
            raise
        except Exception as exc:  # URLError / timeout / decode
            last = exc
            time.sleep(min(60, 5 * (attempt + 1)))
    raise last


def main():
    parser = argparse.ArgumentParser(description="Met bulk-CSV 采集器（中国 PD 子集）")
    parser.add_argument("--limit", type=int, default=0, help="本次处理对象数上限（含跳过），0=全量")
    parser.add_argument("--sleep", type=float, default=1.0, help="每请求间隔秒（每线程）")
    parser.add_argument("--workers", type=int, default=2, help="并发线程数")
    parser.add_argument("--force", action="store_true", help="覆盖已存在的记录")
    parser.add_argument("--csv-only", action="store_true", help="仅下载并过滤 CSV，不拉详情")
    parser.add_argument("--refresh-csv", action="store_true", help="强制重新下载 CSV")
    args = parser.parse_args()

    download_csv(force=args.refresh_csv)
    ids = load_china_pd_ids()
    print(f"bulk 过滤命中（亚洲艺术部+PD+中国）: {len(ids)} 件", flush=True)

    skip_file = RAW_DIR / "_skipped.json"
    skip_set = set(json.loads(skip_file.read_text(encoding="utf-8"))) if skip_file.exists() else set()
    todo = []
    skipped = 0
    for oid in ids:
        if oid in skip_set:
            skipped += 1
            continue
        if (RELICS_DIR / f"MET-{oid}.json").exists() and not args.force:
            skipped += 1
            continue
        todo.append(oid)
    print(f"待拉详情 {len(todo)}  已跳过 {skipped}", flush=True)
    if args.csv_only:
        (RAW_DIR / "_bulk_ids.json").write_text(json.dumps(ids), encoding="utf-8")
        return

    ok = failed = 0
    failures = []
    skip_new = []
    consec_fail = 0
    done_n = 0

    def work(oid):
        raw_path = RAW_DIR / f"{oid}.json"
        try:
            if raw_path.exists():
                obj = json.loads(raw_path.read_text(encoding="utf-8"))
            else:
                obj = get_json(f"{mc.API}/objects/{oid}")
                raw_path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
                time.sleep(args.sleep)
            if not obj.get("isPublicDomain"):
                return ("skip", oid, None)
            cul = (obj.get("culture") or "").lower()
            if "china" not in cul:
                return ("skip", oid, None)
            record = mc.to_record(obj)
            if not record["images"]:
                return ("skip", oid, None)
            (RELICS_DIR / f"MET-{oid}.json").write_text(
                json.dumps(record, ensure_ascii=False, indent=1), encoding="utf-8")
            return ("ok", oid, None)
        except Exception as exc:
            return ("fail", oid, str(exc))

    aborted = False
    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futures = [ex.submit(work, oid) for oid in todo]
        for fut in as_completed(futures):
            status, oid, err = fut.result()
            done_n += 1
            if status == "ok":
                ok += 1
                consec_fail = 0
            elif status == "skip":
                skip_new.append(oid)
                skipped += 1
                consec_fail = 0
            else:
                failed += 1
                consec_fail += 1
                failures.append({"objectID": oid, "error": err})
                if failed % 100 == 1:
                    print(f"  fail sample: {err}", flush=True)
            if done_n % 200 == 0:
                print(f"进度 {done_n}/{len(todo)}  入库 {ok}  跳过 {skipped}  失败 {failed}", flush=True)
            broke = consec_fail >= 100 or (done_n >= 500 and failed > done_n * 0.6)
            if broke:
                print(f"::error::circuit breaker: consec={consec_fail} failed={failed}/{done_n}, aborting", flush=True)
                aborted = True
                for f2 in futures:
                    f2.cancel()
                break
            if args.limit and done_n >= args.limit:
                for f2 in futures:
                    f2.cancel()
                break

    if skip_new:
        skip_set.update(skip_new)
        skip_file.write_text(json.dumps(sorted(skip_set)), encoding="utf-8")
    if failures:
        (RAW_DIR / "_failures.json").write_text(
            json.dumps(failures, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"完成：入库 {ok}  跳过 {skipped}  失败 {failed}" + ("  [已熔断]" if aborted else ""), flush=True)
    sys.exit(1 if (aborted or (todo and failed > len(todo) * 0.5)) else 0)


if __name__ == "__main__":
    main()
