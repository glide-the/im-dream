# [Input] Current Admin OAuth identity, existing public Chat projection and exact share capabilities.
# [Output] Immutable AI/note publication, owner-only management and credential-free public reads.
# [Pos] Unified Dream share ingress; no local-file publication, SQL or runtime DDL.
from __future__ import annotations
from typing import Literal
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError
from services.admin_data.config import AdminDataConfig
from services.admin_data.request_auth import AdminRequestAuth
from services.admin_data import chat_models as chat_dto
from services.admin_data.external_share_data import (
    CREATE_SHARE, LIST_SHARES, GET_SHARE, REVOKE_SHARE, ShareCreateInput,
    ShareIdInput, ShareCursor, ShareListInput, ShareSnapshot, ChatShareSnapshot, SharedMessage,
)
from .deps import get_current_user, get_admin_request_auth, invoke_admin_operation

router = APIRouter()
PUBLIC_HEADERS = {'Cache-Control': 'no-store', 'X-Robots-Tag': 'noindex, nofollow', 'Referrer-Policy': 'no-referrer'}

class PublicationRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    request_key: str = Field(pattern=r'^[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$')

def project_shared_messages(stored_messages) -> list[SharedMessage]:
    """Project visible user prose and completed final answers, without process parts."""
    from .claude_agent import _project_chat_message_for_client
    messages = []
    for item in stored_messages:
        stored = item.model_dump() if hasattr(item, 'model_dump') else item
        public = _project_chat_message_for_client(stored)
        role, parts, metadata = public.get('role'), public.get('parts', []), public.get('metadata', {})
        if role not in {'user', 'assistant'} or metadata.get('visibility') == 'system-hidden':
            continue
        if metadata.get('kind') in {'story-workspace-dream-auto-repair', 'story-workspace-dream-confirmation', 'task-session-result'}:
            continue
        texts = [part['text'] for part in parts if isinstance(part, dict) and part.get('type') == 'text' and isinstance(part.get('text'), str)]
        if role == 'assistant':
            if metadata.get('turnProjectionInvalid') is True or metadata.get('turnStatus') in {'cancelled', 'error'} or metadata.get('is_partial') is True:
                continue
            final = stored.get('history_final_text')
            index = metadata.get('finalPartIndex')
            if isinstance(final, str) and final in texts:
                texts = [final]
            elif metadata.get('turnStatus') == 'completed' and isinstance(index, int) and not isinstance(index, bool) and 0 <= index < len(parts):
                part = parts[index]
                texts = [part['text']] if isinstance(part, dict) and part.get('type') == 'text' and isinstance(part.get('text'), str) else []
            elif not any(key in metadata for key in ('turnId', 'turnStatus', 'finalPartIndex', 'turnProjectionInvalid')) and len(parts) == 1:
                pass
            else:
                continue
        content = '\n\n'.join(texts)
        if content.strip():
            messages.append(SharedMessage(role=role, content=content))
    return messages

async def publish_snapshot(current_user: dict, owner: AdminRequestAuth, snapshot, source_id: str, request_key: str):
    result = await invoke_admin_operation(current_user, lambda data, key, **auth: owner.client.execute(CREATE_SHARE, data, key, **auth),
        ShareCreateInput(kind=snapshot.kind, source_id=source_id, snapshot=snapshot), request_id=request_key)
    if result.share.kind != snapshot.kind or result.share.source_id != source_id:
        raise HTTPException(503, 'Invalid share publication response')
    from .note_shares import public_note_url
    return {**result.model_dump(), 'path': result.share.path, 'url': public_note_url(result.share.path)}

@router.post('/api/claude-agent/threads/{thread_id}/share', status_code=201)
async def create_chat_share(thread_id: str, payload: PublicationRequest, response: Response,
                            current_user: dict = Depends(get_current_user), owner: AdminRequestAuth = Depends(get_admin_request_auth)):
    from .claude_agent import get_admin_chat_data, _admin_thread
    chat = get_admin_chat_data(owner)
    thread = await _admin_thread(current_user, chat, thread_id)
    if thread is None: raise HTTPException(404, 'Thread not found')
    stored = await invoke_admin_operation(current_user, chat.list_messages, chat_dto.ThreadIdInputDTO(thread_id=thread_id))
    messages = project_shared_messages(stored.messages)
    if not messages: raise HTTPException(400, 'Conversation is empty')
    snapshot = ChatShareSnapshot(kind='chat', title=thread.get('title') or messages[0].content.split('\n')[0][:100], created_at=thread.get('created_at'), messages=messages)
    response.headers.update(PUBLIC_HEADERS)
    return await publish_snapshot(current_user, owner, snapshot, thread_id, payload.request_key)

