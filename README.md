# wenwu-database 文物数据库

聚合全球博物馆公开数据的**中国文物纯数据库**：一物一条结构化 JSON（朝代、类别、材质、尺寸、来源、授权），配套 SQLite 快照与静态检索前端（支持朝代/类别/关键词检索、年代排序、同名钱币跨馆聚合浏览）。

**在线检索前端：<https://flamingocheers.github.io/wenwu-database/>**

## 数据规模

当前 **27,819 件**，覆盖 6 家博物馆。数据由 GitHub Actions 定时增量更新。

| 博物馆 | 件数 | 接入方式 | 授权 |
|---|---|---|---|
| 台北故宫博物院 | 11,341 | Open Data 专区 | 开放授权（CC0 1.0） |
| 大都会艺术博物馆 | 10,581 | Open Access API | CC0 |
| 克利夫兰艺术博物馆 | 2,804 | Open Access API | CC0 |
| 陕西历史博物馆 | 1,526 | 公开藏品目录 Excel（钱币按名称聚合为"品种"记录） | ©陕西历史博物馆（仅收录信息与来源链接） |
| 芝加哥艺术馆 | 802 | Open Access API | CC0 |
| 中国国家博物馆 | 765 | 公开网站采集（严格限速：每 6 小时不超过 100 条） | ©中国国家博物馆（仅收录信息与来源链接） |

分布概览：`pipeline/build_db.py` 输出，或 `raw/_validation_report.json`。

## 目录结构

```
├── schemas/            # 数据 Schema（JSON Schema）
├── collectors/         # 各数据源采集器（每馆一个）
├── pipeline/           # 清洗、去重、打标、质检、构建 SQLite/前端索引
├── data/
│   ├── relics/         # 文物 JSON（一物一文件）
│   ├── vocab/          # 受控词表：朝代/类别/地区/主题标签
│   └── museums.json    # 博物馆名录与数据源配置
├── raw/                # 原始数据缓存（gitignore，可重取）
├── web/                # 静态检索前端（GitHub Pages）
├── 工作规划.md 等       # 规划文档
└── .github/workflows/  # 定时任务：增量采集 / 前端自动发布
```

## 快速开始

```bash
# 1. 采集（示例）
python collectors/met_collector.py --limit 50   # 大都会博物馆 Open Access，试跑 50 件
python collectors/sxhm_collector.py             # 陕西历史博物馆（需先按脚本说明下载目录 Excel）

# 2. 质检 + 构建
python pipeline/validate.py                     # 全库质检
python pipeline/build_db.py                     # SQLite 快照
python pipeline/build_web_index.py              # 前端索引（web/data）
```

## 数据规范

- 每件文物一条 JSON：`data/relics/{relic_id}.json`，Schema 见 `schemas/relic.schema.json`
- `relic_id` 格式：`{馆代码}-{馆藏号}`，如 `MET-12345`、`NPM-36115`、`SXHM-H0432026`
- 朝代/类别/地区/主题标签统一归一到 `data/vocab/` 受控词表
- 每条记录必带 `source_url` 与授权字段，全程可溯源

## 社区贡献：关于分享文物照片

欢迎大家在自己的仓库或公开网站上分享本数据库尚未收录的文物照片。数据库也很乐意收录大家补充的文物信息——但目前仅以**跳转链接**的形式引用外部图片与出处，不会保存文物图片文件。

## 合规声明

- Open Access 来源按各馆官方开放数据条款使用
- 未提供开放 API 的馆（国博、陕历博等）仅以等同于人工浏览的方式访问公开网页，不破解、不绕过任何技术防护，并对国内站点严格限速
- 仅收录文物基本信息与指向官方页面的链接，不保存受版权保护的文物影像
- 历史类内容以博物馆公开学术资料为据，观点仅供参考

## License

代码：[MIT](LICENSE)；数据：遵循各来源机构条款（见 LICENSE 中 DATA LICENSE NOTICE）。
