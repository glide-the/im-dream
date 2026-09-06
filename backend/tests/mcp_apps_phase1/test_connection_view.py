"""Phase 1 Node connection projection security contracts.

[Input] Injected actor-scoped records, cached catalogs, and a recording config loader.
[Output] C1 pre-decryption validation, minimal DTO, and redaction assertions.
[Pos] Provider-free tests; no database, provider, or production Apps enablement.
[Sync] 2026-09-06: require explicit server-owned policy before catalog or credential projection.
[Sync] 2026-09-06: cover authoritative credential revision after an expired OAuth refresh.
[Sync] 2026-09-06: require enabled connection App settings and bind their independent revision.
[Sync] 2026-09-06: prove an expired discovery snapshot is rebuilt through the existing bounded discovery path.
"""

import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from backend.claude_mcp.contracts import (
    ClaudeMcpError,
    ClaudeMcpErrorCode,
    McpAppPreferenceState,
    McpAuthKind,
    McpTransport,
)
from backend.claude_mcp.crypto import McpCredentialCipher, McpCredentialContext
from backend.claude_mcp.repository import (
    McpAppSettingsRecord,
    McpCredentialRecord,
    McpServerRecord,
)
from backend.claude_mcp.runtime_snapshot import (
    ManagedMcpRuntimeSnapshotLoader,
    ManagedMcpServerConfigProjection,
    SecretMcpConfigDict,
)
from backend.claude_mcp.service import ClaudeMcpService

SERVER = McpServerRecord(
    id="server-id",
    user_id="42",
    workspace_id="workspace-a",
    scope="workspace",
    server_key="official-basic",
    display_name="Official basic server",
    transport=McpTransport.STREAMABLE_HTTP,
    remote_url="http://127.0.0.1:8766/mcp",
    stdio_profile_key=None,
    auth_kind=McpAuthKind.NONE,
    enabled=True,
    config_revision=4,
    credential_revision=2,
    credential_id=None,
    credential_configured=False,
    created_at="2026-09-05T00:00:00+00:00",
    updated_at="2026-09-05T00:00:00+00:00",
)

INVENTORY = {
    "status": "complete",
    "inventory": {
        "tools": [
            {
                "name": "get-time",
                "annotations": {
                    "readOnlyHint": True,
                    "destructiveHint": False,
                },
                "_meta": {"ui": {"resourceUri": "ui://get-time/mcp-app.html"}},
            },
            {"name": "write_not_allowed", "annotations": {"readOnlyHint": False}},
        ],
        "resources": [
            {"uri": "ui://get-time/mcp-app.html"},
            {"uri": "https://not-an-app-resource.invalid"},
        ],
    },
}

POLICY = {
    "version": 1,
    "revision": 7,
    "default": {"resourceReads": False, "lowRiskToolCalls": False},
    "desired": {"resourceReads": True, "lowRiskToolCalls": True},
    "effective": {"resourceReads": True, "lowRiskToolCalls": True},
    "servers": {
        "official-basic": {
            "allowedTools": ["get-time"],
            "allowedResources": ["ui://get-time/mcp-app.html"],
            "appCallableLowRiskTools": ["get-time"],
        }
    },
}


class Repository:
    def __init__(self, record=SERVER, app_settings=None):
        self.record = record
        self.app_settings = app_settings or McpAppSettingsRecord(
            desired=McpAppPreferenceState(
                enabled=True,
                low_risk_tool_calls=True,
                ui_messages=True,
            ),
            revision=3,
        )

    async def capability_available(self):
        return True

    async def app_settings_capability_available(self):
        return True

    async def get_app_settings(self, actor_id, server_id, workspace_id=None):
        if actor_id != self.record.user_id or server_id != self.record.id:
            return None
        if workspace_id != self.record.workspace_id:
            return None
        return self.app_settings

    async def get_server(self, actor_id, identifier, workspace_id=None):
        if actor_id != self.record.user_id or identifier not in {
            self.record.id,
            self.record.server_key,
        }:
            return None
        if workspace_id != self.record.workspace_id:
            return None
        return self.record

    async def get_discovery_snapshot(self, actor_id, record):
        assert actor_id == record.user_id
        return INVENTORY


class RecordingLoader:
    def __init__(self):
        self.calls = 0

    async def load_server_config(
        self,
        actor_id,
        record,
        *,
        expected_config_revision=None,
        expected_credential_revision=None,
    ):
        self.calls += 1
        assert actor_id == record.user_id
        assert expected_config_revision == record.config_revision
        assert expected_credential_revision == record.credential_revision
        return ManagedMcpServerConfigProjection(
            config=SecretMcpConfigDict(
                type="http",
                url=record.remote_url,
                headers={"Authorization": "redacted-test"},
            ),
            config_revision=record.config_revision,
            credential_revision=record.credential_revision,
        )


