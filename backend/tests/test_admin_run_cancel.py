# [Input] Actual public cancel/default ingress, registered command DTOs and shared transport fixture.
# [Output] Original reason/model/errors, OAuth and bounded original-receipt technical evidence.
# [Pos] Provider-free production entrypoint harness; default loader/Run handler are not replaced.
# [Sync] 2026-09-15: retain cancellation as Admin state persistence with no local SQL/runtime execution.
from __future__ import annotations

import copy

import httpx
import pytest

from models.workflow_run import WorkflowRun
from routers.story_workspace import _WorkflowRunCancelRequest
from services.admin_data import AdminDataError
from services.admin_data.run_data import AdminRunData, CANCEL_RUN, RunCancelInputDTO
from services.errors.error_registry import WORKFLOW_RUN_ROUTE_ERRORS, build_error_payload, workflow_run_route_error
from tests.test_admin_default_workspace import boundary, PREFIX, READ, WRITE
from tests.test_admin_run_routes import RUN_ID, run

URL = PREFIX + "/workflow-runs/" + RUN_ID + "/cancel"


@pytest.mark.parametrize("payload", [{}, {"reason": "cancel this"}, {"reason": "  Line\nbody\u0085"}, {"reason": "界" * 500}])
def test_public_cancel_keeps_original_reason_and_complete_model(boundary, payload):
    browser, state, calls, *_ = boundary
    response = browser.post(URL, headers=WRITE, json=payload)
    assert response.status_code == 200
    assert response.json() == WorkflowRun.model_validate(state["cancel"]["run"]).model_dump(mode="json")
    assert len(response.json()) == 28 and response.json()["status"] == "cancelled"
    assert [item[0] for item in calls] == ["workspace-default.ensure", "workflow-run.cancel"]
    original_reason = _WorkflowRunCancelRequest.model_validate(payload).reason
    assert calls[1][2] == {"workspace_id": "existing-workspace-1", "workflow_run_id": RUN_ID, "reason_code": f"user_cancelled:{original_reason}"}
    assert original_reason not in repr(RunCancelInputDTO(**calls[1][2]))


def test_repeated_cancel_preserves_producer_result_without_local_transition(boundary):
    browser, _state, calls, *_ = boundary
    first = browser.post(URL, headers=WRITE, json={})
    second = browser.post(URL, headers=WRITE, json={"reason": "another visible reason"})
    assert first.status_code == second.status_code == 200 and first.json() == second.json()
    assert [item[0] for item in calls] == ["workspace-default.ensure", "workflow-run.cancel"] * 2


@pytest.mark.parametrize("payload", [{"reason": ""}, {"reason": " "}, {"reason": None}, {"reason": 12}, {"reason": "x" * 501}, {"reason": "synthetic private reason", "actor_id": "43"}])
def test_original_request_bounds_and_safe_scoped_validation(boundary, payload):
    browser, _state, calls, *_ = boundary
    response = browser.post(URL, headers=WRITE, json=payload)
    assert response.status_code == 422 and response.json() == {"detail": "Invalid Workflow Run request"}
    assert not any(item[0] == "workflow-run.cancel" for item in calls)
    assert "synthetic private reason" not in response.text


@pytest.mark.parametrize("path_id", ["invalid", "run_short", " " + RUN_ID, RUN_ID + " "])
def test_invalid_run_path_keeps_original_not_found_mapping(boundary, path_id):
    browser, _state, calls, *_ = boundary
    response = browser.post(PREFIX + "/workflow-runs/" + path_id + "/cancel", headers=WRITE, json={})
    error = workflow_run_route_error("WORKFLOW_RUN_NOT_FOUND")
    assert response.status_code == error.status_code and response.json() == build_error_payload(error.code)
    assert not any(item[0] == "workflow-run.cancel" for item in calls)


@pytest.mark.parametrize("headers,status", [({}, 401), (READ, 403), ({"authorization": "Bearer idg_" + "a" * 43}, 401)])
def test_public_cancel_uses_oauth_write_scope(boundary, headers, status):
    browser, _state, calls, *_ = boundary
    response = browser.post(URL, headers=headers, json={})
    assert response.status_code == status and calls == []


