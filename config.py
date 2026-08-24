import os
import yaml
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

def load_config():
    path = Path(__file__).parent / "config.yaml"
    with open(path) as f:
        cfg = yaml.safe_load(f)
    cfg["deepseek"]["api_key"] = os.environ["DEEPSEEK_API_KEY"]
    cfg["lark"]["rss_webhook"] = os.environ["LARK_RSS_WEBHOOK"]
    cfg["lark"]["github_webhook"] = os.environ["LARK_GITHUB_WEBHOOK"]
    cfg["lark"]["x_webhook"] = os.environ["LARK_X_WEBHOOK"]
    cfg["lark"]["arxiv_webhook"] = os.environ["LARK_ARXIV_WEBHOOK"]
    cfg["lark"]["producthunt_webhook"] = os.environ["LARK_PRODUCTHUNT_WEBHOOK"]
    cfg["lark"]["trends_webhook"] = os.environ["LARK_TRENDS_WEBHOOK"]
    cfg["producthunt"]["token"] = os.environ.get("PRODUCTHUNT_TOKEN", "")
    return cfg

cfg = load_config()
