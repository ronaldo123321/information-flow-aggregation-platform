"""报告上传：把生成的 HTML 上传到 GCS bucket（公开读取），作为报告对外地址。

服务账号凭据按优先级解析（前两个是平台控制台注入的标准变量）：
1. GCS_KEY_FILE             key 文件路径（如 /gcs-key.json，文件需存在）
2. GCS_CONFIG_JSON          key 的 JSON 原文
3. GCS_SERVICE_ACCOUNT_B64  key JSON 的 base64
4. 都没有则走 GOOGLE_APPLICATION_CREDENTIALS / gcloud application-default（本机开发）
"""
import base64
import json
import os
import tempfile
from pathlib import Path

from config import cfg

GCS_PUBLIC_BASE = "https://storage.googleapis.com"


def _temp_key_file(content: str) -> str:
    path = Path(tempfile.gettempdir()) / "gcs_key.json"
    path.write_text(content, encoding="utf-8")
    return str(path)


def _load_sa_key() -> str | None:
    """按优先级解析服务账号 key，返回 key 文件路径；无可用凭据返回 None。"""
    key_file = os.environ.get("GCS_KEY_FILE", "").strip()
    if key_file:
        if Path(key_file).is_file():
            return key_file
        print(f"[gcs] GCS_KEY_FILE 指向的文件不存在: {key_file}，尝试其他凭据")

    inline = os.environ.get("GCS_CONFIG_JSON", "").strip()
    if inline:
        try:
            json.loads(inline)
            return _temp_key_file(inline)
        except json.JSONDecodeError as e:
            print(f"[gcs] GCS_CONFIG_JSON 不是合法 JSON: {e}，尝试其他凭据")

    b64 = os.environ.get("GCS_SERVICE_ACCOUNT_B64", "").strip()
    if b64:
        try:
            return _temp_key_file(base64.b64decode(b64).decode("utf-8"))
        except Exception as e:
            print(f"[gcs] GCS_SERVICE_ACCOUNT_B64 解码失败: {e}，尝试其他凭据")

    return None


def _client():
    from google.cloud import storage

    project = os.environ.get("GCS_PROJECT_ID") or None
    key_path = _load_sa_key()
    if key_path:
        return storage.Client.from_service_account_json(key_path, project=project)
    return storage.Client(project=project)


def upload_reports(files: list[Path], latest_name: str = "latest.html") -> str:
    """上传报告文件到所配 bucket，返回 latest_name 对应的公开 URL。未配置 bucket 返回空串。"""
    bucket_name = cfg["report"].get("gcs_bucket", "")
    if not bucket_name:
        return ""
    client = _client()
    bucket = client.bucket(bucket_name)
    for f in files:
        bucket.blob(f.name).upload_from_filename(
            str(f), content_type="text/html; charset=utf-8"
        )
        print(f"[gcs] 已上传 {f.name} -> gs://{bucket_name}/{f.name}")
    return f"{GCS_PUBLIC_BASE}/{bucket_name}/{latest_name}"


if __name__ == "__main__":
    reports = sorted(Path(__file__).parent.joinpath(
        cfg.get("report", {}).get("dir", "reports")).glob("*.html"))
    print(upload_reports(reports) if reports else "reports/ 目录为空，先跑一次 python -m report")
