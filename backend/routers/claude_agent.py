#!/usr/bin/env python3
# [Input] Consume database chat APIs, Claude Agent request types/factory, and shared auth dependency.
# [Output] Register /api/claude-agent* endpoints.
# [Pos] claude-agent route node in backend/routers
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

import asyncio
import base64
import json
import logging
import os
import re
from enum import Enum
from pathlib import Path
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import AliasChoices, BaseModel, Field, model_validator

import database
from agent_factory import claude_agent_thread_factory
from claude_agent import ClaudeAgentRunRequest
from claude_agent.service import build_thread_plan_payload, build_thread_todos_payload
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
from services.deck.chat_context import DeckChatContextError, DeckChatContextService
from services.admin_gateway import (
    GatewayInferenceError,
    GatewayModel,
    GatewayModelCatalogClient,
    resolve_platform_model,
)

from .deps import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

_SANDBOX_NETWORK_MODES = {"disabled", "allowlist", "open"}
_PLATFORM_MODEL_ALIAS = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,119}$")
_SERVER_MESSAGE_ID_PREFIXES = ("dream_agent_", "dream_confirm_", "guide_")
class PublicDispatchStatus(str, Enum):
    PENDING = "pending"
    DISPATCHING = "dispatching"
    DISPATCHED = "dispatched"
    FAILED = "failed"


class PublicToolChoice(str, Enum):
    AUTO = "auto"
    MANUAL = "manual"
    NONE = "none"


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

        # Dream business rows use the shared Chat history as their visible
        # transcript.  Their body must not be redacted merely because the row
        # carries a server-owned kind, episode action, or legacy visibility
        # marker.  Malformed discriminators still fail closed because their
        # business provenance cannot be established safely.
        return cls.model_validate(values), malformed_discriminator


class PublicChatMessageDto(BaseModel):
    id: Any = None
    role: Any = None
    created_at: Any = None
    parts: list[Any] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @classmethod
    def from_storage(cls, message: dict[str, Any]) -> "PublicChatMessageDto":
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
            [] if suppress_parts else parts if isinstance(parts, list) else []
        )
        values["metadata"] = public_metadata
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


def _project_chat_message_for_client(message: dict[str, Any]) -> dict[str, Any]:
    """Redact server-owned control envelopes from canonical thread history.

    Control rows remain addressable by message id so shared Chat/Dream
    hydration can settle a durable dispatch. Their instruction parts and
    authority-bearing metadata are never browser-readable.
    """

    return PublicChatMessageDto.from_storage(message).model_dump(
        exclude_unset=True,
        mode="json",
    )


async def _resolve_platform_model_alias(
    user_id: int,
    client_model_alias: str | None,
) -> str:
    return (await _resolve_platform_model_selection(user_id, client_model_alias)).model_alias


