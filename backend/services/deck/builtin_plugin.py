"""Seed and resolve the repository-owned Dream Story Claude SDK plugin."""

from __future__ import annotations

from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from typing import Any
import uuid

try:
    from backend.models.deck_plugin import DeckPluginManifestV1, DeckRuntimePluginLock
except ModuleNotFoundError:  # Support backend directory on PYTHONPATH.
    from models.deck_plugin import DeckPluginManifestV1, DeckRuntimePluginLock


BUILTIN_DECK_PLUGIN_ID = "ink.dream.story-workflow"
BUILTIN_DECK_PLUGIN_VERSION = "1.0.0"
BUILTIN_CLAUDE_PLUGIN_ID = "ink-dream-story@platform-builtin"
BUILTIN_SOURCE_REF = "builtin://ink-dream-story"
_LEGACY_BUILTIN_CLAUDE_PLUGIN_ID = "ink-dream-story@local"


def builtin_plugin_path() -> Path:
    return Path(__file__).resolve().parents[3] / "plugins" / "ink-dream-story"


def plugin_artifact_digest(path: Path | None = None) -> str:
    root = (path or builtin_plugin_path()).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Dream Story plugin directory is missing: {root}")
    digest = hashlib.sha256()
    files = sorted(item for item in root.rglob("*") if item.is_file())
    if not files:
        raise ValueError("Dream Story plugin directory is empty")
    for item in files:
        relative = item.relative_to(root).as_posix().encode("utf-8")
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        content = item.read_bytes()
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return "sha256:" + digest.hexdigest()


def resolve_builtin_source(source_ref: str) -> Path | None:
    if source_ref != BUILTIN_SOURCE_REF:
        return None
    return builtin_plugin_path().resolve()


def _builtin_manifest(
    claude_code_plugin_id: str = BUILTIN_CLAUDE_PLUGIN_ID,
) -> DeckPluginManifestV1:
    return DeckPluginManifestV1.model_validate(
        {
            "schema_version": "deck-plugin/v1",
            "deck_plugin_id": BUILTIN_DECK_PLUGIN_ID,
            "deck_plugin_version": BUILTIN_DECK_PLUGIN_VERSION,
            "display_name": "Dream Story Workflow",
            "description": (
                "Create structured story, character, and scene proposals "
                "for Dream review."
            ),
            "author": "Ink & Memory",
            "status": "published",
            "workflow": {
                "workflow_definition_ref": "builtin://ink-dream-story/workflow/v1",
                "input_schema_ref": "builtin://ink-dream-story/input/v1",
                "output_schema_ref": "story-workspace/agent-story/v1",
                "steps": [
                    {
                        "step_id": "propose_story_workspace_bundle",
                        "required_capabilities": ["story.workspace.propose"],
                    }
                ],
            },
            "compatibility": {
                "deck_host_api": "1.0.0",
                "claude_agent_contract": "1.0.0",
                "claude_code": "1.0.0",
                "story_output_schema": "1.0.0",
                "deck_runtime_snapshot_contract": "1.0.0",
            },
            "runtime_configuration": {
                "profile_contract": "deck-agent-profile/v1",
                "required_config_keys": [],
                "secret_ref_kinds": [],
                "allow_profile_versions": "1.x",
            },
            "capabilities": ["story.workspace.propose"],
            "runtime": {
                "claude_code_plugins": [
                    {
                        "claude_code_plugin_id": claude_code_plugin_id,
                        "source_ref": BUILTIN_SOURCE_REF,
                        "version_constraint": BUILTIN_DECK_PLUGIN_VERSION,
                        "required": True,
                        "capability_bindings": ["story.workspace.propose"],
                    }
                ],
                "degraded_modes": [],
            },
            "dependencies": {"deck_plugin_releases": []},
        }
    )


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _manifest_json_and_hash(
    manifest: DeckPluginManifestV1,
) -> tuple[str, str]:
    manifest_json = _canonical_json(manifest.model_dump(mode="json"))
    manifest_hash = (
        "sha256:" + hashlib.sha256(manifest_json.encode("utf-8")).hexdigest()
    )
    return manifest_json, manifest_hash


