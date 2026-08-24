"""用 twitter-cli 爬取 X 上 AI 意见领袖的帖子，整理推送飞书。"""
import subprocess
import json
from datetime import datetime, timezone, timedelta
from config import cfg
from ai_analyze import analyze
from lark_push import push

CUTOFF = lambda: datetime.now(timezone.utc) - timedelta(hours=24)


def fetch_user_posts(account: str, max_posts: int) -> list:
    try:
        result = subprocess.run(
            ["twitter", "user-posts", account, "--max", str(max_posts), "--json"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            print(f"[x] 抓取 @{account} 失败: {result.stderr[:200]}")
            return []
        data = json.loads(result.stdout)
        posts = data if isinstance(data, list) else (data.get("tweets") or data.get("data") or [])
        cutoff = CUTOFF()
        result_posts = []
        for p in posts:
            if not p.get("text"):
                continue
            created = p.get("created_at", "")
            if created:
                try:
                    pub_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    if pub_dt < cutoff:
                        continue
                except ValueError:
                    pass
            result_posts.append({
                "account": account,
                "text": p.get("text", "").strip(),
                "url": f"https://x.com/{account}/status/{p.get('id', '')}",
            })
        return result_posts
    except Exception as e:
        print(f"[x] @{account} 异常: {e}")
        return []


def build_prompt(all_posts: list) -> str:
    items_text = "\n\n".join(
        f"@{p['account']}: {p['text']}\n链接: {p['url']}"
        for p in all_posts
    )
    return f"""以下是 AI 领域意见领袖近期在 X 上发布的帖子（共 {len(all_posts)} 条），请：
1. 归纳出 6-8 个核心话题/观点
2. 每个话题引用 1-2 条最具代表性的原文（保留原文，注明作者）
3. 用一句话点评该话题对行业的意义

输出格式（严格按此）：

## 🐦 AI 领袖观点 · {datetime.now().strftime('%Y-%m-%d')}

**1. {{话题标题}}**
> "{{原文摘录}}" —— @{{作者}}
💡 {{一句话点评}}

**2. {{话题标题}}**
> "{{原文摘录}}" —— @{{作者}}
💡 {{一句话点评}}

（以此类推，共 6-8 条，每条之间空一行，不要用 ### 标题）

---

帖子列表：
{items_text}
"""


def run():
    x_cfg = cfg["x"]
    all_posts = []
    for account in x_cfg["accounts"]:
        posts = fetch_user_posts(account, x_cfg["max_posts_per_account"])
        all_posts.extend(posts)
        print(f"[x] @{account}: {len(posts)} 条")

    if not all_posts:
        print("[x] 未获取到任何帖子，跳过推送")
        return

    content = analyze(build_prompt(all_posts))
    push(
        cfg["lark"]["x_webhook"],
        f"🐦 AI 领袖观点 · {datetime.now().strftime('%Y-%m-%d')}",
        content,
    )
    print(f"[x] 推送完成，处理 {len(all_posts)} 条帖子")


if __name__ == "__main__":
    run()
