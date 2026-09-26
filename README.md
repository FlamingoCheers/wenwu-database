# wenwu-database 文物数据库

聚合全球博物馆公开数据的**中国文物纯数据库**：一物一条结构化 JSON（朝代、类别、材质、尺寸、来源、授权），配套 SQLite 快照与静态检索前端（支持朝代/类别/关键词检索、年代排序、同名钱币跨馆聚合浏览）。

**在线检索前端：<https://flamingocheers.github.io/wenwu-database/>**

## 数据规模

当前 **30,676 件**，覆盖 9 家博物馆。数据由 GitHub Actions 定时增量更新。

| 博物馆 | 件数 | 接入方式 | 授权 |
|---|---|---|---|
| 台北故宫博物院 | 11,302 | Open Data 专区 | 开放授权（CC0 1.0） |
| 大都会艺术博物馆 | 10,581 | Open Access API | CC0 |
| 克利夫兰艺术博物馆 | 2,804 | Open Access API | CC0 |
| 陕西历史博物馆 | 1,515 | 公开藏品目录 Excel（钱币按名称聚合为"品种"记录）+ 精品页 | ©陕西历史博物馆（仅收录信息与来源链接） |
| 史密森尼国家亚洲艺术博物馆 | 1,639 | Open Access API | CC0 |
| 中国国家博物馆 | 1,294 | 公开网站采集（严格限速：每 6 小时不超过 100 条） | ©中国国家博物馆（仅收录信息与来源链接） |
| 故宫博物院（北京） | 621+ | 数字文物库搜索卡片（playwright 渲染，不逆向接口；精选关键词） | ©故宫博物院（仅收录信息与来源链接） |
| 芝加哥艺术馆 | 802 | Open Access API | CC0 |
| 河南博物院 | 17+ | 公开详情页静态采集（每 6 小时不超过 100 条） | ©河南博物院（仅收录信息与来源链接） |

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

## 附录：未接入数据源调研（供其他数据需求者参考）

本数据库只聚合**官方开放 API / 官方明确开放授权**的数据源。调研中我们发现以下优秀的博物馆与数据库因**未提供公开 API**（或条款不开放批量获取）而未接入——它们本身就是查找中国文物数据与影像的权威去处，推荐直接访问：

### 无公开 API 的国际大馆（中国藏品极重要）

| 机构 | 官网 / 藏品检索入口 | 说明 |
|---|---|---|
| 大英博物馆 | <https://www.britishmuseum.org/collection> | 中国文物 2.3 万+ 件，全球最重要收藏之一；无公开 API，且条款不开放批量获取 |
| 波士顿美术馆 (MFA) | <https://collections.mfa.org> | 中国书画与陶瓷收藏世界顶级；无官方 API |
| 纳尔逊-阿特金斯艺术博物馆 | <https://art.nelson-atkins.org> | 中国书画、石刻重镇；无公开 API |
| 吉美博物馆 (Musée Guimet) | <https://www.guimet.fr> / <https://Collections.guimet.fr> | 法国国立亚洲艺术博物馆；无公开 API |
| 东京国立博物馆 | <https://colbase.nich.go.jp> / <https://www.tnm.jp> | 日本最大博物馆，含大量中国文物；COLR/COLBASE 联合检索，无公开 API |
| 耶鲁大学美术馆 | <https://artgallery.yale.edu/collections> | 旧公开 API（api.artgallery.yale.edu）已退役；新 LUX 平台（lux.collections.yale.edu）藏品记录基本不含影像（实测 0/60 带图），暂无可用批量路径 |
| 菲茨威廉博物馆（剑桥） | <https://fitzmuseum.cam.ac.uk/objects> | 官方 API（api.fitzmuseum.cam.ac.uk）已退役，新站仅 HTML 页面，无公开批量接口 |
| 宾夕法尼亚大学博物馆 | <https://www.penn.museum/collections/> | 旧 API（api.penn.museum）已下线，站内检索无公开 JSON 接口 |
| 普林斯顿大学艺术博物馆 | <https://artmuseum.princeton.edu/search/collections> | 检索页有 Cloudflare 人机验证，未提供公开 API |
| 巴黎赛努奇博物馆 | <https://www.cernuschi.paris.fr> | 属巴黎博物馆联盟，其 GraphQL API 需免费注册账号获取令牌后使用：<https://apicollections.parismusees.paris.fr> |
| 香港故宫文化博物馆 | <https://www.hkpm.org.hk> | 藏品以北京故宫借展为主，官网无逐件藏品数据页 |
| 台北故宫博物院（完整目录） | <https://theme.npm.edu.tw/opendata> | 开放数据专区另有整包元数据下载；本库当前经数字典藏检索接入 1.1 万件（见 FAQ） |