def service(record=SERVER, app_settings=None):
    loader = RecordingLoader()
    return ClaudeMcpService(
        repository=Repository(record, app_settings),
        discovery=object(),
        oauth=object(),
        runtime_snapshot_loader=loader,
        mcp_apps_policy_provider=lambda: POLICY,
    ), loader


@pytest.mark.asyncio
async def test_connection_view_is_minimal_short_lived_and_repr_redacts_profile():
    subject, loader = service()
    view = await subject.mcp_apps_connection_view(
        "42",
        SERVER.server_key,
        SERVER.workspace_id,
        expected_config_revision=4,
        expected_credential_revision=2,
        expected_app_settings_revision=3,
        expected_policy_revision=7,
        ttl_seconds=30,
        now=datetime(2026, 9, 5, tzinfo=timezone.utc),
    )

    payload = view.to_dict()
    assert payload["serverId"] == "server-id"
    assert payload["allowedTools"] == ["get-time"]
    assert payload["allowedResources"] == ["ui://get-time/mcp-app.html"]
    assert payload["appCallableLowRiskTools"] == ["get-time"]
    assert payload["appSettingsRevision"] == 3
    assert payload["policy"]["revision"] == 7
    assert payload["connectionProfile"]["type"] == "streamable_http"
    assert payload["expiresAt"] == "2026-09-05T00:00:30+00:00"
    assert "redacted-test" not in repr(view)
    assert "refresh" not in payload
    assert loader.calls == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("record", "expected_config", "expected_credential", "code"),
    [
        (replace(SERVER, enabled=False), 4, 2, ClaudeMcpErrorCode.APP_RUNTIME_DENIED),
        (SERVER, 3, 2, ClaudeMcpErrorCode.APP_RUNTIME_REVISION_CONFLICT),
        (SERVER, 4, 1, ClaudeMcpErrorCode.APP_RUNTIME_REVISION_CONFLICT),
    ],
)
async def test_invalid_state_is_rejected_before_config_or_credential_projection(
    record, expected_config, expected_credential, code
):
    subject, loader = service(record)
    with pytest.raises(ClaudeMcpError) as caught:
        await subject.mcp_apps_connection_view(
            "42",
            record.server_key,
            record.workspace_id,
            expected_config_revision=expected_config,
            expected_credential_revision=expected_credential,
            expected_policy_revision=7,
            ttl_seconds=30,
        )
    assert caught.value.code is code
    assert loader.calls == 0


@pytest.mark.asyncio
async def test_wrong_actor_cannot_reach_config_projection():
    subject, loader = service()
    with pytest.raises(ClaudeMcpError) as caught:
        await subject.mcp_apps_connection_view(
            "99",
            SERVER.server_key,
            SERVER.workspace_id,
            expected_config_revision=4,
            expected_credential_revision=2,
            expected_policy_revision=7,
            ttl_seconds=30,
        )
    assert caught.value.code is ClaudeMcpErrorCode.SERVER_NOT_FOUND
    assert loader.calls == 0


@pytest.mark.asyncio
async def test_disabled_or_stale_app_settings_are_rejected_before_projection():
    disabled = McpAppSettingsRecord(McpAppPreferenceState(), revision=3)
    subject, loader = service(app_settings=disabled)
    with pytest.raises(ClaudeMcpError) as caught:
        await subject.mcp_apps_connection_view(
            SERVER.user_id,
            SERVER.server_key,
            SERVER.workspace_id,
            expected_config_revision=4,
            expected_credential_revision=2,
            expected_app_settings_revision=3,
            expected_policy_revision=7,
            ttl_seconds=30,
        )
    assert caught.value.code is ClaudeMcpErrorCode.APP_RUNTIME_DENIED
    assert loader.calls == 0

    subject, loader = service()
    with pytest.raises(ClaudeMcpError) as caught:
        await subject.mcp_apps_connection_view(
            SERVER.user_id,
            SERVER.server_key,
            SERVER.workspace_id,
            expected_config_revision=4,
            expected_credential_revision=2,
            expected_app_settings_revision=2,
            expected_policy_revision=7,
            ttl_seconds=30,
        )
    assert caught.value.code is ClaudeMcpErrorCode.APP_RUNTIME_REVISION_CONFLICT
    assert loader.calls == 0