async def _resolve_platform_model_selection(
    user_id: int,
    client_model_alias: str | None,
) -> GatewayModel | str:
    try:
        return await asyncio.to_thread(
            resolve_platform_model,
            user_id,
            client_model_alias,
            catalog_client_factory=GatewayModelCatalogClient,
            system_config_reader=database.get_system_config,
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


@router.post("/api/claude-agent")
async def claude_agent_stream(
    body: ClaudeAgentRequestBody,
    current_user: dict = Depends(get_current_user),
):
    """SSE streaming endpoint for Claude Agent.

    Returns ``text/event-stream``; each frame is a JSON object:
    ``{"type": "text-delta"|"tool-event"|"message-final"|"finish"|"error", ...}``

    Requires a ``thread_id`` (created via ``POST /api/claude-agent/threads``).
    """
    user_id = current_user["user_id"]
    thread_id = body.get_thread_id()
    if not thread_id:
        raise HTTPException(status_code=400, detail="thread_id is required")

    thread = database.get_chat_thread(thread_id, user_id)
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

    message_text = body.get_message_text()
    if not message_text:
        raise HTTPException(status_code=400, detail="message text is required")

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
    effective_deck_id = requested_deck_id or persisted_deck_id
    effective_voice_id = requested_voice_id or persisted_voice_id
    if effective_voice_id and not effective_deck_id:
        raise HTTPException(status_code=422, detail="voiceId requires deckId")
    if effective_deck_id:
        deck_db = database.get_db()
        try:
            deck_context = await DeckChatContextService(deck_db).resolve(
                deck_id=str(effective_deck_id),
                actor_id=str(user_id),
                voice_id=str(effective_voice_id) if effective_voice_id else None,
            )
        except DeckChatContextError as exc:
            raise HTTPException(
                status_code=exc.status_code,
                detail={"error_code": exc.code, "message": str(exc)},
            ) from exc
        finally:
            deck_db.close()
        if not persisted_deck_id and not database.bind_chat_thread_deck(
            thread_id,
            user_id,
            str(effective_deck_id),
        ):
            raise HTTPException(
                status_code=409,
                detail={
                    "error_code": "CHAT_DECK_IMMUTABLE",
                    "message": "The conversation Deck changed concurrently.",
                },
            )
        if requested_voice_id and requested_voice_id != persisted_voice_id and not database.select_chat_thread_voice(
            thread_id,
            user_id,
            str(effective_deck_id),
            str(requested_voice_id),
            str(persisted_voice_id) if persisted_voice_id else None,
        ):
            raise HTTPException(
                status_code=409,
                detail={
                    "error_code": "CHAT_AGENT_CONFLICT",
                    "message": "The conversation Agent changed concurrently. Reload and try again.",
                },
            )

    platform_model = await _resolve_platform_model_selection(user_id, body.model)
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
            system_config = database.get_system_config(user_id)
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
    if message_id is not None:
        # Reserve the immutable public message identity before returning an SSE
        # response or starting the Agent runtime.  The service repeats the same
        # write as an exact CAS replay, closing the route/service race without
        # granting browser IDs any server-command authority.
        resolved_user_parts = (
            list(message_parts)
            if message_parts
            else [{"type": "text", "text": ""}]
        )
        try:
            await asyncio.to_thread(
                database.save_chat_message,
                thread_id,
                "user",
                resolved_user_parts,
                message_id,
                message_metadata,
            )
        except database.ChatMessageIdentityConflict as exc:
            raise HTTPException(
                status_code=exc.status_code,
                detail={
                    "error_code": exc.code,
                    "message": "The message identifier is already bound.",
                },
            ) from exc

    request = ClaudeAgentRunRequest(
        user_id=str(user_id),
        thread_id=thread_id,
        resume=body.resume,
        tool_choice=body.tool_choice,
        model=platform_model_alias,
        model_runtime_env=model_runtime_env,
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
):
    """Return chat thread history for the authenticated user.

    Returns the list of chat threads (newest first) so the frontend
    can display the user's past conversations.
    """
    user_id = current_user["user_id"]
    threads = database.list_chat_threads(user_id)
    return {"threads": threads or []}


@router.post("/api/claude-agent/threads", response_model=CreateThreadResponseBody)
async def claude_agent_create_thread(
    current_user: dict = Depends(get_current_user),
    body: Optional[CreateThreadRequestBody] = None,
):
    """Create a new chat thread and return its ``thread_id``.

    Call this endpoint when the user clicks "New Chat".  The returned
    ``thread_id`` must be included in every subsequent
    ``POST /api/claude-agent`` request for that conversation.
    """
    user_id = current_user["user_id"]
    deck_id = body.deck_id if body else None
    voice_id = body.voice_id if body else None
    title = body.title if body else None
    if deck_id:
        deck = database.get_deck_with_voices(user_id, deck_id)
        if deck is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "error_code": "DECK_ACCESS_DENIED",
                    "message": "Deck not found or permission denied.",
                },
            )
        if not bool(deck.get("enabled")):
            raise HTTPException(
                status_code=409,
                detail={
                    "error_code": "DECK_DISABLED",
                    "message": "The selected Deck is disabled.",
                },
            )
        if voice_id and not any(
            str(voice.get("id")) == voice_id and bool(voice.get("enabled"))
            for voice in deck.get("voices", [])
        ):
            raise HTTPException(
                status_code=404,
                detail={
                    "error_code": "AGENT_ACCESS_DENIED",
                    "message": "Agent not found, disabled, or outside the selected Deck.",
                },
            )
    elif voice_id:
        raise HTTPException(status_code=422, detail="voiceId requires deckId")
    thread_id = database.create_chat_thread(user_id, deck_id=deck_id, voice_id=voice_id, title=title)
    return {"thread_id": thread_id, "deck_id": deck_id, "voice_id": voice_id}


