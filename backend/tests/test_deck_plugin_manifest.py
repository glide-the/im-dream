"""Tests for the Deck Plugin manifest validation contract.

[Sync] 2026-09-16: retain pure validation after retiring Dream release persistence.
"""

from __future__ import annotations

import copy
import inspect
import unittest

from pydantic import ValidationError

from backend.models.deck_plugin import DeckPluginManifestV1
from backend.services.deck_plugin.manifest_validator import (
    DECK_PLUGIN_MANIFEST_INVALID,
    DECK_PLUGIN_SOURCE_DENIED,
    DeckPluginValidationError,
    is_valid_semver,
    validate_manifest,
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
    def test_validator_has_no_database_uniqueness_hook(self):
        parameters = inspect.signature(validate_manifest).parameters
        self.assertNotIn("db", parameters)
        self.assertNotIn("exclude_release_id", parameters)
        self.assertNotIn("SELECT", inspect.getsource(validate_manifest))

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


if __name__ == "__main__":
    unittest.main()
