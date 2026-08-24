"""爬取 GitHub Trending 周榜，由 DeepSeek 筛选 AI 相关项目并介绍，推送飞书。"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from config import cfg
from ai_analyze import analyze
from lark_push import push

TRENDING_URL = "https://github.com/trending?since=weekly"
THREE_YEARS_AGO = datetime.now(timezone.utc) - timedelta(days=365 * 3)


def fetch_trending() -> list:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; crawler_bot/1.0)"}
    resp = requests.get(TRENDING_URL, headers=headers, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    repos = []
    for article in soup.select("article.Box-row"):
        name_tag = article.select_one("h2 a")
        if not name_tag:
            continue
        full_name = name_tag.get("href", "").strip("/")
        # 过滤3年以上的老项目
        api_resp = requests.get(f"https://api.github.com/repos/{full_name}", timeout=10)
        if api_resp.status_code == 200:
            created_at = api_resp.json().get("created_at", "")
            if created_at:
                created_dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                if created_dt < THREE_YEARS_AGO:
                    continue
        desc_tag = article.select_one("p")
        description = desc_tag.get_text(strip=True) if desc_tag else ""
        week_stars_tag = article.select_one("span.d-inline-block.float-sm-right")
        week_stars = week_stars_tag.get_text(strip=True) if week_stars_tag else "?"
        lang_tag = article.select_one("[itemprop='programmingLanguage']")
        lang = lang_tag.get_text(strip=True) if lang_tag else "?"
        repos.append({
            "name": full_name,
            "url": f"https://github.com/{full_name}",
            "description": description,
            "week_stars": week_stars,
            "language": lang,
        })
    return repos


def build_prompt(repos: list, top_n: int) -> str:
    items_text = "\n\n".join(
        f"{i+1}. **{r['name']}** ({r['week_stars']}, {r['language']})\n描述: {r['description']}\n链接: {r['url']}"
        for i, r in enumerate(repos)
    )
    return f"""以下是 GitHub 本周 Star 增长榜全部 {len(repos)} 个项目。

任务：
1. 从中筛选出真正与 AI/ML/LLM/深度学习/自然语言处理/计算机视觉 相关的项目，取本周新增 star 最多的前 {top_n} 个
2. 对每个入选项目，用 2-3 句话介绍它是什么、解决什么问题、适合谁用，并给出一个具体使用场景

输出格式（严格按此，不输出其他内容）：

## 🤖 GitHub AI 周榜 · {datetime.now().strftime('%Y 第%W周')}

{{序号}}. **{{项目名}}** ({{语言}}) · 🔥{{本周新增star数}}
📌 简介：{{2-3句介绍}}
🎯 场景：{{一个具体使用场景}}
🔗 {{github链接}}

---

项目列表：
{items_text}
"""


def run():
    top_n = cfg["github"]["max_repos"]
    repos = fetch_trending()
    if not repos:
        print("[github] 未获取到数据，跳过推送")
        return
    print(f"[github] 抓取到 {len(repos)} 个项目，交由 AI 筛选 AI 相关前 {top_n} 个")
    content = analyze(build_prompt(repos, top_n))
    push(
        cfg["lark"]["github_webhook"],
        f"🤖 GitHub AI 周榜 · {datetime.now().strftime('%Y 第%W周')}",
        content,
    )
    print(f"[github] 推送完成")


if __name__ == "__main__":
    run()
