"""Локальный сервер SubPing: статика фронтенда + реверс-прокси /api на render.com.

Телефон ходит на https://mikhailpc.taileb4858.ts.net (Tailscale, HTTPS),
этот сервер отдаёт сайт и проксирует API через локальный VPN-прокси Clash.
"""
import http.server
import mimetypes
import os
import urllib.error
import urllib.request

UPSTREAM = "https://subtrack-api-jszq.onrender.com"
PORT = 8000
FRONTEND_DIR = os.path.normpath(os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "frontend"))
PROXY = "http://127.0.0.1:10809"
PASS_HEADERS = ("Content-Type", "Authorization", "Origin")

urllib.request.install_opener(urllib.request.build_opener(
    urllib.request.ProxyHandler({"http": PROXY, "https": PROXY})))

mimetypes.add_type("text/html", ".html")
mimetypes.add_type("text/plain", ".txt")


def cors_headers(origin):
    h = {
        "Access-Control-Allow-Origin": origin if origin else "*",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
        "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, OPTIONS",
    }
    return h


class Handler(http.server.BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _send(self, code, body=b"", content_type="text/plain; charset=utf-8", extra=None):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def do_OPTIONS(self):
        self._send(204, b"", "text/plain", cors_headers(self.headers.get("Origin")))

    def _serve_static(self):
        rel = self.path.split("?", 1)[0].split("#", 1)[0]
        if rel in ("", "/"):
            rel = "/index.html"
        base = os.path.normpath(FRONTEND_DIR)
        path = os.path.normpath(os.path.join(base, rel.lstrip("/")))
        if not path.startswith(base):
            self._send(403)
            return
        if not os.path.isfile(path):
            self._send(404)
            return
        ctype = mimetypes.guess_type(path)[0] or "application/octet-stream"
        with open(path, "rb") as f:
            body = f.read()
        self._send(200, body, ctype, cors_headers(self.headers.get("Origin")))

    def _proxy_api(self):
        body = None
        length = self.headers.get("Content-Length")
        if length:
            body = self.rfile.read(int(length))
        url = UPSTREAM + self.path
        req = urllib.request.Request(url, data=body, method=self.command)
        for key in PASS_HEADERS:
            value = self.headers.get(key)
            if value:
                req.add_header(key, value)
        extra = cors_headers(self.headers.get("Origin"))
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = resp.read()
                self.send_response(resp.status)
                for key, value in resp.headers.items():
                    if key.lower() not in ("transfer-encoding", "connection", "content-length"):
                        self.send_header(key, value)
                for k, v in extra.items():
                    self.send_header(k, v)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
        except urllib.error.HTTPError as err:
            data = err.read()
            self.send_response(err.code)
            for key, value in err.headers.items():
                if key.lower() not in ("transfer-encoding", "connection", "content-length"):
                    self.send_header(key, value)
            for k, v in extra.items():
                self.send_header(k, v)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        except Exception:
            self._send(502, b'{"detail":"proxy upstream error"}', "application/json", extra)

    def _do(self):
        path = self.path.split("?", 1)[0]
        if path.startswith("/api/"):
            self._proxy_api()
        else:
            self._serve_static()

    do_GET = _do
    do_POST = _do
    do_PUT = _do
    do_PATCH = _do
    do_DELETE = _do

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    http.server.ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