def _repair_legacy_builtin_release(
    db: Any,
    existing: Any,
) -> None:
    """Repair only the exact repository-owned pre-production built-in release."""
    try:
        manifest = DeckPluginManifestV1.model_validate_json(existing["manifest_json"])
    except ValueError:
        return

    persisted_manifest_json, persisted_manifest_hash = _manifest_json_and_hash(manifest)
    if (
        existing["manifest_hash"] != persisted_manifest_hash
        or manifest != _builtin_manifest(_LEGACY_BUILTIN_CLAUDE_PLUGIN_ID)
    ):
        return

    lock_row = db.execute(
        """
        SELECT id, deck_plugin_manifest_hash, lock_json
        FROM deck_runtime_plugin_locks
        WHERE deck_plugin_id = %s AND deck_plugin_version = %s
        """,
        (BUILTIN_DECK_PLUGIN_ID, BUILTIN_DECK_PLUGIN_VERSION),
    ).fetchone()
    if lock_row is None:
        return
    try:
        runtime_lock = DeckRuntimePluginLock.model_validate_json(lock_row["lock_json"])
    except ValueError:
        return

    entries = runtime_lock.claude_code_plugins
    if (
        lock_row["id"] != runtime_lock.runtime_plugin_lock_id
        or lock_row["deck_plugin_manifest_hash"] != persisted_manifest_hash
        or runtime_lock.deck_plugin_id != BUILTIN_DECK_PLUGIN_ID
        or runtime_lock.deck_plugin_version != BUILTIN_DECK_PLUGIN_VERSION
        or runtime_lock.deck_plugin_manifest_hash != persisted_manifest_hash
        or len(entries) != 1
        or entries[0].claude_code_plugin_id
        != _LEGACY_BUILTIN_CLAUDE_PLUGIN_ID
        or entries[0].resolved_version != BUILTIN_DECK_PLUGIN_VERSION
        or entries[0].source_ref != BUILTIN_SOURCE_REF
        or not entries[0].required
        or entries[0].capability_bindings != ["story.workspace.propose"]
        or runtime_lock.production_ready
        or runtime_lock.production_readiness_reasons
        != ["repository_local_plugin", "development_runtime_only"]
    ):
        return

    repaired_manifest = _builtin_manifest()
    repaired_manifest_json, repaired_manifest_hash = _manifest_json_and_hash(
        repaired_manifest
    )
    repaired_lock = DeckRuntimePluginLock(
        runtime_plugin_lock_id=runtime_lock.runtime_plugin_lock_id,
        deck_plugin_id=BUILTIN_DECK_PLUGIN_ID,
        deck_plugin_version=BUILTIN_DECK_PLUGIN_VERSION,
        deck_plugin_manifest_hash=repaired_manifest_hash,
        claude_code_plugins=[
            {
                "claude_code_plugin_id": BUILTIN_CLAUDE_PLUGIN_ID,
                "resolved_version": BUILTIN_DECK_PLUGIN_VERSION,
                "source_ref": BUILTIN_SOURCE_REF,
                "artifact_digest": plugin_artifact_digest(),
                "required": True,
                "capability_bindings": ["story.workspace.propose"],
            }
        ],
        created_at=runtime_lock.created_at,
        production_ready=True,
        production_readiness_reasons=[],
    )
    now = datetime.now(UTC).isoformat()
    with db:
        release_result = db.execute(
            """
            UPDATE deck_plugin_releases
            SET manifest_json = %s, manifest_hash = %s, runtime_spec_json = %s,
                updated_at = %s
            WHERE deck_plugin_id = %s AND deck_plugin_version = %s
              AND manifest_hash = %s AND manifest_json = %s
            """,
            (
                repaired_manifest_json,
                repaired_manifest_hash,
                _canonical_json(repaired_manifest.runtime.model_dump(mode="json")),
                now,
                BUILTIN_DECK_PLUGIN_ID,
                BUILTIN_DECK_PLUGIN_VERSION,
                persisted_manifest_hash,
                persisted_manifest_json,
            ),
        )
        lock_result = db.execute(
            """
            UPDATE deck_runtime_plugin_locks
            SET deck_plugin_manifest_hash = %s, lock_json = %s
            WHERE id = %s AND deck_plugin_id = %s AND deck_plugin_version = %s
              AND deck_plugin_manifest_hash = %s AND lock_json = %s
            """,
            (
                repaired_manifest_hash,
                repaired_lock.model_dump_json(),
                runtime_lock.runtime_plugin_lock_id,
                BUILTIN_DECK_PLUGIN_ID,
                BUILTIN_DECK_PLUGIN_VERSION,
                persisted_manifest_hash,
                lock_row["lock_json"],
            ),
        )
        if release_result.rowcount != 1 or lock_result.rowcount != 1:
            raise RuntimeError("built-in Deck Plugin legacy repair raced")