@pytest.mark.asyncio
async def test_public_settings_separate_user_desired_from_server_availability():
    subject, _ = service()
    settings = await subject.get_mcp_app_connection_settings(
        SERVER.user_id,
        SERVER.server_key,
        SERVER.workspace_id,
    )
    payload = settings.to_dict()
    assert payload["default"] == {
        "enabled": False,
        "interactions": {"lowRiskToolCalls": False, "uiMessages": False},
    }
    assert payload["desired"]["enabled"] is True
    assert payload["server"] == {
        "state": "ready",
        "reasonCode": None,
        "resourceReads": True,
        "lowRiskToolCalls": True,
    }


@pytest.mark.asyncio
async def test_expired_inventory_is_refreshed_for_settings_and_connection_view():
    class ExpiredRepository(Repository):
        def __init__(self):
            super().__init__()
            self.snapshot = None

        async def get_discovery_snapshot(self, actor_id, record):
            assert actor_id == record.user_id
            return self.snapshot

    repository = ExpiredRepository()

    class CompleteStatus:
        value = "complete"

    class RefreshedResult:
        status = CompleteStatus()

        @staticmethod
        def inventory_dict():
            return INVENTORY["inventory"]

    class Discovery:
        def __init__(self):
            self.calls = 0

        async def discover_one(self, actor_id, server_id, **kwargs):
            self.calls += 1
            assert (actor_id, server_id, kwargs) == (
                SERVER.user_id,
                SERVER.id,
                {"workspace_id": SERVER.workspace_id, "force": False},
            )
            repository.snapshot = INVENTORY
            return RefreshedResult()

    discovery = Discovery()
    loader = RecordingLoader()
    subject = ClaudeMcpService(
        repository=repository,
        discovery=discovery,
        oauth=object(),
        runtime_snapshot_loader=loader,
        mcp_apps_policy_provider=lambda: POLICY,
    )

    settings = await subject.get_mcp_app_connection_settings(
        SERVER.user_id,
        SERVER.server_key,
        SERVER.workspace_id,
    )
    assert settings.server.state.value == "ready"
    assert discovery.calls == 1

    view = await subject.mcp_apps_connection_view(
        SERVER.user_id,
        SERVER.server_key,
        SERVER.workspace_id,
        expected_config_revision=SERVER.config_revision,
        expected_credential_revision=SERVER.credential_revision,
        expected_app_settings_revision=3,
        expected_policy_revision=7,
        ttl_seconds=10,
    )
    assert view.allowed_resources == ("ui://get-time/mcp-app.html",)
    assert view.app_callable_low_risk_tools == ("get-time",)
    assert discovery.calls == 1


@pytest.mark.asyncio
async def test_missing_workspace_scope_allows_only_user_scoped_server():
    workspace_subject, workspace_loader = service()
    with pytest.raises(ClaudeMcpError) as caught:
        await workspace_subject.mcp_apps_connection_view(
            SERVER.user_id,
            SERVER.server_key,
            None,
            expected_config_revision=4,
            expected_credential_revision=2,
            expected_policy_revision=7,
            ttl_seconds=30,
        )
    assert caught.value.code is ClaudeMcpErrorCode.SERVER_NOT_FOUND
    assert workspace_loader.calls == 0

    user_server = replace(SERVER, scope="user", workspace_id=None)
    user_subject, user_loader = service(user_server)
    view = await user_subject.mcp_apps_connection_view(
        user_server.user_id,
        user_server.server_key,
        None,
        expected_config_revision=4,
        expected_credential_revision=2,
        expected_policy_revision=7,
        ttl_seconds=30,
    )
    assert view.workspace_scope is None
    assert user_loader.calls == 1


def test_static_view_never_enables_production_apps():
    subject, _ = service()
    payload = subject.mcp_apps_static_view().to_dict()
    assert payload["productionAppsEffective"] is False
    assert payload["transports"] == ["streamable_http"]
    assert payload["policy"]["default"] == {
        "resourceReads": False,
        "lowRiskToolCalls": False,
    }


@pytest.mark.asyncio
async def test_single_server_loader_rechecks_revision_before_credential_read():
    class RuntimeRepository:
        async def get_server(self, actor_id, identifier, workspace_id=None):
            assert actor_id == SERVER.user_id
            return replace(SERVER, config_revision=5)

        async def get_credential(self, actor_id, server_id):
            raise AssertionError("credential must not be read after revision conflict")

    loader = ManagedMcpRuntimeSnapshotLoader(
        RuntimeRepository(),
        cipher=None,
        stdio_profiles=object(),
        max_servers=1,
    )
    with pytest.raises(ClaudeMcpError) as caught:
        await loader.load_server_config(
            SERVER.user_id,
            SERVER,
            expected_config_revision=4,
            expected_credential_revision=2,
        )
    assert caught.value.code is ClaudeMcpErrorCode.APP_RUNTIME_REVISION_CONFLICT


