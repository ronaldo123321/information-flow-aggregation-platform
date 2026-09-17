"""信息源：GitHub Trending 周榜，DeepSeek 筛选 AI 相关项目。"""
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timezone, timedelta
from config import cfg
from ai_analyze import analyze

KEY, ICON, NAME = "github", "🐙", "GitHub 周榜"

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
            "week_stars": week_stars.replace(" stars this week", "").strip(),
            "language": lang,
        })
    return repos


def build_prompt(repos: list, top_n: int) -> str:
    items_text = "\n\n".join(
        f"{i+1}. **{r['name']}** ({r['week_stars']}, {r['language']})\n描述: {r['description']}\n链接: {r['url']}"
        for i, r in enumerate(repos)
    )
    return f"""以下是 GitHub 本周 Star 增长榜全部 {len(repos)} 个项目，请：
1. 筛选出真正与 AI/ML/LLM/深度学习/NLP/CV 相关的项目，按本周新增 star 取前 {top_n} 个
2. 对每个入选项目输出：

**{{序号}}. [{{owner/repo}}]({{链接}})**（{{语言}} · 🔥 +{{本周新增star}})
{{2 句介绍：是什么、解决什么问题，再给 1 个具体使用场景}}

要求：只输出正文条目，不要大标题、分割线和总结语。

---

项目列表：
{items_text}
"""


def collect() -> dict | None:
    top_n = cfg["github"]["max_repos"]
    repos = fetch_trending()
    if not repos:
        print("[github] 未获取到数据")
        return None
    print(f"[github] 抓取到 {len(repos)} 个项目，AI 筛选 AI 相关前 {top_n} 个")
    content = analyze(build_prompt(repos, top_n))
    return {
        "count": len(repos),
        "stat": f"{top_n} 个项目",
        "markdown": content,
        "digest": " / ".join(f"{r['name']}(+{r['week_stars']})" for r in repos[:15]),
    }


if __name__ == "__main__":
    result = collect()
    print(result["markdown"] if result else "（今日无数据）")
