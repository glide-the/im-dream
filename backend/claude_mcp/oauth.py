"""MCP SDK OAuth provider integration backed by encrypted PostgreSQL storage.

[Input] mcp.client.auth OAuthClientProvider, actor-owned Server rows, encrypted repository, and callback URLs.
[Output] Process-local auth operations and TokenStorage persistence without copied metadata/PKCE/refresh logic.
[Pos] Managed MCP OAuth orchestration; protocol state machine remains owned by standard mcp 1.27.1.
[Sync] 2026-08-25: add SDK-native OAuth operations with encrypted TokenStorage and safe cancellation.
[Sync] 2026-08-25: restore persisted token expiry into the standard SDK provider so refresh runs after process restart.
[Sync] 2026-08-25: project the stable Server key in public operations while retaining UUID ownership locks internally.
[Sync] 2026-08-25: stage SDK client registration until tokens exist so a cancelled first login cannot persist a credential-shaped partial document.
[Sync] 2026-08-25: give interactive SDK discovery the OAuth timeout and direct cancellation ownership.
[Sync] 2026-08-25: persist SDK-discovered authorization metadata inside the encrypted token document so reconstructed providers refresh through the discovered token endpoint.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
from typing import Any
from urllib.parse import parse_qs, urlsplit
import uuid

from mcp.client.auth import OAuthClientProvider, TokenStorage
from mcp.shared.auth import (
    OAuthClientInformationFull,
    OAuthClientMetadata,
    OAuthMetadata,
    OAuthToken,
)

from .contracts import (
    ClaudeMcpError,
    ClaudeMcpErrorCode,
    ClaudeMcpOperation,
    ClaudeMcpState,
    McpAuthKind,
)
from .crypto import (
    McpCredentialCipher,
    McpCredentialContext,
    McpCredentialIntegrityError,
    McpEncryptedCredential,
)
from .repository import McpServerRecord


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class EncryptedMcpTokenStorage(TokenStorage):
    """Persist the SDK's token/client models in one encrypted OAuth document."""

    def __init__(
        self,
        repository: Any,
        cipher: McpCredentialCipher,
        *,
        actor_id: str,
        server_id: str,
    ) -> None:
        self.repository = repository
        self.cipher = cipher
        self.actor_id = actor_id
        self.server_id = server_id
        self._lock = asyncio.Lock()
        self._pending_client_info: dict[str, Any] | None = None
        self._oauth_context: Any | None = None

    def bind_oauth_context(self, context: Any) -> None:
        """Bind the SDK context without taking ownership of its OAuth state machine."""

        self._oauth_context = context

    async def _document(self) -> dict[str, Any]:
        record = await self.repository.get_credential(self.actor_id, self.server_id)
        if record is None:
            return {}
        if record.kind != "oauth":
            raise McpCredentialIntegrityError()
        envelope = McpEncryptedCredential(
            ciphertext=record.ciphertext,
            iv=record.iv,
            tag=record.tag,
            fingerprint=record.fingerprint,
            key_version=record.key_version,
        )
        plaintext = self.cipher.decrypt(
            envelope,
            McpCredentialContext(
                user_id=self.actor_id,
                server_id=self.server_id,
                kind="oauth",
                key_version=record.key_version,
            ),
        )
        try:
            payload = json.loads(plaintext)
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise McpCredentialIntegrityError() from None
        if not isinstance(payload, dict) or any(
            key not in {"tokens", "clientInfo", "oauthMetadata"} for key in payload
        ):
            raise McpCredentialIntegrityError()
        return payload

    async def _store(self, key: str, value: dict[str, Any]) -> None:
        async with self._lock:
            document = await self._document()
            if key == "tokens" and self._pending_client_info is not None:
                document["clientInfo"] = dict(self._pending_client_info)
            if key == "tokens" and self._oauth_context is not None:
                oauth_metadata = getattr(self._oauth_context, "oauth_metadata", None)
                if oauth_metadata is not None:
                    document["oauthMetadata"] = oauth_metadata.model_dump(
                        mode="json",
                        exclude_none=True,
                    )
            document[key] = value
            plaintext = json.dumps(
                document,
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
            context = McpCredentialContext(
                user_id=self.actor_id,
                server_id=self.server_id,
                kind="oauth",
                key_version=self.cipher.key_version,
            )
            envelope = self.cipher.encrypt(plaintext, context)
            expires_at = None
            token_payload = document.get("tokens")
            if isinstance(token_payload, dict) and isinstance(token_payload.get("expires_in"), int):
                expires_at = datetime.now(timezone.utc) + timedelta(
                    seconds=token_payload["expires_in"]
                )
            await self.repository.upsert_credential(
                self.actor_id,
                self.server_id,
                kind="oauth",
                envelope=envelope,
                expires_at=expires_at,
            )
            if key == "tokens":
                self._pending_client_info = None

    async def get_tokens(self) -> OAuthToken | None:
        payload = (await self._document()).get("tokens")
        if payload is None:
            return None
        try:
            return OAuthToken.model_validate(payload)
        except Exception:
            raise McpCredentialIntegrityError() from None

    async def set_tokens(self, tokens: OAuthToken) -> None:
        await self._store("tokens", tokens.model_dump(mode="json", exclude_none=True))

    async def get_client_info(self) -> OAuthClientInformationFull | None:
        payload = (await self._document()).get("clientInfo")
        if payload is None:
            payload = self._pending_client_info
        if payload is None:
            return None
        try:
            return OAuthClientInformationFull.model_validate(payload)
        except Exception:
            raise McpCredentialIntegrityError() from None

    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        payload = client_info.model_dump(mode="json", exclude_none=True)
        document = await self._document()
        if "tokens" in document:
            await self._store("clientInfo", payload)
            return
        # Dynamic registration precedes the browser callback.  A process-local
        # operation cannot resume after restart, so clientInfo alone must not
        # become a misleading durable credential.  Keep it in this SDK
        # TokenStorage instance and persist it atomically with the first token.
        self._pending_client_info = dict(payload)

    async def restore_oauth_metadata(self, context: Any) -> None:
        """Restore only metadata previously discovered and validated by the SDK."""

        payload = (await self._document()).get("oauthMetadata")
        if payload is None:
            return
        try:
            context.oauth_metadata = OAuthMetadata.model_validate(payload)
        except Exception:
            raise McpCredentialIntegrityError() from None


class ManagedMcpAuthResolver:
    """Attach SDK OAuth only when an encrypted credential already exists."""

    def __init__(
        self,
        repository: Any,
        cipher: McpCredentialCipher,
        *,
        client_metadata: OAuthClientMetadata,
        timeout_seconds: float,
    ) -> None:
        self.repository = repository
        self.cipher = cipher
        self.client_metadata = client_metadata
        self.timeout_seconds = timeout_seconds

    async def resolve(self, actor_id: str, server: McpServerRecord) -> Any:
        if server.auth_kind is not McpAuthKind.OAUTH or not server.credential_configured:
            # First contact is intentionally anonymous. A 401/403 becomes the
            # safe CREDENTIAL_REQUIRED result and never starts browser auth.
            return None
        storage = EncryptedMcpTokenStorage(
            self.repository,
            self.cipher,
            actor_id=actor_id,
            server_id=server.id,
        )
        provider = OAuthClientProvider(
            server.remote_url or "",
            self.client_metadata,
            storage,
            timeout=self.timeout_seconds,
        )
        storage.bind_oauth_context(provider.context)
        await storage.restore_oauth_metadata(provider.context)
        record = await self.repository.get_credential(actor_id, server.id)
        if record is None or record.kind != "oauth":
            raise McpCredentialIntegrityError()
        if record.expires_at:
            try:
                expiry = datetime.fromisoformat(record.expires_at.replace("Z", "+00:00"))
            except ValueError:
                raise McpCredentialIntegrityError() from None
            if expiry.tzinfo is None:
                raise McpCredentialIntegrityError()
            # mcp 1.27.1 loads TokenStorage models during the first auth flow,
            # but it cannot reconstruct their original absolute expiry from
            # OAuthToken.expires_in alone.  The encrypted DB record owns that
            # timestamp; seeding it here lets the public provider execute its
            # own refreshAuthorization path without copying the OAuth state
            # machine into Dream.
            provider.context.token_expiry_time = expiry.timestamp()
        return provider


@dataclass
class _OperationState:
    operation: ClaudeMcpOperation
    callback: asyncio.Future[tuple[str, str | None]]
    ready: asyncio.Event


class ManagedMcpOAuthCoordinator:
    """Drive SDK OAuth with process-local browser handoff operations."""

    def __init__(
        self,
        repository: Any,
        cipher: McpCredentialCipher,
        discovery: Any,
        *,
        client_metadata: OAuthClientMetadata,
        auth_timeout_seconds: float,
        readiness_timeout_seconds: float,
        max_redirect_url_length: int,
    ) -> None:
        self.repository = repository
        self.cipher = cipher
        self.discovery = discovery
        self.client_metadata = client_metadata
        self.auth_timeout_seconds = auth_timeout_seconds
        self.readiness_timeout_seconds = readiness_timeout_seconds
        self.max_redirect_url_length = max_redirect_url_length
        self._operations: dict[str, _OperationState] = {}
        self._active: dict[tuple[str, str], str] = {}
        self._lock = asyncio.Lock()

    async def start(self, actor_id: str, server: McpServerRecord) -> ClaudeMcpOperation:
        if server.auth_kind is not McpAuthKind.OAUTH or not server.remote_url:
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.AUTH_NOT_REQUIRED,
                "Claude MCP authentication is not required for this server.",
            )
        key = (actor_id, server.id)
        async with self._lock:
            existing_id = self._active.get(key)
            if existing_id:
                return self._operations[existing_id].operation
            loop = asyncio.get_running_loop()
            operation = ClaudeMcpOperation(
                id=str(uuid.uuid4()),
                actor_id=actor_id,
                identity_fingerprint="managed-db",
                server_name=server.server_key,
                state=ClaudeMcpState.AUTH_STARTING,
                created_at=_now(),
                updated_at=_now(),
            )
            state = _OperationState(
                operation=operation,
                callback=loop.create_future(),
                ready=asyncio.Event(),
            )
            self._operations[operation.id] = state
            self._active[key] = operation.id

            async def redirect_handler(url: str) -> None:
                operation.authorization_url = url
                operation.state = ClaudeMcpState.WAITING_FOR_USER
                operation.updated_at = _now()
                state.ready.set()

            async def callback_handler() -> tuple[str, str | None]:
                return await state.callback

            storage = EncryptedMcpTokenStorage(
                self.repository,
                self.cipher,
                actor_id=actor_id,
                server_id=server.id,
            )
            provider = OAuthClientProvider(
                server.remote_url,
                self.client_metadata,
                storage,
                redirect_handler=redirect_handler,
                callback_handler=callback_handler,
                timeout=self.auth_timeout_seconds,
            )
            storage.bind_oauth_context(provider.context)
            await storage.restore_oauth_metadata(provider.context)
            operation.task = asyncio.create_task(
                self._run(state, server, provider),
                name=f"managed-mcp-oauth-{operation.id}",
            )
        try:
            await asyncio.wait_for(
                state.ready.wait(),
                timeout=self.readiness_timeout_seconds,
            )
        except TimeoutError:
            task = operation.task
            if isinstance(task, asyncio.Task) and task.done():
                return operation
            await self.cancel(actor_id, operation.id)
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.AUTH_TIMEOUT,
                "Claude MCP authentication did not become ready in time.",
            ) from None
        return operation

    async def _run(
        self,
        state: _OperationState,
        server: McpServerRecord,
        provider: OAuthClientProvider,
    ) -> None:
        operation = state.operation
        try:
            result = await self.discovery.discover_one(
                operation.actor_id,
                server.id,
                workspace_id=server.workspace_id,
                force=True,
                auth=provider,
                operation_timeout_seconds=self.auth_timeout_seconds,
            )
            if result.error:
                operation.state = ClaudeMcpState.FAILED
                operation.error_code = result.error.code
                operation.error_message = "Claude MCP authentication failed safely."
            else:
                operation.state = ClaudeMcpState.CONNECTED
        except asyncio.CancelledError:
            operation.state = ClaudeMcpState.FAILED
            operation.error_code = ClaudeMcpErrorCode.AUTH_CANCELLED.value
            operation.error_message = "Claude MCP authentication was cancelled."
        except BaseException:
            operation.state = ClaudeMcpState.FAILED
            operation.error_code = ClaudeMcpErrorCode.PROTOCOL_ERROR.value
            operation.error_message = "Claude MCP authentication failed safely."
        finally:
            operation.authorization_url = None
            operation.updated_at = _now()
            state.ready.set()
            async with self._lock:
                self._active.pop((operation.actor_id, server.id), None)

    async def get(self, actor_id: str, operation_id: str) -> ClaudeMcpOperation:
        state = self._operations.get(operation_id)
        if state is None or state.operation.actor_id != actor_id:
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.OPERATION_NOT_FOUND,
                "Claude MCP authentication operation was not found.",
            )
        return state.operation

    async def submit_redirect(
        self,
        actor_id: str,
        operation_id: str,
        redirect_url: str,
    ) -> ClaudeMcpOperation:
        state = self._operations.get(operation_id)
        if state is None or state.operation.actor_id != actor_id:
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.OPERATION_NOT_FOUND,
                "Claude MCP authentication operation was not found.",
            )
        operation = state.operation
        if operation.redirect_submitted or state.callback.done():
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.OPERATION_CONFLICT,
                "Claude MCP authentication callback was already submitted.",
            )
        code, returned_state = self._parse_callback(redirect_url)
        operation.authorization_url = None
        operation.redirect_submitted = True
        operation.state = ClaudeMcpState.EXCHANGING_CODE
        operation.updated_at = _now()
        state.callback.set_result((code, returned_state))
        return operation

    def _parse_callback(self, redirect_url: str) -> tuple[str, str | None]:
        if not isinstance(redirect_url, str) or len(redirect_url) > self.max_redirect_url_length:
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.INVALID_REDIRECT_URL,
                "Claude MCP redirect URL is invalid.",
            )
        parsed = urlsplit(redirect_url)
        loopback = parsed.hostname in {"localhost", "127.0.0.1", "::1"}
        if (
            parsed.scheme not in ({"https"} | ({"http"} if loopback else set()))
            or not parsed.hostname
            or parsed.username
            or parsed.password
            or parsed.fragment
        ):
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.INVALID_REDIRECT_URL,
                "Claude MCP redirect URL is invalid.",
            )
        query = parse_qs(parsed.query, keep_blank_values=True)
        codes = query.get("code", [])
        states = query.get("state", [])
        if len(codes) != 1 or not codes[0] or len(states) > 1:
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.INVALID_REDIRECT_URL,
                "Claude MCP redirect URL is invalid.",
            )
        return codes[0], states[0] if states else None

    async def cancel(self, actor_id: str, operation_id: str) -> ClaudeMcpOperation:
        state = self._operations.get(operation_id)
        if state is None or state.operation.actor_id != actor_id:
            raise ClaudeMcpError(
                ClaudeMcpErrorCode.OPERATION_NOT_FOUND,
                "Claude MCP authentication operation was not found.",
            )
        operation = state.operation
        operation.authorization_url = None
        operation.state = ClaudeMcpState.CANCELLING
        if not state.callback.done():
            state.callback.cancel()
        task = operation.task
        if isinstance(task, asyncio.Task) and not task.done():
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        operation.state = ClaudeMcpState.FAILED
        operation.error_code = ClaudeMcpErrorCode.AUTH_CANCELLED.value
        operation.error_message = "Claude MCP authentication was cancelled."
        operation.updated_at = _now()
        return operation

    async def shutdown(self) -> None:
        tasks = [
            state.operation.task
            for state in self._operations.values()
            if isinstance(state.operation.task, asyncio.Task)
            and not state.operation.task.done()
        ]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)


__all__ = [
    "EncryptedMcpTokenStorage",
    "ManagedMcpAuthResolver",
    "ManagedMcpOAuthCoordinator",
]
