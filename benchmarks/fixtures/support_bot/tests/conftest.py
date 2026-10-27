"""A tiny fake OpenAI-compatible server, started before the app is imported."""

import json
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def _send(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        req = json.loads(self.rfile.read(int(self.headers["Content-Length"])) or b"{}")
        if not self.path.endswith("/chat/completions"):
            return self._send(404, {"error": {"message": "not found"}})
        text = req["messages"][-1]["content"]
        if "BOOM" in text:
            return self._send(500, {"error": {"message": "server error", "type": "server_error"}})
        return self._send(200, {
            "id": "chatcmpl-1", "object": "chat.completion", "created": 1700000000, "model": req["model"],
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "content": f"  Thanks! About: {text.splitlines()[0]}  "}}],
            "usage": {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10}})


_server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=_server.serve_forever, daemon=True).start()
os.environ["LLM_BASE_URL"] = f"http://127.0.0.1:{_server.server_address[1]}/v1"
os.environ["OPENAI_API_KEY"] = "sk-test"
