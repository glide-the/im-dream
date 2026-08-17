#!/usr/bin/env python3
"""Run a real local Admin Gateway -> Dream -> Claude Agent smoke test.

The command is intentionally pinned to the named local E2E canonical user. It
never prints access tokens, service keys, provider responses, or assistant text;
expected Product preflight failures use a closed set of safe diagnostic codes.
"""

from __future__ import annotations

import codecs
import hashlib
import json
import os
import sys
import uuid
from collections import Counter
from collections.abc import Iterable
from pathlib import Path

import requests
from dotenv import load_dotenv


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))
load_dotenv(BACKEND_ROOT / ".env")

import auth  # noqa: E402
import database  # noqa: E402
from services.admin_gateway.config import AdminGatewayConfig  # noqa: E402
from services.admin_gateway.token import issue_gateway_subject_token  # noqa: E402


TEST_EMAIL = os.environ.get(
    "INK_GATEWAY_E2E_EMAIL", "codex-free-round55@ink-memory.test"
)
DREAM_BASE_URL = os.environ.get(
    "INK_GATEWAY_E2E_DREAM_BASE_URL", "http://127.0.0.1:8765"
).rstrip("/")
TARGET_MODEL_ALIAS = os.environ.get("INK_GATEWAY_E2E_MODEL_ALIAS", "").strip() or None
EXPECTED_UPSTREAM_MODEL = os.environ.get(
    "INK_GATEWAY_E2E_EXPECTED_UPSTREAM_MODEL", ""
).strip() or None
PROVISION_SUBSCRIPTION = os.environ.get(
    "INK_GATEWAY_E2E_PROVISION_SUBSCRIPTION", ""
).strip().lower() in {"1", "true", "yes", "on"}
PRODUCT_ORIGIN = os.environ.get(
    "INK_GATEWAY_E2E_PRODUCT_ORIGIN", DREAM_BASE_URL
).rstrip("/")
PREFLIGHT_ONLY = os.environ.get(
    "INK_GATEWAY_E2E_PREFLIGHT_ONLY", ""
).strip().lower() in {"1", "true", "yes", "on"}
EXPECTED_AGENT_CONTRACT_VERSION = os.environ.get(
    "INK_AGENT_CONTRACT_VERSION", "2026-05-29-ink-and-memory-v1"
).strip() or "2026-05-29-ink-and-memory-v1"

USER_PROMPT = "Reply with exactly OK. Do not call tools."
_DREAM_AUTHORITY_METADATA_KEYS = (
    "kind",
    "story_workspace_run_id",
    "story_workspace_dream_source",
    "story_workspace_episode_action",
    "workflow_run_id",
    "dreamRunId",
    "dream_run_id",
    "actor_id",
    "visibility",
    "dispatch_status",
    "dispatchStatus",
)


class ModelContractError(RuntimeError):
    """The exact public alias/upstream pair was not configured."""


class SSEProtocolError(RuntimeError):
    """The streamed response violated the canonical Chat SSE contract."""


class BusinessPreflightError(RuntimeError):
    """An expected provider-free Product preflight boundary rejected the run."""

    def __init__(self, phase: str, error_code: str) -> None:
        super().__init__(error_code)
        self.phase = phase
        self.error_code = error_code


def _required_model_contract() -> tuple[str, str]:
    """Fail before database or HTTP activity unless both exact models exist."""

    if not TARGET_MODEL_ALIAS or not EXPECTED_UPSTREAM_MODEL:
        raise ModelContractError("exact model alias and upstream model are required")
    return TARGET_MODEL_ALIAS, EXPECTED_UPSTREAM_MODEL


def _sse_lines(chunks: Iterable[bytes]) -> Iterable[str]:
    """Incrementally decode UTF-8 SSE lines without assuming chunk boundaries."""

    decoder = codecs.getincrementaldecoder("utf-8")(errors="strict")
    buffer = ""

    def complete_lines(*, eof: bool) -> Iterable[str]:
        nonlocal buffer
        while buffer:
            cr = buffer.find("\r")
            lf = buffer.find("\n")
            positions = [position for position in (cr, lf) if position >= 0]
            if not positions:
                break
            end = min(positions)
            terminator = buffer[end]
            if terminator == "\r" and end + 1 == len(buffer) and not eof:
                break
            consumed = end + 1
            if (
                terminator == "\r"
                and consumed < len(buffer)
                and buffer[consumed] == "\n"
            ):
                consumed += 1
            line = buffer[:end]
            buffer = buffer[consumed:]
            yield line

    for chunk in chunks:
        if not isinstance(chunk, (bytes, bytearray)):
            raise SSEProtocolError("SSE transport yielded a non-byte chunk")
        if not chunk:
            continue
        try:
            buffer += decoder.decode(bytes(chunk), final=False)
        except UnicodeDecodeError as exc:
            raise SSEProtocolError("SSE payload is not valid UTF-8") from exc
        yield from complete_lines(eof=False)

    try:
        buffer += decoder.decode(b"", final=True)
    except UnicodeDecodeError as exc:
        raise SSEProtocolError("SSE payload ended inside a UTF-8 sequence") from exc
    yield from complete_lines(eof=True)
    if buffer:
        raise SSEProtocolError("SSE payload ended with an unterminated line")


