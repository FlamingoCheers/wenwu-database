# 自主工作计划（无人值守执行）

> 用户外出期间按此计划顺序执行，每阶段完成即 commit+push，状态就地更新。
> 铁律：任何入库数据必须过 `pipeline/validate.py` 100% 合格才允许提交；
> 修改采集器后先用 `--limit` 小样本验证再全量；每阶段一个 commit。
> 最后更新：2026-09-07

## Phase A · 修复 Met 全量爬取超时（最高优先级）

**事故**：run #1（33889351556）跑满 360min 被 cancel；串行+sleep 过慢（37,320 件逐件请求）；
raw 缓存被 gitignore → Actions 上无断点，进度全丢。

修复清单：
1. `collectors/met_collector.py`：增加 `--workers N`（线程池并发）+ 降低默认间隔
2. `.github/workflows/update-data.yml`：加 `actions/cache` 缓存 `raw/met/`（跨跑断点续爬）+ 跑 `met_collector --remap` 收尾
3. 重跑 dispatch，确认新增量入库 ≥ 数千件
- 状态：✅（并发+cache 已提交 6fcfa3d；9-07 已 dispatch head=110af4a 的重爬，
  含 culture 过滤；结果待查）

### 事故附记：Met 非中国藏品污染（9-07 发现并治理）
met_collector 按 departmentIds=6（亚洲艺术部）拉取，未过滤国别 → 日本 975、
印尼 163、泰/印/藏/犍陀罗等混入。修复：work() 加 culture 含 "china" 过滤；
按 raw 缓存 culture 判定删除 2,142 件非中国记录；取消跑旧逻辑的 Actions run。

## Phase B · P0-0.1 朝代复核（609 件，规则法，无需 LLM）

`pipeline/infer_dynasty.py`：对 `dynasty=="不详"` 且有 `year_range` 的记录，用
`data/vocab/dynasties.json` 的 range 判定（含跨期取最长重叠），写入 dynasty +
`dynasty_confidence:"inferred"`，产出 `raw/_dynasty_review_report.json`。
验收：needs_review 大幅下降；抽样 20 件人工核对。
- 状态：✅（609 → 445 推断 + 164 真跨期保留；commit b6f999d）

## Phase C · P0-0.2 同名疑重复核（414 组，策略固化）

`pipeline/review_dupes.py`：读 `raw/_dedupe_report.json`，对每组施加严格判定——
同馆藏号视为重复（保留 relic_id 最小）；仅同名+年代重叠但馆藏号不同的**保留**并去掉疑重标记。
政策：开放数据中同名文物（如多件 "Vase"）默认是真实不同藏品，宁可保留不误删。
- 状态：✅（同馆藏号重复 0 组；同名+重叠 414 组按政策保留，报告在 raw/_dedupe_report.json）

## Phase D · 接入第三馆：芝加哥艺术馆 AIC（A 类，无 key，CC0）

`collectors/aic_collector.py`：`api.artic.edu/api/v1/artworks`，
`is_public_domain=true&has_image=1`，中文藏品用 `place_of_origin` / `style_titles` 过滤。
映射到统一 schema，接入 validate/build_db/dedupe。
验收：≥500 件入库过检；site 自动更新（deploy-pages 由 push 触发）。
- 状态：✅（2,803 件入库；深分页窗口 ~3600 限制损失约 8% 已记录；commit 244b7f1）

## Phase E · 国博试点（B 类，截图+OCR 流程验证）

先轻量侦察（curl 探 AJAX 端点能否直出 JSON——能则免 OCR）；
不行再上 Playwright 截图方案。验收：50 件端到端入库。
阻塞预案：反爬导致无法自动化 → 记录到 `collectors/nmc_recon.md` 并标 ⏸，转 Phase F。
- 状态：✅（超预期：实测为纯静态分页 112 页×12 件≈1,344 件，无需截图 OCR；
  `collectors/nmc_collector.py` 试点 52 件入库全合格，commit 110af4a。
  注意：详情页无结构化年代 → 卡片年代+描述关键词推断，其余待 LLM 审核阶段）

### 附记：dynasty_util 补中文映射（9-07）
此前 DYNASTY_MAP 仅英文词+年份，中文朝代词（春秋/清/新石器）全部漏判。
新增 CH_DYN_STRONG（短字段单字词+负向断言防鎏金/公元/说明误伤）与
CH_DYN_WEAK（长文本仅认"代/朝/初/末"复合词）两级表；
nmc_collector 类别映射为名称优先两轮扫描（防描述词劫持）。

## Phase F · 台北故宫 open data 接入（走 Actions runner 海外网络）

probe1-7 探明（9-07）：`theme.npm.edu.tw/opendata` 已整站迁移到
**`digitalarchive.npm.gov.tw/opendata`**（本地大陆网络不可达，runner 直连正常）。
POST `/opendata/Pub/Search`（application/json，body 含 YearDisplay "起~止~朝代" +
WestBeginYear/WestEndYear + PageInfo）返回整页 HTML 列表（每页 15 条，响应内含 PageCount）；
详情页 `/opendata/Pub/Detail/{id}?dep=U&mode=full` 为 td/td 字段表
（文物統一編號/品名中英/分類/時代+西元年/尺寸/說明）；
图片 `data-image="/opendata/Image/GetImage?imageId=..&randomCode=.."` 直接可取
（100万/600万像素下载才需验证码，中图够用）；授权 CC0 1.0 或 CC BY 4.0（页内徽章）。
`collectors/npm_collector.py`：按朝代轴采集（--dynasty 中文或英文 key song/ming/...
—— dispatch 输入中文会被 ASCII 化成 "?"，必须用英文 key），--remap 免网重映射；
`.github/workflows/npm-sync.yml` 手动按朝代 dispatch（crawl → remap → validate → commit）。
- 状态：✅ 试点 20 件全合格入库；宋轴全量运行中（run 34095173027）；
  朝代映射表补漏（CH_DYN_STRONG/WEAK 之前整条"宋"系缺失，COARSE_RANGES 补
  ("宋",960,1279) 粗区间，commit ae3ee02）。后续：其余朝代轴逐个 dispatch。

## 收尾

更新 `ROADMAP.md` 各状态 + 本文件执行日志，汇总报告（新增件数/各馆分布/站点验证）。

## 执行日志

- 2026-09-04 计划固化；Phase A 启动（Met 超时事故确诊）。
- 2026-09-07 Phase A 污染治理（删 2,142 件非中国记录）+ Phase B/C/D 完成
  （commit b6f999d / 244b7f1）；Phase E 国博试点完成（110af4a）；
  Phase F probe 已 dispatch；Met 全量重爬（culture 过滤）dispatch 后台运行。
- 2026-09-07(下午) Phase F 完成：probe5-7 打通新域名+搜索/详情/图片/授权全链路；
  npm_collector + npm-sync 上线（8eee482 / ae3ee02）；朝代映射补宋系漏项；
  宋轴全量后台运行中；Met 全量重爬仍在进行（06:40Z 起）。
