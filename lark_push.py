"""飞书自定义机器人 Webhook 推送：纯 markdown 卡片 + 带按钮的摘要卡片。"""
import requests

# 飞书卡片有大小限制，超长时截断保底
MAX_CONTENT_LEN = 9000


def push(webhook_url: str, title: str, content: str):
    """推送 markdown 卡片消息到飞书群 webhook。

    注意：飞书卡片 markdown 不支持 #/## 标题语法（会原样输出），
    层级强调请用 **加粗**。
    """
    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": "blue"
            },
            "elements": [
                {"tag": "markdown", "content": content[:MAX_CONTENT_LEN]}
            ]
        }
    }
    _post(webhook_url, payload)


def push_card(webhook_url: str, title: str, content: str,
              button_text: str = "", button_url: str = "",
              template: str = "blue"):
    """推送带底部按钮的卡片，button_url 为空则不渲染按钮。"""
    content = content[:MAX_CONTENT_LEN]
    elements = [{"tag": "markdown", "content": content}]
    if button_url:
        elements.append({"tag": "hr"})
        elements.append({
            "tag": "action",
            "actions": [{
                "tag": "button",
                "text": {"tag": "plain_text", "content": button_text or "查看详情"},
                "type": "primary",
                "url": button_url,
            }],
        })
    payload = {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": template,
            },
            "elements": elements,
        }
    }
    _post(webhook_url, payload)


def _post(webhook_url: str, payload: dict):
    resp = requests.post(webhook_url, json=payload, timeout=10)
    resp.raise_for_status()
    result = resp.json()
    if result.get("code", 0) != 0:
        raise RuntimeError(f"Lark error: {result}")
