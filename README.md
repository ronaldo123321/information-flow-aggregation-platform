# Information Flow Aggregation Platform

一个轻量的信息聚合与推送服务：定时抓取 AI 新闻、开源项目、论文、产品、社交媒体观点和全球趋势，使用 DeepSeek 生成中文摘要，再推送到飞书群。

## 数据源

| 任务 | 内容 | 默认频率 |
| --- | --- | --- |
| `job_rss.py` | AI 行业 RSS 日报 | 每天 08:00 |
| `job_trends.py` | Google Trends 全球热搜 | 每天 08:30 |
| `job_producthunt.py` | Product Hunt AI 产品日报 | 每天 09:00 |
| `job_github.py` | GitHub AI 周榜 | 每周一 09:30 |
| `job_arxiv.py` | arXiv AI 论文速递 | 每周三 09:30 |
| `job_x.py` | X 上 AI 领域观点 | 每天 20:00 |

默认时区为 `Asia/Shanghai`，可在 `main.py` 中调整任务时间。

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

服务启动后会在 `http://localhost:8080/health` 提供健康检查接口。也可以单独执行任意任务，例如：

```bash
python job_rss.py
python job_github.py
```

## 环境变量

| 变量 | 用途 |
| --- | --- |
| `DEEPSEEK_API_KEY` | DeepSeek API Key |
| `LARK_RSS_WEBHOOK` | RSS 日报飞书机器人 Webhook |
| `LARK_GITHUB_WEBHOOK` | GitHub 周榜飞书机器人 Webhook |
| `LARK_X_WEBHOOK` | X 观点飞书机器人 Webhook |
| `LARK_ARXIV_WEBHOOK` | arXiv 论文飞书机器人 Webhook |
| `LARK_PRODUCTHUNT_WEBHOOK` | Product Hunt 日报飞书机器人 Webhook |
| `LARK_TRENDS_WEBHOOK` | Google Trends 日报飞书机器人 Webhook |
| `PRODUCTHUNT_TOKEN` | Product Hunt API Token |

完整模板见 `.env.example`。`config.yaml` 只保存不敏感的任务参数，凭据统一从环境变量读取。

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
docker run --env-file .env -p 8080:8080 information-flow-aggregation-platform
```

`.dockerignore` 会阻止本地凭据、Git 元数据、虚拟环境和日志进入镜像。请不要把填写后的 `.env` 提交到版本库或复制到镜像中。

## License

[MIT](LICENSE)
