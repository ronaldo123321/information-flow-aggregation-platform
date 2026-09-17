"""信息源：arXiv 本周高热 AI 论文，DeepSeek 筛选并翻译成人话。"""
import requests
from datetime import datetime, timezone, timedelta
from config import cfg
from ai_analyze import analyze

KEY, ICON, NAME = "arxiv", "📄", "论文速递"

ARXIV_API = "https://export.arxiv.org/api/query"
# AI 相关核心分类
CATEGORIES = "cat:cs.AI OR cat:cs.LG OR cat:cs.CL OR cat:cs.CV"


def fetch_papers(max_results: int) -> list:
    params = {
        "search_query": CATEGORIES,
        "sortBy": "submittedDate",
        "sortOrder": "descending",
        "max_results": max_results,
    }
    resp = requests.get(ARXIV_API, params=params, timeout=15)
    resp.raise_for_status()

    # 解析 Atom XML
    import xml.etree.ElementTree as ET
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    root = ET.fromstring(resp.text)
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    papers = []
    for entry in root.findall("atom:entry", ns):
        published = entry.find("atom:published", ns).text
        pub_dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
        if pub_dt < cutoff:
            continue
        title = entry.find("atom:title", ns).text.strip().replace("\n", " ")
        summary = entry.find("atom:summary", ns).text.strip().replace("\n", " ")[:400]
        link = entry.find("atom:id", ns).text.strip()
        authors = [a.find("atom:name", ns).text for a in entry.findall("atom:author", ns)][:3]
        papers.append({
            "title": title,
            "summary": summary,
            "link": link,
            "authors": ", ".join(authors),
        })
    return papers


def build_prompt(papers: list, top_n: int) -> str:
    items_text = "\n\n".join(
        f"{i+1}. **{p['title']}**\n作者: {p['authors']}\n摘要: {p['summary']}\n链接: {p['link']}"
        for i, p in enumerate(papers)
    )
    return f"""以下是本周 arXiv 最新 AI 论文（共 {len(papers)} 篇），请挑选研究/应用价值最高的 {top_n} 篇，逐条输出：

**{{序号}}. {{论文标题中文翻译}}**
原题：{{英文原标题}}
{{2-3 句通俗解读：研究什么问题、用了什么方法、有什么意义，非专业人士能看懂}}
🔗 [arXiv]({{link}})

要求：只输出正文条目，不要大标题、分割线和总结语。

---

论文列表：
{items_text}
"""


def collect() -> dict | None:
    top_n = cfg.get("arxiv", {}).get("top_n", 6)
    max_fetch = cfg.get("arxiv", {}).get("max_fetch", 50)
    papers = fetch_papers(max_fetch)
    if not papers:
        print("[arxiv] 未获取到论文")
        return None
    print(f"[arxiv] 抓取到 {len(papers)} 篇，AI 筛选前 {top_n} 篇")
    content = analyze(build_prompt(papers, top_n))
    return {
        "count": len(papers),
        "stat": f"{top_n} 篇精选",
        "markdown": content,
        "digest": " / ".join(p["title"][:60] for p in papers[:15]),
    }


if __name__ == "__main__":
    result = collect()
    print(result["markdown"] if result else "（今日无数据）")