def _parse_sse_chunks(chunks: Iterable[bytes]) -> list[dict]:
    """Parse the canonical data-only SSE stream and enforce its terminal order."""

    frames: list[dict] = []
    data_lines: list[str] = []
    finish_seen = False

    for line in _sse_lines(chunks):
        if finish_seen and line:
            raise SSEProtocolError("SSE data appeared after the terminal frame")
        if line == "":
            if not data_lines:
                continue
            raw_data = "\n".join(data_lines)
            data_lines.clear()
            try:
                frame = json.loads(raw_data)
            except (TypeError, ValueError) as exc:
                raise SSEProtocolError("SSE data is not valid JSON") from exc
            if not isinstance(frame, dict):
                raise SSEProtocolError("SSE JSON frame must be an object")
            frame_type = frame.get("type")
            if not isinstance(frame_type, str) or not frame_type:
                raise SSEProtocolError("SSE JSON frame has no type")
            frames.append(frame)
            if frame_type == "finish":
                finish_seen = True
            continue
        if line.startswith(":"):
            if data_lines:
                raise SSEProtocolError("SSE comment split a data event")
            continue
        field, separator, value = line.partition(":")
        if field != "data":
            raise SSEProtocolError("canonical Chat SSE permits only data fields")
        if separator and value.startswith(" "):
            value = value[1:]
        data_lines.append(value if separator else "")

    if data_lines:
        raise SSEProtocolError("SSE payload ended before an event boundary")
    frame_types = [str(frame["type"]) for frame in frames]
    if frame_types.count("message-final") != 1 or frame_types.count("finish") != 1:
        raise SSEProtocolError("SSE must contain one message-final and one finish")
    if len(frame_types) < 2 or frame_types[-2:] != ["message-final", "finish"]:
        raise SSEProtocolError("SSE must end with message-final then finish")

    text_start_count = frame_types.count("text-start")
    text_delta_count = frame_types.count("text-delta")
    text_end_count = frame_types.count("text-end")
    if text_start_count != 1 or text_delta_count < 1 or text_end_count != 1:
        raise SSEProtocolError("SSE must contain one non-empty incremental text block")
    text_start_index = frame_types.index("text-start")
    expected_text_tail = [
        "text-start",
        *(["text-delta"] * text_delta_count),
        "text-end",
        "message-final",
        "finish",
    ]
    if frame_types[text_start_index:] != expected_text_tail:
        raise SSEProtocolError("SSE incremental text frames are out of order")
    nonempty_text_delta_count = 0
    for frame in frames:
        if frame["type"] != "text-delta":
            continue
        delta = frame.get("delta")
        if not isinstance(delta, str):
            raise SSEProtocolError("SSE text-delta must be text")
        if delta.strip():
            nonempty_text_delta_count += 1
    if nonempty_text_delta_count < 1:
        raise SSEProtocolError("SSE must contain a non-empty text-delta")
    final_frame = frames[-2]
    final_text = final_frame.get("text")
    if not isinstance(final_text, str) or not final_text.strip():
        raise SSEProtocolError("message-final text must be non-empty")
    return frames


def _parse_sse_response(response: requests.Response) -> list[dict]:
    """Validate MIME and parse deliberately small raw chunks from a response."""

    media_type = (
        response.headers.get("content-type", "")
        .split(";", 1)[0]
        .strip()
        .lower()
    )
    if media_type != "text/event-stream":
        raise SSEProtocolError("canonical Chat stream has an invalid media type")
    return _parse_sse_chunks(response.iter_content(chunk_size=17, decode_unicode=False))


