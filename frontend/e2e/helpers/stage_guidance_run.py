#!/usr/bin/env python3
"""Stage a workflow run for dream-surface e2e (Task 6).

The real run-creation path requires a full preflight/token ceremony and an
executing worker; for end-to-end acceptance of the *guidance* and *execution
page* contracts we stage one run row directly (with valid FK parents) and let
every subsequent hop — run read, guidance endpoint, chat_message audit,
frontend execution page — go through the real product code.

Printed to stdout: one JSON object {run_id, workspace_id, user_id}.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime, timedelta
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import uuid

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))

from services.story_workspace.agent_integration import (  # noqa: E402
    get_or_create_default_workspace,
)

BUILTIN_DECK_PLUGIN_ID = "ink.dream.story-workflow"
BUILTIN_DECK_PLUGIN_VERSION = "1.0.0"
BUILTIN_LOCK_ID = "rpl_" + uuid.uuid5(
    uuid.NAMESPACE_URL, f"{BUILTIN_DECK_PLUGIN_ID}@{BUILTIN_DECK_PLUGIN_VERSION}"
).hex


def _digest(seed: str) -> str:
    """Full sha256:… digest matching the WorkflowRun SHA256_PATTERN."""
    return "sha256:" + hashlib.sha256(seed.encode("utf-8")).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, required=True)
    parser.add_argument("--user-email", required=True)
    parser.add_argument("--thread-id", required=True)
    parser.add_argument("--deck-id", required=True)
    parser.add_argument("--status", default="confirmed")
    parser.add_argument("--seed", required=True, help="uniqueness seed for ids")
    args = parser.parse_args()

    db = sqlite3.connect(str(args.db))
    db.row_factory = sqlite3.Row
    try:
        db.execute("PRAGMA foreign_keys=ON")
        user = db.execute(
            "SELECT id FROM users WHERE email = ?", (args.user_email,)
        ).fetchone()
        if user is None:
            raise SystemExit(f"user not found: {args.user_email}")
        user_id = int(user["id"])
        workspace_id = get_or_create_default_workspace(db, user_id)

        release = db.execute(
            """
            SELECT manifest_hash, workflow_definition_ref FROM deck_plugin_releases
            WHERE deck_plugin_id = ? AND deck_plugin_version = ?
            """,
            (BUILTIN_DECK_PLUGIN_ID, BUILTIN_DECK_PLUGIN_VERSION),
        ).fetchone()
        if release is None:
            raise SystemExit("built-in deck plugin release missing; seed first")

        binding_id = "dpb_" + hashlib.sha256(f"dpb:{args.seed}".encode("utf-8")).hexdigest()[:32]
        db.execute(
            """
            INSERT OR IGNORE INTO deck_plugin_bindings (
                deck_plugin_binding_id, deck_id, workspace_id, creator_id,
                deck_plugin_id, deck_plugin_version, binding_revision,
                status, applied_to
            ) VALUES (?, ?, ?, ?, ?, ?, 1, 'active', 'next_run')
            """,
            (
                binding_id,
                args.deck_id,
                workspace_id,
                str(user_id),
                BUILTIN_DECK_PLUGIN_ID,
                BUILTIN_DECK_PLUGIN_VERSION,
            ),
        )
        row = db.execute(
            "SELECT deck_plugin_binding_id FROM deck_plugin_bindings "
            "WHERE deck_id = ? AND binding_revision = 1",
            (args.deck_id,),
        ).fetchone()
        binding_id = row["deck_plugin_binding_id"]

        preflight_id = "pf_" + hashlib.sha256(f"pf:{args.seed}".encode("utf-8")).hexdigest()[:32]
        db.execute(
            """
            INSERT INTO workflow_preflights (
                workflow_preflight_id, request_fingerprint, deck_id,
                binding_revision, deck_plugin_id, deck_plugin_version,
                runtime_plugin_lock_id, deck_runtime_profile_id,
                deck_runtime_snapshot_id, input_hash, status, expires_at,
                created_by
            ) VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?, ?, 'passed', ?, ?)
            """,
            (
                preflight_id,
                _digest(f"fp:{args.seed}"),
                args.deck_id,
                BUILTIN_DECK_PLUGIN_ID,
                BUILTIN_DECK_PLUGIN_VERSION,
                BUILTIN_LOCK_ID,
                "profile_" + hashlib.sha256(f"profile:{args.seed}".encode("utf-8")).hexdigest()[:24],
                "snap_" + hashlib.sha256(f"snap:{args.seed}".encode("utf-8")).hexdigest()[:24],
                _digest(f"input:{args.seed}"),
                (datetime.now(UTC) + timedelta(hours=1)).isoformat(),
                str(user_id),
            ),
        )

        run_id = "run_" + hashlib.sha256(
            f"e2e-run:{args.seed}".encode("utf-8")
        ).hexdigest()[:32]
        now = datetime.now(UTC).isoformat()
        # Runs past `queued` must carry joint receipt + agent-session bindings
        # (WorkflowRun model validator); the ids are opaque to the read path.
        receipt_id = "rlr_" + hashlib.sha256(
            f"rlr:{args.seed}".encode("utf-8")
        ).hexdigest()[:32]
        agent_session_id = "as_" + hashlib.sha256(
            f"as:{args.seed}".encode("utf-8")
        ).hexdigest()[:32]
        db.execute(
            """
            INSERT INTO workflow_runs (
                id, workspace_id, deck_plugin_id, deck_plugin_version,
                workflow_definition_ref, deck_runtime_snapshot_id, status,
                deck_plugin_manifest_hash, deck_plugin_binding_id,
                binding_revision, runtime_plugin_lock_id, runtime_load_receipt_id,
                agent_session_id, workflow_preflight_id, source_voice_thread_id,
                source_message_id, source_message_time, idempotency_key,
                input_hash, semantic_fingerprint, created_by,
                created_at, started_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                run_id,
                workspace_id,
                BUILTIN_DECK_PLUGIN_ID,
                BUILTIN_DECK_PLUGIN_VERSION,
                release["workflow_definition_ref"],
                "snap_" + hashlib.sha256(f"snap:{args.seed}".encode("utf-8")).hexdigest()[:24],
                args.status,
                release["manifest_hash"],
                binding_id,
                BUILTIN_LOCK_ID,
                receipt_id,
                agent_session_id,
                preflight_id,
                args.thread_id,
                "srcmsg_" + hashlib.sha256(f"srcmsg:{args.seed}".encode("utf-8")).hexdigest()[:24],
                now,
                "e2e-idem-" + hashlib.sha256(f"idem:{args.seed}".encode("utf-8")).hexdigest()[:24],
                _digest(f"input:{args.seed}"),
                _digest(f"sem:{args.seed}"),
                str(user_id),
                now,
                now,
            ),
        )
        db.commit()
        print(
            json.dumps(
                {"run_id": run_id, "workspace_id": workspace_id, "user_id": user_id}
            )
        )
    finally:
        db.close()


if __name__ == "__main__":
    main()
