from __future__ import annotations

import copy
import hashlib
import json
import sqlite3
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.story_workspace.dream_thread_binding import (
    DreamRunBindingResolver,
    DreamThreadBindingConflict,
)


RUN_A = "run_" + "a" * 32
RUN_B = "run_" + "b" * 32
RUN_C = "run_" + "c" * 32


def _sha256_json(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def attempt(
    run_id: str = RUN_A,
    parent: str | None = None,
    *,
    status: str = "queued",
) -> dict:
    goal = "写第一集"
    source_metadata = {
        "kind": "story-workspace-dream-launch",
        "schemaVersion": "story-workspace-dream-launch/v1",
        "visibility": "system-hidden",
        "actorId": "7",
        "workspaceId": "workspace-1",
        "deckId": "deck-1",
        "agentId": "voice-1",
        "goal": goal,
        "requestFingerprint": _sha256_json(
            {"deck_id": "deck-1", "goal": goal, "agent_id": "voice-1"}
        ),
        "threadId": "thread-1",
        "workflowRunId": RUN_A,
    }
    return {
        "workflow_run_id": run_id,
        "retry_of_run_id": parent,
        "status": status,
        "workspace_id": "workspace-1",
        "created_by": "7",
        "source_voice_thread_id": "thread-1",
        "source_message_id": "source-message-1",
        "source_message_time": "2026-08-11T00:00:00+00:00",
        "source_message_thread_id": "thread-1",
        "source_message_role": "user",
        "source_message_metadata": source_metadata,
        "input_hash": _sha256_json({"goal": goal}),
        "workflow_definition_ref": "builtin://ink-dream-story/workflow/v1",
        "deck_plugin_manifest_hash": "sha256:" + "2" * 64,
        "deck_plugin_id": "ink.dream.story-workflow",
        "deck_plugin_version": "1.0.0",
        "deck_plugin_binding_id": "dpb_" + "3" * 32,
        "binding_revision": 3,
        "deck_runtime_snapshot_id": "drs_" + "4" * 32,
        "runtime_plugin_lock_id": "rpl_" + "5" * 32,
        "workspace_owner_id": 7,
        "binding_deck_id": "deck-1",
        "binding_workspace_id": "workspace-1",
        "binding_deck_plugin_id": "ink.dream.story-workflow",
        "binding_deck_plugin_version": "1.0.0",
        "binding_revision_actual": 3,
    }


class _Rows:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return copy.deepcopy(self._rows)


class _DB:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def execute(self, statement, params):
        self.calls.append((statement, params))
        return _Rows(self.rows)


class TestDreamRunBindingResolver(unittest.TestCase):
    thread = {"id": "thread-1", "user_id": 7, "deck_id": "deck-1", "voice_id": "voice-1"}

    def resolve(self, rows):
        return DreamRunBindingResolver(_DB(rows)).resolve(
            actor_id=7,
            thread_id="thread-1",
            owned_thread=self.thread,
        )

    def test_zero_attempts_is_generic_chat(self) -> None:
        self.assertIsNone(self.resolve([]))

    def test_thread_lookup_uses_the_narrow_source_index(self) -> None:
        db = sqlite3.connect(":memory:")
        self.addCleanup(db.close)
        db.execute(
            "CREATE TABLE workflow_runs "
            "(id TEXT PRIMARY KEY, source_voice_thread_id TEXT)"
        )
        db.execute(
            "CREATE INDEX idx_workflow_runs_source_voice_thread "
            "ON workflow_runs (source_voice_thread_id)"
        )
        plan = db.execute(
            "EXPLAIN QUERY PLAN "
            "SELECT id FROM workflow_runs WHERE source_voice_thread_id = ?",
            ("thread-1",),
        ).fetchall()
        self.assertTrue(
            any(
                "USING INDEX idx_workflow_runs_source_voice_thread" in str(row[3])
                for row in plan
            ),
            plan,
        )

    def test_one_attempt_builds_server_context_and_metadata(self) -> None:
        context = self.resolve([attempt()])
        self.assertEqual(context.workflow_run_id, RUN_A)
        self.assertEqual(context.thread_id, "thread-1")
        self.assertEqual(context.deck_id, "deck-1")
        self.assertEqual(context.agent_id, "voice-1")
        self.assertEqual(
            DreamRunBindingResolver.canonical_message_metadata(context, actor_id=7),
            {
                "kind": "story-workspace-dream-agent-user",
                "story_workspace_run_id": RUN_A,
                "thread_id": "thread-1",
                "actor_id": "7",
            },
        )

    def test_linear_retry_chain_selects_unique_unsuperseded_leaf(self) -> None:
        context = self.resolve(
            [
                attempt(RUN_B, RUN_A, status="rejected"),
                attempt(RUN_A, status="failed"),
                attempt(RUN_C, RUN_B),
            ]
        )
        self.assertEqual(context.workflow_run_id, RUN_C)

    def test_active_leaf_statuses_retain_trusted_dream_context(self) -> None:
        for status in (
            "queued",
            "running",
            "output_validating",
            "pending_review",
            "confirmed",
            "confirmed",
        ):
            with self.subTest(status=status):
                self.assertEqual(
                    self.resolve([attempt(status=status)]).workflow_run_id,
                    RUN_A,
                )

    def test_terminal_leaf_statuses_detach_business_runtime_from_chat(self) -> None:
        for status in ("completed", "failed", "cancelled", "rejected"):
            with self.subTest(status=status):
                self.assertIsNone(self.resolve([attempt(status=status)]))

    def test_preflight_and_unknown_leaf_statuses_fail_closed(self) -> None:
        for status in ("preflight", "future_state"):
            with self.subTest(status=status), self.assertRaises(
                DreamThreadBindingConflict
            ) as raised:
                self.resolve([attempt(status=status)])
            self.assertEqual(raised.exception.reason, "invalid_leaf_status")

    def test_retry_parent_must_be_an_unsuccessful_terminal(self) -> None:
        for status in ("queued", "running", "completed"):
            with self.subTest(status=status), self.assertRaises(
                DreamThreadBindingConflict
            ) as raised:
                self.resolve(
                    [attempt(RUN_A, status=status), attempt(RUN_B, RUN_A)]
                )
            self.assertEqual(
                raised.exception.reason,
                "invalid_retry_parent_status",
            )

    def test_new_retry_leaf_restores_business_context_after_terminal(self) -> None:
        context = self.resolve(
            [attempt(RUN_A, status="failed"), attempt(RUN_B, RUN_A)]
        )
        self.assertEqual(context.workflow_run_id, RUN_B)

    def test_multiple_independent_leaves_fail_closed(self) -> None:
        with self.assertRaises(DreamThreadBindingConflict) as raised:
            self.resolve([attempt(RUN_A), attempt(RUN_B)])
        self.assertEqual(raised.exception.reason, "multiple_retry_roots")

    def test_missing_parent_and_cycle_fail_closed(self) -> None:
        with self.subTest("missing"), self.assertRaises(DreamThreadBindingConflict):
            self.resolve([attempt(RUN_B, RUN_A)])
        with self.subTest("cycle"), self.assertRaises(DreamThreadBindingConflict):
            self.resolve([attempt(RUN_A, RUN_B), attempt(RUN_B, RUN_A)])

    def test_frozen_source_mismatch_fails_closed(self) -> None:
        retry = attempt(RUN_B, RUN_A)
        retry["runtime_plugin_lock_id"] = "rpl_" + "9" * 32
        with self.assertRaises(DreamThreadBindingConflict) as raised:
            self.resolve([attempt(RUN_A), retry])
        self.assertEqual(raised.exception.reason, "frozen_source_mismatch")

    def test_missing_source_message_proof_fails_closed(self) -> None:
        for key, value in (
            ("source_message_id", None),
            ("source_message_time", None),
            ("source_message_thread_id", None),
            ("source_message_role", None),
            ("source_message_metadata", None),
        ):
            row = attempt()
            row[key] = value
            with self.subTest(key=key), self.assertRaises(
                DreamThreadBindingConflict
            ) as raised:
                self.resolve([row])
            self.assertEqual(raised.exception.reason, "malformed_attempt")

    def test_source_message_must_be_same_thread_user_and_server_launch(self) -> None:
        mutations = (
            ("source_message_thread_id", "thread-other"),
            ("source_message_role", "assistant"),
        )
        for key, value in mutations:
            row = attempt()
            row[key] = value
            with self.subTest(key=key), self.assertRaises(
                DreamThreadBindingConflict
            ) as raised:
                self.resolve([row])
            self.assertEqual(
                raised.exception.reason,
                "source_message_provenance_mismatch",
            )

    def test_tampered_source_launch_metadata_fails_closed(self) -> None:
        for key, value in (
            ("actorId", "8"),
            ("requestFingerprint", "sha256:" + "9" * 64),
            ("workflowRunId", RUN_B),
            ("visibility", "visible"),
        ):
            row = attempt()
            row["source_message_metadata"][key] = value
            with self.subTest(key=key), self.assertRaises(
                DreamThreadBindingConflict
            ) as raised:
                self.resolve([row])
            self.assertEqual(
                raised.exception.reason,
                "source_message_provenance_mismatch",
            )

    def test_retry_leaf_must_reuse_root_launch_provenance(self) -> None:
        root = attempt(RUN_A)
        retry = attempt(RUN_B, RUN_A)
        retry["source_message_metadata"]["workflowRunId"] = RUN_B
        with self.assertRaises(DreamThreadBindingConflict) as raised:
            self.resolve([root, retry])
        self.assertEqual(raised.exception.reason, "frozen_source_mismatch")

    def test_actor_workspace_thread_and_binding_mismatches_fail_closed(self) -> None:
        mutations = (
            ("created_by", "8"),
            ("workspace_owner_id", 8),
            ("binding_deck_id", "deck-other"),
            ("binding_workspace_id", "workspace-other"),
            ("binding_revision_actual", 4),
        )
        for key, value in mutations:
            row = attempt()
            row[key] = value
            with self.subTest(key=key), self.assertRaises(DreamThreadBindingConflict):
                self.resolve([row])

    def test_browser_cannot_select_a_run(self) -> None:
        # The public resolver signature has no workflow_run_id selector.  A
        # conflict therefore cannot be bypassed by picking one of two roots.
        with self.assertRaises(TypeError):
            DreamRunBindingResolver(_DB([attempt()])).resolve(
                actor_id=7,
                thread_id="thread-1",
                owned_thread=self.thread,
                workflow_run_id=RUN_A,
            )


if __name__ == "__main__":
    unittest.main()
