"""周度机会画布：汇总本周每日情报摘要，由 DeepSeek 提炼 2-3 个可落地的 POC 方向。

每周五 08:30（日报之后）由 main.py 调度。情报积累不足 3 天时自动跳过，
避免用太薄的输入硬凑方向。手动运行：

    python -m weekly_poc --dry-run   # 生成画布但不推送
    python -m weekly_poc --force     # 忽略最少天数限制
"""
import json
import re
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path

import markdown as md

from ai_analyze import analyze
from config import cfg
from lark_push import push_card
import render_html

REPORTS_DIR = Path(__file__).parent / cfg.get("report", {}).get("dir", "reports")
DIGEST_DIR = REPORTS_DIR / "digests"
MIN_DAYS = 3
WEEKDAY_CN = "一二三四五六日"


def load_week_digests(force: bool = False) -> list | None:
    """加载最近 7 天的每日摘要 JSON，按日期排序。"""
    if not DIGEST_DIR.is_dir():
        print("[weekly-poc] 暂无每日摘要（digests/ 为空），等日报积累后再生成")
        return None
    cutoff = datetime.now() - timedelta(days=7)
    digests = []
    for f in sorted(DIGEST_DIR.glob("*.json")):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
            if datetime.strptime(d.get("date", ""), "%Y-%m-%d") >= cutoff:
                digests.append(d)
        except Exception as e:
            print(f"[weekly-poc] 跳过损坏的摘要 {f.name}: {e}")
    if not force and len(digests) < MIN_DAYS:
        print(f"[weekly-poc] 本周仅积累 {len(digests)} 天情报（不足 {MIN_DAYS} 天），跳过；"
              f"积累充分后自动生成，或用 --force 强制")
        return None
    return digests


def build_prompt(digests: list) -> str:
    signal_lines, source_blocks = [], []
    for d in digests:
        day = d.get("date", "")
        sig = (d.get("signals") or "").strip()
        if sig:
            signal_lines.append(f"【{day}】\n{sig}")
        for s in d.get("sources", []):
            digest = (s.get("digest") or "").strip()
            if digest:
                source_blocks.append(f"[{day}·{s['name']}] {digest[:400]}")
    return f"""你是资深的 AI 产品机会分析师。以下是过去一周「AI 情报日报」累计的核心信号与各源条目清单。

任务：从中提炼 2-3 个可落地的 POC 产品方向。要求：
1. 每个方向必须有本周情报中的具体信号支撑（引用信号，注明日期与来源），禁止凭空编造
2. 方向之间差异化明显，且都能由 1-2 人的小团队在 1-2 周内做出最小验证
3. 明确给出判停指标，宁可保守不要画饼

输出格式（严格按此，不要大标题和总结语，方向之间空一行）：

**POC 1：{{方向名称}}**
📌 信号依据：{{本周哪些信号支撑，注明日期与来源}}
👥 用户与痛点：{{目标用户是谁，痛点是什么}}
🛠 最小验证：{{1-2 周能做出来的 MVP 形态}}
📏 判停指标：{{出现什么情况就放弃}}
⚠️ 风险：{{最大的一个风险}}

---

本周核心信号（按天累计）：
{chr(10).join(signal_lines)}

各源条目清单：
{chr(10).join(source_blocks)}
"""


def render_canvas(digests: list, content: str) -> str:
    now = datetime.now()
    days = [d.get("date", "") for d in digests]
    date_range = f"{days[0]} ~ {days[-1]}" if days else now.strftime("%Y-%m-%d")
    signals_html = "".join(
        f'<div class="signal">{ln.strip()}</div>'
        for d in digests
        for ln in (d.get("signals") or "").splitlines()
        if ln.strip()
    )
    body_html = md.markdown(render_html._normalize_md(content), extensions=["nl2br"])
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI 机会画布 · {date_range}</title>
<style>{render_html.CSS}</style>
</head>
<body id="top">
<main>
<header class="hero">
  <h1>🎯 AI 机会画布</h1>
  <p>{date_range} · 基于本周 {len(digests)} 天情报提炼</p>
</header>
<section class="card"><h2>🧭 本周核心信号回顾</h2>{signals_html}</section>
<section class="card"><h2>💡 POC 产品方向</h2><div class="body">{body_html}</div></section>
<footer>由 crawler_and_push_lark 自动生成于 {now.strftime('%Y-%m-%d %H:%M')}<br>
数据来源：本周各日「AI 情报日报」累计摘要</footer>
</main>
<a class="fab" href="#top">↑</a>
</body>
</html>
"""


def run(push: bool = True, force: bool = False):
    digests = load_week_digests(force)
    if not digests:
        return
    days = [d.get("date", "?") for d in digests]
    date_range = f"{days[0]} ~ {days[-1]}"
    print(f"[weekly-poc] 汇总 {len(digests)} 天情报（{date_range}），AI 提炼 POC 方向")
    content = analyze(build_prompt(digests))

    now = datetime.now()
    dated = REPORTS_DIR / f"poc-{now:%Y-%m-%d}.html"
    poc_latest = REPORTS_DIR / "poc-latest.html"
    REPORTS_DIR.mkdir(exist_ok=True)
    dated.write_text(render_canvas(digests, content), encoding="utf-8")
    shutil.copyfile(dated, poc_latest)
    print(f"[weekly-poc] 画布已生成: {dated}")

    if not push:
        print("[weekly-poc] dry-run 模式，跳过推送")
        return

    # 画布地址：优先 GCS 公网 URL，失败回退本地服务地址
    report_url = ""
    if cfg["report"].get("gcs_bucket"):
        try:
            from storage_gcs import upload_reports
            report_url = upload_reports([dated, poc_latest], latest_name="poc-latest.html")
        except Exception as e:
            print(f"[weekly-poc] GCS 上传失败，回退本地服务地址: {e}")
    if not report_url:
        report_url = cfg["report"]["base_url"].rstrip("/") + "/reports/poc-latest.html"

    if not cfg["lark"]["daily_webhook"]:
        print("[weekly-poc] 未配置 LARK_DAILY_WEBHOOK，跳过推送（画布已生成）")
        return

    names = re.findall(r"^\*\*POC \d+：(.*?)\*\*", content, flags=re.M)
    lines = [
        f"**🎯 本周机会画布 · {date_range}**",
        "",
        f"基于本周 {len(digests)} 天情报，提炼出 {len(names)} 个可落地的 POC 方向：",
        "",
    ]
    lines += [f"{i}. {n}" for i, n in enumerate(names, 1)]
    lines += ["", "证据链与判停指标见完整画布"]
    push_card(
        cfg["lark"]["daily_webhook"],
        f"🎯 AI 机会画布 · {now:%m-%d} 周{WEEKDAY_CN[now.weekday()]}",
        "\n".join(lines),
        button_text="查看机会画布 →",
        button_url=report_url,
    )
    print(f"[weekly-poc] 已推送，画布地址: {report_url}")


if __name__ == "__main__":
    run(push="--dry-run" not in sys.argv, force="--force" in sys.argv)
