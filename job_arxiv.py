"""爬取 arxiv 本周高热 AI 论文，用 DeepSeek 翻译成人话，推送飞书。"""
import requests
from datetime import datetime, timezone, timedelta
from config import cfg
from ai_analyze import analyze
from lark_push import push

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
    return f"""以下是本周 arxiv 最新 AI 论文（共 {len(papers)} 篇），请：
1. 筛选出最有研究/应用价值的 {top_n} 篇
2. 对每篇用通俗语言介绍：研究了什么问题、用了什么方法、有什么意义

输出格式（严格按此）：

## 📄 AI 论文速递 · {datetime.now().strftime('%Y 第%W周')}

**{{序号}}. {{论文标题（中文翻译）}}**
🔬 原题：{{英文原标题}}
💬 通俗解读：{{2-3句话，非专业人士也能看懂}}
✨ 意义：{{一句话，说明对行业/产品的潜在影响}}
🔗 {{arxiv链接}}

---

论文列表：
{items_text}
"""


def run():
    top_n = cfg.get("arxiv", {}).get("top_n", 6)
    max_fetch = cfg.get("arxiv", {}).get("max_fetch", 50)
    papers = fetch_papers(max_fetch)
    if not papers:
        print("[arxiv] 未获取到论文，跳过推送")
        return
    print(f"[arxiv] 抓取到 {len(papers)} 篇，AI 筛选前 {top_n} 篇")
    content = analyze(build_prompt(papers, top_n))
    push(
        cfg["lark"]["arxiv_webhook"],
        f"📄 AI 论文速递 · {datetime.now().strftime('%Y 第%W周')}",
        content,
    )
    print("[arxiv] 推送完成")


if __name__ == "__main__":
    run()
