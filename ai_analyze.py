from openai import OpenAI
from config import cfg

_client = None

def _get_client():
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=cfg["deepseek"]["api_key"],
            base_url=cfg["deepseek"]["base_url"],
        )
    return _client

def analyze(prompt: str) -> str:
    resp = _get_client().chat.completions.create(
        model=cfg["deepseek"]["model"],
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3,
    )
    return resp.choices[0].message.content.strip()
