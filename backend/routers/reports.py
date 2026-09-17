#!/usr/bin/env python3
# [Input] Consume typed Admin analysis-report operations and shared auth dependency.
# [Output] Register /api/reports endpoints.
# [Pos] report route node in backend/routers
# [Sync] 2026-05-25: extracted report routes from backend/server.py.
# [Sync] 2026-09-15: move report list/save persistence to the frozen Admin Reflections domain.

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, ValidationError

from services.admin_data.errors import AdminDataError
from services.admin_data.reflection_task_models import (
    AnalysisReportListInputDTO,
    AnalysisReportSaveInputDTO,
)
from services.admin_data.request_auth import AdminRequestAuth

from .deps import get_admin_request_auth, get_current_user, invoke_admin_operation

router = APIRouter()


class AnalysisReportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    report_type: str
    report_data: dict[str, Any]
    all_notes_text: str = ""


def _data(owner: AdminRequestAuth):
    try:
        return owner.reflections_data()
    except AdminDataError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail={"error_code": exc.code, "outcome_unknown": exc.outcome_unknown},
        ) from None


def _validated_report_input(factory, **values):
    try:
        return factory(**values)
    except ValidationError:
        raise HTTPException(
            status_code=422, detail={"error": "Invalid report request"}
        ) from None


@router.get("/api/reports")
async def get_reports(limit: int = 10,
    current_user: dict = Depends(get_current_user),
    owner: AdminRequestAuth = Depends(get_admin_request_auth)):
    """Get recent analysis reports."""
    result = await invoke_admin_operation(
        current_user,
        _data(owner).list_reports,
        _validated_report_input(AnalysisReportListInputDTO, limit=limit),
    )
    return {
        "reports": [
            {
                "id": item.id,
                "report_type": item.report_type,
                "report_data": item.report_data(),
                "created_at": item.created_at,
            }
            for item in result.reports
        ]
    }


@router.post("/api/reports")
async def save_report(request: AnalysisReportRequest,
    current_user: dict = Depends(get_current_user),
    owner: AdminRequestAuth = Depends(get_admin_request_auth)):
    """
    Save an analysis report.

    Request body:
    {
        "report_type": "echoes" | "traits" | "patterns",
        "report_data": {...},
        "all_notes_text": "optional text"
    }
    """
    if not request.report_type or not request.report_data:
        raise HTTPException(
            status_code=400, detail="report_type and report_data required"
        )
    try:
        raw = json.dumps(
            request.report_data,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError, OverflowError):
        raise HTTPException(status_code=400, detail="invalid report_data") from None
    result = await invoke_admin_operation(
        current_user,
        _data(owner).save_report,
        _validated_report_input(
            AnalysisReportSaveInputDTO,
            report_type=request.report_type,
            report_data_json=raw,
            all_notes_text=request.all_notes_text,
        ),
    )
    return result.model_dump(mode="json")
