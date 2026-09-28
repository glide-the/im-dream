#!/usr/bin/env python3
# [Sync] 2026-09-28: add wait_threads as an in-turn tool wait and retire automatic task-result injection/read cards.
# [Sync] 2026-09-28: replace model task-session commands with authorized create/list/read/send Thread Tools.
# [Sync] 2026-09-27: project a task's saved completed assistant result separately from its launch/runtime state.
# [Sync] 2026-09-27: expose owner-filtered task-session navigation links for Chat.
# [Sync] 2026-09-27: refresh long-running Tool authorization from the authenticated confirmation request.
# [Sync] 2026-09-27: authorize per-card cancellation and side-task transfer.
# [Sync] 2026-09-26: authorize durable Thread input listing, enqueue and selected-message guidance.
# [Input] Consume typed Admin Chat APIs, pending Deck/runtime providers, Claude Agent factory, Skill catalog and Admin actor.
# [Output] Register /api/claude-agent* turn, thread, and common Skill catalog endpoints.
# [Pos] claude-agent route node in backend/routers
# [Sync] 2026-09-16: bind Gateway catalog to Admin OAuth and Runtime to an Admin gateway-cli grant.
# [Sync] 2026-09-16: bind history MCP App projections to the current Admin OAuth authorization.
# [Sync] 2026-09-15: reuse the shared typed Admin invocation adapter with unchanged Chat error semantics.
# [Sync] 2026-09-15: reserve user message/title atomically with a server-only purpose grant; factory owns background renewal cleanup.
# [Sync] 2026-09-15: read Admin Workflow provenance before message/SSE and inject a server-owned immutable snapshot.
# [Sync] 2026-09-15: create the turn-owned Admin Editor runtime before public Agent execution.
# [Sync] 2026-09-15: reuse one OAuth SystemConfig snapshot for model selection and attachment preparation.
# [Sync] 2026-09-15: resolve Deck chat context through Registry105 before persistence, workspace and SSE.
# [Sync] 2026-05-25: extracted Claude Agent routes from backend/server.py.
# [Sync] 2026-08-28: preserve validated model metadata across backend/services dual import identities.
# [Sync] 2026-05-25: add attachment processing — download from file storage and sync to workspace.
# [Sync] 2026-05-27: ClaudeAgentRequestBody.tool_choice uses AliasChoices("tool_choice","toolChoice") so frontend camelCase is accepted.
# [Sync] 2026-05-28: remove planning_mode field and prompt_optimizer integration (unrelated code).
# [Sync] 2026-06-06: stop forwarding client memoryConfig into ClaudeAgentRunRequest;
#                    Memory workspace config is resolved from the partition table
#                    by the workspace file-interface initializer.
# [Sync] 2026-06-09: P3 fix — add GET /api/claude-agent/threads/{thread_id}/status
#                    endpoint returning {running, lifecycle, turn_count} via
#                    claude_agent_thread_factory.session_snapshot().
# [Sync] 2026-06-09: SSE reconnect — GET /threads/{id}/stream; POST body reconnect=true.
# [Sync] 2026-06-13: initialize attachment workspaces with Settings-backed
#                    workspace sandbox mode so per-thread .claude/settings.json
#                    is correct before Claude Code starts.
# [Sync] 2026-06-21: initialize attachment workspaces with sandbox network policy.
# [Sync] 2026-06-22: when Settings Workspace Mode is disabled, attachment
#                    handling no longer initializes or syncs a thread workspace.
# [Sync] 2026-06-25: add thread-scoped stop endpoint so the frontend can cancel
#                    the current Agent turn without deleting the chat thread.
# [Sync] 2026-06-27: /api/claude-agent/threads accepts Chat history search
#                    params backed by plugin-style fuzzy/vector retrievers.
# [Sync] 2026-07-09: default /api/claude-agent/threads lists accept limit/offset
#                    for frontend scroll pagination without loading all threads.
# [Sync] 2026-07-20: add GET /api/claude-agent/threads/{thread_id}/plan —
#                    current Plan Mode plan per thread (claude-plan §5.5).
# [Sync] 2026-07-20: add GET /api/claude-agent/threads/{thread_id}/todos —
#                    current todo list per thread (claude-todo §5.5).
# [Sync] 2026-08-04: add authenticated GET /threads/{thread_id}/subagents —
#                    safe projection of Claude Code subagent transcript metadata.
# [Sync] 2026-08-17: allow owned Chat history to be filtered by Deck for the
#                    Settings / Work related-conversation deletion flow.
# [Sync] 2026-08-17: allow same-Deck Agent selection per turn while Deck provenance stays immutable.
# [Sync] 2026-08-28: resolve the full server-owned model selection so Claude Code Runtime
#                    windows reach the turn without exposing them to the browser request.
# [Sync] 2026-08-30: use the server-owned sandbox enablement capability when
#                    attachment handling initializes a full Thread workspace.
# [Sync] 2026-09-01: project the allowlisted Dream auto-repair message contract
#                    and reserve its server-owned message-id namespace.
# [Sync] 2026-09-01: preserve validated projectCleanup trusted/stale facts in
#                    history so SSE and refresh expose the same repair message.
# [Sync] 2026-09-02: add stable cursor Chat message pages and known-latest
#                    identity stabilization while preserving the legacy full response.
# [Sync] 2026-09-02: expose final-only paged assistant rows and an owned exact-id
#                    process-detail endpoint backed by canonical message parts.
# [Sync] 2026-09-04: expose the authenticated backend-owned common Skill command
#                    catalog used by the shared Chat slash menu.
# [Sync] 2026-09-06: validate the closed McpAppsToolResultProjectionV1 on saved
#                    tool parts, including workspace scope; malformed/error identity
#                    is removed without touching ordinary invocation/output refresh.
# [Sync] 2026-09-06: reconstruct pre-fix user-scope Apps identity only from a
#                    fresh actor-owned tools/list descriptor snapshot.
# [Sync] 2026-09-14: migrate HTTP Thread ownership/CRUD/history to typed Admin operations; background persistence and other domains remain active migration targets.

import asyncio
import base64
import binascii
from hashlib import sha256
import json
import logging
import math
import os
import re
from datetime import datetime, timezone
from concurrent.futures import TimeoutError as FutureTimeoutError
from enum import Enum
from pathlib import Path
from typing import Annotated, Any, List, Literal, Mapping, Optional
from uuid import NAMESPACE_URL, uuid4, uuid5

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import AliasChoices, BaseModel, Field, model_validator
from starlette.concurrency import run_in_threadpool

from agent_factory import claude_agent_thread_factory
from libs.claude_agent_kit.server.session_projection_protocol import (
    ThreadToolCommandRequestDTO,
    ThreadToolCommandResultDTO,
    ThreadToolMessageDTO,
    ThreadToolThreadDTO,
    ThreadToolWaitErrorDTO,
    ThreadToolWaitTargetDTO,
    ThreadToolWaitUpdateDTO,
)
from claude_agent import ClaudeAgentRunRequest
from claude_agent.service import (
    _build_mcp_apps_tool_result_projection,
    _validated_mcp_apps_projection_for_tool_part,
    build_thread_plan_payload,
    build_thread_todos_payload,
)
from claude_agent.sse import streaming_sse_response
from claude_agent.subagent_projection import build_thread_subagents_payload
from claude_agent.tool_confirmation_store import (
    ToolConfirmationError,
    ToolConfirmationResolution,
)
from claude_agent.thread_retrieval import (
    build_chat_thread_search_config,
    is_chat_history_search_requested,
    search_chat_threads,
)
from libs.claude_agent_kit.messages.build_user_message_content import AttachmentPayload
from libs.claude_agent_kit.server.builtin_skill_packages import (
    COMMON_SKILL_NAMESPACE,
    BuiltinSkillPackageError,
    discover_builtin_skill_packages,
)
from libs.claude_agent_kit.server.workspace import (
    get_or_create_workspace,
    get_workspace_root,
    resolve_sandbox_enabled,
)
from libs.claude_agent_kit.server.workspace_file_sync import (
    WorkspaceFileSyncError,
    WorkspaceFileSyncErrorCode,
    inject_attachment_message_parts,
    normalize_workspace_file_sync_error,
    sync_attachments_to_workspace_files,
)
from libs.file_storage import server_file_storage
from services.deck.chat_context import DeckChatContextAssembler, DeckChatContextError
from services.admin_gateway import (
    GatewayInferenceError,
    GatewayModel,
    GatewayModelCatalogClient,
    resolve_platform_model,
)
from services.story_workspace.dream_auto_repair_service import (
    DREAM_AUTO_REPAIR_METADATA_KIND,
    dream_auto_repair_metadata_is_valid,
)

from services.admin_data.chat_data import AdminChatData
from services.admin_data import chat_models as chat_dto
from services.admin_data.errors import AdminDataError
from services.admin_data.request_auth import AdminRequestActor, AdminRequestAuth
from services.admin_data.system_config_data import AdminSystemConfigData, SystemConfigGetInputDTO
from services.admin_data.deck_chat_context_data import (
    AdminDeckChatContextData,
    DeckChatContextInputDTO,
)
from .deps import get_admin_request_auth, get_current_user, invoke_admin_operation


def get_admin_chat_data(owner: AdminRequestAuth = Depends(get_admin_request_auth)) -> AdminChatData:
    return AdminChatData(owner.client)


_chat_invoke = invoke_admin_operation


async def _admin_thread(current_user: dict, chat: AdminChatData, thread_id: str) -> dict | None:
    result = await _chat_invoke(current_user, chat.get_thread, chat_dto.ThreadIdInputDTO(thread_id=thread_id))
    return result.thread.model_dump() if result.thread is not None else None

logger = logging.getLogger(__name__)

router = APIRouter()

_SANDBOX_NETWORK_MODES = {"disabled", "allowlist", "open"}
_PLATFORM_MODEL_ALIAS = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,119}$")
_SERVER_MESSAGE_ID_PREFIXES = (
    "dream_agent_",
    "dream_confirm_",
    "dream_repair_",
    "guide_",
)
_CHAT_MESSAGE_CURSOR_VERSION = 1


def _chat_message_cursor_timestamp(value: object) -> str | None:
    """Serialize a PostgreSQL timestamp without losing offset or microseconds."""

    if value is None:
        return None
    if isinstance(value, datetime):
        timestamp = value
    elif isinstance(value, str):
        try:
            timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError as exc:
            raise ValueError("cursor timestamp is invalid") from exc
    else:
        raise ValueError("cursor timestamp is invalid")
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        # The PostgreSQL driver historically returned UTC-naive values in a
        # few tests; attach the storage timezone rather than ambient local time.
        timestamp = timestamp.replace(tzinfo=timezone.utc)
    return timestamp.isoformat(timespec="microseconds")


def _encode_chat_message_cursor(thread_id: str, message: dict[str, Any]) -> str:
    message_id = message.get("id")
    if not isinstance(message_id, str) or not message_id:
        raise ValueError("cursor message id is invalid")
    payload = {
        "v": _CHAT_MESSAGE_CURSOR_VERSION,
        "thread_id": thread_id,
        "created_at": _chat_message_cursor_timestamp(message.get("created_at")),
        "id": message_id,
    }
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return base64.urlsafe_b64encode(encoded).decode("ascii").rstrip("=")


def _decode_chat_message_cursor(thread_id: str, cursor: str) -> tuple[datetime | None, str, bool]:
    """Decode and bind one opaque cursor to its owning Thread."""

    try:
        padding = "=" * (-len(cursor) % 4)
        raw = base64.b64decode(
            f"{cursor}{padding}",
            altchars=b"-_",
            validate=True,
        )
        payload = json.loads(raw.decode("utf-8"))
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("cursor encoding is invalid") from exc
    if not isinstance(payload, dict) or set(payload) != {"v", "thread_id", "created_at", "id"}:
        raise ValueError("cursor shape is invalid")
    if payload.get("v") != _CHAT_MESSAGE_CURSOR_VERSION:
        raise ValueError("cursor version is unsupported")
    if payload.get("thread_id") != thread_id:
        raise ValueError("cursor thread does not match")
    message_id = payload.get("id")
    if not isinstance(message_id, str) or not message_id:
        raise ValueError("cursor message id is invalid")
    timestamp_value = payload.get("created_at")
    if timestamp_value is None:
        return None, message_id, True
    if not isinstance(timestamp_value, str):
        raise ValueError("cursor timestamp is invalid")
    try:
        timestamp = datetime.fromisoformat(timestamp_value)
    except ValueError as exc:
        raise ValueError("cursor timestamp is invalid") from exc
    if timestamp.tzinfo is None or timestamp.utcoffset() is None:
        raise ValueError("cursor timestamp must include an offset")
    return timestamp, message_id, False


