"""server.py: the door between the web page and the agent. Python's standard library only, listening on 127.0.0.1 ONLY.

    POST /chat    {"message": str, "history": [{"role", "content"}]}  ->  {"reply", "sources", "mode"}     (400 or 429 with a short JSON error when refused)
    GET  /health  ->  {"status", "mode", "model", "web_weather", "has_key"}                                (never the key itself)
    GET  /...     serves the frontend/ folder read-only, so one address shows the page AND the assistant:  open the address it prints
    OPTIONS       answers the browser's permission check, so the page also works when opened straight from a file

Run:  python backend/server.py      (with no key in the root .env it uses the offline model and never touches the network)
"""
import json
import mimetypes
import threading
import time
from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import agent
import config
from llm import GeminiLLM, OfflineLLM

FRONTEND = config.ROOT / "frontend"
MAX_BODY = 20_000


def make_server(llm, cfg, host="127.0.0.1", port=0):
    hits, lock = defaultdict(deque), threading.Lock()

    def limited(ip):
        now = time.time()
        with lock:
            q = hits[ip]
            while q and now - q[0] > 60:
                q.popleft()
            if len(q) >= cfg["rate_per_minute"]:
                return True
            q.append(now)
            return False

    class Handler(BaseHTTPRequestHandler):
        server_version = "InsightsBackend/1.0"

        def log_message(self, fmt, *args):                           # method, path and status only: never the question or any key
            print(f"  {self.command} {self.path.split('?')[0]} -> {args[1] if len(args) > 1 else ''}", flush=True)

        def _send(self, code, payload, ctype="application/json"):
            body = payload if isinstance(payload, bytes) else json.dumps(payload).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_OPTIONS(self):
            self._send(204, b"", "text/plain")

        def do_GET(self):
            path = self.path.split("?")[0]
            if path == "/health":
                p = config.public(cfg)
                return self._send(200, {"status": "ok", "mode": llm.name, "model": p["model"] if llm.name == "gemini" else None, "web_weather": p["enable_web"], "has_key": p["has_key"]})
            rel = "index.html" if path in ("/", "") else path.lstrip("/")
            target = (FRONTEND / rel).resolve()
            if FRONTEND.resolve() not in target.parents or not target.is_file():          # nothing outside frontend/ can ever be read
                return self._send(404, {"error": "not found"})
            self._send(200, target.read_bytes(), (mimetypes.guess_type(str(target))[0] or "application/octet-stream") + ("; charset=utf-8" if target.suffix in (".html", ".js", ".css") else ""))

        def do_POST(self):
            if self.path.split("?")[0] != "/chat":
                return self._send(404, {"error": "not found"})
            if limited(self.client_address[0]):
                return self._send(429, {"error": "too many questions, please wait a moment"})
            try:
                n = int(self.headers.get("Content-Length", "0"))
                if n <= 0 or n > MAX_BODY:
                    return self._send(400, {"error": "empty or too large request"})
                data = json.loads(self.rfile.read(n).decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                return self._send(400, {"error": "the request is not valid JSON"})
            message = data.get("message") if isinstance(data, dict) else None
            if not isinstance(message, str) or not message.strip():
                return self._send(400, {"error": "message is required"})
            if len(message) > cfg["max_message_chars"]:
                return self._send(400, {"error": f"message is longer than {cfg['max_message_chars']} characters"})
            self._send(200, agent.run(llm, data.get("history"), message.strip(), cfg))

    return ThreadingHTTPServer((host, port), Handler)


def main():
    config.load_env()
    cfg = config.settings()
    llm = GeminiLLM(cfg["api_key"], cfg["model"], cfg["timeout_s"], fallbacks=cfg["fallback_models"]) if cfg["api_key"] else OfflineLLM()
    srv = make_server(llm, cfg, "127.0.0.1", cfg["port"])
    print(f"Backend running on http://127.0.0.1:{cfg['port']}  (model: {llm.name}, live weather: {'on' if cfg['enable_web'] else 'off'})")
    print("Open that address to use the page with the assistant. Press Ctrl+C to stop.", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("stopped")


if __name__ == "__main__":
    main()
