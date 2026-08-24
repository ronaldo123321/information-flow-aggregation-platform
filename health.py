"""最小 HTTP 健康检查服务，供容器平台探活使用。"""
from http.server import HTTPServer, BaseHTTPRequestHandler

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"ok")

    def log_message(self, *args):
        pass  # 静默日志

def run(port=8080):
    HTTPServer(("0.0.0.0", port), HealthHandler).serve_forever()
