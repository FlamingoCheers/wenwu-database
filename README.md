# wenwu-database 文物数据库

聚合全球博物馆公开数据的中文文物数据库 + 每日自动选题成文的内容流水线。

> **不做单件文物的介绍，而是"文物组合"叙事**——用一组相互关联的文物，还原一种历史生活状态或一个历史事件，进而联系当下、探讨人性。

## 三大交付物

| 交付物 | 形态 | 状态 |
|---|---|---|
| ① 文物数据库 | 本仓库：结构化 JSON + SQLite 快照 + 图片链接 | 🚧 P0：已入库 5,239 件（Met 2,435 + 克利夫兰 2,804） |
| ② 检索前端 | 静态站（GitHub Pages），按朝代/类别/主题/馆藏搜索 | 📅 P1 |
| ③ 内容流水线 | 每日自动：选题Agent → 文物专家Agent → 编辑Agent，产出公众号+小红书推文（人工过目后发布） | 📅 P2–P3 |

当前数据规模：**5,239 件**（大都会艺术博物馆 2,435 + 克利夫兰艺术博物馆 2,804，均 CC0）。分布概览见 `pipeline/build_db.py` 输出或 `raw/_validation_report.json`。

## 目录结构

```
├── schemas/            # 数据 Schema（JSON Schema）
├── collectors/         # 各数据源采集器（A类 API；B类 截图+OCR，每馆一个）
├── pipeline/           # 清洗、去重、打标、质检、构建 SQLite/索引
├── data/
│   ├── relics/         # 文物 JSON（一物一文件）
│   ├── vocab/          # 受控词表：朝代/类别/地区/主题标签
│   └── museums.json    # 博物馆名录与数据源配置
├── raw/                # 原始数据（gitignore，可重取）
├── web/                # 检索前端（P1）
├── agents/             # Agent 流水线（P2–P3）：选题/文物专家/编辑/总协调
├── output/articles/    # 每日产出的推文
├── 工作规划.md          # 完整工作规划（先读这个）
└── .github/workflows/  # 定时任务：增量采集 / 索引构建 / 每日成稿
```

## 快速开始

```bash
# 1. 采集（大都会博物馆 Open Access，CC0）
python collectors/met_collector.py --limit 50        # 试跑 50 件
python collectors/met_collector.py --limit 0         # 全量（亚洲艺术部）

# 2. 构建 SQLite 快照（供检索/Agent 使用）
python pipeline/build_db.py
```

## 数据规范

- 每件文物一条 JSON：`data/relics/{relic_id}.json`，Schema 见 `schemas/relic.schema.json`
- `relic_id` 格式：`{馆代码}-{馆藏号}`，如 `MET-12345`
- 朝代/类别/地区/主题标签必须归一到 `data/vocab/` 受控词表
- 每条记录必带 `source_url` 与授权字段，全程可溯源

## 数据来源与授权

| 类型 | 来源 | 接入方式 | 授权 |
|---|---|---|---|
| A | 大都会博物馆、克利夫兰、史密森尼、哈佛等 | Open Access API | CC0 / 开放授权 |
| A | 台北故宫博物院 | Open Data 专区 | 开放授权 |
| B | 中国国家博物馆（**试点馆**）、故宫博物院等 | 浏览器实开网页 + 截图 + OCR（不做爬虫，不绕过任何防护） | 图片版权归馆藏机构，credit 标注来源 |

完整数据源清单与采集合规原则见 `工作规划.md` 第 3 节。

## 路线图

- **P0**（当前）：数据库 MVP——Schema/词表定稿、Met 等友好源入库 ≥2,000 件、采集流水线跑通
- **P1**：检索前端上线（GitHub Pages）
- **P2**：历史学+考古学 RAG 知识库、文物专家Agent
- **P3**：选题/编辑/总协调Agent，每日自动产出 1 篇推文（人工过目后发布到公众号+小红书）
- **P4**：扩源至 ≥50,000 件、文物组合浏览、读者反馈回路

## 合规声明

- A 类来源按官方 Open Access 条款使用；B 类来源仅以"浏览器人工浏览+手动保存"等同方式采集，不破解、不绕过任何技术防护
- OCR 文字仅作检索与解读素材，成稿一律重新撰写
- 历史类内容以博物馆公开学术资料为据，观点仅供参考

## License

代码：[MIT](LICENSE)；数据：遵循各来源机构条款（见 LICENSE 中 DATA LICENSE NOTICE）。