@router.get("/api/claude-agent/threads/{thread_id}/plugin-load-receipt")
async def claude_agent_thread_plugin_load_receipt(
    thread_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Return the workspace plugin pack + launch receipt for a thread.

    The receipt is produced by the server-side workspace packer when the
    thread's locked Deck has enabled Claude plugin installations.  It carries
    package spec, resolved version and artifact digest per plugin, plus the
    frozen flag.  A thread without plugins returns an empty plugin list.
    """
    user_id = current_user["user_id"]
    thread = database.get_chat_thread(thread_id, user_id)
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
    limit: Optional[int] = Query(default=None, ge=1),
    offset: int = Query(default=0, ge=0),
    current_user: dict = Depends(get_current_user),
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
        threads = database.list_chat_threads(
            user_id,
            limit=limit,
            offset=offset,
            deck_id=deck_id,
        )
        return {"threads": threads}

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
        candidates = database.list_chat_threads_for_search(user_id, deck_id=deck_id)
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
    current_user: dict = Depends(get_current_user),
):
    """Return all persisted messages for *thread_id* in chronological order.

    Returns 404 if the thread does not exist or belongs to another user.
    """
    user_id = current_user["user_id"]
    thread = database.get_chat_thread(thread_id, user_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    messages = [
        _project_chat_message_for_client(message)
        for message in database.list_chat_messages(thread_id)
    ]
    return {
        "thread": _project_chat_thread_for_client(thread),
        "messages": messages,
    }


@router.get("/api/claude-agent/threads/{thread_id}/subagents")
async def claude_agent_thread_subagents(
    thread_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Return thread-owned subagent tasks without exposing raw transcripts."""

    user_id = current_user["user_id"]
    thread = database.get_chat_thread(thread_id, user_id)
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
):
    """SSE reconnect endpoint — subscribe to an in-flight turn's EventBus.

    Replays buffered frames then streams live events until the turn completes.
    Returns 409 when the thread is not currently running.
    """
    user_id = current_user["user_id"]
    thread = database.get_chat_thread(thread_id, user_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")

    snapshot = claude_agent_thread_factory.session_snapshot(thread_id)
    if snapshot is None or snapshot.get("lifecycle") != "running":
        raise HTTPException(status_code=409, detail="Thread is not running")

    async def generate():
        async for frame in claude_agent_thread_factory.subscribe_stream(thread_id):
            yield frame

    return streaming_sse_response(generate())


@router.get("/api/claude-agent/threads/{thread_id}/status")
async def claude_agent_thread_status(
    thread_id: str,
    current_user: dict = Depends(get_current_user),
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
    thread = database.get_chat_thread(thread_id, user_id)
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
    thread = database.get_chat_thread(thread_id, user_id)
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
    thread = database.get_chat_thread(thread_id, user_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")

    snapshot = claude_agent_thread_factory.session_snapshot(thread_id)
    todo_state = snapshot.get("todo_state") if snapshot else None
    return build_thread_todos_payload(thread_id, todo_state=todo_state)


@router.post("/api/claude-agent/threads/{thread_id}/stop")
async def claude_agent_stop_thread(
    thread_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Cancel the running Agent turn for *thread_id*.

    The endpoint is idempotent: if the thread belongs to the caller but has no
    running in-memory turn, it returns ``stop_requested=false``.
    """

    user_id = current_user["user_id"]
    thread = database.get_chat_thread(thread_id, user_id)
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
):
    """Delete a chat thread and all its messages."""
    user_id = current_user["user_id"]
    deleted = database.delete_chat_thread(thread_id, user_id)
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
):
    """Return the keepalive snapshot for the caller's active session.

    *session_id* must be a valid ``thread_id``.
    """
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id (thread_id) is required")
    if database.get_chat_thread(session_id, current_user["user_id"]) is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    snapshot = claude_agent_thread_factory.session_snapshot(session_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="No active session found")
    return snapshot


@router.delete("/api/claude-agent/session")
async def claude_agent_session_close(
    session_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    """Explicitly close (destroy) the caller's Claude Agent session.

    Triggers Phase 4 lifecycle hooks; the next request will start a fresh session.
    *session_id* must be a valid ``thread_id``.
    """
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id (thread_id) is required")
    if database.get_chat_thread(session_id, current_user["user_id"]) is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    claude_agent_thread_factory.close_thread(session_id)
    return {"ok": True, "session_id": session_id}


@router.post("/api/claude-agent/tool-confirm")
async def claude_agent_tool_confirm(
    body: ToolConfirmRequestBody,
    current_user: dict = Depends(get_current_user),
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
    if database.get_chat_thread(session_id, user_id) is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    try:
        resolved = await claude_agent_thread_factory.confirm_tool(
            session_id=session_id,
            tool_call_id=body.tool_call_id,
            approved=body.approved,
            reason=body.reason,
            answers=body.answers,
            actor_id=str(user_id),
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
