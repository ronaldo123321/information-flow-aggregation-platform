"""晚间 X 观点增量卡：只覆盖今天早报（08:00）之后的新帖，无新帖则不打扰。"""
from datetime import datetime, timezone, timedelta

from config import cfg
from ai_analyze import analyze
from lark_push import push
from sources.x import build_prompt, fetch_all_posts

CST = timezone(timedelta(hours=8))


def run():
    x_cfg = cfg["x"]
    today_eight = datetime.now(CST).replace(hour=8, minute=0, second=0, microsecond=0)
    posts = fetch_all_posts(x_cfg["accounts"], x_cfg["max_posts_per_account"], since=today_eight)
    if not posts:
        print("[evening-x] 早报之后无新帖，跳过推送")
        return
    print(f"[evening-x] 早报后新增 {len(posts)} 条帖子，AI 归纳话题")
    if not cfg["lark"]["x_webhook"]:
        print("[evening-x] 未配置 LARK_X_WEBHOOK，跳过推送")
        return
    content = analyze(build_prompt(posts, topics=5))
    push(
        cfg["lark"]["x_webhook"],
        f"🐦 X 观点速递 · {datetime.now():%m-%d} 晚间",
        content,
    )
    print("[evening-x] 推送完成")


if __name__ == "__main__":
    run()