class PublicDispatchStatus(str, Enum):
    PENDING = "pending"
    DISPATCHING = "dispatching"
    DISPATCHED = "dispatched"
    FAILED = "failed"


class PublicToolChoice(str, Enum):
    AUTO = "auto"
    MANUAL = "manual"
    NONE = "none"


class PublicAssistantTurnStatus(str, Enum):
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    ERROR = "error"


class PublicChatThreadDto(BaseModel):
    id: Any = None
    title: Any = None
    deck_id: Any = None
    voice_id: Any = None
    created_at: Any = None
    updated_at: Any = None

    @classmethod
    def from_storage(cls, thread: dict[str, Any]) -> "PublicChatThreadDto":
        return cls.model_validate(thread)


class PublicChatMetadataDto(BaseModel):
    kind: str | None = None
    visibility: str | None = None
    dispatch_status: PublicDispatchStatus | None = None
    usage: dict[str, int | float] | None = None
    chatModel: dict[str, str] | None = None
    toolChoice: PublicToolChoice | None = None
    toolCount: int | None = None
    is_partial: bool | None = None
    turnId: str | None = None
    turnStatus: PublicAssistantTurnStatus | None = None
    finalPartIndex: int | None = None
    durationMs: int | float | None = None
    turnProjectionInvalid: bool | None = None
    schemaVersion: str | None = None
    originatingMessageId: str | None = None
    originatingTurnId: str | None = None
    workflowRunId: str | None = None
    repairAttempt: int | None = None
    validationCode: str | None = None
    idempotencyKey: str | None = None
    projectCleanup: dict[str, Any] | None = None

    @classmethod
    def from_storage(
        cls,
        metadata: dict[str, Any],
    ) -> tuple["PublicChatMetadataDto", bool]:
        values: dict[str, Any] = {}
        malformed_discriminator = False

        kind = metadata.get("kind")
        if "kind" in metadata:
            if isinstance(kind, str) and kind:
                values["kind"] = kind
            else:
                malformed_discriminator = True

        visibility = metadata.get("visibility")
        if "visibility" in metadata:
            if isinstance(visibility, str) and visibility:
                values["visibility"] = visibility
            else:
                malformed_discriminator = True

        snake_status = metadata.get("dispatch_status")
        camel_status = metadata.get("dispatchStatus")
        if (
            "dispatch_status" in metadata
            and "dispatchStatus" in metadata
            and snake_status != camel_status
        ):
            malformed_discriminator = True
            dispatch_status = None
        elif "dispatch_status" in metadata:
            dispatch_status = snake_status
        else:
            dispatch_status = camel_status
        if "dispatch_status" in metadata or "dispatchStatus" in metadata:
            try:
                values["dispatch_status"] = PublicDispatchStatus(dispatch_status)
            except (TypeError, ValueError):
                malformed_discriminator = True

        usage = metadata.get("usage")
        if isinstance(usage, dict):
            public_usage = {
                field: value
                for field in ("inputTokens", "outputTokens", "totalTokens")
                if isinstance((value := usage.get(field)), (int, float))
                and not isinstance(value, bool)
                and value >= 0
            }
            if public_usage:
                values["usage"] = public_usage

        chat_model = metadata.get("chatModel")
        if isinstance(chat_model, dict):
            provider = chat_model.get("provider")
            model = chat_model.get("model")
            if (
                isinstance(provider, str)
                and provider
                and isinstance(model, str)
                and model
            ):
                values["chatModel"] = {"provider": provider, "model": model}

        tool_choice = metadata.get("toolChoice")
        try:
            values["toolChoice"] = PublicToolChoice(tool_choice)
        except (TypeError, ValueError):
            pass
        tool_count = metadata.get("toolCount")
        if (
            isinstance(tool_count, int)
            and not isinstance(tool_count, bool)
            and tool_count >= 0
        ):
            values["toolCount"] = tool_count
        is_partial = metadata.get("is_partial")
        if isinstance(is_partial, bool):
            values["is_partial"] = is_partial

        turn_fields = {"turnId", "turnStatus", "finalPartIndex", "durationMs"}
        if any(field in metadata for field in turn_fields):
            turn_id = metadata.get("turnId")
            turn_status_raw = metadata.get("turnStatus")
            final_part_index = metadata.get("finalPartIndex")
            duration_ms = metadata.get("durationMs")
            try:
                turn_status = PublicAssistantTurnStatus(turn_status_raw)
            except (TypeError, ValueError):
                turn_status = None
            duration_valid = (
                duration_ms is None
                or (
                    isinstance(duration_ms, (int, float))
                    and not isinstance(duration_ms, bool)
                    and math.isfinite(duration_ms)
                    and duration_ms >= 0
                )
            )
            completed_shape = (
                turn_status is PublicAssistantTurnStatus.COMPLETED
                and isinstance(final_part_index, int)
                and not isinstance(final_part_index, bool)
                and final_part_index >= 0
                and is_partial is not True
            )
            partial_shape = (
                turn_status in {
                    PublicAssistantTurnStatus.CANCELLED,
                    PublicAssistantTurnStatus.ERROR,
                }
                and final_part_index is None
                and is_partial is True
            )
            if (
                isinstance(turn_id, str)
                and bool(turn_id.strip())
                and duration_valid
                and (completed_shape or partial_shape)
            ):
                values["turnId"] = turn_id
                values["turnStatus"] = turn_status
                if completed_shape:
                    values["finalPartIndex"] = final_part_index
                if duration_ms is not None:
                    values["durationMs"] = duration_ms
            else:
                # Ordinary turn projection corruption must not trigger the
                # private Dream-envelope parts suppression.  Tell the shared
                # renderer to retain the complete diagnostic transcript.
                if isinstance(turn_id, str) and bool(turn_id.strip()):
                    values["turnId"] = turn_id
                values["turnProjectionInvalid"] = True

        if kind == DREAM_AUTO_REPAIR_METADATA_KIND:
            if dream_auto_repair_metadata_is_valid(metadata):
                for field in (
                    "schemaVersion",
                    "originatingMessageId",
                    "originatingTurnId",
                    "workflowRunId",
                    "repairAttempt",
                    "validationCode",
                    "idempotencyKey",
                ):
                    values[field] = metadata[field]
                project_cleanup = metadata.get("projectCleanup")
                if isinstance(project_cleanup, dict):
                    values["projectCleanup"] = project_cleanup
            else:
                # An incomplete server-owned repair envelope could otherwise
                # expose instruction text without verifiable provenance.
                malformed_discriminator = True

        # Dream business rows use the shared Chat history as their visible
        # transcript.  Their body must not be redacted merely because the row
        # carries a server-owned kind, episode action, or legacy visibility
        # marker.  Malformed discriminators still fail closed because their
        # business provenance cannot be established safely.
        return cls.model_validate(values), malformed_discriminator


class McpAppsToolResultProjectionV1(BaseModel):
    """Closed, non-secret public identity for one saved managed MCP result."""

    version: Literal[1]
    serverRef: str
    toolName: str
    toolCallId: str
    input: dict[str, Any]
    workspaceScope: str | None
    resourceUri: str
    result: dict[str, Any]

    model_config = {"extra": "forbid"}

    @classmethod
    def from_tool_part(
        cls,
        projection: Any,
        part: dict[str, Any],
    ) -> "McpAppsToolResultProjectionV1 | None":
        safe = _validated_mcp_apps_projection_for_tool_part(
            projection,
            tool_name=part.get("toolName"),
            tool_call_id=part.get("toolCallId"),
            tool_input=part.get("input"),
            output=part.get("output"),
        )
        if safe is None:
            return None
        try:
            return cls.model_validate(safe)
        except (TypeError, ValueError):
            return None


def _project_public_chat_parts(
    parts: list[Any],
    *,
    mcp_app_resource_bindings: Mapping[str, Mapping[str, str]] | None = None,
) -> list[Any]:
    """Validate Apps identity and safely recover descriptor-bound old rows."""

    projected: list[Any] = []
    for part in parts:
        if not isinstance(part, dict):
            projected.append(part)
            continue
        public_part = dict(part)
        if "mcpAppResult" in public_part:
            mcp_app_result = McpAppsToolResultProjectionV1.from_tool_part(
                public_part.get("mcpAppResult"),
                public_part,
            )
        elif mcp_app_resource_bindings and public_part.get("state") == "output-available":
            candidate = _build_mcp_apps_tool_result_projection(
                managed_server_keys=tuple(mcp_app_resource_bindings),
                managed_app_resource_bindings=mcp_app_resource_bindings,
                managed_workspace_scope=None,
                registered_tool_name=public_part.get("toolName"),
                tool_call_id=public_part.get("toolCallId"),
                tool_input=public_part.get("input"),
                call_tool_result=public_part.get("output"),
                is_error=False,
            )
            mcp_app_result = McpAppsToolResultProjectionV1.from_tool_part(
                candidate,
                public_part,
            )
        else:
            mcp_app_result = None
        if mcp_app_result is None:
            public_part.pop("mcpAppResult", None)
        else:
            public_part["mcpAppResult"] = mcp_app_result.model_dump(mode="json")
        projected.append(public_part)
    return projected


class PublicChatMessageDto(BaseModel):
    id: Any = None
    role: Any = None
    created_at: Any = None
    parts: list[Any] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    projection_version: int | None = None
    process_available: bool | None = None

    @classmethod
    def from_storage(
        cls,
        message: dict[str, Any],
        *,
        mcp_app_resource_bindings: Mapping[str, Mapping[str, str]] | None = None,
    ) -> "PublicChatMessageDto":
        parts = message.get("parts")
        metadata = message.get("metadata")
        if message.get("metadata_decode_error") is True:
            public_metadata: dict[str, Any] = {}
            suppress_parts = True
        elif metadata is None:
            public_metadata = {}
            suppress_parts = False
        elif isinstance(metadata, dict):
            dto, suppress_parts = PublicChatMetadataDto.from_storage(metadata)
            public_metadata = dto.model_dump(exclude_none=True, mode="json")
        else:
            public_metadata = {}
            suppress_parts = True
        values = {
            key: message[key]
            for key in ("id", "role", "created_at")
            if key in message
        }
        values["parts"] = (
            []
            if suppress_parts
            else _project_public_chat_parts(
                parts,
                mcp_app_resource_bindings=(
                    mcp_app_resource_bindings
                    if message.get("role") == "assistant"
                    else None
                ),
            )
            if isinstance(parts, list)
            else []
        )
        values["metadata"] = public_metadata
        if (
            message.get("history_projection_version") == 1
            and isinstance(message.get("history_process_available"), bool)
        ):
            values["projection_version"] = 1
            values["process_available"] = message["history_process_available"]
        return cls.model_validate(values)


def _project_chat_thread_for_client(thread: dict[str, Any]) -> dict[str, Any]:
    """Expose display identity only, never owner/runtime binding columns."""

    return PublicChatThreadDto.from_storage(thread).model_dump(exclude_unset=True)


