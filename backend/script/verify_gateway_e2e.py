#!/usr/bin/env python3
"""Run a real local Admin Gateway -> Dream -> Claude Agent smoke test.

The command is intentionally pinned to the named local E2E canonical user. It
never prints access tokens, service keys, provider responses, or assistant text.
"""

from __future__ import annotations

from collections import Counter
import json
import os
from pathlib import Path
import sys

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


TEST_EMAIL = "codex-gateway-e2e@ink-memory.test"
DREAM_BASE_URL = "http://127.0.0.1:8765"


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


def _metrics(platform_user_id: str) -> dict[str, int]:
    connection = database.get_db()
    try:
        cursor = connection.execute(
            """
            SELECT
              (SELECT COUNT(*) FROM gateway_requests WHERE platform_user_id = %s) AS requests,
              (SELECT COUNT(*) FROM gateway_requests WHERE platform_user_id = %s AND settled_at IS NOT NULL) AS settled,
              (SELECT COUNT(*) FROM subscription_token_ledger_entries WHERE platform_user_id = %s) AS token_ledger
            """,
            (platform_user_id, platform_user_id, platform_user_id),
        )
        row = cursor.fetchone()
        return {
            "gatewayRequests": int(row[0]),
            "settledGatewayRequests": int(row[1]),
            "tokenLedger": int(row[2]),
        }
    finally:
        connection.close()


def main() -> int:
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
    model_alias = str(admin_data[0].get("id") or "")

    auth_headers = {"authorization": f"Bearer {dream_token}"}
    dream_health = requests.get(f"{DREAM_BASE_URL}/api/health", timeout=10)
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

    config_response = requests.put(
        f"{DREAM_BASE_URL}/api/system-config",
        headers={**auth_headers, "content-type": "application/json"},
        json={"provider": "gateway", "model": model_alias},
        timeout=20,
    )
    if config_response.status_code != 200:
        print(json.dumps({
            "phase": "dream-model-selection",
            "status": config_response.status_code,
            "errorCode": _safe_error_code(config_response),
        }))
        return 1

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
    with requests.post(
        f"{DREAM_BASE_URL}/api/claude-agent",
        headers={**auth_headers, "content-type": "application/json"},
        json={
            "thread_id": thread_id,
            "message": {
                "id": "gateway-real-e2e-turn",
                "role": "user",
                "parts": [
                    {
                        "type": "text",
                        "text": "Reply with exactly OK. Do not call tools.",
                    }
                ],
            },
            "model": model_alias,
            "resume": False,
            "toolChoice": "auto",
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
        frame_types: Counter[str] = Counter()
        terminal_type = None
        terminal_error_code = None
        for raw_line in stream_response.iter_lines(decode_unicode=True):
            if not raw_line or not raw_line.startswith("data:"):
                continue
            try:
                frame = json.loads(raw_line[5:].strip())
            except json.JSONDecodeError:
                continue
            if not isinstance(frame, dict):
                continue
            frame_type = str(frame.get("type") or "unknown")
            frame_types[frame_type] += 1
            if frame_type in {"finish", "error"}:
                terminal_type = frame_type
                code = frame.get("code") or frame.get("error_code")
                terminal_error_code = str(code) if code else None

    after = _metrics(platform_user_id)
    deltas = {key: after[key] - before[key] for key in before}
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
        },
        "modelSelection": {"status": config_response.status_code},
        "claudeAgent": {
            "threadStatus": thread_response.status_code,
            "streamStatus": stream_response.status_code,
            "contentType": content_type.split(";", 1)[0],
            "frameTypes": dict(sorted(frame_types.items())),
            "terminalType": terminal_type,
            "terminalErrorCode": terminal_error_code,
        },
        "persistenceDeltas": deltas,
        "secretsPrinted": False,
    }
    print(json.dumps(receipt, ensure_ascii=False, sort_keys=True))
    return 0 if (
        terminal_type == "finish"
        and frame_types["error"] == 0
        and deltas["gatewayRequests"] > 0
        and deltas["settledGatewayRequests"] > 0
        and deltas["tokenLedger"] >= 2
    ) else 2


if __name__ == "__main__":
    raise SystemExit(main())
