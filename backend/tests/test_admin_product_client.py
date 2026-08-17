from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import unittest

import httpx
import jwt

from services.admin_product.client import (
    AdminProductClient,
    _FORBIDDEN_RESPONSE_KEY_FRAGMENTS,
    assert_safe_product_payload,
)
from services.admin_product.config import AdminProductConfig
from services.admin_product.errors import ProductBffError
from services.admin_product.identity import PostgresCanonicalUserRepository
from services.admin_product.models import (
    ExecuteSubscriptionCommand,
    PaymentIntentCreate,
    PlansQuery,
    PreviewSubscriptionCommand,
    UsageQuery,
)
from services.admin_product.token import issue_product_token


def _configuration() -> AdminProductConfig:
    return AdminProductConfig(
        base_url="https://admin.example.test",
        jwt_secret="test-product-secret-that-is-at-least-32-bytes",
        jwt_issuer="ink-dream-test",
        jwt_audience="ink-admin-product-test",
        client_id="dream-bff-test",
        request_origin="https://dream.example.test",
        token_lifetime_seconds=240,
        timeout_seconds=2,
    )


def _meta() -> dict:
    return {"requestId": "req_test"}


def _plan() -> dict:
    return {
        "planCode": "creator",
        "planName": "Creator",
        "eyebrow": "For active stories",
        "note": "A real monthly plan",
        "details": ["More room to create"],
        "description": None,
        "planVersionId": "pv_creator_1",
        "version": 1,
        "versionStatus": "published",
        "billingCycle": "monthly",
        "monthlyAllowanceTokens": 100_000,
        "monthlyPriceMicrousd": 9_000_000,
        "currency": "USD",
        "available": True,
        "unavailableReason": None,
        "entitlements": [
            {
                "gatewayScopes": ["messages:create"],
                "modelAliases": ["dream-balanced"],
                "rpmLimit": 30,
                "dailyTokenLimit": None,
                "storageBytes": 1_024,
            }
        ],
        "eligibility": {
            "eligible": True,
            "reasonCode": None,
            "appliesAt": "2030-01-01T00:00:00.000Z",
        },
        "availableActions": ["create"],
    }


def _context() -> dict:
    return {
        "canonicalUser": {"id": "7"},
        "subscription": {
            "id": "sub_1",
            "status": "active",
            "version": 7,
            "cycleAnchorAt": "2030-01-01T00:00:00.000Z",
            "currentPeriodNumber": 0,
            "currentPeriodStart": "2030-01-01T00:00:00.000Z",
            "currentPeriodEnd": "2030-02-01T00:00:00.000Z",
            "renewalEnabled": True,
            "cancelAtPeriodEnd": False,
            "pendingChange": None,
            "allowedActions": ["upgrade", "downgrade", "pause", "cancel"],
        },
        "planVersion": {
            "planCode": "creator",
            "planName": "Creator",
            "planVersionId": "pv_creator_1",
            "version": 1,
            "billingCycle": "monthly",
            "monthlyAllowanceTokens": 100_000,
            "monthlyPriceMicrousd": 9_000_000,
            "currency": "USD",
        },
        "entitlements": [
            {
                "gatewayScope": "messages:create",
                "modelAliases": ["dream-balanced"],
                "rpmLimit": 30,
                "dailyTokenLimit": None,
                "storageBytes": 1_024,
            }
        ],
        "allowance": {
            "unit": "tokens",
            "granted": 100_000,
            "reserved": 1_000,
            "consumed": 20_000,
            "remaining": 79_000,
            "resetsAt": "2030-02-01T00:00:00.000Z",
        },
        "asOf": "2030-01-01T00:00:00.000Z",
    }