def _project_public_chat_metadata(
    metadata: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    """Return a value-validated metadata allowlist plus privacy fail-closed bit."""

    dto, private = PublicChatMetadataDto.from_storage(metadata)
    return dto.model_dump(exclude_none=True, mode="json"), private


def _project_chat_message_for_client(
    message: dict[str, Any],
    *,
    mcp_app_resource_bindings: Mapping[str, Mapping[str, str]] | None = None,
) -> dict[str, Any]:
    """Redact server-owned control envelopes from canonical thread history.

    Control rows remain addressable by message id so shared Chat/Dream
    hydration can settle a durable dispatch. Their instruction parts and
    authority-bearing metadata are never browser-readable.
    """

    return PublicChatMessageDto.from_storage(
        message,
        mcp_app_resource_bindings=mcp_app_resource_bindings,
    ).model_dump(
        exclude_unset=True,
        mode="json",
    )


async def _load_current_user_mcp_app_resource_bindings(
    current_user: dict,
) -> dict[str, dict[str, str]]:
    """Best-effort read of current user-scope descriptor bindings for history."""

    try:
        from claude_mcp.service import (  # noqa: PLC0415
            get_default_managed_mcp_runtime_snapshot_loader,
        )
        from claude_mcp.repository import (  # noqa: PLC0415
            McpDataAuthorization,
        )

        loader = get_default_managed_mcp_runtime_snapshot_loader()
        actor = current_user.get("_admin_actor")
        if loader is None or not isinstance(actor, AdminRequestActor):
            return {}
        with loader.authorize(
            McpDataAuthorization(
                actor_id=actor.canonical_user_id,
                access_token=actor.access_token,
            )
        ):
            return await loader.load_mcp_app_resource_bindings(
                actor.canonical_user_id,
                None,
            )
    except Exception:  # noqa: BLE001 - history must retain ordinary MCP output
        logger.warning(
            "Managed MCP App history descriptor projection failed safely."
        )
        return {}


async def _resolve_platform_model_alias(
    user_id: int,
    client_model_alias: str | None,
    system_config: Mapping[str, Any],
    *,
    access_token: str | None = None,
) -> str:
    return (
        await _resolve_platform_model_selection(
            user_id,
            client_model_alias,
            system_config,
            access_token=access_token,
        )
    ).model_alias


async def _resolve_platform_model_selection(
    user_id: int,
    client_model_alias: str | None,
    system_config: Mapping[str, Any],
    *,
    access_token: str | None = None,
) -> GatewayModel | str:
    try:
        catalog_factory = (
            GatewayModelCatalogClient
            if access_token is None
            else lambda _canonical_user_id: GatewayModelCatalogClient(
                access_token=access_token
            )
        )
        return await asyncio.to_thread(
            resolve_platform_model,
            user_id,
            client_model_alias,
            catalog_client_factory=catalog_factory,
            system_config_reader=lambda _canonical_user_id: system_config,
        )
    except GatewayInferenceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"error_code": exc.code, "message": "The platform model catalog is unavailable."},
        ) from exc


def _coerce_sandbox_network_mode(value: object) -> str:
    mode = str(value or "").strip().lower()
    return mode if mode in _SANDBOX_NETWORK_MODES else "allowlist"


def _coerce_string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _parse_vector_query_param(value: Optional[str]) -> dict[str, Any] | None:
    """Parse the reserved vector_query query-param JSON object."""
    if value is None or not value.strip():
        return None
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid vector_query JSON") from exc
    if not isinstance(parsed, dict):
        raise HTTPException(status_code=400, detail="vector_query must be a JSON object")
    return parsed


def _extract_message_text(message: Any) -> str:
    """Extract plain text from a message value.

    Accepts either a plain ``str`` or a Vercel AI SDK ``UIMessage`` dict
    (has ``parts`` list with ``{type: 'text', text: '...'}`` entries).
    """
    if isinstance(message, str):
        return message
    if isinstance(message, dict):
        parts = message.get("parts") or []
        texts = [
            p.get("text", "")
            for p in parts
            if isinstance(p, dict) and p.get("type") == "text"
        ]
        text = " ".join(t for t in texts if t).strip()
        if not text:
            text = str(message.get("content") or "").strip()
        return text
    return str(message) if message else ""


class ChatAttachment(BaseModel):
    type: str  # "file" | "source-url"
    url: str
    storageKey: Optional[str] = None
    mediaType: Optional[str] = None
    filename: Optional[str] = None
    size: Optional[int] = None
    workspacePath: Optional[str] = None
    savedAt: Optional[str] = None
    hash: Optional[str] = None

    def to_dict(self) -> dict:
        return self.model_dump(exclude_none=True)


# Client-supplied plugin/settings controls rejected by Deck Chat requests
# (deck-integration-delta §AgentRunOptions boundary).  Covers snake_case,
# camelCase and the literal CLI flag spelling.
_FORBIDDEN_CLIENT_PLUGIN_FIELDS = frozenset({
    "settings_json", "settingsJson", "settings",
    "claude_settings_json", "claudeSettingsJson",
    "local_plugin_paths", "localPluginPaths",
    "claude_plugin_paths", "claudePluginPaths",
    "plugin_paths", "pluginPaths", "plugins",
    "plugin_dir", "pluginDir", "plugin-dir",
    "enabled_plugins", "enabledPlugins",
    "plugin_installation_path", "pluginInstallationPath",
    "package_installation_path", "packageInstallationPath",
})


class ClaudeAgentRequestBody(BaseModel):
    thread_id: Optional[str] = None
    id: Optional[str] = None
    message: Any = None
    reconnect: bool = False
    resume: bool = False
    tool_choice: str = Field(default="auto", validation_alias=AliasChoices("tool_choice", "toolChoice"))
    chatModel: Optional[dict] = None
    model: Optional[str] = None
    max_turns: int = 100
    cwd: Optional[str] = None
    attachments: List[ChatAttachment] = []
    editor_state: Optional[dict] = None
    system_prompt: Optional[str] = Field(default=None, validation_alias=AliasChoices("system_prompt", "systemPrompt"))
    deck_id: Optional[str] = Field(default=None, min_length=1, validation_alias=AliasChoices("deck_id", "deckId"))
    voice_id: Optional[str] = Field(default=None, min_length=1, validation_alias=AliasChoices("voice_id", "voiceId"))

    @model_validator(mode="before")
    @classmethod
    def _reject_client_plugin_controls(cls, data: Any) -> Any:
        """Deck Chat requests must never carry plugin/settings controls.

        Rejected (deck-integration-delta §AgentRunOptions boundary): plugin
        paths, settings JSON, ``--plugin-dir`` values, package installation
        paths, and dynamic enabledPlugins maps.  Plugin loading is a
        server-side workspace bootstrap concern only.
        """
        if isinstance(data, dict):
            banned = _FORBIDDEN_CLIENT_PLUGIN_FIELDS.intersection(data.keys())
            if banned:
                raise ValueError(
                    "Client-supplied plugin or settings fields are not accepted: "
                    + ", ".join(sorted(banned))
                )
        return data

    @model_validator(mode="after")
    def _normalize_model_alias(self):
        chat_model = self.chatModel if isinstance(self.chatModel, dict) else {}
        chat_alias = chat_model.get("model")
        if chat_alias is not None and not isinstance(chat_alias, str):
            raise ValueError("chatModel.model must be a stable model alias")
        if self.model and chat_alias and self.model != chat_alias:
            raise ValueError("model and chatModel.model must identify the same alias")
        candidate = (self.model or chat_alias or "").strip()
        if candidate and not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,119}", candidate):
            raise ValueError("model must be a stable model alias")
        self.model = candidate or None
        return self

    def get_thread_id(self) -> Optional[str]:
        return self.thread_id or self.id

    def get_message_text(self) -> str:
        return _extract_message_text(self.message)


class QueueSelectBody(BaseModel):
    expected_revision: int = Field(gt=0)


class ToolConfirmRequestBody(BaseModel):
    thread_id: str
    tool_call_id: str
    approved: bool
    reason: Optional[str] = None
    answers: Optional[dict] = None


class CreateThreadResponseBody(BaseModel):
    thread_id: str
    deck_id: Optional[str] = None
    voice_id: Optional[str] = None


class CreateThreadRequestBody(BaseModel):
    deck_id: Optional[str] = Field(default=None, min_length=1, validation_alias=AliasChoices("deck_id", "deckId"))
    voice_id: Optional[str] = Field(default=None, min_length=1, validation_alias=AliasChoices("voice_id", "voiceId"))
    title: Optional[str] = Field(default=None, max_length=200)


class PublicSkillCommandDto(BaseModel):
    command: str
    name: str


class PublicSkillCommandCatalogDto(BaseModel):
    commands: list[PublicSkillCommandDto]


@router.get(
    "/api/claude-agent/skill-commands",
    response_model=PublicSkillCommandCatalogDto,
)
async def claude_agent_skill_commands(
    current_user: dict = Depends(get_current_user),
):
    """Return validated backend-owned common Skills for Chat slash discovery."""

    del current_user
    try:
        packages = discover_builtin_skill_packages((COMMON_SKILL_NAMESPACE,))
    except (BuiltinSkillPackageError, OSError) as exc:
        logger.error("Backend-owned common Skill catalog is unavailable")
        raise HTTPException(
            status_code=503,
            detail={
                "error_code": "COMMON_SKILL_CATALOG_UNAVAILABLE",
                "message": "Common Skills are temporarily unavailable.",
            },
        ) from exc
    return PublicSkillCommandCatalogDto(
        commands=[
            PublicSkillCommandDto(
                command=f"/{package.skill_id}",
                name=package.skill_id,
            )
            for package in packages
        ],
    )


