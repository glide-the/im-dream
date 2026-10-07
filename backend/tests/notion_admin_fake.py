# [Sync] 2026-10-07: script frozen execution DTO replies and exclude internal execution JSON; no imitation of DB lease/CAS/fencing proofs.
# [Sync] 2026-10-07: expose the explicit fixture service-token provider so transport assertions use its configured value.
# [Input] Production AdminDataClient DTO transport and synthetic Notion domain values.
# [Output] Stateful provider-free Admin Notion boundary for Store and router contract tests.
# [Pos] Test harness only; exercises public DTO operations without SQL or a shadow Dream repository.
# [Sync] 2026-09-16: replace the retired Dream PostgreSQL Notion fake.
# [Sync] 2026-10-05: include real user-preferences DTO/capability reads for Calendar timezone contracts.
from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass, field
from uuid import UUID

import httpx

from services.admin_data import AdminDataClient, AdminDataConfig
from services.admin_data.notion_connector_data import (
    NOTION_CONNECTOR_OPERATIONS,
    NOTION_CONNECTOR_SCHEMA_REQUIREMENTS,
    NOTION_SYNC_RUN_OPERATIONS, NOTION_SYNC_RUN_SCHEMA_REQUIREMENTS,
    AdminNotionConnectorData,
)
from services.admin_data.preferences_data import PREFERENCES_OPERATIONS
from services.admin_data.workflow_data import WORKFLOW_SCHEMA_REQUIREMENTS
from services.admin_data.request_auth import (
    AdminRequestActor,
    AdminRequestAuth,
)
from notion.store import NotionConnectorStore


_NOW = "2026-09-16T00:00:00.123456Z"
NOTION_SERVICE_TOKEN = "synthetic-notion-service-token"


class _UnusedVerifier:
    def verify(self, *_args, **_kwargs):  # pragma: no cover - dependency is overridden
        raise AssertionError("Synthetic Notion routes must use the explicit actor fixture")


