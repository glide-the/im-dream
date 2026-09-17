# [Sync] 2026-09-17: reuse the validated immutable Admin capability snapshot instead of repeating discovery per domain call.
# [Input] Actual Admin socialFriendship DTOs/contracts and current request OAuth.
# [Output] Nine exact operations and original public integer IDs/errors/nullable timestamps.
# [Pos] Social consumer; Admin owns invitation policy, pair locks and relationship transitions.
# [Sync] 2026-09-15: replace public friend SQL with closed DTOs and original-ID receipt recovery.
from __future__ import annotations

from typing import Annotated, Literal

from pydantic import AfterValidator, ConfigDict, Field, RootModel, field_validator, model_validator

from .chat_models import ChatStrictDTO, NonnegativeSafeInteger, validate_timestamp_text
from .client import AdminDataClient, DomainOperation
from .errors import AdminDataError
from .models import CanonicalUserId, OperationCapabilityDTO, PrincipalDTO
from .workflow_data import WORKFLOW_SCHEMA_REQUIREMENTS

DecimalId = Annotated[CanonicalUserId, AfterValidator(PrincipalDTO.validate_canonical_id)]
# PostgreSQL bigint and JSON safe-integer boundaries, rather than product quotas.
PublicDatabaseId = Annotated[int, Field(ge=1, le=9_223_372_036_854_775_807)]


class SocialEmptyDTO(ChatStrictDTO):
    pass


class UseInviteDTO(ChatStrictDTO):
    code: str


class FriendRequestDTO(ChatStrictDTO):
    request_id: DecimalId


class FriendSelectorDTO(ChatStrictDTO):
    friend_id: DecimalId


class FriendTimelineDTO(FriendSelectorDTO):
    limit: NonnegativeSafeInteger


class FriendPictureInputDTO(FriendSelectorDTO):
    date: str


class GeneratedInviteDTO(ChatStrictDTO):
    code: str = Field(min_length=1)
    expires_at: str
    _timestamp = field_validator('expires_at')(validate_timestamp_text)


class SocialSuccessDTO(ChatStrictDTO):
    success: Literal[True]

    @model_validator(mode='before')
    @classmethod
    def require_true(cls, value):
        if not isinstance(value, dict) or value.get('success') is not True:
            raise ValueError('Success must be a boolean')
        return value


class SocialFailureDTO(ChatStrictDTO):
    success: Literal[False]
    error: Literal[
        'Invalid invite code', 'Invite code already used', 'Invite code expired',
        'Cannot add yourself as friend', 'Already friends', 'Friend request already pending',
        'Request not found', 'Permission denied', 'Request already accepted',
        'Request already rejected', 'Friendship not found',
    ]

    @model_validator(mode='before')
    @classmethod
    def require_false(cls, value):
        if not isinstance(value, dict) or value.get('success') is not False:
            raise ValueError('Success must be a boolean')
        return value


class InviteUsedDTO(SocialSuccessDTO):
    friend_request_id: DecimalId
    inviter_id: DecimalId
    inviter_name: str


class SocialDecisionDTO(RootModel[Annotated[SocialSuccessDTO | SocialFailureDTO, Field(discriminator='success')]]):
    model_config = ConfigDict(frozen=True, hide_input_in_errors=True)


class InviteUseResultDTO(RootModel[Annotated[InviteUsedDTO | SocialFailureDTO, Field(discriminator='success')]]):
    model_config = ConfigDict(frozen=True, hide_input_in_errors=True)


class PendingFriendDTO(ChatStrictDTO):
    id: DecimalId
    requester_id: DecimalId
    requester_name: str
    created_at: str | None
    _timestamp = field_validator('created_at')(validate_timestamp_text)


class AcceptedFriendDTO(ChatStrictDTO):
    friend_id: DecimalId
    friend_name: str
    friend_email: str
    since: str | None
    _timestamp = field_validator('since')(validate_timestamp_text)


class FriendPictureDTO(ChatStrictDTO):
    date: str
    base64: str
    prompt: str | None
    created_at: str | None
    _timestamp = field_validator('created_at')(validate_timestamp_text)


class PendingFriendsDTO(ChatStrictDTO):
    requests: list[PendingFriendDTO]


class AcceptedFriendsDTO(ChatStrictDTO):
    friends: list[AcceptedFriendDTO]


class FriendPicturesDTO(ChatStrictDTO):
    pictures: list[FriendPictureDTO] | None


class FriendFullPictureDTO(ChatStrictDTO):
    image_base64: str | None


def _operation(name, kind, input_dto, output_dto, digest):
    return DomainOperation(OperationCapabilityDTO(name=name, kind=kind,
        user_scope='dream:read' if kind == 'read' else 'dream:write', background_scope=None,
        input_schema_version=1, output_schema_version=1, contract_sha256=digest), input_dto, output_dto)