@router.post("/api/claude-agent")
async def claude_agent_stream(
    body: ClaudeAgentRequestBody,
    current_user: dict = Depends(get_current_user),
    chat: AdminChatData = Depends(get_admin_chat_data),
    owner: AdminRequestAuth = Depends(get_admin_request_auth),
):
    """SSE streaming endpoint for Claude Agent.

    Returns ``text/event-stream``; each frame is a JSON object:
    ``{"type": "text-delta"|"tool-event"|"chat-message"|"message-final"|"finish"|"error", ...}``

    Requires a ``thread_id`` (created via ``POST /api/claude-agent/threads``).
    """
    user_id = current_user["user_id"]
    thread_id = body.get_thread_id()
    if not thread_id:
        raise HTTPException(status_code=400, detail="thread_id is required")

    thread = await _admin_thread(current_user, chat, thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")

    _msg_dict = body.message if isinstance(body.message, dict) else None
    message_id = _msg_dict.get("id") if _msg_dict else None
    if message_id is not None and (
        not isinstance(message_id, str) or not message_id
    ):
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "CHAT_MESSAGE_ID_INVALID",
                "message": "The message identifier must be non-empty text.",
            },
        )
    if isinstance(message_id, str) and message_id.startswith(
        _SERVER_MESSAGE_ID_PREFIXES
    ):
        raise HTTPException(
            status_code=422,
            detail={
                "error_code": "CHAT_RESERVED_MESSAGE_ID",
                "message": "The message identifier uses a reserved namespace.",
            },
        )

    if body.reconnect:
        snapshot = claude_agent_thread_factory.session_snapshot(thread_id)
        if snapshot is None or snapshot.get("lifecycle") != "running":
            raise HTTPException(status_code=409, detail="Thread is not running")

        request = ClaudeAgentRunRequest(
            user_id=str(user_id),
            thread_id=thread_id,
            reconnect=True,
            resume=body.resume,
        )

        async def generate_reconnect():
            async for frame in claude_agent_thread_factory.run_streaming(request):
                yield frame

        return streaming_sse_response(generate_reconnect())

    accepting_input = getattr(claude_agent_thread_factory, "accepting_input", None)
    if callable(accepting_input) and accepting_input(thread_id):
        raise HTTPException(
            status_code=409,
            detail={"error_code": "CHAT_INPUT_USE_QUEUE"},
        )
    # A lost process owner must not let the ordinary Chat path overtake a
    # durable queued or uncertain input.  Older Admin deployments without the
    # queue capability still serve their existing single-turn Chat contract.
    list_inputs = getattr(chat, "list_inputs", None)
    if callable(list_inputs):
        try:
            queue_snapshot = await _chat_invoke(
                current_user, list_inputs,
                chat_dto.ThreadIdInputDTO(thread_id=thread_id),
            )
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, dict) else {}
            if detail.get("error_code") != "ADMIN_CAPABILITY_UNAVAILABLE":
                raise
        else:
            if any(entry.status in ("queued", "selected", "dispatching", "state_unknown")
                   for entry in queue_snapshot.entries):
                raise HTTPException(
                    status_code=409,
                    detail={"error_code": "CHAT_INPUT_RECONCILIATION_REQUIRED"},
                )

    message_text = body.get_message_text()
    if not message_text:
        raise HTTPException(status_code=400, detail="message text is required")

    actor = current_user.get("_admin_actor")
    if not isinstance(actor, AdminRequestActor):
        raise HTTPException(status_code=503, detail="ADMIN_CONFIGURATION_INVALID")
    system_config = await invoke_admin_operation(
        current_user,
        AdminSystemConfigData(owner.client).get_user,
        SystemConfigGetInputDTO(),
    )

    requested_deck_id = body.deck_id
    persisted_deck_id = thread.get("deck_id")
    requested_voice_id = body.voice_id
    persisted_voice_id = thread.get("voice_id")
    if requested_deck_id and persisted_deck_id and requested_deck_id != persisted_deck_id:
        raise HTTPException(
            status_code=409,
            detail={
                "error_code": "CHAT_DECK_IMMUTABLE",
                "message": "The Deck cannot be changed after the conversation starts.",
            },
        )
    deck_context = None
    admin_deck_chat_context = None
    effective_deck_id = requested_deck_id or persisted_deck_id
    effective_voice_id = requested_voice_id or persisted_voice_id
    if effective_voice_id and not effective_deck_id:
        raise HTTPException(status_code=422, detail="voiceId requires deckId")
    if effective_deck_id:
        try:
            admin_deck_chat_context = await invoke_admin_operation(
                current_user,
                AdminDeckChatContextData(
                    owner.client,
                    canonical_user_id=actor.canonical_user_id,
                ).resolve,
                DeckChatContextInputDTO(
                    deck_id=str(effective_deck_id),
                    voice_id=(
                        str(effective_voice_id)
                        if effective_voice_id
                        else None
                    ),
                ),
            )
            deck_context = await DeckChatContextAssembler(
                admin_deck_chat_context.context_for(
                    actor_id=str(user_id),
                    deck_id=str(effective_deck_id),
                    voice_id=(
                        str(effective_voice_id)
                        if effective_voice_id
                        else None
                    ),
                ),
                selected_voice_id=(
                    str(effective_voice_id)
                    if effective_voice_id
                    else None
                ),
            ).resolve()
        except DeckChatContextError as exc:
            raise HTTPException(
                status_code=exc.status_code,
                detail={"error_code": exc.code, "message": str(exc)},
            ) from exc
        if not persisted_deck_id and not (await _chat_invoke(current_user, chat.bind_deck,
            chat_dto.ThreadBindDeckInputDTO(thread_id=thread_id, deck_id=str(effective_deck_id)))).changed:
            raise HTTPException(
                status_code=409,
                detail={
                    "error_code": "CHAT_DECK_IMMUTABLE",
                    "message": "The conversation Deck changed concurrently.",
                },
            )
        if requested_voice_id and requested_voice_id != persisted_voice_id and not (await _chat_invoke(current_user, chat.select_voice,
            chat_dto.ThreadSelectVoiceInputDTO(thread_id=thread_id, deck_id=str(effective_deck_id), voice_id=str(requested_voice_id),
                expected_voice_id=str(persisted_voice_id) if persisted_voice_id else None))).changed:
            raise HTTPException(
                status_code=409,
                detail={
                    "error_code": "CHAT_AGENT_CONFLICT",
                    "message": "The conversation Agent changed concurrently. Reload and try again.",
                },
            )

    workflow_request_id = str(uuid4())
    try:
        workflow_resolution = await run_in_threadpool(owner.workflow_context, actor, thread_id, workflow_request_id)
    except AdminDataError as exc:
        raise HTTPException(status_code=exc.status_code, detail={"error_code": exc.code, "request_id": exc.request_id or workflow_request_id, "outcome_unknown": exc.outcome_unknown}) from None
    if workflow_resolution.context is not None and (
        workflow_resolution.context.deck_id != effective_deck_id
        or workflow_resolution.context.agent_id != effective_voice_id
    ):
        raise HTTPException(status_code=409, detail={"error_code": "DREAM_THREAD_BINDING_CONFLICT", "request_id": workflow_request_id, "outcome_unknown": False})
    editor_session_id = None
    if body.editor_state is not None:
        editor_session_id = body.editor_state.get("id")
        if not isinstance(editor_session_id, str) or not editor_session_id:
            raise HTTPException(
                status_code=422,
                detail={
                    "error_code": "EDITOR_SESSION_ID_INVALID",
                    "message": "The Editor Session identifier must be non-empty text.",
                },
            )
    platform_model = await _resolve_platform_model_selection(
        user_id,
        body.model,
        system_config,
        access_token=actor.access_token,
    )
    if isinstance(platform_model, str):
        # Compatibility for isolated route tests/custom injection points that
        # intentionally resolve only an alias.
        platform_model_alias = platform_model
        model_runtime_env = {}
    else:
        # The repository supports both ``services`` and ``backend.services``
        # import roots. The same validated frozen dataclass can therefore have
        # two Python class identities in tests; narrow by the only compatibility
        # variant (str) instead of dropping authenticated Runtime metadata.
        platform_model_alias = platform_model.model_alias
        model_runtime_env = platform_model.claude_code_runtime_env()

    message_parts = list(_msg_dict.get("parts") or []) if _msg_dict else None

    # Process attachments: download from file storage and sync to workspace when
    # Workspace Mode is enabled.  When disabled, keep the turn chat-only and do
    # not create a thread workspace as a side effect of attachments.
    attachment_payloads: list[AttachmentPayload] = []
    if body.attachments:
        try:
            workspace_enabled = bool(system_config.get("workspace_enabled", True))
            workspace_path = None
            if workspace_enabled:
                workspace_path = get_or_create_workspace(
                    thread_id,
                    sandbox_enabled=resolve_sandbox_enabled(),
                    sandbox_network_mode=_coerce_sandbox_network_mode(
                        system_config.get("sandbox_network_mode")
                    ),
                    sandbox_network_allowed_domains=_coerce_string_list(
                        system_config.get("sandbox_network_allowed_domains")
                    ),
                )
            else:
                logger.info(
                    "[Claude Agent API] Workspace Mode disabled; skipping "
                    "attachment workspace sync for thread_id=%s",
                    thread_id,
                )
        except Exception as exc:
            raise HTTPException(status_code=500, detail="Failed to load workspace settings") from exc

        if workspace_path is not None:
            async def _download_file(url: str, storage_key: Optional[str] = None):
                if not storage_key:
                    raise WorkspaceFileSyncError(
                        WorkspaceFileSyncErrorCode.INVALID_ATTACHMENT,
                        f"Attachment storage key is required for file download: {url}",
                        400,
                        {"url": url},
                    )
                content = await server_file_storage.download(storage_key)
                metadata = await server_file_storage.get_metadata(storage_key)
                content_type = (metadata.content_type if metadata else None) or "application/octet-stream"
                return content, content_type

            workspace_sync_error = None
            workspace_file_parts: list = []
            try:
                workspace_file_parts = await sync_attachments_to_workspace_files(
                    workspace_path=workspace_path,
                    attachments=[a.to_dict() for a in body.attachments],
                    download_file=_download_file,
                )
            except WorkspaceFileSyncError as exc:
                workspace_sync_error = normalize_workspace_file_sync_error(exc)
                logger.warning(
                    "[Claude Agent API] Workspace file sync degraded: %s", workspace_sync_error
                )
            except Exception as exc:
                workspace_sync_error = normalize_workspace_file_sync_error(exc)
                logger.warning(
                    "[Claude Agent API] Workspace file sync degraded: %s", workspace_sync_error
                )

            if workspace_file_parts:
                message_parts = inject_attachment_message_parts(
                    message_parts,
                    workspace_file_parts,
                )
                logger.info(
                    "[Claude Agent API] Injected %d workspace file parts into message",
                    len(workspace_file_parts),
                )

            # Build AttachmentPayload list from synced workspace files so that
            # images, PDFs, and text files are also passed as content blocks to Claude.
            for part in workspace_file_parts:
                rel_path = part.get("workspacePath")
                if not rel_path:
                    continue
                try:
                    file_bytes = (workspace_path / rel_path).read_bytes()
                    attachment_payloads.append(
                        AttachmentPayload(
                            name=part.get("fileName") or Path(rel_path).name,
                            media_type=part.get("mimeType") or "application/octet-stream",
                            data=base64.b64encode(file_bytes).decode("ascii"),
                        )
                    )
                except Exception as exc:
                    logger.warning(
                        "[Claude Agent API] Could not read workspace file for AttachmentPayload: %s — %s",
                        rel_path,
                        exc,
                    )

    message_metadata = (
        {
            "deckId": str(effective_deck_id) if effective_deck_id else None,
            "voiceId": str(effective_voice_id) if effective_voice_id else None,
        }
        if effective_deck_id or effective_voice_id
        else None
    )
    message_id = message_id or str(uuid4())

    # Construct long-turn owners only after all fallible request preparation.
    # Factory starts active keepers after admission and owns terminal cleanup.
    gateway_request_id = str(uuid4())
    try:
        gateway_runtime = await run_in_threadpool(
            owner.gateway_runtime,
            actor,
            workflow_resolution,
            gateway_request_id,
        )
    except AdminDataError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={
                "error_code": exc.code,
                "request_id": exc.request_id or gateway_request_id,
                "outcome_unknown": exc.outcome_unknown,
            },
        ) from None
    persistence_request_id = str(uuid4())
    try:
        turn_persistence = await run_in_threadpool(
            owner.turn_persistence,
            actor,
            workflow_resolution,
            persistence_request_id,
        )
    except AdminDataError as exc:
        await run_in_threadpool(gateway_runtime.close)
        raise HTTPException(
            status_code=exc.status_code,
            detail={
                "error_code": exc.code,
                "request_id": exc.request_id or persistence_request_id,
                "outcome_unknown": exc.outcome_unknown,
            },
        ) from None

    turn_persistence.bind_thread_tool_provider(_ThreadToolTurnProvider(
        loop=asyncio.get_running_loop(), current_user=current_user, chat=chat,
        owner=owner, source_thread_id=thread_id, source_message_id=message_id,
        timeout_seconds=owner.session_broker_settings.timeout_seconds,
    ))

    editor_request_id = str(uuid4())
    try:
        editor_runtime = await run_in_threadpool(
            owner.editor_runtime,
            actor,
            workflow_resolution,
            editor_request_id,
            initial_session_id=editor_session_id,
        )
    except AdminDataError as exc:
        await run_in_threadpool(gateway_runtime.close)
        await run_in_threadpool(turn_persistence.close)
        raise HTTPException(
            status_code=exc.status_code,
            detail={
                "error_code": exc.code,
                "request_id": exc.request_id or editor_request_id,
                "outcome_unknown": exc.outcome_unknown,
            },
        ) from None

    if message_id is not None:
        # One Admin transaction guards the control record, reserves the user
        # message and fills only a missing title. Service reuses this known
        # reservation, retaining the original command and request identity.
        resolved_user_parts = (
            list(message_parts)
            if message_parts
            else [{"type": "text", "text": ""}]
        )
        try:
            await run_in_threadpool(turn_persistence.persist_user, actor_id=str(user_id), thread_id=thread_id,
                parts=resolved_user_parts, message_id=message_id, metadata=message_metadata)
        except AdminDataError as exc:
            await run_in_threadpool(gateway_runtime.close)
            await run_in_threadpool(turn_persistence.close)
            await run_in_threadpool(editor_runtime.close)
            detail = {"error_code": exc.code, "request_id": exc.request_id, "outcome_unknown": exc.outcome_unknown}
            if exc.code == "CHAT_MESSAGE_IDENTITY_CONFLICT":
                detail["message"] = "The message identifier is already bound."
            raise HTTPException(status_code=exc.status_code, detail=detail) from None

    request = ClaudeAgentRunRequest(
        user_id=str(user_id),
        thread_id=thread_id,
        resume=body.resume,
        tool_choice=body.tool_choice,
        model=platform_model_alias,
        model_runtime_env=model_runtime_env,
        admin_workflow_resolution=workflow_resolution,
        admin_turn_persistence=turn_persistence,
        admin_gateway_runtime=gateway_runtime,
        admin_editor_runtime=editor_runtime,
        admin_deck_chat_context=admin_deck_chat_context,
        max_turns=body.max_turns,
        cwd=body.cwd,
        message_id=message_id,
        message_parts=message_parts,
        attachments=attachment_payloads or None,
        editor_state=body.editor_state,
        system_prompt=(
            deck_context.system_prompt
            if deck_context is not None
            else body.system_prompt or None
        ),
        message_metadata=message_metadata,
        # NOTE (2026-08-02, deck-integration-delta): Deck plugin
        # settings/paths are no longer passed here.  The thread-locked Deck's
        # plugin installations are packed into the thread workspace by the
        # agent service (workspace bootstrap) and loaded by the CLI via
        # --plugin-dir from the server-controlled launch manifest.
    )

    async def generate():
        async for frame in claude_agent_thread_factory.run_streaming(request):
            yield frame

    return streaming_sse_response(generate())