def _projected_history_receipt(
    history_messages: object,
    *,
    expected_user_text: str,
) -> dict[str, bool | int]:
    """Validate projected REST history without returning any message content."""

    if not isinstance(history_messages, list):
        return {
            "messageCount": 0,
            "userCount": 0,
            "assistantCount": 0,
            "malformedMessageCount": 1,
            "blankProjectionCount": 0,
            "privateDiscriminatorCount": 0,
            "exactUserTextPart": False,
            "assistantSingleNonemptyText": False,
            "valid": False,
        }

    messages = [message for message in history_messages if isinstance(message, dict)]
    malformed_count = len(history_messages) - len(messages) + sum(
        1 for message in messages if not isinstance(message.get("metadata"), dict)
    )
    users = [message for message in messages if message.get("role") == "user"]
    assistants = [
        message for message in messages if message.get("role") == "assistant"
    ]
    blank_projection_count = sum(
        1
        for message in messages
        if not isinstance(message.get("parts"), list) or not message.get("parts")
    )
    private_discriminator_count = sum(
        1
        for message in messages
        if isinstance((metadata := message.get("metadata")), dict)
        and any(key in metadata for key in _DREAM_AUTHORITY_METADATA_KEYS)
    )

    exact_user_text = bool(
        len(users) == 1
        and users[0].get("parts")
        == [{"type": "text", "text": expected_user_text}]
    )
    assistant_single_nonempty_text = False
    if len(assistants) == 1:
        assistant_parts = assistants[0].get("parts")
        if isinstance(assistant_parts, list) and len(assistant_parts) == 1:
            part = assistant_parts[0]
            assistant_single_nonempty_text = bool(
                isinstance(part, dict)
                and set(part) == {"type", "text"}
                and part.get("type") == "text"
                and isinstance(part.get("text"), str)
                and part["text"].strip()
            )

    valid = bool(
        len(history_messages) == 2
        and malformed_count == 0
        and len(users) == 1
        and len(assistants) == 1
        and exact_user_text
        and assistant_single_nonempty_text
        and blank_projection_count == 0
        and private_discriminator_count == 0
    )
    return {
        "messageCount": len(history_messages),
        "userCount": len(users),
        "assistantCount": len(assistants),
        "malformedMessageCount": malformed_count,
        "blankProjectionCount": blank_projection_count,
        "privateDiscriminatorCount": private_discriminator_count,
        "exactUserTextPart": exact_user_text,
        "assistantSingleNonemptyText": assistant_single_nonempty_text,
        "valid": valid,
    }


def _json(response: requests.Response) -> dict:
    try:
        value = response.json()
    except ValueError:
        return {}
    return value if isinstance(value, dict) else {}


def _safe_error_code(response: requests.Response) -> str | None:
    payload = _json(response)
    error = payload.get("error")
    detail = payload.get("detail")
    for value in (error, detail, payload):
        if isinstance(value, dict):
            code = value.get("code") or value.get("error_code")
            if isinstance(code, str):
                return code
    return None


def _require_json_response(response: requests.Response, phase: str) -> dict:
    payload = _json(response)
    if response.status_code < 200 or response.status_code >= 300:
        raise RuntimeError(
            f"{phase} failed: status={response.status_code} "
            f"code={_safe_error_code(response) or 'UNKNOWN'}"
        )
    return payload


def _model_aliases(entitlements: object) -> set[str]:
    aliases: set[str] = set()
    if not isinstance(entitlements, list):
        return aliases
    for entitlement in entitlements:
        if not isinstance(entitlement, dict):
            continue
        values = entitlement.get("modelAliases")
        if isinstance(values, list):
            aliases.update(str(value) for value in values if isinstance(value, str))
    return aliases


def _remaining_tokens(context_data: dict) -> int:
    allowance = context_data.get("allowance")
    if not isinstance(allowance, dict):
        return 0
    remaining = allowance.get("remaining")
    return int(remaining) if isinstance(remaining, int) and not isinstance(remaining, bool) else 0


def _current_subscription_access_evidence(
    context_data: dict, model_alias: str
) -> dict | None:
    """Describe an existing Product subject using Gateway's allowance policy."""

    subscription = context_data.get("subscription")
    plan = context_data.get("planVersion")
    if (
        not isinstance(subscription, dict)
        or not isinstance(plan, dict)
        or _remaining_tokens(context_data) <= 0
    ):
        return None
    exact_entitlement = model_alias in _model_aliases(
        context_data.get("entitlements")
    )
    return {
        "provisioned": False,
        "planCode": plan.get("planCode"),
        "remainingTokensPositive": True,
        "accessMode": "plan-entitlement" if exact_entitlement else "allowance-only",
    }


