"""HTTP 服务：健康检查 + 托管 reports/ 目录下的 HTML 报告。

- GET /health        -> ok（供容器平台探活）
- GET /reports/x.html -> 报告静态文件
- GET /              -> 跳转最新报告
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

REPORTS_DIR = Path(__file__).parent / "reports"


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = self.path.split("?")[0]
        if path in ("/health", "/healthz"):
            self._text(200, "ok")
        elif path == "/reports" or path == "/reports/":
            self._redirect("/reports/latest.html")
        elif path.startswith("/reports/"):
            self._serve_report(path[len("/reports/"):])
        elif path == "/":
            if (REPORTS_DIR / "latest.html").is_file():
                self._redirect("/reports/latest.html")
            else:
                self._text(200, "service is running")
        else:
            self._text(404, "not found")

    def _serve_report(self, name: str):
        # 只允许纯文件名，防路径穿越
        if "/" in name or ".." in name:
            self._text(404, "not found")
            return
        target = REPORTS_DIR / name
        if not target.is_file():
            self._text(404, "report not found")
            return
        body = target.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _redirect(self, location: str):
        self.send_response(302)
        self.send_header("Location", location)
        self.end_headers()

    def _text(self, code: int, text: str):
        body = text.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass  # 静默日志


def run(port=8080):
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()
