"""Authenticated same-origin BFF for the Admin public Gateway model catalog."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Depends, HTTPException

from services.admin_gateway import GatewayInferenceError, GatewayModelCatalogClient

from .deps import get_current_user


router = APIRouter()


@router.get("/api/gateway/models")
async def gateway_models(current_user: dict = Depends(get_current_user)):
    try:
        catalog = await asyncio.to_thread(
            GatewayModelCatalogClient(current_user["user_id"]).fetch_catalog
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
