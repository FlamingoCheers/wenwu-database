# -*- coding: utf-8 -*-
"""P0-0.1 朝代复核：对 dynasty=="不详" 且有 year_range 的记录，用词表 range 推断。

策略：
- 取 [begin,end] 与各朝代 range 的重叠长度，最长重叠且覆盖率≥60% 则判定
- 判定写 dynasty + dynasty_confidence="inferred"，needs_review 保持 False
- 完全判不了的维持现状，记入报告
产出：raw/_dynasty_review_report.json
"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
VOCAB = ROOT / "data" / "vocab" / "dynasties.json"
RELICS = ROOT / "data" / "relics"
REPORT = ROOT / "raw" / "_dynasty_review_report.json"

MIN_OVERLAP_RATIO = 0.6  # 文物年代区间被朝代区间覆盖的比例下限


def load_ranges():
    data = json.loads(VOCAB.read_text(encoding="utf-8"))
    out = []
    for d in data["dynasties"]:
        key = d["key"]
        rng = d.get("range")
        if not rng or rng[0] is None:
            continue
        out.append((key, int(rng[0]), int(rng[1])))
    return out


def infer(begin, end, ranges):
    """返回 (dynasty, overlap, ratio) 或 None。跨期（如 南北朝跨多朝）取最长重叠。"""
    if begin is None or end is None or begin > end:
        return None
    span = end - begin + 1
    best = None
    for key, lo, hi in ranges:
        ov = min(end, hi) - max(begin, lo) + 1
        if ov <= 0:
            continue
        ratio = ov / span
        if ratio >= MIN_OVERLAP_RATIO and (best is None or ov > best[1]):
            best = (key, ov, ratio)
    return best


def main():
    ranges = load_ranges()
    reviewed = inferred = unchanged = 0
    samples, unresolved = [], []

    for f in sorted(RELICS.glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        if d.get("dynasty") not in ("", None, "不详") or d.get("needs_review") is not True:
            continue
        reviewed += 1
        yr = d.get("year_range") or [None, None]
        hit = infer(yr[0], yr[1], ranges)
        if hit and len(hit[0]) <= 6:  # 排除超宽泛词条误配（理论上不会出现）
            key, ov, ratio = hit
            d["dynasty"] = key
            d["dynasty_confidence"] = "inferred"
            d["needs_review"] = False
            f.write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
            inferred += 1
            if len(samples) < 40:
                samples.append({"id": d["relic_id"], "years": yr, "to": key, "overlap": ov, "ratio": round(ratio, 2)})
        else:
            unchanged += 1
            if len(unresolved) < 40:
                unresolved.append({"id": d["relic_id"], "years": yr, "name": d.get("name", "")})

    report = {"reviewed": reviewed, "inferred": inferred, "unresolved": unchanged,
              "policy": "overlap>=60%, longest wins", "samples_inferred": samples,
              "samples_unresolved": unresolved}
    REPORT.parent.mkdir(exist_ok=True)
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"复核 {reviewed}  推断 {inferred}  无法判定 {unchanged} -> {REPORT.name}")


if __name__ == "__main__":
    main()
