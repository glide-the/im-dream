"""Product BFF route and Admin-authenticated OAuth actor contracts.

[Sync] 2026-09-16: forward an Admin OAuth actor DTO without Dream token signing or user-id request fields.
"""

from __future__ import annotations

import os
from pathlib import Path
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers import product
from services.admin_data.errors import AdminDataError
from services.admin_data.request_auth import AdminRequestActor
from services.admin_product.errors import ProductBffError
from services.admin_product.service import ProductBffService, ProductSessionActor


OAUTH_ACCESS_TOKEN = "valid_admin_oauth_" + "x" * 43


class _AuthOwner:
    def authenticate(self, access_token, request_id, *, required_scopes):
        if access_token != OAUTH_ACCESS_TOKEN:
            raise AdminDataError("INVALID_ACCESS_TOKEN", 401, request_id)
        if required_scopes not in {
            frozenset({"product:read"}),
            frozenset({"product:write"}),
        }:
            raise AssertionError(required_scopes)
        return AdminRequestActor(
            subject="better-auth-user-7",
            canonical_user_id="7",
            client_id="dream-browser",
            scopes=frozenset({"product:read", "product:write"}),
            issued_at=1,
            expires_at=4_102_444_800,
            access_token=access_token,
        )


class _FakeProductBff:
    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.error: ProductBffError | None = None
        self.forbidden_response = False

    def _result(self, kind: str, request_id: str):
        if self.error is not None:
            raise self.error
        data = {"kind": kind}
        if self.forbidden_response:
            data["providerSecret"] = "must-not-leak"
        return {"data": data, "meta": {"requestId": request_id}}

    async def plans(self, subject, query, request_id):
        self.calls.append(("plans", subject, query, request_id))
        return self._result("plans", request_id)

    async def subscription_context(self, subject, request_id):
        self.calls.append(("context", subject, request_id))
        return self._result("context", request_id)

    async def usage(self, subject, query, request_id):
        self.calls.append(("usage", subject, query, request_id))
        return self._result("usage", request_id)

    async def model_catalog(self, subject, request_id):
        self.calls.append(("models", subject, request_id))
        return self._result("models", request_id)

    async def subscription_command(
        self, subject, command, request_id, idempotency_key
    ):
        self.calls.append(
            ("commands", subject, command, request_id, idempotency_key)
        )
        return self._result(command.phase, request_id)

    async def create_payment_intent(
        self, subject, payment, request_id, idempotency_key
    ):
        self.calls.append(
            ("create_payment", subject, payment, request_id, idempotency_key)
        )
        return self._result("create_payment", request_id)

    async def payment_intent(self, subject, payment_intent_id, request_id):
        self.calls.append(("payment", subject, payment_intent_id, request_id))
        return self._result("payment", request_id)


class ProductBffRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = _FakeProductBff()
        self.app = FastAPI()
        self.app.dependency_overrides[product.get_product_bff_service] = (
            lambda: self.service
        )
        self.app.state.admin_request_auth = _AuthOwner()
        self.app.include_router(product.router)
        self.headers = {"authorization": "Bearer " + OAUTH_ACCESS_TOKEN}
        self.environment = patch.dict(
            os.environ,
            {"INK_ADMIN_PRODUCT_ORIGIN": "https://dream.example.test"},
            clear=False,
        )
        self.environment.start()

    def tearDown(self) -> None:
        self.environment.stop()

    def test_router_exposes_the_subscription_payment_and_usage_operations(self) -> None:
        operations = {
            (method, route.path)
            for route in product.router.routes
            for method in (route.methods or set())
        }
        self.assertEqual(
            operations,
            {
                ("GET", "/api/story-workspace/subscription/context"),
                ("GET", "/api/story-workspace/subscription/plans"),
                ("POST", "/api/story-workspace/subscription/commands"),
                ("GET", "/api/story-workspace/usage"),
                ("GET", "/api/story-workspace/models"),
                ("POST", "/api/story-workspace/subscription/payment-intents"),
                ("GET", "/api/story-workspace/subscription/payment-intents/{payment_intent_id}"),
            },
        )

    def test_five_routes_bind_session_subject_and_forward_strict_contracts(self) -> None:
        with TestClient(self.app) as client:
            context = client.get(
                "/api/story-workspace/subscription/context",
                headers={**self.headers, "x-request-id": "req_context"},
            )
            plans = client.get(
                "/api/story-workspace/subscription/plans?page=2&pageSize=10",
                headers=self.headers,
            )
            usage = client.get(
                "/api/story-workspace/usage?outcome=completed&page=3&pageSize=5",
                headers=self.headers,
            )
            models = client.get("/api/story-workspace/models", headers=self.headers)
            preview = client.post(
                "/api/story-workspace/subscription/commands",
                headers={
                    **self.headers,
                    "origin": "https://dream.example.test",
                    "content-type": "application/json",
                },
                json={"action": "pause", "phase": "preview", "expectedVersion": 7},
            )
            create_payment = client.post(
                "/api/story-workspace/subscription/payment-intents",
                headers={
                    **self.headers,
                    "origin": "https://dream.example.test",
                    "content-type": "application/json",
                    "idempotency-key": "payment-key-123",
                },
                json={"planVersionId": "pv_creator_1"},
            )
            payment = client.get(
                "/api/story-workspace/subscription/payment-intents/pay_1234567890abcdef1234567890abcdef",
                headers=self.headers,
            )

        for response in [context, plans, usage, models, preview, create_payment, payment]:
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(context.json()["meta"]["requestId"], "req_context")
        self.assertTrue(
            all(
                isinstance(call[1], ProductSessionActor)
                and call[1].canonical_user_id == "7"
                and call[1].access_token == OAUTH_ACCESS_TOKEN
                for call in self.service.calls
            )
        )
        plan_call = next(call for call in self.service.calls if call[0] == "plans")
        self.assertEqual((plan_call[2].page, plan_call[2].pageSize), (2, 10))
        usage_call = next(call for call in self.service.calls if call[0] == "usage")
        self.assertEqual((usage_call[2].outcome, usage_call[2].page), ("completed", 3))
        command_call = next(call for call in self.service.calls if call[0] == "commands")
        self.assertEqual(command_call[2].phase, "preview")
        self.assertIsNone(command_call[4])
        payment_call = next(call for call in self.service.calls if call[0] == "create_payment")
        self.assertEqual(payment_call[2].planVersionId, "pv_creator_1")
        self.assertEqual(payment_call[4], "payment-key-123")

    def test_execute_requires_and_forwards_idempotency_key(self) -> None:
        body = {
            "action": "pause",
            "phase": "execute",
            "expectedVersion": 7,
            "previewId": "preview_abcdefghijklmnopqrstuv",
            "digest": "sha256:" + "a" * 43,
            "expiresAt": "2030-01-01T00:05:00.000Z",
            "reason": "  User confirmed pause  ",
        }
        headers = {
            **self.headers,
            "origin": "https://dream.example.test",
            "content-type": "application/json",
        }
        with TestClient(self.app) as client:
            missing = client.post(
                "/api/story-workspace/subscription/commands",
                headers=headers,
                json=body,
            )
            executed = client.post(
                "/api/story-workspace/subscription/commands",
                headers={**headers, "idempotency-key": "command-key-123"},
                json=body,
            )
            spaced_key = client.post(
                "/api/story-workspace/subscription/commands",
                headers={**headers, "idempotency-key": " command-key-123 "},
                json=body,
            )
        self.assertEqual(missing.status_code, 400)
        self.assertEqual(
            missing.json()["error"]["code"], "PRODUCT_IDEMPOTENCY_KEY_REQUIRED"
        )
        self.assertEqual(executed.status_code, 200, executed.text)
        self.assertEqual(spaced_key.status_code, 400)
        command_call = next(call for call in self.service.calls if call[0] == "commands")
        self.assertEqual(command_call[2].reason, "User confirmed pause")
        self.assertEqual(command_call[4], "command-key-123")

    def test_preview_rejects_idempotency_and_extra_body_fields(self) -> None:
        headers = {
            **self.headers,
            "origin": "https://dream.example.test",
            "content-type": "application/json",
        }
        with TestClient(self.app) as client:
            key_on_preview = client.post(
                "/api/story-workspace/subscription/commands",
                headers={**headers, "idempotency-key": "command-key-123"},
                json={"action": "pause", "phase": "preview", "expectedVersion": 7},
            )
            extra = client.post(
                "/api/story-workspace/subscription/commands",
                headers=headers,
                json={
                    "action": "pause",
                    "phase": "preview",
                    "expectedVersion": 7,
                    "userId": "8",
                },
            )
            duplicate = client.post(
                "/api/story-workspace/subscription/commands",
                headers=headers,
                content=(
                    '{"action":"pause","action":"resume",'
                    '"phase":"preview","expectedVersion":7}'
                ),
            )
        self.assertEqual(key_on_preview.status_code, 400)
        self.assertEqual(
            key_on_preview.json()["error"]["code"],
            "PRODUCT_IDEMPOTENCY_KEY_NOT_ALLOWED",
        )
        self.assertEqual(extra.status_code, 400)
        self.assertEqual(extra.json()["error"]["code"], "PRODUCT_INPUT_INVALID")
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(duplicate.json()["error"]["code"], "PRODUCT_JSON_INVALID")

    def test_post_origin_is_required_and_fail_closed(self) -> None:
        body = {"action": "pause", "phase": "preview", "expectedVersion": 7}
        with TestClient(self.app) as client:
            missing = client.post(
                "/api/story-workspace/subscription/commands",
                headers={**self.headers, "content-type": "application/json"},
                json=body,
            )
            denied = client.post(
                "/api/story-workspace/subscription/commands",
                headers={
                    **self.headers,
                    "content-type": "application/json",
                    "origin": "https://attacker.example.test",
                },
                json=body,
            )
        self.assertEqual(missing.status_code, 403)
        self.assertEqual(missing.json()["error"]["code"], "PRODUCT_ORIGIN_REQUIRED")
        self.assertEqual(denied.status_code, 403)
        self.assertEqual(denied.json()["error"]["code"], "PRODUCT_ORIGIN_DENIED")

    def test_auth_identity_override_and_unknown_query_are_rejected(self) -> None:
        with TestClient(self.app) as client:
            anonymous = client.get("/api/story-workspace/models")
            override = client.get(
                "/api/story-workspace/models",
                headers={**self.headers, "x-canonical-user-id": "8"},
            )
            unknown = client.get(
                "/api/story-workspace/subscription/plans?userId=8",
                headers=self.headers,
            )
            repeated = client.get(
                "/api/story-workspace/subscription/plans?page=1&page=2",
                headers=self.headers,
            )
            context_unknown = client.get(
                "/api/story-workspace/subscription/context?unknown=1",
                headers=self.headers,
            )
            context_repeated = client.get(
                "/api/story-workspace/subscription/context?unknown=1&unknown=2",
                headers=self.headers,
            )
            models_unknown = client.get(
                "/api/story-workspace/models?unknown=1",
                headers=self.headers,
            )
        self.assertEqual(anonymous.status_code, 401)
        self.assertEqual(anonymous.json()["error"]["code"], "PRODUCT_AUTH_REQUIRED")
        self.assertEqual(override.status_code, 400)
        self.assertEqual(
            override.json()["error"]["code"], "PRODUCT_USER_OVERRIDE_DENIED"
        )
        self.assertEqual(unknown.status_code, 400)
        self.assertEqual(repeated.status_code, 400)
        self.assertEqual(context_unknown.status_code, 400)
        self.assertEqual(context_repeated.status_code, 400)
        self.assertEqual(models_unknown.status_code, 400)
        self.assertFalse(
            any(call[0] in {"context", "models"} for call in self.service.calls)
        )

    def test_command_media_type_body_size_and_machine_whitespace_are_strict(self) -> None:
        preview = '{"action":"pause","phase":"preview","expectedVersion":7}'
        headers = {
            **self.headers,
            "origin": "https://dream.example.test",
        }
        with TestClient(self.app) as client:
            wrong_media = client.post(
                "/api/story-workspace/subscription/commands",
                headers={**headers, "content-type": "text/plain"},
                content=preview,
            )
            oversized = client.post(
                "/api/story-workspace/subscription/commands",
                headers={
                    **headers,
                    "content-type": "application/json",
                    "content-length": "16385",
                },
                content=preview,
            )
            spaced_target = client.post(
                "/api/story-workspace/subscription/commands",
                headers={**headers, "content-type": "application/json"},
                json={
                    "action": "create",
                    "phase": "preview",
                    "targetPlanVersionId": " planv_target ",
                    "expectedVersion": None,
                },
            )
            spaced_query = client.get(
                "/api/story-workspace/usage?modelAlias=%20dream-balanced%20",
                headers=self.headers,
            )
        self.assertEqual(wrong_media.status_code, 415)
        self.assertEqual(wrong_media.json()["error"]["code"], "PRODUCT_JSON_REQUIRED")
        self.assertEqual(oversized.status_code, 413)
        self.assertEqual(oversized.json()["error"]["code"], "PRODUCT_BODY_TOO_LARGE")
        self.assertEqual(spaced_target.status_code, 400)
        self.assertEqual(spaced_query.status_code, 400)

    def test_stable_error_statuses_are_preserved_and_forbidden_output_is_blocked(self) -> None:
        with TestClient(self.app) as client:
            for status in [401, 402, 403, 404, 409, 429, 502, 503]:
                self.service.error = ProductBffError(
                    code=f"TEST_STATUS_{status}",
                    message="Safe error.",
                    status_code=status,
                    retry_after_seconds=2 if status == 429 else None,
                )
                response = client.get(
                    "/api/story-workspace/models", headers=self.headers
                )
                self.assertEqual(response.status_code, status, response.text)
                self.assertEqual(response.json()["error"]["code"], f"TEST_STATUS_{status}")
            self.service.error = None
            self.service.forbidden_response = True
            forbidden = client.get(
                "/api/story-workspace/models", headers=self.headers
            )
        self.assertEqual(forbidden.status_code, 503)
        self.assertNotIn("must-not-leak", forbidden.text)