GENERATE_INVITE = _operation('friend-invite.generate', 'write', SocialEmptyDTO, GeneratedInviteDTO, '9d23284d2f485948649df4651b40a28974c14d70233b83f3c111fd958b8ffb95')
USE_INVITE = _operation('friend-invite.use', 'write', UseInviteDTO, InviteUseResultDTO, 'ecabd9cd9114d6e1e0933ef44a35f90b148eb9495aaab3fbc8de9f621f266268')
LIST_REQUESTS = _operation('friend-request.list', 'read', SocialEmptyDTO, PendingFriendsDTO, '144c8d5c963e1d35113d071d7e20e9aff228540eeecbb16993924a1afbe1ed77')
ACCEPT_REQUEST = _operation('friend-request.accept', 'write', FriendRequestDTO, SocialDecisionDTO, '0284fd791b8e4866115f07dace29edf5223290a553db459dfbc0fc8d9b232925')
REJECT_REQUEST = _operation('friend-request.reject', 'write', FriendRequestDTO, SocialDecisionDTO, '0b5e94c71120e458087b1ead0e0be729632401a7ab1199788388b8ce78d51f79')
LIST_FRIENDS = _operation('friendship.list', 'read', SocialEmptyDTO, AcceptedFriendsDTO, '2591c795cdbe36e7edaef2241f7c81c755df17acbc8b9d577631d936cc4fb5f4')
REMOVE_FRIEND = _operation('friendship.remove', 'write', FriendSelectorDTO, SocialDecisionDTO, '1c2c37ee6116297d7fb1ee69121c2497dac0e82602be749ce9c9e28a0579a195')
FRIEND_TIMELINE = _operation('friendship.timeline', 'read', FriendTimelineDTO, FriendPicturesDTO, '22b42c3c6fef35994f3ea3467e287e6bf9032888f53356602c1ea904652f41dd')
FRIEND_PICTURE = _operation('friendship.picture-full', 'read', FriendPictureInputDTO, FriendFullPictureDTO, '59af48f8e48b59ffaee5bff2eabaea87d07659c2785dda40d2eabeda107987fe')
SOCIAL_OPERATIONS = (GENERATE_INVITE, USE_INVITE, LIST_REQUESTS, ACCEPT_REQUEST, REJECT_REQUEST,
    LIST_FRIENDS, REMOVE_FRIEND, FRIEND_TIMELINE, FRIEND_PICTURE)


def public_social_result(result) -> dict:
    value = result.model_dump()
    if isinstance(result, InviteUseResultDTO) and isinstance(result.root, InviteUsedDTO):
        for key in ('friend_request_id', 'inviter_id'):
            value[key] = int(value[key])
    elif isinstance(result, PendingFriendsDTO):
        for row in value['requests']:
            for key in ('id', 'requester_id'):
                row[key] = int(row[key])
    elif isinstance(result, AcceptedFriendsDTO):
        for row in value['friends']:
            row['friend_id'] = int(row['friend_id'])
    return value


class AdminSocialData:
    def __init__(self, client: AdminDataClient):
        self._client = client

    def _execute(self, operation, input_dto, request_id, access_token) -> dict:
        capabilities = self._client.capabilities_snapshot(request_id)
        schemas = {item.capability: item for item in capabilities.schema_capabilities}
        if len(schemas) != len(capabilities.schema_capabilities) or any(schemas.get(item.capability) != item for item in WORKFLOW_SCHEMA_REQUIREMENTS):
            raise AdminDataError('ADMIN_CAPABILITY_UNAVAILABLE', 503, request_id)
        result = self._client.execute(operation, input_dto, request_id, access_token=access_token)
        return public_social_result(result)

    def generate(self, input_dto, request_id, *, access_token):
        return self._execute(GENERATE_INVITE, input_dto, request_id, access_token)

    def use(self, input_dto, request_id, *, access_token):
        return self._execute(USE_INVITE, input_dto, request_id, access_token)

    def requests(self, input_dto, request_id, *, access_token):
        return self._execute(LIST_REQUESTS, input_dto, request_id, access_token)

    def accept(self, input_dto, request_id, *, access_token):
        return self._execute(ACCEPT_REQUEST, input_dto, request_id, access_token)

    def reject(self, input_dto, request_id, *, access_token):
        return self._execute(REJECT_REQUEST, input_dto, request_id, access_token)

    def friends(self, input_dto, request_id, *, access_token):
        return self._execute(LIST_FRIENDS, input_dto, request_id, access_token)

    def remove(self, input_dto, request_id, *, access_token):
        return self._execute(REMOVE_FRIEND, input_dto, request_id, access_token)

    def timeline(self, input_dto, request_id, *, access_token):
        return self._execute(FRIEND_TIMELINE, input_dto, request_id, access_token)

    def full(self, input_dto, request_id, *, access_token):
        return self._execute(FRIEND_PICTURE, input_dto, request_id, access_token)

    def receipt(self, operation, request_id, *, access_token):
        if not any(operation is spec and spec.capability.kind == 'write' for spec in SOCIAL_OPERATIONS):
            raise AdminDataError('ADMIN_OPERATION_CONTRACT_INVALID', 503, request_id)
        # Original operation/UUID only. Absent stays absent and never dispatches.
        return self._client.receipt(operation, request_id, access_token=access_token)
