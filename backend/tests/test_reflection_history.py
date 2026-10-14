# [Input] Public report router, production Admin consumer and strict additive history DTOs.
# [Output] Provider-free owner transport, cursor validation, missing capability and exact projection evidence.
# [Pos] Reflections public API contract tests; no normal database, model or schema writes.
# [Sync] 2026-10-14: validate real production entry with an injected external Admin boundary.
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
from routers import reports
from services.admin_data.reflection_history_data import (
    AdminReflectionHistoryData, HISTORY_PAGE, HISTORY_OPERATIONS, ReflectionHistoryCursorDTO,
    ReflectionHistoryInputDTO, ReflectionHistoryOutputDTO,
)
from services.admin_data.reflection_task_data import FROZEN_REFLECTION_TASK_SCHEMA_REQUIREMENTS
from services.admin_data.request_auth import AdminRequestActor

CREATED = "2026-09-30T16:00:00.123456Z"
REPORT_ID = "9007199254740993"

@pytest.fixture
def boundary():
    client = Mock()
    client.supports.return_value = True
    client.execute.return_value = ReflectionHistoryOutputDTO.model_validate({
        "reports": [{"id": REPORT_ID, "report_type": "full_analysis", "report_data_json": '{"echoes":[],"stats":{"days":120}}',
            "created_at": "2026-12-01T00:00:00Z", "task_id": "123e4567-e89b-12d3-a456-426614174000", "analysis_created_at": CREATED}],
        "next_cursor": {"id": REPORT_ID, "created_at": CREATED},
    })
    actor = AdminRequestActor(subject="history-fixture", canonical_user_id="7001", client_id="fixture-browser",
        scopes=frozenset({"dream:read"}), issued_at=1, expires_at=2, access_token="fixture-delegated-user")
    app = FastAPI(); app.include_router(reports.router)
    app.dependency_overrides[reports.get_current_user] = lambda: {"_admin_actor": actor}
    app.dependency_overrides[reports.get_admin_request_auth] = lambda: SimpleNamespace(client=client)
    with TestClient(app) as browser:
        yield browser, client


def test_public_history_preserves_creation_and_decimal_id(boundary):
    browser, client = boundary
    result = browser.get('/api/reports/history', params={"limit": 3, "before_created_at": CREATED, "before_id": REPORT_ID})
    assert result.status_code == 200
    data = result.json()
    assert data['reports'][0]['analysis_created_at'] == CREATED
    assert data['reports'][0]['created_at'] == '2026-12-01T00:00:00Z'
    assert data['reports'][0]['id'] == REPORT_ID
    assert data['next_cursor'] == {"id": REPORT_ID, "created_at": CREATED}
    client.supports.assert_called_once_with(HISTORY_OPERATIONS, FROZEN_REFLECTION_TASK_SCHEMA_REQUIREMENTS)
    operation, value, _ = client.execute.call_args.args
    assert operation is HISTORY_PAGE
    assert value == ReflectionHistoryInputDTO(limit=3, before=ReflectionHistoryCursorDTO(id=REPORT_ID, created_at=CREATED))
    assert client.execute.call_args.kwargs == {"access_token": "fixture-delegated-user"}


@pytest.mark.parametrize('query', [
    {"before_id": REPORT_ID}, {"before_created_at": CREATED}, {"limit": 0},
    {"before_id": "9223372036854775808", "before_created_at": CREATED},
    {"before_id": REPORT_ID, "before_created_at": "2026-02-30T00:00:00Z"},
    {"before_id": REPORT_ID, "before_created_at": "2026-10-01"},
])
def test_invalid_cursor_fails_before_admin_read(boundary, query):
    browser, client = boundary
    assert browser.get('/api/reports/history', params=query).status_code == 422
    client.execute.assert_not_called()


def test_unadvertised_history_capability_fails_closed(boundary):
    browser, client = boundary
    client.supports.return_value = False
    response = browser.get('/api/reports/history')
    assert response.status_code == 503
    assert response.json()['detail']['error_code'] == 'ADMIN_CAPABILITY_UNAVAILABLE'
    client.execute.assert_not_called()


@pytest.mark.parametrize('value', [None, '', '2026-10-01', '2026-02-30T00:00:00Z'])
def test_missing_creation_is_not_replaced_by_report_time(value):
    with pytest.raises(ValidationError):
        ReflectionHistoryOutputDTO.model_validate({"reports": [{"id": REPORT_ID, "report_type": "full_analysis",
            "report_data_json": '{"echoes":[]}', "created_at": '2026-12-01T00:00:00Z',
            "task_id": None, "analysis_created_at": value}], "next_cursor": None})
