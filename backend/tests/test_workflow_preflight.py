"""Focused tests for the authoritative Workflow Preflight contract."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
import sqlite3
import unittest
from unittest.mock import Mock

from pydantic import ValidationError

from backend.schema.legacy_main_sqlite import create_tables
from backend.models.workflow_preflight import (
    PreflightCheck,
    PreflightStatus,
    WorkflowPreflight,
)
from backend.services.workflow.preflight_service import (
    PreflightCheckError,
    PreflightService,
    PreflightTokenError,
)


DIGEST = "sha256:" + "a" * 64
OTHER_DIGEST = "sha256:" + "b" * 64
MANIFEST_HASH = "sha256:" + "c" * 64
SUMMARY_HASH = "sha256:" + "d" * 64
TOKEN_SECRET = b"workflow-preflight-test-secret-32-bytes-minimum"


class WorkflowPreflightTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        create_tables(self.db)
        self.now = datetime(2026, 8, 1, 9, 0, tzinfo=UTC)
        self.calls: list[PreflightCheck] = []
        self.fail_at: PreflightCheck | None = None
        self.snapshot_calls = 0
        self.snapshot_payload: dict | None = None
        self.materialization_payload: dict | None = None
        self.service = self._make_service()

    def tearDown(self) -> None:
        self.db.close()

    def _record(self, check: PreflightCheck) -> None:
        self.calls.append(check)
        if self.fail_at is check:
            raise PreflightCheckError("TEST_" + check.value.upper())

    async def _identity(self, deck_id: str, actor: str) -> dict:
        self._record(PreflightCheck.IDENTITY_WORKSPACE_PERMISSION)
        return {"workspace_id": "workspace-1"}

    async def _binding(self, deck_id: str, binding_revision: int) -> dict:
        self._record(PreflightCheck.BINDING_RELEASE)
        return {
            "deck_plugin_id": "voice-decks.story-dramatize",
            "deck_plugin_version": "3.1.0",
            "runtime_plugin_lock_id": "rpl_" + "1" * 32,
            "deck_runtime_profile_id": "drp_" + "2" * 32,
            "deck_runtime_snapshot_contract": "1.0.0",
            "manifest_hash": MANIFEST_HASH,
            "workflow_definition_ref": (
                "deck://voice-decks.story-dramatize/3.1.0/workflow.json"
            ),
            "input_schema_ref": "schema://story-workspace/input/v1",
            "output_schema_ref": "schema://story-workspace/result/v1",
            "required_runtime_plugins": [
                {
                    "claude_code_plugin_id": "ink-dream-tools@voice-decks",
                    "artifact_digest": DIGEST,
                }
            ],
        }

    async def _manifest(self, binding, input_data: dict) -> bool:
        self._record(PreflightCheck.MANIFEST_WORKFLOW_SCHEMA)
        return True

    async def _compatibility(self, binding, identity) -> bool:
        self._record(PreflightCheck.HOST_AGENT_RUNTIME_COMPATIBILITY)
        return True

    async def _capability(self, binding, identity) -> bool:
        self._record(PreflightCheck.CAPABILITY_SOURCE_POLICY)
        return True

    async def _snapshot(self, deck_id: str, profile_id: str, contract: str) -> dict:
        self._record(PreflightCheck.DECK_RUNTIME_SNAPSHOT)
        self.snapshot_calls += 1
        await asyncio.sleep(0)
        return self.snapshot_payload or {
            "deck_runtime_snapshot_id": "drs_" + "3" * 32,
            "sanitized_summary_hash": SUMMARY_HASH,
            "reused": self.snapshot_calls > 1,
        }

    async def _materialization(self, runtime_lock_id: str) -> dict:
        self._record(PreflightCheck.RUNTIME_MATERIALIZATION)
        return self.materialization_payload or {
            "runtime_plugin_lock_id": runtime_lock_id,
            "plugins": [
                {
                    "claude_code_plugin_id": "ink-dream-tools@voice-decks",
                    "declaration_status": "declared",
                    "materialization_status": "materialized",
                    "activation_status": "loadable",
                    "artifact_digest": DIGEST,
                }
            ],
            "load_smoke_passed": True,
        }

    def _make_service(self) -> PreflightService:
        return PreflightService(
            self.db,
            identity_checker=self._identity,
            binding_resolver=self._binding,
            manifest_schema_checker=self._manifest,
            compatibility_checker=self._compatibility,
            capability_policy_checker=self._capability,
            deck_snapshot_owner=self._snapshot,
            runtime_materialization_reader=self._materialization,
            token_secret=TOKEN_SECRET,
            clock=lambda: self.now,
        )

    async def _execute(self, deck_id: str = "deck-1") -> WorkflowPreflight:
        return await self.service.execute_preflight(
            deck_id,
            7,
            {"theme": "memory", "episodes": 3},
            "user-1",
        )

    async def test_eight_steps_are_fixed_and_each_failure_short_circuits(self):
        order = list(PreflightCheck)
        for failed_index, failed_check in enumerate(order[:-1]):
            with self.subTest(failed_check=failed_check):
                self.calls = []
                self.fail_at = failed_check
                result = await self._execute(f"deck-fail-{failed_index}")
                self.assertEqual(result.status, PreflightStatus.FAILED)
                self.assertEqual(result.failed_check, failed_check)
                self.assertEqual(self.calls, order[: failed_index + 1])
                self.assertIsNone(result.preflight_token)

        self.calls = []
        self.fail_at = None
        original_issuer = self.service._issue_preflight_token
        self.service._issue_preflight_token = Mock(
            side_effect=PreflightCheckError("PREFLIGHT_TOKEN_ISSUE_FAILED")
        )
        try:
            token_failure = await self._execute("deck-fail-token")
        finally:
            self.service._issue_preflight_token = original_issuer
        self.assertEqual(token_failure.status, PreflightStatus.FAILED)
        self.assertEqual(token_failure.failed_check, PreflightCheck.TOKEN_ISSUANCE)
        self.assertEqual(self.calls, order[:-1])

    async def test_success_persists_only_sanitized_snapshot_reference_and_hash(self):
        result = await self._execute()
        self.assertEqual(result.status, PreflightStatus.PASSED)
        self.assertTrue(result.preflight_token.startswith("pft_"))
        self.assertEqual(self.calls, list(PreflightCheck)[:-1])

        row = self.db.execute(
            "SELECT * FROM workflow_preflights WHERE workflow_preflight_id = ?",
            (result.workflow_preflight_id,),
        ).fetchone()
        columns = {item[1] for item in self.db.execute("PRAGMA table_info(workflow_preflights)")}
        self.assertEqual(row["deck_runtime_snapshot_id"], result.deck_runtime_snapshot_id)
        self.assertEqual(row["deck_runtime_snapshot_summary_hash"], SUMMARY_HASH)
        self.assertIsNotNone(row["preflight_token_hash"])
        self.assertNotEqual(row["preflight_token_hash"], result.preflight_token)
        self.assertFalse(
            columns
            & {
                "prompt",
                "prompt_template",
                "secret",
                "secret_ref",
                "runtime_config",
            }
        )

    async def test_snapshot_owner_payload_rejects_sensitive_or_extra_configuration(self):
        self.snapshot_payload = {
            "deck_runtime_snapshot_id": "drs_" + "3" * 32,
            "sanitized_summary_hash": SUMMARY_HASH,
            "reused": False,
            "secret": "must-not-cross-owner-boundary",
        }
        result = await self._execute("deck-sensitive")
        self.assertEqual(result.status, PreflightStatus.FAILED)
        self.assertEqual(result.failed_check, PreflightCheck.DECK_RUNTIME_SNAPSHOT)
        stored = " ".join(
            str(value)
            for value in self.db.execute(
                "SELECT * FROM workflow_preflights WHERE workflow_preflight_id = ?",
                (result.workflow_preflight_id,),
            ).fetchone()
            if value is not None
        )
        self.assertNotIn("must-not-cross-owner-boundary", stored)

    async def test_runtime_materialization_checks_all_four_readiness_dimensions(self):
        cases = (
            ({"declaration_status": "disabled"}, "RUNTIME_PLUGIN_NOT_READY"),
            ({"materialization_status": "failed"}, "RUNTIME_PLUGIN_NOT_READY"),
            ({"activation_status": "load_failed"}, "RUNTIME_PLUGIN_NOT_READY"),
            ({"artifact_digest": OTHER_DIGEST}, "DECK_PLUGIN_INTEGRITY_FAILED"),
            ({"load_smoke_passed": False}, "RUNTIME_PLUGIN_LOAD_FAILED"),
            ({"runtime_plugin_lock_id": "rpl_" + "9" * 32}, "CONFIG_VERSION_DRIFT"),
        )
        for index, (updates, expected_code) in enumerate(cases):
            with self.subTest(updates=updates):
                payload = {
                    "runtime_plugin_lock_id": "rpl_" + "1" * 32,
                    "plugins": [
                        {
                            "claude_code_plugin_id": (
                                "ink-dream-tools@voice-decks"
                            ),
                            "declaration_status": "declared",
                            "materialization_status": "materialized",
                            "activation_status": "loadable",
                            "artifact_digest": DIGEST,
                        }
                    ],
                    "load_smoke_passed": True,
                }
                if "load_smoke_passed" in updates:
                    payload["load_smoke_passed"] = updates["load_smoke_passed"]
                elif "runtime_plugin_lock_id" in updates:
                    payload["runtime_plugin_lock_id"] = updates[
                        "runtime_plugin_lock_id"
                    ]
                else:
                    payload["plugins"][0].update(updates)
                self.materialization_payload = payload
                result = await self._execute(f"deck-materialization-{index}")
                self.assertEqual(result.status, PreflightStatus.FAILED)
                self.assertEqual(
                    result.failed_check,
                    PreflightCheck.RUNTIME_MATERIALIZATION,
                )
                self.assertEqual(result.error_code, expected_code)
        self.materialization_payload = None

    async def test_concurrent_identical_preflights_reuse_snapshot_record_and_token(self):
        first, second = await asyncio.gather(self._execute(), self._execute())
        self.assertEqual(first.workflow_preflight_id, second.workflow_preflight_id)
        self.assertEqual(first.deck_runtime_snapshot_id, second.deck_runtime_snapshot_id)
        self.assertEqual(first.preflight_token, second.preflight_token)
        self.assertEqual(self.snapshot_calls, 1)
        count = self.db.execute(
            "SELECT COUNT(*) FROM workflow_preflights"
        ).fetchone()[0]
        self.assertEqual(count, 1)

    async def test_token_binds_revision_input_snapshot_and_lock_then_blocks_replay(self):
        result = await self._execute()
        token = result.preflight_token
        assert token is not None
        valid_kwargs = {
            "binding_revision": 7,
            "input_data": {"theme": "memory", "episodes": 3},
            "deck_runtime_snapshot_id": result.deck_runtime_snapshot_id,
            "runtime_plugin_lock_id": result.runtime_plugin_lock_id,
        }
        mismatch_cases = (
            ("binding_revision", 8, "PREFLIGHT_TOKEN_BINDING_MISMATCH"),
            ("input_data", {"theme": "changed"}, "PREFLIGHT_TOKEN_INPUT_MISMATCH"),
            ("deck_runtime_snapshot_id", "drs_other", "PREFLIGHT_TOKEN_SNAPSHOT_MISMATCH"),
            ("runtime_plugin_lock_id", "rpl_other", "PREFLIGHT_TOKEN_RUNTIME_LOCK_MISMATCH"),
        )
        for key, value, expected_code in mismatch_cases:
            with self.subTest(key=key):
                kwargs = dict(valid_kwargs)
                kwargs[key] = value
                with self.assertRaises(PreflightTokenError) as captured:
                    self.service.consume_preflight_token(token, **kwargs)
                self.assertEqual(captured.exception.code, expected_code)

        consumed = self.service.consume_preflight_token(token, **valid_kwargs)
        self.assertEqual(consumed.status, PreflightStatus.PASSED)
        self.assertIsNone(consumed.preflight_token)
        with self.assertRaises(PreflightTokenError) as captured:
            self.service.consume_preflight_token(token, **valid_kwargs)
        self.assertEqual(captured.exception.code, "PREFLIGHT_TOKEN_REPLAYED")

        replacement = await self._execute()
        self.assertNotEqual(
            replacement.workflow_preflight_id,
            result.workflow_preflight_id,
        )
        self.assertNotEqual(replacement.preflight_token, token)

    async def test_expired_token_marks_preflight_expired(self):
        result = await self._execute()
        token = result.preflight_token
        assert token is not None
        self.now += timedelta(minutes=6)
        with self.assertRaises(PreflightTokenError) as captured:
            self.service.consume_preflight_token(
                token,
                binding_revision=7,
                input_data={"theme": "memory", "episodes": 3},
                deck_runtime_snapshot_id=result.deck_runtime_snapshot_id,
                runtime_plugin_lock_id=result.runtime_plugin_lock_id,
            )
        self.assertEqual(captured.exception.code, "PREFLIGHT_TOKEN_EXPIRED")
        status = self.db.execute(
            """
            SELECT status FROM workflow_preflights
            WHERE workflow_preflight_id = ?
            """,
            (result.workflow_preflight_id,),
        ).fetchone()[0]
        self.assertEqual(status, PreflightStatus.EXPIRED.value)

    async def test_failure_has_no_agent_start_or_pseudo_workflow_run_side_effect(self):
        self.fail_at = PreflightCheck.IDENTITY_WORKSPACE_PERMISSION
        result = await self._execute("deck-denied")
        self.assertEqual(result.status, PreflightStatus.FAILED)
        self.assertEqual(self.calls, [PreflightCheck.IDENTITY_WORKSPACE_PERMISSION])
        run_tables = self.db.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type = 'table' AND name LIKE '%workflow%run%'
            """
        ).fetchall()
        self.assertEqual(run_tables, [])
        self.assertFalse(hasattr(self.service, "agent_service"))

    def test_database_initialization_is_idempotent_and_model_is_strict(self):
        create_tables(self.db)
        columns = {
            item[1] for item in self.db.execute("PRAGMA table_info(workflow_preflights)")
        }
        self.assertIn("deck_runtime_snapshot_id", columns)
        self.assertIn("preflight_token_hash", columns)

        with self.assertRaises(ValidationError):
            WorkflowPreflight(
                workflow_preflight_id="pf_" + "1" * 32,
                deck_id="deck-1",
                binding_revision=1,
                deck_plugin_id="plugin",
                deck_plugin_version="1.0.0",
                runtime_plugin_lock_id="lock",
                deck_runtime_profile_id="profile",
                input_hash="sha256:" + "0" * 64,
                status="failed",
                error_code=None,
                failed_check=None,
                expires_at=self.now + timedelta(minutes=5),
                created_by="actor",
                created_at=self.now,
                unexpected="forbidden",
            )


if __name__ == "__main__":
    unittest.main()
