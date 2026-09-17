"""跨源核心信号：把各源的条目清单交给 DeepSeek，提炼今日最重要的 3-5 个信号。

这是合并成日报后才有的编辑层：同一事件在多个源同时出现（如既上新闻又有大佬讨论）
会被合并为一条高优先级信号。
"""
from ai_analyze import analyze

MAX_DIGEST_PER_SOURCE = 700


def build_input(results: list) -> str:
    blocks = []
    for r in results:
        digest = (r.get("digest") or "").strip()
        if r.get("ok") and not r.get("empty") and digest:
            blocks.append(f"[{r['name']}] {digest[:MAX_DIGEST_PER_SOURCE]}")
    return "\n\n".join(blocks)


def generate(results: list) -> str:
    """返回核心信号 markdown（编号行列表）；无可用输入或调用失败时返回空串。"""
    source_digest = build_input(results)
    if not source_digest:
        return ""
    prompt = f"""以下是今日各信息源的条目清单。请跨源综合判断，挑出今天最重要的 3-5 个核心信号：
1. 优先合并"多个源同时出现"的话题（如同一事件既上新闻又有大佬讨论、既上热搜又发了论文）
2. 每条信号一句话（不超过 50 字），信息量优先，不要空话
3. 末尾用括号标注来源，如（新闻 · X 观点）

输出格式（严格按此，每行一条，共 3-5 行，不要其他内容）：
1. {{信号}}
2. {{信号}}

---

各源条目清单：
{source_digest}
"""
    try:
        return analyze(prompt)
    except Exception as e:
        print(f"[signals] 核心信号提炼失败（不影响版块内容）: {e}")
        return ""


if __name__ == "__main__":
    from sources import ALL_SOURCES, run_source
    print(generate([run_source(m) for m in ALL_SOURCES]))
