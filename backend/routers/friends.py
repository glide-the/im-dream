#!/usr/bin/env python3
# [Input] Current Admin request actor and nine strict social DTO operations.
# [Output] Original /api/friends routes, integer IDs, product errors and image responses.
# [Pos] Social route node; no Dream database or client-authored acting identity.
# [Sync] 2026-05-25: extracted friend and friend-picture routes from backend/server.py.
# [Sync] 2026-09-15: consume Admin invitation/friendship policy and atomic transitions.
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from services.admin_data.chat_models import NonnegativeSafeInteger
from services.admin_data.request_auth import AdminRequestAuth
from services.admin_data.social_data import (
    AdminSocialData, FriendPictureInputDTO, FriendRequestDTO, FriendSelectorDTO,
    FriendTimelineDTO, PublicDatabaseId, SocialEmptyDTO, UseInviteDTO,
)

from .deps import SafeRequestValidationRoute, get_current_user, invoke_admin_operation


class _SocialRoute(SafeRequestValidationRoute):
    validation_error_detail = 'Invalid friend request'


router = APIRouter(route_class=_SocialRoute)
UseInviteCodeRequest = UseInviteDTO
FriendRequestActionRequest = SocialEmptyDTO


def _data(request: Request) -> AdminSocialData:
    owner = getattr(request.app.state, 'admin_request_auth', None)
    if not isinstance(owner, AdminRequestAuth):
        raise HTTPException(status_code=503, detail='ADMIN_CONFIGURATION_INVALID')
    return AdminSocialData(owner.client)


def _decision(result: dict) -> dict:
    if result['success'] is False:
        raise HTTPException(status_code=400, detail=result['error'])
    return result


@router.get('/api/friends/{friend_id}/pictures/{date}/full')
async def get_friend_picture_full_endpoint(
    friend_id: PublicDatabaseId, date: str, current_user: dict = Depends(get_current_user), data: AdminSocialData = Depends(_data),
):
    result = await invoke_admin_operation(current_user, data.full, FriendPictureInputDTO(friend_id=str(friend_id), date=date))
    if not result['image_base64']:
        raise HTTPException(status_code=404, detail='Picture not found or not accessible')
    return result


@router.post('/api/friends/invite/generate')
async def generate_friend_invite(current_user: dict = Depends(get_current_user), data: AdminSocialData = Depends(_data)):
    return await invoke_admin_operation(current_user, data.generate, SocialEmptyDTO())


@router.post('/api/friends/invite/use')
async def use_friend_invite(request: UseInviteCodeRequest, current_user: dict = Depends(get_current_user), data: AdminSocialData = Depends(_data)):
    return _decision(await invoke_admin_operation(current_user, data.use, request))


@router.get('/api/friends/requests')
async def get_friend_requests(current_user: dict = Depends(get_current_user), data: AdminSocialData = Depends(_data)):
    return await invoke_admin_operation(current_user, data.requests, SocialEmptyDTO())


@router.post('/api/friends/requests/{request_id}/accept')
async def accept_friend_request(request_id: PublicDatabaseId, current_user: dict = Depends(get_current_user), data: AdminSocialData = Depends(_data)):
    return _decision(await invoke_admin_operation(current_user, data.accept, FriendRequestDTO(request_id=str(request_id))))


@router.post('/api/friends/requests/{request_id}/reject')
async def reject_friend_request(request_id: PublicDatabaseId, current_user: dict = Depends(get_current_user), data: AdminSocialData = Depends(_data)):
    return _decision(await invoke_admin_operation(current_user, data.reject, FriendRequestDTO(request_id=str(request_id))))


@router.get('/api/friends')
async def get_friends(current_user: dict = Depends(get_current_user), data: AdminSocialData = Depends(_data)):
    return await invoke_admin_operation(current_user, data.friends, SocialEmptyDTO())


@router.delete('/api/friends/{friend_id}')
async def remove_friend(friend_id: PublicDatabaseId, current_user: dict = Depends(get_current_user), data: AdminSocialData = Depends(_data)):
    return _decision(await invoke_admin_operation(current_user, data.remove, FriendSelectorDTO(friend_id=str(friend_id))))


@router.get('/api/friends/{friend_id}/timeline')
async def get_friend_timeline(
    friend_id: PublicDatabaseId, limit: Annotated[NonnegativeSafeInteger, Query()] = 30,
    current_user: dict = Depends(get_current_user), data: AdminSocialData = Depends(_data),
):
    result = await invoke_admin_operation(current_user, data.timeline, FriendTimelineDTO(friend_id=str(friend_id), limit=limit))
    if result['pictures'] is None:
        raise HTTPException(status_code=403, detail='Not friends or friend not found')
    return result
