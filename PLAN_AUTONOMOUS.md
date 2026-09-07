# 自主工作计划（无人值守执行）

> 用户外出期间按此计划顺序执行，每阶段完成即 commit+push，状态就地更新。
> 铁律：任何入库数据必须过 `pipeline/validate.py` 100% 合格才允许提交；
> 修改采集器后先用 `--limit` 小样本验证再全量；每阶段一个 commit。
> 最后更新：2026-09-04（启动时）

## Phase A · 修复 Met 全量爬取超时（最高优先级）

**事故**：run #1（33889351556）跑满 360min 被 cancel；串行+sleep 过慢（37,320 件逐件请求）；
raw 缓存被 gitignore → Actions 上无断点，进度全丢。

修复清单：
1. `collectors/met_collector.py`：增加 `--workers N`（线程池并发）+ 降低默认间隔
2. `.github/workflows/update-data.yml`：加 `actions/cache` 缓存 `raw/met/`（跨跑断点续爬）+ 跑 `met_collector --remap` 收尾
3. 重跑 dispatch，确认新增量入库 ≥ 数千件
- 状态：⬜ → 执行中

## Phase B · P0-0.1 朝代复核（609 件，规则法，无需 LLM）

`pipeline/infer_dynasty.py`：对 `dynasty=="不详"` 且有 `year_range` 的记录，用
`data/vocab/dynasties.json` 的 range 判定（含跨期取最长重叠），写入 dynasty +
`dynasty_confidence:"inferred"`，产出 `raw/_dynasty_review_report.json`。
验收：needs_review 大幅下降；抽样 20 件人工核对。
- 状态：⬜

## Phase C · P0-0.2 同名疑重复核（414 组，策略固化）

`pipeline/review_dupes.py`：读 `raw/_dedupe_report.json`，对每组施加严格判定——
同馆藏号视为重复（保留 relic_id 最小）；仅同名+年代重叠但馆藏号不同的**保留**并去掉疑重标记。
政策：开放数据中同名文物（如多件 "Vase"）默认是真实不同藏品，宁可保留不误删。
- 状态：⬜

## Phase D · 接入第三馆：芝加哥艺术馆 AIC（A 类，无 key，CC0）

`collectors/aic_collector.py`：`api.artic.edu/api/v1/artworks`，
`is_public_domain=true&has_image=1`，中文藏品用 `place_of_origin` / `style_titles` 过滤。
映射到统一 schema，接入 validate/build_db/dedupe。
验收：≥500 件入库过检；site 自动更新（deploy-pages 由 push 触发）。
- 状态：⬜

## Phase E · 国博试点（B 类，截图+OCR 流程验证）

先轻量侦察（curl 探 AJAX 端点能否直出 JSON——能则免 OCR）；
不行再上 Playwright 截图方案。验收：50 件端到端入库。
阻塞预案：反爬导致无法自动化 → 记录到 `collectors/nmc_recon.md` 并标 ⏸，转 Phase F。
- 状态：⬜

## Phase F · 台北故宫 open data 侦察（走 Actions runner 海外网络）

加 `npm-probe` workflow：runner 上 curl 探测 opendata.npm.gov.tw 整包地址与授权字段，
结果写回 `collectors/npm_recon.md`（artifact 取回）。采集器本体留下轮。
- 状态：⬜

## 收尾

更新 `ROADMAP.md` 各状态 + 本文件执行日志，汇总报告（新增件数/各馆分布/站点验证）。

## 执行日志

- 2026-09-04 计划固化；Phase A 启动（Met 超时事故确诊）。