@dataclass
class StatefulNotionAdmin:
    config: AdminDataConfig
    user_id: str = "7"
    connectors: dict[str, dict] = field(default_factory=dict)
    resources: dict[str, list[dict]] = field(default_factory=dict)
    snapshots: dict[str, list[dict]] = field(default_factory=dict)
    thread_bindings: dict[str, str] = field(default_factory=dict)
    calls: list[tuple[str, dict, str | None]] = field(default_factory=list)
    _sequence: int = 1
    timezone: str | None = "UTC"
    service_token: str = NOTION_SERVICE_TOKEN
    # DTO scripts exercise Dream consumers, not Admin's PostgreSQL lease/fencing.
    sync_scripts: dict[str, list[dict]] = field(default_factory=dict)
    sync_runs: dict[str, dict] = field(default_factory=dict)
    execution_capability: bool = True

    def _uuid(self) -> str:
        value = str(UUID(int=self._sequence, version=4))
        self._sequence += 1
        return value

    def _connector(self, connector_id: str) -> dict | None:
        value = self.connectors.get(connector_id)
        if value is None:
            return None
        result = deepcopy(value)
        result["sources"] = deepcopy(self.resources.get(connector_id, []))
        result["config"].pop("snapshot_sync_execution", None)
        return result

    def _create_connector(self, value: dict) -> dict:
        connector_id = self._uuid()
        connector = {
            "id": connector_id,
            "user_id": self.user_id,
            "name": value["name"],
            "platform": value["platform"],
            "auth_status": "pending",
            "config": deepcopy(value.get("config") or {}),
            "current_snapshot_version": None,
            "current_source_revision": None,
            "current_sync_cursor": None,
            "last_synced_at": None,
            "created_at": _NOW,
            "updated_at": _NOW,
        }
        self.connectors[connector_id] = connector
        self.resources[connector_id] = []
        self.snapshots[connector_id] = []
        return self._connector(connector_id) or {}

    def _patch_connector(self, connector_id: str, patch: dict) -> dict:
        connector = self.connectors[connector_id]
        config_patch = patch.pop("config_patch", None)
        if isinstance(config_patch, dict):
            connector["config"] = {**connector["config"], **deepcopy(config_patch)}
        connector.update(deepcopy(patch))
        connector["updated_at"] = _NOW
        return self._connector(connector_id) or {}

    def _replace_resources(self, connector_id: str, value: dict) -> dict:
        resources: list[dict] = []
        for key, resource_type in (
            ("databases", "notion_database"),
            ("pages", "notion_page"),
        ):
            for item in value.get(key, []):
                resources.append(
                    {
                        "id": self._uuid(),
                        "connector_id": connector_id,
                        "resource_type": resource_type,
                        "external_id": item["external_id"],
                        "title": item["title"],
                        "metadata": deepcopy(item.get("metadata") or {}),
                        "sync_status": "pending",
                        "created_at": _NOW,
                        "updated_at": _NOW,
                    }
                )
        self.resources[connector_id] = resources
        connector = self.connectors[connector_id]
        connector["config"] = {
            **connector["config"],
            "selected_databases": [
                item["external_id"]
                for item in resources
                if item["resource_type"] == "notion_database"
            ],
            "selected_pages": [
                item["external_id"]
                for item in resources
                if item["resource_type"] == "notion_page"
            ],
        }
        if not resources:
            for key in ("current_snapshot_version", "current_source_revision", "current_sync_cursor", "last_synced_at"):
                connector[key] = None
        return self._connector(connector_id) or {}

    def _sync_reply(self, name: str, value: dict) -> dict:
        connector_id = value["connector_id"]
        scripted = self.sync_scripts.get(name, [])
        if scripted:
            return deepcopy(scripted.pop(0))
        policy = {"lease_seconds": 3000, "heartbeat_seconds": 1000, "renewal_budget_seconds": 1}
        status, snapshot = "claimed", None
        if name in ("notion.sync-run.request", "notion.sync-run.claim"):
            run = {"run_id": self._uuid(), "fence_epoch": 1, "service_client_id": self.config.service_client_id,
                "worker_id": value["worker_id"], "owner_user_id": self.user_id,
                "selection_revision": 1, "authorization_revision": 1, "policy_revision": 1,
                "started_at": _NOW, "heartbeat_at": _NOW, "lease_expires_at": "2026-09-16T01:00:00Z",
                "status": "running", "error_code": None}
            self.sync_runs[connector_id] = run
        else:
            run = deepcopy(self.sync_runs[connector_id])
            if name == "notion.sync-run.renew":
                status = "renewed"
            else:
                outcome = value["outcome"]
                status = run["status"] = outcome["status"]
                run["error_code"] = outcome.get("error_code")
                if status == "succeeded":
                    snapshot = self._save_snapshot(connector_id, outcome)
        return {"status": status, "connector": self._connector(connector_id), "run": run,
            "server_now": _NOW, "retry_at": None, "execution_policy": policy, "snapshot": snapshot}

    def _save_snapshot(self, connector_id: str, value: dict) -> dict:
        snapshot = deepcopy(value["snapshot"])
        metadata = snapshot["metadata"]
        connector = self.connectors[connector_id]
        connector.update(
            {
                "current_snapshot_version": metadata["snapshot_version"],
                "current_source_revision": metadata["source_revision"],
                "current_sync_cursor": metadata["sync_cursor"],
                "last_synced_at": metadata["fetched_at"],
                "updated_at": _NOW,
            }
        )
        synced = {
            (item["resource_type"], item["external_id"])
            for item in value.get("synced_resources", [])
        }
        for resource in self.resources.get(connector_id, []):
            if (resource["resource_type"], resource["external_id"]) in synced:
                resource["sync_status"] = "synced"
                resource["updated_at"] = _NOW
        record = {
            "id": self._uuid(),
            "connector_id": connector_id,
            "snapshot_version": metadata["snapshot_version"],
            "source_revision": metadata["source_revision"],
            "sync_cursor": metadata["sync_cursor"],
            "fetched_at": metadata["fetched_at"],
            "state": "snapshot_ready",
            "created_at": _NOW,
            "updated_at": _NOW,
            "snapshot": snapshot,
        }
        self.snapshots.setdefault(connector_id, []).append(record)
        return snapshot

    def _execute(self, name: str, value: dict) -> dict:
        if name.startswith("notion.sync-run."):
            return self._sync_reply(name, value)
        if name == "user-preferences.get":
            return {"preferences": {"voice_configs_json": None, "meta_prompt": None,
                "state_config_json": None, "selected_state": None, "timezone": self.timezone,
                "first_login_completed": 1, "updated_at": _NOW}}
        connector_id = str(value.get("connector_id") or "")
        if name == "notion.connector.create":
            return {"connector": self._create_connector(value)}
        if name == "notion.connector.list":
            return {"connectors": [self._connector(key) for key in self.connectors]}
        if name in {"notion.connector.get", "notion.sync-connector.get"}:
            return {"connector": self._connector(connector_id)}
        if name == "notion.connector.active":
            candidates = [self._connector(key) for key in self.connectors]
            return {"connector": candidates[-1] if candidates else None}
        if name in {"notion.connector.patch", "notion.sync-connector.patch"}:
            return {
                "connector": self._patch_connector(
                    connector_id, deepcopy(value["patch"])
                )
            }
        if name == "notion.auth-state.save":
            return {
                "connector": self._patch_connector(
                    connector_id,
                    {
                        "auth_status": value["auth_status"],
                        "config_patch": value.get("config_patch") or {},
                    },
                )
            }
        if name == "notion.connector.delete":
            deleted = connector_id in self.connectors
            self.connectors.pop(connector_id, None)
            self.resources.pop(connector_id, None)
            self.snapshots.pop(connector_id, None)
            self.thread_bindings = {
                thread: bound
                for thread, bound in self.thread_bindings.items()
                if bound != connector_id
            }
            return {"deleted": deleted}
        if name == "notion.resources.replace":
            return {"connector": self._replace_resources(connector_id, value)}
        if name in {"notion.resources.list", "notion.sync-resources.list"}:
            return {"resources": deepcopy(self.resources.get(connector_id, []))}
        if name == "notion.resource.delete":
            before = self.resources.get(connector_id, [])
            remaining = [item for item in before if item["id"] != value["resource_id"]]
            self.resources[connector_id] = remaining
            return {"deleted": len(remaining) != len(before)}
        if name in {"notion.snapshot.save", "notion.sync-snapshot.save"}:
            return {"snapshot": self._save_snapshot(connector_id, value)}
        if name == "notion.snapshot.current":
            records = self.snapshots.get(connector_id, [])
            return {"snapshot": deepcopy(records[-1]["snapshot"]) if records else None}
        if name == "notion.snapshot.get":
            record = next(
                (
                    item
                    for item in self.snapshots.get(connector_id, [])
                    if item["snapshot_version"] == value["snapshot_version"]
                ),
                None,
            )
            return {"snapshot": deepcopy(record["snapshot"]) if record else None}
        if name == "notion.snapshot.list":
            return {"snapshots": deepcopy(self.snapshots.get(connector_id, []))}
        if name == "notion.thread.attach":
            self.thread_bindings[value["thread_id"]] = connector_id
            return {"connector": self._connector(connector_id)}
        if name == "notion.thread.resolve":
            return {
                "connector": self._connector(
                    self.thread_bindings.get(value["thread_id"], "")
                )
            }
        if name == "notion.sync-candidates.list":
            return {
                "connectors": [
                    self._connector(key)
                    for key, connector in self.connectors.items()
                    if connector["auth_status"] == "authenticated"
                ]
            }
        raise AssertionError(f"Unexpected Notion operation: {name}")

    def handler(self, request: httpx.Request) -> httpx.Response:
        request_id = request.headers["x-request-id"]
        if request.url.path.endswith("/capabilities"):
            value = {
                "version": "1",
                "auth": {
                    "issuer": self.config.issuer,
                    "jwks_uri": self.config.jwks_uri,
                    "algorithm": "ES256",
                    "resource": self.config.resource,
                    "clients": {"browser": "dream-browser", "device": "dream-device"},
                    "scopes": ["dream:read", "dream:write"],
                    "delegations": [],
                },
                "schema_capabilities": [
                    item.model_dump() for item in {entry.capability: entry for entry in (*NOTION_CONNECTOR_SCHEMA_REQUIREMENTS, *WORKFLOW_SCHEMA_REQUIREMENTS,
                        *(NOTION_SYNC_RUN_SCHEMA_REQUIREMENTS if self.execution_capability else ()))}.values()
                ],
                "operations": [
                    item.capability.model_dump()
                    for item in (*NOTION_CONNECTOR_OPERATIONS, *PREFERENCES_OPERATIONS,
                        *(NOTION_SYNC_RUN_OPERATIONS if self.execution_capability else ()))
                ],
            }
        elif "/operations/" in request.url.path:
            name = request.url.path.rsplit("/", 1)[-1]
            body = json.loads(request.content)
            value_input = body["input"]
            access_token = request.headers.get("authorization")
            self.calls.append((name, deepcopy(value_input), access_token))
            if access_token == "Bearer other-notion-oauth-token" and name in {
                "notion.connector.get",
                "notion.connector.active",
                "notion.thread.resolve",
            }:
                value = {"connector": None}
            elif access_token == "Bearer other-notion-oauth-token" and name == "notion.connector.list":
                value = {"connectors": []}
            else:
                value = self._execute(name, value_input)
            if "__http_error__" in value:
                return httpx.Response(value.get("status", 409), json={"request_id": request_id,
                    "error": {"code": value["__http_error__"], "message": "Synthetic operation rejected"}})
        else:
            raise AssertionError(f"Unexpected Admin request: {request.url}")
        return httpx.Response(
            200,
            json={"request_id": request_id, "data": value},
        )


