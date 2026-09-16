from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.admin_gateway.config import (
    AdminGatewayConfig,
    AdminGatewayConfigurationError,
)
from services.admin_gateway.sdk import apply_gateway_sdk_env_to_options
from libs.claude_agent_kit.server.sdk_env import apply_project_sdk_runtime_options


DELEGATION_TOKEN = "idg_" + "d" * 43


@dataclass
class Options:
    env: dict[str, str] = field(default_factory=dict)
    settings: str | None = None


def configured_environment() -> dict[str, str]:
    return {
        "INK_GATEWAY_CLAUDE_AGENT_ENABLED": "true",
        "INK_GATEWAY_BASE_URL": "https://admin.example.test",
        "INK_GATEWAY_SERVICE_KEY": "gw_" + "k" * 43,
    }


def test_disabled_gateway_preserves_existing_provider_environment():
    options = Options(env={"ANTHROPIC_AUTH_TOKEN": "legacy"})
    apply_gateway_sdk_env_to_options(options, "7", environment={})
    assert options.env == {"ANTHROPIC_AUTH_TOKEN": "legacy"}


def test_enabled_gateway_uses_admin_delegation_without_projecting_service_key():
    values = configured_environment()
    options = Options(
        env={
            "ANTHROPIC_AUTH_TOKEN": "user-override",
            "ANTHROPIC_BASE_URL": "https://bypass.example",
            "ANTHROPIC_API_KEY": "legacy-secret",
        }
    )

    apply_gateway_sdk_env_to_options(
        options,
        DELEGATION_TOKEN,
        gateway_idempotency_key="dream-turn-" + "a" * 64,
        environment=values,
    )

    assert options.env["ANTHROPIC_BASE_URL"] == "https://admin.example.test"
    assert options.env["ANTHROPIC_CUSTOM_HEADERS"] == (
        "x-ink-turn-idempotency-key: dream-turn-" + "a" * 64
    )
    assert options.env["ANTHROPIC_API_KEY"] == ""
    assert options.env["ANTHROPIC_AUTH_TOKEN"] == DELEGATION_TOKEN
    assert options.env["CLAUDE_CODE_OAUTH_TOKEN"] == ""
    assert options.env.get("INK_GATEWAY_SERVICE_KEY") in {None, ""}
    assert options.settings is None


def test_gateway_credentials_survive_the_sdk_runtime_defaults_reapply(tmp_path):
    """The SDK's second env merge must not restore a direct Provider token."""

    values = configured_environment()
    options = Options()
    apply_gateway_sdk_env_to_options(
        options,
        DELEGATION_TOKEN,
        gateway_idempotency_key="dream-turn-" + "c" * 64,
        environment=values,
    )
    env_file = tmp_path / ".env"
    env_file.write_text(
        "\n".join(
            (
                "ANTHROPIC_AUTH_TOKEN=direct-provider-token-must-not-return",
                "ANTHROPIC_BASE_URL=https://provider-bypass.example.test",
            )
        ),
        encoding="utf-8",
    )

    apply_project_sdk_runtime_options(options, env_file=env_file)

    assert options.env["ANTHROPIC_API_KEY"] == ""
    assert options.env["ANTHROPIC_AUTH_TOKEN"] == DELEGATION_TOKEN
    assert options.env["CLAUDE_CODE_OAUTH_TOKEN"] == ""
    assert options.env["ANTHROPIC_BASE_URL"] == values["INK_GATEWAY_BASE_URL"]
    assert options.env["ANTHROPIC_CUSTOM_HEADERS"].startswith(
        "x-ink-turn-idempotency-key:"
    )


def test_gateway_tombstones_parent_process_credentials_on_sdk_reapply(
    tmp_path,
    monkeypatch,
):
    values = configured_environment()
    options = Options()
    apply_gateway_sdk_env_to_options(
        options,
        DELEGATION_TOKEN,
        environment=values,
    )
    for name in (
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_AUTH_TOKEN",
        "CLAUDE_CODE_OAUTH_TOKEN",
    ):
        monkeypatch.setenv(name, f"ambient-{name.lower()}-must-not-flow")

    apply_project_sdk_runtime_options(options, env_file=tmp_path / "missing.env")

    assert options.env["ANTHROPIC_API_KEY"] == ""
    assert options.env["ANTHROPIC_AUTH_TOKEN"] == DELEGATION_TOKEN
    assert options.env["CLAUDE_CODE_OAUTH_TOKEN"] == ""
    assert options.env.get("INK_GATEWAY_SERVICE_KEY") in {None, ""}


def test_disabled_gateway_still_loads_direct_provider_token(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "ANTHROPIC_AUTH_TOKEN=direct-provider-token\n",
        encoding="utf-8",
    )
    options = Options()

    apply_project_sdk_runtime_options(options, env_file=env_file)

    assert options.env["ANTHROPIC_AUTH_TOKEN"] == "direct-provider-token"


def test_explicit_primary_gateway_disable_wins_over_legacy_enable(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_AUTH_TOKEN", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "ANTHROPIC_AUTH_TOKEN=direct-provider-token\n",
        encoding="utf-8",
    )
    options = Options(
        env={
            "INK_GATEWAY_ENABLED": "0",
            "INK_GATEWAY_CLAUDE_AGENT_ENABLED": "1",
        }
    )

    apply_project_sdk_runtime_options(options, env_file=env_file)

    assert options.env["ANTHROPIC_AUTH_TOKEN"] == "direct-provider-token"


