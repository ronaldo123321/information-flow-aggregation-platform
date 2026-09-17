"""容器入口：健康检查/报告托管服务 + APScheduler 定时任务。

- 每天 08:00 跑全部信息源，生成 HTML 报告并推送摘要卡片
- 每天 20:00 推送 X 观点晚间增量（无新帖不打扰）
"""
import threading
import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from health import run as run_health
import report
import evening_x

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

scheduler = BlockingScheduler(timezone="Asia/Shanghai")

# 每天 08:00 生成并推送 AI 情报日报
scheduler.add_job(report.run, "cron", hour=8, minute=0)
# 每天 20:00 推送 X 观点晚间增量
scheduler.add_job(evening_x.run, "cron", hour=20, minute=0)


if __name__ == "__main__":
    threading.Thread(target=run_health, daemon=True).start()
    logging.info("服务已启动: :8080/health, 报告托管: /reports/latest.html")
    logging.info("调度器启动: 日报 08:00 · X 晚间增量 20:00")
    scheduler.start()
