# -*- coding: utf-8 -*-
"""词表新增「现当代」：按原文件紧凑单行风格插入，不重排整个 JSON（幂等）。"""
import io, os, sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VP = os.path.join(ROOT, "data", "vocab", "dynasties.json")

raw = open(VP, encoding="utf-8").read()
if '"现当代"' in raw:
    print("vocab: 现当代 已存在，跳过")
    sys.exit(0)

anchor = '    { "key": "近代", "aliases": ["民国", "民国时期", "清代晚期"], "range": [1912, 1949] },\n'
if anchor not in raw:
    print("未找到「近代」锚点行，需手工检查", file=sys.stderr)
    sys.exit(1)

newline = '    { "key": "现当代", "aliases": ["现代", "当代"], "range": [1949, 2026] },\n'
out = raw.replace(anchor, anchor + newline, 1)
with open(VP, "w", encoding="utf-8", newline="\n") as f:
    f.write(out)
print("vocab: 已在「近代」后插入「现当代」")
