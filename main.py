"""容器入口：健康检查/报告托管服务 + APScheduler 定时任务。

- 每天 08:00 跑全部信息源，生成 HTML 报告并推送摘要卡片
- 每天 20:00 推送 X 观点晚间增量（无新帖不打扰）
- 每周五 08:30 汇总本周情报，生成机会画布并推送
- 每天 8:00 / 14:00 / 20:00 检查 Tibo 的 Codex 重置播报，有新帖立即推送
"""
import threading
import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from health import run as run_health
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
# 白天（北京时间 8:00-20:00）每 6 小时检查一次 Codex 重置播报
scheduler.add_job(tibo_monitor.run, "cron", hour="8,14,20", minute=0)


if __name__ == "__main__":
    threading.Thread(target=run_health, daemon=True).start()
    logging.info("服务已启动: :8080/health, 报告托管: /reports/latest.html")
    logging.info("调度器启动: 日报 08:00 · X 晚间增量 20:00 · 机会画布 周五 08:30 · 重置监控 8/14/20 点")
    scheduler.start()
