# [Input] Deck Plugin manifests and the pure degradation policy service.
# [Output] Fail-closed regression evidence without retired revocation/rollback persistence.
# [Pos] Provider-free Deck Plugin policy test boundary.
# [Sync] 2026-09-16: split active degradation behavior from the retired SQL fixture.

"""Regression tests for the active pure Deck Plugin degradation policy."""

from __future__ import annotations

from dataclasses import replace
import unittest

from backend.models.deck_plugin import DeckPluginManifestV1
from backend.services.deck_plugin.degradation_service import (
    DEGRADATION_NOT_DECLARED,
    DEGRADATION_OUTPUT_SCHEMA_MISMATCH,
    DEGRADATION_PERMISSION_DENIED,
    DEGRADATION_REQUIRED_PLUGIN_MISSING,
    DEGRADATION_SECURITY_REVOCATION,
    DegradationService,
    DegradedModeDefinition,
)
from backend.tests.test_deck_plugin_manifest import valid_manifest_data


def mode_manifest(*, declared: bool = True, optional: bool = True) -> DeckPluginManifestV1:
    data = valid_manifest_data()
    data["runtime"]["degraded_modes"] = ["without-voice-tools"] if declared else []
    data["runtime"]["claude_code_plugins"][0]["required"] = not optional
    return DeckPluginManifestV1.model_validate(data)


class DegradationTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        manifest = mode_manifest()
        plugin = manifest.runtime.claude_code_plugins[0]
        self.plugin_id = plugin.claude_code_plugin_id
        self.capability = plugin.capability_bindings[0]
        self.definition = DegradedModeDefinition(
            degraded_mode_id="without-voice-tools",
            optional_plugin_ids=frozenset({self.plugin_id}),
            omittable_capabilities=frozenset({self.capability}),
            replacement_steps=("skip_optional_voice_enrichment",),
            output_schema_ref=manifest.workflow.output_schema_ref,
        )
        self.service = DegradationService([self.definition])

    async def test_degradation_requires_manifest_declaration_and_same_schema(self) -> None:
        undeclared = await self.service.evaluate_degradation(
            mode_manifest(declared=False), [self.plugin_id], [self.capability]
        )
        self.assertFalse(undeclared.allowed)
        self.assertEqual(undeclared.error_code, DEGRADATION_NOT_DECLARED)

        allowed = await self.service.evaluate_degradation(
            mode_manifest(), [self.plugin_id], [self.capability]
        )
        self.assertTrue(allowed.allowed)
        self.assertEqual(allowed.degraded_mode_id, "without-voice-tools")
        self.assertTrue(allowed.user_confirmation_required)
        self.assertTrue(allowed.runtime_load_receipt_required)
        self.assertEqual(
            allowed.output_schema_ref, mode_manifest().workflow.output_schema_ref
        )

        wrong_schema = DegradationService(
            [replace(self.definition, output_schema_ref="schema://different")]
        )
        denied = await wrong_schema.evaluate_degradation(
            mode_manifest(), [self.plugin_id], [self.capability]
        )
        self.assertEqual(denied.error_code, DEGRADATION_OUTPUT_SCHEMA_MISMATCH)

    async def test_required_permission_and_revocation_never_auto_degrade(self) -> None:
        required = await self.service.evaluate_degradation(
            mode_manifest(optional=False), [self.plugin_id], [self.capability]
        )
        self.assertEqual(required.error_code, DEGRADATION_REQUIRED_PLUGIN_MISSING)

        unauthorized = await self.service.evaluate_degradation(
            mode_manifest(),
            [self.plugin_id],
            [self.capability],
            capability_authorization_satisfied=False,
        )
        self.assertEqual(unauthorized.error_code, DEGRADATION_PERMISSION_DENIED)

        revoked = await self.service.evaluate_degradation(
            mode_manifest(),
            [self.plugin_id],
            [self.capability],
            security_revoked=True,
        )
        self.assertEqual(revoked.error_code, DEGRADATION_SECURITY_REVOCATION)


if __name__ == "__main__":
    unittest.main()
