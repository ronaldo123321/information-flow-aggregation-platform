import requests

def push(webhook_url: str, title: str, content: str):
    """推送卡片消息到飞书群 webhook"""
    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": title},
                "template": "blue"
            },
            "elements": [
                {"tag": "markdown", "content": content}
            ]
        }
    }
    resp = requests.post(webhook_url, json=payload, timeout=10)
    resp.raise_for_status()
    result = resp.json()
    if result.get("code", 0) != 0:
        raise RuntimeError(f"Lark error: {result}")
