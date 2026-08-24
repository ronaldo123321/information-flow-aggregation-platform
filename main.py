"""容器入口：健康检查服务 + APScheduler 定时任务。"""
import threading
import logging
from apscheduler.schedulers.blocking import BlockingScheduler
from health import run as run_health
import job_rss
import job_github
import job_x
import job_arxiv
import job_producthunt
import job_trends

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

scheduler = BlockingScheduler(timezone="Asia/Shanghai")

# 每天 08:00 推 RSS 日报
scheduler.add_job(job_rss.run, "cron", hour=8, minute=0)
# 每周一 09:30 推 GitHub 周榜
scheduler.add_job(job_github.run, "cron", day_of_week="mon", hour=9, minute=30)
# 每天 20:00 推 X 观点
scheduler.add_job(job_x.run, "cron", hour=20, minute=0)
# 每周三 09:30 推 arxiv 论文速递
scheduler.add_job(job_arxiv.run, "cron", day_of_week="wed", hour=9, minute=30)
# 每天 09:00 推 Product Hunt AI 产品日报
scheduler.add_job(job_producthunt.run, "cron", hour=9, minute=0)
# 每天 08:30 推 Google Trends 全球热搜
scheduler.add_job(job_trends.run, "cron", hour=8, minute=30)



if __name__ == "__main__":
    threading.Thread(target=run_health, daemon=True).start()
    logging.info("健康检查已启动 :8080/health")
    logging.info("调度器启动，等待任务触发...")
    scheduler.start()
