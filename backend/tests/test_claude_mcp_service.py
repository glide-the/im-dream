"""Claude MCP operation-service lifecycle and concurrency contracts.

[Input] Static test identities plus the fake CLI/PTTY fixture across success and failure modes.
[Output] Verified configuration, redirect exchange, cancel, timeout, errors, logout/removal, version gates, idempotency, and conflicts.
[Pos] Provider-free domain integration coverage; no real OAuth or business credential writes.
[Sync] 2026-08-19: cover the reviewed minimal operation state machine and security boundaries.
[Sync] 2026-08-19: inject a no-secret projection seam; file synchronization has dedicated tests.
[Sync] 2026-08-19: verify login avoids historical fan-out and restricted user-scope add/remove.
[Sync] 2026-08-20: cover localhost browser callback racing with redirect stdin submission.
[Sync] 2026-08-21: accept remote HTTP and reject removal outside parsed user scope before CLI mutation.
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
            ClaudeMcpErrorCode.CLI_FAILED,
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
        assert result.state is ClaudeMcpState.LOGGED_OUT
        assert (tmp_path / "supported" / "state").read_text(encoding="utf-8") == "logged_out"

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
