#!/usr/bin/env python3
# [Input] Explicit Admin request actor/typed preferences and unchanged local default-voice config.
# [Output] Register preferences and default-voice endpoints.
# [Pos] preferences route node in backend/routers
# [Sync] 2026-05-25: extracted preference routes from backend/server.py.
# [Sync] 2026-09-15: public preferences use two Admin operations; system/first-login policy remains separate.
# [Sync] 2026-09-15: validation failures return fixed 422 JSON without echoing the request body.

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

import config
from services.admin_data.preferences_data import AdminPreferencesData, PreferencesGetInputDTO, PreferencesSaveRequestDTO
from services.admin_data.request_auth import AdminRequestAuth

from .deps import get_current_user, invoke_admin_operation

class _PreferencesRoute(APIRoute):
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def validate_request(request: Request):
            try:
                return await handler(request)
            except RequestValidationError:
                # Framework validation details include the raw input, which may
                # contain nonfinite JSON numbers or private preference text.
                return JSONResponse(status_code=422, content={"detail": "Invalid preferences request"})

        return validate_request


router = APIRouter(route_class=_PreferencesRoute)


def _data(request: Request) -> AdminPreferencesData:
    owner = getattr(request.app.state, "admin_request_auth", None)
    if not isinstance(owner, AdminRequestAuth):
        raise HTTPException(status_code=503, detail="ADMIN_CONFIGURATION_INVALID")
    return AdminPreferencesData(owner.client)


@router.get("/api/preferences")
async def get_preferences(current_user: dict = Depends(get_current_user), data: AdminPreferencesData = Depends(_data)):
    """Get user preferences."""
    return await invoke_admin_operation(current_user, data.get, PreferencesGetInputDTO())


@router.post("/api/preferences")
async def save_preferences_endpoint(
    request: PreferencesSaveRequestDTO, current_user: dict = Depends(get_current_user), data: AdminPreferencesData = Depends(_data)
):
    """
    Save user preferences.

    Request body can contain any of:
    - voice_configs: dict
    - meta_prompt: str
    - state_config: dict
    - selected_state: str
    """
    result = await invoke_admin_operation(current_user, data.save, request.domain_input())
    return result.model_dump()


@router.get("/api/default-voices")
def get_default_voices():
    """Get default voice configurations"""
    return config.VOICE_ARCHETYPES
