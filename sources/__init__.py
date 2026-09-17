"""信息源采集包：每个模块只负责抓取和 AI 提炼，返回结构化结果，由 report 统一编排。

模块约定：
- KEY / ICON / NAME：源标识，用于卡片速览和 HTML 锚点
- collect() -> dict | None：返回 {"count", "stat", "markdown", "digest"}，
  无数据返回 None；digest 是供跨源核心信号提炼用的标题清单
"""
from datetime import datetime

from . import rss, github, arxiv, producthunt, trends, x

# 每个源参与的星期（weekday(): 周一=0）；None 表示每天
SCHEDULE = {
    rss.KEY: None,
    github.KEY: {0},
    arxiv.KEY: {2},
    producthunt.KEY: None,
    trends.KEY: None,
    x.KEY: None,
}

# 未排期时在卡片里展示的频率说明
CADENCE = {
    github.KEY: "每周一更新",
    arxiv.KEY: "每周三更新",
}

ALL_SOURCES = [rss, github, arxiv, producthunt, trends, x]


def due_sources(weekday=None) -> list:
    """返回今天应参与日报的源模块。"""
    weekday = datetime.now().weekday() if weekday is None else weekday
    return [m for m in ALL_SOURCES if SCHEDULE[m.KEY] is None or weekday in SCHEDULE[m.KEY]]


def run_source(module) -> dict:
    """运行单个源并做失败隔离：单个源挂掉只影响自己的版块。"""
    base = {"key": module.KEY, "icon": module.ICON, "name": module.NAME}
    try:
        result = module.collect()
    except Exception as e:
        print(f"[report] {module.KEY} 采集失败: {e}")
        return {**base, "ok": False, "empty": False, "error": str(e),
                "count": 0, "stat": "", "markdown": "", "digest": ""}
    if not result:
        return {**base, "ok": True, "empty": True, "error": None,
                "count": 0, "stat": "今日无更新", "markdown": "", "digest": ""}
    return {**base, "ok": True, "empty": False, "error": None, **result}
