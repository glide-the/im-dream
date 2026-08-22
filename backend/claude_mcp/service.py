"""User-scoped Claude MCP discovery and OAuth operation orchestration.

[Input] Actor-owned API actions, exact runtime identities, and public CLI driver results.
[Output] Recoverable in-process operations, restricted user HTTP configuration, verified states, cancellation, and logout.
[Pos] Domain orchestration layer; owns concurrency and never persists or logs OAuth material.
[Sync] 2026-08-19: implement the reviewed schema-free v1 lifecycle with fail-closed gates.
[Sync] 2026-08-19: use production user identities and project verified login/logout state into existing Agent threads.
[Sync] 2026-08-19: enable macOS platform identities, remove login-time historical fan-out, and add restricted add/remove.
[Sync] 2026-08-20: accept browser-callback completion racing with redirect stdin submission as idempotent success.
[Sync] 2026-08-20: verify Darwin login through formal `mcp get` without reading Keychain payloads.
[Sync] 2026-08-20: expose prompt-free public-SDK tool inventory under the same user identity as Chat.
[Sync] 2026-08-21: accept absolute HTTP(S) servers and authorize removal from parsed user scope only.
"""

from __future__ import annotations

import asyncio
from collections.abc import Mapping
from datetime import datetime, timezone
import uuid

from .contracts import (
    ClaudeMcpCapability,
    ClaudeMcpConfigScope,
    ClaudeMcpError,
    ClaudeMcpErrorCode,
    ClaudeMcpOperation,
    ClaudeMcpRuntimeIdentity,
    ClaudeMcpServer,
    ClaudeMcpServerInventory,
    ClaudeMcpState,
)
from .driver import ClaudeMcpCliDriver, ClaudeMcpLoginHandle
from .credentials import (
    ClaudeMcpCredentialError,
    ClaudeMcpCredentialSynchronizer,
    get_default_credential_synchronizer,
)
from .identity import (
    ClaudeMcpIdentityProvider,
    PlatformClaudeMcpIdentityProvider,
)
from .inventory import ClaudeMcpInventoryClient
from .parser import (
    parse_authorization_url,
    parse_server_names,
    parse_server_scope,
    parse_server_state,
    parse_version,
    validate_redirect_url,
    validate_server_url,
    validate_server_name,
    version_at_least,
)
from .settings import ClaudeMcpSettings


