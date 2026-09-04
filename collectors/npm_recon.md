# 台北故宫（NPM）Open Data 侦察笔记

> 侦察日期：2026-09-04 ｜ 结论：**暂缓，归入 B 类待办**（网络不可达）

## 探测结果

| 域名 | 结果 |
|---|---|
| `theme.npm.edu.tw/opendata/` | 超时（21s 无响应，curl 000） |
| `opendata.npm.gov.tw/` | 瞬断（curl 000） |
| webfetch 工具 | Transport error |

**判定：台湾政府/故宫域名对本机网络（大陆出口）不可达**，浏览器方案在本机同样会被卡住。

## 可行路径（按优先级）

1. **GitHub Actions runner 下载（推荐，A 类整包）**：Actions runner 在海外 Azure 网络，可直连
   `theme.npm.edu.tw/opendata/`。该站点提供器物典藏等资料集的 CSV/JSON 整包下载（无需 API key）。
   做法：在 update-data.yml 中加一个 job，runner 下载整包 → 解析 → 按 schema 映射 → 提交。
   ⚠️ 待验证（页面未打开成，以下为待办清单）：
   - 整包下载 URL 与档案权限（Open Data 政府站台 generally CC0/BY，需确认 each dataset 授权条款）
   - 数据字段与 relic.schema.json 的映射（藏品号、品名、朝代、尺寸、图档 URL、授权栏位）
   - 图档域名（通常 `theme.npm.edu.tw` 或 `digitalarchive.npm.gov.tw`）是否也限速/防盗链
2. **本机代理/VPN 后走 B 类浏览器**：与国博截图流程共用 Playwright 基建。

## 关联决策

- 工作规划 P1 的"台北故宫接入"调整前置条件：优先在 Actions workflow 里实现 runner 端整包下载。
- 不阻塞当前主线（Met/CLE 已 5,239 件，P1 还有克利夫兰之外的海外源可接）。
