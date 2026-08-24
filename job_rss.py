"""爬取 RSS AI 新闻，用 DeepSeek 提炼用户痛点和行业价值，推送飞书。"""
import feedparser
from datetime import datetime, timezone, timedelta
from config import cfg
from ai_analyze import analyze
from lark_push import push


def fetch_recent_entries(feeds: list, max_items: int) -> list:
    """从多个 RSS 源抓取最近 24 小时内的条目"""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    entries = []
    for feed in feeds:
        parsed = feedparser.parse(feed["url"])
        for e in parsed.entries:
            # 获取发布时间
            published = e.get("published_parsed") or e.get("updated_parsed")
            if published:
                pub_dt = datetime(*published[:6], tzinfo=timezone.utc)
                if pub_dt < cutoff:
                    continue
            title = e.get("title", "").strip()
            link = e.get("link", "").strip()
            summary = e.get("summary", "").strip()[:500]
            if title and link:
                entries.append({
                    "source": feed["name"],
                    "title": title,
                    "link": link,
                    "summary": summary,
                })
        if len(entries) >= max_items:
            break
    return entries[:max_items]


def build_prompt(entries: list) -> str:
    items_text = "\n\n".join(
        f"{i+1}. [{e['source']}] {e['title']}\n摘要: {e['summary']}\n链接: {e['link']}"
        for i, e in enumerate(entries)
    )
    return f"""以下是今日 AI 行业最新新闻（共 {len(entries)} 条），请：
1. 筛选出最有价值的 {cfg['rss']['top_n']} 条
2. 对每条：用一句话说明**行业价值**，再用一句话提炼**可能的用户痛点**
3. 输出格式（严格按此，不要多余文字）：

## 📰 AI 行业日报 · {datetime.now().strftime('%Y-%m-%d')}

对每条新闻输出：
**{'{序号}'}. {'{标题}'}**
📄 概述：{'{2-3句话概述这条新闻的主要内容}'}
🔍 行业价值：{'{一句话}'}
💡 用户痛点：{'{一句话}'}
🚀 机会洞察：{'{一句话，指出这条新闻背后潜在的产品/商业机会}'}
🔗 来源：[{'{source}'}]({'{link}'})

---

新闻列表：
{items_text}
"""


def run():
    rss_cfg = cfg["rss"]
    entries = fetch_recent_entries(rss_cfg["feeds"], rss_cfg["max_items"])
    if not entries:
        print("[rss] 今日无新条目，跳过推送")
        return
    content = analyze(build_prompt(entries))
    push(
        cfg["lark"]["rss_webhook"],
        f"📰 AI 行业日报 · {datetime.now().strftime('%Y-%m-%d')}",
        content,
    )
    print(f"[rss] 推送完成，处理 {len(entries)} 条新闻")


if __name__ == "__main__":
    run()
