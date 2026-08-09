from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

import auth
from routers import product
from services.admin_product.errors import ProductBffError
from services.admin_product.identity import CanonicalUserIdentity
from services.admin_product.service import ProductBffService


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
            data["payment"] = "must-not-leak"
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


class ProductBffRouteTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = _FakeProductBff()
        self.app = FastAPI()
        self.app.dependency_overrides[product.get_product_bff_service] = (
            lambda: self.service
        )
        self.app.include_router(product.router)
        self.token = auth.create_access_token(7, "canonical@example.test")
        self.headers = {"authorization": f"Bearer {self.token}"}
        self.environment = patch.dict(
            os.environ,
            {"INK_ADMIN_PRODUCT_ORIGIN": "https://dream.example.test"},
            clear=False,
        )
        self.environment.start()

    def tearDown(self) -> None:
        self.environment.stop()

    def test_router_exposes_only_the_five_documented_bff_operations(self) -> None:
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

        for response in [context, plans, usage, models, preview]:
            self.assertEqual(response.status_code, 200, response.text)
            self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(context.json()["meta"]["requestId"], "req_context")
        self.assertTrue(all(call[1] == "7" for call in self.service.calls))
        plan_call = next(call for call in self.service.calls if call[0] == "plans")
        self.assertEqual((plan_call[2].page, plan_call[2].pageSize), (2, 10))
        usage_call = next(call for call in self.service.calls if call[0] == "usage")
        self.assertEqual((usage_call[2].outcome, usage_call[2].page), ("completed", 3))
        command_call = next(call for call in self.service.calls if call[0] == "commands")
        self.assertEqual(command_call[2].phase, "preview")
        self.assertIsNone(command_call[4])

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


class _Lookup:
    def __init__(self, identity):
        self.identity = identity
        self.subjects = []

    async def find_active(self, subject):
        self.subjects.append(subject)
        return self.identity


class _Gateway:
    def __init__(self, returned_subject="7"):
        self.returned_subject = returned_subject
        self.subjects = []

    async def subscription_context(self, subject, request_id):
        self.subjects.append(subject)
        return {
            "data": {"canonicalUser": {"id": self.returned_subject}},
            "meta": {"requestId": request_id},
        }


class ProductBffSubjectBindingTests(unittest.IsolatedAsyncioTestCase):
    async def test_pg_lookup_identity_is_the_only_subject_sent_to_admin(self) -> None:
        lookup = _Lookup(CanonicalUserIdentity("7"))
        gateway = _Gateway()
        service = ProductBffService(canonical_users=lookup, admin_product=gateway)  # type: ignore[arg-type]
        result = await service.subscription_context("7", "req_1")
        self.assertEqual(result["data"]["canonicalUser"]["id"], "7")
        self.assertEqual(lookup.subjects, ["7"])
        self.assertEqual(gateway.subjects, ["7"])

    async def test_missing_or_mismatched_canonical_identity_fails_closed(self) -> None:
        missing = ProductBffService(
            canonical_users=_Lookup(None),  # type: ignore[arg-type]
            admin_product=_Gateway(),  # type: ignore[arg-type]
        )
        with self.assertRaises(ProductBffError) as missing_error:
            await missing.subscription_context("7", "req_1")
        self.assertEqual(missing_error.exception.status_code, 403)

        mismatched_response = ProductBffService(
            canonical_users=_Lookup(CanonicalUserIdentity("7")),  # type: ignore[arg-type]
            admin_product=_Gateway("8"),  # type: ignore[arg-type]
        )
        with self.assertRaises(ProductBffError) as mismatch_error:
            await mismatched_response.subscription_context("7", "req_1")
        self.assertEqual(mismatch_error.exception.status_code, 503)


if __name__ == "__main__":
    unittest.main()
