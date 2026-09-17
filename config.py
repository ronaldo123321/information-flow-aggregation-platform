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
    # 日报推送的群 Webhook；兼容旧变量名 LARK_RSS_WEBHOOK
    cfg["lark"]["daily_webhook"] = (
        os.environ.get("LARK_DAILY_WEBHOOK") or os.environ.get("LARK_RSS_WEBHOOK", "")
    )
    # 晚间 X 增量卡单独一个 Webhook
    cfg["lark"]["x_webhook"] = os.environ.get("LARK_X_WEBHOOK", "")
    # Codex 重置监控推送；未配置时回落到 X 观点的群
    cfg["lark"]["tibo_webhook"] = os.environ.get("LARK_TIBO_WEBHOOK") or cfg["lark"]["x_webhook"]
    cfg["producthunt"]["token"] = os.environ.get("PRODUCTHUNT_TOKEN", "")
    # 报告对外访问地址：环境变量 > config.yaml > 本机默认
    cfg["report"]["base_url"] = (
        os.environ.get("REPORT_BASE_URL")
        or cfg.get("report", {}).get("base_url")
        or "http://localhost:8080"
    )
    # GCS bucket：配置后报告会自动上传，卡片按钮用公网地址。
    # GCS_BUCKET_NAME 是平台控制台的标准变量名，GCS_BUCKET 为本机简写
    cfg["report"]["gcs_bucket"] = (
        os.environ.get("GCS_BUCKET_NAME")
        or os.environ.get("GCS_BUCKET")
        or cfg.get("report", {}).get("gcs_bucket")
        or ""
    )
    return cfg

cfg = load_config()