def _usage() -> dict:
    return {
        "period": {
            "start": "2030-01-01T00:00:00.000Z",
            "end": "2030-02-01T00:00:00.000Z",
            "timezone": "UTC",
        },
        "allowance": {
            "unit": "tokens",
            "granted": 100_000,
            "reserved": 1_000,
            "consumed": 20_000,
            "remaining": 79_000,
            "resetsAt": "2030-02-01T00:00:00.000Z",
        },
        "summary": {
            "requestCount": 1,
            "inputTokens": 1_200,
            "outputTokens": 800,
            "cacheReadTokens": 0,
            "cacheWriteTokens": 0,
            "totalTokens": 2_000,
            "unknownUsageCount": 0,
        },
        "projection": {
            "asOf": "2030-01-01T00:00:00.000Z",
            "sampleWindowDays": 7,
            "projectedExhaustionAt": None,
            "projectedTokenShortfall": None,
            "confidence": "insufficientData",
        },
        "items": [
            {
                "gatewayRequestId": "gwr_1",
                "modelAlias": "dream-balanced",
                "gatewayScope": "messages:create",
                "protocol": "anthropic",
                "outcome": "completed",
                "settlementState": "settled",
                "inputTokens": 1_200,
                "outputTokens": 800,
                "cacheReadTokens": 0,
                "cacheWriteTokens": 0,
                "totalTokens": 2_000,
                "allowanceReservedTokens": 2_500,
                "allowanceConsumedTokens": 2_000,
                "allowanceReleasedTokens": 500,
                "occurredAt": "2030-01-01T00:01:00.000Z",
                "errorCategory": None,
            }
        ],
    }


def _catalog() -> dict:
    return {
        "items": [
            {
                "modelAlias": "dream-balanced",
                "displayName": "Balanced",
                "description": None,
                "capabilities": ["text", "stream"],
                "contexts": [],
                "eligibility": {
                    "allowed": True,
                    "reasonCode": None,
                    "subscriptionStatus": "active",
                    "gatewayScopes": ["messages:create"],
                    "rpmLimit": 30,
                    "dailyTokenLimit": None,
                    "storageBytes": 1_024,
                    "monthlyTokenRemaining": 79_000,
                    "monthlyTokenResetAt": "2030-02-01T00:00:00.000Z",
                },
                "limits": {"contextWindow": 200_000, "maxOutputTokens": 8_192},
                "availability": "available",
                "asOf": "2030-01-01T00:00:00.000Z",
            }
        ],
        "asOf": "2030-01-01T00:00:00.000Z",
    }


def _preview() -> dict:
    return {
        "action": "pause",
        "allowed": True,
        "reasonCode": None,
        "previewId": "preview_abcdefghijklmnopqrstuv",
        "digest": "sha256:" + "a" * 43,
        "expiresAt": "2030-01-01T00:05:00.000Z",
        "expectedVersion": 7,
        "current": None,
        "target": None,
        "appliesAt": "2030-01-01T00:00:00.000Z",
        "allowanceImpact": {
            "unit": "tokens",
            "currentPeriodTokens": 100_000,
            "nextPeriodTokens": 100_000,
            "currentPeriodChanges": False,
        },
        "entitlementImpact": {
            "currentModelAliases": ["dream-balanced"],
            "targetModelAliases": ["dream-balanced"],
        },
        "gatewayImpact": {"callableAfterExecute": False},
        "warnings": [],
    }


def _command_result() -> dict:
    return {
        "commandId": "command_abc",
        "outcome": "applied",
        "subscription": {
            "id": "sub_1",
            "status": "paused",
            "version": 8,
            "planVersionId": "pv_creator_1",
            "pendingPlanVersionId": None,
            "currentPeriodStart": "2030-01-01T00:00:00.000Z",
            "currentPeriodEnd": "2030-02-01T00:00:00.000Z",
        },
        "actualImpact": {
            "unit": "tokens",
            "appliesAt": None,
            "grantedTokens": 100_000,
            "reservedTokens": 0,
            "consumedTokens": 2_000,
            "remainingTokens": 98_000,
        },
        "idempotentReplay": False,
    }


def _payment_intent() -> dict:
    return {
        "id": "pay_1234567890abcdef1234567890abcdef",
        "planVersionId": "pv_creator_1",
        "subscriptionId": None,
        "operation": "initial_activation",
        "amountMicrousd": 9_000_000,
        "currency": "USD",
        "status": "requires_action",
        "nextAction": {"type": "test_webhook"},
        "failureCode": None,
        "createdAt": "2030-01-01T00:00:00.000Z",
        "updatedAt": "2030-01-01T00:00:00.000Z",
    }


