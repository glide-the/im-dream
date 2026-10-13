# [Input] Reflection section authority DTOs, production Admin worker consumer, and Admin HTTP contracts.
# [Output] Provider-free renewal evidence through ReflectionAuthorityKeeper, AdminReflectionsWorkerData, and typed HTTP DTOs.
# [Pos] Technical harness only; no normal Admin, PostgreSQL, Gateway, browser, or model is used.
# [Sync] 2026-10-13: R13 uses the actual background worker/client path to diagnose section authority renewal expiry.

from __future__ import annotations

from datetime import datetime, timezone
import json
import unittest

import httpx

from services.admin_data.client import AdminDataClient
from services.admin_data.config import AdminDataConfig
from services.admin_data.reflection_section_persistence import ReflectionAuthorityKeeper
from services.admin_data.reflection_task_data import (
    AdminReflectionsWorkerData,
    FROZEN_REFLECTION_TASK_CONTRACTS,
    FROZEN_REFLECTION_TASK_OPERATION_CAPABILITIES,
    FROZEN_REFLECTION_TASK_SCHEMA_REQUIREMENTS,
)
from services.admin_data.reflection_task_models import ReflectionAuthorityDTO
from services.admin_data.delegation_keeper import RuntimeRenewalSettings


TASK_ID = "123e4567-e89b-12d3-a456-426614174000"
THREAD_ID = "123e4567-e89b-12d3-a456-426614174001"
TOKEN = "rta_" + "a" * 43


class _Clock:
    def __init__(self, value: datetime) -> None:
        self.value = value

    def __call__(self) -> datetime:
        return self.value


def _catalog_payload() -> dict:
    return {
        "version": "1",
        "auth": {
            "issuer": "https://admin.example/api/auth",
            "jwks_uri": "https://admin.example/api/auth/jwks",
            "algorithm": "ES256",
            "resource": "dream",
            "clients": {"browser": "browser", "device": "device"},
            "scopes": ["dream:read", "dream:write"],
            "delegations": [],
        },
        "schema_capabilities": [
            item.model_dump(mode="json")
            for item in FROZEN_REFLECTION_TASK_SCHEMA_REQUIREMENTS
        ],
        "operations": [
            item.model_dump(mode="json")
            for item in FROZEN_REFLECTION_TASK_OPERATION_CAPABILITIES
        ],
    }


def _authority(*, expires_at: str, maximum_expires_at: str) -> ReflectionAuthorityDTO:
    return ReflectionAuthorityDTO(
        token=TOKEN,
        purpose="reflections-worker",
        task_id=TASK_ID,
        section="echoes",
        thread_id=THREAD_ID,
        scopes=("dream:read", "dream:write"),
        expires_at=expires_at,
        maximum_expires_at=maximum_expires_at,
    )


class ReflectionAuthorityKeeperHttpTest(unittest.TestCase):
    def test_tick_renews_through_real_worker_and_admin_client_contract(self):
        now = datetime(2026, 10, 13, 0, 0, tzinfo=timezone.utc)
        clock = _Clock(now)
        calls: list[tuple[str, str, dict]] = []
        renewed = {
            "purpose": "reflections-worker",
            "task_id": TASK_ID,
            "section": "echoes",
            "thread_id": THREAD_ID,
            "scopes": ["dream:read", "dream:write"],
            "expires_at": "2026-10-13T00:08:00Z",
            "maximum_expires_at": "2026-10-13T01:00:00Z",
        }

        def handler(request: httpx.Request) -> httpx.Response:
            request_id = request.headers["x-request-id"]
            if request.url.path.endswith("/capabilities"):
                return httpx.Response(
                    200,
                    json={"request_id": request_id, "data": _catalog_payload()},
                )
            self.assertEqual(
                request.url.path,
                "/api/internal/dream/v1/operations/reflection-section.authority-renew",
            )
            self.assertEqual(request.headers["authorization"], "Bearer fixture.service.token")
            body = json.loads(request.content)
            calls.append((request.method, request_id, body))
            self.assertEqual(
                body,
                {
                    "request_id": request_id,
                    "input": {"task_id": TASK_ID, "section": "echoes"},
                },
            )
            return httpx.Response(
                200,
                json={"request_id": request_id, "data": renewed},
            )

        config = AdminDataConfig(
            base_url="https://admin.example",
            issuer="https://admin.example/api/auth",
            resource="dream",
            service_secret="s" * 32,
            service_client_id="dream",
        )
        http = httpx.Client(transport=httpx.MockTransport(handler))
        client = AdminDataClient(
            config,
            client=http,
            operations=FROZEN_REFLECTION_TASK_CONTRACTS.operations,
            service_token_provider=lambda: "fixture.service.token",
        )
        worker = AdminReflectionsWorkerData(client, FROZEN_REFLECTION_TASK_CONTRACTS)
        keeper = ReflectionAuthorityKeeper(
            _authority(
                expires_at="2026-10-13T00:05:00Z",
                maximum_expires_at="2026-10-13T01:00:00Z",
            ),
            worker,
            settings=RuntimeRenewalSettings(advance_fraction=0.5, check_interval_seconds=1),
            clock=clock,
            request_id_factory=lambda: "renew-request-1",
        )

        clock.value = datetime(2026, 10, 13, 0, 0, 1, tzinfo=timezone.utc)
        keeper.tick()
        self.assertEqual(calls, [])

        clock.value = datetime(2026, 10, 13, 0, 3, tzinfo=timezone.utc)
        keeper.tick()
        self.assertEqual(len(calls), 1)
        self.assertEqual(keeper._expires_at.isoformat(), "2026-10-13T00:08:00+00:00")
        self.assertEqual(keeper._maximum_expires_at.isoformat(), "2026-10-13T01:00:00+00:00")
        self.assertEqual(keeper.current_token(), TOKEN)
        http.close()


if __name__ == "__main__":
    unittest.main()