@router.get('/api/shares')
async def list_shares(response: Response, kind: Literal['chat', 'note'], status: Literal['active', 'revoked'] = 'active',
                      limit: int = Query(20, ge=1, le=100), before_created_at: str | None = None, before_id: str | None = None,
                      current_user: dict = Depends(get_current_user), owner: AdminRequestAuth = Depends(get_admin_request_auth)):
    response.headers.update(PUBLIC_HEADERS)
    if (before_created_at is None) != (before_id is None): raise HTTPException(400, 'Invalid share cursor')
    try: before = ShareCursor(created_at=before_created_at, id=before_id) if before_id is not None else None
    except ValidationError: raise HTTPException(400, 'Invalid share cursor') from None
    result = await invoke_admin_operation(current_user, lambda data, key, **auth: owner.client.execute(LIST_SHARES, data, key, **auth), ShareListInput(kind=kind, status=status, limit=limit, before=before))
    from .note_shares import public_note_url
    return {**result.model_dump(), 'public_origin': public_note_url('')}

def _share_id_input(share_id: str) -> ShareIdInput:
    try: return ShareIdInput(id=share_id)
    except ValidationError: raise HTTPException(404, 'Share not found') from None

@router.get('/api/shares/{share_id}')
async def get_share(share_id: str, response: Response, current_user: dict = Depends(get_current_user), owner: AdminRequestAuth = Depends(get_admin_request_auth)):
    response.headers.update(PUBLIC_HEADERS)
    result = await invoke_admin_operation(current_user, lambda data, key, **auth: owner.client.execute(GET_SHARE, data, key, **auth), _share_id_input(share_id))
    if result.share is None: raise HTTPException(404, 'Share not found')
    if result.share.id != share_id: raise HTTPException(503, 'Invalid share response')
    return result.model_dump()

@router.post('/api/shares/{share_id}/revoke')
async def revoke_share(share_id: str, payload: PublicationRequest, response: Response, current_user: dict = Depends(get_current_user), owner: AdminRequestAuth = Depends(get_admin_request_auth)):
    response.headers.update(PUBLIC_HEADERS)
    result = await invoke_admin_operation(current_user, lambda data, key, **auth: owner.client.execute(REVOKE_SHARE, data, key, **auth), _share_id_input(share_id), request_id=payload.request_key)
    if result.share.id != share_id or result.share.status != 'revoked': raise HTTPException(503, 'Invalid share response')
    return result.model_dump()

@router.get('/api/public/shares/{token}')
async def read_public_share(token: str, response: Response):
    import re
    if not re.fullmatch(r'[A-Za-z0-9_-]{43}', token): raise HTTPException(404, 'Share unavailable', headers=PUBLIC_HEADERS)
    try:
        config = AdminDataConfig.from_env()
        async with httpx.AsyncClient(timeout=config.timeout_seconds, follow_redirects=False) as client:
            async with client.stream('GET', config.transport_origin + '/api/public/shares/' + token, headers={'accept': 'application/json'}) as upstream:
                if upstream.status_code in (404, 410): raise HTTPException(404, 'Share unavailable', headers=PUBLIC_HEADERS)
                if upstream.status_code != 200: raise HTTPException(503, 'Share temporarily unavailable', headers=PUBLIC_HEADERS)
                content = bytearray()
                async for part in upstream.aiter_bytes():
                    content.extend(part)
                    if len(content) > config.max_response_bytes: raise HTTPException(503, 'Share temporarily unavailable', headers=PUBLIC_HEADERS)
        snapshot = TypeAdapter(ShareSnapshot).validate_json(bytes(content))
    except HTTPException: raise
    except Exception: raise HTTPException(503, 'Share temporarily unavailable', headers=PUBLIC_HEADERS) from None
    response.headers.update(PUBLIC_HEADERS)
    return snapshot.model_dump()