def _ensure_subscription(auth_headers: dict[str, str], model_alias: str) -> dict:
    """Accept an eligible subject or provision an authorized clone-only one."""

    context_response = requests.get(
        f"{DREAM_BASE_URL}/api/story-workspace/subscription/context",
        headers=auth_headers,
        timeout=20,
    )
    context_payload = _require_json_response(context_response, "subscription-context")
    context_data = context_payload.get("data")
    if not isinstance(context_data, dict):
        raise BusinessPreflightError(
            "subscription-context", "INVALID_PRODUCT_CONTEXT_PAYLOAD"
        )
    existing_access = _current_subscription_access_evidence(
        context_data, model_alias
    )
    if existing_access is not None:
        return existing_access
    if not PROVISION_SUBSCRIPTION:
        raise BusinessPreflightError(
            "subscription-preflight", "SUBSCRIPTION_OR_ALLOWANCE_UNAVAILABLE"
        )
    if context_data.get("subscription") is not None:
        raise BusinessPreflightError(
            "subscription-preflight", "EXISTING_SUBJECT_LACKS_EXACT_ENTITLEMENT"
        )

    plans_response = requests.get(
        f"{DREAM_BASE_URL}/api/story-workspace/subscription/plans",
        headers=auth_headers,
        params={"page": 1, "pageSize": 20},
        timeout=20,
    )
    plans_payload = _require_json_response(plans_response, "subscription-plans")
    plans = plans_payload.get("data")
    if not isinstance(plans, list):
        raise BusinessPreflightError(
            "subscription-plans", "INVALID_PRODUCT_PLANS_PAYLOAD"
        )
    candidates = [
        plan
        for plan in plans
        if isinstance(plan, dict)
        and plan.get("available") is True
        and isinstance(plan.get("planVersionId"), str)
        and "create" in (plan.get("availableActions") or [])
        and model_alias in _model_aliases(plan.get("entitlements"))
    ]
    candidates.sort(
        key=lambda plan: (
            int(plan.get("monthlyPriceMicrousd") or 0),
            -int(plan.get("monthlyAllowanceTokens") or 0),
            str(plan.get("planCode") or ""),
        )
    )
    if not candidates:
        raise BusinessPreflightError(
            "subscription-plans", "NO_CREATABLE_EXACT_MODEL_PLAN"
        )
    target = candidates[0]
    if int(target.get("monthlyPriceMicrousd") or 0) != 0:
        raise BusinessPreflightError(
            "subscription-plans", "PAID_PLAN_REQUIRES_EXTERNAL_AUTHORITY"
        )

    write_headers = {
        **auth_headers,
        "content-type": "application/json",
        "origin": PRODUCT_ORIGIN,
    }
    preview_response = requests.post(
        f"{DREAM_BASE_URL}/api/story-workspace/subscription/commands",
        headers=write_headers,
        json={
            "action": "create",
            "phase": "preview",
            "targetPlanVersionId": target["planVersionId"],
            "expectedVersion": None,
        },
        timeout=20,
    )
    preview_payload = _require_json_response(preview_response, "subscription-preview")
    preview = preview_payload.get("data")
    if (
        not isinstance(preview, dict)
        or preview.get("allowed") is not True
        or model_alias
        not in _model_aliases(
            [{"modelAliases": (preview.get("entitlementImpact") or {}).get("targetModelAliases")}]
        )
        or (preview.get("gatewayImpact") or {}).get("callableAfterExecute") is not True
    ):
        raise BusinessPreflightError(
            "subscription-preview", "EXACT_ENTITLEMENT_NOT_AUTHORIZED"
        )

    execute_headers = {
        **write_headers,
        "idempotency-key": f"gateway-real-e2e-{uuid.uuid4()}",
    }
    execute_response = requests.post(
        f"{DREAM_BASE_URL}/api/story-workspace/subscription/commands",
        headers=execute_headers,
        json={
            "action": "create",
            "phase": "execute",
            "targetPlanVersionId": target["planVersionId"],
            "expectedVersion": None,
            "previewId": preview.get("previewId"),
            "digest": preview.get("digest"),
            "expiresAt": preview.get("expiresAt"),
            "reason": "Isolated real-model release verification",
        },
        timeout=20,
    )
    execute_payload = _require_json_response(execute_response, "subscription-execute")
    result = execute_payload.get("data")
    if not isinstance(result, dict) or result.get("outcome") != "applied":
        raise BusinessPreflightError(
            "subscription-execute", "SUBSCRIPTION_NOT_APPLIED"
        )

    verified_response = requests.get(
        f"{DREAM_BASE_URL}/api/story-workspace/subscription/context",
        headers=auth_headers,
        timeout=20,
    )
    verified_payload = _require_json_response(verified_response, "subscription-verify")
    verified = verified_payload.get("data")
    if (
        not isinstance(verified, dict)
        or model_alias not in _model_aliases(verified.get("entitlements"))
        or _remaining_tokens(verified) <= 0
    ):
        raise BusinessPreflightError(
            "subscription-verify", "ENTITLEMENT_OR_ALLOWANCE_MISSING"
        )
    return {
        "provisioned": True,
        "planCode": target.get("planCode"),
        "remainingTokensPositive": True,
        "accessMode": "plan-entitlement",
    }


def _metrics(platform_user_id: str) -> dict[str, int]:
    connection = database.get_db()
    try:
        cursor = connection.execute(
            """
            SELECT
              requests.total,
              requests.settled,
              ledger.total
            FROM (
              SELECT COUNT(*)::bigint AS total,
                     COUNT(*) FILTER (WHERE settled_at IS NOT NULL)::bigint AS settled
                FROM gateway_requests
               WHERE platform_user_id = %s
            ) AS requests
            CROSS JOIN (
              SELECT COUNT(*)::bigint AS total
                FROM subscription_token_ledger_entries
               WHERE platform_user_id = %s
            ) AS ledger
            """,
            (platform_user_id, platform_user_id),
        )
        row = cursor.fetchone()
        return {
            "gatewayRequests": int(row[0]),
            "settledGatewayRequests": int(row[1]),
            "tokenLedger": int(row[2]),
        }
    finally:
        connection.close()


