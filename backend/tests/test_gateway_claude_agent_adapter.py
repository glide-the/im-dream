from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import jwt
import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.admin_gateway.config import (
    AdminGatewayConfig,
    AdminGatewayConfigurationError,
)
from services.admin_gateway.sdk import apply_gateway_sdk_env_to_options
from services.admin_gateway.token import issue_gateway_subject_token
from libs.claude_agent_kit.server.sdk_env import apply_project_sdk_runtime_options


@dataclass
class Options:
    env: dict[str, str] = field(default_factory=dict)
    settings: str | None = None


def configured_environment() -> dict[str, str]:
    return {
        "INK_GATEWAY_CLAUDE_AGENT_ENABLED": "true",
        "INK_GATEWAY_BASE_URL": "https://admin.example.test",
        "INK_GATEWAY_SERVICE_KEY": "gw_" + "k" * 43,
        "INK_GATEWAY_SUBJECT_JWT_ISSUER": "https://dream.example.test",
        "INK_GATEWAY_SUBJECT_JWT_AUDIENCE": "ink-memory-gateway",
        "INK_GATEWAY_SERVICE_CLIENT_ID": "dream-bff",
        "INK_GATEWAY_SUBJECT_TOKEN_LIFETIME_SECONDS": "240",
    }


def test_disabled_gateway_preserves_existing_provider_environment():
    options = Options(env={"ANTHROPIC_AUTH_TOKEN": "legacy"})
    apply_gateway_sdk_env_to_options(options, "7", environment={})
    assert options.env == {"ANTHROPIC_AUTH_TOKEN": "legacy"}


def test_enabled_gateway_uses_refreshable_helper_and_binds_canonical_subject():
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
        "205",
        gateway_idempotency_key="dream-turn-" + "a" * 64,
        environment=values,
    )

    assert options.env["ANTHROPIC_BASE_URL"] == "https://admin.example.test"
    assert options.env["ANTHROPIC_CUSTOM_HEADERS"] == (
        "x-api-key: " + values["INK_GATEWAY_SERVICE_KEY"]
        + "\nx-ink-turn-idempotency-key: dream-turn-" + "a" * 64
    )
    assert options.env["ANTHROPIC_API_KEY"] == ""
    assert options.env["ANTHROPIC_AUTH_TOKEN"] == ""
    assert options.env["CLAUDE_CODE_OAUTH_TOKEN"] == ""
    assert options.env["INK_GATEWAY_CANONICAL_SUBJECT"] == "205"
    assert options.env["CLAUDE_CODE_API_KEY_HELPER_TTL_MS"] == "120000"
    settings = json.loads(options.settings or "")
    assert "services.admin_gateway.subject_token_helper" in settings["apiKeyHelper"]


