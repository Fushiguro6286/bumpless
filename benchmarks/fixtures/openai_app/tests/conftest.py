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
        if self.path.endswith("/chat/completions"):
            prompt = req["messages"][-1]["content"]
            if "RATE_LIMIT" in prompt:
                return self._send(429, {"error": {"message": "slow down", "type": "rate_limit_error", "code": "rate"}})
            if "BOOM" in prompt:
                return self._send(400, {"error": {"message": "bad request", "type": "invalid_request_error"}})
            content = "SUMMARY: " + prompt.split("\n")[-1][:40]
            return self._send(200, {
                "id": "chatcmpl-1", "object": "chat.completion", "created": 1700000000, "model": req["model"],
                "choices": [{"index": 0, "message": {"role": "assistant", "content": content}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": len(prompt.split()), "completion_tokens": 3,
                          "total_tokens": len(prompt.split()) + 3},
            })
        if self.path.endswith("/embeddings"):
            texts = req["input"] if isinstance(req["input"], list) else [req["input"]]
            data = [{"object": "embedding", "index": i,
                     "embedding": [float(len(t)), float(t.count("a")), 1.0]} for i, t in enumerate(texts)]
            return self._send(200, {"object": "list", "data": data, "model": req["model"],
                                    "usage": {"prompt_tokens": 1, "total_tokens": 1}})
        self._send(404, {"error": {"message": "not found"}})


_server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=_server.serve_forever, daemon=True).start()
os.environ["LLM_BASE_URL"] = f"http://127.0.0.1:{_server.server_address[1]}/v1"
os.environ.setdefault("OPENAI_API_KEY", "sk-test")