def build_notion_admin_boundary(*, user_id: str = "7"):
    config = AdminDataConfig(
        base_url="https://admin.example",
        issuer="https://admin.example/api/auth",
        resource="https://dream.example/api",
        service_client_id="dream-service",
        service_secret="s" * 32,
    )
    state = StatefulNotionAdmin(config=config, user_id=user_id)
    http = httpx.Client(transport=httpx.MockTransport(state.handler))
    client = AdminDataClient(
        config,
        client=http,
        operations=(*NOTION_CONNECTOR_OPERATIONS, *PREFERENCES_OPERATIONS, *NOTION_SYNC_RUN_OPERATIONS),
        service_token_provider=lambda: state.service_token,
    )
    owner = AdminRequestAuth(config, client=client, verifier=_UnusedVerifier())
    actor = AdminRequestActor(
        subject="notion-subject",
        canonical_user_id=user_id,
        client_id="dream-browser",
        scopes=frozenset({"dream:read", "dream:write"}),
        issued_at=100,
        expires_at=400,
        access_token="notion-oauth-token",
    )
    user_store = NotionConnectorStore(
        AdminNotionConnectorData(client),
        access_token=actor.access_token,
        expected_user_id=user_id,
    )
    background_store = NotionConnectorStore(
        AdminNotionConnectorData(client),
        background=True,
    )
    return owner, actor, state, user_store, background_store


__all__ = ["StatefulNotionAdmin", "build_notion_admin_boundary"]
