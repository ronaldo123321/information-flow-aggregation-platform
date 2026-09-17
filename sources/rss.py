"""信息源：AI 行业 RSS 新闻，DeepSeek 精选并提炼行业价值。"""
import feedparser
from datetime import datetime, timezone, timedelta
from config import cfg
from ai_analyze import analyze

KEY, ICON, NAME = "rss", "📰", "行业新闻"


def fetch_recent_entries(feeds: list, max_items: int) -> list:
    """从多个 RSS 源抓取最近 24 小时内的条目"""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    entries = []
    for feed in feeds:
        parsed = feedparser.parse(feed["url"])
        for e in parsed.entries:
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


def build_prompt(entries: list, top_n: int) -> str:
    items_text = "\n\n".join(
        f"{i+1}. [{e['source']}] {e['title']}\n摘要: {e['summary']}\n链接: {e['link']}"
        for i, e in enumerate(entries)
    )
    return f"""以下是今日 AI 行业最新新闻（共 {len(entries)} 条），请挑选最有价值的 {top_n} 条，逐条输出：

**{{序号}}. {{中文标题}}**
{{2-3 句概述：发生了什么 + 对行业的价值/影响}}
🔗 [阅读原文]({{link}})

要求：只输出正文条目，不要大标题、分割线和总结语；标题译成中文，链接保持原样。

---

新闻列表：
{items_text}
"""


def collect() -> dict | None:
    rss_cfg = cfg["rss"]
    entries = fetch_recent_entries(rss_cfg["feeds"], rss_cfg["max_items"])
    if not entries:
        print("[rss] 最近 24 小时无新条目")
        return None
    top_n = min(rss_cfg["top_n"], len(entries))
    print(f"[rss] 抓取到 {len(entries)} 条新闻，AI 精选 {top_n} 条")
    content = analyze(build_prompt(entries, top_n))
    return {
        "count": len(entries),
        "stat": f"{top_n} 条精选",
        "markdown": content,
        "digest": " / ".join(e["title"][:60] for e in entries[:15]),
    }


if __name__ == "__main__":
    result = collect()
    print(result["markdown"] if result else "（今日无数据）")