@router.get("/api/claude-agent/chat-history")
async def claude_agent_chat_history(
    current_user: dict = Depends(get_current_user),
    chat: AdminChatData = Depends(get_admin_chat_data),
):
    """Return chat thread history for the authenticated user.

    Returns the list of chat threads (newest first) so the frontend
    can display the user's past conversations.
    """
    result = await _chat_invoke(current_user, chat.list_threads, chat_dto.ThreadListInputDTO(deck_id=None, limit=None, offset=0))
    return {"threads": [thread.model_dump() for thread in result.threads]}


@router.post("/api/claude-agent/threads", response_model=CreateThreadResponseBody)
async def claude_agent_create_thread(
    current_user: dict = Depends(get_current_user),
    chat: AdminChatData = Depends(get_admin_chat_data),
    body: Optional[CreateThreadRequestBody] = None,
):
    """Create a new chat thread and return its ``thread_id``.

    Call this endpoint when the user clicks "New Chat".  The returned
    ``thread_id`` must be included in every subsequent
    ``POST /api/claude-agent`` request for that conversation.
    """
    deck_id = body.deck_id if body else None
    voice_id = body.voice_id if body else None
    title = body.title if body else None
    if voice_id and not deck_id:
        raise HTTPException(status_code=422, detail="voiceId requires deckId")
    result = await _chat_invoke(current_user, chat.create_thread, chat_dto.ThreadCreateInputDTO(deck_id=deck_id, voice_id=voice_id, title=title))
    return result.model_dump()


