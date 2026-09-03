#!/usr/bin/env python3
"""Deterministic Anthropic SSE provider for a real Docker Claude sandbox probe.

[Input] HTTP POST requests from a test-owned Claude Code CLI and a caller-supplied listen port.
[Output] One configurable Bash tool_use followed by one end_turn response; no external model/OAuth traffic.
[Pos] Manual/CI container compatibility fixture, outside production runtime.
[Sync] 2026-08-19: add provider-free CLI 2.1.235 Bash and credential deny-read validation.
[Sync] 2026-09-04: accept an explicit test-owned command for provider-free
                    PreToolUse/Runtime contract probes; retain the sandbox probe default.
"""

from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json


def _frame(event: str, payload: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


def _response(*, request_number: int, use_tool: bool, command: str) -> bytes:
    if use_tool:
        events = (
            (
                "message_start",
                {
                    "type": "message_start",
                    "message": {
                        "id": f"msg_sandbox_{request_number}",
                        "type": "message",
                        "role": "assistant",
                        "content": [],
                        "model": "claude-sandbox-fake",
                        "stop_reason": None,
                        "stop_sequence": None,
                        "usage": {"input_tokens": 1, "output_tokens": 0},
                    },
                },
            ),
            (
                "content_block_start",
                {
                    "type": "content_block_start",
                    "index": 0,
                    "content_block": {
                        "type": "tool_use",
                        "id": "toolu_sandbox_probe",
                        "name": "Bash",
                        "input": {},
                    },
                },
            ),
            (
                "content_block_delta",
                {
                    "type": "content_block_delta",
                    "index": 0,
                    "delta": {
                        "type": "input_json_delta",
                        "partial_json": json.dumps({"command": command}),
                    },
                },
            ),
            ("content_block_stop", {"type": "content_block_stop", "index": 0}),
            (
                "message_delta",
                {
                    "type": "message_delta",
                    "delta": {"stop_reason": "tool_use", "stop_sequence": None},
                    "usage": {"output_tokens": 1},
                },
            ),
            ("message_stop", {"type": "message_stop"}),
        )
    else:
        events = (
            (
                "message_start",
                {
                    "type": "message_start",
                    "message": {
                        "id": f"msg_sandbox_{request_number}",
                        "type": "message",
                        "role": "assistant",
                        "content": [],
                        "model": "claude-sandbox-fake",
                        "stop_reason": None,
                        "stop_sequence": None,
                        "usage": {"input_tokens": 1, "output_tokens": 0},
                    },
                },
            ),
            (
                "content_block_start",
                {
                    "type": "content_block_start",
                    "index": 0,
                    "content_block": {"type": "text", "text": ""},
                },
            ),
            (
                "content_block_delta",
                {
                    "type": "content_block_delta",
                    "index": 0,
                    "delta": {"type": "text_delta", "text": "sandbox probe complete"},
                },
            ),
            ("content_block_stop", {"type": "content_block_stop", "index": 0}),
            (
                "message_delta",
                {
                    "type": "message_delta",
                    "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                    "usage": {"output_tokens": 1},
                },
            ),
            ("message_stop", {"type": "message_stop"}),
        )
    return "".join(_frame(event, payload) for event, payload in events).encode()


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    request_number = 0
    command = (
        "printf 'workspace-write-ok\\n' > sandbox-write.txt; "
        "if cat .claude-home/.credentials.json >/dev/null 2>&1; "
        "then printf 'credential-readable\\n'; exit 91; "
        "else printf 'credential-denied\\n'; fi"
    )

    def log_message(self, _format: str, *_args: object) -> None:
        return

    def do_POST(self) -> None:  # noqa: N802 - stdlib handler contract
        size = int(self.headers.get("content-length", "0"))
        body = self.rfile.read(size)
        if self.path.endswith("/count_tokens"):
            encoded = json.dumps({"input_tokens": 1}).encode()
            content_type = "application/json"
        else:
            type(self).request_number += 1
            try:
                payload = json.loads(body)
            except json.JSONDecodeError:
                payload = {}
            messages = payload.get("messages") if isinstance(payload, dict) else []
            has_tool_result = any(
                isinstance(item, dict) and item.get("type") == "tool_result"
                for message in messages or []
                if isinstance(message, dict)
                for item in (
                    message.get("content")
                    if isinstance(message.get("content"), list)
                    else []
                )
            )
            encoded = _response(
                request_number=type(self).request_number,
                use_tool=not has_tool_result,
                command=type(self).command,
            )
            content_type = "text/event-stream"
            print(
                f"REQUEST {type(self).request_number} tool_result={has_tool_result}",
                flush=True,
            )
        self.send_response(200)
        self.send_header("content-type", content_type)
        self.send_header("content-length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--command")
    args = parser.parse_args()
    if args.command:
        _Handler.command = args.command
    server = ThreadingHTTPServer(("0.0.0.0", args.port), _Handler)
    print(f"READY {args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
