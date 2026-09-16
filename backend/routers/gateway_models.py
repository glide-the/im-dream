# [Input] Current Admin OAuth actor and the server-only Gateway catalog client.
# [Output] Same-origin public model DTOs with subscription-aware callability.
# [Pos] Browser BFF; it never accepts user IDs or exposes Gateway credentials.
# [Sync] 2026-09-16: forward the verified Admin OAuth bearer instead of signing in Dream.
"""Authenticated same-origin BFF for the Admin public Gateway model catalog."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException

from services.admin_gateway import GatewayInferenceError, GatewayModelCatalogClient
from services.admin_data.request_auth import AdminRequestActor

from .deps import get_current_user


router = APIRouter()


@router.get("/api/gateway/models")
async def gateway_models(current_user: dict = Depends(get_current_user)):
    actor = current_user.get("_admin_actor")
    if not isinstance(actor, AdminRequestActor):
        raise HTTPException(status_code=503, detail="ADMIN_CONFIGURATION_INVALID")
    try:
        catalog = await asyncio.to_thread(
            GatewayModelCatalogClient(
                access_token=actor.access_token,
            ).fetch_catalog
        )
    except GatewayInferenceError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": "The platform model catalog is unavailable."},
        ) from exc
    return {
        "data": [model.public_dict() for model in catalog.models],
        "defaultModelAlias": catalog.default_model_alias,
    }
