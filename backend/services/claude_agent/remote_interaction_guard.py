"""Fail-closed reload guard for run-scoped and management sessions."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, field_validator


RUNTIME_PLUGIN_RELOAD_UNSUPPORTED = "RUNTIME_PLUGIN_RELOAD_UNSUPPORTED"
MANAGEMENT_SMOKE_ALLOWED = "MANAGEMENT_SMOKE_ALLOWED"


class _StrictFrozenModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        str_strip_whitespace=True,
    )


class PluginRef(_StrictFrozenModel):
    claude_code_plugin_id: str = Field(min_length=1)
    resolved_version: str = Field(min_length=1)
    artifact_digest: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    capabilities: list[str] = Field(default_factory=list)
    materialized: bool
    marketplace_cached: bool

    @field_validator("capabilities")
    @classmethod
    def capabilities_are_canonical(cls, value: list[str]) -> list[str]:
        if value != sorted(set(value)):
            raise ValueError("capabilities must be sorted and unique")
        return value


class ManagementSmokeContext(_StrictFrozenModel):
    management_session_id: str = Field(pattern=r"^mgmt_[A-Za-z0-9._-]+$")
    deployment_tier: str
    plugins: list[PluginRef]


class GuardResult(_StrictFrozenModel):
    allowed: bool
    reason_code: str
    diagnostic_only: bool
    writes_readiness: bool
    creates_receipt: bool
    production_authorized: bool


ManagementContextReader = Callable[[str], ManagementSmokeContext | None]


class RemoteInteractionGuard:
    def __init__(
        self,
        db: Any,
        *,
        management_context_reader: ManagementContextReader | None = None,
    ) -> None:
        self.db = db
        self._management_context_reader = management_context_reader

    async def guard_reload(
        self,
        *,
        workflow_run_id: str | None,
        agent_session_id: str | None,
        proposed_plugins: list[PluginRef],
        proposed_capabilities: list[str],
    ) -> GuardResult:
        """Allow only a proven idle dev/test management smoke diagnostic."""

        if proposed_capabilities != sorted(set(proposed_capabilities)):
            return self._deny()
        if workflow_run_id is not None:
            run = self.db.execute(
                "SELECT status FROM workflow_runs WHERE id = %s",
                (workflow_run_id,),
            ).fetchone()
            if run is not None:
                return self._deny()
            return self._deny()
        if agent_session_id is None:
            return self._deny()
        run_session = self.db.execute(
            "SELECT status FROM agent_sessions WHERE agent_session_id = %s",
            (agent_session_id,),
        ).fetchone()
        if run_session is not None:
            return self._deny()
        if self._management_context_reader is None:
            return self._deny()
        context = self._management_context_reader(agent_session_id)
        if (
            context is None
            or context.management_session_id != agent_session_id
            or context.deployment_tier not in {"development", "test"}
        ):
            return self._deny()
        current = {
            item.claude_code_plugin_id: item for item in context.plugins
        }
        proposed = {
            item.claude_code_plugin_id: item for item in proposed_plugins
        }
        if len(current) != len(context.plugins) or len(proposed) != len(proposed_plugins):
            return self._deny()
        if set(current) != set(proposed):
            return self._deny()
        for plugin_id, requested in proposed.items():
            trusted = current[plugin_id]
            if (
                not requested.materialized
                or not requested.marketplace_cached
                or requested.resolved_version != trusted.resolved_version
                or requested.artifact_digest != trusted.artifact_digest
                or requested.capabilities != trusted.capabilities
            ):
                return self._deny()
        allowed_capabilities = sorted(
            {
                capability
                for plugin in context.plugins
                for capability in plugin.capabilities
            }
        )
        if proposed_capabilities != allowed_capabilities:
            return self._deny()
        return GuardResult(
            allowed=True,
            reason_code=MANAGEMENT_SMOKE_ALLOWED,
            diagnostic_only=True,
            writes_readiness=False,
            creates_receipt=False,
            production_authorized=False,
        )

    @staticmethod
    def _deny() -> GuardResult:
        return GuardResult(
            allowed=False,
            reason_code=RUNTIME_PLUGIN_RELOAD_UNSUPPORTED,
            diagnostic_only=True,
            writes_readiness=False,
            creates_receipt=False,
            production_authorized=False,
        )
