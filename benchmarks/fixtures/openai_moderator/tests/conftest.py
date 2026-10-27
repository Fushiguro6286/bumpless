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
        if self.headers.get("Authorization") != "Bearer sk-test":
            return self._send(401, {"error": {"message": "bad key", "type": "invalid_request_error",
                                              "code": "invalid_api_key"}})
        if self.path.endswith("/moderations"):
            text = req["input"] if isinstance(req["input"], str) else req["input"][0]
            hate, violence = "hate" in text, "kill" in text
            return self._send(200, {"id": "modr-1", "model": "omni-moderation-latest", "results": [{
                "flagged": hate or violence,
                "categories": {"hate": hate, "violence": violence, "sexual": False},
                "category_scores": {"hate": 0.9 if hate else 0.01, "violence": 0.9 if violence else 0.01,
                                    "sexual": 0.0}}]})
        if self.path.endswith("/completions"):
            words = req["prompt"].split(":", 1)[-1].split()
            return self._send(200, {
                "id": "cmpl-1", "object": "text_completion", "created": 1700000000, "model": req["model"],
                "choices": [{"index": 0, "text": f"  Thanks for sharing about {words[-1] if words else 'that'}!",
                             "finish_reason": "stop", "logprobs": None}],
                "usage": {"prompt_tokens": 5, "completion_tokens": 5, "total_tokens": 10}})
        self._send(404, {"error": {"message": "not found"}})


_server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
threading.Thread(target=_server.serve_forever, daemon=True).start()
os.environ["LLM_BASE_URL"] = f"http://127.0.0.1:{_server.server_address[1]}/v1"
os.environ["OPENAI_API_KEY"] = "sk-test"
