"""信息源：Google Trends 各重点市场每日热搜（官方 RSS），DeepSeek 提炼出海机会。"""
import requests
import xml.etree.ElementTree as ET
from config import cfg
from ai_analyze import analyze

KEY, ICON, NAME = "trends", "🔥", "全球热搜"

RSS_URL = "https://trends.google.com/trending/rss?geo={geo}"
NS = {"ht": "https://trends.google.com/trending/rss"}


def fetch_trending(countries: dict, per_country: int) -> dict:
    """countries: {国家显示名: geo代码}，返回 {显示名: [(关键词, 搜索量, [新闻标题...])]}"""
    result = {}
    for name, geo in countries.items():
        try:
            resp = requests.get(RSS_URL.format(geo=geo), timeout=15)
            resp.raise_for_status()
            root = ET.fromstring(resp.content)
            items = []
            for item in root.findall(".//item")[:per_country]:
                title = item.findtext("title", "").strip()
                traffic = item.findtext("ht:approx_traffic", "", NS).strip()
                news = [
                    n.findtext("ht:news_item_title", "", NS).strip()
                    for n in item.findall("ht:news_item", NS)
                ][:2]
                items.append((title, traffic, news))
            result[name] = items
            print(f"[trends] {name}: {len(items)} 个热搜")
        except Exception as e:
            print(f"[trends] {name} 抓取失败: {e}")
    return result


def build_prompt(data: dict) -> str:
    blocks = []
    for name, items in data.items():
        lines = [f"【{name}】"]
        for title, traffic, news in items:
            news_str = f"（相关新闻: {'; '.join(news)}）" if news else ""
            lines.append(f"- {title} [{traffic}]{news_str}")
        blocks.append("\n".join(lines))
    blocks_text = "\n\n".join(blocks)
    markets = "、".join(data.keys())
    return f"""以下是今日 Google Trends 各重点市场（{markets}）的每日热搜关键词（含搜索量和相关新闻）。

任务：
1. 识别跨市场共同出现的热点，重点标注与 AI / 科技 / 互联网产品相关的趋势
2. 按以下结构输出：

**🤖 AI / 科技相关热点**
- **{{关键词}}**（{{出现市场}}）：{{一句话解释为什么火 + 对出海产品的启发}}

**🌍 其他值得关注的趋势**
- **{{关键词}}**（{{市场}}）：{{一句话解释}}

**💡 出海启示**
{{2-3 句话，总结今日热搜对 AI 出海产品的可参考机会}}

要求：只输出以上三部分，不要大标题、分割线和总结语；没有 AI 相关热点时省略第一部分。

---

原始热搜数据：
{blocks_text}
"""


def collect() -> dict | None:
    tcfg = cfg.get("trends", {})
    countries = tcfg.get("countries", {"美国": "US"})
    per_country = tcfg.get("per_country", 10)
    data = fetch_trending(countries, per_country)
    if not data:
        print("[trends] 未获取到任何热搜")
        return None
    total = sum(len(v) for v in data.values())
    content = analyze(build_prompt(data))
    return {
        "count": total,
        "stat": f"{len(data)} 个市场",
        "markdown": content,
        "digest": "；".join(
            f"{name}: {('、'.join(t for t, _, _ in items))[:120]}"
            for name, items in data.items()
        ),
    }


if __name__ == "__main__":
    result = collect()
    print(result["markdown"] if result else "（今日无数据）")