def seed_builtin_deck_plugin(db: Any) -> None:
    """Publish the immutable built-in workflow release once per database."""
    existing = db.execute(
        """
        SELECT manifest_json, manifest_hash FROM deck_plugin_releases
        WHERE deck_plugin_id = %s AND deck_plugin_version = %s
        """,
        (BUILTIN_DECK_PLUGIN_ID, BUILTIN_DECK_PLUGIN_VERSION),
    ).fetchone()
    if existing is not None:
        _repair_legacy_builtin_release(db, existing)
        return

    now = datetime.now(UTC)
    manifest = _builtin_manifest()
    manifest_json, manifest_hash = _manifest_json_and_hash(manifest)
    lock_id = "rpl_" + uuid.uuid5(
        uuid.NAMESPACE_URL,
        f"{BUILTIN_DECK_PLUGIN_ID}@{BUILTIN_DECK_PLUGIN_VERSION}",
    ).hex
    runtime_lock = DeckRuntimePluginLock(
        runtime_plugin_lock_id=lock_id,
        deck_plugin_id=BUILTIN_DECK_PLUGIN_ID,
        deck_plugin_version=BUILTIN_DECK_PLUGIN_VERSION,
        deck_plugin_manifest_hash=manifest_hash,
        claude_code_plugins=[
            {
                "claude_code_plugin_id": BUILTIN_CLAUDE_PLUGIN_ID,
                "resolved_version": BUILTIN_DECK_PLUGIN_VERSION,
                "source_ref": BUILTIN_SOURCE_REF,
                "artifact_digest": plugin_artifact_digest(),
                "required": True,
                "capability_bindings": ["story.workspace.propose"],
            }
        ],
        created_at=now,
        production_ready=True,
        production_readiness_reasons=[],
    )
    with db:
        db.execute(
            """
            INSERT INTO deck_plugin_releases (
                id, deck_plugin_id, deck_plugin_version, display_name,
                description, author, status, manifest_json, manifest_hash,
                workflow_definition_ref, input_schema_ref, output_schema_ref,
                capabilities_json, compatibility_json,
                deck_runtime_contract_json, runtime_spec_json,
                dependencies_json, created_at, updated_at, published_at
            ) VALUES (%s, %s, %s, %s, %s, %s, 'published', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                "dr_" + uuid.uuid5(uuid.NAMESPACE_URL, BUILTIN_DECK_PLUGIN_ID).hex,
                manifest.deck_plugin_id,
                manifest.deck_plugin_version,
                manifest.display_name,
                manifest.description,
                manifest.author,
                manifest_json,
                manifest_hash,
                manifest.workflow.workflow_definition_ref,
                manifest.workflow.input_schema_ref,
                manifest.workflow.output_schema_ref,
                json.dumps(manifest.capabilities, separators=(",", ":")),
                json.dumps(manifest.compatibility.model_dump(mode="json"), separators=(",", ":")),
                json.dumps(
                    manifest.runtime_configuration.model_dump(mode="json"),
                    separators=(",", ":"),
                ),
                json.dumps(manifest.runtime.model_dump(mode="json"), separators=(",", ":")),
                json.dumps(manifest.dependencies.model_dump(mode="json"), separators=(",", ":")),
                now.isoformat(),
                now.isoformat(),
                now.isoformat(),
            ),
        )
        db.execute(
            """
            INSERT INTO deck_runtime_plugin_locks (
                id, deck_plugin_id, deck_plugin_version,
                deck_plugin_manifest_hash, lock_json, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                lock_id,
                manifest.deck_plugin_id,
                manifest.deck_plugin_version,
                manifest_hash,
                runtime_lock.model_dump_json(),
                now.isoformat(),
            ),
        )
