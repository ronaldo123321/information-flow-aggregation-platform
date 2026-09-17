"""把日报各版块渲染成单页 HTML 报告（自包含样式，无外部依赖）。"""
import re
from datetime import datetime
import markdown as md

WEEKDAY_CN = "一二三四五六日"

CSS = """
:root{--ink:#2c2a26;--muted:#8a8378;--teal:#1d3b36;--accent:#c96f2e;
--card-border:#e7dfd0;--bg:#f6f1e8}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.8 -apple-system,BlinkMacSystemFont,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif}
main{max-width:840px;margin:0 auto;padding:32px 20px 60px}
.hero{background:linear-gradient(135deg,#16382f 0%,#3f5d4a 55%,#c07a3e 100%);color:#fff;
border-radius:22px;padding:38px 36px;box-shadow:0 12px 30px rgba(22,56,47,.18)}
.hero h1{margin:0 0 8px;font-size:28px;letter-spacing:1px}
.hero p{margin:0;opacity:.85;font-size:14.5px}
.toc{display:flex;flex-wrap:wrap;gap:10px;margin:20px 0 6px}
.chip{background:#fff;border:1px solid var(--card-border);border-radius:999px;
padding:5px 14px;font-size:13px;color:var(--teal);text-decoration:none}
.card{background:#fff;border:1px solid var(--card-border);border-radius:16px;
padding:26px 28px;margin:18px 0}
.card h2{margin:0 0 14px;font-size:20px;color:var(--teal)}
.signal{background:#f2ede2;border-left:3px solid var(--accent);border-radius:8px;
padding:10px 14px;margin:10px 0;line-height:1.7}
.muted{color:var(--muted)}
.body p{margin:10px 0}
.body h1,.body h2,.body h3,.body h4{color:var(--teal);font-size:16px;margin:18px 0 6px}
.body a{color:#2f6fab;text-decoration:none;border-bottom:1px solid #c9dcec}
.body blockquote{margin:8px 0;padding:6px 14px;border-left:3px solid #d8cfbe;
color:#5f594e;background:#faf7f0;border-radius:0 8px 8px 0}
.body code{background:#f2ede2;border-radius:4px;padding:1px 5px;font-size:13px}
.body ul,.body ol{padding-left:22px;margin:10px 0}
footer{margin-top:26px;text-align:center;color:var(--muted);font-size:12.5px;line-height:1.8}
.fab{position:fixed;right:22px;bottom:26px;width:42px;height:42px;border-radius:50%;
background:var(--teal);color:#fff;display:flex;align-items:center;justify-content:center;
text-decoration:none;font-size:18px;box-shadow:0 6px 16px rgba(0,0,0,.2)}
@media (max-width:600px){.hero{padding:26px 22px}.card{padding:20px 18px}}
"""


_LIST_RE = re.compile(r"^\s*(?:[-*+]\s+|\d+[.、)]\s+)")
_QUOTE_RE = re.compile(r"^\s*>")


def _line_kind(line: str):
    if _LIST_RE.match(line):
        return "list"
    if _QUOTE_RE.match(line):
        return "quote"
    return None


def _normalize_md(text: str) -> str:
    """AI 输出是聊天式排版：列表/引用行常紧跟在普通文字后。

    Python-Markdown 要求块级元素前有空行，否则 "- item"、"> 引用" 会被
    当成普通段落文本原样输出，这里自动补空行。
    """
    out = []
    for line in text.splitlines():
        kind = _line_kind(line)
        if kind and out:
            prev = out[-1]
            if prev.strip() and _line_kind(prev) != kind:
                out.append("")
        out.append(line)
    return "\n".join(out)


def _md_to_html(text: str) -> str:
    # nl2br：AI 输出是聊天式换行，单个换行也要断行
    return md.markdown(_normalize_md(text), extensions=["nl2br"])


def _signals_html(signals: str) -> str:
    lines = [ln.strip() for ln in signals.splitlines() if ln.strip()]
    lead = re.compile(r"^[-*]\s*|^\d+[.、]\s*")
    blocks = "\n".join(
        f'<div class="signal">{lead.sub("", ln)}</div>'
        for ln in lines
    )
    return f'<section class="card"><h2>🎯 今日核心信号</h2>{blocks}</section>'


def render(results: list, signals: str) -> str:
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    subtitle = now.strftime("%Y-%m-%d") + f"（周{WEEKDAY_CN[now.weekday()]}）"

    chips, sections = [], []
    for r in results:
        chips.append(f'<a class="chip" href="#{r["key"]}">{r["icon"]} {r["name"]}</a>')
        if r["ok"] and r.get("markdown"):
            body = _md_to_html(r["markdown"])
        elif r["empty"]:
            body = '<p class="muted">今日无更新。</p>'
        else:
            body = '<p class="muted">⚠️ 本版块抓取失败，其余版块不受影响。</p>'
        sections.append(
            f'<section class="card" id="{r["key"]}">'
            f'<h2>{r["icon"]} {r["name"]}</h2>'
            f'<div class="body">{body}</div></section>'
        )

    signals_section = _signals_html(signals) if signals else ""
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI 情报日报 · {date_str}</title>
<style>{CSS}</style>
</head>
<body id="top">
<main>
<header class="hero">
  <h1>🧭 AI 情报日报</h1>
  <p>{subtitle}</p>
</header>
<nav class="toc">{''.join(chips)}</nav>
{signals_section}
{''.join(sections)}
<footer>由 crawler_and_push_lark 自动生成于 {now.strftime('%Y-%m-%d %H:%M')}<br>
数据源：RSS · Google Trends · Product Hunt · GitHub · arXiv · X</footer>
</main>
<a class="fab" href="#top">↑</a>
</body>
</html>
"""
