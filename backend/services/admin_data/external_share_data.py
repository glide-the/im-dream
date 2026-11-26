# [Input] Generated exact Admin operation descriptors and server-projected public prose.
# [Output] Closed share snapshots, metadata and current-user publication/management operations.
# [Pos] Dream share consumer; Admin owns persistence, source ownership and revocation.
from __future__ import annotations
import json
from pathlib import Path
from typing import Annotated, Literal
from pydantic import Field, field_validator
from .chat_models import ChatStrictDTO, EntityId, validate_timestamp_text
from .client import DomainOperation
from .models import OperationCapabilityDTO
ShareId = Annotated[str, Field(pattern=r'^[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$')]

class NoteShareSnapshot(ChatStrictDTO):
    kind: Literal['note']
    title: str
    created_at: str | None
    paragraphs: list[str]
    _timestamp = field_validator('created_at')(validate_timestamp_text)

class SharedMessage(ChatStrictDTO):
    role: Literal['user', 'assistant']
    content: str

class ChatShareSnapshot(ChatStrictDTO):
    kind: Literal['chat']
    title: str
    created_at: str | None
    messages: list[SharedMessage]
    _timestamp = field_validator('created_at')(validate_timestamp_text)

ShareSnapshot = Annotated[NoteShareSnapshot | ChatShareSnapshot, Field(discriminator='kind')]

class ShareMetadata(ChatStrictDTO):
    id: ShareId
    kind: Literal['chat', 'note']
    source_id: EntityId
    title: str
    path: Annotated[str, Field(pattern=r'^/share/[A-Za-z0-9_-]{43}$')]
    status: Literal['active', 'revoked']
    source_available: bool
    created_at: str
    revoked_at: str | None
    _timestamps = field_validator('created_at', 'revoked_at')(validate_timestamp_text)

class ShareCreateInput(ChatStrictDTO):
    kind: Literal['chat', 'note']
    source_id: EntityId
    snapshot: ShareSnapshot

class ShareIdInput(ChatStrictDTO):
    id: ShareId

class ShareCursor(ChatStrictDTO):
    created_at: str
    id: ShareId
    _timestamp = field_validator('created_at')(validate_timestamp_text)

class ShareListInput(ChatStrictDTO):
    kind: Literal['chat', 'note']
    status: Literal['active', 'revoked']
    limit: int = Field(ge=1, le=100)
    before: ShareCursor | None

class ShareResult(ChatStrictDTO):
    share: ShareMetadata

class ShareGetResult(ChatStrictDTO):
    share: ShareMetadata | None

class ShareCounts(ChatStrictDTO):
    chat: int = Field(ge=0)
    note: int = Field(ge=0)

class ShareListResult(ChatStrictDTO):
    shares: list[ShareMetadata]
    counts: ShareCounts
    next_cursor: ShareCursor | None

_descriptors = json.loads(Path(__file__).with_name('external_share_contract.json').read_text())['operations']
_types = [(ShareCreateInput, ShareResult), (ShareListInput, ShareListResult), (ShareIdInput, ShareGetResult), (ShareIdInput, ShareResult)]
EXTERNAL_SHARE_OPERATIONS = tuple(DomainOperation(OperationCapabilityDTO.model_validate(descriptor), *types) for descriptor, types in zip(_descriptors, _types, strict=True))
CREATE_SHARE, LIST_SHARES, GET_SHARE, REVOKE_SHARE = EXTERNAL_SHARE_OPERATIONS
