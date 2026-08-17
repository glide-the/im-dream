"""Durable Deck draft projection and explicit immutable content commits.

[Input] Existing mutable Deck/Voice/plugin-reference/binding rows and Admin schema capability.
[Output] Canonical snapshot hashes, diff previews, CAS commits, and read-only version history.
[Pos] Deck aggregate content-version application service.
[Sync] 2026-08-16: implement the CozeLoop-inspired draft -> preview -> commit lifecycle.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any, Mapping

try:
    from backend.models.deck_version import (
        DeckVersionChange,
        DeckVersionCommitRequest,
        DeckVersionCommitResponse,
        DeckVersionDetailResponse,
        DeckVersionHistoryResponse,
        DeckVersionMutationRequest,
        DeckVersionPreviewResponse,
        DeckVersionState,
        DeckVersionSummary,
    )
    from backend.schema.capabilities import DECK_CONTENT_VERSIONS_CAPABILITY
    from backend.services.deck.agent_type import agent_type_from_manifest
except ModuleNotFoundError:  # pragma: no cover - backend PYTHONPATH compatibility
    from models.deck_version import (
        DeckVersionChange,
        DeckVersionCommitRequest,
        DeckVersionCommitResponse,
        DeckVersionDetailResponse,
        DeckVersionHistoryResponse,
        DeckVersionMutationRequest,
        DeckVersionPreviewResponse,
        DeckVersionState,
        DeckVersionSummary,
    )
    from schema.capabilities import DECK_CONTENT_VERSIONS_CAPABILITY
    from services.deck.agent_type import agent_type_from_manifest


DECK_VERSION_CAPABILITY_MISSING = "DECK_VERSION_CAPABILITY_MISSING"
DECK_VERSION_ACCESS_DENIED = "DECK_VERSION_ACCESS_DENIED"
DECK_VERSION_CONFLICT = "DECK_VERSION_CONFLICT"
DECK_VERSION_NO_CHANGES = "DECK_VERSION_NO_CHANGES"


class DeckVersionCapabilityError(RuntimeError):
    code = DECK_VERSION_CAPABILITY_MISSING


class DeckVersionAccessError(PermissionError):
    code = DECK_VERSION_ACCESS_DENIED


class DeckVersionConflict(RuntimeError):
    code = DECK_VERSION_CONFLICT

    def __init__(self, *, draft_revision: int, latest_version: int | None) -> None:
        self.draft_revision = draft_revision
        self.latest_version = latest_version
        super().__init__("Deck draft changed. Refresh the preview before committing.")


class DeckVersionNoChanges(ValueError):
    code = DECK_VERSION_NO_CHANGES


def content_version_capability_available(db: Any) -> bool:
    """Read the Admin-owned feature receipt without issuing DDL."""

    try:
        row = db.execute(
            "SELECT version, contract_sha256 FROM drizzle.schema_capabilities "
            "WHERE capability = %s",
            (DECK_CONTENT_VERSIONS_CAPABILITY,),
        ).fetchone()
    except Exception:
        return False
    if row is None:
        return False
    contract_hash = str(row["contract_sha256"])
    return int(row["version"]) >= 1 and len(contract_hash) == 64


def advance_deck_draft_revision(db: Any, deck_id: str) -> int | None:
    """Advance the aggregate revision when the capability is present.

    The caller owns the transaction and must already hold the Deck row lock.
    Older expanded-but-not-yet-adopted deployments keep CRUD available and do
    not infer version facts.
    """

    if not content_version_capability_available(db):
        return None
    row = db.execute(
        """
        UPDATE decks
        SET draft_revision = draft_revision + 1,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = %s
        RETURNING draft_revision
        """,
        (deck_id,),
    ).fetchone()
    return int(row["draft_revision"]) if row is not None else None


def decorate_decks_with_content_version_state(db: Any, decks: list[dict[str, Any]]) -> None:
    """Add list-safe aggregate facts only when Admin proves the capability."""

    if not decks or not content_version_capability_available(db):
        for deck in decks:
            deck["deck_version_capability"] = False
        return
    for deck in decks:
        latest = int(deck.get("latest_version") or 0)
        draft_revision = int(deck.get("draft_revision") or 1)
        published_revision = int(deck.get("published_draft_revision") or 0)
        dirty = latest == 0 or draft_revision != published_revision
        deck.update(
            {
                "deck_version_capability": True,
                "deck_version": latest or None,
                "draft_revision": draft_revision,
                "deck_version_dirty": dirty,
                "deck_version_status": (
                    "unpublished" if latest == 0 else "draft" if dirty else "published"
                ),
                "next_deck_version": latest + 1,
            }
        )


def _json_value(value: Any) -> Any:
    if value is None or isinstance(value, (dict, list, bool, int, float)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return value
    return value


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _content_hash(snapshot: dict[str, object]) -> str:
    digest = hashlib.sha256(_canonical_json(snapshot).encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


class DeckContentVersionService:
    def __init__(self, db: Any) -> None:
        self.db = db

    def _require_capability(self) -> None:
        if not content_version_capability_available(self.db):
            raise DeckVersionCapabilityError()

    def _owned_deck(self, deck_id: str, actor_id: int, *, lock: bool = False) -> Any:
        suffix = " FOR UPDATE" if lock else ""
        row = self.db.execute(
            """
            SELECT id, name, name_zh, name_en, description, description_zh,
                   description_en, icon, color, enabled, order_index,
                   draft_revision, latest_version, published_draft_revision
            FROM decks
            WHERE id = %s AND owner_id = %s
            """ + suffix,
            (deck_id, actor_id),
        ).fetchone()
        if row is None:
            raise DeckVersionAccessError()
        return row

    @staticmethod
    def _state(deck: Mapping[str, Any]) -> DeckVersionState:
        latest_value = int(deck["latest_version"] or 0)
        latest = latest_value or None
        draft_revision = int(deck["draft_revision"])
        published_revision = int(deck["published_draft_revision"] or 0)
        dirty = latest is None or draft_revision != published_revision
        return DeckVersionState(
            deck_id=str(deck["id"]),
            draft_revision=draft_revision,
            latest_version=latest,
            published_draft_revision=published_revision,
            dirty=dirty,
            status="unpublished" if latest is None else "draft" if dirty else "published",
            next_version=(latest or 0) + 1,
        )

    def get_state(self, deck_id: str, actor_id: int) -> DeckVersionState:
        self._require_capability()
        return self._state(self._owned_deck(deck_id, actor_id))

    def _snapshot(self, deck: Mapping[str, Any]) -> dict[str, object]:
        deck_id = str(deck["id"])
        voice_rows = self.db.execute(
            """
            SELECT id, name, name_zh, name_en, system_prompt, icon, color,
                   enabled, order_index, memory_workspace_config
            FROM voices
            WHERE deck_id = %s
            ORDER BY order_index, created_at, id
            """,
            (deck_id,),
        ).fetchall()
        ref_rows = self.db.execute(
            """
            SELECT plugin_installation_id, package_spec, resolved_version,
                   artifact_digest, enabled, order_index
            FROM deck_claude_plugin_refs
            WHERE deck_id = %s
            ORDER BY order_index, plugin_installation_id
            """,
            (deck_id,),
        ).fetchall()
        binding = self.db.execute(
            """
            SELECT b.deck_plugin_id, b.deck_plugin_version, b.binding_revision,
                   r.manifest_json
            FROM deck_plugin_bindings AS b
            JOIN deck_plugin_releases AS r
              ON r.deck_plugin_id = b.deck_plugin_id
             AND r.deck_plugin_version = b.deck_plugin_version
            WHERE b.deck_id = %s AND b.status = 'active'
            ORDER BY b.binding_revision DESC
            LIMIT 1
            """,
            (deck_id,),
        ).fetchone()
        runtime_binding: dict[str, object] | None = None
        agent_type = "chat"
        if binding is not None:
            agent_type = agent_type_from_manifest(binding["manifest_json"]).value
            runtime_binding = {
                "deck_plugin_id": str(binding["deck_plugin_id"]),
                "deck_plugin_version": str(binding["deck_plugin_version"]),
                "binding_revision": int(binding["binding_revision"]),
            }
        return {
            "schema_version": "deck-content/v1",
            "deck": {
                key: deck[key]
                for key in (
                    "id", "name", "name_zh", "name_en", "description",
                    "description_zh", "description_en", "icon", "color",
                    "enabled", "order_index",
                )
            },
            "agent_type": agent_type,
            "agents": [
                {
                    "id": str(row["id"]),
                    "name": row["name"],
                    "name_zh": row["name_zh"],
                    "name_en": row["name_en"],
                    "system_prompt": row["system_prompt"],
                    "icon": row["icon"],
                    "color": row["color"],
                    "enabled": bool(row["enabled"]),
                    "order_index": row["order_index"],
                    "memory_workspace_config": _json_value(row["memory_workspace_config"]),
                }
                for row in voice_rows
            ],
            "claude_plugins": [
                {
                    "plugin_installation_id": str(row["plugin_installation_id"]),
                    "package_spec": row["package_spec"],
                    "resolved_version": row["resolved_version"],
                    "artifact_digest": row["artifact_digest"],
                    "enabled": bool(row["enabled"]),
                    "order_index": row["order_index"],
                }
                for row in ref_rows
            ],
            "runtime_binding": runtime_binding,
        }

    def _latest_snapshot(self, deck_id: str, latest_version: int | None) -> dict[str, object] | None:
        if latest_version is None:
            return None
        row = self.db.execute(
            "SELECT snapshot_json FROM deck_versions WHERE deck_id = %s AND version = %s",
            (deck_id, latest_version),
        ).fetchone()
        if row is None:
            raise DeckVersionConflict(draft_revision=1, latest_version=latest_version)
        snapshot = _json_value(row["snapshot_json"])
        if not isinstance(snapshot, dict):
            raise ValueError("Deck version snapshot is invalid")
        return snapshot

    @staticmethod
    def _diff(base: dict[str, object] | None, current: dict[str, object]) -> list[DeckVersionChange]:
        if base is None:
            changes = [
                DeckVersionChange(scope="deck", change_type="added", label="Deck 基础信息"),
                DeckVersionChange(scope="agent_type", change_type="added", label="Agent 类型"),
            ]
            if current.get("agents"):
                changes.append(DeckVersionChange(scope="agents", change_type="added", label="Agents"))
            if current.get("claude_plugins"):
                changes.append(DeckVersionChange(scope="claude_plugins", change_type="added", label="Claude 插件"))
            if current.get("runtime_binding"):
                changes.append(DeckVersionChange(scope="runtime_binding", change_type="added", label="运行绑定"))
            return changes

        changes: list[DeckVersionChange] = []
        base_deck = base.get("deck") if isinstance(base.get("deck"), dict) else {}
        current_deck = current.get("deck") if isinstance(current.get("deck"), dict) else {}
        deck_fields = sorted(
            key for key in set(base_deck) | set(current_deck)
            if base_deck.get(key) != current_deck.get(key)
        )
        if deck_fields:
            changes.append(DeckVersionChange(scope="deck", change_type="modified", label="Deck 基础信息", fields=deck_fields))
        if base.get("agent_type") != current.get("agent_type"):
            changes.append(DeckVersionChange(scope="agent_type", change_type="modified", label="Agent 类型", fields=["agent_type"]))
        for key, scope, label in (
            ("agents", "agents", "Agents"),
            ("claude_plugins", "claude_plugins", "Claude 插件"),
            ("runtime_binding", "runtime_binding", "运行绑定"),
        ):
            if base.get(key) != current.get(key):
                changes.append(DeckVersionChange(scope=scope, change_type="modified", label=label))
        return changes

    @staticmethod
    def _assert_expected(state: DeckVersionState, request: DeckVersionMutationRequest) -> None:
        if (
            request.expected_draft_revision != state.draft_revision
            or request.expected_base_version != state.latest_version
        ):
            raise DeckVersionConflict(
                draft_revision=state.draft_revision,
                latest_version=state.latest_version,
            )

    def preview(
        self,
        deck_id: str,
        actor_id: int,
        request: DeckVersionMutationRequest,
    ) -> DeckVersionPreviewResponse:
        self._require_capability()
        deck = self._owned_deck(deck_id, actor_id)
        state = self._state(deck)
        self._assert_expected(state, request)
        snapshot = self._snapshot(deck)
        base = self._latest_snapshot(deck_id, state.latest_version)
        changes = self._diff(base, snapshot)
        if not changes or (base is not None and _content_hash(base) == _content_hash(snapshot)):
            raise DeckVersionNoChanges("Deck draft has no content changes.")
        return DeckVersionPreviewResponse(
            **state.model_dump(),
            target_version=state.next_version,
            changes=changes,
            impact=[
                "新建 Thread/新运行可以选择该最新 Deck 版本。",
                "历史 Thread 不会自动升级。",
                "当前草稿在提交成功后与新版本一致。",
            ],
        )

    def commit(
        self,
        deck_id: str,
        actor_id: int,
        request: DeckVersionCommitRequest,
    ) -> DeckVersionCommitResponse:
        if getattr(self.db, "in_transaction", False):
            self.db.rollback()
        self.db.execute("BEGIN")
        try:
            self._require_capability()
            deck = self._owned_deck(deck_id, actor_id, lock=True)
            state = self._state(deck)
            self._assert_expected(state, request)
            snapshot = self._snapshot(deck)
            base = self._latest_snapshot(deck_id, state.latest_version)
            changes = self._diff(base, snapshot)
            snapshot_hash = _content_hash(snapshot)
            if not changes or (base is not None and _content_hash(base) == snapshot_hash):
                raise DeckVersionNoChanges("Deck draft has no content changes.")
            version_id = f"dcv_{uuid.uuid4().hex}"
            row = self.db.execute(
                """
                INSERT INTO deck_versions (
                    id, deck_id, version, base_version, source_draft_revision,
                    description, snapshot_json, content_hash, created_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING version, base_version, source_draft_revision,
                          description, content_hash, created_by, created_at
                """,
                (
                    version_id,
                    deck_id,
                    state.next_version,
                    state.latest_version,
                    state.draft_revision,
                    request.description.strip() if request.description else None,
                    _canonical_json(snapshot),
                    snapshot_hash,
                    actor_id,
                ),
            ).fetchone()
            self.db.execute(
                """
                UPDATE decks
                SET latest_version = %s,
                    published_draft_revision = draft_revision,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
                """,
                (state.next_version, deck_id),
            )
            updated = self._owned_deck(deck_id, actor_id)
            self.db.commit()
            assert row is not None
            return DeckVersionCommitResponse(
                deck_id=deck_id,
                version=self._summary(row, snapshot=snapshot),
                state=self._state(updated),
            )
        except Exception:
            self.db.rollback()
            raise

    @staticmethod
    def _summary(row: Mapping[str, Any], *, snapshot: dict[str, object] | None = None) -> DeckVersionSummary:
        runtime_version = None
        if snapshot is not None and isinstance(snapshot.get("runtime_binding"), dict):
            value = snapshot["runtime_binding"].get("deck_plugin_version")  # type: ignore[index]
            runtime_version = str(value) if value is not None else None
        return DeckVersionSummary(
            version=int(row["version"]),
            base_version=int(row["base_version"]) if row["base_version"] is not None else None,
            source_draft_revision=int(row["source_draft_revision"]),
            description=row["description"],
            content_hash=str(row["content_hash"]),
            created_by=int(row["created_by"]),
            created_at=row["created_at"],
            runtime_plugin_version=runtime_version,
        )

    def list_versions(self, deck_id: str, actor_id: int, *, limit: int = 50) -> DeckVersionHistoryResponse:
        self._require_capability()
        state = self._state(self._owned_deck(deck_id, actor_id))
        rows = self.db.execute(
            """
            SELECT version, base_version, source_draft_revision, description,
                   snapshot_json, content_hash, created_by, created_at
            FROM deck_versions
            WHERE deck_id = %s
            ORDER BY version DESC
            LIMIT %s
            """,
            (deck_id, limit),
        ).fetchall()
        versions = []
        for row in rows:
            snapshot = _json_value(row["snapshot_json"])
            versions.append(self._summary(row, snapshot=snapshot if isinstance(snapshot, dict) else None))
        return DeckVersionHistoryResponse(deck_id=deck_id, current=state, versions=versions)

    def get_version(self, deck_id: str, actor_id: int, version: int) -> DeckVersionDetailResponse:
        self._require_capability()
        self._owned_deck(deck_id, actor_id)
        row = self.db.execute(
            """
            SELECT version, base_version, source_draft_revision, description,
                   snapshot_json, content_hash, created_by, created_at
            FROM deck_versions
            WHERE deck_id = %s AND version = %s
            """,
            (deck_id, version),
        ).fetchone()
        if row is None:
            raise DeckVersionAccessError()
        snapshot = _json_value(row["snapshot_json"])
        if not isinstance(snapshot, dict):
            raise ValueError("Deck version snapshot is invalid")
        return DeckVersionDetailResponse(
            deck_id=deck_id,
            snapshot=snapshot,
            **self._summary(row, snapshot=snapshot).model_dump(),
        )


__all__ = [
    "DECK_VERSION_ACCESS_DENIED",
    "DECK_VERSION_CAPABILITY_MISSING",
    "DECK_VERSION_CONFLICT",
    "DECK_VERSION_NO_CHANGES",
    "DeckContentVersionService",
    "DeckVersionAccessError",
    "DeckVersionCapabilityError",
    "DeckVersionConflict",
    "DeckVersionNoChanges",
    "advance_deck_draft_revision",
    "content_version_capability_available",
    "decorate_decks_with_content_version_state",
]