class _Gateway:
    def __init__(self, returned_subject="7"):
        self.returned_subject = returned_subject
        self.access_tokens = []

    async def subscription_context(self, access_token, request_id):
        self.access_tokens.append(access_token)
        return {
            "data": {"canonicalUser": {"id": self.returned_subject}},
            "meta": {"requestId": request_id},
        }


class ProductBffSubjectBindingTests(unittest.IsolatedAsyncioTestCase):
    @staticmethod
    def actor(
        canonical_user_id: str = "7",
        scopes: frozenset[str] = frozenset({"product:read", "product:write"}),
    ) -> ProductSessionActor:
        return ProductSessionActor(canonical_user_id, scopes, OAUTH_ACCESS_TOKEN)

    async def test_authenticated_actor_forwards_only_the_oauth_bearer_to_admin(self) -> None:
        gateway = _Gateway()
        service = ProductBffService(admin_product=gateway)  # type: ignore[arg-type]
        result = await service.subscription_context(self.actor(), "req_1")
        self.assertEqual(result["data"]["canonicalUser"]["id"], "7")
        self.assertEqual(gateway.access_tokens, [OAUTH_ACCESS_TOKEN])

    async def test_invalid_scope_or_mismatched_canonical_subject_fails_closed(self) -> None:
        service = ProductBffService(admin_product=_Gateway())  # type: ignore[arg-type]
        for invalid in ("", "0", "-1", "user-7", str(9_223_372_036_854_775_808)):
            with self.assertRaises(ProductBffError) as invalid_error:
                await service.subscription_context(self.actor(invalid), "req_1")
            self.assertEqual(invalid_error.exception.status_code, 401)

        with self.assertRaises(ProductBffError) as scope_error:
            await service.subscription_context(
                self.actor(scopes=frozenset({"product:write"})), "req_1"
            )
        self.assertEqual(scope_error.exception.status_code, 401)

        mismatched_response = ProductBffService(
            admin_product=_Gateway("8"),  # type: ignore[arg-type]
        )
        with self.assertRaises(ProductBffError) as mismatch_error:
            await mismatched_response.subscription_context(self.actor(), "req_1")
        self.assertEqual(mismatch_error.exception.status_code, 503)

    def test_product_composition_contains_no_database_access(self) -> None:
        root = Path(__file__).resolve().parents[1] / "services" / "admin_product"
        sources = "\n".join(
            (root / name).read_text(encoding="utf-8")
            for name in ("__init__.py", "runtime.py", "service.py")
        )
        forbidden = (
            "PostgresPool",
            "PostgresCanonicalUserRepository",
            "persistence.postgres",
            "persistence.unit_of_work",
            "DATABASE_URL",
            "SELECT ",
        )
        self.assertFalse([value for value in forbidden if value in sources])


if __name__ == "__main__":
    unittest.main()
