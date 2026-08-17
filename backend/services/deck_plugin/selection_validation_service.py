"""Server-authoritative Deck Plugin selection validation orchestration."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import inspect
import json
from typing import Any
try:
    from backend.models.deck_plugin import (
        CompatibilityCheck,
        DeckPluginOption,
        DeckPluginOptionsResponse,
        SelectionCompatibility,
        SelectionRecovery,
        SelectionValidationSummary,
        SEMVER_PATTERN,
    )
    from backend.services.deck_plugin.compatibility_service import (
        CompatibilityService,
        RuntimeContext,
    )
    from backend.services.deck_plugin.installation_service import Scope
except ModuleNotFoundError:  # Support the backend directory on PYTHONPATH.
    from models.deck_plugin import (
        CompatibilityCheck,
        DeckPluginOption,
        DeckPluginOptionsResponse,
        SelectionCompatibility,
        SelectionRecovery,
        SelectionValidationSummary,
        SEMVER_PATTERN,
    )
    from services.deck_plugin.compatibility_service import (
        CompatibilityService,
        RuntimeContext,
    )
    from services.deck_plugin.installation_service import Scope


DECK_PLUGIN_UNAVAILABLE = "DECK_PLUGIN_UNAVAILABLE"
DECK_PLUGIN_DISABLED = "DECK_PLUGIN_DISABLED"
DECK_PLUGIN_UPGRADE_PENDING = "DECK_PLUGIN_UPGRADE_PENDING"
RUNTIME_CONTEXT_UNAVAILABLE = "RUNTIME_CONTEXT_UNAVAILABLE"


RuntimeContextResolver = Callable[
    [str, str, str, str],
    RuntimeContext | Awaitable[RuntimeContext],
]


_RECOVERY = {
    DECK_PLUGIN_UNAVAILABLE: SelectionRecovery(
        owner="deck_plugin_admin",
        action="select_an_available_installed_release",
    ),
    DECK_PLUGIN_DISABLED: SelectionRecovery(
        owner="deck_plugin_admin",
        action="enable_the_installation_or_select_another_release",
    ),
    DECK_PLUGIN_UPGRADE_PENDING: SelectionRecovery(
        owner="deck_plugin_admin",
        action="approve_the_capability_expansion_or_keep_the_ready_version",
    ),
    RUNTIME_CONTEXT_UNAVAILABLE: SelectionRecovery(
        owner="runtime_platform",
        action="restore_server_side_compatibility_and_readiness_signals",
    ),
}


class SelectionValidationService:
    """Compose persisted release/installation facts with DECK-004 verdicts.

    Runtime compatibility and permission inputs are accepted only through the
    injected server-side resolver. Without that owning-service adapter the
    validator fails closed instead of manufacturing client-controlled facts.
    """

    def __init__(
        self,
        db: Any,
        *,
        runtime_context_resolver: RuntimeContextResolver | None = None,
    ) -> None:
        self.db = db
        self._runtime_context_resolver = runtime_context_resolver
        self._compatibility = CompatibilityService(db)

    async def validate(
        self,
        *,
        deck_plugin_id: str,
        deck_plugin_version: str,
        workspace_id: str,
        actor_id: str,
    ) -> SelectionValidationSummary:
        if not SEMVER_PATTERN.fullmatch(deck_plugin_version):
            return self._failure(
                release_status="unknown",
                installation_status="unknown",
                reason_code=DECK_PLUGIN_UNAVAILABLE,
            )

        release = self.db.execute(
            """
            SELECT display_name, status
            FROM deck_plugin_releases
            WHERE deck_plugin_id = %s AND deck_plugin_version = %s
            """,
            (deck_plugin_id, deck_plugin_version),
        ).fetchone()
        if release is None:
            return self._failure(
                release_status="missing",
                installation_status="missing",
                reason_code=DECK_PLUGIN_UNAVAILABLE,
            )
        release_status = str(release["status"])
        if release_status not in {"published", "deprecated"}:
            return self._failure(
                release_status=release_status,
                installation_status="unknown",
                reason_code=DECK_PLUGIN_UNAVAILABLE,
            )

        scope, installation = self._installation_scope(
            workspace_id, deck_plugin_id
        )
        if installation is None or scope is None:
            return self._failure(
                release_status=release_status,
                installation_status="missing",
                reason_code=DECK_PLUGIN_UNAVAILABLE,
            )
        installation_status = str(installation["status"])
        if installation_status == "disabled":
            return self._failure(
                release_status=release_status,
                installation_status=installation_status,
                reason_code=DECK_PLUGIN_DISABLED,
            )
        if installation_status == "upgrade_pending":
            return self._failure(
                release_status=release_status,
                installation_status=installation_status,
                reason_code=DECK_PLUGIN_UPGRADE_PENDING,
            )
        if installation_status != "ready" or deck_plugin_version not in self._json_set(
            installation["installed_versions_json"]
        ):
            return self._failure(
                release_status=release_status,
                installation_status=installation_status,
                reason_code=DECK_PLUGIN_UNAVAILABLE,
            )

        runtime_context = await self._resolve_runtime_context(
            deck_plugin_id,
            deck_plugin_version,
            workspace_id,
            actor_id,
        )
        if runtime_context is None:
            return self._failure(
                release_status=release_status,
                installation_status=installation_status,
                reason_code=RUNTIME_CONTEXT_UNAVAILABLE,
                compatibility=SelectionCompatibility.UNKNOWN,
            )

        result = await self._compatibility.check_compatibility(
            deck_plugin_id,
            deck_plugin_version,
            scope,
            runtime_context,
        )
        if result.passed:
            return SelectionValidationSummary(
                selectable=True,
                release_status=release_status,
                installation_status=installation_status,
                compatibility=SelectionCompatibility.PASSED,
                runtime_readiness="materialized",
                capability_summary=result.effective_capabilities,
            )

        reason_code = result.error_code or DECK_PLUGIN_UNAVAILABLE
        late_check = result.failed_check in {
            CompatibilityCheck.WORKFLOW_PERMISSION,
            CompatibilityCheck.RUNTIME_PLUGIN_READY,
        }
        return SelectionValidationSummary(
            selectable=False,
            release_status=release_status,
            installation_status=installation_status,
            compatibility=(
                SelectionCompatibility.PASSED
                if late_check
                else SelectionCompatibility.FAILED
            ),
            runtime_readiness=(
                "not_ready"
                if result.failed_check is CompatibilityCheck.RUNTIME_PLUGIN_READY
                else "unknown"
            ),
            reason_code=reason_code,
            recovery=SelectionRecovery(
                owner=self._recovery_owner(result.failed_check),
                action=result.recovery_action or "select_another_release",
            ),
        )

    async def list_options(
        self,
        *,
        deck_id: str,
        workspace_id: str,
        actor_id: str,
    ) -> DeckPluginOptionsResponse:
        releases = self.db.execute(
            """
            SELECT display_name, deck_plugin_id, deck_plugin_version, status
            FROM deck_plugin_releases
            WHERE status IN ('published', 'deprecated', 'revoked')
            ORDER BY display_name, deck_plugin_id, deck_plugin_version DESC
            """
        ).fetchall()
        options: list[DeckPluginOption] = []
        for release in releases:
            summary = await self.validate(
                deck_plugin_id=release["deck_plugin_id"],
                deck_plugin_version=release["deck_plugin_version"],
                workspace_id=workspace_id,
                actor_id=actor_id,
            )
            options.append(
                DeckPluginOption(
                    display_name=release["display_name"],
                    deck_plugin_id=release["deck_plugin_id"],
                    deck_plugin_version=release["deck_plugin_version"],
                    release_status=summary.release_status,
                    installation_status=summary.installation_status,
                    compatibility=summary.compatibility,
                    runtime_readiness=summary.runtime_readiness,
                    selectable=summary.selectable,
                    reason_code=summary.reason_code,
                    recovery=summary.recovery,
                    capability_summary=summary.capability_summary,
                )
            )
        return DeckPluginOptionsResponse(deck_id=deck_id, options=options)

    async def _resolve_runtime_context(
        self,
        deck_plugin_id: str,
        deck_plugin_version: str,
        workspace_id: str,
        actor_id: str,
    ) -> RuntimeContext | None:
        if self._runtime_context_resolver is None:
            return None
        try:
            result = self._runtime_context_resolver(
                deck_plugin_id,
                deck_plugin_version,
                workspace_id,
                actor_id,
            )
            if inspect.isawaitable(result):
                result = await result
            if isinstance(result, RuntimeContext):
                return result
            if hasattr(result, "model_dump"):
                result = result.model_dump()
            return RuntimeContext.model_validate(result)
        except Exception:
            return None

    def _installation_scope(
        self,
        workspace_id: str,
        deck_plugin_id: str,
    ) -> tuple[Scope | None, Any | None]:
        row = self.db.execute(
            """
            SELECT * FROM deck_plugin_installations
            WHERE scope_type = 'workspace' AND scope_id = %s AND deck_plugin_id = %s
            """,
            (workspace_id, deck_plugin_id),
        ).fetchone()
        if row is not None:
            return Scope(scope_type="workspace", scope_id=workspace_id), row
        row = self.db.execute(
            """
            SELECT * FROM deck_plugin_installations
            WHERE scope_type = 'instance' AND deck_plugin_id = %s
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (deck_plugin_id,),
        ).fetchone()
        if row is None:
            return None, None
        return Scope(scope_type="instance", scope_id=row["scope_id"]), row

    @staticmethod
    def _failure(
        *,
        release_status: str,
        installation_status: str,
        reason_code: str,
        compatibility: SelectionCompatibility = SelectionCompatibility.FAILED,
    ) -> SelectionValidationSummary:
        return SelectionValidationSummary(
            selectable=False,
            release_status=release_status,
            installation_status=installation_status,
            compatibility=compatibility,
            runtime_readiness="unknown",
            reason_code=reason_code,
            recovery=_RECOVERY[reason_code],
        )

    @staticmethod
    def _recovery_owner(check: CompatibilityCheck | None) -> str:
        if check is CompatibilityCheck.WORKFLOW_PERMISSION:
            return "workspace_admin"
        if check is CompatibilityCheck.RUNTIME_PLUGIN_READY:
            return "runtime_platform"
        return "deck_plugin_publisher"

    @staticmethod
    def _json_set(value: str | None) -> set[str]:
        try:
            parsed = json.loads(value or "[]")
        except (TypeError, json.JSONDecodeError):
            return set()
        if not isinstance(parsed, list) or any(
            not isinstance(item, str) for item in parsed
        ):
            return set()
        return set(parsed)