def test_real_claude_cli_uses_three_native_retries_for_429(tmp_path):
    """The server-owned default reaches Claude Code's HTTP retry transport."""

    claude = shutil.which("claude")
    if claude is None:
        pytest.skip("real Claude CLI is not installed")

    attempts: list[int] = []
    paths: list[str] = []
    retry_counts: list[str | None] = []
    request_models: list[str | None] = []
    request_message_counts: list[int] = []
    request_bodies: list[bytes] = []
    response_statuses: list[int] = []

    class RetryGatewayHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, _format, *_args):
            return

        def do_POST(self):  # noqa: N802 - stdlib handler contract
            size = int(self.headers.get("content-length", "0"))
            body = self.rfile.read(size)
            attempts.append(len(attempts) + 1)
            paths.append(self.path)
            retry_counts.append(self.headers.get("x-stainless-retry-count"))
            request_payload = json.loads(body)
            request_bodies.append(body)
            request_models.append(request_payload.get("model"))
            request_message_counts.append(len(request_payload.get("messages", [])))
            if len(attempts) <= 3:
                status = 429
                payload = {
                    "type": "error",
                    "error": {
                        "type": "rate_limit_error",
                        "code": "REQUEST_RATE_LIMIT_EXCEEDED",
                        "message": "transient test throttle",
                    },
                }
            else:
                status = 200
                events = (
                    (
                        "message_start",
                        {
                            "type": "message_start",
                            "message": {
                                "id": "msg_claude_code_retry_test",
                                "type": "message",
                                "role": "assistant",
                                "content": [],
                                "model": "claude-code-retry-test",
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
                            "delta": {"type": "text_delta", "text": "ok"},
                        },
                    ),
                    (
                        "content_block_stop",
                        {"type": "content_block_stop", "index": 0},
                    ),
                    (
                        "message_delta",
                        {
                            "type": "message_delta",
                            "delta": {
                                "stop_reason": "end_turn",
                                "stop_sequence": None,
                            },
                            "usage": {"output_tokens": 1},
                        },
                    ),
                    ("message_stop", {"type": "message_stop"}),
                )
                encoded = "".join(
                    f"event: {event}\ndata: {json.dumps(data)}\n\n"
                    for event, data in events
                ).encode("utf-8")
            if status == 429:
                encoded = json.dumps(payload).encode("utf-8")
            response_statuses.append(status)
            self.send_response(status)
            self.send_header(
                "content-type",
                "application/json" if status == 429 else "text/event-stream",
            )
            self.send_header("content-length", str(len(encoded)))
            if status == 429:
                self.send_header("retry-after", "0")
            self.end_headers()
            self.wfile.write(encoded)

    server = ThreadingHTTPServer(("127.0.0.1", 0), RetryGatewayHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    try:
        options = Options(
            env={
                "ANTHROPIC_AUTH_TOKEN": "test-token",
                "ANTHROPIC_BASE_URL": f"http://127.0.0.1:{server.server_port}",
            }
        )
        apply_project_sdk_runtime_options(
            options,
            env_file=tmp_path / "missing.env",
        )
        environment = {
            **os.environ,
            **options.env,
            "ANTHROPIC_API_KEY": "",
            "CLAUDE_CODE_OAUTH_TOKEN": "",
            "CLAUDE_CONFIG_DIR": str(tmp_path / "claude-home"),
            "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
        }
        completed = subprocess.run(
            [
                claude,
                "--print",
                "reply with ok",
                "--output-format",
                "json",
                "--model",
                "claude-code-retry-test",
                "--tools",
                "",
                "--max-turns",
                "1",
            ],
            cwd=tmp_path,
            env=environment,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    finally:
        server.shutdown()
        server.server_close()
        server_thread.join(timeout=5)

    assert completed.returncode == 0, completed.stderr[-500:]
    assert response_statuses[:4] == [429, 429, 429, 200], (
        paths,
        retry_counts,
        request_models,
        request_message_counts,
    )
    assert len(set(request_bodies[:4])) == 1


def test_enabled_gateway_fails_closed_for_missing_subject_or_configuration():
    with pytest.raises(AdminGatewayConfigurationError):
        apply_gateway_sdk_env_to_options(
            Options(),
            None,
            environment=configured_environment(),
        )
    incomplete = configured_environment()
    incomplete.pop("INK_GATEWAY_SERVICE_KEY")
    with pytest.raises(AdminGatewayConfigurationError):
        apply_gateway_sdk_env_to_options(
            Options(), DELEGATION_TOKEN, environment=incomplete
        )


def test_gateway_config_repr_and_errors_do_not_expose_secret_values():
    values = configured_environment()
    config = AdminGatewayConfig.from_environment(values)
    assert values["INK_GATEWAY_SERVICE_KEY"] not in repr(config)
    assert config.enabled


def test_gateway_rejects_header_injection_and_non_https_remote_urls():
    values = configured_environment()
    values["INK_GATEWAY_SERVICE_KEY"] += "\nAuthorization: bad"
    with pytest.raises(AdminGatewayConfigurationError):
        AdminGatewayConfig.from_environment(values)


def test_gateway_rejects_an_unsafe_turn_idempotency_header():
    with pytest.raises(AdminGatewayConfigurationError):
        apply_gateway_sdk_env_to_options(
            Options(),
            DELEGATION_TOKEN,
            gateway_idempotency_key="safe\nx-api-key: injected",
            environment=configured_environment(),
        )
    values = configured_environment()
    values["INK_GATEWAY_BASE_URL"] = "http://admin.example.test"
    with pytest.raises(AdminGatewayConfigurationError):
        AdminGatewayConfig.from_environment(values)
