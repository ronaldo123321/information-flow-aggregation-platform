"""爬取 Product Hunt 每日 AI 产品榜，用 DeepSeek 介绍，推送飞书。"""
import requests
from datetime import datetime, date, timedelta
from config import cfg
from ai_analyze import analyze
from lark_push import push

PH_API = "https://api.producthunt.com/v2/api/graphql"

QUERY = """
query {{
  posts(order: VOTES, postedAfter: "{date}T00:00:00Z", topic: "artificial-intelligence", first: {limit}) {{
    edges {{
      node {{
        name
        tagline
        description
        votesCount
        url
        website
        topics {{
          edges {{ node {{ name }} }}
        }}
      }}
    }}
  }}
}}
"""


def fetch_products(max_results: int) -> list:
    token = cfg.get("producthunt", {}).get("token", "")
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    resp = requests.post(
        PH_API,
        json={"query": QUERY.format(date=yesterday, limit=max_results)},
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        timeout=15,
    )
    resp.raise_for_status()
    edges = resp.json().get("data", {}).get("posts", {}).get("edges", [])
    return [
        {
            "name": e["node"]["name"],
            "tagline": e["node"]["tagline"],
            "description": (e["node"].get("description") or "")[:300],
            "votes": e["node"]["votesCount"],
            "url": e["node"]["url"],
        }
        for e in edges
    ]


def build_prompt(products: list, top_n: int) -> str:
    items_text = "\n\n".join(
        f"{i+1}. **{p['name']}** (👍{p['votes']})\n一句话: {p['tagline']}\n描述: {p['description']}\n链接: {p['url']}"
        for i, p in enumerate(products)
    )
    return f"""以下是 Product Hunt 昨日 AI 产品榜单（共 {len(products)} 个），请：
1. 筛选出最值得关注的前 {top_n} 个
2. 对每个产品：介绍它解决什么问题、目标用户是谁、有什么亮点

输出格式（严格按此）：

## 🚀 AI 产品日报 · {datetime.now().strftime('%Y-%m-%d')}

**{{序号}}. {{产品名}}** · 👍{{票数}}
📌 定位：{{一句话说清楚是什么}}
🎯 用户：{{目标用户群体}}
✨ 亮点：{{最值得关注的一个特性}}
🔗 {{product hunt链接}}

---

产品列表：
{items_text}
"""


def run():
    top_n = cfg.get("producthunt", {}).get("top_n", 6)
    max_fetch = cfg.get("producthunt", {}).get("max_fetch", 20)
    products = fetch_products(max_fetch)
    if not products:
        print("[producthunt] 未获取到产品，跳过推送")
        return
    print(f"[producthunt] 抓取到 {len(products)} 个，AI 筛选前 {top_n} 个")
    content = analyze(build_prompt(products, top_n))
    push(
        cfg["lark"]["producthunt_webhook"],
        f"🚀 AI 产品日报 · {datetime.now().strftime('%Y-%m-%d')}",
        content,
    )
    print("[producthunt] 推送完成")


if __name__ == "__main__":
    run()