def _gateway_receipt(
    platform_user_id: str,
    idempotency_key: str,
    expected_alias: str,
    expected_upstream: str,
) -> dict:
    request_key_prefix = (
        "turn-"
        + hashlib.sha256(idempotency_key.encode("utf-8")).hexdigest()[:24]
        + "-request-"
    )
    connection = database.get_db()
    try:
        rows = connection.execute(
            """
            SELECT id, status, outcome, http_status, requested_model,
                   resolved_model, response_summary ->> 'model' AS provider_model,
                   upstream_request_id IS NOT NULL AS upstream_id_present,
                   subscription_entitlement_id IS NOT NULL AS entitlement_bound,
                   subscription_id, settled_at IS NOT NULL AS settled
              FROM gateway_requests
             WHERE platform_user_id = %s AND idempotency_key LIKE %s
            """,
            (platform_user_id, request_key_prefix + "%"),
        ).fetchall()
        if len(rows) != 1:
            raise RuntimeError(
                f"gateway-receipt failed: expected one request, found {len(rows)}"
            )
        row = rows[0]
        ledger = connection.execute(
            """
            SELECT request_sequence, entry_type, amount_tokens
              FROM subscription_token_ledger_entries
             WHERE gateway_request_id = %s
             ORDER BY request_sequence
            """,
            (row[0],),
        ).fetchall()
        reserved = sum(int(item[2]) for item in ledger if item[1] == "reserve")
        captured = sum(int(item[2]) for item in ledger if item[1] == "capture")
        released = sum(int(item[2]) for item in ledger if item[1] == "release")
        allowance_reserved = connection.execute(
            """
            SELECT COALESCE(SUM(reserved_tokens), 0)
              FROM subscription_usage_allowances
             WHERE subscription_id = %s
            """,
            (row[9],),
        ).fetchone()[0]
        if not (
            row[1] == "settled"
            and row[2] == "succeeded"
            and row[3] == 200
            and row[4] == expected_alias
            and row[5] == expected_upstream
            and row[6] == expected_upstream
            and bool(row[7])
            and bool(row[8])
            and bool(row[10])
            and reserved > 0
            and reserved == captured + released
            and int(allowance_reserved) == 0
        ):
            raise RuntimeError("gateway-receipt failed: routing or settlement mismatch")
        return {
            "requestCount": 1,
            "status": row[1],
            "outcome": row[2],
            "httpStatus": row[3],
            "requestedAlias": row[4],
            "resolvedUpstream": row[5],
            "providerReportedModel": row[6],
            "upstreamRequestIdPresent": bool(row[7]),
            "entitlementBound": bool(row[8]),
            "ledgerEntryTypes": [str(item[1]) for item in ledger],
            "reserveEqualsCapturePlusRelease": reserved == captured + released,
            "reservedTokens": int(allowance_reserved),
        }
    finally:
        connection.close()


def _thread_receipt(
    thread_id: str,
    user_id: str,
    message_id: str,
    *,
    expected_user_text: str,
    expected_alias: str,
    expected_session_id: str,
    expected_agent_contract_version: str,
) -> dict:
    connection = database.get_db()
    try:
        receipt = connection.execute(
            """
            WITH messages AS (
              SELECT id, role, parts::jsonb AS parts_json,
                     COALESCE(metadata, '{}')::jsonb AS metadata_json
                FROM chat_message
               WHERE thread_id = %s
            )
            SELECT
              COUNT(*) FILTER (WHERE role = 'user')::int AS user_count,
              COUNT(*) FILTER (WHERE role = 'assistant')::int AS assistant_count,
              COUNT(*)::int AS total_count,
              COALESCE(BOOL_AND(
                id = %s
                AND jsonb_typeof(parts_json) = 'array'
                AND jsonb_array_length(parts_json) = 1
                AND parts_json -> 0 ->> 'type' = 'text'
                AND parts_json -> 0 ->> 'text' = %s
              ) FILTER (WHERE role = 'user'), FALSE) AS exact_user_message,
              COALESCE(BOOL_AND(
                jsonb_typeof(parts_json) = 'array'
                AND EXISTS (
                  SELECT 1 FROM jsonb_array_elements(parts_json) AS part
                   WHERE part ->> 'type' = 'text'
                     AND LENGTH(BTRIM(COALESCE(part ->> 'text', ''))) > 0
                )
                AND NOT EXISTS (
                  SELECT 1 FROM jsonb_array_elements(parts_json) AS part
                   WHERE part ->> 'type' LIKE 'tool%%'
                )
                AND (
                  metadata_json -> 'is_partial' IS NULL
                  OR metadata_json -> 'is_partial' = 'false'::jsonb
                )
                AND metadata_json -> 'chatModel' ->> 'provider' = 'gateway'
                AND metadata_json -> 'chatModel' ->> 'model' = %s
              ) FILTER (WHERE role = 'assistant'), FALSE) AS exact_assistant_message,
              COALESCE(BOOL_AND(
                NOT metadata_json ?| %s::text[]
              ), FALSE) AS no_dream_authority
            FROM messages
            """,
            (
                thread_id,
                message_id,
                expected_user_text,
                expected_alias,
                list(_DREAM_AUTHORITY_METADATA_KEYS),
            ),
        ).fetchall()
        if len(receipt) != 1:
            raise RuntimeError("thread-receipt failed: persistence aggregate missing")
        row = receipt[0]
        thread = connection.execute(
            """
            SELECT claude_session_id = %s AS exact_session,
                   agent_contract_version = %s AS exact_contract_version
              FROM chat_thread
             WHERE id = %s AND user_id = %s
            """,
            (
                expected_session_id,
                expected_agent_contract_version,
                thread_id,
                int(user_id),
            ),
        ).fetchone()
        if not (
            int(row[0]) == 1
            and int(row[1]) == 1
            and int(row[2]) == 2
            and bool(row[3])
            and bool(row[4])
            and bool(row[5])
            and thread is not None
            and bool(thread[0])
            and bool(thread[1])
        ):
            raise RuntimeError("thread-receipt failed: canonical persistence mismatch")
        return {
            "roleCounts": {"assistant": int(row[1]), "user": int(row[0])},
            "exactUserTextPart": True,
            "assistantNonempty": True,
            "assistantToolParts": False,
            "assistantPartial": False,
            "storedChatModel": {
                "provider": "gateway",
                "model": expected_alias,
            },
            "dreamAuthorityMetadataPresent": False,
            "sdkSessionMatchesFinal": True,
            "agentContractVersionMatchesRuntime": True,
        }
    finally:
        connection.close()


