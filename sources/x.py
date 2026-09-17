"""信息源：X（twitter-cli）上 AI 意见领袖的帖子，DeepSeek 归纳核心话题。

fetch_all_posts 的 since 参数供晚间增量复用：只取某个时间点之后的帖子。
"""
import subprocess
import json
from datetime import datetime, timezone, timedelta
from config import cfg
from ai_analyze import analyze

KEY, ICON, NAME = "x", "🐦", "X 观点"

CUTOFF = lambda: datetime.now(timezone.utc) - timedelta(hours=24)


def fetch_all_posts(accounts: list, max_posts: int, since: datetime | None = None) -> list:
    """抓取多个账号的近期帖子；since 为 None 时取最近 24 小时。"""
    cutoff = since or CUTOFF()
    all_posts = []
    for account in accounts:
        posts = fetch_user_posts(account, max_posts, cutoff)
        all_posts.extend(posts)
        print(f"[x] @{account}: {len(posts)} 条")
    return all_posts


def fetch_user_posts(account: str, max_posts: int, cutoff: datetime) -> list:
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
        kept = []
        for p in posts:
            if not p.get("text"):
                continue
            # twitter-cli 的字段是 createdAtISO，兼容旧的 created_at
            created = p.get("createdAtISO") or p.get("created_at", "")
            if created:
                try:
                    pub_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    if pub_dt < cutoff:
                        continue
                except ValueError:
                    pass
            kept.append({
                "account": account,
                "text": p.get("text", "").strip(),
                "url": f"https://x.com/{account}/status/{p.get('id', '')}",
                "id": str(p.get("id", "")),
                "created_at": created,
            })
        return kept
    except Exception as e:
        print(f"[x] @{account} 异常: {e}")
        return []


def build_prompt(all_posts: list, topics: int = 7) -> str:
    items_text = "\n\n".join(
        f"@{p['account']}: {p['text'][:500]}\n链接: {p['url']}"
        for p in all_posts
    )
    return f"""以下是 AI 领域意见领袖近期在 X 上发布的帖子（共 {len(all_posts)} 条），请：
1. 归纳出 {topics} 个左右的核心话题/观点（帖子少时可以更少，不要硬凑）
2. 每个话题输出：

**{{序号}}. {{话题标题}}**
{{一句话点评该话题对行业的意义}}
> {{最具代表性的原文摘录，80 字内，保留原味}} —— @{{作者}}

要求：只输出正文条目，不要大标题、分割线和总结语。

---

帖子列表：
{items_text}
"""


def collect() -> dict | None:
    x_cfg = cfg["x"]
    all_posts = fetch_all_posts(x_cfg["accounts"], x_cfg["max_posts_per_account"])
    if not all_posts:
        print("[x] 最近 24 小时未获取到帖子")
        return None
    content = analyze(build_prompt(all_posts))
    return {
        "count": len(all_posts),
        "stat": f"{len(all_posts)} 条帖子",
        "markdown": content,
        "digest": " / ".join(p["text"][:60] for p in all_posts[:12]),
    }


if __name__ == "__main__":
    result = collect()
    print(result["markdown"] if result else "（今日无数据）")
