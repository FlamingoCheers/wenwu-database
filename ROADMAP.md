# ROADMAP · 工作表

> 固化版执行计划，随进度更新状态。详细背景见 `工作规划.md`。
> 状态图例：✅ 完成 · 🔄 进行中 · ⬜ 待办 · ⏸ 受阻
> 最后更新：2026-09-23

## 当前基线

- 定位：**纯文物数据库**（数据采集 + 质检 + 静态检索前端，无内容生产）
- 数据：**28,315 件**（台北故宫 11,302 + Met 10,581 + 克利夫兰 2,804 + 陕西历史博物馆 1,515 + 国博 1,294 + 芝加哥 802 + 河南博物院 17），质检合格率 100%，needs_review 6,188
- 仓库：github.com/FlamingoCheers/wenwu-database（公开），Pages 已上线（https://flamingocheers.github.io/wenwu-database/ ），数据推送自动重新部署
- **采集限速政策**：国内博物馆（含国博及省级馆）一律 ≤ 100 件 / 6 小时 / 馆（`nmc-sync.yml` cron "20 */6"、`hn-sync.yml` cron "40 */6" 已按此实现）；台北故宫与海外馆不受此限
- 已知问题：9-11 起每周 update-data（Met 增量）因 Met API 连续失败触发熔断（`circuit breaker: consec=100`）而失败，暂挂起待修；SQLite 快照由 nmc-sync 每次重建兜底

---

## P1 · 检索前端 ✅（已上线 https://flamingocheers.github.io/wenwu-database/ ）

| # | 任务 | 产出 | 状态 |
|---|------|------|------|
| 1.1 | 设计稿确认 | `web/design/mockup.html` | ✅ |
| 1.2 | Web 索引构建器 | `pipeline/build_web_index.py` → `web/data/index.json.gz`（约 2MB） | ✅ |
| 1.3 | 静态站实现 | `web/index.html` + css + js：搜索/朝代/类别筛选/详情弹层/同名钱币聚合页（#coins/#coin=）/朝代序排序（do 字段） | ✅ |
| 1.4 | GitHub Pages 部署 | `deploy-pages.yml`（push + workflow_run 触发链） | ✅ |
| 1.5 | 移动端 + SEO | 响应式 + meta/OG + sitemap | ⬜ |

---

## P0 · 数据质量工程 ✅（2026-09-22 ~ 09-23 六轮迭代）

| 轮次 | 内容 | 结果 |
|------|------|------|
| A 分类复核 | 词表 18 类 + LLM 分片复核 323 疑误 | ✅ 改判 149 |
| B 描述补全 | MET/NMC 回源探查 + LLM 兜底 3,426（NPM 官方说明回源失败已回滚） | ✅ desc_ai 4,060+ |
| C 标签补全 | 规则打标 9,962 + LLM 4,336 + 文房回填 | ✅ 14,317 件 |
| 朝代修正 | NPM 世纪误读 bug 修复、位置优先 map_dynasty、audit_dynasty 规则审计 1,271 条、QA 复核 31 条、册页/年号钱/仿古专项 ~2,600 条 | ✅ |
| 外域清理 | 全库扫描，删除非中国文物 72 件（痕都斯坦玉等清宫旧藏保留） | ✅ |
| NPM 源址修复 | dep 字母迁移探测 + 全站重配对（2,749 条 source_url 改写） | ✅ |

> 数据规范：`desc_ai=true` 表示 LLM 生成描述（均置 needs_review）；`历史影像` 为新增类目（126 条照片类）； SXHM/HN 无图为源站特性，validate 已豁免。

---

## P2 · 数据扩源

| # | 任务 | 产出 | 状态 |
|---|------|------|------|
| 2.1 | 国博全量 | `nmc_collector.py` + `nmc-sync.yml`（每 6h ≤100） | ✅ 全量 1,294 件（含历史影像 126） |
| 2.2 | 台北故宫 open data | `npm_collector.py`（Actions runner） | 🔄 11,302 件；余朝代逐批 dispatch |
| 2.6 | 陕西历史博物馆 | `sxhm_collector.py`（35 张 Excel 清单 1,513 钱币品种）+ 精品页 playwright 18 件 | ✅ 1,515 件 |
| 2.7 | 河南博物院 | `hn_collector.py`（playwright 收割列表 96 条 + 静态详情）+ `hn-sync.yml`（每 6h ≤100） | 🔄 17 件，cron 增量中 |
| 2.8 | 其他省级馆探查 | Actions 实测：山西/浙江/湖北/天津/辽宁/南京（海外 IP 屏蔽）、湖南（新库超时+国宝栏仅照片无文字）、上海（无公开列表接口）、首都（ugi 令牌门禁 API） | ⏸ 按授权放弃，馆方开放后再评估 |
| 2.3 | 香港故宫 / 史密森尼 API | — | ⬜ |
| 2.4 | 跨馆去重 | — | ⬜ |
| 2.5 | 图片本地化策略 | — | ⬜ |

---

## P3 · 运营化（精简后）

| # | 任务 | 状态 |
|---|------|------|
| 3.1 | needs_review 复核工作流（当前 6,188 条，主要为 desc_ai 待人工确认） | ⬜ |
| 3.2 | 质量看板 / 数据统计页 | ⬜ |
| 3.3 | Met 周更修复（熔断待查） | ⏸ |

> 原内容生产流水线（选题/编辑/推文 Agent）已按"纯数据库"定位移除。

## 执行节奏建议

1. **当前**：HN cron 增量收尾 → 2.2 台北故宫余朝代批次
2. **下一步**：2.3 香港故宫/史密森尼 → 2.4 跨馆去重
3. **穿插**：3.1 needs_review 复核、3.3 Met 周更修复