class AdminProductConfigurationTests(unittest.TestCase):
    def test_token_only_field_firewall_is_exact_and_allows_token_balance(self) -> None:
        self.assertEqual(
            _FORBIDDEN_RESPONSE_KEY_FRAGMENTS,
            (
                "cash",
                "monetary",
                "financial",
                "topup",
                "ledger",
                "effectivefrom",
                "effectiveto",
                "provider",
                "secret",
                "credential",
                "platformuserid",
                "authorization",
                "apikey",
                "keyhash",
                "ciphertext",
            ),
        )
        assert_safe_product_payload(
            {
                "tokenBalance": {"remainingTokens": 100, "unit": "tokens"},
                "payment": {"amountMicrousd": 9_000_000, "currency": "USD"},
            }
        )
        for forbidden in (
            "cashAvailable",
            "monetaryBalance",
            "financialLedgerEntries",
            "providerSecret",
        ):
            with self.assertRaises(ProductBffError):
                assert_safe_product_payload({forbidden: "unsafe"})

    def test_token_has_the_required_short_lived_subject_bound_claims(self) -> None:
        configuration = _configuration()
        token = issue_product_token(
            configuration,
            canonical_user_id="7",
            scope="product:write",
            now=datetime(2030, 1, 1, tzinfo=UTC),
            token_id="jti-test",
        )
        payload = jwt.decode(
            token,
            configuration.jwt_secret,
            algorithms=["HS256"],
            audience=configuration.jwt_audience,
            issuer=configuration.jwt_issuer,
            options={"verify_exp": False, "verify_iat": False},
        )
        self.assertEqual(payload["sub"], "7")
        self.assertEqual(payload["client_id"], "dream-bff-test")
        self.assertEqual(payload["scope"], "product:write")
        self.assertEqual(payload["jti"], "jti-test")
        self.assertEqual(payload["exp"] - payload["iat"], 240)
        self.assertLessEqual(payload["exp"] - payload["iat"], 300)

    def test_configuration_repr_and_errors_do_not_reveal_url_or_secret(self) -> None:
        configuration = _configuration()
        rendered = repr(configuration)
        self.assertNotIn(configuration.base_url, rendered)
        self.assertNotIn(configuration.jwt_secret, rendered)
        with self.assertRaises(ProductBffError) as raised:
            AdminProductConfig.from_env(environ={})
        self.assertNotIn("INK_ADMIN_PRODUCT", str(raised.exception))


class AdminProductClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_published_configuration_incomplete_plan_is_valid(self) -> None:
        unavailable = {
            **_plan(),
            "monthlyAllowanceTokens": None,
            "monthlyPriceMicrousd": None,
            "available": False,
            "unavailableReason": "configuration_incomplete",
            "eligibility": {
                "eligible": False,
                "reasonCode": "PLAN_NOT_AVAILABLE",
                "appliesAt": None,
            },
            "availableActions": [],
        }

        async def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "data": [unavailable],
                    "meta": {**_meta(), "total": 1, "page": 1, "pageSize": 20},
                },
            )

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as http_client:
            client = AdminProductClient(_configuration(), client=http_client)
            result = await client.plans("7", PlansQuery(), "req_test")

        self.assertEqual(result["data"][0]["versionStatus"], "published")
        self.assertEqual(
            result["data"][0]["unavailableReason"], "configuration_incomplete"
        )

    async def test_unavailable_plan_with_commercial_values_is_rejected(self) -> None:
        invalid = {
            **_plan(),
            "available": False,
            "unavailableReason": "configuration_incomplete",
            "availableActions": [],
        }

        async def handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "data": [invalid],
                    "meta": {**_meta(), "total": 1, "page": 1, "pageSize": 20},
                },
            )

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler)
        ) as http_client:
            client = AdminProductClient(_configuration(), client=http_client)
            with self.assertRaises(ProductBffError) as raised:
                await client.plans("7", PlansQuery(), "req_test")

        self.assertEqual(raised.exception.status_code, 503)

    async def test_product_routes_claim_scopes_and_write_idempotency(self) -> None:
        configuration = _configuration()
        observed: list[httpx.Request] = []

        async def handler(request: httpx.Request) -> httpx.Response:
            observed.append(request)
            claims = jwt.decode(
                request.headers["authorization"].removeprefix("Bearer "),
                configuration.jwt_secret,
                algorithms=["HS256"],
                audience=configuration.jwt_audience,
                issuer=configuration.jwt_issuer,
            )
            self.assertEqual(claims["sub"], "7")
            if request.url.path == "/api/product/v1/plans":
                self.assertEqual(claims["scope"], "product:read")
                return httpx.Response(
                    200,
                    json={
                        "data": [_plan()],
                        "meta": {**_meta(), "total": 1, "page": 1, "pageSize": 20},
                    },
                )
            if request.url.path == "/api/product/v1/me/subscription-context":
                return httpx.Response(200, json={"data": _context(), "meta": _meta()})
            if request.url.path == "/api/product/v1/me/usage":
                return httpx.Response(
                    200,
                    json={
                        "data": _usage(),
                        "meta": {**_meta(), "total": 0, "page": 1, "pageSize": 25},
                    },
                )
            if request.url.path == "/api/product/v1/me/model-catalog":
                return httpx.Response(200, json={"data": _catalog(), "meta": _meta()})
            if request.url.path == "/api/product/v1/me/payment-intents":
                self.assertEqual(claims["scope"], "product:write")
                self.assertEqual(request.headers["idempotency-key"], "payment-key-123")
                return httpx.Response(200, json={"data": _payment_intent(), "meta": _meta()})
            if request.url.path.startswith("/api/product/v1/me/payment-intents/"):
                self.assertEqual(claims["scope"], "product:read")
                return httpx.Response(200, json={"data": _payment_intent(), "meta": _meta()})
            self.assertEqual(request.url.path, "/api/product/v1/me/subscription-commands")
            self.assertEqual(request.headers["origin"], "https://dream.example.test")
            self.assertEqual(claims["scope"], "product:write")
            body = json_from_request(request)
            if body["phase"] == "preview":
                self.assertNotIn("idempotency-key", request.headers)
                self.assertNotIn("targetPlanVersionId", body)
                return httpx.Response(200, json={"data": _preview(), "meta": _meta()})
            self.assertEqual(request.headers["idempotency-key"], "command-key-123")
            return httpx.Response(200, json={"data": _command_result(), "meta": _meta()})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
            client = AdminProductClient(configuration, client=http_client)
            await client.plans("7", PlansQuery(), "req_test")
            await client.subscription_context("7", "req_test")
            await client.usage("7", UsageQuery(), "req_test")
            await client.model_catalog("7", "req_test")
            await client.subscription_command(
                "7",
                PreviewSubscriptionCommand(
                    action="pause", phase="preview", expectedVersion=7
                ),
                "req_test",
                None,
            )
            await client.subscription_command(
                "7",
                ExecuteSubscriptionCommand(
                    action="pause",
                    phase="execute",
                    expectedVersion=7,
                    previewId="preview_abcdefghijklmnopqrstuv",
                    digest="sha256:" + "a" * 43,
                    expiresAt="2030-01-01T00:05:00.000Z",
                    reason="User confirmed pause",
                ),
                "req_test",
                "command-key-123",
            )
            await client.create_payment_intent(
                "7",
                PaymentIntentCreate(planVersionId="pv_creator_1"),
                "req_test",
                "payment-key-123",
            )
            await client.payment_intent(
                "7", "pay_1234567890abcdef1234567890abcdef", "req_test"
            )

        self.assertEqual(
            [(request.method, request.url.path) for request in observed],
            [
                ("GET", "/api/product/v1/plans"),
                ("GET", "/api/product/v1/me/subscription-context"),
                ("GET", "/api/product/v1/me/usage"),
                ("GET", "/api/product/v1/me/model-catalog"),
                ("POST", "/api/product/v1/me/subscription-commands"),
                ("POST", "/api/product/v1/me/subscription-commands"),
                ("POST", "/api/product/v1/me/payment-intents"),
                ("GET", "/api/product/v1/me/payment-intents/pay_1234567890abcdef1234567890abcdef"),
            ],
        )
        self.assertEqual(dict(observed[0].url.params), {"page": "1", "pageSize": "20"})

    async def test_forbidden_response_field_is_rejected_without_value_leakage(self) -> None:
        configuration = _configuration()
        forbidden_value = "must-not-leak"

        async def handler(_request: httpx.Request) -> httpx.Response:
            payload = {"data": _context(), "meta": _meta()}
            payload["data"]["cashBalance"] = forbidden_value
            return httpx.Response(200, json=payload)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
            client = AdminProductClient(configuration, client=http_client)
            with self.assertRaises(ProductBffError) as raised:
                await client.subscription_context("7", "req_test")
        self.assertEqual(raised.exception.status_code, 503)
        self.assertNotIn(forbidden_value, str(raised.exception))

    async def test_unsafe_admin_identifier_is_rejected_fail_closed(self) -> None:
        async def handler(_request: httpx.Request) -> httpx.Response:
            catalog = _catalog()
            catalog["items"][0]["modelAlias"] = "unsafe model alias"
            return httpx.Response(200, json={"data": catalog, "meta": _meta()})

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
            client = AdminProductClient(_configuration(), client=http_client)
            with self.assertRaises(ProductBffError) as raised:
                await client.model_catalog("7", "req_test")
        self.assertEqual(raised.exception.status_code, 503)

    async def test_safe_rate_limit_error_is_mapped_and_unknown_fields_fail_closed(self) -> None:
        configuration = _configuration()
        upstream_message = "raw dependency detail must not cross the BFF"

        async def safe_handler(_request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                429,
                json={
                    "error": {
                        "code": "PRODUCT_RATE_LIMITED",
                        "message": upstream_message,
                        "details": {"window": "minute", "current": 30, "limit": 30, "remaining": 0},
                    },
                    "meta": {"requestId": "req_test", "retryAfterSeconds": 2},
                },
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(safe_handler)) as http_client:
            client = AdminProductClient(configuration, client=http_client)
            with self.assertRaises(ProductBffError) as raised:
                await client.subscription_context("7", "req_test")
        self.assertEqual(raised.exception.status_code, 429)
        self.assertEqual(raised.exception.retry_after_seconds, 2)
        self.assertNotIn(upstream_message, raised.exception.message)

    async def test_transport_failure_is_attempted_once_and_sanitized(self) -> None:
        attempts = 0

        async def handler(request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            raise httpx.ConnectError("contains-upstream-url", request=request)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http_client:
            client = AdminProductClient(_configuration(), client=http_client)
            with self.assertRaises(ProductBffError) as raised:
                await client.subscription_context("7", "req_test")
        self.assertEqual(attempts, 1)
        self.assertEqual(raised.exception.status_code, 503)
        self.assertNotIn("upstream", str(raised.exception))


def json_from_request(request: httpx.Request) -> dict:
    import json

    return json.loads(request.content)


class _FakeCursor:
    def __init__(self, row):
        self._row = row

    def fetchone(self):
        return self._row


class _FakeUnitOfWork:
    def __init__(self, row):
        self.row = row
        self.query = ""
        self.parameters = ()

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, query, parameters):
        self.query = query
        self.parameters = parameters
        return _FakeCursor(self.row)


class CanonicalUserRepositoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_repository_uses_postgres_parameter_binding_and_no_sqlite_module(self) -> None:
        unit = _FakeUnitOfWork({"canonical_user_id": "7"})
        repository = PostgresCanonicalUserRepository(
            unit_of_work_factory=lambda: unit  # type: ignore[arg-type]
        )
        identity = await repository.find_active("7")
        self.assertEqual(identity.canonical_user_id, "7")  # type: ignore[union-attr]
        self.assertIn("FROM users", unit.query)
        self.assertIn("%s::bigint", unit.query)
        self.assertNotIn("?", unit.query)
        self.assertEqual(unit.parameters, ("7",))
        source = (
            Path(__file__).resolve().parents[1]
            / "services"
            / "admin_product"
            / "identity.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("import database", source)
        self.assertNotIn("sqlite3", source)
        self.assertNotIn("database.get_db", source)


if __name__ == "__main__":
    unittest.main()
