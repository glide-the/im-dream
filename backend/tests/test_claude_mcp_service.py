"""Claude MCP operation-service lifecycle and concurrency contracts.

[Input] Static test identities plus the fake CLI/PTTY fixture across success and failure modes.
[Output] Verified auth projection, semantic errors, redirect/cancel/timeout, logout/removal, gates, and concurrency.
[Pos] Provider-free domain integration coverage; no real OAuth or business credential writes.
[Sync] 2026-08-19: cover the reviewed minimal operation state machine and security boundaries.
[Sync] 2026-08-19: inject a no-secret projection seam; file synchronization has dedicated tests.
[Sync] 2026-08-19: verify login avoids historical fan-out and restricted user-scope add/remove.
[Sync] 2026-08-20: cover localhost browser callback racing with redirect stdin submission.
[Sync] 2026-08-21: accept remote HTTP and reject removal outside parsed user scope before CLI mutation.
[Sync] 2026-08-25: cover auth identity projection, semantic login errors, authless removal/logout, and exit-zero verification.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from claude_mcp.contracts import (
    ClaudeMcpAuthState,
    ClaudeMcpConfigScope,
    ClaudeMcpError,
    ClaudeMcpErrorCode,
    ClaudeMcpRuntimeIdentity,
    ClaudeMcpState,
)
from claude_mcp.driver import ClaudeMcpCliDriver
from claude_mcp.service import ClaudeMcpService
from claude_mcp.settings import ClaudeMcpSettings


FIXTURE = Path(__file__).resolve().parent / "fixtures" / "claude_mcp_fake_cli.py"


class _IdentityProvider:
    def __init__(self, identity: ClaudeMcpRuntimeIdentity) -> None:
        self.identity = identity

    def resolve(self, actor_id: str) -> ClaudeMcpRuntimeIdentity:
        assert actor_id
        return self.identity


class _CredentialSynchronizer:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail

        self.verification_calls = 0
        self.revocation_calls = 0

    @property
    def requires_file_credential_verification(self) -> bool:
        return True

    async def has_user_mcp_credentials(self, actor_id: str) -> bool:
        assert actor_id
        self.verification_calls += 1
        if self.fail:
            from claude_mcp.credentials import ClaudeMcpCredentialError

            raise ClaudeMcpCredentialError("safe test failure")
        return True

    async def revoke_existing_thread_credentials(self, actor_id: str) -> None:
        assert actor_id
        self.revocation_calls += 1
        if self.fail:
            from claude_mcp.credentials import ClaudeMcpCredentialError

            raise ClaudeMcpCredentialError("safe test failure")


def _settings(*, auth_timeout: int = 3) -> ClaudeMcpSettings:
    return ClaudeMcpSettings(
        auth_timeout_seconds=auth_timeout,
        command_timeout_seconds=3,
        terminate_grace_seconds=1,
        readiness_timeout_seconds=2,
        max_capture_bytes=65536,
        max_server_name_length=512,
        max_redirect_url_length=8192,
    )


def _service(
    tmp_path: Path,
    *,
    auth_timeout: int = 3,
    sync_failure: bool = False,
    **env_overrides: str,
) -> ClaudeMcpService:
    config_dir = tmp_path / "config"
    config_dir.mkdir(exist_ok=True)
    env = dict(os.environ)
    env.update(
        {
            "CLAUDE_MCP_FAKE_STATE_PATH": str(tmp_path / "state"),
            "CLAUDE_MCP_FAKE_REDIRECT_PATH": str(tmp_path / "redirect"),
            "CLAUDE_MCP_FAKE_CONFIGURED_PATH": str(tmp_path / "configured.json"),
            "CLAUDE_MCP_FAKE_REMOVED_PATH": str(tmp_path / "removed"),
            **env_overrides,
        }
    )
    identity = ClaudeMcpRuntimeIdentity(
        command=(sys.executable, str(FIXTURE)),
        config_dir=config_dir.resolve(),
        cwd=tmp_path.resolve(),
        env=env,
        fingerprint="actor-7-agent-identity",
    )
    settings = _settings(auth_timeout=auth_timeout)
    return ClaudeMcpService(
        identity_provider=_IdentityProvider(identity),
        credential_synchronizer=_CredentialSynchronizer(  # type: ignore[arg-type]
            fail=sync_failure
        ),
        driver=ClaudeMcpCliDriver(settings),
        settings=settings,
    )


async def _wait_terminal(operation, *, timeout: float = 4) -> None:
    deadline = asyncio.get_running_loop().time() + timeout
    while operation.state in {
        ClaudeMcpState.AUTH_STARTING,
        ClaudeMcpState.WAITING_FOR_USER,
        ClaudeMcpState.EXCHANGING_CODE,
        ClaudeMcpState.CANCELLING,
    }:
        if asyncio.get_running_loop().time() >= deadline:
            raise AssertionError("operation did not reach a terminal state")
        await asyncio.sleep(0.03)


def test_success_writes_redirect_once_clears_secrets_and_verifies_connected(tmp_path: Path) -> None:
    async def scenario() -> None:
        service = _service(tmp_path)
        operation = await service.start_auth("7", "plugin:comfy-cloud:comfy-cloud")
        assert operation.state is ClaudeMcpState.WAITING_FOR_USER
        assert operation.authorization_url and "state=session-secret" in operation.authorization_url

        redirect = "https://callback.example.test/done?code=private-code&state=private-state"
        submitted = await service.submit_redirect("7", operation.id, redirect)
        assert submitted.state is ClaudeMcpState.EXCHANGING_CODE
        assert submitted.authorization_url is None
        assert redirect not in repr(submitted.to_dict())
        await _wait_terminal(operation)
        assert operation.state is ClaudeMcpState.CONNECTED
        assert operation.authorization_url is None
        assert operation.error_code is None
        assert (tmp_path / "redirect").read_text(encoding="utf-8") == redirect
        server = await service.get_server("7", "plugin:comfy-cloud:comfy-cloud")
        assert server.state is ClaudeMcpState.CONNECTED
        assert server.auth_state is ClaudeMcpAuthState.AUTHENTICATED
        try:
            await service.submit_redirect("7", operation.id, redirect)
        except ClaudeMcpError as exc:
            assert exc.code is ClaudeMcpErrorCode.OPERATION_CONFLICT
        else:  # pragma: no cover
            raise AssertionError("duplicate redirect submission was accepted")
        await service.shutdown()

    asyncio.run(scenario())


def test_browser_callback_completion_race_is_idempotent_success(tmp_path: Path) -> None:
    class _DelayedRedirectDriver(ClaudeMcpCliDriver):
        async def start_login(self, identity, server_name):
            handle = await super().start_login(identity, server_name)
            original_write = handle.write_redirect

            async def delayed_write(redirect_url: str) -> None:
                await asyncio.sleep(0.15)
                await original_write(redirect_url)

            handle.write_redirect = delayed_write  # type: ignore[method-assign]
            return handle

    async def scenario() -> None:
        service = _service(
            tmp_path,
            CLAUDE_MCP_FAKE_BEHAVIOR="browser_callback",
            CLAUDE_MCP_FAKE_CALLBACK_SECONDS="0.05",
        )
        service.driver = _DelayedRedirectDriver(service.settings)
        operation = await service.start_auth("7", "server:browser-callback")
        submitted = await service.submit_redirect(
            "7",
            operation.id,
            "http://localhost:43123/callback?code=private&state=private",
        )
        assert submitted.state is ClaudeMcpState.CONNECTED
        assert submitted.redirect_submitted is True
        assert submitted.authorization_url is None
        assert submitted.error_code is None
        assert submitted.error_message is None
        assert not (tmp_path / "redirect").exists()
        await service.shutdown()

    asyncio.run(scenario())


def test_restricted_http_configuration_and_removal_use_user_owned_names(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        service = _service(tmp_path)
        configured = await service.configure_http_server(
            "7", "user-server", "http://mcp.example.test/api"
        )
        assert configured.name == "user-server"
        assert configured.state is ClaudeMcpState.NEEDS_AUTH
        assert configured.auth_state is ClaudeMcpAuthState.REQUIRED
        assert configured.transport == "http"
        assert configured.config_scope is ClaudeMcpConfigScope.USER
        assert configured.removable is True
        assert (tmp_path / "configured.json").read_text(encoding="utf-8")

        removed = await service.remove_server("7", "user-server")
        assert removed.state is ClaudeMcpState.NOT_CONFIGURED
        assert (tmp_path / "removed").read_text(encoding="utf-8") == "user-server"

        for name, url, expected in (
            ("plugin:owned:server", "https://mcp.example.test", ClaudeMcpErrorCode.SERVER_OWNERSHIP_CONFLICT),
            ("user-server", "ftp://mcp.example.test", ClaudeMcpErrorCode.SERVER_CONFIGURATION_INVALID),
        ):
            try:
                await service.configure_http_server("7", name, url)
            except ClaudeMcpError as exc:
                assert exc.code is expected
            else:  # pragma: no cover
                raise AssertionError("unsafe configuration was accepted")

    asyncio.run(scenario())


def test_project_scope_removal_is_rejected_before_cli_mutation(tmp_path: Path) -> None:
    async def scenario() -> None:
        service = _service(tmp_path, CLAUDE_MCP_FAKE_SCOPE="project")
        try:
            await service.remove_server("7", "project-server")
        except ClaudeMcpError as exc:
            assert exc.code is ClaudeMcpErrorCode.SERVER_OWNERSHIP_CONFLICT
        else:  # pragma: no cover
            raise AssertionError("project-scope server removal was accepted")
        assert not (tmp_path / "removed").exists()
        await service.shutdown()

    asyncio.run(scenario())


def test_user_cancel_terminates_process_and_is_actor_owned(tmp_path: Path) -> None:
    async def scenario() -> None:
        service = _service(
            tmp_path,
            CLAUDE_MCP_FAKE_BEHAVIOR="timeout",
            CLAUDE_MCP_FAKE_SLEEP_SECONDS="10",
        )
        operation = await service.start_auth("7", "server:cancel")
        try:
            await service.cancel_auth("8", operation.id)
        except ClaudeMcpError as exc:
            assert exc.code is ClaudeMcpErrorCode.OPERATION_NOT_FOUND
        else:  # pragma: no cover
            raise AssertionError("cross-actor cancellation was accepted")
        cancelled = await service.cancel_auth("7", operation.id)
        assert cancelled.state is ClaudeMcpState.FAILED
        assert cancelled.error_code == ClaudeMcpErrorCode.AUTH_CANCELLED.value
        await service.shutdown()

    asyncio.run(scenario())


def test_timeout_nonzero_and_malformed_output_are_distinct_failures(tmp_path: Path) -> None:
    async def run_case(
        root: Path,
        behavior: str,
        expected: ClaudeMcpErrorCode,
        *,
        timeout: int = 3,
    ) -> None:
        root.mkdir()
        service = _service(
            root,
            auth_timeout=timeout,
            CLAUDE_MCP_FAKE_BEHAVIOR=behavior,
            CLAUDE_MCP_FAKE_SLEEP_SECONDS="5",
        )
        operation = await service.start_auth("7", f"server:{behavior}")
        await _wait_terminal(operation, timeout=4)
        assert operation.state is ClaudeMcpState.FAILED
        assert operation.error_code == expected.value
        assert operation.authorization_url is None
        await service.shutdown()

    async def scenario() -> None:
        await run_case(
            tmp_path / "timeout",
            "timeout",
            ClaudeMcpErrorCode.AUTH_TIMEOUT,
            timeout=1,
        )
        await run_case(
            tmp_path / "nonzero",
            "nonzero",
            ClaudeMcpErrorCode.PROCESS_EXITED,
        )
        await run_case(
            tmp_path / "malformed",
            "malformed",
            ClaudeMcpErrorCode.MALFORMED_CLI_OUTPUT,
        )

    asyncio.run(scenario())


def test_logout_is_verified_and_version_gate_is_fail_closed(tmp_path: Path) -> None:
    async def scenario() -> None:
        service = _service(tmp_path / "supported")
        (tmp_path / "supported" / "state").write_text("connected", encoding="utf-8")
        result = await service.logout("7", "server:logout")
        assert result.state is ClaudeMcpState.NEEDS_AUTH
        assert result.auth_state is ClaudeMcpAuthState.REQUIRED
        assert (tmp_path / "supported" / "state").read_text(encoding="utf-8") == "needs_auth"

        unsupported = _service(
            tmp_path / "unsupported",
            CLAUDE_MCP_FAKE_VERSION="2.1.186",
        )
        capability = await unsupported.capability("7")
        assert not capability.enabled
        assert capability.reason_code == ClaudeMcpErrorCode.CLI_VERSION_UNSUPPORTED.value
        try:
            await unsupported.list_servers("7")
        except ClaudeMcpError as exc:
            assert exc.code is ClaudeMcpErrorCode.CLI_VERSION_UNSUPPORTED
        else:  # pragma: no cover
            raise AssertionError("unsupported CLI was allowed")

        missing_flag = _service(
            tmp_path / "missing-flag",
            CLAUDE_MCP_FAKE_HIDE_NO_BROWSER="1",
        )
        capability = await missing_flag.capability("7")
        assert not capability.enabled
        assert capability.reason_code == ClaudeMcpErrorCode.CLI_VERSION_UNSUPPORTED.value

    (tmp_path / "supported").mkdir()
    (tmp_path / "unsupported").mkdir()
    (tmp_path / "missing-flag").mkdir()
    asyncio.run(scenario())


def test_duplicate_request_is_idempotent_and_other_server_conflicts(tmp_path: Path) -> None:
    async def scenario() -> None:
        service = _service(
            tmp_path,
            CLAUDE_MCP_FAKE_BEHAVIOR="timeout",
            CLAUDE_MCP_FAKE_SLEEP_SECONDS="10",
        )
        first = await service.start_auth("7", "plugin:one:server")
        repeated = await service.start_auth("7", "plugin:one:server")
        assert repeated.id == first.id
        try:
            await service.start_auth("7", "plugin:two:server")
        except ClaudeMcpError as exc:
            assert exc.code is ClaudeMcpErrorCode.OPERATION_CONFLICT
        else:  # pragma: no cover
            raise AssertionError("concurrent credential mutation was accepted")
        await service.cancel_auth("7", first.id)
        await service.shutdown()

    asyncio.run(scenario())


def test_connected_and_logout_fail_closed_when_thread_projection_fails(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        login_root = tmp_path / "login"
        login_root.mkdir()
        service = _service(login_root, sync_failure=True)
        operation = await service.start_auth("7", "server:sync-failure")
        await service.submit_redirect(
            "7",
            operation.id,
            "https://callback.example.test/done?code=private&state=private",
        )
        await _wait_terminal(operation)
        assert operation.state is ClaudeMcpState.FAILED
        assert operation.error_code == ClaudeMcpErrorCode.CREDENTIAL_SYNC_FAILED.value

        logout_root = tmp_path / "logout"
        logout_root.mkdir()
        logout_service = _service(logout_root, sync_failure=True)
        (logout_root / "state").write_text("connected", encoding="utf-8")
        try:
            await logout_service.logout("7", "server:sync-failure")
        except ClaudeMcpError as exc:
            assert exc.code is ClaudeMcpErrorCode.CREDENTIAL_SYNC_FAILED
        else:  # pragma: no cover
            raise AssertionError("logout projection failure was hidden")

    asyncio.run(scenario())


def test_server_projection_expands_auth_transport_and_legacy_unknown(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        anonymous_root = tmp_path / "anonymous"
        anonymous_root.mkdir()
        anonymous = _service(
            anonymous_root,
            CLAUDE_MCP_FAKE_AUTH_STATE="anonymous",
        )
        (anonymous_root / "state").write_text("connected", encoding="utf-8")
        server = await anonymous.get_server("7", "server:anonymous:colon")
        assert server.state is ClaudeMcpState.CONNECTED
        assert server.auth_state is ClaudeMcpAuthState.ANONYMOUS
        assert server.transport == "http"
        assert server.to_dict()["auth_state"] == "anonymous"

        legacy_root = tmp_path / "legacy"
        legacy_root.mkdir()
        legacy = _service(
            legacy_root,
            CLAUDE_MCP_FAKE_LEGACY_OUTPUT="1",
        )
        (legacy_root / "state").write_text("connected", encoding="utf-8")
        old_server = await legacy.get_server("7", "official-old")
        assert old_server.state is ClaudeMcpState.CONNECTED
        assert old_server.auth_state is ClaudeMcpAuthState.UNKNOWN
        assert old_server.transport == "http"

        failed_root = tmp_path / "failed"
        failed_root.mkdir()
        failed = _service(
            failed_root,
            CLAUDE_MCP_FAKE_FAILURE_CODE="network_unreachable",
        )
        (failed_root / "state").write_text("unavailable", encoding="utf-8")
        failed_server = await failed.get_server("7", "server:failed")
        assert failed_server.state is ClaudeMcpState.FAILED
        assert failed_server.auth_state is ClaudeMcpAuthState.UNKNOWN
        assert failed_server.detail == "Claude MCP server is unreachable."

    asyncio.run(scenario())


def test_explicit_login_consumes_runtime_semantic_failures_without_secret_leakage(
    tmp_path: Path,
) -> None:
    expected = {
        "auth_not_required": ClaudeMcpErrorCode.AUTH_NOT_REQUIRED,
        "auth_not_advertised": ClaudeMcpErrorCode.AUTH_NOT_ADVERTISED,
        "metadata_invalid": ClaudeMcpErrorCode.AUTH_METADATA_INVALID,
        "network_unreachable": ClaudeMcpErrorCode.NETWORK_UNREACHABLE,
        "server_rejected": ClaudeMcpErrorCode.SERVER_REJECTED,
        "semantic_timeout": ClaudeMcpErrorCode.AUTH_TIMEOUT,
        "process_exited": ClaudeMcpErrorCode.PROCESS_EXITED,
    }

    async def scenario() -> None:
        for behavior, error_code in expected.items():
            root = tmp_path / behavior
            root.mkdir()
            overrides = {"CLAUDE_MCP_FAKE_BEHAVIOR": behavior}
            if behavior == "auth_not_required":
                overrides["CLAUDE_MCP_FAKE_AUTH_STATE"] = "anonymous"
                overrides["CLAUDE_MCP_FAKE_DEFAULT_STATE"] = "connected"
            elif behavior == "auth_not_advertised":
                overrides["CLAUDE_MCP_FAKE_DEFAULT_STATE"] = "configured"
            elif behavior == "network_unreachable":
                overrides["CLAUDE_MCP_FAKE_DEFAULT_STATE"] = "unavailable"
            service = _service(root, **overrides)
            operation = await service.start_auth("7", f"server:{behavior}")
            await _wait_terminal(operation)
            assert operation.state is ClaudeMcpState.FAILED
            assert operation.error_code == error_code.value
            serialized = repr(operation.to_dict())
            assert "fixture-secret" not in serialized
            assert "refresh_token" not in serialized
            await service.shutdown()

    asyncio.run(scenario())


def test_exit_zero_without_authorization_url_accepts_only_authenticated_truth(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        authenticated_root = tmp_path / "authenticated"
        authenticated_root.mkdir()
        service = _service(
            authenticated_root,
            CLAUDE_MCP_FAKE_BEHAVIOR="exit0_authenticated",
        )
        operation = await service.start_auth("7", "server:already-authenticated")
        await _wait_terminal(operation)
        assert operation.state is ClaudeMcpState.CONNECTED
        assert operation.error_code is None
        await service.shutdown()

        anonymous_root = tmp_path / "anonymous"
        anonymous_root.mkdir()
        anonymous = _service(
            anonymous_root,
            CLAUDE_MCP_FAKE_BEHAVIOR="exit0_authenticated",
            CLAUDE_MCP_FAKE_AUTH_STATE="anonymous",
        )
        anonymous_operation = await anonymous.start_auth("7", "server:anonymous")
        await _wait_terminal(anonymous_operation)
        assert anonymous_operation.state is ClaudeMcpState.FAILED
        assert (
            anonymous_operation.error_code
            == ClaudeMcpErrorCode.MALFORMED_CLI_OUTPUT.value
        )
        await anonymous.shutdown()

    asyncio.run(scenario())


def test_callback_verification_rejects_explicit_anonymous_truth_but_keeps_legacy_rollback(
    tmp_path: Path,
) -> None:
    async def complete(root: Path, **overrides: str):
        root.mkdir()
        service = _service(root, **overrides)
        operation = await service.start_auth("7", "server:callback-verification")
        assert operation.state is ClaudeMcpState.WAITING_FOR_USER
        await service.submit_redirect(
            "7",
            operation.id,
            "https://callback.example.test/done?code=private&state=private",
        )
        await _wait_terminal(operation)
        await service.shutdown()
        return operation

    async def scenario() -> None:
        anonymous = await complete(
            tmp_path / "anonymous",
            CLAUDE_MCP_FAKE_AUTH_STATE="anonymous",
        )
        assert anonymous.state is ClaudeMcpState.FAILED
        assert anonymous.error_code == ClaudeMcpErrorCode.CLI_FAILED.value

        legacy = await complete(
            tmp_path / "legacy",
            CLAUDE_MCP_FAKE_LEGACY_OUTPUT="1",
        )
        assert legacy.state is ClaudeMcpState.CONNECTED
        assert legacy.error_code is None

    asyncio.run(scenario())


def test_logout_and_remove_trust_authless_or_protected_runtime_truth(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        protected_root = tmp_path / "protected"
        protected_root.mkdir()
        protected = _service(protected_root)
        (protected_root / "state").write_text("connected", encoding="utf-8")
        logged_out = await protected.logout("7", "server:protected")
        assert logged_out.state is ClaudeMcpState.NEEDS_AUTH
        assert logged_out.auth_state is ClaudeMcpAuthState.REQUIRED

        anonymous_root = tmp_path / "anonymous"
        anonymous_root.mkdir()
        anonymous = _service(
            anonymous_root,
            CLAUDE_MCP_FAKE_AUTH_STATE="anonymous",
            CLAUDE_MCP_FAKE_LOGOUT_FAILURE_CODE="auth_not_required",
        )
        (anonymous_root / "state").write_text("connected", encoding="utf-8")
        still_connected = await anonymous.logout("7", "server:anonymous")
        assert still_connected.state is ClaudeMcpState.CONNECTED
        assert still_connected.auth_state is ClaudeMcpAuthState.ANONYMOUS

        removable_root = tmp_path / "removable"
        removable_root.mkdir()
        removable = _service(
            removable_root,
            CLAUDE_MCP_FAKE_AUTH_STATE="anonymous",
            CLAUDE_MCP_FAKE_LOGOUT_FAILURE_CODE="auth_not_required",
        )
        (removable_root / "state").write_text("connected", encoding="utf-8")
        removed = await removable.remove_server("7", "server:anonymous:colon")
        assert removed.state is ClaudeMcpState.NOT_CONFIGURED
        assert (removable_root / "removed").read_text(encoding="utf-8") == "server:anonymous:colon"

        authenticated_root = tmp_path / "authenticated"
        authenticated_root.mkdir()
        authenticated = _service(
            authenticated_root,
            CLAUDE_MCP_FAKE_LOGOUT_FAILURE_CODE="server_rejected",
        )
        (authenticated_root / "state").write_text("connected", encoding="utf-8")
        try:
            await authenticated.remove_server("7", "server:authenticated")
        except ClaudeMcpError as exc:
            assert exc.code is ClaudeMcpErrorCode.SERVER_REJECTED
        else:  # pragma: no cover
            raise AssertionError("authenticated removal ignored logout failure")
        assert not (authenticated_root / "removed").exists()

    asyncio.run(scenario())


def test_explicit_login_rejects_disabled_state_but_allows_user_discovery(
    tmp_path: Path,
) -> None:
    async def scenario() -> None:
        disabled = _service(
            tmp_path,
            CLAUDE_MCP_FAKE_DEFAULT_STATE="disabled",
        )
        try:
            await disabled.start_auth("7", "server:disabled")
        except ClaudeMcpError as exc:
            assert exc.code is ClaudeMcpErrorCode.OPERATION_CONFLICT
        else:  # pragma: no cover
            raise AssertionError("disabled server accepted login")

    asyncio.run(scenario())
