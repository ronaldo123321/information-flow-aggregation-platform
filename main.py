"""容器入口：健康检查/报告托管服务 + APScheduler 定时任务。

- 每天 08:00 跑全部信息源，生成 HTML 报告并推送摘要卡片
- 每天 20:00 推送 X 观点晚间增量（无新帖不打扰）
- 每周五 08:30 汇总本周情报，生成机会画布并推送
- 定时检查 Tibo 的 Codex 重置播报，有新帖立即推送
"""
import threading
import logging
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from health import run as run_health
from config import cfg
import report
import evening_x
import weekly_poc
import tibo_monitor

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

scheduler = BlockingScheduler(timezone="Asia/Shanghai")

# 每天 08:00 生成并推送 AI 情报日报
scheduler.add_job(report.run, "cron", hour=8, minute=0)
# 每天 20:00 推送 X 观点晚间增量
scheduler.add_job(evening_x.run, "cron", hour=20, minute=0)
# 每周五 08:30 汇总本周情报，生成机会画布
scheduler.add_job(weekly_poc.run, "cron", day_of_week="fri", hour=8, minute=30)
# 定时检查 Codex 重置播报（启动时先跑一次做基线，不推送）
scheduler.add_job(
    tibo_monitor.run, "interval",
    minutes=cfg.get("tibo", {}).get("interval_minutes", 10),
    next_run_time=datetime.now(scheduler.timezone),
)


if __name__ == "__main__":
    threading.Thread(target=run_health, daemon=True).start()
    logging.info("服务已启动: :8080/health, 报告托管: /reports/latest.html")
    logging.info("调度器启动: 日报 08:00 · X 晚间增量 20:00 · 机会画布 周五 08:30 · "
                 f"重置监控每 {cfg.get('tibo', {}).get('interval_minutes', 10)} 分钟")
    scheduler.start()
