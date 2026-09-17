# Information Flow Aggregation Platform

一个轻量的信息聚合与推送服务：定时抓取 AI 新闻、开源项目、论文、产品、社交媒体观点和全球趋势，用 DeepSeek 做跨源提炼，**每天推送一份中文情报日报到飞书群**——摘要卡片 + 可点击的完整 HTML 报告。

## 工作方式

```
sources/*（抓取 + AI 提炼，独立容错）
        │
        ▼
report.py（汇总编排）
  ├─ signals.py     跨源提炼「今日核心信号」
  ├─ render_html.py 渲染完整 HTML 报告（reports/日期.html + latest.html）
  └─ lark_push.py   推送摘要卡片（核心信号 + 版块速览 + 「阅读完整报告」按钮）
```

| 信息源 | 内容 | 频率 |
| --- | --- | --- |
| `sources/rss.py` | TechCrunch、The Verge、Hacker News 等 AI 行业新闻 | 每天 |
| `sources/trends.py` | Google Trends 多市场热搜 | 每天 |
| `sources/producthunt.py` | Product Hunt AI 产品榜 | 每天 |
| `sources/x.py` | X 上 AI 大佬观点（twitter-cli） | 每天（晚间另有增量卡） |
| `sources/github.py` | GitHub AI 周榜 | 每周一 |
| `sources/arxiv.py` | arXiv AI 论文速递 | 每周三 |

- **08:00 日报**：单个源失败只影响自己的版块，不拖垮整份报告；GitHub/arXiv 非更新日在卡片中标注"本期未排期"。
- **20:00 X 晚间增量**：只覆盖早报之后的新帖，无新帖则不打扰。
- **周五 08:30 机会画布**：汇总本周每日摘要（`reports/digests/`），由 DeepSeek 提炼 2-3 个可落地的 POC 产品方向（信号依据 / 用户痛点 / 最小验证 / 判停指标），生成 `poc-latest.html` 并推送；情报不足 3 天自动跳过。
- **Codex 重置监控**：每 10 分钟检查 Tibo（@thsottiaux）的 X 帖子，命中"reset"关键词的新帖立即推卡（附中文判定与原帖链接）；首次运行只记基线，去重状态存 `state/`。
- **报告托管二选一**：配置 `GCS_BUCKET_NAME` 后报告自动上传到 GCS（公开读取），卡片按钮指向公网地址；未配置时由服务自带端口托管，`http://<host>:8080/reports/latest.html`（按日期归档，`/` 自动跳转最新一篇）。

## 快速开始

```bash
git clone https://github.com/ronaldo123321/information-flow-aggregation-platform.git
cd information-flow-aggregation-platform

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# 编辑 .env，填入自己的 API Key 和飞书 Webhook

python main.py
```

手动调试：

```bash
python -m report --dry-run      # 生成当日报告但不推送
python -m report                # 生成并推送
python -m sources.rss           # 单独跑某个源，打印提炼结果
python evening_x.py             # 手动跑晚间 X 增量
python -m weekly_poc            # 手动生成机会画布（--dry-run 不推送，--force 忽略最少天数）
python -m tibo_monitor          # 手动检查一次 Codex 重置播报（--force 演示推送）
```

服务启动后 `http://localhost:8080/health` 为健康检查，报告访问地址取决于部署环境：
本机运行是 `http://localhost:8080/reports/latest.html`，服务器/容器部署时把对外地址填到 `REPORT_BASE_URL`（或 `config.yaml` 的 `report.base_url`），卡片里的按钮才会指向正确链接。

## 环境变量

| 变量 | 用途 |
| --- | --- |
| `DEEPSEEK_API_KEY` | DeepSeek API Key |
| `LARK_DAILY_WEBHOOK` | 日报摘要卡片推送的群 Webhook（未填时回退旧变量名 `LARK_RSS_WEBHOOK`） |
| `LARK_X_WEBHOOK` | X 晚间增量卡推送的群 Webhook |
| `LARK_TIBO_WEBHOOK` | 可选：Codex 重置监控推送的群 Webhook（未填回落到 `LARK_X_WEBHOOK`） |
| `GCS_BUCKET_NAME` | GCS bucket 名；配置后报告自动上传，卡片按钮指向 `https://storage.googleapis.com/<bucket>/latest.html` |
| `GCS_PROJECT_ID` | GCP 项目 ID（如 `nebula-pro-438302`） |
| `GCS_KEY_FILE` | 服务账号 key 文件路径（如 `/gcs-key.json`） |
| `GCS_CONFIG_JSON` | 服务账号 key 的 JSON 原文（与 `GCS_KEY_FILE` 二选一） |
| `REPORT_BASE_URL` | 本地服务托管时的报告地址，如 `http://1.2.3.4:8080` |
| `PRODUCTHUNT_TOKEN` | Product Hunt API Token |

GCS 认证按优先级解析：`GCS_KEY_FILE`（文件需存在）→ `GCS_CONFIG_JSON` → base64 变量 `GCS_SERVICE_ACCOUNT_B64` → `GOOGLE_APPLICATION_CREDENTIALS` / gcloud 默认凭据（本机开发）。bucket 需允许公开读取（allUsers: Storage Object Viewer），服务账号需要写入权限（Storage Object Creator）。手动补传已有报告：`python -m storage_gcs`。

完整模板见 `.env.example`。`config.yaml` 只保存不敏感的任务参数（RSS 源、X 账号、关注市场等），凭据统一从环境变量读取。

## X 数据源

X 任务依赖 `twitter-cli`，它会读取本机浏览器中已有的登录状态：

```bash
uv tool install twitter-cli
twitter user-posts sama --max 5
```

在服务器或容器中运行时，需要单独配置 `twitter-cli` 所需的认证方式。

## Docker

```bash
docker build -t information-flow-aggregation-platform .
docker run --env-file .env -p 8080:8080 -v $(pwd)/reports:/app/reports information-flow-aggregation-platform
```

`reports/` 挂载为卷可以保留历史报告；不挂载则报告随容器生命周期存储。`.dockerignore` 会阻止本地凭据、Git 元数据、虚拟环境和日志进入镜像。请不要把填写后的 `.env` 提交到版本库或复制到镜像中。

## License

[MIT](LICENSE)
