"""Tests for the Deck Plugin manifest and release foundation."""

from __future__ import annotations

import copy
import sqlite3
import unittest

from pydantic import ValidationError

from backend import database
from backend.models.deck_plugin import (
    DeckPluginManifestV1,
    DeckPluginReleaseStatus,
)
from backend.services.deck_plugin.manifest_validator import (
    DECK_PLUGIN_MANIFEST_INVALID,
    DECK_PLUGIN_SOURCE_DENIED,
    DeckPluginValidationError,
    is_valid_semver,
    validate_manifest,
)
from backend.services.deck_plugin.release_service import (
    DeckPluginReleaseService,
    DeckPluginReleaseStateError,
    assert_release_transition,
)


SOURCE_ALLOWLIST = {"marketplace://voice-decks"}


def valid_manifest_data() -> dict:
    return {
        "schema_version": "deck-plugin/v1",
        "deck_plugin_id": "voice-decks.story-dramatize",
        "deck_plugin_version": "3.1.0",
        "display_name": "Story dramatizer",
        "description": "Create reviewable story assets from a theme.",
        "author": "voice-decks",
        "status": "draft",
        "workflow": {
            "workflow_definition_ref": (
                "deck://voice-decks.story-dramatize/3.1.0/workflow.json"
            ),
            "input_schema_ref": "schema://story-workspace/input/v1",
            "output_schema_ref": "schema://story-workspace/result/v1",
            "steps": [
                {
                    "step_id": "outline",
                    "required_capabilities": ["story.context.read"],
                },
                {
                    "step_id": "draft",
                    "required_capabilities": ["story.result.produce"],
                },
            ],
        },
        "compatibility": {
            "deck_host_api": ">=1.0.0 <2.0.0",
            "claude_agent_contract": ">=1.0.0 <2.0.0",
            "claude_code": ">=2.0.0 <3.0.0",
            "story_output_schema": "1.0.0",
            "deck_runtime_snapshot_contract": "1.0.0",
        },
        "runtime_configuration": {
            "profile_contract": "story-generation/v1",
            "required_config_keys": ["model_policy", "prompt_template_ref"],
            "secret_ref_kinds": ["anthropic-auth"],
            "allow_profile_versions": ">=2.0.0 <3.0.0",
        },
        "capabilities": [
            "story.context.read",
            "story.result.produce",
            "workspace.files.read",
        ],
        "runtime": {
            "claude_code_plugins": [
                {
                    "claude_code_plugin_id": "ink-dream-tools@voice-decks",
                    "source_ref": "marketplace://voice-decks",
                    "version_constraint": "1.4.x",
                    "required": True,
                    "capability_bindings": [
                        "workspace.files.read",
                        "story.result.produce",
                    ],
                }
            ],
            "degraded_modes": [],
        },
        "dependencies": {"deck_plugin_releases": []},
    }


