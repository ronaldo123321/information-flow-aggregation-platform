"""日报编排：跑当日所有信息源（独立容错）→ 跨源核心信号 → HTML 报告 + 飞书摘要卡片。

手动执行：
    python -m report --dry-run   # 生成 HTML 但不推送
    python -m report             # 生成并推送
"""
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

from config import cfg
from lark_push import push_card
from sources import ALL_SOURCES, CADENCE, due_sources, run_source
import signals as signals_mod
import render_html

WEEKDAY_CN = "一二三四五六日"
REPORTS_DIR = Path(__file__).parent / cfg.get("report", {}).get("dir", "reports")


def build_card(results: list, signals: str, not_due: list) -> str:
    lines = []
    if signals:
        lines += ["**🎯 今日核心信号**", "", signals, ""]
    lines.append("**📊 今日版块**")
    lines.append("")
    for r in results:
        if r["ok"] and not r["empty"]:
            lines.append(f"{r['icon']} **{r['name']}** · {r['stat']}")
        elif r["empty"]:
            lines.append(f"{r['icon']} {r['name']} · 今日无更新")
        else:
            lines.append(f"{r['icon']} {r['name']} · ⚠️ 抓取失败")
    if not_due:
        lines += ["", f"🕘 本期未排期：{' · '.join(not_due)}"]
    lines += ["", f"🕒 生成于 {datetime.now():%H:%M}，详细内容见完整报告"]
    return "\n".join(lines)


def write_digest(results: list, signals: str):
    """把当天结构化摘要存为 JSON，供周度机会画布（weekly_poc）汇总。"""
    digest_dir = REPORTS_DIR / "digests"
    digest_dir.mkdir(exist_ok=True)
    payload = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "signals": signals,
        "sources": [
            {
                "key": r["key"],
                "name": r["name"],
                "stat": r.get("stat", ""),
                "digest": r.get("digest", ""),
                "markdown": (r.get("markdown") or "")[:4000],
            }
            for r in results if r["ok"] and not r["empty"]
        ],
    }
    path = digest_dir / f"{payload['date']}.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[report] 当日摘要已存档: {path}")


def run(push: bool = True):
    due = due_sources()
    results = [run_source(m) for m in due]

    if not any(r["ok"] and not r["empty"] for r in results):
        failed = [r["key"] for r in results if not r["ok"]]
        if failed:
            print(f"[report] 当日所有源均未产出内容（失败: {', '.join(failed)}），跳过生成与推送，请检查 DeepSeek Key 和网络")
        else:
            print("[report] 当日所有源均无新内容，跳过生成与推送")
        return

    sig = signals_mod.generate(results)

    html = render_html.render(results, sig)
    REPORTS_DIR.mkdir(exist_ok=True)
    dated = REPORTS_DIR / f"{datetime.now():%Y-%m-%d}.html"
    dated.write_text(html, encoding="utf-8")
    shutil.copyfile(dated, REPORTS_DIR / "latest.html")
    write_digest(results, sig)
    print(f"[report] 报告已生成: {dated}")

    if not push:
        print("[report] dry-run 模式，跳过推送")
        return
    due_keys = {r["key"] for r in results}
    not_due = [
        f"{m.ICON} {m.NAME}（{CADENCE.get(m.KEY, '定期更新')}）"
        for m in ALL_SOURCES if m.KEY not in due_keys
    ]
    now = datetime.now()
    title = f"🧭 AI 情报日报 · {now:%m-%d} 周{WEEKDAY_CN[now.weekday()]}"

    # 报告地址：优先上传 GCS 拿公网 URL，失败或未配置则回退本地服务地址
    report_url = ""
    if cfg["report"].get("gcs_bucket"):
        try:
            from storage_gcs import upload_reports
            report_url = upload_reports([dated, REPORTS_DIR / "latest.html"])
        except Exception as e:
            print(f"[report] GCS 上传失败，回退本地服务地址: {e}")
    if not report_url:
        report_url = cfg["report"]["base_url"].rstrip("/") + "/reports/latest.html"

    if not cfg["lark"]["daily_webhook"]:
        print("[report] 未配置 LARK_DAILY_WEBHOOK，跳过推送（HTML 报告已生成）")
        return

    push_card(
        cfg["lark"]["daily_webhook"],
        title,
        build_card(results, sig, not_due),
        button_text="阅读完整报告 →",
        button_url=report_url,
    )
    print(f"[report] 摘要卡片已推送，报告地址: {report_url}")


if __name__ == "__main__":
    run(push="--dry-run" not in sys.argv)