@pytest.mark.parametrize("code", list(WORKFLOW_RUN_ROUTE_ERRORS))
def test_original_eight_business_error_mapping_is_reused(boundary, code):
    browser, state, calls, *_ = boundary
    state["cancel"] = (WORKFLOW_RUN_ROUTE_ERRORS[code][1], code)
    response = browser.post(URL, headers=WRITE, json={})
    error = workflow_run_route_error(code)
    assert response.status_code == error.status_code and response.json() == build_error_payload(error.code)
    assert len(calls) == 2 and "private upstream" not in response.text


@pytest.mark.parametrize("patch", [{"created_by": "43"}, {"workspace_id": "other"}, {"workflow_run_id": "run_" + "2" * 32}, {"status": "queued"}])
def test_cancel_reply_binding_or_status_mismatch_is_unknown(boundary, patch):
    browser, state, calls, *_ = boundary
    state["cancel"]["run"].update(patch)
    response = browser.post(URL, headers=WRITE, json={})
    assert response.status_code == 503
    assert response.json()["detail"]["outcome_unknown"] is True
    assert response.json()["detail"]["request_id"] == calls[1][1] and len(calls) == 2


@pytest.mark.parametrize("status", ["absent", "committed"])
def test_unknown_cancel_uses_original_two_state_receipt_without_resend(boundary, status):
    browser, state, calls, _schemas, _operations, _data = boundary
    state["cancel"] = httpx.ReadTimeout("synthetic private reason")
    response = browser.post(URL, headers=WRITE, json={"reason": "synthetic private reason"})
    assert response.status_code == 504 and response.json()["detail"]["outcome_unknown"] is True
    rid = response.json()["detail"]["request_id"]
    state["receipt_operation"] = "workflow-run.cancel"
    state["receipt"] = {"status": status, "operation": "workflow-run.cancel", "request_id": rid, **({"result": {"run": run("cancelled")}} if status == "committed" else {})}
    data = AdminRunData(browser.app.state.admin_request_auth.client, canonical_user_id="42")
    receipt = data.receipt(CANCEL_RUN, RunCancelInputDTO(**calls[1][2]), rid, access_token="write-token")
    assert receipt.status == status
    assert [item[0] for item in calls] == ["workspace-default.ensure", "workflow-run.cancel", "receipt"] and calls[2][1] == calls[1][1]
    if status == "committed":
        assert receipt.result.run.status == "cancelled"
    assert "synthetic private reason" not in response.text


@pytest.mark.parametrize("patch", [{"status": "queued"}, {"workflow_run_id": "run_" + "2" * 32}])
def test_committed_receipt_revalidates_original_cancel_result(boundary, patch):
    browser, state, calls, *_ = boundary
    rid = "b6213f0f-2ae3-4647-bdb2-241f8b817370"
    state["receipt_operation"] = "workflow-run.cancel"
    row = copy.deepcopy(run("cancelled"))
    row.update(patch)
    state["receipt"] = {"status": "committed", "operation": "workflow-run.cancel", "request_id": rid, "result": {"run": row}}
    data = AdminRunData(browser.app.state.admin_request_auth.client, canonical_user_id="42")
    with pytest.raises(AdminDataError, match="ADMIN_RESPONSE_INVALID"):
        data.receipt(CANCEL_RUN, RunCancelInputDTO(workspace_id="existing-workspace-1", workflow_run_id=RUN_ID, reason_code=None), rid, access_token="write-token")
    assert calls == [("receipt", rid, None)]


@pytest.mark.parametrize("fault", ["missing", "hash"])
def test_cancel_capability_mismatch_stops_before_command_http(boundary, fault):
    browser, _state, calls, _schemas, operations, _data = boundary
    spec = next(item for item in operations if item["name"] == "workflow-run.cancel")
    if fault == "missing":
        operations.remove(spec)
    else:
        spec["contract_sha256"] = "0" * 64
    response = browser.post(URL, headers=WRITE, json={})
    assert response.status_code == 503 and [item[0] for item in calls] == ["workspace-default.ensure"]


def test_nullable_reason_wire_preserves_original_text_without_new_bounds():
    dto = RunCancelInputDTO(workspace_id="existing", workflow_run_id=RUN_ID, reason_code="  retained\u0085")
    assert dto.reason_code == "  retained\u0085" and RunCancelInputDTO(workspace_id="existing", workflow_run_id=RUN_ID, reason_code=None).reason_code is None