_ACTIVE_STATES = {
    ClaudeMcpState.AUTH_STARTING,
    ClaudeMcpState.WAITING_FOR_USER,
    ClaudeMcpState.EXCHANGING_CODE,
    ClaudeMcpState.CANCELLING,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ClaudeMcpService:
    """Coordinate official CLI operations while keeping all secrets transient."""

    def __init__(
        self,
        *,
        identity_provider: ClaudeMcpIdentityProvider | None = None,
        credential_synchronizer: ClaudeMcpCredentialSynchronizer | None = None,
        driver: ClaudeMcpCliDriver | None = None,
        inventory_client: ClaudeMcpInventoryClient | None = None,
        settings: ClaudeMcpSettings | None = None,
    ) -> None:
        using_default_settings = settings is None
        self.settings = settings or ClaudeMcpSettings.from_env()
        self.driver = driver or ClaudeMcpCliDriver(self.settings)
        self.inventory_client = inventory_client or ClaudeMcpInventoryClient(
            self.settings
        )
        self.credential_synchronizer = (
            credential_synchronizer
            or (
                get_default_credential_synchronizer()
                if using_default_settings
                else ClaudeMcpCredentialSynchronizer(self.settings)
            )
        )
        self.identity_provider = identity_provider or PlatformClaudeMcpIdentityProvider(
            self.settings,
            synchronizer=self.credential_synchronizer,
        )
        self._operations: dict[str, ClaudeMcpOperation] = {}
        self._active_by_server: dict[tuple[str, str], str] = {}
        self._credential_locks: dict[str, asyncio.Lock] = {}
        self._inventory_locks: dict[tuple[str, str], asyncio.Lock] = {}
        self._registry_lock = asyncio.Lock()

    def _identity(self, actor_id: str) -> ClaudeMcpRuntimeIdentity:
        return self.identity_provider.resolve(actor_id)

    async def _checked_identity(
        self, actor_id: str
    ) -> tuple[ClaudeMcpRuntimeIdentity, str]:
        try:
            identity = self._identity(actor_id)
        except ClaudeMcpError:
            raise
        except Exception as exc:
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.IDENTITY_UNAVAILABLE,
                "Claude MCP runtime identity could not be resolved.",
            ) from exc
        try:
            result = await self.driver.version(identity)
        except (OSError, ValueError) as exc:
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.CLI_UNAVAILABLE,
                "Claude Code CLI version could not be verified.",
            ) from exc
        if not result.ok:
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.CLI_UNAVAILABLE,
                "Claude Code CLI version could not be verified.",
            )
        parsed = parse_version(result.output)
        if parsed is None or not version_at_least(
            result.output, self.settings.headless_minimum_cli_version
        ):
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.CLI_VERSION_UNSUPPORTED,
                "Claude Code CLI does not satisfy the headless MCP OAuth minimum version.",
            )
        try:
            login_help, logout_help, add_help, remove_help = await asyncio.gather(
                self.driver.login_help(identity),
                self.driver.logout_help(identity),
                self.driver.add_help(identity),
                self.driver.remove_help(identity),
            )
        except (OSError, ValueError) as exc:
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.CLI_UNAVAILABLE,
                "Claude Code CLI command capabilities could not be verified.",
            ) from exc
        if (
            not login_help.ok
            or "--no-browser" not in login_help.output
            or not logout_help.ok
            or not add_help.ok
            or "--scope" not in add_help.output
            or "--transport" not in add_help.output
            or not remove_help.ok
            or "--scope" not in remove_help.output
        ):
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.CLI_VERSION_UNSUPPORTED,
                "Claude Code CLI does not expose the required public MCP OAuth argv commands.",
            )
        version = ".".join(str(part) for part in parsed)
        return identity, version

    async def capability(self, actor_id: str) -> ClaudeMcpCapability:
        try:
            identity, version = await self._checked_identity(actor_id)
        except ClaudeMcpError as exc:
            return ClaudeMcpCapability(
                enabled=False,
                reason_code=exc.code.value,
                cli_version=None,
                minimum_cli_version=self.settings.minimum_cli_version,
                headless_minimum_cli_version=self.settings.headless_minimum_cli_version,
            )
        return ClaudeMcpCapability(
            enabled=True,
            reason_code=None,
            cli_version=version,
            minimum_cli_version=self.settings.minimum_cli_version,
            headless_minimum_cli_version=self.settings.headless_minimum_cli_version,
            credential_identity=identity.fingerprint,
        )

    async def list_servers(self, actor_id: str) -> list[ClaudeMcpServer]:
        identity, _ = await self._checked_identity(actor_id)
        result = await self.driver.list_servers(identity)
        if not result.ok:
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.CLI_FAILED,
                "Claude MCP server discovery failed.",
            )
        servers: list[ClaudeMcpServer] = []
        for name in parse_server_names(
            result.output,
            max_length=self.settings.max_server_name_length,
        ):
            servers.append(await self._server(identity, name))
        return servers

    async def configure_http_server(
        self,
        actor_id: str,
        server_name: str,
        server_url: str,
    ) -> ClaudeMcpServer:
        """Create one actor-owned, user-scope remote HTTP MCP server."""

        identity, _ = await self._checked_identity(actor_id)
        name = self._user_owned_server_name(server_name)
        try:
            url = validate_server_url(
                server_url,
                max_length=self.settings.max_server_url_length,
            )
        except ValueError as exc:
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.SERVER_CONFIGURATION_INVALID,
                "Claude MCP server URL must be an absolute HTTP or HTTPS URL.",
            ) from exc
        self._ensure_identity_is_idle(identity)
        lock = self._credential_locks.setdefault(identity.fingerprint, asyncio.Lock())
        async with lock:
            result = await self.driver.add_http_user_server(identity, name, url)
            if not result.ok:
                raise ClaudeMcpError(
                    ClaudeMcpErrorCode.CLI_FAILED,
                    "Claude MCP server configuration failed.",
                )
            return await self._server(identity, name)

    async def remove_server(
        self,
        actor_id: str,
        server_name: str,
    ) -> ClaudeMcpServer:
        """Remove one actor-owned user-scope server and revoke existing projections."""

        identity, _ = await self._checked_identity(actor_id)
        name = self._user_owned_server_name(server_name)
        self._ensure_identity_is_idle(identity)
        current = await self._server(identity, name)
        if current.config_scope is not ClaudeMcpConfigScope.USER:
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.SERVER_OWNERSHIP_CONFLICT,
                "Only user-scoped Claude MCP servers can be removed from Resources.",
            )
        lock = self._credential_locks.setdefault(identity.fingerprint, asyncio.Lock())
        async with lock:
            logout_result = await self.driver.logout(identity, name)
            if current.state is ClaudeMcpState.CONNECTED and not logout_result.ok:
                raise ClaudeMcpError(
                    ClaudeMcpErrorCode.CLI_FAILED,
                    "Claude MCP credentials could not be revoked before removal.",
                )
            result = await self.driver.remove_user_server(identity, name)
            if not result.ok:
                raise ClaudeMcpError(
                    ClaudeMcpErrorCode.CLI_FAILED,
                    "Claude MCP server removal failed.",
                )
            verified = await self.driver.get_server(identity, name)
            state = parse_server_state(verified.output)
            if verified.ok or state is not ClaudeMcpState.NOT_CONFIGURED:
                raise ClaudeMcpError(
                    ClaudeMcpErrorCode.CLI_FAILED,
                    "Claude MCP server removal could not be verified.",
                )
        try:
            await self.credential_synchronizer.revoke_existing_thread_credentials(
                actor_id
            )
        except ClaudeMcpCredentialError as exc:
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.CREDENTIAL_SYNC_FAILED,
                "Claude MCP server was removed, but stale Agent projections could not be revoked safely.",
            ) from exc
        return ClaudeMcpServer(
            name=name,
            state=ClaudeMcpState.NOT_CONFIGURED,
            config_scope=ClaudeMcpConfigScope.USER,
            removable=False,
        )

    async def get_server(self, actor_id: str, server_name: str) -> ClaudeMcpServer:
        identity, _ = await self._checked_identity(actor_id)
        name = self._server_name(server_name)
        return await self._server(identity, name)

    async def get_server_inventory(
        self,
        actor_id: str,
        server_name: str,
    ) -> ClaudeMcpServerInventory:
        """Return one safe live inventory without sending a prompt or tool call."""

        identity, _ = await self._checked_identity(actor_id)
        name = self._server_name(server_name)
        await self._server(identity, name)
        try:
            definitions = await self.credential_synchronizer.read_user_mcp_servers(
                actor_id
            )
        except ClaudeMcpCredentialError as exc:
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.INVENTORY_UNAVAILABLE,
                "Claude MCP server definitions could not be read safely.",
            ) from exc
        server_config = definitions.get(name)
        if not isinstance(server_config, Mapping):
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.INVENTORY_UNAVAILABLE,
                "Claude MCP server is not available to the Agent runtime.",
            )
        secure_storage_home = self.credential_synchronizer.secure_storage_home(
            actor_id
        )
        lock = self._inventory_locks.setdefault(
            (identity.fingerprint, name), asyncio.Lock()
        )
        async with lock:
            return await self.inventory_client.inspect(
                identity=identity,
                server_name=name,
                server_config=server_config,
                secure_storage_home=(
                    str(secure_storage_home) if secure_storage_home else None
                ),
            )

    async def _server(
        self,
        identity: ClaudeMcpRuntimeIdentity,
        name: str,
    ) -> ClaudeMcpServer:
        active_id = self._active_by_server.get((identity.fingerprint, name))
        if active_id:
            operation = self._operations.get(active_id)
            if operation and operation.state in _ACTIVE_STATES:
                return ClaudeMcpServer(
                    name=name,
                    state=operation.state,
                    active_operation_id=operation.id,
                )
        result = await self.driver.get_server(identity, name)
        state = parse_server_state(result.output)
        if not result.ok and state is ClaudeMcpState.NOT_CONFIGURED:
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.SERVER_NOT_FOUND,
                "Claude MCP server was not found.",
            )
        if not result.ok:
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.CLI_FAILED,
                "Claude MCP server status could not be verified.",
            )
        scope = parse_server_scope(result.output)
        return ClaudeMcpServer(
            name=name,
            state=state,
            config_scope=scope,
            removable=scope is ClaudeMcpConfigScope.USER,
        )

    async def start_auth(
        self,
        actor_id: str,
        server_name: str,
    ) -> ClaudeMcpOperation:
        identity, _ = await self._checked_identity(actor_id)
        name = self._server_name(server_name)
        await self._server(identity, name)
        key = (identity.fingerprint, name)
        async with self._registry_lock:
            for (active_fingerprint, _), active_operation_id in self._active_by_server.items():
                active_operation = self._operations.get(active_operation_id)
                if (
                    active_fingerprint == identity.fingerprint
                    and active_operation
                    and active_operation.state in _ACTIVE_STATES
                ):
                    if (
                        active_operation.actor_id == actor_id
                        and active_operation.server_name == name
                    ):
                        return active_operation
                    raise ClaudeMcpError(
                        ClaudeMcpErrorCode.OPERATION_CONFLICT,
                        "Another authentication operation is already mutating this credential identity.",
                    )
            existing_id = self._active_by_server.get(key)
            if existing_id:
                existing = self._operations.get(existing_id)
                if existing and existing.state in _ACTIVE_STATES:
                    if existing.actor_id == actor_id:
                        return existing
                    raise ClaudeMcpError(
                        ClaudeMcpErrorCode.OPERATION_CONFLICT,
                        "Another authentication operation is already active.",
                    )
            operation = ClaudeMcpOperation(
                id=str(uuid.uuid4()),
                actor_id=actor_id,
                identity_fingerprint=identity.fingerprint,
                server_name=name,
                state=ClaudeMcpState.AUTH_STARTING,
                created_at=_now(),
                updated_at=_now(),
            )
            self._operations[operation.id] = operation
            self._active_by_server[key] = operation.id
            task = asyncio.create_task(self._run_auth(operation, identity))
            operation.task = task

        deadline = asyncio.get_running_loop().time() + self.settings.readiness_timeout_seconds
        while operation.state is ClaudeMcpState.AUTH_STARTING:
            if asyncio.get_running_loop().time() >= deadline:
                await self.cancel_auth(actor_id, operation.id)
                self._fail(
                    operation,
                    ClaudeMcpErrorCode.MALFORMED_CLI_OUTPUT,
                    "Claude MCP login did not provide an authorization URL.",
                )
                break
            await asyncio.sleep(0.02)
        return operation

    async def _run_auth(
        self,
        operation: ClaudeMcpOperation,
        identity: ClaudeMcpRuntimeIdentity,
    ) -> None:
        buffer = ""
        handle: ClaudeMcpLoginHandle | None = None
        try:
            handle = await self.driver.start_login(identity, operation.server_name)
            operation.handle = handle
            deadline = (
                asyncio.get_running_loop().time() + self.settings.auth_timeout_seconds
            )
            while True:
                remaining = deadline - asyncio.get_running_loop().time()
                if remaining <= 0:
                    raise asyncio.TimeoutError
                chunk = await asyncio.wait_for(handle.read(), timeout=remaining)
                if chunk:
                    decoded = chunk.decode("utf-8", errors="replace")
                    buffer = (buffer + decoded)[-self.settings.max_capture_bytes :]
                    if operation.authorization_url is None:
                        authorization_url = parse_authorization_url(buffer)
                        if authorization_url:
                            operation.authorization_url = authorization_url
                            operation.state = ClaudeMcpState.WAITING_FOR_USER
                            operation.updated_at = _now()
                    continue
                exit_code = await handle.wait()
                if operation.state is ClaudeMcpState.CANCELLING:
                    self._fail(
                        operation,
                        ClaudeMcpErrorCode.AUTH_CANCELLED,
                        "Claude MCP authentication was cancelled.",
                    )
                    return
                if exit_code != 0:
                    self._fail(
                        operation,
                        ClaudeMcpErrorCode.CLI_FAILED,
                        "Claude MCP login exited before authentication completed.",
                    )
                    return
                if operation.authorization_url is None:
                    self._fail(
                        operation,
                        ClaudeMcpErrorCode.MALFORMED_CLI_OUTPUT,
                        "Claude MCP login output did not contain an authorization URL.",
                    )
                    return
                verified = await self.driver.get_server(identity, operation.server_name)
                if not verified.ok or parse_server_state(verified.output) is not ClaudeMcpState.CONNECTED:
                    self._fail(
                        operation,
                        ClaudeMcpErrorCode.CLI_FAILED,
                        "Claude MCP authentication could not be verified.",
                    )
                    return
                # Linux credentials are an official file-backed store and can
                # be verified without exposing their values.  On macOS Claude
                # Code owns the config-dir-keyed Keychain item: reading it from
                # Python would trigger SecurityAgent and copy secrets into the
                # backend process.  There the formal `mcp get` result above is
                # the verification boundary; Agent reuses the same secure-store
                # selector rather than decrypting or projecting the item.
                if self.credential_synchronizer.requires_file_credential_verification:
                    try:
                        if not await self.credential_synchronizer.has_user_mcp_credentials(
                            operation.actor_id
                        ):
                            raise ClaudeMcpCredentialError(
                                "The verified login did not produce user-scoped MCP credentials."
                            )
                    except ClaudeMcpCredentialError:
                        self._fail(
                            operation,
                            ClaudeMcpErrorCode.CREDENTIAL_SYNC_FAILED,
                            "Claude MCP connected, but its user credential store could not be verified safely.",
                        )
                        return
                operation.authorization_url = None
                operation.state = ClaudeMcpState.CONNECTED
                operation.error_code = None
                operation.error_message = None
                operation.updated_at = _now()
                return
        except asyncio.TimeoutError:
            self._fail(
                operation,
                ClaudeMcpErrorCode.AUTH_TIMEOUT,
                "Claude MCP authentication timed out.",
            )
        except asyncio.CancelledError:
            self._fail(
                operation,
                ClaudeMcpErrorCode.AUTH_CANCELLED,
                "Claude MCP authentication was cancelled.",
            )
            raise
        except Exception:
            if operation.state is ClaudeMcpState.CANCELLING:
                self._fail(
                    operation,
                    ClaudeMcpErrorCode.AUTH_CANCELLED,
                    "Claude MCP authentication was cancelled.",
                )
            else:
                self._fail(
                    operation,
                    ClaudeMcpErrorCode.CLI_FAILED,
                    "Claude MCP authentication process failed.",
                )
        finally:
            operation.authorization_url = None if operation.state not in _ACTIVE_STATES else operation.authorization_url
            if handle is not None:
                if handle.process.returncode is None:
                    await handle.terminate()
                else:
                    handle.close()
            operation.handle = None
            self._active_by_server.pop(
                (operation.identity_fingerprint, operation.server_name), None
            )

    async def submit_redirect(
        self,
        actor_id: str,
        operation_id: str,
        redirect_url: str,
    ) -> ClaudeMcpOperation:
        operation = self._owned_operation(actor_id, operation_id)
        if operation.state is not ClaudeMcpState.WAITING_FOR_USER or operation.redirect_submitted:
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.OPERATION_CONFLICT,
                "The authentication operation is not waiting for a redirect URL.",
            )
        try:
            validated = validate_redirect_url(
                redirect_url,
                max_length=self.settings.max_redirect_url_length,
            )
        except ValueError as exc:
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.INVALID_REDIRECT_URL,
                "Redirect URL must be a valid absolute HTTP(S) URL.",
            ) from exc
        handle = operation.handle
        if not isinstance(handle, ClaudeMcpLoginHandle):
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.OPERATION_CONFLICT,
                "The authentication process is no longer available.",
            )
        operation.state = ClaudeMcpState.EXCHANGING_CODE
        operation.redirect_submitted = True
        operation.authorization_url = None
        operation.updated_at = _now()
        try:
            await handle.write_redirect(validated)
        except (BrokenPipeError, OSError) as exc:
            # Current Claude Code may receive the localhost browser callback
            # directly and complete before the UI posts the same redirect URL.
            # Let the single owning task finish its official `mcp get`
            # verification before classifying the closed PTY as a failure.
            task = operation.task
            if isinstance(task, asyncio.Task) and not task.done():
                try:
                    await asyncio.wait_for(
                        asyncio.shield(task),
                        timeout=self.settings.readiness_timeout_seconds,
                    )
                except asyncio.TimeoutError:
                    pass
            if operation.state is ClaudeMcpState.CONNECTED:
                operation.error_code = None
                operation.error_message = None
                operation.updated_at = _now()
                return operation
            self._fail(
                operation,
                ClaudeMcpErrorCode.CLI_FAILED,
                "Claude MCP login closed before accepting the redirect URL.",
            )
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.CLI_FAILED,
                "Claude MCP login closed before accepting the redirect URL.",
            ) from exc
        return operation

    async def cancel_auth(
        self,
        actor_id: str,
        operation_id: str,
    ) -> ClaudeMcpOperation:
        operation = self._owned_operation(actor_id, operation_id)
        if operation.state not in _ACTIVE_STATES:
            return operation
        operation.state = ClaudeMcpState.CANCELLING
        operation.authorization_url = None
        operation.updated_at = _now()
        handle = operation.handle
        if isinstance(handle, ClaudeMcpLoginHandle):
            await handle.terminate()
        task = operation.task
        if isinstance(task, asyncio.Task) and not task.done():
            try:
                await asyncio.wait_for(asyncio.shield(task), timeout=self.settings.terminate_grace_seconds + 1)
            except asyncio.TimeoutError:
                task.cancel()
        if operation.state is ClaudeMcpState.CANCELLING:
            self._fail(
                operation,
                ClaudeMcpErrorCode.AUTH_CANCELLED,
                "Claude MCP authentication was cancelled.",
            )
        return operation

    async def get_operation(
        self,
        actor_id: str,
        operation_id: str,
    ) -> ClaudeMcpOperation:
        return self._owned_operation(actor_id, operation_id)

    async def logout(self, actor_id: str, server_name: str) -> ClaudeMcpServer:
        identity, _ = await self._checked_identity(actor_id)
        name = self._server_name(server_name)
        current = await self._server(identity, name)
        key = (identity.fingerprint, name)
        if key in self._active_by_server:
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.OPERATION_CONFLICT,
                "Cancel the active authentication operation before logging out.",
            )
        lock = self._credential_locks.setdefault(identity.fingerprint, asyncio.Lock())
        async with lock:
            result = await self.driver.logout(identity, name)
            if not result.ok:
                raise ClaudeMcpError(
                    ClaudeMcpErrorCode.CLI_FAILED,
                    "Claude MCP logout failed.",
                )
            verified = await self.driver.get_server(identity, name)
        state = parse_server_state(verified.output)
        if verified.ok and state is ClaudeMcpState.CONNECTED:
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.CLI_FAILED,
                "Claude MCP logout could not be verified.",
            )
        try:
            await self.credential_synchronizer.revoke_existing_thread_credentials(
                actor_id
            )
        except ClaudeMcpCredentialError as exc:
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.CREDENTIAL_SYNC_FAILED,
                "Claude MCP logged out, but stale Agent credential projections could not be revoked safely.",
            ) from exc
        return ClaudeMcpServer(
            name=name,
            state=ClaudeMcpState.LOGGED_OUT,
            config_scope=current.config_scope,
            removable=current.removable,
        )

    async def shutdown(self) -> None:
        active = [
            operation
            for operation in self._operations.values()
            if operation.state in _ACTIVE_STATES
        ]
        for operation in active:
            await self.cancel_auth(operation.actor_id, operation.id)

    def _server_name(self, value: str) -> str:
        try:
            return validate_server_name(
                value,
                max_length=self.settings.max_server_name_length,
            )
        except ValueError as exc:
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.SERVER_NOT_FOUND,
                "Claude MCP server name is invalid.",
            ) from exc

    def _user_owned_server_name(self, value: str) -> str:
        name = self._server_name(value)
        if name.startswith("plugin:"):
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.SERVER_OWNERSHIP_CONFLICT,
                "Plugin-owned MCP servers must be managed from Plugins.",
            )
        return name

    def _ensure_identity_is_idle(self, identity: ClaudeMcpRuntimeIdentity) -> None:
        for (fingerprint, _), operation_id in self._active_by_server.items():
            operation = self._operations.get(operation_id)
            if (
                fingerprint == identity.fingerprint
                and operation
                and operation.state in _ACTIVE_STATES
            ):
                raise ClaudeMcpError(
                    ClaudeMcpErrorCode.OPERATION_CONFLICT,
                    "Cancel the active authentication operation before changing MCP configuration.",
                )

    def _owned_operation(
        self,
        actor_id: str,
        operation_id: str,
    ) -> ClaudeMcpOperation:
        operation = self._operations.get(operation_id)
        if operation is None or operation.actor_id != actor_id:
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.OPERATION_NOT_FOUND,
                "Claude MCP authentication operation was not found.",
            )
        return operation

    @staticmethod
    def _fail(
        operation: ClaudeMcpOperation,
        code: ClaudeMcpErrorCode,
        message: str,
    ) -> None:
        operation.state = ClaudeMcpState.FAILED
        operation.authorization_url = None
        operation.error_code = code.value
        operation.error_message = message
        operation.updated_at = _now()