### 国内博物馆公开目录（无 API，仅提供网页/目录检索）

| 机构 | 入口 | 说明 |
|---|---|---|
| 国家博物馆 | <https://www.chnmuseum.cn/zp/zpml/> | 藏品精粹公开页（本库经严格限速的公开网页采集） |
| 南京博物院 | <https://www.njmuseum.com> | 纯前端渲染站，无数据接口 |
| 山西博物院 | <https://www.shanximuseum.com> | 藏品页 JS 动态加载 |
| 湖南博物院 | <https://www.hnmuseum.com> | 馆藏国宝栏目为静态页；新版数字库需浏览器环境 |
| 湖北省博物馆 | <https://www.hbww.org> | 站点对境外网络不开放 |
| 浙江省博物馆 | <https://www.zhejiangmuseum.com> | 对部分境外网络不开放 |
| 上海博物馆 | <https://www.shanghaimuseum.net> | 数字文库需浏览器交互，无公开 API |
| 首都博物馆 | <https://www.capitalmuseum.org.cn> | 列表数据内嵌加密令牌接口，未开放 |
| 天津博物馆 | <https://www.tjbwg.com> | 域名对境外不可解析 |
| 秦始皇帝陵博物院 | <https://www.bmy.com.cn> | 兵马俑专题，无公开 API |
| 三星堆博物馆 | <https://www.sxd.cn> | 无公开 API |

### 专题与聚合类资源（合法公开，供检索/浏览）

| 资源 | 入口 | 说明 |
|---|---|---|
| 数字敦煌 | <https://www.e-dunhuang.com> | 敦煌研究院官方高清洞窟与壁画影像库 |
| 中华珍宝馆 | <https://ltfc.net> | 民间聚合的中国书画高清扫描，无 API，仅网页浏览 |
| 书格 | <https://new.shuge.org> | 公版古籍书画影像，公益项目 |
| Europeana | <https://www.europeana.eu> | 欧洲文化聚合器（含各国博物馆中国藏品，开放授权可过滤） |
| DPLA | <https://dp.la> | 美国数字公共图书馆聚合器 |
| Google Arts & Culture | <https://artsandculture.google.com> | 跨馆超高清影像，无公开 API |

### 本库的合规立场

1. **只聚合公开授权数据**：Open Access 馆按官方条款接入；未开放 API 的馆绝不破解、不逆向接口、不绕过防护（哪怕技术上可行，如加密参数/令牌墙）。
2. **©馆藏影像不入库**：对©馆（国博/陕历博/河南/北京故宫）只保存基本信息与指向官方页面的跳转链接，不保存、不热链其文物影像。
3. **严格限速**：国内站点一律 ≤100 件/6 小时/馆，单线程小间隔，尊重对方服务器。
4. **随时可下架**：任何馆若认为数据不适合被聚合，提出后即删除对应记录。

> 寻找上述未接入馆的数据？请直接访问各馆官网检索入口；学术批量需求可联系馆方申请研究数据。

## FAQ

**Q：台北故宫约 70 万件藏品，为什么库里只有 1.1 万件台北故宫文物？**

A：70 万是台北故宫**总典藏量**，其中约 55 万+ 是**图书文献与清代宫廷档案**（奏折、账册、圣旨、善本古籍等文书类），绝大多数未数字化为带影像的"文物条目"。开放数据检索（digitalarchive）中已数字化、带开放影像且结构化为器物/书画条目的约十余万条，本库经 19 个朝代年代轴 + 带开放影像过滤后收录 11,302 件——**不是"不是中国的"（全部是中国文物），而是：①档案文书类不在本库"文物器物"范围；②大量藏品尚未数字化开放影像；③少量深分页损失已记录**。如需完整目录请访问上表中的开放数据专区（另有整包元数据下载）。

## License

代码：[MIT](LICENSE)；数据：遵循各来源机构条款（见 LICENSE 中 DATA LICENSE NOTICE）。
