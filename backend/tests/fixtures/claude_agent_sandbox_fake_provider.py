#!/usr/bin/env python3
"""Deterministic Anthropic SSE provider for a real Docker Claude sandbox probe.

[Input] HTTP POST requests from a test-owned Claude Code CLI, caller-supplied listen port, and optional fixed Bash/final-text fixtures.
[Output] One configurable Bash tool_use followed by one end_turn response; no external model/OAuth traffic.
[Pos] Manual/CI container compatibility fixture, outside production runtime.
[Sync] 2026-08-19: add provider-free CLI 2.1.235 Bash and credential deny-read validation.
[Sync] 2026-09-04: expose a reusable handler factory for process-isolated notion-cli Runtime contracts while preserving CLI defaults.
"""

from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

_DEFAULT_COMMAND = (
    "printf 'workspace-write-ok\\n' > sandbox-write.txt; "
    "if cat .claude-home/.credentials.json >/dev/null 2>&1; "
    "then printf 'credential-readable\\n'; exit 91; "
    "else printf 'credential-denied\\n'; fi"
)
_DEFAULT_FINAL_TEXT = "sandbox probe complete"


def _frame(event: str, payload: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload)}\n\n"


def _response(
    *,
    request_number: int,
    use_tool: bool,
    command: str = _DEFAULT_COMMAND,
    final_text: str = _DEFAULT_FINAL_TEXT,
) -> bytes:
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
                    "delta": {"type": "text_delta", "text": final_text},
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


def build_handler(
    *,
    command: str = _DEFAULT_COMMAND,
    final_text: str = _DEFAULT_FINAL_TEXT,
    requests_seen: list[dict[str, Any]] | None = None,
    announce_requests: bool = True,
) -> type[BaseHTTPRequestHandler]:
    """Build an isolated deterministic Provider handler for one test server."""

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"
        request_number = 0

        def log_message(self, _format: str, *_args: object) -> None:
            return

        def do_POST(self) -> None:
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
                if requests_seen is not None and isinstance(payload, dict):
                    requests_seen.append(payload)
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
                    command=command,
                    final_text=final_text,
                )
                content_type = "text/event-stream"
                if announce_requests:
                    print(
                        f"REQUEST {type(self).request_number} "
                        f"tool_result={has_tool_result}",
                        flush=True,
                    )
            self.send_response(200)
            self.send_header("content-type", content_type)
            self.send_header("content-length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    return Handler


_Handler = build_handler()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
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
