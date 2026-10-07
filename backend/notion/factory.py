# [Sync] 2026-10-07: share owned sync flow, enforce renewal completion budgets after cancellation, read strict accepted versions, and separate saved-selection errors.
# [Sync] 2026-10-06: Calendar reads selected canonical snapshots and binds today-only verification to version/credential context.
# [Input] Notion connector auth, operation, Admin DTO store, and sync helpers.
# [Output] Provide a compact facade for routes and Claude Agent workspace attach.
# [Pos] factory node in backend/notion
# [Sync] 2026-10-05: actor-owned Calendar metadata reads recheck authorization/credential context before returning without persistence.
# [Sync] 2026-07-04: initial Notion connector facade for auth, discovery, selection,
#                    snapshot sync, and workspace materialization.
# [Sync] 2026-07-05: add backend auth-session lifecycle tracking to avoid poll-induced
#                    state regression and maintain frontend-safe auth session state.
# [Sync] 2026-08-28: bind every connector operation to an actor-owned agentdata
#                    credential store, stage reauthorization, and project credentials per turn.
# [Sync] 2026-08-28: publish canonical snapshots to the same actor agentdata root,
#                    apply versioned sync-policy state, and make Chat materialization remote-I/O free.
# [Sync] 2026-08-28: publish index-only snapshots, mark only exact included
#                    resources synced, and persist cancellation as a retryable local failure.
# [Sync] 2026-08-29: preserve effective credentials after failed reauthorization
#                    and make an empty source selection a successful fail-closed clear.
# [Sync] 2026-09-16: inject OAuth/background Admin DTO persistence authorities.

"""Connector facade for the Notion resource connector backend."""
from __future__ import annotations

import asyncio
import hashlib
import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Optional
from uuid import uuid4

from services.admin_data.errors import AdminDataError

from . import auth, operations, store, sync
from .credentials import NotionCredentialProjection, NotionCredentialStore
from .errors import (
    NotionAuthRequiredError,
    NotionCLIUnavailableError,
    NotionConnectorNotFoundError,
    NotionCredentialError,
    NotionOperationError,
    NotionPermissionError,
    NotionSnapshotNotReadyError,
    NotionSyncBusyError,
    NotionSelectionSyncError,
)
from .snapshot_store import NotionSnapshotStore
from .sync_policy import (
    SYNC_POLICY_CONFIG_KEY,
    update_sync_policy as build_updated_sync_policy,
)


_SESSION_TTL_SECONDS = 15 * 60
_SESSION_POLL_IN_FLIGHT_SECONDS = 20
_NO_PENDING_TOKENS = (
    "no pending login session found",
    "authorization session already consumed",
)
_SESSION_VALID_STATUSES = {"running", "pending", "authenticated", "consumed", "expired", "failed"}
logger = logging.getLogger(__name__)
_REQUEST_PROTECTED_CONFIG_KEYS = frozenset(
    {
        "notion_home",
        "NOTION_HOME",
        "notion_api_token",
        "NOTION_API_TOKEN",
        "auth_session",
        "verification_url",
        "verification_code",
        "auth_error",
    }
)


def _mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_iso(value: Any) -> Optional[datetime]:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _normalize_session(raw: Any) -> dict[str, Any]:
    now = _utcnow_iso()
    session = {
        "auth_session_id": None,
        "auth_session_status": "pending",
        "auth_session_started_at": now,
        "auth_session_last_polled_at": None,
        "auth_session_poll_in_flight": False,
        "auth_session_expires_at": now,
    }
    session.update(_mapping(raw))
    if session["auth_session_status"] not in _SESSION_VALID_STATUSES:
        session["auth_session_status"] = "pending"
    if not session["auth_session_id"]:
        session["auth_session_id"] = None
    if isinstance(session["auth_session_poll_in_flight"], str):
        session["auth_session_poll_in_flight"] = session["auth_session_poll_in_flight"].strip().lower() in {"1", "true", "yes", "on"}
    else:
        session["auth_session_poll_in_flight"] = bool(session["auth_session_poll_in_flight"])
    return session


def _is_no_pending_message(detail: str) -> bool:
    low = (detail or "").lower()
    return any(token in low for token in _NO_PENDING_TOKENS)