def main() -> int:
    model_alias, expected_upstream_model = _required_model_contract()

    connection = database.get_db()
    try:
        user = connection.execute(
            "SELECT id, email FROM users WHERE email = %s AND status = 'active'",
            (TEST_EMAIL,),
        ).fetchone()
        if user is None:
            raise RuntimeError("The local E2E canonical user is not provisioned")
        canonical_user_id = str(user[0])
        projection = connection.execute(
            """
            SELECT id FROM platform_users
             WHERE source = 'ink-dream' AND external_user_id = %s AND status = 'active'
            """,
            (canonical_user_id,),
        ).fetchone()
        if projection is None:
            raise RuntimeError("The local E2E billing projection is unavailable")
        platform_user_id = str(projection[0])
    finally:
        connection.close()

    dream_token = auth.create_access_token(canonical_user_id, TEST_EMAIL)
    auth_headers = {"authorization": f"Bearer {dream_token}"}
    dream_health = requests.get(f"{DREAM_BASE_URL}/api/health", timeout=10)
    if dream_health.status_code != 200:
        print(json.dumps({"phase": "dream-health", "status": dream_health.status_code}))
        return 1

    subscription_evidence: dict | None = None
    if PROVISION_SUBSCRIPTION:
        subscription_evidence = _ensure_subscription(
            auth_headers, model_alias
        )

    gateway = AdminGatewayConfig.from_environment()
    gateway_subject = issue_gateway_subject_token(
        gateway,
        canonical_user_id,
        scope="models:list",
    )
    admin_models = requests.get(
        f"{gateway.base_url}/v1/models",
        headers={
            "authorization": f"Bearer {gateway_subject}",
            "x-api-key": gateway.service_key,
            "accept": "application/json",
        },
        timeout=20,
    )
    admin_payload = _json(admin_models)
    admin_data = admin_payload.get("data") if isinstance(admin_payload.get("data"), list) else []
    if admin_models.status_code != 200 or not admin_data:
        print(json.dumps({
            "phase": "admin-model-catalog",
            "status": admin_models.status_code,
            "errorCode": _safe_error_code(admin_models),
        }))
        return 1
    selected_admin_model = next(
        (
            item for item in admin_data
            if isinstance(item, dict) and item.get("id") == model_alias
        ),
        None,
    )
    if not selected_admin_model:
        print(json.dumps({
            "phase": "admin-model-catalog",
            "status": 200,
            "errorCode": "EXACT_MODEL_ALIAS_MISSING",
        }))
        return 1
    if selected_admin_model.get("callable") is not True:
        print(json.dumps({
            "phase": "admin-model-callability",
            "status": 200,
            "availability": selected_admin_model.get("availability"),
        }))
        return 1
    selected_alias = str(selected_admin_model.get("id") or "")
    if selected_alias != model_alias:
        raise ModelContractError("model catalog selected a different alias")

    dream_models = requests.get(
        f"{DREAM_BASE_URL}/api/gateway/models",
        headers=auth_headers,
        timeout=20,
    )
    dream_payload = _json(dream_models)
    dream_data = dream_payload.get("data") if isinstance(dream_payload.get("data"), list) else []
    if dream_models.status_code != 200 or model_alias not in {
        str(item.get("modelAlias")) for item in dream_data if isinstance(item, dict)
    }:
        print(json.dumps({
            "phase": "dream-model-catalog",
            "healthStatus": dream_health.status_code,
            "status": dream_models.status_code,
            "errorCode": _safe_error_code(dream_models),
        }))
        return 1
    selected_dream_model = next(
        (item for item in dream_data if isinstance(item, dict) and item.get("modelAlias") == model_alias),
        None,
    )
    if not selected_dream_model or selected_dream_model.get("callable") is not True:
        print(json.dumps({"phase": "dream-model-callability", "status": dream_models.status_code}))
        return 1

    if subscription_evidence is None:
        subscription_evidence = _ensure_subscription(auth_headers, model_alias)

    plans_response = requests.get(
        f"{DREAM_BASE_URL}/api/story-workspace/subscription/plans",
        headers=auth_headers,
        params={"page": 1, "pageSize": 20},
        timeout=20,
    )
    plans_payload = _json(plans_response)
    plans_data = plans_payload.get("data") if isinstance(plans_payload.get("data"), list) else []
    plan_states = {
        str(plan.get("planCode")): {
            "available": plan.get("available"),
            "versionStatus": plan.get("versionStatus"),
        }
        for plan in plans_data if isinstance(plan, dict)
    }
    if plans_response.status_code != 200 or not plan_states:
        print(json.dumps({
            "phase": "dream-product-plans",
            "status": plans_response.status_code,
            "errorCode": _safe_error_code(plans_response),
        }))
        return 1

    config_response = requests.put(
        f"{DREAM_BASE_URL}/api/system-config",
        headers={**auth_headers, "content-type": "application/json"},
        json={"provider": "gateway", "model": model_alias},
        timeout=20,
    )
    config_payload = _json(config_response)
    config_data = config_payload.get("data")
    if (
        config_response.status_code != 200
        or not isinstance(config_data, dict)
        or config_data.get("provider") != "gateway"
        or config_data.get("model") != model_alias
    ):
        print(json.dumps({
            "phase": "dream-model-selection",
            "status": config_response.status_code,
            "errorCode": _safe_error_code(config_response),
        }))
        return 1

    if PREFLIGHT_ONLY:
        print(json.dumps({
            "preflightOnly": True,
            "adminModelsStatus": admin_models.status_code,
            "dreamModelsStatus": dream_models.status_code,
            "selectedAlias": model_alias,
            "subscription": subscription_evidence,
            "modelSelectionStatus": config_response.status_code,
            "providerCalled": False,
            "secretsPrinted": False,
            "privateContentPrinted": False,
        }, ensure_ascii=False, sort_keys=True))
        return 0

    thread_response = requests.post(
        f"{DREAM_BASE_URL}/api/claude-agent/threads",
        headers={**auth_headers, "content-type": "application/json"},
        json={"title": "gateway-real-e2e"},
        timeout=20,
    )
    thread_id = _json(thread_response).get("thread_id")
    if thread_response.status_code != 200 or not isinstance(thread_id, str):
        print(json.dumps({
            "phase": "claude-thread",
            "status": thread_response.status_code,
            "errorCode": _safe_error_code(thread_response),
        }))
        return 1

    before = _metrics(platform_user_id)
    message_id = f"gateway-real-e2e-{uuid.uuid4()}"
    idempotency_key = "dream-turn-" + hashlib.sha256(
        f"{canonical_user_id}\n{thread_id}\n{message_id}".encode("utf-8")
    ).hexdigest()
    with requests.post(
        f"{DREAM_BASE_URL}/api/claude-agent",
        headers={**auth_headers, "content-type": "application/json"},
        json={
            "thread_id": thread_id,
            "message": {
                "id": message_id,
                "role": "user",
                "parts": [
                    {
                        "type": "text",
                        "text": USER_PROMPT,
                    }
                ],
            },
            "model": model_alias,
            "resume": False,
            "toolChoice": "none",
            "max_turns": 1,
        },
        stream=True,
        timeout=(20, 300),
    ) as stream_response:
        content_type = stream_response.headers.get("content-type", "")
        if stream_response.status_code != 200:
            print(json.dumps({
                "phase": "claude-agent-sse",
                "status": stream_response.status_code,
                "contentType": content_type.split(";", 1)[0],
                "errorCode": _safe_error_code(stream_response),
            }))
            return 1
        frames = _parse_sse_response(stream_response)
        incremental_text_sequence_valid = True
        frame_types: Counter[str] = Counter()
        terminal_error_code = None
        finish_reasons: list[str] = []
        finish_cancelled: list[bool] = []
        final_session_id: str | None = None
        final_text_nonempty = False
        nonempty_text_delta_count = 0
        for frame in frames:
            frame_type = str(frame["type"])
            frame_types[frame_type] += 1
            if frame_type == "finish":
                finish_reasons.append(str(frame.get("finishReason") or ""))
                finish_cancelled.append(frame.get("cancelled") is True)
            if frame_type == "message-final":
                session_id = frame.get("sessionId")
                if not isinstance(session_id, str) or not session_id:
                    raise SSEProtocolError("message-final has no SDK session")
                final_session_id = session_id
                final_text = frame.get("text")
                final_text_nonempty = bool(
                    isinstance(final_text, str) and final_text.strip()
                )
            if frame_type == "text-delta":
                delta = frame.get("delta")
                if isinstance(delta, str) and delta.strip():
                    nonempty_text_delta_count += 1
            if frame_type == "error":
                code = frame.get("code") or frame.get("error_code")
                terminal_error_code = str(code) if code else None

    if final_session_id is None:
        raise SSEProtocolError("message-final has no SDK session")

    after = _metrics(platform_user_id)
    deltas = {key: after[key] - before[key] for key in before}
    gateway_receipt = _gateway_receipt(
        platform_user_id,
        idempotency_key,
        model_alias,
        expected_upstream_model,
    )
    thread_receipt = _thread_receipt(
        thread_id,
        canonical_user_id,
        message_id,
        expected_user_text=USER_PROMPT,
        expected_alias=model_alias,
        expected_session_id=final_session_id,
        expected_agent_contract_version=EXPECTED_AGENT_CONTRACT_VERSION,
    )
    history_response = requests.get(
        f"{DREAM_BASE_URL}/api/claude-agent/threads/{thread_id}/messages",
        headers=auth_headers,
        timeout=20,
    )
    history_payload = _require_json_response(history_response, "thread-history")
    history_messages = history_payload.get("messages")
    history_receipt = _projected_history_receipt(
        history_messages,
        expected_user_text=USER_PROMPT,
    )
    status_response = requests.get(
        f"{DREAM_BASE_URL}/api/claude-agent/threads/{thread_id}/status",
        headers=auth_headers,
        timeout=20,
    )
    status_payload = _require_json_response(status_response, "thread-status")
    tool_frames = sum(
        count for frame_type, count in frame_types.items()
        if frame_type.startswith("tool-")
    )
    receipt = {
        "adminModels": {
            "status": admin_models.status_code,
            "count": len(admin_data),
            "selectedAlias": model_alias,
        },
        "dreamModels": {
            "healthStatus": dream_health.status_code,
            "status": dream_models.status_code,
            "count": len(dream_data),
            "availabilityCounts": dict(sorted(Counter(
                str(item.get("availability")) for item in dream_data if isinstance(item, dict)
            ).items())),
        },
        "subscription": subscription_evidence,
        "productPlans": {
            "status": plans_response.status_code,
            "count": len(plan_states),
        },
        "modelSelection": {"status": config_response.status_code},
        "claudeAgent": {
            "threadStatus": thread_response.status_code,
            "streamStatus": stream_response.status_code,
            "contentType": content_type.split(";", 1)[0],
            "frameTypes": dict(sorted(frame_types.items())),
            "finishReasons": finish_reasons,
            "finishCancelled": finish_cancelled,
            "terminalErrorCode": terminal_error_code,
            "finalSessionPresent": True,
            "finalTextNonempty": final_text_nonempty,
            "nonemptyTextDeltaCount": nonempty_text_delta_count,
            "incrementalTextSequenceValid": incremental_text_sequence_valid,
            "toolFrameCount": tool_frames,
            "historyProjection": history_receipt,
            "runningAfterFinish": status_payload.get("running"),
        },
        "persistenceDeltas": deltas,
        "threadReceipt": thread_receipt,
        "gatewayReceipt": gateway_receipt,
        "secretsPrinted": False,
        "privateContentPrinted": False,
    }
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0 if (
        frame_types["finish"] == 1
        and finish_reasons == ["stop"]
        and finish_cancelled == [False]
        and frame_types["message-final"] == 1
        and frame_types["text-start"] == 1
        and frame_types["text-delta"] >= 1
        and frame_types["text-end"] == 1
        and nonempty_text_delta_count >= 1
        and final_text_nonempty
        and incremental_text_sequence_valid
        and frame_types["error"] == 0
        and tool_frames == 0
        and frame_types["story-workspace-output"] == 0
        and final_session_id is not None
        and status_payload.get("running") is False
        and history_receipt["valid"] is True
        and deltas["gatewayRequests"] == 1
        and deltas["settledGatewayRequests"] == 1
        and deltas["tokenLedger"] >= 2
        and gateway_receipt is not None
    ) else 2


def _safe_entrypoint() -> int:
    try:
        return main()
    except Exception as exc:
        error_code = None
        if isinstance(exc, BusinessPreflightError):
            phase = exc.phase
            error_code = exc.error_code
        elif isinstance(exc, ModelContractError):
            phase = "model-contract"
        elif isinstance(exc, SSEProtocolError):
            phase = "claude-agent-sse-contract"
        else:
            phase = "gateway-real-e2e"
        diagnostic = {
            "phase": phase,
            "errorClass": type(exc).__name__,
            "secretsPrinted": False,
            "privateContentPrinted": False,
        }
        if error_code is not None:
            diagnostic["errorCode"] = error_code
        print(json.dumps(diagnostic, sort_keys=True))
        return 3


if __name__ == "__main__":
    raise SystemExit(_safe_entrypoint())
