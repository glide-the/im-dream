# [Input] Canonical registration DB fixtures and retired public email/Google paths.
# [Output] Preserve transactional provisioning regression checks and refuse Dream local authority.
# [Pos] Registration migration contracts; Admin owns actual registration and default provisioning.
# [Sync] 2026-09-14: public email/Google tests now assert explicit retirement, not local signing.

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock

from fastapi import FastAPI
from fastapi.testclient import TestClient


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from routers import auth as auth_router
from routers import oauth as oauth_router


class _Diagnostic:
    def __init__(self, constraint_name: str) -> None:
        self.constraint_name = constraint_name


class _RegistrationIntegrityError(Exception):
    def __init__(self, constraint_name: str) -> None:
        self.diag = _Diagnostic(constraint_name)


class _FailingRegistrationConnection:
    def __init__(self, constraint_name: str) -> None:
        self.error = _RegistrationIntegrityError(constraint_name)
        self.rollbacks = 0
        self.closes = 0

    def execute(self, _query: str, _parameters: tuple[object, ...]):
        raise self.error

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.closes += 1


class _Result:
    def __init__(self, row: dict[str, object] | None) -> None:
        self.row = row

    def fetchone(self):
        return self.row


class _IncompleteRegistrationConnection:
    def __init__(self) -> None:
        self.executions = 0
        self.commits = 0
        self.rollbacks = 0
        self.closes = 0

    def execute(self, _query: str, _parameters: tuple[object, ...]):
        self.executions += 1
        if self.executions == 1:
            return _Result({"id": 42})
        return _Result(None)

    def commit(self) -> None:
        self.commits += 1

    def rollback(self) -> None:
        self.rollbacks += 1

    def close(self) -> None:
        self.closes += 1


class TestRegistrationProvisioningBoundary(unittest.TestCase):
    def setUp(self) -> None:
        app = FastAPI()
        app.include_router(auth_router.router)
        self.client = TestClient(app)

    def tearDown(self) -> None:
        self.client.close()

    def _create_user_with_integrity_failure(self, constraint_name: str) -> None:
        connection = _FailingRegistrationConnection(constraint_name)
        try:
            with (
                mock.patch.object(
                    auth_router.database,
                    "get_db",
                    return_value=connection,
                ),
                mock.patch.object(
                    auth_router.database,
                    "PostgresIntegrityError",
                    _RegistrationIntegrityError,
                ),
            ):
                auth_router.database.create_user("user@example.test", "hash")
            self.fail("create_user should have raised")
        finally:
            self.assertEqual(connection.rollbacks, 1)
            self.assertEqual(connection.closes, 1)

    def test_duplicate_email_remains_a_client_conflict(self) -> None:
        with self.assertRaisesRegex(ValueError, "Email already exists"):
            self._create_user_with_integrity_failure("users_email_uidx")

    def test_default_free_integrity_failure_is_not_reported_as_duplicate_email(self) -> None:
        with self.assertRaises(auth_router.database.UserRegistrationUnavailable):
            self._create_user_with_integrity_failure(
                "default_free_projection_ready_check"
            )

    def test_missing_default_free_postcondition_rolls_back_canonical_user(self) -> None:
        connection = _IncompleteRegistrationConnection()
        with (
            mock.patch.object(
                auth_router.database,
                "get_db",
                return_value=connection,
            ),
            self.assertRaises(auth_router.database.UserRegistrationUnavailable),
        ):
            auth_router.database.create_user("user@example.test", "hash")

        self.assertEqual(connection.executions, 2)
        self.assertEqual(connection.commits, 0)
        self.assertEqual(connection.rollbacks, 1)
        self.assertEqual(connection.closes, 1)

    def test_email_registration_is_retired_without_creating_a_user(self) -> None:
        with (
            mock.patch.dict(os.environ, {"INK_ADMIN_DREAM_BASE_URL": "https://admin.example", "INK_ADMIN_AUTH_ISSUER": "https://admin.example/api/auth", "INK_DREAM_API_RESOURCE": "https://dream.example/api"}),
            mock.patch.object(auth_router.database, "create_user", side_effect=AssertionError("Dream registration must not write")),
        ):
            response = self.client.post("/api/register", json={"email": "new-user@example.test", "password": "secret123", "display_name": "New User"})
        self.assertEqual(response.status_code, 410)
        self.assertEqual(response.json()["error"]["code"], "DREAM_AUTHENTICATION_RETIRED")

    def test_google_signup_is_retired_without_resolving_or_linking_accounts(self) -> None:
        app = FastAPI(); app.include_router(oauth_router.router)
        with (
            mock.patch.dict(os.environ, {"INK_ADMIN_DREAM_BASE_URL": "https://admin.example", "INK_ADMIN_AUTH_ISSUER": "https://admin.example/api/auth", "INK_DREAM_API_RESOURCE": "https://dream.example/api"}),
            mock.patch.object(auth_router.database, "create_user", side_effect=AssertionError("Dream Google signup must not write")),
            TestClient(app) as client,
        ):
            response = client.get("/oauth/google/callback?code=synthetic-google-code&state=synthetic-state")
        self.assertEqual(response.status_code, 410)
        self.assertNotIn("synthetic-google-code", response.text)


if __name__ == "__main__":
    unittest.main()