@router.get("/api/claude-agent/threads/{thread_id}/plugin-load-receipt")
async def claude_agent_thread_plugin_load_receipt(
    thread_id: str,
    current_user: dict = Depends(get_current_user),
    chat: AdminChatData = Depends(get_admin_chat_data),
):
    """Return the workspace plugin pack + launch receipt for a thread.

    The receipt is produced by the server-side workspace packer when the
    thread's locked Deck has enabled Claude plugin installations.  It carries
    package spec, resolved version and artifact digest per plugin, plus the
    frozen flag.  A thread without plugins returns an empty plugin list.
    """
    user_id = current_user["user_id"]
    thread = await _admin_thread(current_user, chat, thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")

    try:
        from services.claude_plugin import workspace_packer as _packer
    except ModuleNotFoundError:
        from backend.services.claude_plugin import workspace_packer as _packer

    payload: dict[str, Any] = {
        "thread_id": thread_id,
        "deck_id": thread.get("deck_id"),
        "workspace_found": False,
        "receipt": None,
        "launch_manifest": None,
    }
    try:
        root = get_workspace_root().resolve(strict=False)
        workspace = (root / thread_id).resolve(strict=False)
        workspace.relative_to(root)
    except (OSError, RuntimeError, ValueError):
        return payload
    if not workspace.is_dir():
        return payload
    payload["workspace_found"] = True
    receipt_path = workspace / _packer.PACK_RECEIPT_RELATIVE_PATH
    if receipt_path.is_file():
        try:
            payload["receipt"] = json.loads(receipt_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            payload["receipt"] = None
    manifest_path = workspace / _packer.LAUNCH_MANIFEST_RELATIVE_PATH
    if manifest_path.is_file():
        try:
            payload["launch_manifest"] = json.loads(
                manifest_path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError):
            payload["launch_manifest"] = None
    return payload


@router.get("/api/claude-agent/threads")
async def claude_agent_list_threads(
    deck_id: Optional[str] = Query(default=None),
    query: Optional[str] = Query(default=None),
    search_scope: str = Query(default="all"),
    retrieval_mode: Optional[str] = Query(default=None),
    vector_query: Optional[str] = Query(default=None),
    min_score: Optional[float] = Query(default=None, ge=0, le=1),
    limit: Optional[chat_dto.PositiveSafeInteger] = Query(default=None, ge=1),
    offset: chat_dto.NonnegativeSafeInteger = Query(default=0, ge=0),
    current_user: dict = Depends(get_current_user),
    chat: AdminChatData = Depends(get_admin_chat_data),
):
    """Return chat threads, optionally searched by title and message content.

    Default listing keeps the original newest-first behavior.  Search uses the
    configured retriever registry; ``fuzzy`` is the default, while ``vector`` is
    an interface-only placeholder aligned with get_sessions_range.vector_query.
    """
    user_id = current_user["user_id"]
    vector_query_obj = _parse_vector_query_param(vector_query)

    if not is_chat_history_search_requested(
        query,
        retrieval_mode=retrieval_mode,
        vector_query=vector_query_obj,
    ):
        result = await _chat_invoke(current_user, chat.list_threads, chat_dto.ThreadListInputDTO(deck_id=deck_id, limit=limit, offset=offset))
        return {"threads": [thread.model_dump() for thread in result.threads]}

    config = build_chat_thread_search_config(
        query=query,
        retrieval_mode=retrieval_mode,
        search_scope=search_scope,
        min_score=min_score,
        limit=limit,
        vector_query=vector_query_obj,
    )
    if config is None:
        raise HTTPException(
            status_code=400,
            detail="Invalid chat history retrieval_mode or search_scope",
        )

    candidates = []
    if config.retrieval_mode != "vector":
        result = await _chat_invoke(current_user, chat.search_threads, chat_dto.ThreadSearchInputDTO(deck_id=deck_id))
        candidates = [thread.model_dump() for thread in result.threads]
    outcome = search_chat_threads(candidates, config)
    payload: dict[str, Any] = {
        "threads": outcome.threads,
        "retrieval": outcome.retrieval,
    }
    if outcome.warnings:
        payload["warnings"] = outcome.warnings
    if not outcome.ok:
        payload["ok"] = False
        payload["error"] = outcome.error
        payload["detail"] = outcome.detail
    return payload


@router.get("/api/claude-agent/threads/{thread_id}/messages")
async def claude_agent_thread_messages(
    thread_id: str,
    limit: Annotated[int | None, Query(ge=1, le=100)] = None,
    cursor: str | None = None,
    known_latest_message_id: str | None = None,
    current_user: dict = Depends(get_current_user),
    chat: AdminChatData = Depends(get_admin_chat_data),
):
    """Return legacy full history or one stable newest-to-older message page.

    Returns 404 if the thread does not exist or belongs to another user.
    """
    user_id = current_user["user_id"]
    thread = await _admin_thread(current_user, chat, thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    if limit is None:
        if cursor is not None or known_latest_message_id is not None:
            raise HTTPException(
                status_code=400,
                detail="limit is required for cursor pagination",
            )
        mcp_app_resource_bindings = (
            await _load_current_user_mcp_app_resource_bindings(current_user)
        )
        result = await _chat_invoke(current_user, chat.list_messages, chat_dto.ThreadIdInputDTO(thread_id=thread_id))
        messages = [
            _project_chat_message_for_client(
                message,
                mcp_app_resource_bindings=mcp_app_resource_bindings,
            )
            for message in (item.model_dump() for item in result.messages)
        ]
        return {
            "thread": _project_chat_thread_for_client(thread),
            "messages": messages,
        }
    if cursor is not None and known_latest_message_id is not None:
        raise HTTPException(
            status_code=400,
            detail="cursor and known_latest_message_id are mutually exclusive",
        )
    if known_latest_message_id is not None:
        if not known_latest_message_id:
            raise HTTPException(status_code=400, detail="known latest id is invalid")
        latest_message_id = (await _chat_invoke(current_user, chat.latest_message, chat_dto.ThreadIdInputDTO(thread_id=thread_id))).message_id
        if latest_message_id == known_latest_message_id:
            return {
                "thread": _project_chat_thread_for_client(thread),
                "messages": [],
                "next_cursor": None,
                "has_more": False,
                "latest_message_id": latest_message_id,
                "unchanged": True,
            }

    before_created_at: datetime | None = None
    before_id: str | None = None
    before_created_at_is_null = False
    if cursor is not None:
        try:
            before_created_at, before_id, before_created_at_is_null = (
                _decode_chat_message_cursor(thread_id, cursor)
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    before = None
    if before_id is not None:
        before = chat_dto.MessageBeforeDTO(id=before_id, created_at=None if before_created_at_is_null else before_created_at.isoformat())
    page = (await _chat_invoke(current_user, chat.message_page, chat_dto.MessagePageInputDTO(thread_id=thread_id, limit=limit, before=before))).model_dump()
    page_messages = page["messages"]
    if not isinstance(page_messages, list):
        raise RuntimeError("chat message page result is invalid")
    next_cursor = None
    if page.get("has_more") is True and page_messages:
        next_cursor = _encode_chat_message_cursor(thread_id, page_messages[0])
    mcp_app_resource_bindings = (
        await _load_current_user_mcp_app_resource_bindings(current_user)
    )
    return {
        "thread": _project_chat_thread_for_client(thread),
        "messages": [
            _project_chat_message_for_client(
                message,
                mcp_app_resource_bindings=mcp_app_resource_bindings,
            )
            for message in page_messages
        ],
        "next_cursor": next_cursor,
        "has_more": page.get("has_more") is True,
        "latest_message_id": page.get("latest_message_id"),
        "unchanged": False,
    }


@router.get(
    "/api/claude-agent/threads/{thread_id}/messages/{message_id}/process"
)
async def claude_agent_thread_message_process(
    thread_id: str,
    message_id: str,
    current_user: dict = Depends(get_current_user),
    chat: AdminChatData = Depends(get_admin_chat_data),
):
    """Return one owned projected assistant message's canonical process parts."""

    user_id = current_user["user_id"]
    thread = await _admin_thread(current_user, chat, thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="Message process not found")
    result = await _chat_invoke(current_user, chat.process_detail, chat_dto.MessageDetailInputDTO(thread_id=thread_id, message_id=message_id))
    if result.message is None:
        raise HTTPException(status_code=404, detail="Message process not found")
    mcp_app_resource_bindings = (
        await _load_current_user_mcp_app_resource_bindings(current_user)
    )
    return _project_chat_message_for_client(
        result.message.model_dump(),
        mcp_app_resource_bindings=mcp_app_resource_bindings,
    )


@router.get("/api/claude-agent/threads/{thread_id}/subagents")
async def claude_agent_thread_subagents(
    thread_id: str,
    current_user: dict = Depends(get_current_user),
    chat: AdminChatData = Depends(get_admin_chat_data),
):
    """Return thread-owned subagent tasks without exposing raw transcripts."""

    user_id = current_user["user_id"]
    thread = await _admin_thread(current_user, chat, thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    runtime_snapshot = claude_agent_thread_factory.session_snapshot(thread_id)
    runtime_running = (
        runtime_snapshot is not None
        and runtime_snapshot.get("lifecycle") == "running"
    )
    return await asyncio.to_thread(
        build_thread_subagents_payload,
        thread_id,
        get_workspace_root(),
        runtime_running=runtime_running,
    )


@router.get("/api/claude-agent/threads/{thread_id}/stream")
async def claude_agent_thread_stream(
    thread_id: str,
    current_user: dict = Depends(get_current_user),
    chat: AdminChatData = Depends(get_admin_chat_data),
):
    """SSE reconnect endpoint — subscribe to an in-flight turn's EventBus.

    Replays buffered frames then streams live events until the turn completes.
    Returns 409 when the thread is not currently running.
    """
    user_id = current_user["user_id"]
    thread = await _admin_thread(current_user, chat, thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")

    snapshot = claude_agent_thread_factory.session_snapshot(thread_id)
    if snapshot is None or snapshot.get("lifecycle") != "running":
        raise HTTPException(status_code=409, detail="Thread is not running")

    async def generate():
        async for frame in claude_agent_thread_factory.subscribe_stream(thread_id):
            yield frame

    return streaming_sse_response(generate())


@router.get("/api/claude-agent/threads/{thread_id}/inputs")
async def claude_agent_thread_inputs(
    thread_id: str,
    current_user: dict = Depends(get_current_user),
    chat: AdminChatData = Depends(get_admin_chat_data),
):
    if await _admin_thread(current_user, chat, thread_id) is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    result = await _chat_invoke(
        current_user, chat.list_inputs,
        chat_dto.ThreadIdInputDTO(thread_id=thread_id),
    )
    return {
        "entries": [entry.model_dump() for entry in result.entries],
        "local_owner": claude_agent_thread_factory.accepting_input(thread_id),
    }


@router.post("/api/claude-agent/threads/{thread_id}/inputs")
async def claude_agent_thread_enqueue_input(
    thread_id: str,
    body: ClaudeAgentRequestBody,
    current_user: dict = Depends(get_current_user),
    chat: AdminChatData = Depends(get_admin_chat_data),
):
    thread = await _admin_thread(current_user, chat, thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    if body.get_thread_id() not in (None, thread_id):
        raise HTTPException(status_code=422, detail={"error_code": "CHAT_INPUT_THREAD_MISMATCH"})
    if body.reconnect or body.attachments or body.editor_state is not None:
        raise HTTPException(status_code=422, detail={"error_code": "CHAT_INPUT_UNSUPPORTED_PAYLOAD"})
    if body.deck_id is not None and body.deck_id != thread.get("deck_id"):
        raise HTTPException(status_code=409, detail={"error_code": "CHAT_DECK_IMMUTABLE"})
    if body.voice_id is not None and body.voice_id != thread.get("voice_id"):
        raise HTTPException(status_code=409, detail={"error_code": "CHAT_AGENT_CONFLICT"})
    message = body.message if isinstance(body.message, dict) else None
    message_id = message.get("id") if message else None
    parts = message.get("parts") if message else None
    text = body.get_message_text()
    if (
        not isinstance(message_id, str) or not message_id
        or message_id.startswith(_SERVER_MESSAGE_ID_PREFIXES)
        or not isinstance(parts, list) or len(parts) != 1
        or not all(isinstance(part, dict) and part.get("type") == "text"
                   and isinstance(part.get("text"), str) for part in parts)
        or not text.strip()
    ):
        raise HTTPException(status_code=422, detail={"error_code": "CHAT_INPUT_INVALID"})
    actor = current_user.get("_admin_actor")
    if not isinstance(actor, AdminRequestActor):
        raise HTTPException(status_code=503, detail={"error_code": "ADMIN_CONFIGURATION_INVALID"})
    try:
        entry = await claude_agent_thread_factory.enqueue_input(
            thread_id=thread_id, user_id=str(current_user["user_id"]),
            message_id=message_id, parts=parts, title_candidate=text,
            tool_choice=body.tool_choice, chat=chat, access_token=actor.access_token,
        )
    except AdminDataError as exc:
        raise HTTPException(status_code=exc.status_code, detail={
            "error_code": exc.code, "request_id": exc.request_id,
            "outcome_unknown": exc.outcome_unknown,
        }) from None
    except RuntimeError as exc:
        if str(exc) == "CHAT_INPUT_OWNER_UNAVAILABLE":
            raise HTTPException(status_code=409, detail={"error_code": str(exc)}) from None
        raise
    return entry.model_dump()


@router.post("/api/claude-agent/threads/{thread_id}/inputs/{message_id}/select")
async def claude_agent_thread_select_input(
    thread_id: str,
    message_id: str,
    body: QueueSelectBody,
    current_user: dict = Depends(get_current_user),
    chat: AdminChatData = Depends(get_admin_chat_data),
):
    if await _admin_thread(current_user, chat, thread_id) is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    try:
        entry, interrupt_signalled = await claude_agent_thread_factory.select_input(
            thread_id=thread_id, user_id=str(current_user["user_id"]),
            message_id=message_id, expected_revision=body.expected_revision,
        )
    except AdminDataError as exc:
        raise HTTPException(status_code=exc.status_code, detail={
            "error_code": exc.code, "request_id": exc.request_id,
            "outcome_unknown": exc.outcome_unknown,
        }) from None
    except RuntimeError as exc:
        if str(exc) in ("CHAT_INPUT_OWNER_UNAVAILABLE", "CHAT_INPUT_PERSISTENCE_UNAVAILABLE"):
            raise HTTPException(status_code=409, detail={"error_code": str(exc)}) from None
        raise
    return {"entry": entry.model_dump(), "interrupt_signalled": interrupt_signalled}


@router.post("/api/claude-agent/threads/{thread_id}/inputs/{message_id}/cancel")
async def claude_agent_thread_cancel_input(
    thread_id: str,
    message_id: str,
    body: QueueSelectBody,
    current_user: dict = Depends(get_current_user),
    chat: AdminChatData = Depends(get_admin_chat_data),
):
    """Cancel only one queued input under Admin's owner and revision checks."""
    if await _admin_thread(current_user, chat, thread_id) is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    snapshot = await _chat_invoke(
        current_user, chat.list_inputs,
        chat_dto.ThreadIdInputDTO(thread_id=thread_id),
    )
    current = next((item for item in snapshot.entries if item.message_id == message_id), None)
    if current is None:
        raise HTTPException(status_code=404, detail={"error_code": "CHAT_INPUT_NOT_FOUND"})
    if current.status != "queued" or current.revision != body.expected_revision:
        raise HTTPException(status_code=409, detail={"error_code": "CHAT_INPUT_STATE_CONFLICT"})
    result = await _chat_invoke(
        current_user, chat.transition_input,
        chat_dto.QueueTransitionInputDTO(
            thread_id=thread_id,
            message_id=message_id,
            expected_revision=body.expected_revision,
            action="cancel",
            dispatch_turn_id=None,
        ),
    )
    return result.entry.model_dump()


_task_session_stream_drains: set[asyncio.Task[None]] = set()


async def _drain_task_session_stream(response, *, thread_id: str) -> None:
    """Keep the public child Thread SSE iterator alive without a browser owner."""
    try:
        async for _frame in response.body_iterator:
            pass
    except Exception:
        logger.exception("Task-session stream ended unexpectedly: thread_id=%s", thread_id)


async def _task_session_detail(current_user: dict, chat: AdminChatData, source_thread_id: str, task_id: str):
    if await _admin_thread(current_user, chat, source_thread_id) is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    result = await _chat_invoke(current_user, chat.get_task_session,
        chat_dto.TaskSessionGetInputDTO(source_thread_id=source_thread_id, task_id=task_id))
    if result.task is None:
        raise HTTPException(status_code=404, detail={"error_code": "TASK_SESSION_NOT_FOUND"})
    return result.task


async def _task_session_status(current_user: dict, chat: AdminChatData,
                               task: chat_dto.TaskSessionDTO) -> tuple[str, bool, str | None, str | None]:
    """Project a committed final assistant result without inferring it from text."""
    if task.launch_status in ("pending", "failed"):
        return task.launch_status, False, None, None
    runtime = claude_agent_thread_factory.session_snapshot(task.thread_id)
    if runtime and runtime.get("lifecycle") == "running":
        return "running", True, None, None
    page = await _chat_invoke(current_user, chat.message_page,
        chat_dto.MessagePageInputDTO(thread_id=task.thread_id, limit=1, before=None))
    latest = page.messages[-1] if page.messages else None
    if (latest is not None and latest.role == "assistant"
        and not latest.metadata_decode_error
        and isinstance(latest.metadata, dict)
        and latest.metadata.get("turnStatus") == "completed"
        and latest.metadata.get("is_partial") is not True
        and latest.history_projection_version == 1
        and isinstance(latest.history_final_text, str)
        and latest.history_final_text.strip()):
        return "completed", False, latest.id, latest.history_final_text
    if runtime and runtime.get("lifecycle") == "idle":
        target = await _admin_thread(current_user, chat, task.thread_id)
        if target and target.get("claude_session_id"):
            return "idle", False, None, None
    return "state_unknown", False, None, None


async def _task_session_launch_initial(
    *, task: chat_dto.TaskSessionDTO, current_user: dict, chat: AdminChatData,
    owner: AdminRequestAuth,
) -> dict:
    claim = await _chat_invoke(current_user, chat.launch_task_session,
        chat_dto.TaskSessionLaunchInputDTO(
            source_thread_id=task.source_thread_id, task_id=task.task_id,
            action="claim", error_code=None,
        ))
    if not claim.changed:
        return {"task_id": task.task_id, "thread_id": task.thread_id,
                "launch_status": claim.task.launch_status,
                "dispatch_started": False}
    try:
        response = await claude_agent_stream(
            ClaudeAgentRequestBody(
                thread_id=task.thread_id, resume=False,
                message={"id": task.initial_message_id, "role": "user",
                         "parts": [{"type": "text", "text": task.initial_message}]},
            ), current_user=current_user, chat=chat, owner=owner,
        )
    except Exception as exc:
        code = "TASK_SESSION_LAUNCH_FAILED"
        if isinstance(exc, HTTPException) and isinstance(exc.detail, dict):
            candidate = exc.detail.get("error_code")
            if isinstance(candidate, str) and candidate:
                code = candidate
        try:
            await _chat_invoke(current_user, chat.launch_task_session,
                chat_dto.TaskSessionLaunchInputDTO(
                    source_thread_id=task.source_thread_id, task_id=task.task_id,
                    action="fail", error_code=code,
                ))
        except Exception:
            logger.exception("Task-session launch failure state could not be saved: task_id=%s", task.task_id)
            return {"task_id": task.task_id, "thread_id": task.thread_id,
                    "launch_status": "starting", "dispatch_started": False,
                    "error_code": "TASK_SESSION_STATE_UNKNOWN"}
        return {"task_id": task.task_id, "thread_id": task.thread_id,
                "launch_status": "failed", "dispatch_started": False,
                "error_code": code}
    drain = asyncio.create_task(_drain_task_session_stream(response, thread_id=task.thread_id),
                                name=f"task-session-stream-{task.task_id}")
    _task_session_stream_drains.add(drain)
    drain.add_done_callback(_task_session_stream_drains.discard)
    return {"task_id": task.task_id, "thread_id": task.thread_id,
            "launch_status": "starting", "dispatch_started": True}


class _ThreadToolTurnProvider:
    """Host-only bridge from one MCP turn to the authorized Chat/Thread path."""

    def __init__(self, *, loop: asyncio.AbstractEventLoop, current_user: dict,
                 chat: AdminChatData, owner: AdminRequestAuth,
                 source_thread_id: str, source_message_id: str,
                 timeout_seconds: float) -> None:
        self._loop = loop
        self._current_user = current_user
        self._chat = chat
        self._owner = owner
        self._source_thread_id = source_thread_id
        self._source_message_id = source_message_id
        self._timeout_seconds = timeout_seconds

    def refresh_authorization(self, current_user: dict) -> None:
        """Accept only a fresh request actor for the same canonical user."""

        actor = current_user.get("_admin_actor")
        if (
            not isinstance(actor, AdminRequestActor)
            or str(current_user.get("user_id") or "")
            != str(self._current_user.get("user_id") or "")
            or actor.canonical_user_id != str(current_user.get("user_id"))
        ):
            raise AdminDataError("THREAD_TOOL_AUTHORIZATION_INVALID", 403)
        self._current_user = current_user

    def perform_thread_tool(self, request: ThreadToolCommandRequestDTO) -> ThreadToolCommandResultDTO:
        future = asyncio.run_coroutine_threadsafe(self._perform(request), self._loop)
        wait_seconds = (
            ((request.timeout_ms if request.timeout_ms is not None else 120_000) / 1000.0)
            if request.operation == "thread.wait"
            else 0.0
        )
        try:
            return future.result(timeout=self._timeout_seconds + wait_seconds)
        except FutureTimeoutError:
            if request.operation == "thread.wait":
                # Waiting is read-only. Stop the orphaned coroutine after the
                # transport deadline; the caller receives no invented result.
                future.cancel()
                raise AdminDataError(
                    "THREAD_WAIT_STATE_UNKNOWN", 503, request.request_id
                ) from None
            # A mutation may already have committed. Never cancel and retry it.
            raise AdminDataError("THREAD_TOOL_STATE_UNKNOWN", 503, request.request_id) from None
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, dict) else {}
            code = detail.get("error_code") if isinstance(detail.get("error_code"), str) else "THREAD_TOOL_UNAVAILABLE"
            raise AdminDataError(code, exc.status_code, request.request_id) from None
        except RuntimeError as exc:
            code = str(exc)
            if code in ("CHAT_INPUT_OWNER_UNAVAILABLE", "CHAT_INPUT_PERSISTENCE_UNAVAILABLE"):
                raise AdminDataError(code, 409, request.request_id) from None
            raise

    async def _perform(self, request: ThreadToolCommandRequestDTO) -> ThreadToolCommandResultDTO:
        source = self._source_thread_id
        user = self._current_user
        chat = self._chat

        if request.operation == "thread.create":
            prompt = str(request.prompt).strip()
            title = str(request.title).strip() if request.title is not None else prompt
            created = await _chat_invoke(user, chat.create_task_session,
                chat_dto.TaskSessionCreateInputDTO(
                    source_thread_id=source,
                    request_key=f"tool:{self._source_message_id}:{request.tool_call_id}:create",
                    title=title, initial_message=prompt,
                    source_message_id=None, expected_revision=None,
                ))
            if created.task is None:
                raise HTTPException(status_code=503, detail={"error_code": "THREAD_CREATE_UNAVAILABLE"})
            launched = await _task_session_launch_initial(
                task=created.task, current_user=user, chat=chat, owner=self._owner)
            return ThreadToolCommandResultDTO(
                thread_id=created.task.thread_id,
                title=created.task.title,
                status=launched["launch_status"],
                error_code=launched.get("error_code"),
            )

        if request.operation == "thread.list":
            limit = request.limit or 20
            if request.query is None:
                listed = await _chat_invoke(
                    user,
                    chat.list_threads,
                    chat_dto.ThreadListInputDTO(deck_id=None, limit=limit, offset=0),
                )
                rows = [item.model_dump() for item in listed.threads]
            else:
                candidates = await _chat_invoke(
                    user, chat.search_threads, chat_dto.ThreadSearchInputDTO(deck_id=None)
                )
                config = build_chat_thread_search_config(
                    query=request.query,
                    retrieval_mode="fuzzy",
                    search_scope="all",
                    limit=limit,
                )
                if config is None:
                    raise HTTPException(status_code=400, detail={"error_code": "THREAD_QUERY_INVALID"})
                outcome = search_chat_threads(
                    [item.model_dump() for item in candidates.threads], config
                )
                if not outcome.ok:
                    raise HTTPException(status_code=503, detail={"error_code": "THREAD_SEARCH_UNAVAILABLE"})
                rows = outcome.threads
            return ThreadToolCommandResultDTO(
                status="ok",
                threads=[
                    ThreadToolThreadDTO(
                        thread_id=str(row["id"]),
                        title=row.get("title"),
                        created_at=row.get("created_at"),
                        updated_at=row.get("updated_at"),
                    )
                    for row in rows
                ],
            )

        if request.operation == "thread.wait":
            return await self._wait_threads(request)

        target_thread_id = str(request.thread_id)
        target = await _admin_thread(user, chat, target_thread_id)
        if target is None:
            raise HTTPException(status_code=404, detail={"error_code": "THREAD_NOT_FOUND"})
        runtime = claude_agent_thread_factory.session_snapshot(target_thread_id)
        running = bool(runtime and runtime.get("lifecycle") == "running")

        if request.operation == "thread.read":
            saved = await _chat_invoke(
                user, chat.list_messages, chat_dto.ThreadIdInputDTO(thread_id=target_thread_id)
            )
            limit = request.message_limit or 20
            recent = saved.messages[-limit:]
            if running:
                status = "running"
            elif target.get("claude_session_id"):
                status = "idle"
            else:
                links = await _chat_invoke(
                    user,
                    chat.list_task_session_links,
                    chat_dto.ThreadIdInputDTO(thread_id=target_thread_id),
                )
                if links.source is not None and links.source.launch_status == "failed":
                    status = "failed"
                elif links.source is not None:
                    status = "starting"
                else:
                    status = "not_started"
            return ThreadToolCommandResultDTO(
                status=status,
                thread_id=target_thread_id,
                title=target.get("title"),
                running=running,
                messages=[
                    ThreadToolMessageDTO(
                        message_id=item.id,
                        role=item.role,
                        text=_extract_message_text(item.model_dump()),
                        created_at=item.created_at,
                    )
                    for item in recent
                ],
            )

        if request.operation != "thread.send":
            raise HTTPException(status_code=400, detail={"error_code": "THREAD_TOOL_OPERATION_INVALID"})
        text = str(request.prompt).strip()
        message_id = str(uuid5(NAMESPACE_URL,
            f"thread-tool:{source}:{self._source_message_id}:{request.tool_call_id}:{target_thread_id}:send"))
        existing = await _chat_invoke(user, chat.list_messages,
            chat_dto.ThreadIdInputDTO(thread_id=target_thread_id))
        if any(item.id == message_id for item in existing.messages):
            queued = await _chat_invoke(user, chat.list_inputs,
                chat_dto.ThreadIdInputDTO(thread_id=target_thread_id))
            known = next((item for item in queued.entries if item.message_id == message_id), None)
            return ThreadToolCommandResultDTO(
                thread_id=target_thread_id,
                status=known.status if known else "state_unknown",
                message_id=message_id,
                error_code=None if known else "THREAD_MESSAGE_ALREADY_SUBMITTED",
            )
        actor = user.get("_admin_actor")
        if not isinstance(actor, AdminRequestActor):
            raise HTTPException(status_code=503, detail={"error_code": "ADMIN_CONFIGURATION_INVALID"})
        if claude_agent_thread_factory.accepting_input(target_thread_id):
            entry = await claude_agent_thread_factory.enqueue_input(
                thread_id=target_thread_id, user_id=str(user["user_id"]),
                message_id=message_id, parts=[{"type": "text", "text": text}],
                title_candidate=text, tool_choice="auto", chat=chat,
                access_token=actor.access_token,
            )
            return ThreadToolCommandResultDTO(
                thread_id=target_thread_id, status=entry.status, message_id=message_id
            )
        if running:
            raise HTTPException(status_code=409, detail={"error_code": "THREAD_OWNER_UNAVAILABLE"})
        if not target.get("claude_session_id"):
            raise HTTPException(status_code=409, detail={"error_code": "THREAD_NOT_READY"})
        response = await claude_agent_stream(
            ClaudeAgentRequestBody(thread_id=target_thread_id, resume=True,
                message={"id": message_id, "role": "user", "parts": [{"type": "text", "text": text}]}),
            current_user=user, chat=chat, owner=self._owner,
        )
        drain = asyncio.create_task(
            _drain_task_session_stream(response, thread_id=target_thread_id),
            name=f"thread-tool-send-{target_thread_id}",
        )
        _task_session_stream_drains.add(drain)
        drain.add_done_callback(_task_session_stream_drains.discard)
        return ThreadToolCommandResultDTO(
            thread_id=target_thread_id, status="dispatching", message_id=message_id
        )

    @staticmethod
    def _wait_cursor(
        *,
        thread_id: str,
        status: str,
        final_message_id: str | None,
        pending_tool_call_ids: list[str],
        turn_count: int | None,
    ) -> str:
        material = json.dumps(
            {
                "thread_id": thread_id,
                "status": status,
                "final_message_id": final_message_id,
                "pending_tool_call_ids": pending_tool_call_ids,
                "turn_count": turn_count,
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        return sha256(material.encode("utf-8")).hexdigest()

    async def _wait_update(
        self,
        target: ThreadToolWaitTargetDTO,
        thread: dict,
    ) -> ThreadToolWaitUpdateDTO:
        thread_id = target.thread_id
        runtime = claude_agent_thread_factory.session_snapshot(thread_id)
        running = bool(runtime and runtime.get("lifecycle") == "running")
        confirmation = claude_agent_thread_factory.tool_confirmation_snapshot(thread_id)
        pending_ids = (
            list(confirmation.get("pending_tool_call_ids") or [])
            if confirmation.get("tool_confirmation_observation") == "known"
            else []
        )
        final_message_id: str | None = None
        final_text: str | None = None

        if running and pending_ids:
            status = "needs_attention"
        elif running:
            status = "running"
        else:
            page = await _chat_invoke(
                self._current_user,
                self._chat.message_page,
                chat_dto.MessagePageInputDTO(
                    thread_id=thread_id,
                    limit=1,
                    before=None,
                ),
            )
            latest = page.messages[-1] if page.messages else None
            metadata = (
                latest.metadata
                if latest is not None
                and not latest.metadata_decode_error
                and isinstance(latest.metadata, dict)
                else {}
            )
            turn_status = metadata.get("turnStatus")
            if (
                latest is not None
                and latest.role == "assistant"
                and turn_status == "completed"
                and metadata.get("is_partial") is not True
                and latest.history_projection_version == 1
                and isinstance(latest.history_final_text, str)
                and latest.history_final_text.strip()
            ):
                status = "completed"
                final_message_id = latest.id
                final_text = latest.history_final_text
            elif latest is not None and turn_status in {
                "error",
                "failed",
                "cancelled",
                "stopped",
            }:
                status = "failed"
                final_message_id = latest.id
            elif runtime and runtime.get("lifecycle") == "idle" and thread.get(
                "claude_session_id"
            ):
                status = "idle"
            else:
                links = await _chat_invoke(
                    self._current_user,
                    self._chat.list_task_session_links,
                    chat_dto.ThreadIdInputDTO(thread_id=thread_id),
                )
                if links.source is not None and links.source.launch_status == "failed":
                    status = "failed"
                elif links.source is not None:
                    status = "starting"
                elif thread.get("claude_session_id"):
                    status = "idle"
                else:
                    status = "not_started"

        cursor = self._wait_cursor(
            thread_id=thread_id,
            status=status,
            final_message_id=final_message_id,
            pending_tool_call_ids=pending_ids,
            turn_count=(
                int(runtime.get("turn_count", 0)) if runtime is not None else None
            ),
        )
        return ThreadToolWaitUpdateDTO(
            thread_id=thread_id,
            title=thread.get("title"),
            status=status,
            cursor=cursor,
            final_message_id=final_message_id,
            final_text=(
                final_text
                if final_text is not None and cursor != target.after_cursor
                else None
            ),
            pending_tool_call_ids=pending_ids or None,
        )

    async def _wait_threads(
        self,
        request: ThreadToolCommandRequestDTO,
    ) -> ThreadToolCommandResultDTO:
        """Keep this parent tool call open until a target changes meaningfully."""

        targets = list(request.targets or [])
        valid: list[tuple[ThreadToolWaitTargetDTO, dict]] = []
        errors: list[ThreadToolWaitErrorDTO] = []
        for target in targets:
            if target.thread_id == self._source_thread_id:
                errors.append(
                    ThreadToolWaitErrorDTO(
                        thread_id=target.thread_id,
                        error_code="THREAD_WAIT_TARGET_INVALID",
                    )
                )
                continue
            try:
                thread = await _admin_thread(
                    self._current_user,
                    self._chat,
                    target.thread_id,
                )
            except Exception:
                errors.append(
                    ThreadToolWaitErrorDTO(
                        thread_id=target.thread_id,
                        error_code="THREAD_WAIT_TARGET_UNAVAILABLE",
                    )
                )
                continue
            if thread is None:
                errors.append(
                    ThreadToolWaitErrorDTO(
                        thread_id=target.thread_id,
                        error_code="THREAD_NOT_FOUND",
                    )
                )
                continue
            valid.append((target, thread))

        if not valid:
            return ThreadToolCommandResultDTO(
                status="ok",
                wait_reason="error",
                updates=[],
                errors=errors,
            )

        timeout_ms = request.timeout_ms if request.timeout_ms is not None else 120_000
        deadline = self._loop.time() + (timeout_ms / 1000.0)
        source_generation = claude_agent_thread_factory.input_generation(
            self._source_thread_id
        )

        while True:
            try:
                updates = list(
                    await asyncio.gather(
                        *(self._wait_update(target, thread) for target, thread in valid)
                    )
                )
            except Exception:
                return ThreadToolCommandResultDTO(
                    status="ok",
                    wait_reason="error",
                    updates=[],
                    errors=[
                        *errors,
                        *[
                            ThreadToolWaitErrorDTO(
                                thread_id=target.thread_id,
                                error_code="THREAD_WAIT_TARGET_UNAVAILABLE",
                            )
                            for target, _thread in valid
                        ],
                    ],
                )

            by_id = {target.thread_id: target for target, _thread in valid}
            changed_terminal = next(
                (
                    update
                    for update in updates
                    if update.status in {"completed", "needs_attention", "failed"}
                    and update.cursor != by_id[update.thread_id].after_cursor
                ),
                None,
            )
            if changed_terminal is not None:
                return ThreadToolCommandResultDTO(
                    status="ok",
                    wait_reason=(
                        "error"
                        if changed_terminal.status == "failed"
                        else changed_terminal.status
                    ),
                    updates=updates,
                    errors=(
                        [
                            *errors,
                            ThreadToolWaitErrorDTO(
                                thread_id=changed_terminal.thread_id,
                                error_code="THREAD_TARGET_FAILED",
                            ),
                        ]
                        if changed_terminal.status == "failed"
                        else errors or None
                    ),
                )

            remaining = deadline - self._loop.time()
            if timeout_ms == 0 or remaining <= 0:
                return ThreadToolCommandResultDTO(
                    status="ok",
                    wait_reason="timeout",
                    updates=updates,
                    errors=errors or None,
                )

            input_received = await claude_agent_thread_factory.wait_for_input_after(
                self._source_thread_id,
                source_generation,
                timeout_seconds=min(0.5, remaining),
            )
            if input_received:
                return ThreadToolCommandResultDTO(
                    status="ok",
                    wait_reason="input_received",
                    updates=updates,
                    errors=errors or None,
                )


@router.post("/api/claude-agent/threads/{thread_id}/inputs/{message_id}/side-task")
async def claude_agent_thread_input_side_task(
    thread_id: str, message_id: str, body: QueueSelectBody,
    current_user: dict = Depends(get_current_user),
    chat: AdminChatData = Depends(get_admin_chat_data),
    owner: AdminRequestAuth = Depends(get_admin_request_auth),
):
    """Atomically move one queued message into a new independent task Thread."""
    if await _admin_thread(current_user, chat, thread_id) is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    listed = await _chat_invoke(current_user, chat.list_inputs,
        chat_dto.ThreadIdInputDTO(thread_id=thread_id))
    entry = next((item for item in listed.entries if item.message_id == message_id), None)
    if entry is None:
        raise HTTPException(status_code=404, detail={"error_code": "CHAT_INPUT_NOT_FOUND"})
    if not ((entry.status == "queued" and entry.revision == body.expected_revision)
            or (entry.status == "cancelled" and entry.revision == body.expected_revision + 1)):
        raise HTTPException(status_code=409, detail={"error_code": "CHAT_INPUT_STATE_CONFLICT"})
    created = await _chat_invoke(current_user, chat.create_task_session,
        chat_dto.TaskSessionCreateInputDTO(
            source_thread_id=thread_id, request_key=f"side:{message_id}",
            title=entry.text, initial_message=entry.text,
            source_message_id=message_id, expected_revision=body.expected_revision,
        ))
    if created.task is None:
        raise HTTPException(status_code=503, detail={"error_code": "TASK_SESSION_CREATE_UNAVAILABLE"})
    return await _task_session_launch_initial(task=created.task, current_user=current_user,
                                               chat=chat, owner=owner)


@router.get("/api/claude-agent/threads/{source_thread_id}/tasks/{task_id}")
async def claude_agent_task_session_get(
    source_thread_id: str, task_id: str,
    current_user: dict = Depends(get_current_user),
    chat: AdminChatData = Depends(get_admin_chat_data),
):
    task = await _task_session_detail(current_user, chat, source_thread_id, task_id)
    status, running, result_message_id, result_text = await _task_session_status(current_user, chat, task)
    return {"task_id": task.task_id, "thread_id": task.thread_id, "title": task.title,
            "launch_status": task.launch_status, "error_code": task.launch_error_code,
            "status": status, "running": running,
            "result_message_id": result_message_id, "result_text": result_text}


@router.get("/api/claude-agent/threads/{thread_id}/task-links")
async def claude_agent_task_session_links(
    thread_id: str,
    current_user: dict = Depends(get_current_user),
    chat: AdminChatData = Depends(get_admin_chat_data),
):
    """Return owner-filtered business Thread relations used by Chat navigation."""
    if await _admin_thread(current_user, chat, thread_id) is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    result = await _chat_invoke(
        current_user,
        chat.list_task_session_links,
        chat_dto.ThreadIdInputDTO(thread_id=thread_id),
    )
    return result.model_dump()


@router.get("/api/claude-agent/threads/{thread_id}/status")
async def claude_agent_thread_status(
    thread_id: str,
    current_user: dict = Depends(get_current_user),
    chat: AdminChatData = Depends(get_admin_chat_data),
):
    """Return the live inference lifecycle state of *thread_id*.

    Response body::

        {
          "running": true,           // true when AgentRunState.lifecycle == "running"
          "lifecycle": "running",    // "idle" | "running" | "destroyed" | "not_found"
          "turn_count": 3,           // completed turn count (0 when not found)
          "pending_tool_call_ids": ["call_..."],
          "tool_confirmation_observation": "known" // "known" | "unknown"
        }

    Ownership is validated: returns 404 when the thread does not belong to the
    caller.  When the thread exists but has no in-memory session (idle / never
    started / TTL evicted) ``running`` is ``false`` and ``lifecycle`` is
    ``"not_found"``.
    """
    user_id = current_user["user_id"]
    thread = await _admin_thread(current_user, chat, thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")

    snapshot = claude_agent_thread_factory.session_snapshot(thread_id)
    confirmation_snapshot = (
        claude_agent_thread_factory.tool_confirmation_snapshot(thread_id)
    )
    if snapshot is None:
        return {
            "running": False,
            "lifecycle": "not_found",
            "turn_count": 0,
            **confirmation_snapshot,
        }

    lifecycle: str = snapshot.get("lifecycle", "idle")
    return {
        "running": lifecycle == "running",
        "lifecycle": lifecycle,
        "turn_count": snapshot.get("turn_count", 0),
        **confirmation_snapshot,
    }


@router.get("/api/claude-agent/threads/{thread_id}/plan")
async def claude_agent_thread_plan(
    thread_id: str,
    current_user: dict = Depends(get_current_user),
    chat: AdminChatData = Depends(get_admin_chat_data),
):
    """Return the current Plan Mode plan for *thread_id* (claude-plan §5.5).

    Response body::

        {
          "thread_id": "thread-abc123",
          "plan_mode": "none" | "planning" | "exited",
          "exists": true,
          "slug": "amber-churn-otter",
          "file_name": "amber-churn-otter.md",
          "content": "# 计划\\n...",
          "content_bytes": 1832,
          "truncated": false,
          "updated_at": "2026-07-20T01:23:45.678Z"
        }

    Ownership is validated like ``/status``: 404 when the thread does not
    belong to the caller.  ``plan_mode`` comes from in-memory run state while
    the thread is running, else ``"none"``.  Plan data is rebuilt from the
    workspace plans directory (the only persistent layer); ``exists:false``
    returns null ``slug``/``file_name``/``content``/``content_bytes``/
    ``updated_at``.  Workspace Mode disabled → fixed ``exists:false`` +
    ``plan_mode:"none"`` (never probes the global ``~/.claude/plans``).
    """
    user_id = current_user["user_id"]
    thread = await _admin_thread(current_user, chat, thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")

    snapshot = claude_agent_thread_factory.session_snapshot(thread_id)
    plan_mode = "none"
    if snapshot and snapshot.get("lifecycle") == "running":
        plan_mode = str(snapshot.get("plan_mode") or "none")
    return build_thread_plan_payload(thread_id, plan_mode=plan_mode)


@router.get("/api/claude-agent/threads/{thread_id}/todos")
async def claude_agent_thread_todos(
    thread_id: str,
    current_user: dict = Depends(get_current_user),
    chat: AdminChatData = Depends(get_admin_chat_data),
):
    """Return the current todo list for *thread_id* (claude-todo §5.5).

    Response body::

        {
          "thread_id": "thread-abc123",
          "source": "todo_write" | "task_v2" | null,
          "exists": true,
          "todos": [
            {"id": "1", "content": "...", "status": "pending",
             "active_form": null, "owner": null, "blocked_by": []}
          ],
          "truncated": false,
          "updated_at": "2026-07-20T06:30:00.000Z"
        }

    Ownership is validated like ``/plan``: 404 when the thread does not
    belong to the caller.  When the v2 tasks directory holds task JSON the
    filesystem is the source of truth (and the in-memory state is corrected);
    otherwise the in-memory v1 TodoWrite capture from the session snapshot is
    returned.  ``exists:false`` returns ``source:null``, ``todos:[]`` and
    ``updated_at:null``.  Workspace Mode disabled → fixed ``exists:false``
    (never probes the global ``~/.claude/tasks``).
    """
    user_id = current_user["user_id"]
    thread = await _admin_thread(current_user, chat, thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")

    snapshot = claude_agent_thread_factory.session_snapshot(thread_id)
    todo_state = snapshot.get("todo_state") if snapshot else None
    return build_thread_todos_payload(thread_id, todo_state=todo_state)


@router.post("/api/claude-agent/threads/{thread_id}/stop")
async def claude_agent_stop_thread(
    thread_id: str,
    current_user: dict = Depends(get_current_user),
    chat: AdminChatData = Depends(get_admin_chat_data),
):
    """Cancel the running Agent turn for *thread_id*.

    The endpoint is idempotent: if the thread belongs to the caller but has no
    running in-memory turn, it returns ``stop_requested=false``.
    """

    user_id = current_user["user_id"]
    thread = await _admin_thread(current_user, chat, thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")

    try:
        result = await claude_agent_thread_factory.stop_thread(thread_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {"ok": True, "thread_id": thread_id, **result}


@router.delete("/api/claude-agent/threads/{thread_id}")
async def claude_agent_delete_thread(
    thread_id: str,
    current_user: dict = Depends(get_current_user),
    chat: AdminChatData = Depends(get_admin_chat_data),
):
    """Delete a chat thread and all its messages."""
    deleted = (await _chat_invoke(current_user, chat.delete_thread, chat_dto.ThreadIdInputDTO(thread_id=thread_id))).changed
    if not deleted:
        raise HTTPException(status_code=404, detail="Thread not found")
    claude_agent_thread_factory.close_thread(thread_id)
    return {"ok": True}


@router.post("/api/claude-agent/message-latency")
async def claude_agent_message_latency(
    body: dict,
    current_user: dict = Depends(get_current_user),
):
    """Record browser-side latency metrics for a Claude Agent message.

    Stored as extra metadata on the session record when available;
    silently ignored if the referenced session is not found.
    """
    import logging as _logging

    _logging.getLogger("claude_agent.latency").info(
        "message-latency user_id=%s data=%s",
        current_user.get("user_id"),
        body,
    )
    return {"ok": True}


@router.get("/api/claude-agent/session")
async def claude_agent_session_status(
    session_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    chat: AdminChatData = Depends(get_admin_chat_data),
):
    """Return the keepalive snapshot for the caller's active session.

    *session_id* must be a valid ``thread_id``.
    """
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id (thread_id) is required")
    if await _admin_thread(current_user, chat, session_id) is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    snapshot = claude_agent_thread_factory.session_snapshot(session_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="No active session found")
    return snapshot


@router.delete("/api/claude-agent/session")
async def claude_agent_session_close(
    session_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
    chat: AdminChatData = Depends(get_admin_chat_data),
):
    """Explicitly close (destroy) the caller's Claude Agent session.

    Triggers Phase 4 lifecycle hooks; the next request will start a fresh session.
    *session_id* must be a valid ``thread_id``.
    """
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id (thread_id) is required")
    if await _admin_thread(current_user, chat, session_id) is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    claude_agent_thread_factory.close_thread(session_id)
    return {"ok": True, "session_id": session_id}


@router.post("/api/claude-agent/tool-confirm")
async def claude_agent_tool_confirm(
    body: ToolConfirmRequestBody,
    current_user: dict = Depends(get_current_user),
    chat: AdminChatData = Depends(get_admin_chat_data),
):
    """Resolve a pending tool confirmation from the frontend.

    Must be called while the SSE stream is still open and the agent is
    awaiting approval in its ``on_tool_confirmation_request`` callback.
    ``body.thread_id`` must be the ``thread_id`` of the active conversation.
    """
    session_id = body.thread_id
    if not session_id:
        raise HTTPException(status_code=400, detail="thread_id is required")
    user_id = current_user["user_id"]
    if await _admin_thread(current_user, chat, session_id) is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    try:
        resolved = await claude_agent_thread_factory.confirm_tool(
            session_id=session_id,
            tool_call_id=body.tool_call_id,
            approved=body.approved,
            reason=body.reason,
            answers=body.answers,
            actor_id=str(user_id),
            authorization_context=current_user,
        )
    except ToolConfirmationError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={
                "code": exc.code,
                "tool_call_id": body.tool_call_id,
            },
        ) from exc
    if not resolved:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "TOOL_CONFIRMATION_NOT_PENDING",
                "tool_call_id": body.tool_call_id,
            },
        )
    if not isinstance(resolved, ToolConfirmationResolution):
        # Fail closed if an out-of-date factory bypasses the exact policy API.
        raise HTTPException(
            status_code=409,
            detail={
                "code": "TOOL_CONFIRMATION_NOT_PENDING",
                "tool_call_id": body.tool_call_id,
            },
        )
    return {"ok": True, "approved": resolved.result.approved}