class ManifestValidatorTests(unittest.TestCase):
    def test_valid_manifest_covers_v1_contract(self):
        manifest = validate_manifest(
            valid_manifest_data(), source_allowlist=SOURCE_ALLOWLIST
        )
        self.assertIsInstance(manifest, DeckPluginManifestV1)
        self.assertEqual(manifest.schema_version, "deck-plugin/v1")
        self.assertEqual(manifest.runtime.claude_code_plugins[0].required, True)

    def test_semver_2_syntax(self):
        for value in ("0.0.0", "3.1.0", "1.2.3-alpha.1+build.5"):
            with self.subTest(value=value):
                self.assertTrue(is_valid_semver(value))
        for value in ("v1.0.0", "1.0", "01.0.0", "1.0.0-01", "latest"):
            with self.subTest(value=value):
                self.assertFalse(is_valid_semver(value))

        data = valid_manifest_data()
        data["deck_plugin_version"] = "1.0.00"
        with self.assertRaisesRegex(DeckPluginValidationError, "SemVer") as caught:
            validate_manifest(data, source_allowlist=SOURCE_ALLOWLIST)
        self.assertEqual(caught.exception.code, DECK_PLUGIN_MANIFEST_INVALID)

    def test_stable_identifier_is_required(self):
        data = valid_manifest_data()
        data["deck_plugin_id"] = "Story Plugin"
        with self.assertRaises(ValidationError):
            DeckPluginManifestV1.model_validate(data)
        with self.assertRaises(DeckPluginValidationError) as caught:
            validate_manifest(data, source_allowlist=SOURCE_ALLOWLIST)
        self.assertEqual(caught.exception.code, DECK_PLUGIN_MANIFEST_INVALID)

    def test_workflow_and_schema_refs_must_be_version_pinned(self):
        data = valid_manifest_data()
        data["workflow"]["workflow_definition_ref"] = (
            "deck://voice-decks.story-dramatize/latest/workflow.json"
        )
        with self.assertRaises(DeckPluginValidationError):
            validate_manifest(data, source_allowlist=SOURCE_ALLOWLIST)

        data = valid_manifest_data()
        data["workflow"]["input_schema_ref"] = "schema://story-workspace/input/latest"
        with self.assertRaises(DeckPluginValidationError):
            validate_manifest(data, source_allowlist=SOURCE_ALLOWLIST)

    def test_step_and_runtime_capabilities_must_be_declared(self):
        data = valid_manifest_data()
        data["workflow"]["steps"][0]["required_capabilities"] = ["admin.write"]
        with self.assertRaisesRegex(DeckPluginValidationError, "undeclared"):
            validate_manifest(data, source_allowlist=SOURCE_ALLOWLIST)

        data = valid_manifest_data()
        data["runtime"]["claude_code_plugins"][0]["capability_bindings"] = [
            "admin.write"
        ]
        with self.assertRaisesRegex(DeckPluginValidationError, "undeclared"):
            validate_manifest(data, source_allowlist=SOURCE_ALLOWLIST)

    def test_source_allowlist_and_local_production_source(self):
        with self.assertRaises(DeckPluginValidationError) as caught:
            validate_manifest(valid_manifest_data(), source_allowlist={"marketplace://other"})
        self.assertEqual(caught.exception.code, DECK_PLUGIN_SOURCE_DENIED)

        data = valid_manifest_data()
        data["runtime"]["claude_code_plugins"][0]["source_ref"] = "file:///tmp/plugin"
        with self.assertRaises(DeckPluginValidationError) as caught:
            validate_manifest(data, source_allowlist={"file:///tmp/plugin"})
        self.assertEqual(caught.exception.code, DECK_PLUGIN_SOURCE_DENIED)

        parsed = validate_manifest(data, source_allowlist=(), production=False)
        self.assertEqual(parsed.runtime.claude_code_plugins[0].source_ref, "file:///tmp/plugin")

    def test_pinned_allowlisted_source_is_accepted(self):
        data = valid_manifest_data()
        data["runtime"]["claude_code_plugins"][0]["source_ref"] = (
            "marketplace://voice-decks@2026-08-01"
        )
        validate_manifest(data, source_allowlist=SOURCE_ALLOWLIST)

    def test_plaintext_secrets_and_full_prompts_are_rejected(self):
        for key, value in (
            ("api_key", "not-allowed"),
            ("password", "not-allowed"),
            ("system_prompt", "full runtime prompt text"),
        ):
            data = valid_manifest_data()
            data["runtime_configuration"][key] = value
            with self.subTest(key=key):
                with self.assertRaises(DeckPluginValidationError) as caught:
                    validate_manifest(data, source_allowlist=SOURCE_ALLOWLIST)
                self.assertEqual(caught.exception.code, DECK_PLUGIN_MANIFEST_INVALID)

    def test_optional_plugin_requires_explicit_degraded_mode(self):
        data = valid_manifest_data()
        data["runtime"]["claude_code_plugins"][0]["required"] = False
        with self.assertRaisesRegex(DeckPluginValidationError, "degraded mode"):
            validate_manifest(data, source_allowlist=SOURCE_ALLOWLIST)

        data["runtime"]["degraded_modes"] = ["continue-without-story-tools"]
        validate_manifest(data, source_allowlist=SOURCE_ALLOWLIST)


class ReleaseServiceTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        database.create_tables(self.db)
        self.service = DeckPluginReleaseService(
            self.db, source_allowlist=SOURCE_ALLOWLIST
        )

    def tearDown(self):
        self.db.close()

    def test_database_initialization_is_idempotent_and_indexed(self):
        database.create_tables(self.db)
        table = self.db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name='deck_plugin_releases'"
        ).fetchone()
        self.assertIsNotNone(table)
        indexes = {
            row["name"]
            for row in self.db.execute("PRAGMA index_list('deck_plugin_releases')")
        }
        self.assertIn("idx_deck_plugin_releases_id_version", indexes)
        self.assertIn("idx_deck_plugin_releases_status", indexes)

    def test_database_table_can_be_rolled_back_and_recovered(self):
        self.db.execute("DROP TABLE deck_plugin_releases")
        database.create_tables(self.db)
        self.assertIsNotNone(
            self.db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' "
                "AND name='deck_plugin_releases'"
            ).fetchone()
        )

    def test_crud_unique_constraint_and_release_lifecycle(self):
        manifest = DeckPluginManifestV1.model_validate(valid_manifest_data())
        draft = self.service.create_draft(manifest)
        self.assertTrue(draft.id.startswith("dr_"))
        self.assertEqual(draft.status, DeckPluginReleaseStatus.DRAFT)
        draft_hash = draft.manifest_hash

        with self.assertRaises(DeckPluginValidationError) as caught:
            self.service.create_draft(manifest)
        self.assertEqual(caught.exception.code, DECK_PLUGIN_MANIFEST_INVALID)

        published = self.service.validate_release(draft.id)
        self.assertEqual(published.status, DeckPluginReleaseStatus.PUBLISHED)
        self.assertEqual(published.manifest.status, DeckPluginReleaseStatus.PUBLISHED)
        self.assertNotEqual(published.manifest_hash, draft_hash)
        self.assertIsNotNone(published.published_at)

        fetched = self.service.get_release(
            manifest.deck_plugin_id, manifest.deck_plugin_version
        )
        self.assertEqual(fetched.id, draft.id)

        deprecated = self.service.deprecate_release(draft.id)
        self.assertEqual(deprecated.status, DeckPluginReleaseStatus.DEPRECATED)
        self.assertEqual(deprecated.manifest_hash, published.manifest_hash)
        revoked = self.service.revoke_release(draft.id, "security policy")
        self.assertEqual(revoked.status, DeckPluginReleaseStatus.REVOKED)
        self.assertEqual(revoked.manifest_hash, published.manifest_hash)

    def test_invalid_transitions_are_rejected(self):
        with self.assertRaises(DeckPluginReleaseStateError):
            assert_release_transition(
                DeckPluginReleaseStatus.PUBLISHED, DeckPluginReleaseStatus.DRAFT
            )

        draft = self.service.create_draft(
            DeckPluginManifestV1.model_validate(valid_manifest_data())
        )
        with self.assertRaises(DeckPluginReleaseStateError):
            self.service.deprecate_release(draft.id)
        self.assertEqual(
            self.service.get_release(draft.deck_plugin_id, draft.deck_plugin_version).status,
            DeckPluginReleaseStatus.DRAFT,
        )

    def test_unique_constraint_is_enforced_by_sqlite(self):
        manifest = DeckPluginManifestV1.model_validate(valid_manifest_data())
        release = self.service.create_draft(manifest)
        row = self.db.execute(
            "SELECT * FROM deck_plugin_releases WHERE id = ?", (release.id,)
        ).fetchone()
        values = dict(row)
        values["id"] = "dr_duplicate"
        columns = list(values)
        placeholders = ",".join("?" for _ in columns)
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(
                f"INSERT INTO deck_plugin_releases ({','.join(columns)}) "
                f"VALUES ({placeholders})",
                [values[column] for column in columns],
            )


if __name__ == "__main__":
    unittest.main()
