# [Input] Request-scoped Admin Registry130-132 consumer, OAuth bearer and shared artifact verifier.
# [Output] Authorized current or frozen launch binding after local immutable Runtime verification.
# [Pos] Dream launch Runtime port; contains no PostgreSQL client, ORM, SQL or persistence fallback.
# [Sync] 2026-09-16: replace DreamRuntimeProvisioningService with Admin DTO orchestration.
"""Request-scoped launch Runtime preparation through Admin-owned data operations."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, Mapping
from uuid import uuid4

try:
    from services.admin_data.deck_plugin_binding_data import (
        AdminDeckPluginBindingData,
        DreamLaunchRuntimePlanInputDTO,
        DreamLaunchRuntimePrepareInputDTO,
        DreamLaunchRuntimeScopeInputDTO,
    )
    from services.admin_data.errors import AdminDataError
    from services.deck.agent_type_runtime import (
        AgentTypeRuntimeUnavailable,
        verify_agent_type_runtime,
    )
except ModuleNotFoundError:  # Support package imports from repository root.
    from backend.services.admin_data.deck_plugin_binding_data import (
        AdminDeckPluginBindingData,
        DreamLaunchRuntimePlanInputDTO,
        DreamLaunchRuntimePrepareInputDTO,
        DreamLaunchRuntimeScopeInputDTO,
    )
    from backend.services.admin_data.errors import AdminDataError
    from backend.services.deck.agent_type_runtime import (
        AgentTypeRuntimeUnavailable,
        verify_agent_type_runtime,
    )


class DreamLaunchRuntimeError(RuntimeError):
    def __init__(self, code: str, status_code: int) -> None:
        self.code = code
        self.status_code = status_code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class PreparedDreamLaunchBinding:
    deck_plugin_id: str
    deck_plugin_version: str
    deck_plugin_binding_id: str
    binding_revision: int


class AdminDreamLaunchRuntime:
    """Perform one authenticated launch Runtime sequence without exposing tokens."""

    def __init__(self, data: AdminDeckPluginBindingData, access_token: str) -> None:
        if not access_token or any(character.isspace() for character in access_token):
            raise DreamLaunchRuntimeError("INVALID_ACCESS_TOKEN", 401)
        self._data = data
        self._access_token = access_token

    async def authorize(
        self,
        *,
        deck_id: str,
        workspace_id: str,
        agent_id: str | None,
    ) -> None:
        input_dto = DreamLaunchRuntimeScopeInputDTO(
            deck_id=deck_id,
            workspace_id=workspace_id,
            agent_id=agent_id,
        )
        await self._call(self._data.launch_runtime_scope, input_dto)

    async def prepare(
        self,
        *,
        deck_id: str,
        workspace_id: str,
        agent_id: str | None,
        existing_run: Mapping[str, Any] | None,
    ) -> PreparedDreamLaunchBinding:
        if existing_run is None:
            plan_input = DreamLaunchRuntimePlanInputDTO(
                deck_id=deck_id,
                workspace_id=workspace_id,
                agent_id=agent_id,
                mode="current",
                workflow_run_id=None,
                thread_id=None,
            )
        else:
            plan_input = DreamLaunchRuntimePlanInputDTO(
                deck_id=deck_id,
                workspace_id=workspace_id,
                agent_id=agent_id,
                mode="replay",
                workflow_run_id=str(existing_run["id"]),
                thread_id=str(existing_run["source_voice_thread_id"]),
            )
        plan = await self._call(self._data.launch_runtime_plan, plan_input)
        try:
            evidence = await asyncio.to_thread(
                verify_agent_type_runtime,
                plan.target,
            )
        except AgentTypeRuntimeUnavailable as exc:
            raise DreamLaunchRuntimeError("RUNTIME_PLUGIN_NOT_READY", 503) from exc
        prepared = await self._call(
            self._data.launch_runtime_prepare,
            DreamLaunchRuntimePrepareInputDTO(
                **plan_input.model_dump(),
                expected_binding_revision=plan.binding.binding_revision,
                verified_plugin=evidence,
            ),
        )
        if prepared.binding != plan.binding:
            raise DreamLaunchRuntimeError("ADMIN_RESPONSE_INVALID", 503)
        return PreparedDreamLaunchBinding(
            deck_plugin_id=prepared.binding.deck_plugin_id,
            deck_plugin_version=prepared.binding.deck_plugin_version,
            deck_plugin_binding_id=prepared.binding.deck_plugin_binding_id,
            binding_revision=prepared.binding.binding_revision,
        )

    async def _call(self, method, input_dto):
        try:
            return await asyncio.to_thread(
                method,
                input_dto,
                str(uuid4()),
                access_token=self._access_token,
            )
        except AdminDataError as exc:
            raise DreamLaunchRuntimeError(exc.code, exc.status_code) from exc


__all__ = [
    "AdminDreamLaunchRuntime",
    "DreamLaunchRuntimeError",
    "PreparedDreamLaunchBinding",
]