def test_gateway_credentials_survive_the_sdk_runtime_defaults_reapply(tmp_path):
    """The SDK's second env merge must not restore a direct Provider token."""

    values = configured_environment()
    options = Options()
    apply_gateway_sdk_env_to_options(
        options,
        "205",
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
    assert options.env["ANTHROPIC_AUTH_TOKEN"] == ""
    assert options.env["CLAUDE_CODE_OAUTH_TOKEN"] == ""
    assert options.env["ANTHROPIC_BASE_URL"] == values["INK_GATEWAY_BASE_URL"]
    assert options.env["ANTHROPIC_CUSTOM_HEADERS"].startswith(
        "x-api-key: " + values["INK_GATEWAY_SERVICE_KEY"]
    )


def test_gateway_tombstones_parent_process_credentials_on_sdk_reapply(
    tmp_path,
    monkeypatch,
):
    values = configured_environment()
    options = Options()
    apply_gateway_sdk_env_to_options(
        options,
        "205",
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
    assert options.env["ANTHROPIC_AUTH_TOKEN"] == ""
    assert options.env["CLAUDE_CODE_OAUTH_TOKEN"] == ""
    assert json.loads(options.settings or "")["apiKeyHelper"]


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


def test_subject_helper_issues_fresh_short_lived_tokens(monkeypatch, capsys):
    from services.admin_gateway.subject_token_helper import main

    values = configured_environment()
    values["INK_GATEWAY_CANONICAL_SUBJECT"] = "205"
    for name, value in values.items():
        monkeypatch.setenv(name, value)

    assert main() == 0
    first = capsys.readouterr().out.strip()
    assert main() == 0
    second = capsys.readouterr().out.strip()
    assert first != second
    for token in (first, second):
        payload = jwt.decode(
            token,
            values["INK_GATEWAY_SERVICE_KEY"],
            algorithms=["HS256"],
            audience=values["INK_GATEWAY_SUBJECT_JWT_AUDIENCE"],
            issuer=values["INK_GATEWAY_SUBJECT_JWT_ISSUER"],
        )
        assert payload["sub"] == "205"
        assert payload["scope"] == "messages:create"
        assert payload["exp"] - payload["iat"] == 240


def test_real_claude_cli_refreshes_helper_token_after_gateway_401():
    """The helper must win over inherited credentials and refresh after 401."""

    claude = shutil.which("claude")
    if claude is None:
        pytest.skip("real Claude CLI is not installed")

    tokens: list[str] = []
    service_keys: list[str | None] = []

    class GatewayHandler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, _format, *_args):
            return

        def do_POST(self):  # noqa: N802 - stdlib handler contract
            size = int(self.headers.get("content-length", "0"))
            self.rfile.read(size)
            authorization = self.headers.get("authorization", "")
            tokens.append(
                authorization.removeprefix("Bearer ")
                if authorization.startswith("Bearer ")
                else ""
            )
            service_keys.append(self.headers.get("x-api-key"))
            if len(tokens) == 1:
                status = 401
                payload = {
                    "type": "error",
                    "error": {
                        "type": "authentication_error",
                        "message": "subject refresh required",
                    },
                }
            else:
                status = 200
                payload = {
                    "id": "msg_gateway_refresh_test",
                    "type": "message",
                    "role": "assistant",
                    "content": [{"type": "text", "text": "ok"}],
                    "model": "gateway-refresh-test",
                    "stop_reason": "end_turn",
                    "stop_sequence": None,
                    "usage": {"input_tokens": 1, "output_tokens": 1},
                }
            encoded = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("content-type", "application/json")
            self.send_header("content-length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    server = ThreadingHTTPServer(("127.0.0.1", 0), GatewayHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    try:
        values = configured_environment()
        values["INK_GATEWAY_BASE_URL"] = f"http://127.0.0.1:{server.server_port}"
        options = Options()
        apply_gateway_sdk_env_to_options(
            options,
            "205",
            gateway_idempotency_key="dream-turn-" + "b" * 64,
            environment=values,
        )
        environment = dict(os.environ)
        # Match the SDK transport, which inherits the parent process before
        # overlaying options.env. These inert sentinels must not replace the
        # canonical-subject helper configured by the server.
        environment.update(
            {
                "ANTHROPIC_API_KEY": "ambient-api-key-must-not-flow",
                "ANTHROPIC_AUTH_TOKEN": "ambient-auth-token-must-not-flow",
                "CLAUDE_CODE_OAUTH_TOKEN": "ambient-oauth-must-not-flow",
                "ANTHROPIC_FEDERATION_RULE_ID": "ambient-rule-must-not-flow",
                "ANTHROPIC_ORGANIZATION_ID": "ambient-org-must-not-flow",
            }
        )
        environment.update(options.env)
        environment["CLAUDE_CODE_MAX_RETRIES"] = "1"
        with tempfile.TemporaryDirectory() as config_home:
            environment["CLAUDE_CONFIG_DIR"] = config_home
            completed = subprocess.run(
                [
                    claude,
                    "--print",
                    "reply with ok",
                    "--output-format",
                    "json",
                    "--model",
                    "gateway-refresh-test",
                    "--tools",
                    "",
                    "--max-turns",
                    "1",
                    "--settings",
                    options.settings or "",
                ],
                cwd=config_home,
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
    assert len(tokens) >= 2
    assert all(tokens)
    assert tokens[0] != tokens[-1]
    assert service_keys == [values["INK_GATEWAY_SERVICE_KEY"]] * len(tokens)
    token_ids: set[str] = set()
    for token in tokens:
        payload = jwt.decode(
            token,
            values["INK_GATEWAY_SERVICE_KEY"],
            algorithms=["HS256"],
            audience=values["INK_GATEWAY_SUBJECT_JWT_AUDIENCE"],
            issuer=values["INK_GATEWAY_SUBJECT_JWT_ISSUER"],
        )
        assert payload["sub"] == "205"
        token_ids.add(str(payload["jti"]))
    assert len(token_ids) >= 2


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
        apply_gateway_sdk_env_to_options(Options(), "7", environment=incomplete)


def test_gateway_config_repr_and_errors_do_not_expose_secret_values():
    values = configured_environment()
    config = AdminGatewayConfig.from_environment(values)
    assert values["INK_GATEWAY_SERVICE_KEY"] not in repr(config)
    with pytest.raises(AdminGatewayConfigurationError) as error:
        issue_gateway_subject_token(config, "not-a-user")
    assert values["INK_GATEWAY_SERVICE_KEY"] not in str(error.value)


def test_gateway_rejects_header_injection_and_non_https_remote_urls():
    values = configured_environment()
    values["INK_GATEWAY_SERVICE_KEY"] += "\nAuthorization: bad"
    with pytest.raises(AdminGatewayConfigurationError):
        AdminGatewayConfig.from_environment(values)


def test_gateway_rejects_an_unsafe_turn_idempotency_header():
    with pytest.raises(AdminGatewayConfigurationError):
        apply_gateway_sdk_env_to_options(
            Options(),
            "7",
            gateway_idempotency_key="safe\nx-api-key: injected",
            environment=configured_environment(),
        )
    values = configured_environment()
    values["INK_GATEWAY_BASE_URL"] = "http://admin.example.test"
    with pytest.raises(AdminGatewayConfigurationError):
        AdminGatewayConfig.from_environment(values)
