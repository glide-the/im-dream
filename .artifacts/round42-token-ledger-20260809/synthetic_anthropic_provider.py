from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json


class Handler(BaseHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers.get("content-length", "0"))
        raw = self.rfile.read(length)
        if self.path != "/v1/messages":
            self.send_response(404)
            self.end_headers()
            return
        request_body = json.loads(raw or b"{}")
        response_body = {
                "id": "msg_round42_synthetic",
                "type": "message",
                "role": "assistant",
                "model": "round42-synthetic",
                "content": [{"type": "text", "text": "ok"}],
                "stop_reason": "end_turn",
                "stop_sequence": None,
        }
        messages = request_body.get("messages", [])
        if not any(message.get("content") == "missing usage" for message in messages):
            response_body["usage"] = {"input_tokens": 7, "output_tokens": 5}
        body = json.dumps(response_body).encode("utf-8")
        self.send_response(200)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.send_header("request-id", "provider-round42-synthetic")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        return


ThreadingHTTPServer(("127.0.0.1", 4101), Handler).serve_forever()
