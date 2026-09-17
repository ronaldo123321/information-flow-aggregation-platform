"""Codex 重置监控：盯 Tibo（@thsottiaux）的 X 帖子，发现重置相关发言立即推飞书。

Tibo 是 Codex 额度重置的"播报员"，重置推送完成后会发帖确认。本模块定时
（默认 10 分钟）抓取他的最新帖子，命中关键词且未推过的才推送；首次运行
只记录基线不推送，避免把历史帖子当新闻。状态存 state/tibo_monitor.json。

手动运行：
    python -m tibo_monitor           # 检查一次
    python -m tibo_monitor --force   # 无视去重，把最新一条匹配帖当新帖推一遍（演示用）
"""
import json
import re
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

from config import cfg
from lark_push import push_card
from sources.x import fetch_user_posts

CST = timezone(timedelta(hours=8))
STATE_FILE = Path(__file__).parent / "state" / "tibo_monitor.json"
MAX_STATE_IDS = 100

# 帖子文本 -> 中文判定
DONE_RE = re.compile(r"pushed|completed|finished|done|all set", re.I)
ONGOING_RE = re.compile(r"tonight|today|soon|rolling|started|landing|will|underway", re.I)


def classify(text: str) -> str:
    if DONE_RE.search(text):
        return "✅ 重置已推送完成，Codex 额度应已到账"
    if ONGOING_RE.search(text):
        return "⏳ 重置预告/进行中"
    return "📣 重置相关动态"


def load_state() -> dict | None:
    if not STATE_FILE.is_file():
        return None
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return None


def save_state(pushed_ids: list):
    STATE_FILE.parent.mkdir(exist_ok=True)
    STATE_FILE.write_text(
        json.dumps({"pushed_ids": pushed_ids[-MAX_STATE_IDS:]}, ensure_ascii=False),
        encoding="utf-8",
    )


def push_post(post: dict):
    tc = cfg.get("tibo", {})
    account = tc.get("account", "thsottiaux")
    created = post.get("created_at") or ""
    try:
        pub = datetime.fromisoformat(created.replace("Z", "+00:00")).astimezone(CST)
        pub_str = f"{pub:%m-%d %H:%M}"
    except ValueError:
        pub_str = "时间未知"
    now = datetime.now(CST)
    webhook = cfg["lark"].get("tibo_webhook") or cfg["lark"]["x_webhook"]
    push_card(
        webhook,
        f"✅ Codex 重置播报 · 检测于 {now:%H:%M}",
        f"**@{account} 刚刚发布**\n\n"
        f"> {post['text']}\n\n"
        f"🔎 判定：{classify(post['text'])}\n"
        f"🕐 发布于 {pub_str}（北京时间）",
        button_text="在 X 查看原帖 →",
        button_url=post["url"],
        template="green",
    )
    print(f"[tibo] 已推送: {post['url']}")


def _parse_created(post: dict) -> datetime | None:
    raw = post.get("created_at") or ""
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def run(force: bool = False):
    tc = cfg.get("tibo", {})
    account = tc.get("account", "thsottiaux")
    keywords = [k.lower() for k in tc.get("keywords", ["reset"])]
    max_posts = tc.get("max_posts", 5)
    max_age_hours = tc.get("max_age_hours", 24)

    posts = []
    for attempt in range(3):
        posts = fetch_user_posts(account, max_posts, datetime.now(timezone.utc) - timedelta(hours=max_age_hours))
        if posts:
            break
        if attempt < 2:
            time.sleep(5)  # twitter-cli 偶发 ClientTransaction 失败，重试两次
    matched = [p for p in posts if any(k in p["text"].lower() for k in keywords)]
    if not matched:
        print(f"[tibo] @{account} 近 {max_age_hours} 小时无重置相关帖子")
        return

    state = load_state()
    if state is None and not force:
        # 首次运行：2 小时前的帖子只记基线不推送，刚发生的照常提醒
        baseline, fresh = [], []
        for p in matched:
            created = _parse_created(p)
            if created and datetime.now(timezone.utc) - created <= timedelta(hours=2):
                fresh.append(p)
            else:
                baseline.append(p["id"])
        save_state(baseline + [p["id"] for p in fresh])
        if fresh:
            for p in sorted(fresh, key=lambda x: x.get("created_at") or ""):
                push_post(p)
            print(f"[tibo] 首次运行，基线 {len(baseline)} 条，推送新帖 {len(fresh)} 条")
        else:
            print(f"[tibo] 首次运行，基线记录 {len(baseline)} 条，不推送")
        return

    pushed = set(state.get("pushed_ids", [])) if state else set()
    new = [p for p in matched if p["id"] not in pushed]
    if force:
        latest = matched[0]
        if latest["id"] in pushed and not [p for p in new if p["id"] != latest["id"]]:
            new = [latest]  # 演示：把最新一条再推一遍
    if not new:
        print(f"[tibo] 匹配 {len(matched)} 条，均为已推送过的旧帖")
        return

    for p in sorted(new, key=lambda x: x.get("created_at") or ""):
        push_post(p)
    pushed.update(p["id"] for p in new)
    save_state(sorted(pushed))
    print(f"[tibo] 本次推送 {len(new)} 条，累计记录 {len(pushed)} 条")


if __name__ == "__main__":
    run(force="--force" in __import__("sys").argv)
