# [Input] Authenticated saved note, expected prose digest and Admin-owned share publication.
# [Output] Immutable database snapshot with owner metadata; legacy file-token reads are closed.
# [Pos] Note adapter to the unified external-share domain; no file/publication fallback.
from __future__ import annotations
import hashlib
import os
from urllib.parse import urlsplit
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import Field
from services.admin_data import session_models as dto
from services.admin_data.request_auth import AdminRequestAuth
from services.admin_data.session_data import AdminSessionData
from services.admin_data.external_share_data import NoteShareSnapshot
from .deps import get_current_user, get_admin_request_auth, invoke_admin_operation
from .sessions import get_admin_session_data, _session_input
from .external_shares import PublicationRequest, publish_snapshot, PUBLIC_HEADERS
router = APIRouter()

class ShareNoteInput(PublicationRequest):
    content_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')

def public_note_url(path: str) -> str | None:
    configured = (os.environ.get('INK_PUBLIC_SITE_URL') or os.environ.get('INK_PUBLIC_BASE_URL') or '').strip()
    try:
        parsed = urlsplit(configured)
        port = parsed.port
    except ValueError: return None
    if parsed.scheme in ('https', 'http') and parsed.hostname and (port is None or port > 0) and parsed.path in ('', '/') and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment and not any(character.isspace() or ord(character) < 32 or character == '\\' for character in configured):
        return configured.rstrip('/') + path
    return None

@router.post('/api/sessions/{session_id}/share', status_code=201)
async def create_note_share(session_id: str, payload: ShareNoteInput, response: Response, current_user: dict = Depends(get_current_user),
                            sessions: AdminSessionData = Depends(get_admin_session_data), owner: AdminRequestAuth = Depends(get_admin_request_auth)):
    result = await invoke_admin_operation(current_user, sessions.get, _session_input(dto.SessionIdInputDTO, session_id=session_id))
    if result.session is None: raise HTTPException(404, 'Session not found')
    session = result.session
    paragraphs = [cell.content for cell in session.editor_state.cells if cell.type == 'text']
    text = '\n\n'.join(paragraphs)
    if not text.strip(): raise HTTPException(400, 'Note is empty')
    if hashlib.sha256(text.encode('utf-8')).hexdigest() != payload.content_sha256: raise HTTPException(409, 'Note changed; reopen sharing')
    title = next((line.strip() for line in text.splitlines() if line.strip()), '')[:100]
    snapshot = NoteShareSnapshot(kind='note', title=title, created_at=session.created_at, paragraphs=paragraphs)
    response.headers.update(PUBLIC_HEADERS)
    return await publish_snapshot(current_user, owner, snapshot, session_id, payload.request_key)

@router.get('/api/public/note-shares/{token}')
async def legacy_note_share(token: str):
    raise HTTPException(404, 'Share unavailable', headers=PUBLIC_HEADERS)