@pytest.mark.asyncio
async def test_expired_oauth_is_rejected_before_decryption():
    oauth_server = replace(
        SERVER,
        auth_kind=McpAuthKind.OAUTH,
        credential_configured=True,
        credential_id="credential-id",
    )
    credential = McpCredentialRecord(
        id="credential-id",
        server_id=SERVER.id,
        user_id=SERVER.user_id,
        kind="oauth",
        ciphertext="never-decrypt",
        iv="never-decrypt",
        tag="never-decrypt",
        fingerprint="never-decrypt",
        key_version=1,
        credential_revision=2,
        expires_at="2000-01-01T00:00:00+00:00",
    )

    class RuntimeRepository:
        async def get_server(self, actor_id, identifier, workspace_id=None):
            return oauth_server

        async def get_credential(self, actor_id, server_id):
            return credential

    class ForbiddenCipher:
        def decrypt(self, *_args, **_kwargs):
            raise AssertionError("expired credential must not be decrypted")

    loader = ManagedMcpRuntimeSnapshotLoader(
        RuntimeRepository(),
        cipher=ForbiddenCipher(),
        stdio_profiles=object(),
        max_servers=1,
    )
    with pytest.raises(ClaudeMcpError) as caught:
        await loader.load_server_config(
            SERVER.user_id,
            oauth_server,
            expected_config_revision=4,
            expected_credential_revision=2,
        )
    assert caught.value.code is ClaudeMcpErrorCode.CREDENTIAL_REQUIRED


def _oauth_credential(
    cipher: McpCredentialCipher,
    *,
    revision: int,
    token: str,
    expires_at: str,
) -> McpCredentialRecord:
    envelope = cipher.encrypt(
        json.dumps({"tokens": {"access_token": token}}).encode(),
        McpCredentialContext(
            user_id=SERVER.user_id,
            server_id=SERVER.id,
            kind="oauth",
            key_version=1,
        ),
    )
    return McpCredentialRecord(
        id="credential-id",
        server_id=SERVER.id,
        user_id=SERVER.user_id,
        kind="oauth",
        ciphertext=envelope.ciphertext,
        iv=envelope.iv,
        tag=envelope.tag,
        fingerprint=envelope.fingerprint,
        key_version=1,
        credential_revision=revision,
        expires_at=expires_at,
    )


@pytest.mark.asyncio
async def test_expired_oauth_view_returns_refreshed_authoritative_revision():
    cipher = McpCredentialCipher(key=b"k" * 32, key_version=1)
    oauth_server = replace(
        SERVER,
        auth_kind=McpAuthKind.OAUTH,
        credential_configured=True,
        credential_id="credential-id",
    )

    class RefreshingRepository(Repository):
        def __init__(self):
            super().__init__(oauth_server)
            self.credential = _oauth_credential(
                cipher,
                revision=2,
                token="expired-private",
                expires_at="2000-01-01T00:00:00+00:00",
            )

        async def get_credential(self, actor_id, server_id):
            assert actor_id == self.record.user_id
            assert server_id == self.record.id
            return self.credential

    repository = RefreshingRepository()

    class Refresher:
        async def discover_one(self, actor_id, server_id, **kwargs):
            assert (actor_id, server_id, kwargs) == (
                SERVER.user_id,
                SERVER.id,
                {"workspace_id": SERVER.workspace_id, "force": True},
            )
            repository.credential = _oauth_credential(
                cipher,
                revision=3,
                token="refreshed-private",
                expires_at=(datetime.now(timezone.utc) + timedelta(hours=1)).isoformat(),
            )
            repository.record = replace(repository.record, credential_revision=3)
            return type("DiscoveryResult", (), {"error": None})()

    loader = ManagedMcpRuntimeSnapshotLoader(
        repository,
        cipher,
        stdio_profiles=object(),
        max_servers=1,
        oauth_refresher=Refresher(),
    )
    subject = ClaudeMcpService(
        repository=repository,
        discovery=object(),
        oauth=object(),
        runtime_snapshot_loader=loader,
        mcp_apps_policy_provider=lambda: POLICY,
    )

    view = await subject.mcp_apps_connection_view(
        SERVER.user_id,
        SERVER.server_key,
        SERVER.workspace_id,
        expected_config_revision=4,
        expected_credential_revision=2,
        expected_policy_revision=7,
        ttl_seconds=30,
    )

    assert view.credential_revision == 3
    assert view.connection_profile["headers"]["Authorization"] == (
        "Bearer refreshed-private"
    )
    assert "expired-private" not in repr(view)
