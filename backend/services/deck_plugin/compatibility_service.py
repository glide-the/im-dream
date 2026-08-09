"""Server-authoritative Deck Plugin compatibility and expansion boundaries."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import inspect
import json
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

try:
    from backend.models.deck_plugin import (
        CapabilityDiff,
        CompatibilityCheck,
        CompatibilityResult,
        DeckPluginInstallation,
        DeckPluginManifestV1,
        DeckPluginReleaseStatus,
        DeckRuntimePluginLock,
        InstallationStatus,
    )
    from backend.services.deck_plugin.capability_evaluator import (
        compute_effective_capabilities,
    )
    from backend.services.deck_plugin.installation_service import Scope
except ModuleNotFoundError:  # Support the backend directory on PYTHONPATH.
    from models.deck_plugin import (
        CapabilityDiff,
        CompatibilityCheck,
        CompatibilityResult,
        DeckPluginInstallation,
        DeckPluginManifestV1,
        DeckPluginReleaseStatus,
        DeckRuntimePluginLock,
        InstallationStatus,
    )
    from services.deck_plugin.capability_evaluator import (
        compute_effective_capabilities,
    )
    from services.deck_plugin.installation_service import Scope


DECK_PLUGIN_UNAVAILABLE = "DECK_PLUGIN_UNAVAILABLE"
DECK_HOST_INCOMPATIBLE = "DECK_HOST_INCOMPATIBLE"
CLAUDE_AGENT_INCOMPATIBLE = "CLAUDE_AGENT_INCOMPATIBLE"
STORY_SCHEMA_INCOMPATIBLE = "STORY_SCHEMA_INCOMPATIBLE"
DECK_RUNTIME_CONFIG_INCOMPATIBLE = "DECK_RUNTIME_CONFIG_INCOMPATIBLE"
RUNTIME_PLUGIN_UNRESOLVED = "RUNTIME_PLUGIN_UNRESOLVED"
WORKFLOW_PERMISSION_DENIED = "WORKFLOW_PERMISSION_DENIED"
RUNTIME_PLUGIN_NOT_READY = "RUNTIME_PLUGIN_NOT_READY"
CAPABILITY_EXPANSION_APPROVAL_REQUIRED = (
    "DECK_PLUGIN_UPGRADE_APPROVAL_REQUIRED"
)
CAPABILITY_APPROVAL_DENIED = "CAPABILITY_APPROVAL_DENIED"
CAPABILITY_APPROVAL_INVALID = "CAPABILITY_APPROVAL_INVALID"

_MUTABLE_INSTALLATION_COLUMNS = frozenset(
    {
        "approved_capabilities_json",
        "last_error_code",
        "last_error_summary",
        "pending_capabilities_json",
        "pending_version",
        "status",
    }
)


RECOVERY_ACTIONS = {
    CompatibilityCheck.RELEASE_AVAILABLE: (
        "select_available_release_or_complete_installation"
    ),
    CompatibilityCheck.DECK_HOST_COMPATIBLE: "upgrade_deck_host",
    CompatibilityCheck.CLAUDE_AGENT_COMPATIBLE: (
        "select_compatible_claude_agent_runtime"
    ),
    CompatibilityCheck.STORY_SCHEMA_COMPATIBLE: "select_compatible_story_schema",
    CompatibilityCheck.DECK_RUNTIME_CONFIG_COMPATIBLE: (
        "select_compatible_deck_runtime_snapshot"
    ),
    CompatibilityCheck.RUNTIME_PLUGIN_RESOLVED: "regenerate_runtime_plugin_lock",
    CompatibilityCheck.WORKFLOW_PERMISSION: "request_required_capability_grants",
    CompatibilityCheck.RUNTIME_PLUGIN_READY: "materialize_required_runtime_plugins",
}


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class RuntimeContext(_StrictModel):
    """Server-resolved compatibility inputs; intentionally contains no versions.

    Version/schema comparisons happen in their owning services. This context only
    carries their authoritative verdicts so callers cannot replace server policy
    with client-side string comparison.
    """

    deck_host_compatible: bool
    claude_agent_compatible: bool
    story_schema_compatible: bool
    deck_runtime_config_compatible: bool
    deck_runtime_snapshot_policy: set[str]
    user_and_workspace_grants: set[str]
    claude_agent_runtime_supported: set[str]
    materialized_runtime_plugin_ids: set[str]
    loadable_runtime_plugin_ids: set[str]
    deprecated_release_allowed_by_policy: bool = False
    known_capabilities: set[str] | None = None

    @field_validator(
        "deck_runtime_snapshot_policy",
        "user_and_workspace_grants",
        "claude_agent_runtime_supported",
        "materialized_runtime_plugin_ids",
        "loadable_runtime_plugin_ids",
        "known_capabilities",
    )
    @classmethod
    def names_are_non_blank(cls, value: set[str] | None) -> set[str] | None:
        if value is not None and any(not item.strip() for item in value):
            raise ValueError("server-resolved names must not be blank")
        return value


class CompatibilityServiceError(ValueError):
    """Safe, structured error for capability approval operations."""

    def __init__(self, code: str, summary: str) -> None:
        super().__init__(summary)
        self.code = code
        self.summary = summary

    def to_dict(self) -> dict[str, dict[str, str]]:
        return {"error": {"code": self.code, "summary": self.summary}}


AdministratorAuthorizer = Callable[[str], bool | Awaitable[bool]]


class CompatibilityService:
    """Evaluate the fixed eight-step compatibility chain against server state."""

    def __init__(
        self,
        db: Any,
        *,
        administrator_authorizer: AdministratorAuthorizer | None = None,
    ) -> None:
        self.db = db
        self._administrator_authorizer = (
            administrator_authorizer or (lambda _actor: False)
        )

    async def check_compatibility(
        self,
        deck_plugin_id: str,
        deck_plugin_version: str,
        scope: Scope,
        runtime_context: RuntimeContext,
    ) -> CompatibilityResult:
        """Run all checks in fixed order and stop at the first failure."""

        release = self.db.execute(
            """
            SELECT status, manifest_json, manifest_hash
            FROM deck_plugin_releases
            WHERE deck_plugin_id = %s AND deck_plugin_version = %s
            """,
            (deck_plugin_id, deck_plugin_version),
        ).fetchone()
        installation = self.db.execute(
            """
            SELECT * FROM deck_plugin_installations
            WHERE scope_type = %s AND scope_id = %s AND deck_plugin_id = %s
            """,
            (scope.scope_type, scope.scope_id, deck_plugin_id),
        ).fetchone()
        manifest = self._available_manifest(
            release,
            installation,
            deck_plugin_id,
            deck_plugin_version,
            runtime_context.deprecated_release_allowed_by_policy,
        )
        if manifest is None:
            return self._failure(
                CompatibilityCheck.RELEASE_AVAILABLE,
                DECK_PLUGIN_UNAVAILABLE,
            )
        assert installation is not None

        if not runtime_context.deck_host_compatible:
            return self._failure(
                CompatibilityCheck.DECK_HOST_COMPATIBLE,
                DECK_HOST_INCOMPATIBLE,
            )
        if not runtime_context.claude_agent_compatible:
            return self._failure(
                CompatibilityCheck.CLAUDE_AGENT_COMPATIBLE,
                CLAUDE_AGENT_INCOMPATIBLE,
            )
        if not runtime_context.story_schema_compatible:
            return self._failure(
                CompatibilityCheck.STORY_SCHEMA_COMPATIBLE,
                STORY_SCHEMA_INCOMPATIBLE,
            )
        if not runtime_context.deck_runtime_config_compatible:
            return self._failure(
                CompatibilityCheck.DECK_RUNTIME_CONFIG_COMPATIBLE,
                DECK_RUNTIME_CONFIG_INCOMPATIBLE,
            )

        runtime_lock = self._resolved_runtime_lock(
            release,
            manifest,
            deck_plugin_id,
            deck_plugin_version,
        )
        if runtime_lock is None:
            return self._failure(
                CompatibilityCheck.RUNTIME_PLUGIN_RESOLVED,
                RUNTIME_PLUGIN_UNRESOLVED,
            )

        approved = self._json_set(installation["approved_capabilities_json"])
        effective = compute_effective_capabilities(
            set(manifest.capabilities),
            approved,
            runtime_context.deck_runtime_snapshot_policy,
            runtime_context.user_and_workspace_grants,
            runtime_context.claude_agent_runtime_supported,
            known_capabilities=runtime_context.known_capabilities,
        )
        if not self._required_capabilities(manifest).issubset(effective):
            return self._failure(
                CompatibilityCheck.WORKFLOW_PERMISSION,
                WORKFLOW_PERMISSION_DENIED,
            )

        required_plugins = {
            plugin.claude_code_plugin_id
            for plugin in manifest.runtime.claude_code_plugins
            if plugin.required
        }
        if not required_plugins.issubset(
            runtime_context.materialized_runtime_plugin_ids
        ) or not required_plugins.issubset(
            runtime_context.loadable_runtime_plugin_ids
        ):
            return self._failure(
                CompatibilityCheck.RUNTIME_PLUGIN_READY,
                RUNTIME_PLUGIN_NOT_READY,
            )

        return CompatibilityResult(
            passed=True,
            effective_capabilities=sorted(effective),
        )

    async def check_capability_expansion(
        self,
        installation_id: str,
        target_manifest: DeckPluginManifestV1,
    ) -> CapabilityDiff:
        """Stage capability expansion for explicit administrator approval."""

        installation = self._installation_row(installation_id)
        if target_manifest.deck_plugin_id != installation["deck_plugin_id"]:
            raise CompatibilityServiceError(
                CAPABILITY_APPROVAL_INVALID,
                "target release does not match the installation",
            )
        approved = self._json_set(installation["approved_capabilities_json"])
        target = set(target_manifest.capabilities)
        diff = CapabilityDiff(
            added=sorted(target - approved),
            removed=sorted(approved - target),
            requires_approval=bool(target - approved),
        )
        if not diff.requires_approval:
            return diff
        if installation["status"] not in {
            InstallationStatus.READY.value,
            InstallationStatus.UPGRADE_PENDING.value,
        }:
            raise CompatibilityServiceError(
                CAPABILITY_APPROVAL_INVALID,
                "installation is not eligible for capability expansion",
            )

        pending_json = json.dumps(sorted(target))
        if installation["status"] == InstallationStatus.UPGRADE_PENDING.value:
            if (
                installation["pending_version"] != target_manifest.deck_plugin_version
                or installation["pending_capabilities_json"] != pending_json
            ):
                raise CompatibilityServiceError(
                    CAPABILITY_APPROVAL_INVALID,
                    "another capability expansion is already pending",
                )
            return diff

        self._update_installation(
            installation,
            status=InstallationStatus.UPGRADE_PENDING.value,
            pending_version=target_manifest.deck_plugin_version,
            pending_capabilities_json=pending_json,
            last_error_code=CAPABILITY_EXPANSION_APPROVAL_REQUIRED,
            last_error_summary="capability expansion requires administrator approval",
        )
        return diff

    async def approve_capability_expansion(
        self,
        installation_id: str,
        approved_capabilities: list[str],
        actor: str,
    ) -> DeckPluginInstallation:
        """Apply an exact pending capability set after explicit admin approval."""

        if not actor.strip() or not await self._is_administrator(actor):
            raise CompatibilityServiceError(
                CAPABILITY_APPROVAL_DENIED,
                "administrator approval is required",
            )
        installation = self._installation_row(installation_id)
        if installation["status"] != InstallationStatus.UPGRADE_PENDING.value:
            raise CompatibilityServiceError(
                CAPABILITY_APPROVAL_INVALID,
                "installation has no pending capability expansion",
            )
        if any(not value.strip() for value in approved_capabilities) or len(
            approved_capabilities
        ) != len(set(approved_capabilities)):
            raise CompatibilityServiceError(
                CAPABILITY_APPROVAL_INVALID,
                "approved capabilities must be non-blank and unique",
            )
        pending = self._json_set(installation["pending_capabilities_json"])
        approved = set(approved_capabilities)
        if approved != pending:
            raise CompatibilityServiceError(
                CAPABILITY_APPROVAL_INVALID,
                "approval must exactly match the pending capability set",
            )

        self._update_installation(
            installation,
            status=InstallationStatus.READY.value,
            approved_capabilities_json=json.dumps(sorted(approved)),
            pending_version=None,
            pending_capabilities_json=None,
            last_error_code=None,
            last_error_summary=None,
        )
        return self._installation_model(self._installation_row(installation_id))

    @staticmethod
    def _available_manifest(
        release: Any | None,
        installation: Any | None,
        deck_plugin_id: str,
        deck_plugin_version: str,
        deprecated_allowed: bool,
    ) -> DeckPluginManifestV1 | None:
        if release is None or installation is None:
            return None
        allowed_statuses = {DeckPluginReleaseStatus.PUBLISHED.value}
        if deprecated_allowed:
            allowed_statuses.add(DeckPluginReleaseStatus.DEPRECATED.value)
        if (
            release["status"] not in allowed_statuses
            or installation["status"] != InstallationStatus.READY.value
            or deck_plugin_version
            not in CompatibilityService._json_set(
                installation["installed_versions_json"]
            )
        ):
            return None
        try:
            manifest = DeckPluginManifestV1.model_validate_json(
                release["manifest_json"]
            )
        except Exception:
            return None
        if (
            manifest.deck_plugin_id != deck_plugin_id
            or manifest.deck_plugin_version != deck_plugin_version
        ):
            return None
        return manifest

    def _resolved_runtime_lock(
        self,
        release: Any | None,
        manifest: DeckPluginManifestV1,
        deck_plugin_id: str,
        deck_plugin_version: str,
    ) -> DeckRuntimePluginLock | None:
        row = self.db.execute(
            """
            SELECT deck_plugin_manifest_hash, lock_json
            FROM deck_runtime_plugin_locks
            WHERE deck_plugin_id = %s AND deck_plugin_version = %s
            """,
            (deck_plugin_id, deck_plugin_version),
        ).fetchone()
        if (
            row is None
            or release is None
            or row["deck_plugin_manifest_hash"] != release["manifest_hash"]
        ):
            return None
        try:
            runtime_lock = DeckRuntimePluginLock.model_validate_json(row["lock_json"])
        except Exception:
            return None
        if (
            runtime_lock.deck_plugin_id != deck_plugin_id
            or runtime_lock.deck_plugin_version != deck_plugin_version
            or runtime_lock.deck_plugin_manifest_hash != release["manifest_hash"]
        ):
            return None
        entries = runtime_lock.claude_code_plugins
        if len({entry.claude_code_plugin_id for entry in entries}) != len(entries):
            return None
        digest_pattern = re.compile(r"^sha256:[0-9a-f]{64}$")
        if any(
            not entry.source_ref.strip()
            or not entry.resolved_version.strip()
            or not digest_pattern.fullmatch(entry.artifact_digest)
            for entry in entries
        ):
            return None
        declared = {
            plugin.claude_code_plugin_id
            for plugin in manifest.runtime.claude_code_plugins
        }
        if declared != {entry.claude_code_plugin_id for entry in entries}:
            return None
        return runtime_lock

    @staticmethod
    def _required_capabilities(manifest: DeckPluginManifestV1) -> set[str]:
        required = {
            capability
            for step in manifest.workflow.steps
            for capability in step.required_capabilities
        }
        required.update(
            capability
            for plugin in manifest.runtime.claude_code_plugins
            if plugin.required
            for capability in plugin.capability_bindings
        )
        return required

    @staticmethod
    def _failure(
        failed_check: CompatibilityCheck,
        error_code: str,
    ) -> CompatibilityResult:
        return CompatibilityResult(
            passed=False,
            failed_check=failed_check,
            error_code=error_code,
            recovery_action=RECOVERY_ACTIONS[failed_check],
        )

    def _installation_row(self, installation_id: str) -> Any:
        row = self.db.execute(
            "SELECT * FROM deck_plugin_installations WHERE id = %s",
            (installation_id,),
        ).fetchone()
        if row is None:
            raise CompatibilityServiceError(
                CAPABILITY_APPROVAL_INVALID,
                "Deck Plugin installation was not found",
            )
        return row

    async def _is_administrator(self, actor: str) -> bool:
        result = self._administrator_authorizer(actor)
        if inspect.isawaitable(result):
            result = await result
        return bool(result)

    def _update_installation(self, row: Any, **updates: Any) -> None:
        unknown_columns = set(updates) - _MUTABLE_INSTALLATION_COLUMNS
        if unknown_columns:
            raise ValueError(
                "unsupported deck installation update columns: "
                + ", ".join(sorted(unknown_columns))
            )
        assignments: list[str] = []
        parameters: list[Any] = []
        for column, value in updates.items():
            assignments.append(f"{column} = %s")
            parameters.append(value)
        assignments.extend(
            ("updated_at = CURRENT_TIMESTAMP", "revision = revision + 1")
        )
        parameters.extend((row["id"], row["revision"]))
        try:
            cursor = self.db.execute(
                f"UPDATE deck_plugin_installations SET {', '.join(assignments)} "
                "WHERE id = %s AND revision = %s",
                parameters,
            )
            if cursor.rowcount != 1:
                raise CompatibilityServiceError(
                    CAPABILITY_APPROVAL_INVALID,
                    "installation changed during capability approval",
                )
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    @staticmethod
    def _json_set(value: str | None) -> set[str]:
        if value is None:
            return set()
        try:
            parsed = json.loads(value)
        except (TypeError, json.JSONDecodeError):
            return set()
        if not isinstance(parsed, list) or any(
            not isinstance(item, str) for item in parsed
        ):
            return set()
        return set(parsed)

    @staticmethod
    def _installation_model(row: Any) -> DeckPluginInstallation:
        return DeckPluginInstallation(
            deck_plugin_installation_id=row["id"],
            scope_type=row["scope_type"],
            scope_id=row["scope_id"],
            deck_plugin_id=row["deck_plugin_id"],
            installed_versions=sorted(
                CompatibilityService._json_set(row["installed_versions_json"])
            ),
            default_version=row["default_version"],
            status=InstallationStatus(row["status"]),
            approved_capabilities=sorted(
                CompatibilityService._json_set(row["approved_capabilities_json"])
            ),
            source_policy_id=row["source_policy_id"],
            last_error_code=row["last_error_code"],
            last_error_summary=row["last_error_summary"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
