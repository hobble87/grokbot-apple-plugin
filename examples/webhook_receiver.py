"""Tiny example webhook receiver for local testing.

Run:  APPLE_BRIDGE_WEBHOOK_TOKEN=secret python3 examples/webhook_receiver.py
Then set webhook_url to http://127.0.0.1:8765/hook. It echoes each message back
by returning {"reply": ...}; swap `answer()` for a call to your AI model.
"""
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

TOKEN = os.environ.get("APPLE_BRIDGE_WEBHOOK_TOKEN", "")


def answer(payload: dict) -> str:
    return f"You said: {payload['text']}"


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        if TOKEN and self.headers.get("Authorization") != f"Bearer {TOKEN}":
            self.send_response(401); self.end_headers(); return
        payload = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
        body = json.dumps({"reply": answer(payload)}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 8765), Handler).serve_forever()