def _safe_request_config(config: Optional[Mapping[str, Any]]) -> dict[str, Any]:
    """Drop every credential/session selector from browser-authored config."""

    return {
        str(key): value
        for key, value in _mapping(config).items()
        if str(key) not in _REQUEST_PROTECTED_CONFIG_KEYS
    }


def _build_auth_session() -> dict[str, Any]:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    return {
        "auth_session_id": uuid4().hex,
        "auth_session_status": "running",
        "auth_session_started_at": now.isoformat().replace("+00:00", "Z"),
        "auth_session_last_polled_at": None,
        "auth_session_poll_in_flight": False,
        "auth_session_expires_at": (now + timedelta(seconds=_SESSION_TTL_SECONDS)).isoformat().replace("+00:00", "Z"),
    }


def _session_expired(session: Mapping[str, Any]) -> bool:
    expires_at = _parse_iso(session.get("auth_session_expires_at"))
    if expires_at is None:
        return False
    return datetime.now(timezone.utc) >= expires_at


@dataclass
class NotionConnectorFacade:
    """Thin orchestration wrapper for a user-owned Notion connector."""

    user_id: int
    connector_store: store.NotionConnectorStore = field(repr=False)
    connector_id: Optional[str] = None
    credential_store: NotionCredentialStore = field(
        default_factory=NotionCredentialStore,
        repr=False,
    )
    snapshot_store: NotionSnapshotStore | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if self.snapshot_store is None:
            self.snapshot_store = NotionSnapshotStore(self.credential_store)

    def _resolve_connector(self, connector_id: Optional[str] = None) -> dict[str, Any]:
        resolved = connector_id or self.connector_id
        if resolved:
            connector = self.connector_store.get_connector(resolved, self.user_id)
            if connector is None:
                raise NotionConnectorNotFoundError(
                    f"Connector {resolved!r} not found for user_id={self.user_id}"
                )
            return connector
        active = self.connector_store.get_active_connector_for_user(self.user_id)
        if active is None:
            raise NotionConnectorNotFoundError(
                f"No Notion connector found for user_id={self.user_id}"
            )
        self.connector_id = str(active["id"])
        return active

    def _session(self, connector: Mapping[str, Any]) -> dict[str, Any]:
        return _normalize_session(_mapping(connector.get("config")).get("auth_session"))

    def _session_in_flight(self, session: Mapping[str, Any]) -> bool:
        if not session.get("auth_session_poll_in_flight"):
            return False
        last_polled = _parse_iso(session.get("auth_session_last_polled_at"))
        if last_polled is None:
            return False
        return (datetime.now(timezone.utc) - last_polled).total_seconds() < _SESSION_POLL_IN_FLIGHT_SECONDS

    def _session_has_effective_auth(self, session: Mapping[str, Any]) -> bool:
        """Preserve only an authorization known effective before reauth began."""

        return (
            str(session.get("auth_session_previous_status") or "")
            == "authenticated"
            and self.credential_store.has_credentials(self.user_id)
        )

    def _persist_auth_state(
        self,
        connector_id: str,
        *,
        auth_status: str,
        session: Mapping[str, Any],
        detail: Optional[str] = None,
        verification_url: Optional[str] = None,
        verification_code: Optional[str] = None,
        poll_interval_seconds: Optional[int] = None,
    ) -> dict[str, Any]:
        config_patch: dict[str, Any] = {
            "auth_session": dict(session),
        }
        if verification_url is not None:
            config_patch["verification_url"] = verification_url
        if verification_code is not None:
            config_patch["verification_code"] = verification_code
        if poll_interval_seconds is not None:
            config_patch["poll_interval_seconds"] = poll_interval_seconds
        if detail is not None:
            config_patch["auth_error"] = detail
        return self.connector_store.save_auth_state(
            connector_id,
            self.user_id,
            auth_status=auth_status,
            config_patch=config_patch,
            error_detail=detail,
        )

    def create_connector(
        self,
        name: str,
        platform: str = "notion",
        config: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        return self.connector_store.create_connector(
            self.user_id,
            name=name,
            platform=platform,
            config=_safe_request_config(config),
        )

    def list_connectors(self) -> list[dict[str, Any]]:
        return self.connector_store.list_connectors(self.user_id)

    def get_connector(self, connector_id: Optional[str] = None) -> dict[str, Any]:
        return self._resolve_connector(connector_id)

    def update_connector(self, updates: Mapping[str, Any], connector_id: Optional[str] = None) -> dict[str, Any]:
        connector = self._resolve_connector(connector_id)
        safe_updates = dict(updates)
        safe_updates.pop("auth_status", None)
        if "config" in safe_updates:
            safe_updates["config"] = _safe_request_config(
                safe_updates.get("config") if isinstance(safe_updates.get("config"), Mapping) else {}
            )
        return self.connector_store.update_connector(
            str(connector["id"]), self.user_id, safe_updates
        )

    def delete_connector(self, connector_id: Optional[str] = None) -> bool:
        connector = self._resolve_connector(connector_id)
        deleted = self.connector_store.delete_connector(
            str(connector["id"]), self.user_id
        )
        if deleted:
            self.credential_store.clear_user(self.user_id)
        return deleted

    def update_sync_policy(
        self,
        *,
        enabled: bool,
        interval_minutes: int,
        connector_id: Optional[str] = None,
    ) -> dict[str, Any]:
        connector = self._resolve_connector(connector_id)
        config = _mapping(connector.get("config"))
        policy = build_updated_sync_policy(
            config.get(SYNC_POLICY_CONFIG_KEY),
            enabled=enabled,
            interval_minutes=interval_minutes,
            last_synced_at=connector.get("last_synced_at"),
        )
        return self.connector_store.update_connector(
            str(connector["id"]),
            self.user_id,
            {"config": {SYNC_POLICY_CONFIG_KEY: policy}},
        )

    async def start_auth(self, connector_id: Optional[str] = None) -> dict[str, Any]:
        connector = self._resolve_connector(connector_id)
        session = _build_auth_session()
        session["auth_session_previous_status"] = str(
            connector.get("auth_status") or ""
        )
        auth_session_id = str(session["auth_session_id"])
        pending_home = self.credential_store.begin_auth(self.user_id, auth_session_id)
        try:
            result = await auth.start_login(pending_home)
        except Exception:
            self.credential_store.abort_auth(self.user_id, auth_session_id)
            raise
        session.update(
            {
                "auth_session_status": "pending",
                "auth_session_started_at": _utcnow_iso(),
                "auth_session_last_polled_at": None,
                "auth_session_poll_in_flight": False,
            }
        )
        updated = self._persist_auth_state(
            str(connector["id"]),
            auth_status="pending",
            session=session,
            detail="",
            verification_url=result.verification_url,
            verification_code=result.verification_code,
            poll_interval_seconds=result.poll_interval_seconds,
        )
        return {
            "connector": updated,
            "verificationUrl": result.verification_url,
            "verificationCode": result.verification_code,
            "pollIntervalSeconds": result.poll_interval_seconds,
            "auth_status": "pending",
        }

    async def poll_auth(self, connector_id: Optional[str] = None) -> dict[str, Any]:
        connector = self._resolve_connector(connector_id)
        session = self._session(connector)

        if session.get("auth_session_status") == "authenticated":
            return {
                "connector": connector,
                "auth_status": "authenticated",
                "status": "authenticated",
                "detail": connector.get("config", {}).get("auth_error") or "Session already authenticated.",
            }

        if _session_expired(session) and str(connector.get("auth_status") or "") != "authenticated":
            session["auth_session_status"] = "expired"
            auth_session_id = str(session.get("auth_session_id") or "")
            if auth_session_id:
                try:
                    self.credential_store.abort_auth(self.user_id, auth_session_id)
                except NotionCredentialError:
                    pass
            preserved_status = (
                "authenticated"
                if self._session_has_effective_auth(session)
                else "expired"
            )
            updated = self._persist_auth_state(
                str(connector["id"]),
                auth_status=preserved_status,
                session=session,
                detail="Auth session expired.",
            )
            return {
                "connector": updated,
                "auth_status": preserved_status,
                "status": "expired",
                "detail": "Auth session expired.",
            }

        if self._session_in_flight(session):
            return {
                "connector": connector,
                "auth_status": session.get("auth_session_status") or "pending",
                "status": session.get("auth_session_status") or "pending",
                "detail": "Authorization poll already in progress.",
            }

        session = dict(session)
        session["auth_session_poll_in_flight"] = True
        session["auth_session_last_polled_at"] = _utcnow_iso()
        saved = self._persist_auth_state(
            str(connector["id"]),
            auth_status=str(connector.get("auth_status") or "pending"),
            session=session,
            detail=_mapping(connector.get("config")).get("auth_error") or "",
        )

        try:
            auth_session_id = str(session.get("auth_session_id") or "")
            pending_home = self.credential_store.pending_home(
                self.user_id,
                auth_session_id,
            )
            poll_result = await auth.poll_login(pending_home)
        except Exception:
            session["auth_session_poll_in_flight"] = False
            self._persist_auth_state(
                str(connector["id"]),
                auth_status=str(saved.get("auth_status") or "pending"),
                session=session,
                detail="Notion authorization could not be completed. Please retry.",
            )
            raise

        session["auth_session_last_polled_at"] = _utcnow_iso()
        session["auth_session_poll_in_flight"] = False

        detail = poll_result.detail or ""
        auth_status = str(connector.get("auth_status") or "pending").strip().lower() or "pending"
        if poll_result.status == "authenticated":
            try:
                self.credential_store.promote_auth(
                    self.user_id,
                    str(session.get("auth_session_id") or ""),
                )
            except Exception:
                session["auth_session_status"] = "failed"
                preserved_status = (
                    "authenticated"
                    if self._session_has_effective_auth(session)
                    else "error"
                )
                self._persist_auth_state(
                    str(connector["id"]),
                    auth_status=preserved_status,
                    session=session,
                    detail="Notion authorization could not be saved. Please retry.",
                )
                raise NotionCredentialError(
                    "Notion authorization could not be saved. Please retry."
                )
            auth_status = "authenticated"
            session["auth_session_status"] = "authenticated"
            detail = detail or "authenticated"
            saved = self._persist_auth_state(
                str(connector["id"]),
                auth_status=auth_status,
                session=session,
                detail=detail,
            )
            return {
                "connector": saved,
                "auth_status": auth_status,
                "status": "authenticated",
                "detail": detail,
            }

        if poll_result.status == "consumed" or (
            poll_result.status == "pending" and _is_no_pending_message(detail)
        ):
            # 已消费/无可用会话时不回退到未认证
            if str(session.get("auth_session_status")) == "authenticated":
                auth_status = "authenticated"
            elif str(saved.get("auth_status") or "") == "authenticated":
                auth_status = "authenticated"
            elif self._session_has_effective_auth(session):
                auth_status = "authenticated"
            else:
                session["auth_session_status"] = "consumed"
                auth_status = "error"
            saved = self._persist_auth_state(
                str(connector["id"]),
                auth_status=auth_status,
                session=session,
                detail=detail or "No pending login session found.",
            )
            return {
                "connector": saved,
                "auth_status": auth_status,
                "status": auth_status if auth_status == "authenticated" else "error",
                "detail": detail or "No pending login session found.",
            }

        if poll_result.status == "pending":
            session["auth_session_status"] = session.get("auth_session_status") or "pending"
            if auth_status != "authenticated":
                auth_status = "pending"
            saved = self._persist_auth_state(
                str(connector["id"]),
                auth_status=auth_status,
                session=session,
                detail=detail or "No pending authorization yet.",
            )
            return {
                "connector": saved,
                "auth_status": auth_status,
                "status": poll_result.status,
                "detail": detail or "No pending authorization yet.",
            }

        if poll_result.status == "expired":
            session["auth_session_status"] = "expired"
            try:
                self.credential_store.abort_auth(
                    self.user_id,
                    str(session.get("auth_session_id") or ""),
                )
            except NotionCredentialError:
                pass
            auth_status = (
                "authenticated"
                if self._session_has_effective_auth(session)
                else "expired"
            )
            saved = self._persist_auth_state(
                str(connector["id"]),
                auth_status=auth_status,
                session=session,
                detail=detail or "Auth session expired.",
            )
            return {
                "connector": saved,
                "auth_status": auth_status,
                "status": "expired",
                "detail": detail or "Auth session expired.",
            }

        # Unknown auth states fail closed for Notion while the Agent turn stays isolated.
        session["auth_session_status"] = "failed"
        auth_status = (
            "authenticated"
            if self._session_has_effective_auth(session)
            else "error"
        )
        saved = self._persist_auth_state(
            str(connector["id"]),
            auth_status=auth_status,
            session=session,
            detail=detail or "Authentication unknown error.",
        )
        return {
            "connector": saved,
            "auth_status": auth_status,
            "status": "error",
            "detail": detail or "Authentication unknown error.",
        }

    async def verify_auth(self, connector_id: Optional[str] = None) -> dict[str, Any]:
        connector = self._resolve_connector(connector_id)
        notion_home = self.credential_store.effective_home(self.user_id)
        poll_result = await auth.verify_status(notion_home)
        session = self._session(connector)
        if poll_result.status == "authenticated":
            session["auth_session_status"] = "authenticated"
        updated = self._persist_auth_state(
            str(connector["id"]),
            auth_status=poll_result.status,
            session=session,
            detail=poll_result.detail or "",
        )
        return {
            "connector": updated,
            "auth_status": poll_result.status,
            "status": poll_result.status,
            "detail": poll_result.detail,
        }

    async def list_databases(self, connector_id: Optional[str] = None, query: Optional[str] = None) -> list[dict[str, Any]]:
        connector = self._resolve_connector(connector_id)
        selected_ids = {
            str(resource.get("external_id") or "")
            for resource in self.connector_store.list_connector_resources(str(connector["id"]), self.user_id)
            if resource.get("resource_type") == "notion_database"
        }
        notion_home = self.credential_store.effective_home(self.user_id)
        records = await operations.discover_databases(notion_home, query=query)
        for record in records:
            record["selected"] = record.get("database_id") in selected_ids
        return records

    async def list_pages(self, connector_id: Optional[str] = None, query: Optional[str] = None) -> list[dict[str, Any]]:
        connector = self._resolve_connector(connector_id)
        selected_ids = {
            str(resource.get("external_id") or "")
            for resource in self.connector_store.list_connector_resources(str(connector["id"]), self.user_id)
            if resource.get("resource_type") == "notion_page"
        }
        notion_home = self.credential_store.effective_home(self.user_id)
        records = await operations.discover_pages(notion_home, query=query)
        for record in records:
            record["selected"] = record.get("page_id") in selected_ids
        return records

    async def today_pages(self, date_key: str, time_zone: str, *, now: datetime | None = None,
                          validate_remote: bool = False, snapshot_version: str | None = None) -> dict:
        from .today import NotionTodayError, api_version, day_context, read_documents, snapshot_records, timestamp
        from .sync import filter_snapshot_for_connector

        connector = self._resolve_connector()
        if connector.get("auth_status") != "authenticated":
            code = "NOTION_AUTH_PENDING" if connector.get("auth_status") in {"pending", "running"} else "NOTION_AUTH_EXPIRED"
            raise NotionTodayError(code, 409 if code == "NOTION_AUTH_PENDING" else 401)
        context = day_context(time_zone, date_key, now or datetime.now(timezone.utc))
        before = self._credential_identity()
        home = self.credential_store.effective_home(self.user_id)
        assert self.snapshot_store is not None
        source = await asyncio.to_thread(self._accepted_snapshot, connector)
        version = _mapping(_mapping(source).get("metadata")).get("snapshot_version")
        if validate_remote and snapshot_version != version:
            raise NotionTodayError("NOTION_SNAPSHOT_CHANGED", 409)
        selected = filter_snapshot_for_connector(source, connector) if source is not None else None
        records, _ = snapshot_records(selected)
        start, end = timestamp(context["intervalStart"]), timestamp(context["intervalEnd"])
        needs_remote = validate_remote and date_key == context["todayKey"] and any(
            (edited := timestamp(raw.get("last_edited_time"))) is not None and start <= edited < end
            for raw in records.values())
        client = operations.NotionOperationClient(home, api_version=api_version()) if needs_remote else None
        result = await read_documents(client, str(connector["id"]), context, selected)
        current = self._resolve_connector()
        after = self._credential_identity()
        def scope(value):
            return sorted((str(item.get("resource_type")), str(item.get("external_id")))
                          for item in value.get("sources") or [])
        if (current.get("auth_status") != "authenticated"
                or current.get("updated_at") != connector.get("updated_at") or scope(current) != scope(connector)
                or before != after):
            raise NotionTodayError("NOTION_CONTEXT_CHANGED", 409)
        latest = await asyncio.to_thread(self._accepted_snapshot, current)
        if _mapping(_mapping(latest).get("metadata")).get("snapshot_version") != version:
            raise NotionTodayError("NOTION_SNAPSHOT_CHANGED", 409)
        final_connector = self._resolve_connector()
        final_credential = self._credential_identity()
        if (self._read_context(final_connector) != self._read_context(connector)
                or before != final_credential):
            raise NotionTodayError("NOTION_CONTEXT_CHANGED", 409)
        if self._accepted_identity(final_connector) != self._accepted_identity(connector):
            raise NotionTodayError("NOTION_SNAPSHOT_CHANGED", 409)
        after_context = day_context(time_zone, date_key, now or datetime.now(timezone.utc))
        if after_context["todayKey"] != context["todayKey"]:
            raise NotionTodayError("NOTION_DATE_CONTEXT_CHANGED", 409, context=after_context)
        return result

    def list_selected_resources(self, connector_id: Optional[str] = None) -> list[dict[str, Any]]:
        connector = self._resolve_connector(connector_id)
        return self.connector_store.list_connector_resources(str(connector["id"]), self.user_id)

    def delete_selected_resource(
        self,
        resource_id: str,
        connector_id: Optional[str] = None,
    ) -> bool:
        connector = self._resolve_connector(connector_id)
        return self.connector_store.delete_connector_resource(
            str(connector["id"]), self.user_id, resource_id
        )

    async def select_resources(
        self,
        databases: Iterable[Mapping[str, Any]],
        pages: Iterable[Mapping[str, Any]],
        connector_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> dict[str, Any]:
        connector = self._resolve_connector(connector_id)
        selected_databases = [dict(item) for item in databases]
        selected_pages = [dict(item) for item in pages]
        selection = self.connector_store.replace_connector_resources(
            str(connector["id"]),
            self.user_id,
            selected_databases,
            selected_pages,
        )
        if not selected_databases and not selected_pages:
            connector_key = str(connector["id"])
            assert self.snapshot_store is not None
            self.snapshot_store.clear_connector(self.user_id, connector_key)
            cleared_connector = selection["connector"]
            return {
                "connector": cleared_connector,
                "snapshot": None,
                "snapshotIdentity": None,
                "databaseCount": 0,
                "pageCount": 0,
                "synced": False,
            }
        try:
            return await self.sync(connector_id=str(connector["id"]), workspace_id=workspace_id)
        except Exception as exc:
            raise NotionSelectionSyncError(exc) from exc

    def _credential_identity(self):
        from .credentials import NOTION_AUTH_FILENAME, _read_private_file
        path = self.credential_store.effective_home(self.user_id) / NOTION_AUTH_FILENAME
        payload = _read_private_file(path, max_bytes=self.credential_store.settings.max_credential_file_bytes)
        if payload is None:
            raise NotionCredentialError("Notion authorization is required.")
        info = path.stat()
        # effective_home hardens permissions on every read; chmod changes ctime even
        # when authorization bytes are identical. Bind content plus replacement/mtime
        # identity, without exporting either credentials or their digest.
        return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, hashlib.sha256(payload).digest())

    @staticmethod
    def _read_context(connector):
        return (connector.get("id"), connector.get("user_id"), connector.get("platform"),
            connector.get("auth_status"), connector.get("updated_at"),
            tuple(sorted((item.get("resource_type"), item.get("external_id")) for item in connector.get("sources") or [])))

    @staticmethod
    def _accepted_identity(connector):
        return tuple(connector.get(key) for key in ("current_snapshot_version",
            "current_source_revision", "current_sync_cursor", "last_synced_at"))

    def _accepted_snapshot(self, connector):
        if connector.get("auth_status") != "authenticated":
            raise NotionAuthRequiredError("Notion authorization is required.")
        assert self.snapshot_store is not None
        if not connector.get("current_snapshot_version"):
            return None
        cached = self.snapshot_store.load_accepted(self.user_id, connector)
        if cached is not None:
            return cached
        snapshot = self.connector_store.get_current_snapshot(str(connector["id"]), str(connector["id"]), self.user_id)
        if snapshot is None:
            raise NotionSnapshotNotReadyError("Accepted Notion snapshot is unavailable.")
        return self.snapshot_store.cache_accepted(self.user_id, connector, snapshot)

    async def sync(self, connector_id: Optional[str] = None, workspace_id: Optional[str] = None) -> dict[str, Any]:
        del workspace_id
        connector = await asyncio.to_thread(self._resolve_connector, connector_id)
        connector_key = str(connector["id"])
        claim_request = asyncio.create_task(asyncio.to_thread(
            self.connector_store.begin_sync_run, connector_key, self.user_id))
        try:
            claimed = await asyncio.shield(claim_request)
        except asyncio.CancelledError:
            # A dispatched claim may still commit; await its finite transport and leave
            # any resulting lease to Admin instead of issuing an unconfirmed finish.
            await asyncio.gather(claim_request, return_exceptions=True)
            raise
        if claimed.status == "busy":
            if self.connector_store.background:
                return {"connector": self.connector_store._project_connector(claimed.connector), "synced": False}
            delay = None
            if claimed.retry_at is not None:
                delay = math.ceil(max(0, (datetime.fromisoformat(claimed.retry_at.replace("Z", "+00:00"))
                    - datetime.fromisoformat(claimed.server_now.replace("Z", "+00:00"))).total_seconds()))
                if delay > 9_007_199_254_740_991:
                    delay = None
            raise NotionSyncBusyError(delay)
        if claimed.status == "not_due":
            return {"connector": self.connector_store._project_connector(claimed.connector), "synced": False}
        state = {"run": claimed.run, "policy": claimed.execution_policy, "lost": False}
        pending_admin: list[asyncio.Task] = []
        renewal_attempts: list[dict] = []
        stopped = asyncio.Event()
        builder = heartbeat = None
        terminal_started = False

        async def finish(outcome):
            request = asyncio.create_task(asyncio.to_thread(
                self.connector_store.finish_sync_run, connector_key, state["run"], outcome))
            pending_admin.append(request)
            # Keep the finite transport/receipt request owned when its waiter is cancelled.
            return await asyncio.shield(request)

        async def renew():
            loop = asyncio.get_running_loop()
            attempt = {"deadline": loop.time() + state["policy"].renewal_budget_seconds, "completed_at": None}
            renewal_attempts.append(attempt)
            async def dispatch():
                try:
                    return await asyncio.to_thread(self.connector_store.renew_sync_run, connector_key, state["run"])
                finally:
                    attempt["completed_at"] = loop.time()
            request = asyncio.create_task(dispatch())
            pending_admin.append(request)
            done, _ = await asyncio.wait({request}, timeout=state["policy"].renewal_budget_seconds)
            if not done or attempt["completed_at"] >= attempt["deadline"]:
                state["lost"] = True
                raise AdminDataError("NOTION_SYNC_RENEWAL_TIMEOUT", 503, outcome_unknown=True)
            try:
                response = request.result()
            except Exception:
                state["lost"] = True
                raise
            state["run"], state["policy"] = response.run, response.execution_policy

        async def heartbeat_loop():
            while True:
                try:
                    await asyncio.wait_for(stopped.wait(), timeout=state["policy"].heartbeat_seconds)
                    return
                except TimeoutError:
                    await renew()

        async def stop_owned_work():
            stopped.set()
            if builder is not None and not builder.done():
                builder.cancel()
            if heartbeat is not None and not heartbeat.done():
                heartbeat.cancel()
            await asyncio.gather(*(task for task in (builder, heartbeat) if task is not None), return_exceptions=True)
            # Cancelling an async waiter does not cancel a dispatched synchronous HTTP write.
            results = await asyncio.gather(*pending_admin, return_exceptions=True)
            if (any(isinstance(result, BaseException) for result in results)
                or any(attempt["completed_at"] is None or attempt["completed_at"] >= attempt["deadline"]
                    for attempt in renewal_attempts)):
                state["lost"] = True

        try:
            await renew()  # A recovered old claim receipt is not proof of a current lease.
            connector = self.connector_store._project_connector(claimed.connector, requested_user_id=self.user_id)
            sources = connector["sources"]
            before = self._credential_identity()
            ops = operations.NotionOperationClient(self.credential_store.effective_home(self.user_id))
            builder = asyncio.create_task(sync.build_canonical_snapshot(connector=connector,
                selected_resources=sources, workspace_id=connector_key, operations=ops))
            heartbeat = asyncio.create_task(heartbeat_loop())
            done, _ = await asyncio.wait({builder, heartbeat}, return_when=asyncio.FIRST_COMPLETED)
            if heartbeat in done:
                state["lost"] = True
                heartbeat.result()
                raise AdminDataError("NOTION_SYNC_RUN_INVALID", 409)
            snapshot = builder.result()
            stopped.set()
            await heartbeat
            if self._credential_identity() != before:
                state["lost"] = True
                raise NotionCredentialError("Notion authorization changed during synchronization.")
            terminal_started = True
            accepted = await finish({
                "status": "succeeded", "workspace_id": connector_key, "snapshot": snapshot,
                "synced_resources": [{"resource_type": item["resource_type"], "external_id": item["external_id"]} for item in sources]})
        except BaseException as exc:
            await stop_owned_work()
            if not terminal_started and not state["lost"]:
                terminal_started = True
                outcome = ({"status": "cancelled", "error_code": "NOTION_SYNC_CANCELLED"} if isinstance(exc, asyncio.CancelledError)
                    else {"status": "failed", "error_code": "NOTION_UPSTREAM_UNAVAILABLE" if isinstance(exc, NotionOperationError) else "NOTION_SYNC_FAILED"})
                try:
                    await finish(outcome)
                except Exception:
                    logger.warning("Notion terminal outcome could not be confirmed safely")
            raise
        current_connector = self.connector_store._project_connector(accepted.connector, requested_user_id=self.user_id)
        saved_snapshot = accepted.snapshot.model_dump(mode="json")
        assert self.snapshot_store is not None
        try:
            self.snapshot_store.cache_accepted(self.user_id, current_connector, saved_snapshot)
        except (OSError, NotionSnapshotNotReadyError, NotionCredentialError):
            # The Admin success is durable; cache failures must not rewrite it to failed.
            logger.warning("Accepted Notion snapshot cache will require read recovery")
        return {"connector": current_connector, "snapshot": saved_snapshot,
            "snapshotIdentity": saved_snapshot["identity"], "databaseCount": len(saved_snapshot["databases"]),
            "pageCount": len(saved_snapshot["index"]), "synced": True}

    def get_current_snapshot(
        self,
        connector_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        connector = self._resolve_connector(connector_id)
        del workspace_id
        assert self.snapshot_store is not None
        before = self._credential_identity()
        snapshot = self._accepted_snapshot(connector)
        current = self._resolve_connector(str(connector["id"]))
        if (self._read_context(current) != self._read_context(connector)
            or self._accepted_identity(current) != self._accepted_identity(connector)
            or self._credential_identity() != before):
            raise NotionSnapshotNotReadyError("Notion snapshot context changed. Refresh and retry.")
        return snapshot

    def materialize_workspace(
        self,
        workspace_path: Path,
        connector_id: Optional[str] = None,
        workspace_id: Optional[str] = None,
    ) -> None:
        del workspace_id
        assert self.snapshot_store is not None
        try:
            connector = self._resolve_connector(connector_id)
            before = self._credential_identity()
            snapshot = self._accepted_snapshot(connector)
            self.snapshot_store.project_thread(self.user_id, connector, workspace_path, snapshot=snapshot)
            current = self._resolve_connector(str(connector["id"]))
            if (self._read_context(current) != self._read_context(connector)
                or self._accepted_identity(current) != self._accepted_identity(connector)
                or self._credential_identity() != before):
                raise NotionSnapshotNotReadyError("Notion projection context changed. Retry the turn.")
        except Exception:
            self.snapshot_store.clear_thread(workspace_path)
            raise

    def project_runtime_credentials(
        self,
        workspace_path: Path,
        connector_id: Optional[str] = None,
    ) -> NotionCredentialProjection:
        """Deliver the current actor credential snapshot to one Agent thread."""

        self._resolve_connector(connector_id)
        return self.credential_store.project_thread(self.user_id, workspace_path)


def build_notion_facade(
    user_id: int,
    connector_id: Optional[str] = None,
    *,
    credential_store: NotionCredentialStore | None = None,
    connector_store: store.NotionConnectorStore | None = None,
) -> NotionConnectorFacade:
    """Convenience constructor for router/service callers."""

    resolved_store = credential_store or NotionCredentialStore()
    return NotionConnectorFacade(
        user_id=user_id,
        connector_id=connector_id,
        connector_store=connector_store or store.default_store(),
        credential_store=resolved_store,
        snapshot_store=NotionSnapshotStore(resolved_store),
    )
