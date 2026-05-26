#!/usr/bin/env python3
# [Input] Consume database chat APIs, Claude Agent request types/factory, and shared auth dependency.
# [Output] Register /api/claude-agent* endpoints.
# [Pos] claude-agent route node in backend/routers
# [Sync] 2026-05-25: extracted Claude Agent routes from backend/server.py.
# [Sync] 2026-05-25: add attachment processing — download from file storage and sync to workspace.

import base64
import logging
from pathlib import Path
from typing import Any, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

import database
from agent_factory import claude_agent_thread_factory
from claude_agent import ClaudeAgentRunRequest
from libs.claude_agent_kit.messages.build_user_message_content import AttachmentPayload
from libs.claude_agent_kit.server.workspace import get_or_create_workspace
from libs.claude_agent_kit.server.workspace_file_sync import (
    WorkspaceFileSyncError,
    WorkspaceFileSyncErrorCode,
    inject_attachment_message_parts,
    normalize_workspace_file_sync_error,
    sync_attachments_to_workspace_files,
)
from libs.file_storage import server_file_storage

from .deps import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()


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


class ClaudeAgentRequestBody(BaseModel):
    thread_id: Optional[str] = None
    id: Optional[str] = None
    message: Any
    resume: bool = False
    tool_choice: str = "auto"
    chatModel: Optional[dict] = None
    model: Optional[str] = None
    max_turns: int = 100
    cwd: Optional[str] = None
    attachments: List[ChatAttachment] = []

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

    message_text = body.get_message_text()
    if not message_text:
        raise HTTPException(status_code=400, detail="message text is required")

    _msg_dict = body.message if isinstance(body.message, dict) else None
    message_parts = list(_msg_dict.get("parts") or []) if _msg_dict else None

    # Process attachments: download from file storage and sync to workspace.
    attachment_payloads: list[AttachmentPayload] = []
    if body.attachments:
        try:
            workspace_path = get_or_create_workspace(thread_id)
        except Exception as exc:
            raise HTTPException(status_code=500, detail="Failed to initialize workspace") from exc

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

    request = ClaudeAgentRunRequest(
        user_id=str(user_id),
        thread_id=thread_id,
        message=message_text,
        resume=body.resume,
        tool_choice=body.tool_choice,
        model=body.model,
        max_turns=body.max_turns,
        cwd=body.cwd,
        message_id=_msg_dict.get("id") if _msg_dict else None,
        message_parts=message_parts,
        attachments=attachment_payloads or None,
    )

    async def generate():
        async for frame in claude_agent_thread_factory.run_streaming(request):
            yield frame

    return StreamingResponse(generate(), media_type="text/event-stream")


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
):
    """Create a new chat thread and return its ``thread_id``.

    Call this endpoint when the user clicks "New Chat".  The returned
    ``thread_id`` must be included in every subsequent
    ``POST /api/claude-agent`` request for that conversation.
    """
    user_id = current_user["user_id"]
    thread_id = database.create_chat_thread(user_id)
    return {"thread_id": thread_id}


@router.get("/api/claude-agent/threads")
async def claude_agent_list_threads(
    current_user: dict = Depends(get_current_user),
):
    """Return all chat threads for the authenticated user, newest first."""
    user_id = current_user["user_id"]
    threads = database.list_chat_threads(user_id)
    return {"threads": threads}


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
    messages = database.list_chat_messages(thread_id)
    return {"thread": thread, "messages": messages}


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
    del current_user

    if not session_id:
        raise HTTPException(status_code=400, detail="session_id (thread_id) is required")
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
    del current_user

    if not session_id:
        raise HTTPException(status_code=400, detail="session_id (thread_id) is required")
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
    del current_user

    session_id = body.thread_id
    if not session_id:
        raise HTTPException(status_code=400, detail="thread_id is required")
    resolved = claude_agent_thread_factory.confirm_tool(
        session_id=session_id,
        tool_call_id=body.tool_call_id,
        approved=body.approved,
        reason=body.reason,
        answers=body.answers,
    )
    if not resolved:
        raise HTTPException(
            status_code=404,
            detail=f"No pending confirmation for tool_call_id={body.tool_call_id}",
        )
    return {"ok": True, "approved": body.approved}
